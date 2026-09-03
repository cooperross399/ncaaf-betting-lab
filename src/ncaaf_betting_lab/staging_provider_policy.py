"""The fail-closed provider policy.

`data/manual/staging_provider_policy.json` decides which provider and which
markets the card may use, **per league**. It ships allowlisting nothing, and
every failure mode here resolves to "not allowed":

* file missing -> not allowed
* file unreadable -> not allowed
* file malformed -> not allowed
* entry for a different league -> not allowed
* market absent from `required_markets` -> not allowed
* allowlist entry without a reviewer and a receipt id -> not allowed
* receipt file named but not present on disk -> not allowed

That is the whole design. A policy loader that returns a permissive default on
an unreadable file is a policy loader that stops existing the moment something
goes wrong, which is exactly when it matters.

## Why the entries are keyed by league

Approving `player_pass_yds` in the NFL says nothing about approving it in
college football, where the distribution, the roster churn and the books' own
coverage are all different. One receipt, one league. The key is
`the_odds_api:nfl`, built by `League.policy_key()`, so a policy file cannot
express "allowed everywhere" even by accident.

## What Claude may never do

Claude may prepare a policy change and open a pull request for it. Claude may
never write a receipt, add a name to `allowed_provider_names`, or add a market
to `required_markets`. Those are Cooper's, and the PR gate re-verifies the
paperwork on every policy change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ncaaf_betting_lab.config import MANUAL_DIR
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.markets import MARKETS_BY_KEY


POLICY_FILENAME = "staging_provider_policy.json"
RECEIPTS_DIRNAME = "human_acceptance_receipts"

#: The one provider this lab is built around. Naming it here does not allow
#: it; the policy file does that, and it does not.
ODDS_API_PROVIDER_NAME = "the_odds_api"


@dataclass(frozen=True)
class AllowlistEntry:
    """One league's reviewed approval, and exactly what it covers."""

    policy_key: str
    status: str
    approved_at: str
    reviewer_name: str
    evidence_receipt_id: str
    required_markets: tuple[str, ...]
    known_limitations: tuple[str, ...] = ()

    @property
    def is_allowed(self) -> bool:
        """Every condition, not any of them.

        A status of "allowed" with no reviewer is what a half-finished edit
        looks like, and it must not read as an approval.
        """
        return (
            self.status == "allowed"
            and bool(self.reviewer_name.strip())
            and bool(self.evidence_receipt_id.strip())
            and bool(self.required_markets)
        )


class StagingProviderPolicy:
    """What the card is allowed to read, and the reason when it is not."""

    def __init__(
        self,
        entries: dict[str, AllowlistEntry] | None = None,
        *,
        load_error: str = "",
        manual_dir: Path | None = None,
    ) -> None:
        self.entries = dict(entries or {})
        self.load_error = load_error
        self.manual_dir = Path(manual_dir) if manual_dir else MANUAL_DIR

    # -- loading ----------------------------------------------------------

    @classmethod
    def load(
        cls, path: Path | None = None, *, manual_dir: Path | None = None
    ) -> "StagingProviderPolicy":
        directory = Path(manual_dir) if manual_dir else MANUAL_DIR
        target = Path(path) if path else directory / POLICY_FILENAME
        if not target.is_file():
            return cls(
                load_error=f"No policy file at {target}.", manual_dir=directory
            )
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return cls(
                load_error=f"The policy file could not be read: {exc}.",
                manual_dir=directory,
            )
        if not isinstance(payload, dict):
            return cls(
                load_error="The policy file is not a JSON object.",
                manual_dir=directory,
            )
        raw = payload.get("provider_allowlist_entries")
        if not isinstance(raw, dict):
            return cls(manual_dir=directory)

        entries: dict[str, AllowlistEntry] = {}
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            entries[str(key)] = AllowlistEntry(
                policy_key=str(key),
                status=str(value.get("allowlist_status", "")).strip().lower(),
                approved_at=str(value.get("approved_at", "")).strip(),
                reviewer_name=str(value.get("reviewer_name", "")).strip(),
                evidence_receipt_id=str(value.get("evidence_receipt_id", "")).strip(),
                required_markets=tuple(
                    str(item).strip()
                    for item in (value.get("required_markets") or [])
                    if str(item).strip()
                ),
                known_limitations=tuple(
                    str(item) for item in (value.get("known_limitations") or [])
                ),
            )
        return cls(entries, manual_dir=directory)

    # -- decisions --------------------------------------------------------

    def entry_for(self, league: League) -> AllowlistEntry | None:
        return self.entries.get(league.policy_key())

    def receipt_path(self, entry: AllowlistEntry) -> Path:
        return self.manual_dir / RECEIPTS_DIRNAME / f"{entry.evidence_receipt_id}.md"

    def market_allowed(self, league: League, market: str) -> bool:
        """The one question the card asks. Every path out of it is explicit."""
        if self.load_error:
            return False
        entry = self.entry_for(league)
        if entry is None or not entry.is_allowed:
            return False
        key = str(market).strip()
        if key not in MARKETS_BY_KEY:
            # A market this lab cannot price or settle is never allowed, even
            # if a policy file names it. The policy grants permission; it does
            # not confer the ability to settle a bet.
            return False
        if key not in entry.required_markets:
            return False
        # The receipt must exist on disk, not merely be named. An id pointing
        # at nothing is the shape a fabricated approval takes.
        return self.receipt_path(entry).is_file()

    def refusal_reason(self, league: League, market: str) -> str:
        """Why a market is not allowed, in words a card can print."""
        if self.load_error:
            return (
                f"{self.load_error} A policy that cannot be read allows "
                "nothing, so no market may reach the card."
            )
        entry = self.entry_for(league)
        if entry is None:
            if self.entries:
                # There are approvals, just not for this league. Say which,
                # because "no approval anywhere" and "approved next door"
                # are different situations and only one of them is a
                # question for Cooper.
                return (
                    f"No approval covers `{league.policy_key()}`. Other "
                    f"entries exist ({', '.join(sorted(self.entries))}) and "
                    "none carries across: the distributions, the roster churn "
                    "and the books' coverage differ by league."
                )
            return (
                "No market has a reviewed approval yet. Allowlisting takes "
                "measurement against real prices and a signed human "
                "acceptance receipt, and this is the correct state until "
                "both exist."
            )
        if not entry.is_allowed:
            missing = [
                name
                for name, present in (
                    ("a status of 'allowed'", entry.status == "allowed"),
                    ("a reviewer name", bool(entry.reviewer_name.strip())),
                    ("an evidence receipt id", bool(entry.evidence_receipt_id.strip())),
                    ("a non-empty market list", bool(entry.required_markets)),
                )
                if not present
            ]
            return (
                f"The allowlist entry for `{league.policy_key()}` is not a "
                f"complete approval: it lacks {', '.join(missing)}."
            )
        key = str(market).strip()
        if key not in MARKETS_BY_KEY:
            return (
                f"`{key}` is not a market this lab knows how to price or "
                "settle, so no approval can make it usable."
            )
        if key not in entry.required_markets:
            return (
                f"`{key}` is not named in the reviewed approval for "
                f"`{league.policy_key()}` (receipt "
                f"`{entry.evidence_receipt_id}`). Measurement and a signed "
                "human acceptance receipt are what add a market; nothing else."
            )
        path = self.receipt_path(entry)
        if not path.is_file():
            return (
                f"The approval names receipt `{entry.evidence_receipt_id}` but "
                f"no such file exists at {path}. An id pointing at nothing is "
                "not an approval."
            )
        return ""

    def allowed_markets(self, league: League) -> tuple[str, ...]:
        entry = self.entry_for(league)
        if entry is None:
            return ()
        return tuple(
            market
            for market in entry.required_markets
            if self.market_allowed(league, market)
        )

    def summary_line(self, league: League) -> str:
        allowed = self.allowed_markets(league)
        if not allowed:
            return (
                f"No market is allowlisted for {league.title}. That is the "
                "correct state until a market has been measured against real "
                "prices and Cooper has signed a receipt."
            )
        return (
            f"{len(allowed)} market(s) allowlisted for {league.title}: "
            f"{', '.join(allowed)}."
        )


def write_starter_policy(path: Path) -> None:
    """Write the shipping policy: allowlisting nothing.

    Exists so the file's default state is created by code with a comment
    explaining itself, rather than by hand where a future edit could quietly
    turn an empty list into a populated one with no reviewer.
    """
    payload: dict[str, Any] = {
        "_comment": [
            "This file decides which provider and which markets the card may",
            "use, per league. It ships allowlisting NOTHING, and that is the",
            "correct state until a market has been measured against real",
            "prices and Cooper has reviewed the evidence and signed a human",
            "acceptance receipt.",
            "",
            "Entries are keyed `{provider}:{league}`. Approving a market in",
            "the NFL never approves it in NCAAF.",
            "",
            "Claude may prepare a change to this file and open a pull request",
            "for it. Claude may never add a provider, add a market, or write a",
            "receipt. See docs/provider_allowlist_approval.md.",
        ],
        "allowed_provider_names": [],
        "provider_allowlist_entries": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
