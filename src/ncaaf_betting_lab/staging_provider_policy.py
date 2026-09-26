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
* receipt unreadable, a symlink, for another league, naming another id, or
  signed by a different reviewer than the entry names -> not allowed
* market absent from the receipt's own `approved_markets` -> not allowed
* entry's provider absent from `allowed_provider_names` -> not allowed

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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ncaaf_betting_lab.config import MANUAL_DIR
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.markets import MARKETS_BY_KEY


POLICY_FILENAME = "staging_provider_policy.json"
RECEIPTS_DIRNAME = "human_acceptance_receipts"

#: A receipt id becomes a filename. Anything outside this could climb out of
#: the receipts directory, and a receipt read from elsewhere is not a receipt.
RECEIPT_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,128}")

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
    def provider_name(self) -> str:
        """`the_odds_api` in `the_odds_api:nfl`: the name that has to appear in
        `allowed_provider_names` for this entry to count."""
        return self.policy_key.split(":", 1)[0].strip()

    def missing(self) -> tuple[str, ...]:
        """What a complete approval has that this entry lacks."""
        return tuple(
            name
            for name, present in (
                ("a status of 'allowed'", self.status == "allowed"),
                ("a reviewer name", bool(self.reviewer_name.strip())),
                ("an evidence receipt id", bool(self.evidence_receipt_id.strip())),
                ("a non-empty market list", bool(self.required_markets)),
            )
            if not present
        )

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
        allowed_provider_names: tuple[str, ...] = (),
    ) -> None:
        self.entries = dict(entries or {})
        self.load_error = load_error
        self.manual_dir = Path(manual_dir) if manual_dir else MANUAL_DIR
        self.allowed_provider_names = tuple(allowed_provider_names)
        #: Each receipt is read once per loaded policy, so every decision in a
        #: card run is judged against the same bytes: the list checked is the
        #: list used, for the whole run and not just for one call.
        self._receipts: dict[tuple[str, str], tuple[dict[str, Any] | None, str]] = {}

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
        names_value = payload.get("allowed_provider_names")
        names = tuple(
            str(item).strip()
            for item in (names_value if isinstance(names_value, list) else [])
            if isinstance(item, str) and item.strip()
        )
        raw = payload.get("provider_allowlist_entries")
        if not isinstance(raw, dict):
            return cls(manual_dir=directory, allowed_provider_names=names)

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
        return cls(entries, manual_dir=directory, allowed_provider_names=names)

    # -- decisions --------------------------------------------------------

    def entry_for(self, league: League) -> AllowlistEntry | None:
        return self.entries.get(league.policy_key())

    def receipts_dir(self) -> Path:
        return self.manual_dir / RECEIPTS_DIRNAME

    def receipt_path(self, entry: AllowlistEntry) -> Path:
        """Where the cited receipt has to be. Refuses to build a path from an
        id that could point anywhere else: every path construction goes
        through this guard, not just the one `load_receipt` makes."""
        identifier = entry.evidence_receipt_id
        if not RECEIPT_ID_PATTERN.fullmatch(identifier):
            raise ValueError(f"receipt id {identifier!r} is not a safe filename")
        return self.receipts_dir() / f"{identifier}.json"

    def load_receipt(self, entry: AllowlistEntry) -> tuple[dict[str, Any] | None, str]:
        """The receipt an entry cites, opened and read, or why it could not be.

        Opened, not merely found. A receipt that only had to exist approved
        whatever the policy file said it approved: a file containing the word
        "signed" was as good as a reviewed decision, and so was a real receipt
        for two markets sitting under an entry that lists twenty.
        """
        identifier = entry.evidence_receipt_id
        try:
            path = self.receipt_path(entry)
        except ValueError as exc:
            return None, str(exc)
        try:
            # A symlink committed into the receipts directory would read a
            # file from anywhere on disk as a receipt; so would a real file
            # whose resolved location is elsewhere. Neither is a receipt.
            if path.is_symlink() or not path.resolve().is_relative_to(
                self.receipts_dir().resolve()
            ):
                return None, (
                    f"receipt `{identifier}` is not a regular file inside "
                    f"`data/manual/{RECEIPTS_DIRNAME}/`"
                )
            if not path.is_file():
                return None, (
                    f"the approval names receipt `{identifier}` but no such "
                    f"file exists at {path}. An id pointing at nothing is not "
                    "an approval"
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            return None, f"receipt `{identifier}` could not be read: {exc}"
        if not isinstance(payload, dict):
            return None, f"receipt `{identifier}` is not a JSON object"
        return payload, ""

    def checked_receipt(
        self, entry: AllowlistEntry
    ) -> tuple[dict[str, Any] | None, str]:
        """The receipt, if it can stand behind this entry; else why not.

        What the card checks on every run. The PR gate
        (`reports/policy_pr_gate.py`) checks this and more - the reviewer's
        statement, the review time, the evidence checksums - because those
        are properties of the paperwork, and the paperwork only changes in a
        pull request.
        """
        cache_key = (entry.policy_key, entry.evidence_receipt_id)
        if cache_key not in self._receipts:
            payload, error = self.load_receipt(entry)
            if payload is not None:
                error = self._receipt_field_problem(entry, payload)
                if error:
                    payload = None
            self._receipts[cache_key] = (payload, error)
        return self._receipts[cache_key]

    def _receipt_field_problem(
        self, entry: AllowlistEntry, payload: dict[str, Any]
    ) -> str:
        identifier = entry.evidence_receipt_id
        if str(payload.get("receipt_id", "")).strip() != identifier:
            return (
                f"receipt file `{identifier}.json` names itself "
                f"{payload.get('receipt_id')!r}. A receipt copied under a new "
                "name is not the receipt the approval cites"
            )
        if str(payload.get("policy_key", "")).strip() != entry.policy_key:
            return (
                f"receipt `{identifier}` approves {payload.get('policy_key')!r}, "
                f"not `{entry.policy_key}`. One receipt, one league"
            )
        reviewer = str(payload.get("reviewer_name", "")).strip()
        if not reviewer:
            return f"receipt `{identifier}` names no reviewer"
        if reviewer != entry.reviewer_name.strip():
            return (
                f"receipt `{identifier}` is signed by {reviewer!r} but the "
                f"entry names {entry.reviewer_name!r}. A receipt is one "
                "person's decision, and the entry has to say whose"
            )
        approved = payload.get("approved_markets")
        if not isinstance(approved, list) or not all(
            isinstance(item, str) for item in approved
        ):
            return f"receipt `{identifier}` needs `approved_markets` as a list of keys"
        return ""

    def receipt_problem(self, entry: AllowlistEntry) -> str:
        return self.checked_receipt(entry)[1]

    def approved_by_receipt(self, entry: AllowlistEntry) -> frozenset[str]:
        """The markets the cited receipt approves; empty when it cannot stand."""
        payload, _ = self.checked_receipt(entry)
        if payload is None:
            return frozenset()
        return frozenset(item.strip() for item in payload["approved_markets"])

    def receipt_approves(self, entry: AllowlistEntry, market: str) -> bool:
        return market in self.approved_by_receipt(entry)

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
        if entry.provider_name not in self.allowed_provider_names:
            # Naming a provider in `allowed_provider_names` is Cooper's, and
            # an entry under a name he has not written there is not his.
            return False
        # The receipt must be opened and must itself approve this market.
        # The policy's market list is what someone wants; the receipt's is
        # what Cooper signed, and only their overlap is allowed.
        return self.receipt_approves(entry, key)

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
            return (
                f"The allowlist entry for `{league.policy_key()}` is not a "
                f"complete approval: it lacks {', '.join(entry.missing())}."
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
        if entry.provider_name not in self.allowed_provider_names:
            return (
                f"`{entry.provider_name}` is not in `allowed_provider_names`, "
                f"so the entry for `{league.policy_key()}` is not an approval "
                "Cooper has written down."
            )
        # One read, shared with `market_allowed`: the reason printed is about
        # the same bytes the decision was made on.
        payload, problem = self.checked_receipt(entry)
        if payload is None:
            return f"{problem[0].upper()}{problem[1:]}."
        if key not in {item.strip() for item in payload["approved_markets"]}:
            return (
                f"`{key}` is in the policy's list for `{league.policy_key()}` "
                f"but not in the `approved_markets` of receipt "
                f"`{entry.evidence_receipt_id}`. A market list widened after "
                "signing is not an approval."
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
