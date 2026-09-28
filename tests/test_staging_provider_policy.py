"""The policy allows nothing until a human says otherwise, and fails closed.

Every one of these is a way the policy could accidentally start permitting
something. A loader that returns a permissive default on an unreadable file is
a loader that stops existing the moment something goes wrong, which is exactly
when it matters.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ncaaf_betting_lab.config import STAGING_PROVIDER_POLICY_PATH
from ncaaf_betting_lab.markets import ALL_MARKETS, MARKETS_BY_KEY
from ncaaf_betting_lab.leagues import NCAAF, League
from ncaaf_betting_lab.staging_provider_policy import (
    POLICY_FILENAME,
    RECEIPTS_DIRNAME,
    StagingProviderPolicy,
    write_starter_policy,
)


NFL = League(
    key="nfl",
    title="NFL",
    provider_sport_key="americanfootball_nfl",
    data_adapter="x",
    market_registry="y",
    timezone=NCAAF.timezone,
    daily_credit_cap=1,
)


def _receipt(receipt_id: str, markets: list[str], **overrides) -> dict:
    """A receipt approving `markets` for NCAAF, complete unless overridden."""
    body = {
        "receipt_id": receipt_id,
        "policy_key": NCAAF.policy_key(),
        "reviewer_name": "cooperross399",
        "reviewer_statement": "Read the evidence bundle.",
        "reviewed_at": "2026-09-01T12:00:00-04:00",
        "approved_markets": list(markets),
        "evidence": [],
    }
    body.update(overrides)
    return body


def _write(
    tmp_path: Path,
    payload: dict,
    *,
    receipt: str | None = None,
    receipt_body: dict | str | None = None,
) -> Path:
    """Write the policy and, if named, the receipt it cites.

    By default the receipt approves exactly the markets the policy's NCAAF entry
    lists, so a test only has to say what it changes.
    """
    (tmp_path / POLICY_FILENAME).write_text(json.dumps(payload), encoding="utf-8")
    if receipt:
        receipts = tmp_path / RECEIPTS_DIRNAME
        receipts.mkdir(parents=True, exist_ok=True)
        if receipt_body is None:
            entry = (payload.get("provider_allowlist_entries") or {}).get(
                NCAAF.policy_key(), {}
            )
            receipt_body = _receipt(receipt, entry.get("required_markets", []))
        text = receipt_body if isinstance(receipt_body, str) else json.dumps(receipt_body)
        (receipts / f"{receipt}.json").write_text(text, encoding="utf-8")
    return tmp_path / POLICY_FILENAME


def _approval(markets: list[str], receipt: str = "r-1") -> dict:
    return {
        "allowed_provider_names": ["the_odds_api"],
        "provider_allowlist_entries": {
            NCAAF.policy_key(): {
                "allowlist_status": "allowed",
                "approved_at": "2026-09-01T12:00:00-04:00",
                "reviewer_name": "cooperross399",
                "evidence_receipt_id": receipt,
                "required_markets": markets,
            }
        }
    }


def test_the_shipped_policy_allowlists_nothing(tmp_path: Path) -> None:
    write_starter_policy(tmp_path / POLICY_FILENAME)

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.allowed_markets(NCAAF) == ()
    assert not policy.market_allowed(NCAAF, "moneyline")


def test_a_missing_policy_file_allows_nothing(tmp_path: Path) -> None:
    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "No policy file" in policy.refusal_reason(NCAAF, "moneyline")


def test_an_unreadable_policy_file_allows_nothing(tmp_path: Path) -> None:
    (tmp_path / POLICY_FILENAME).write_text("{not json", encoding="utf-8")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "could not be read" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_policy_file_that_is_not_an_object_allows_nothing(tmp_path: Path) -> None:
    (tmp_path / POLICY_FILENAME).write_text("[]", encoding="utf-8")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")


def test_a_complete_approval_allows_exactly_the_markets_it_names(
    tmp_path: Path,
) -> None:
    _write(tmp_path, _approval(["moneyline", "spread"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.market_allowed(NCAAF, "moneyline")
    assert policy.market_allowed(NCAAF, "spread")
    assert not policy.market_allowed(NCAAF, "total_points")
    assert "not named in the reviewed approval" in policy.refusal_reason(
        NCAAF, "total_points"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowlist_status", "pending"),
        ("reviewer_name", ""),
        ("evidence_receipt_id", ""),
    ],
)
def test_an_incomplete_approval_is_not_an_approval(
    tmp_path: Path, field: str, value: str
) -> None:
    """A status of "allowed" with no reviewer is what a half-finished edit
    looks like, and it must not read as an approval."""
    payload = _approval(["moneyline"])
    payload["provider_allowlist_entries"][NCAAF.policy_key()][field] = value
    _write(tmp_path, payload, receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "not a complete approval" in policy.refusal_reason(NCAAF, "moneyline")


def test_an_approval_naming_a_receipt_that_does_not_exist_allows_nothing(
    tmp_path: Path,
) -> None:
    """An id pointing at nothing is the shape a fabricated approval takes."""
    _write(tmp_path, _approval(["moneyline"], receipt="r-missing"))

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "no such file exists" in policy.refusal_reason(NCAAF, "moneyline")


def test_an_approval_naming_a_market_this_lab_cannot_settle_allows_nothing(
    tmp_path: Path,
) -> None:
    """The policy grants permission. It does not confer the ability to settle
    a bet, so it cannot make an unwired market usable."""
    _write(tmp_path, _approval(["moneyline", "player_wickets"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "player_wickets")
    assert "not a market this lab knows" in policy.refusal_reason(NCAAF, "player_wickets")


def test_approving_a_market_in_one_league_never_approves_it_in_another(
    tmp_path: Path,
) -> None:
    """The distribution, the roster churn and the books' coverage are all
    different. One receipt, one league."""
    _write(tmp_path, _approval(["moneyline"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.market_allowed(NCAAF, "moneyline")
    assert not policy.market_allowed(NFL, "moneyline")
    reason = policy.refusal_reason(NFL, "moneyline")
    assert "none carries across" in reason
    # ...and it names the entry that does exist, because "nothing is approved
    # anywhere" and "approved next door" are different situations and only one
    # of them is a question for Cooper.
    assert NCAAF.policy_key() in reason


def test_every_refusal_gives_a_reason_a_card_can_print(tmp_path: Path) -> None:
    """A market excluded with no stated reason is indistinguishable from one
    silently dropped."""
    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    for market in ("moneyline", "pass_yards", "not_a_market"):
        reason = policy.refusal_reason(NCAAF, market)
        assert reason and not reason.endswith(" ")


def test_a_market_that_is_allowed_has_no_refusal_reason(tmp_path: Path) -> None:
    """Otherwise a card could print an approval and a refusal for one market."""
    _write(tmp_path, _approval(["moneyline"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.refusal_reason(NCAAF, "moneyline") == ""


def test_the_repositorys_own_policy_allowlists_exactly_what_its_receipt_signed() -> None:
    """The state that ships: every allowlisted market is one the cited receipt
    approves, and every market the entry lists is allowed. If this fails, the
    policy and its receipt have drifted apart."""
    policy = StagingProviderPolicy.load()
    entry = policy.entry_for(NCAAF)
    assert entry is not None and entry.is_allowed

    allowed = set(policy.allowed_markets(NCAAF))

    assert allowed == set(entry.required_markets)
    assert allowed <= set(policy.approved_by_receipt(entry))


def test_a_policy_with_no_entries_at_all_says_so_rather_than_blaming_a_league(
    tmp_path: Path,
) -> None:
    """The state that ships. Telling a reader their approval "does not carry
    across" when there is no approval anywhere points at the wrong problem."""
    write_starter_policy(tmp_path / POLICY_FILENAME)

    reason = StagingProviderPolicy.load(manual_dir=tmp_path).refusal_reason(
        NCAAF, "moneyline"
    )

    assert "No market has a reviewed approval yet" in reason
    assert "carries across" not in reason


# -- the receipt is opened, not merely found ------------------------------


def test_a_receipt_that_merely_exists_approves_nothing(tmp_path: Path) -> None:
    """The old check was `is_file()`. A file saying "signed" passed it."""
    _write(tmp_path, _approval(["moneyline"]), receipt="r-1", receipt_body="signed")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "could not be read" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_receipt_approves_only_the_markets_it_names(tmp_path: Path) -> None:
    """A market list widened after signing is not an approval.

    The policy is what someone wants the card to read; the receipt is what
    Cooper signed. Only their overlap is allowed.
    """
    _write(
        tmp_path,
        _approval(["moneyline", "spread"]),
        receipt="r-1",
        receipt_body=_receipt("r-1", ["moneyline"]),
    )

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.market_allowed(NCAAF, "moneyline")
    assert not policy.market_allowed(NCAAF, "spread")
    assert "widened after signing" in policy.refusal_reason(NCAAF, "spread")
    assert policy.allowed_markets(NCAAF) == ("moneyline",)


def test_a_receipt_for_another_league_approves_nothing(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _approval(["moneyline"]),
        receipt="r-1",
        receipt_body=_receipt("r-1", ["moneyline"], policy_key=NFL.policy_key()),
    )

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "One receipt, one league" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_receipt_copied_under_another_name_approves_nothing(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _approval(["moneyline"]),
        receipt="r-1",
        receipt_body=_receipt("r-0", ["moneyline"]),
    )

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "names itself" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_receipt_with_no_reviewer_approves_nothing(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _approval(["moneyline"]),
        receipt="r-1",
        receipt_body=_receipt("r-1", ["moneyline"], reviewer_name="  "),
    )

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")


def test_a_receipt_whose_markets_are_not_a_list_approves_nothing(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _approval(["moneyline"]),
        receipt="r-1",
        receipt_body=_receipt("r-1", [], approved_markets="moneyline"),
    )

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")


@pytest.mark.parametrize("receipt_id", ["../r-1", "r/1", "r 1", "a" * 129])
def test_a_receipt_id_that_is_not_a_safe_filename_approves_nothing(
    tmp_path: Path, receipt_id: str
) -> None:
    """The id becomes a path. One that could climb out of the receipts
    directory is refused before anything is opened - and this test puts a
    well-formed receipt at the place the id would reach, so it fails if
    the guard is ever removed rather than passing by absence."""
    _write(tmp_path, _approval(["moneyline"], receipt=receipt_id))
    target = tmp_path / RECEIPTS_DIRNAME / f"{receipt_id}.json"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(_receipt(receipt_id, ["moneyline"])), encoding="utf-8"
        )
    except OSError:
        pass  # a name the filesystem itself refuses is refused twice over

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "not a safe filename" in policy.refusal_reason(NCAAF, "moneyline")


def test_an_empty_receipt_id_is_an_incomplete_approval(tmp_path: Path) -> None:
    _write(tmp_path, _approval(["moneyline"], receipt=""))

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "evidence receipt id" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_receipt_signed_by_someone_else_approves_nothing(tmp_path: Path) -> None:
    """The entry says who approved; the receipt has to be that person's."""
    _write(
        tmp_path,
        _approval(["moneyline"]),
        receipt="r-1",
        receipt_body=_receipt("r-1", ["moneyline"], reviewer_name="someone_else"),
    )

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "signed by 'someone_else'" in policy.refusal_reason(NCAAF, "moneyline")


def test_an_entry_under_a_provider_not_in_allowed_provider_names_approves_nothing(
    tmp_path: Path,
) -> None:
    payload = _approval(["moneyline"])
    payload["allowed_provider_names"] = []
    _write(tmp_path, payload, receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "allowed_provider_names" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_symlinked_receipt_approves_nothing(tmp_path: Path) -> None:
    """A symlink in the receipts directory reads a file from anywhere on disk
    as a receipt. It is not one."""
    _write(tmp_path, _approval(["moneyline"]))
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text(json.dumps(_receipt("r-1", ["moneyline"])), encoding="utf-8")
    receipts = tmp_path / RECEIPTS_DIRNAME
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "r-1.json").symlink_to(elsewhere)

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "not a regular file" in policy.refusal_reason(NCAAF, "moneyline")


def test_a_receipt_is_read_once_per_loaded_policy(tmp_path: Path) -> None:
    """Every row of a card run is judged against the same bytes: after the
    first decision the receipt on disk no longer matters to this policy."""
    _write(tmp_path, _approval(["moneyline", "spread"]), receipt="r-1")
    policy = StagingProviderPolicy.load(manual_dir=tmp_path)
    assert policy.market_allowed(NCAAF, "moneyline")

    (tmp_path / RECEIPTS_DIRNAME / "r-1.json").unlink()

    assert policy.market_allowed(NCAAF, "spread")
    assert policy.refusal_reason(NCAAF, "spread") == ""
    assert not StagingProviderPolicy.load(manual_dir=tmp_path).market_allowed(NCAAF, "spread")


# -- the committed policy file (from the allowlist proposal, #4) ---------


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
