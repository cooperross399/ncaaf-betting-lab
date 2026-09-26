"""The Provider Policy PR Gate: an approval's paperwork, checked in full.

`test_the_shipped_policy_passes_the_gate` is the gate. It runs inside the
suite branch protection requires, so a pull request that changes the policy
file or a receipt cannot merge with the paperwork incomplete. The rest prove
that each check fires.

This is a registered guard (`tests/test_the_guards_exist.py`): deleting,
renaming or deselecting it is a red build, not a smaller green one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.reports.policy_pr_gate import check_policy
from ncaaf_betting_lab.staging_provider_policy import (
    POLICY_FILENAME,
    RECEIPTS_DIRNAME,
    StagingProviderPolicy,
)


EVIDENCE = "data/outputs/ncaaf_allowlist_evidence.md"


def _checkout(tmp_path: Path, **receipt_overrides) -> tuple[StagingProviderPolicy, Path]:
    """A checkout holding one complete NCAAF approval of `moneyline`.

    Every test starts from paperwork that passes and breaks one thing, so a
    failure names the check that fired rather than the first of several.
    """
    root = tmp_path / "repo"
    manual = root / "data" / "manual"
    evidence = root / EVIDENCE
    evidence.parent.mkdir(parents=True)
    evidence.write_text("the bundle Cooper read\n", encoding="utf-8")
    (manual / RECEIPTS_DIRNAME).mkdir(parents=True)
    (manual / POLICY_FILENAME).write_text(
        json.dumps(
            {
                "allowed_provider_names": ["the_odds_api"],
                "provider_allowlist_entries": {
                    NCAAF.policy_key(): {
                        "allowlist_status": "allowed",
                        "approved_at": "2026-09-01T12:00:00-04:00",
                        "reviewer_name": "cooperross399",
                        "evidence_receipt_id": "r-1",
                        "required_markets": ["moneyline"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    receipt = {
        "receipt_id": "r-1",
        "policy_key": NCAAF.policy_key(),
        "reviewer_name": "cooperross399",
        "reviewer_statement": "Read the evidence bundle.",
        "reviewed_at": "2026-09-01T12:00:00-04:00",
        "approved_markets": ["moneyline"],
        "evidence": [
            {
                "path": EVIDENCE,
                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
            }
        ],
    }
    receipt.update(receipt_overrides)
    (manual / RECEIPTS_DIRNAME / "r-1.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    return StagingProviderPolicy.load(manual_dir=manual), root


def test_the_shipped_policy_passes_the_gate() -> None:
    """THE GATE. Reads the repository's own policy, receipts and evidence."""
    assert check_policy(StagingProviderPolicy.load()) == []


def test_complete_paperwork_passes(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path)

    assert check_policy(policy, repository_root=root) == []


def test_a_proposed_entry_needs_no_receipt(tmp_path: Path) -> None:
    """A proposal allows nothing, so it has nothing to prove yet."""
    policy, root = _checkout(tmp_path)
    (root / "data" / "manual" / RECEIPTS_DIRNAME / "r-1.json").unlink()
    entry = policy.entries[NCAAF.policy_key()]
    policy.entries[NCAAF.policy_key()] = type(entry)(
        **{**entry.__dict__, "status": "proposed", "evidence_receipt_id": ""}
    )

    assert check_policy(policy, repository_root=root) == []


def test_a_missing_receipt_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path)
    (root / "data" / "manual" / RECEIPTS_DIRNAME / "r-1.json").unlink()

    (problem,) = check_policy(policy, repository_root=root)
    assert "no such file" in problem


def test_a_policy_listing_more_than_the_receipt_approves_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path, approved_markets=[])

    problems = check_policy(policy, repository_root=root)

    assert any("does not approve" in p for p in problems), problems


def test_a_receipt_for_another_league_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path, policy_key="the_odds_api:nfl")

    (problem,) = check_policy(policy, repository_root=root)
    assert "One receipt, one league" in problem


def test_a_receipt_with_no_statement_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path, reviewer_statement="   ")

    (problem,) = check_policy(policy, repository_root=root)
    assert "no reviewer statement" in problem


@pytest.mark.parametrize("stamp", ["", "yesterday", "2026-09-01T12:00:00"])
def test_a_receipt_without_a_timezone_aware_review_time_fails(
    tmp_path: Path, stamp: str
) -> None:
    policy, root = _checkout(tmp_path, reviewed_at=stamp)

    (problem,) = check_policy(policy, repository_root=root)
    assert "reviewed_at" in problem


def test_a_receipt_citing_no_evidence_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path, evidence=[])

    (problem,) = check_policy(policy, repository_root=root)
    assert "cites no evidence" in problem


def test_evidence_that_changed_after_signing_fails(tmp_path: Path) -> None:
    """The receipt was signed against one bundle; the file now says another."""
    policy, root = _checkout(tmp_path)
    (root / EVIDENCE).write_text("a different bundle\n", encoding="utf-8")

    (problem,) = check_policy(policy, repository_root=root)
    assert "no longer matches" in problem


def test_evidence_outside_the_repository_fails(tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere.md"
    outside.write_text("x", encoding="utf-8")
    policy, root = _checkout(
        tmp_path,
        evidence=[
            {
                "path": "../elsewhere.md",
                "sha256": hashlib.sha256(b"x").hexdigest(),
            }
        ],
    )

    (problem,) = check_policy(policy, repository_root=root)
    assert "outside the repository" in problem


def test_evidence_that_does_not_exist_fails(tmp_path: Path) -> None:
    policy, root = _checkout(
        tmp_path, evidence=[{"path": "data/outputs/gone.md", "sha256": "0" * 64}]
    )

    (problem,) = check_policy(policy, repository_root=root)
    assert "does not exist" in problem


def test_a_malformed_checksum_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path, evidence=[{"path": EVIDENCE, "sha256": "abc"}])

    (problem,) = check_policy(policy, repository_root=root)
    assert "lowercase sha256" in problem


def test_an_unreadable_policy_fails_the_gate(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / POLICY_FILENAME).write_text("{", encoding="utf-8")

    (problem,) = check_policy(
        StagingProviderPolicy.load(manual_dir=manual), repository_root=tmp_path
    )
    assert "could not be read" in problem


def test_an_entry_that_says_allowed_but_is_incomplete_fails(tmp_path: Path) -> None:
    """The half-finished edit: `allowed` with no reviewer must not merge green."""
    policy, root = _checkout(tmp_path)
    entry = policy.entries[NCAAF.policy_key()]
    policy.entries[NCAAF.policy_key()] = type(entry)(
        **{**entry.__dict__, "reviewer_name": "", "evidence_receipt_id": ""}
    )

    (problem,) = check_policy(policy, repository_root=root)
    assert "says `allowed` but lacks" in problem
    assert "a reviewer name" in problem and "an evidence receipt id" in problem


def test_a_provider_not_in_allowed_provider_names_fails(tmp_path: Path) -> None:
    policy, root = _checkout(tmp_path)
    policy.allowed_provider_names = ()

    problems = check_policy(policy, repository_root=root)
    assert any("not in `allowed_provider_names`" in p for p in problems), problems


def test_a_receipt_signed_by_someone_other_than_the_entry_names_fails(
    tmp_path: Path,
) -> None:
    policy, root = _checkout(tmp_path, reviewer_name="someone_else")

    (problem,) = check_policy(policy, repository_root=root)
    assert "signed by 'someone_else'" in problem


def test_the_policy_or_a_receipt_cannot_be_its_own_evidence(tmp_path: Path) -> None:
    first, root = _checkout(tmp_path)
    own = root / "data" / "manual" / POLICY_FILENAME
    policy, root = _checkout(
        tmp_path / "again",
        evidence=[
            {
                "path": "data/manual/" + POLICY_FILENAME,
                "sha256": hashlib.sha256(own.read_bytes()).hexdigest(),
            }
        ],
    )

    (problem,) = check_policy(policy, repository_root=root)
    assert "cannot also be the evidence" in problem
