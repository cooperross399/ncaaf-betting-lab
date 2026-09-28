"""The Provider Policy PR Gate: the approval paperwork, checked in full.

`staging_provider_policy.market_allowed` opens the receipt on every card run
and refuses a market the receipt does not approve. This module checks what
the card does not need to re-check on every run, because it only changes in
a pull request: that the receipt carries a reviewer's statement and a review
time, that it approves nothing this lab cannot price, and that the evidence
it cites is still the evidence it was signed against.

It runs as `tests/test_policy_pr_gate.py::test_the_shipped_policy_passes_the_gate`,
inside the suite that branch protection requires, so a pull request that
changes the policy or a receipt cannot merge with the paperwork incomplete.

What it cannot do is verify that a human wrote the receipt. Nothing in a file
can: the checker and the file live in the same repository, and whoever can
edit one can edit the other. Cooper's review on the pull request, enforced by
branch protection, is what carries that weight. This gate makes the record
complete and current; it does not make it authentic.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ncaaf_betting_lab.config import PROJECT_ROOT
from ncaaf_betting_lab.markets import MARKETS_BY_KEY
from ncaaf_betting_lab.staging_provider_policy import StagingProviderPolicy


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evidence_problems(
    identifier: str, evidence: Any, *, repository_root: Path
) -> list[str]:
    if not isinstance(evidence, list) or not evidence:
        return [
            f"receipt `{identifier}` cites no evidence. An approval that read "
            "nothing is a signature on a blank page"
        ]
    problems: list[str] = []
    root = repository_root.resolve()
    for item in evidence:
        if not isinstance(item, dict):
            problems.append(f"receipt `{identifier}` has an evidence item that is not an object")
            continue
        relative = str(item.get("path", "")).strip()
        checksum = str(item.get("sha256", "")).strip()
        if not relative or not SHA256_PATTERN.fullmatch(checksum):
            problems.append(
                f"receipt `{identifier}` cites evidence without both a path "
                "and a lowercase sha256"
            )
            continue
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            problems.append(
                f"receipt `{identifier}` cites `{relative}`, which is outside "
                "the repository"
            )
            continue
        if target.is_relative_to((root / "data" / "manual").resolve()):
            problems.append(
                f"receipt `{identifier}` cites `{relative}` as evidence. The "
                "policy and the receipts are what is being approved; they "
                "cannot also be the evidence for it"
            )
            continue
        if not target.is_file():
            problems.append(f"receipt `{identifier}` cites `{relative}`, which does not exist")
            continue
        if _sha256(target) != checksum:
            problems.append(
                f"receipt `{identifier}` cites `{relative}` with a checksum that "
                "no longer matches. The approval rests on evidence that has "
                "changed since it was read"
            )
    return problems


def check_policy(
    policy: StagingProviderPolicy, *, repository_root: Path | None = None
) -> list[str]:
    """Every problem with the policy's approvals, or an empty list.

    Only entries that claim to be approvals are checked. A `proposed` entry
    allows nothing, so it needs no receipt; the moment its status says
    `allowed`, it needs all of it - a half-finished edit that says `allowed`
    with no reviewer is exactly what must not merge with a green gate.
    """
    root = (repository_root or PROJECT_ROOT).resolve()
    if policy.load_error:
        return [policy.load_error]
    problems: list[str] = []
    for key, entry in sorted(policy.entries.items()):
        if entry.status != "allowed":
            continue
        if not entry.is_allowed:
            problems.append(
                f"`{key}` says `allowed` but lacks {', '.join(entry.missing())}"
            )
            continue
        if entry.provider_name not in policy.allowed_provider_names:
            problems.append(
                f"`{key}` is under `{entry.provider_name}`, which is not in "
                "`allowed_provider_names`. Naming a provider there is Cooper's"
            )
        unknown = sorted(set(entry.required_markets) - set(MARKETS_BY_KEY))
        if unknown:
            problems.append(f"`{key}` lists markets this lab cannot price: {unknown}")
        payload, problem = policy.checked_receipt(entry)
        if payload is None:
            problems.append(f"`{key}`: {problem}")
            continue
        identifier = entry.evidence_receipt_id
        approved = {item.strip() for item in payload["approved_markets"]}
        uncovered = sorted(set(entry.required_markets) - approved)
        if uncovered:
            problems.append(
                f"`{key}` lists {uncovered} but receipt `{identifier}` does not "
                "approve them. A receipt for one market does not approve another"
            )
        beyond = sorted(approved - set(MARKETS_BY_KEY))
        if beyond:
            problems.append(f"receipt `{identifier}` approves unknown markets {beyond}")
        if not str(payload.get("reviewer_statement", "")).strip():
            problems.append(
                f"receipt `{identifier}` carries no reviewer statement. An "
                "approval with nothing said about the evidence is a signature "
                "on a blank page"
            )
        reviewed_at = str(payload.get("reviewed_at", "")).strip()
        try:
            stamp = datetime.fromisoformat(reviewed_at)
        except ValueError:
            stamp = None
        if stamp is None or stamp.tzinfo is None:
            problems.append(
                f"receipt `{identifier}` needs `reviewed_at` as a timezone-aware "
                "ISO timestamp"
            )
        problems.extend(
            _evidence_problems(identifier, payload.get("evidence"), repository_root=root)
        )
    return problems
