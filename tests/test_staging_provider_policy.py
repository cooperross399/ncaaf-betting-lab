"""The committed policy file, and the fail-closed rules it must keep obeying.

`data/manual/staging_provider_policy.json` arrived carrying a PROPOSAL: all ten
markets named under `required_markets`, with the reviewer and receipt fields
empty so that nothing is allowlisted. Until now nothing in the suite read that
file at all — `market_allowed()` has no callers in `src/` or `scripts/`, so a
policy that quietly started allowing things would have been caught by no test
and by no gate.

Every assertion here is an INVARIANT rather than a snapshot of today's state.
That distinction is deliberate and it is the difference between a guard and a
tripwire: a test asserting "nothing is allowlisted" would go red the moment
Cooper legitimately signs a receipt, and a test that must be deleted to do the
correct next thing teaches people to delete tests. So what is pinned is the
COUPLING — a market may read as allowed only when the paperwork it claims is
genuinely there — which stays true before a signature and after one.

The fail-closed rules themselves live in
`src/ncaaf_betting_lab/staging_provider_policy.py` and are re-driven here
against synthetic trees, because a rule nobody exercises is a rule that was
true when it was written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ncaaf_betting_lab.config import STAGING_PROVIDER_POLICY_PATH
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.markets import ALL_MARKETS, MARKETS_BY_KEY
from ncaaf_betting_lab.staging_provider_policy import (
    RECEIPTS_DIRNAME,
    StagingProviderPolicy,
)


@pytest.fixture(scope="module")
def committed() -> StagingProviderPolicy:
    """The real file, loaded exactly as a caller would load it."""
    return StagingProviderPolicy.load()


# -- the committed file -------------------------------------------------


def test_the_committed_policy_file_exists_and_parses(
    committed: StagingProviderPolicy,
) -> None:
    """A policy that cannot be read allows nothing — correct, and still a bug.

    Fail-closed is the right behaviour for a malformed file and it is a bad
    thing to ship: every refusal downstream would then be explained by a typo
    rather than by the absence of evidence, and the two read identically in a
    report.
    """
    assert STAGING_PROVIDER_POLICY_PATH.is_file(), (
        f"No policy file at {STAGING_PROVIDER_POLICY_PATH}."
    )
    assert committed.load_error == "", committed.load_error


def test_every_named_market_is_one_this_lab_can_price_and_settle(
    committed: StagingProviderPolicy,
) -> None:
    """A typo in `required_markets` is invisible without this.

    `market_allowed()` returns False for a market it does not recognise, so a
    misspelling does not fail loudly — it produces a market that is named in
    the approval and can never be selected, which in a report looks exactly
    like a market no book quoted.
    """
    entry = committed.entry_for(NCAAF)
    assert entry is not None, "No entry for NCAAF in the committed policy."
    unknown = [m for m in entry.required_markets if m not in MARKETS_BY_KEY]
    assert not unknown, (
        f"Named in required_markets but absent from the registry: {unknown}. "
        f"Known: {sorted(MARKETS_BY_KEY)}."
    )


def test_every_named_market_carries_its_own_recorded_limitation(
    committed: StagingProviderPolicy,
) -> None:
    """A market may not be proposed without saying what is unknown about it.

    The per-market lines are keyed by leading token, so `moneyline` cannot
    satisfy `moneyline_h1` by being a prefix of it — which is the shape of
    mistake that would leave the half markets undocumented while the test
    stayed green.
    """
    entry = committed.entry_for(NCAAF)
    assert entry is not None
    documented = {
        line.split(" ", 1)[0] for line in entry.known_limitations if line.strip()
    }
    undocumented = [m for m in entry.required_markets if m not in documented]
    assert not undocumented, (
        f"Named in required_markets with no known_limitations line of their "
        f"own: {undocumented}. A market is proposed with its limitations or "
        f"it is not proposed."
    )


# -- the invariant, before a signature and after one --------------------


def test_no_market_reads_as_allowed_without_the_paperwork_it_claims(
    committed: StagingProviderPolicy,
) -> None:
    """The coupling, pinned. True today, and true after Cooper signs.

    A market may report allowed ONLY when the entry is a complete approval and
    the receipt it names is a real file. An id pointing at nothing is the shape
    a fabricated approval takes, which is why the loader re-checks the file on
    every call rather than trusting the id.
    """
    entry = committed.entry_for(NCAAF)
    assert entry is not None
    for market in MARKETS_BY_KEY:
        if not committed.market_allowed(NCAAF, market):
            continue
        assert entry.is_allowed, (
            f"`{market}` reads as allowed from an entry that is not a "
            f"complete approval."
        )
        receipt = committed.receipt_path(entry)
        assert receipt.is_file(), (
            f"`{market}` reads as allowed but the receipt it names is not on "
            f"disk at {receipt}."
        )


def test_an_entry_that_is_not_an_approval_allows_nothing(
    committed: StagingProviderPolicy,
) -> None:
    """While the entry is a proposal, `allowed_markets` must stay empty.

    Stated as an implication rather than as a fact about today, so signing a
    receipt turns this test green-by-vacuity instead of red.
    """
    entry = committed.entry_for(NCAAF)
    assert entry is not None
    if not entry.is_allowed:
        assert committed.allowed_markets(NCAAF) == ()
        assert "No market is allowlisted" in committed.summary_line(NCAAF)


def test_a_refusal_names_what_is_missing(committed: StagingProviderPolicy) -> None:
    """An unusable market must say why, in words a card can print.

    "Not allowed" with no reason is how an absence becomes a pass: a reader
    cannot tell a market awaiting a signature from one that was measured and
    rejected.
    """
    entry = committed.entry_for(NCAAF)
    assert entry is not None
    for market in entry.required_markets:
        if committed.market_allowed(NCAAF, market):
            continue
        assert committed.refusal_reason(NCAAF, market).strip(), (
            f"`{market}` is refused with no reason given."
        )


# -- the fail-closed rules, re-driven ------------------------------------


def _write(tmp_path: Path, entry: dict) -> StagingProviderPolicy:
    path = tmp_path / "staging_provider_policy.json"
    path.write_text(
        json.dumps({"provider_allowlist_entries": {NCAAF.policy_key(): entry}}),
        encoding="utf-8",
    )
    return StagingProviderPolicy.load(path, manual_dir=tmp_path)


COMPLETE = {
    "allowlist_status": "allowed",
    "approved_at": "2026-09-25",
    "reviewer_name": "A Reviewer",
    "evidence_receipt_id": "a-receipt",
    "required_markets": ["spread"],
}


def test_a_complete_approval_naming_an_absent_receipt_allows_nothing(
    tmp_path: Path,
) -> None:
    """Everything filled in, no file on disk. This is the important one."""
    policy = _write(tmp_path, dict(COMPLETE))
    assert policy.market_allowed(NCAAF, "spread") is False
    assert "no such file exists" in policy.refusal_reason(NCAAF, "spread")


def test_the_same_approval_with_the_receipt_present_allows_it(
    tmp_path: Path,
) -> None:
    """The other half: the rule must be a rule and not a refusal-to-ever-pass.

    Without this, every assertion above is satisfied by a loader that returns
    False unconditionally, and a gate that can never open is not evidence that
    the gate works.
    """
    policy = _write(tmp_path, dict(COMPLETE))
    receipts = tmp_path / RECEIPTS_DIRNAME
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "a-receipt.md").write_text("signed", encoding="utf-8")
    assert policy.market_allowed(NCAAF, "spread") is True
    assert policy.refusal_reason(NCAAF, "spread") == ""


@pytest.mark.parametrize(
    "field",
    ["allowlist_status", "reviewer_name", "evidence_receipt_id"],
)
def test_a_missing_field_allows_nothing_even_with_a_receipt(
    tmp_path: Path, field: str
) -> None:
    """Every condition, not any of them.

    A status of "allowed" with no reviewer is what a half-finished edit looks
    like, and it must not read as an approval — so each field is knocked out
    in turn with the receipt genuinely present, which is the arrangement that
    would otherwise pass.
    """
    entry = dict(COMPLETE)
    entry[field] = ""
    policy = _write(tmp_path, entry)
    receipts = tmp_path / RECEIPTS_DIRNAME
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "a-receipt.md").write_text("signed", encoding="utf-8")
    assert policy.market_allowed(NCAAF, "spread") is False


def test_an_empty_market_list_allows_nothing(tmp_path: Path) -> None:
    entry = dict(COMPLETE)
    entry["required_markets"] = []
    policy = _write(tmp_path, entry)
    assert policy.allowed_markets(NCAAF) == ()


def test_a_market_outside_the_registry_is_never_allowed(tmp_path: Path) -> None:
    """The policy grants permission; it does not confer the ability to settle.

    A market this lab cannot price or settle stays refused even when a policy
    file names it and the receipt is on disk.
    """
    entry = dict(COMPLETE)
    entry["required_markets"] = ["player_pass_yds"]
    policy = _write(tmp_path, entry)
    receipts = tmp_path / RECEIPTS_DIRNAME
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "a-receipt.md").write_text("signed", encoding="utf-8")
    assert policy.market_allowed(NCAAF, "player_pass_yds") is False
    assert "not a market this lab knows how to price" in policy.refusal_reason(
        NCAAF, "player_pass_yds"
    )


@pytest.mark.parametrize(
    "body", ["", "not json", "[]", '"a string"', "null"]
)
def test_an_unreadable_or_malformed_policy_allows_nothing(
    tmp_path: Path, body: str
) -> None:
    path = tmp_path / "staging_provider_policy.json"
    path.write_text(body, encoding="utf-8")
    policy = StagingProviderPolicy.load(path, manual_dir=tmp_path)
    assert policy.market_allowed(NCAAF, "spread") is False
    for market in MARKETS_BY_KEY:
        assert policy.market_allowed(NCAAF, market) is False


def test_a_missing_policy_file_allows_nothing(tmp_path: Path) -> None:
    policy = StagingProviderPolicy.load(
        tmp_path / "nope.json", manual_dir=tmp_path
    )
    assert policy.load_error
    for market in MARKETS_BY_KEY:
        assert policy.market_allowed(NCAAF, market) is False


def test_an_entry_for_another_league_does_not_carry_across(
    tmp_path: Path,
) -> None:
    """One receipt, one league. The key cannot express "allowed everywhere"."""
    path = tmp_path / "staging_provider_policy.json"
    path.write_text(
        json.dumps({"provider_allowlist_entries": {"the_odds_api:nfl": COMPLETE}}),
        encoding="utf-8",
    )
    receipts = tmp_path / RECEIPTS_DIRNAME
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "a-receipt.md").write_text("signed", encoding="utf-8")
    policy = StagingProviderPolicy.load(path, manual_dir=tmp_path)
    assert policy.entry_for(NCAAF) is None
    assert policy.market_allowed(NCAAF, "spread") is False
    assert "none carries across" in policy.refusal_reason(NCAAF, "spread")


# -- the registry itself -------------------------------------------------


def test_no_market_claims_a_retention_it_has_not_earned() -> None:
    """`retained=True` would be a guess. No probe has run for college football.

    Guarded here rather than left to review because `True` is one keystroke
    from `None` and reads as a measurement everywhere downstream.
    """
    guessed = [m.key for m in ALL_MARKETS if m.retained is True]
    assert not guessed, (
        f"retained=True without a probe: {guessed}. None means unprobed; "
        f"False would be a finding and True would be a guess."
    )
