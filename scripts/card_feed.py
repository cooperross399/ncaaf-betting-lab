#!/usr/bin/env python3
"""The card-feed branch: stand down, restore, publish, and tell a human.

    python scripts/card_feed.py standdown   # writes run=yes|no to $GITHUB_OUTPUT
    python scripts/card_feed.py restore     # ledger and snapshots from the branch
    python scripts/card_feed.py publish     # card, ledger, snapshots, status
    python scripts/card_feed.py post        # the card, or a loud degraded notice

Ported from the shell in the sibling NFL lab's gameday workflow, and moved
into Python on purpose. `tests/test_workflows.py` executes every run block
with each command stubbed to fail and refuses any block that carries on past
a failure, which is exactly right for a test job and leaves no way to write
"the branch may not exist yet" in shell. Here that branch is an explicit
question with three answers — present, absent, could not tell — and the
third is an error, never a guess. That is also what makes it testable.

## The feed is the evidence, so it is built with plumbing

Only the files named below can reach the branch. A `git add -A` on a working
tree holding staged prices and a `.env` is how a credential reaches a ref.
Anything the run does not hold locally (a run that died before restoring) is
carried forward from the branch tip rather than published as an absence: the
ledger cannot be back-dated, so a commit that omits it destroys it.

## A broken day retries, a bounded number of times

Thirteen hourly triggers run, and the first clean publish stands the rest
down. A degraded publish does not — the next trigger retries — but only
`MAX_ATTEMPTS` times a league day, because the credit cap is per run and an
unbounded retry on a provider outage would spend it thirteen times.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ncaaf_betting_lab.config import ARCHIVE_DIR, OUTPUTS_DIR, PROCESSED_DIR
from ncaaf_betting_lab.forward_evidence import LEDGER_FILENAME, SNAPSHOT_DIRNAME
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from ncaaf_betting_lab.season import game_date

BRANCH = "card-feed"
TIP_REF = "refs/card-feed-tip"
STATUS_FILE = "latest_status.json"
CARD_FILE = "card.md"
SELECTIONS_FILE = "selections.json"
SNAPSHOTS_TREE = "snapshots"
#: The operating-home issue. A contract string: matched exactly, em dash and
#: all, so a near-miss posts nowhere rather than somewhere wrong.
OPERATING_HOME = "NCAAF Betting Lab — Claude Operating Home"
CHANGED_MARKER = "Selections changed"
MAX_ATTEMPTS = 3
DEGRADED = "degraded"


class FeedError(RuntimeError):
    """The branch could not be read or written, and nothing was guessed."""


@dataclass(frozen=True)
class Decision:
    run: bool
    reason: str


def standdown_decision(
    status: dict | None, *, today: str, max_attempts: int = MAX_ATTEMPTS
) -> Decision:
    """Whether a scheduled trigger should card today. Pure, so it is tested.

    The league date, never UTC: the card stamps its slate in league time, and
    a guard on another calendar stands down on the wrong day the moment a
    trigger moves either side of midnight UTC.
    """
    if not status:
        return Decision(True, "no status on the feed yet")
    if str(status.get("slate_date", "")) != today:
        return Decision(True, f"the feed's last card is for {status.get('slate_date')}")
    decision = str(status.get("decision", ""))
    if decision != DEGRADED:
        return Decision(False, f"today's card already published ({decision})")
    attempts = int(status.get("attempts", 1) or 1)
    if attempts >= max_attempts:
        return Decision(
            False,
            f"today has failed {attempts} time(s), the most a day retries. "
            "A human dispatch still runs; a scheduled one would spend the cap "
            "again on whatever broke the last three.",
        )
    return Decision(True, f"today's last attempt was degraded ({attempts} so far)")


def next_status(
    previous: dict | None, *, today: str, decision: str, run_id: str
) -> dict:
    attempts = 1
    if previous and str(previous.get("slate_date", "")) == today:
        attempts = int(previous.get("attempts", 1) or 1) + 1
    return {
        "slate_date": today,
        "decision": decision,
        "run": run_id,
        "attempts": attempts,
    }


def selections_changed(previous: list | None, current: list) -> bool:
    def keys(items: list | None) -> set[tuple]:
        return {
            (i.get("game"), i.get("market"), i.get("selection"), i.get("line"))
            for i in (items or [])
            if isinstance(i, dict)
        }

    return keys(previous) != keys(current)


# -- git, authenticated without putting the token in a URL ----------------


class Feed:
    def __init__(self, repository: str, token: str, workdir: Path) -> None:
        if not repository or not token:
            raise FeedError(
                "GITHUB_REPOSITORY and GH_TOKEN must both be set. The "
                "repository is private, so an unauthenticated read cannot see "
                "the branch — and a guard that cannot see it must not guess."
            )
        self.remote = f"https://github.com/{repository}"
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        self._auth = f"http.extraheader=AUTHORIZATION: basic {basic}"
        self.workdir = workdir

    def git(self, *args: str, check: bool = True, stdin: str | None = None) -> str:
        completed = subprocess.run(
            ["git", "-c", self._auth, *args],
            cwd=self.workdir,
            input=stdin,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            # The command line carries the auth header, so it is never printed.
            raise FeedError(f"git {args[0]} failed: {completed.stderr.strip()[:400]}")
        return completed.stdout

    def fetch_tip(self) -> bool:
        """True when the branch exists and was fetched; False when it does not.

        `ls-remote` first, because a failed fetch cannot tell "no branch" from
        "no access", and only one of those is safe to proceed on.
        """
        heads = self.git("ls-remote", "--heads", self.remote, BRANCH)
        if not heads.strip():
            return False
        self.git("fetch", "--depth=1", self.remote, f"+refs/heads/{BRANCH}:{TIP_REF}")
        return True

    def has(self, path: str) -> bool:
        return (
            subprocess.run(
                ["git", "cat-file", "-e", f"{TIP_REF}:{path}"],
                cwd=self.workdir,
                capture_output=True,
            ).returncode
            == 0
        )

    def show(self, path: str) -> str:
        return self.git("show", f"{TIP_REF}:{path}")

    def show_bytes(self, path: str) -> bytes:
        completed = subprocess.run(
            ["git", "show", f"{TIP_REF}:{path}"], cwd=self.workdir, capture_output=True
        )
        if completed.returncode != 0:
            raise FeedError(f"could not read {path} from the feed")
        return completed.stdout

    def status(self) -> dict | None:
        if not self.has(STATUS_FILE):
            return None
        try:
            payload = json.loads(self.show(STATUS_FILE))
        except json.JSONDecodeError as exc:
            raise FeedError(f"{STATUS_FILE} on the feed is not JSON: {exc}") from exc
        return payload if isinstance(payload, dict) else None


def _feed() -> Feed:
    workdir = Path(tempfile.mkdtemp(prefix="card-feed-"))
    subprocess.run(["git", "init", "-q", str(workdir)], check=True)
    return Feed(
        os.environ.get("GITHUB_REPOSITORY", ""),
        os.environ.get("GH_TOKEN", ""),
        workdir,
    )


def _output(name: str, value: str) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    print(f"{name}={value}")


def _today(league) -> str:
    return game_date(datetime.now(timezone.utc).isoformat(), league)


def _run_status(league) -> dict:
    """What `run_gameday_card.py` recorded about itself, or a degraded stand-in."""
    path = OUTPUTS_DIR / league.output_name("card_run", ".json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"decision": DEGRADED, "selections": []}
    return payload if isinstance(payload, dict) else {"decision": DEGRADED}


# -- the four commands ----------------------------------------------------


def cmd_standdown(league, *, respect: bool) -> int:
    if not respect:
        _output("run", "yes")
        print("Not a scheduled trigger and not asked to respect the standdown; running.")
        return 0
    feed = _feed()
    status = feed.status() if feed.fetch_tip() else None
    decision = standdown_decision(status, today=_today(league))
    print(decision.reason)
    if not decision.run and status and status.get("decision") == DEGRADED:
        print(f"::warning::{decision.reason}")
    _output("run", "yes" if decision.run else "no")
    return 0


def cmd_restore(league) -> int:
    feed = _feed()
    ledger = PROCESSED_DIR / LEDGER_FILENAME
    snapshots = ARCHIVE_DIR / SNAPSHOT_DIRNAME
    ledger.parent.mkdir(parents=True, exist_ok=True)
    snapshots.mkdir(parents=True, exist_ok=True)
    if not feed.fetch_tip():
        print(
            "::warning::No card-feed branch. Correct on the first run ever; "
            "on any later run the season's ledger is gone."
        )
        return 0
    if feed.has(LEDGER_FILENAME):
        data = feed.show_bytes(LEDGER_FILENAME)
        if not data:
            raise FeedError("the feed's ledger is empty; refusing to restore nothing")
        ledger.write_bytes(data)
        rows = data.count(b"\n") - 1
        print(f"Ledger restored: {rows} row(s).")
    else:
        print("No ledger on the feed yet.")
    restored = 0
    if feed.has(SNAPSHOTS_TREE):
        for name in feed.git("ls-tree", "--name-only", f"{TIP_REF}:{SNAPSHOTS_TREE}").split():
            data = feed.show_bytes(f"{SNAPSHOTS_TREE}/{name}")
            if data:
                (snapshots / name).write_bytes(data)
                restored += 1
            else:
                print(f"::warning::{name} on the feed is empty and was not restored.")
    print(f"Snapshots restored: {restored}.")
    return 0


def cmd_publish(league, *, run_id: str) -> int:
    feed = _feed()
    has_tip = feed.fetch_tip()
    today = _today(league)
    previous = feed.status() if has_tip else None
    run = _run_status(league)
    decision = str(run.get("decision") or DEGRADED)
    status = next_status(previous, today=today, decision=decision, run_id=run_id)

    def blob(data: bytes) -> str:
        handle = feed.workdir / "blob.tmp"
        handle.write_bytes(data)
        return feed.git("hash-object", "-w", str(handle)).strip()

    root: list[str] = []
    root.append(
        f"100644 blob {blob((json.dumps(status, indent=2) + chr(10)).encode())}\t{STATUS_FILE}"
    )
    card = OUTPUTS_DIR / league.output_name("gameday_card", ".md")
    if card.is_file() and decision != DEGRADED:
        root.append(f"100644 blob {blob(card.read_bytes())}\t{CARD_FILE}")
        selections = run.get("selections") or []
        root.append(
            f"100644 blob {blob((json.dumps(selections, indent=2) + chr(10)).encode())}"
            f"\t{SELECTIONS_FILE}"
        )
    elif has_tip:
        for carried in (CARD_FILE, SELECTIONS_FILE):
            if feed.has(carried):
                sha = feed.git("rev-parse", f"{TIP_REF}:{carried}").strip()
                root.append(f"100644 blob {sha}\t{carried}")

    ledger = PROCESSED_DIR / LEDGER_FILENAME
    if ledger.is_file() and ledger.stat().st_size:
        root.append(f"100644 blob {blob(ledger.read_bytes())}\t{LEDGER_FILENAME}")
    elif has_tip and feed.has(LEDGER_FILENAME):
        sha = feed.git("rev-parse", f"{TIP_REF}:{LEDGER_FILENAME}").strip()
        root.append(f"100644 blob {sha}\t{LEDGER_FILENAME}")
        print("::warning::No local ledger; carried the feed's copy forward.")

    snapshot_entries = [
        f"100644 blob {blob(path.read_bytes())}\t{path.name}"
        for path in sorted((ARCHIVE_DIR / SNAPSHOT_DIRNAME).glob("*.csv"))
        if path.stat().st_size
    ]
    if snapshot_entries:
        tree = feed.git("mktree", stdin="\n".join(snapshot_entries) + "\n").strip()
        root.append(f"040000 tree {tree}\t{SNAPSHOTS_TREE}")
    elif has_tip and feed.has(SNAPSHOTS_TREE):
        sha = feed.git("rev-parse", f"{TIP_REF}:{SNAPSHOTS_TREE}").strip()
        root.append(f"040000 tree {sha}\t{SNAPSHOTS_TREE}")
        print("::warning::No local snapshots; carried the feed's tree forward.")

    tree = feed.git("mktree", stdin="\n".join(root) + "\n").strip()
    identity = [
        "-c", "user.name=github-actions[bot]",
        "-c", "user.email=github-actions[bot]@users.noreply.github.com",
    ]
    message = f"card {today} ({decision})"
    parent = ["-p", feed.git("rev-parse", TIP_REF).strip()] if has_tip else []
    commit = feed.git(*identity, "commit-tree", tree, *parent, "-m", message).strip()
    feed.git("push", feed.remote, f"{commit}:refs/heads/{BRANCH}")
    print(f"card-feed updated for {today} ({decision}, attempt {status['attempts']}).")

    # Remembered for `post`, which compares against the feed as it was.
    previous_selections = None
    if has_tip and feed.has(SELECTIONS_FILE):
        try:
            previous_selections = json.loads(feed.show(SELECTIONS_FILE))
        except json.JSONDecodeError:
            previous_selections = None
    marker = OUTPUTS_DIR / league.output_name("card_previous_selections", ".json")
    marker.write_text(json.dumps(previous_selections), encoding="utf-8")
    return 0


def cmd_post(league, *, run_url: str) -> int:
    token = os.environ.get("GH_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repository:
        raise FeedError("GH_TOKEN and GITHUB_REPOSITORY must be set to post.")
    run = _run_status(league)
    decision = str(run.get("decision") or DEGRADED)
    card = OUTPUTS_DIR / league.output_name("gameday_card", ".md")
    if decision == DEGRADED or not card.is_file():
        body = (
            "## Run did not complete\n\nNo card was published from this run. "
            "**This is a fault, not a quiet day.** The next scheduled trigger "
            f"retries, up to {MAX_ATTEMPTS} times a day.\n"
        )
    else:
        body = card.read_text(encoding="utf-8")
        previous_path = OUTPUTS_DIR / league.output_name(
            "card_previous_selections", ".json"
        )
        try:
            previous = json.loads(previous_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = None
        if selections_changed(previous, run.get("selections") or []):
            body = f"**{CHANGED_MARKER}** since the last published card.\n\n" + body
    body += f"\n---\n[Run]({run_url})\n"

    number = _find_issue(repository, token)
    if number is None:
        print(
            f"::warning::No issue titled '{OPERATING_HOME}'. Nothing was posted, "
            "and a broken run would go unnoticed. Create the issue."
        )
        return 0
    _api(
        f"/repos/{repository}/issues/{number}/comments",
        token,
        data={"body": body[:65000]},
    )
    print(f"Posted to operating home #{number} (decision: {decision}).")
    return 0


def _api(path: str, token: str, *, data: dict | None = None):
    request = urllib.request.Request(
        "https://api.github.com" + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8") or "null")


def _find_issue(repository: str, token: str) -> int | None:
    for page in range(1, 6):
        query = urllib.parse.urlencode({"state": "all", "per_page": 100, "page": page})
        issues = _api(f"/repos/{repository}/issues?{query}", token)
        if not issues:
            return None
        for issue in issues:
            if issue.get("title") == OPERATING_HOME and "pull_request" not in issue:
                return int(issue["number"])
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("standdown", "restore", "publish", "post"))
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--respect-standdown", default="true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args(argv)
    league = league_for(args.league)
    try:
        if args.command == "standdown":
            return cmd_standdown(
                league, respect=args.respect_standdown.strip().lower() == "true"
            )
        if args.command == "restore":
            return cmd_restore(league)
        if args.command == "publish":
            return cmd_publish(league, run_id=args.run_id)
        return cmd_post(league, run_url=args.run_url)
    except FeedError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
