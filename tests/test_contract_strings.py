"""Strings Cooper's automation hard-codes. Renaming one breaks it silently.

A renamed workflow, branch or secret does not raise. The scheduled run simply
stops arriving, and the breakage looks exactly like the lab going quiet — which
is the one failure mode a lab whose whole product is evidence cannot afford,
because the evidence it stops gathering cannot be gathered later.

**These are deliberately NOT the NFL lab's strings.** That repository owns
`Football Gameday Refresh`, `FOOTBALL_ODDS_API_KEY` and its own operating-home
issue. Two labs sharing a workflow name or a secret would have each one's runs
appearing under the other's history, and a card-feed branch shared between them
would have one league's frozen opinions overwriting the other's ledger.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"

WORKFLOW_NAME = "NCAAF Gameday Refresh"
WORKFLOW_FILE = ".github/workflows/ncaaf-gameday-refresh.yml"
CARD_FEED_BRANCH = "card-feed"
OPERATING_HOME_ISSUE = "NCAAF Betting Lab — Claude Operating Home"
CHANGED_SELECTIONS_MARKER = "Selections changed"
ODDS_API_SECRET = "NCAAF_ODDS_API_KEY"

CONTRACT_STRINGS = (
    WORKFLOW_NAME,
    WORKFLOW_FILE,
    CARD_FEED_BRANCH,
    OPERATING_HOME_ISSUE,
    CHANGED_SELECTIONS_MARKER,
    ODDS_API_SECRET,
)


def test_every_contract_string_is_recorded_in_claude_md() -> None:
    """The table in CLAUDE.md is what a future session reads before renaming
    anything. A string that is load-bearing and undocumented is one that gets
    renamed by someone tidying up."""
    if not CLAUDE_MD.is_file():
        pytest.skip("CLAUDE.md not written yet")
    text = CLAUDE_MD.read_text(encoding="utf-8")
    missing = [s for s in CONTRACT_STRINGS if s not in text]
    assert not missing, (
        "Load-bearing strings absent from CLAUDE.md's contract table:\n  "
        + "\n  ".join(missing)
    )


def test_the_operating_home_title_uses_an_em_dash() -> None:
    """Matched literally by the workflow's `gh issue list --jq`. A hyphen
    posts nowhere, and posting nowhere is how a degraded run goes unseen."""
    assert "—" in OPERATING_HOME_ISSUE
    assert " - " not in OPERATING_HOME_ISSUE


def test_the_secret_is_not_the_nfl_lab_s_secret() -> None:
    """Two labs on one credential cannot be told apart in the provider's usage
    accounting, and a quota exhausted by one silently starves the other's
    fetch — which reads in the reports as a market nobody quoted."""
    assert ODDS_API_SECRET != "FOOTBALL_ODDS_API_KEY"
    assert "NCAAF" in ODDS_API_SECRET


def test_the_workflow_name_is_not_the_nfl_lab_s() -> None:
    assert WORKFLOW_NAME != "Football Gameday Refresh"
    assert "NCAAF" in WORKFLOW_NAME


def test_no_secret_value_is_ever_written_beside_its_name() -> None:
    """The name is a contract string and must appear in the repo. The VALUE
    must never. This asserts the distinction is live rather than assumed."""
    for path in PROJECT_ROOT.rglob("*.py"):
        if ".venv" in path.parts or path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if ODDS_API_SECRET in line:
                assert "=" not in line.split(ODDS_API_SECRET)[-1][:3], (
                    f"{path.name}: a value appears to be assigned beside the "
                    "secret's name"
                )
