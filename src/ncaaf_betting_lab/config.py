"""Paths and the betting-discipline constants.

League-specific facts do **not** live here — they live in `leagues.py`. This
file holds only what is true for the repository as a whole, which is why it
carries no sport key, no market list, and no season calendar.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANUAL_DIR = DATA_DIR / "manual"
STAGING_DIR = DATA_DIR / "staging"
OUTPUTS_DIR = DATA_DIR / "outputs"
ARCHIVE_DIR = DATA_DIR / "archive"

STAGING_PROVIDER_POLICY_PATH = MANUAL_DIR / "staging_provider_policy.json"

# Betting discipline, carried over from the NHL lab and confirmed for this one.

#: Cooper does not lay heavy juice. A price worse than this needs an explicit
#: human decision; the card will not select one on its own.
MAX_DEFAULT_JUICE = -160

#: Longest price the models are trusted to judge. Compound yardage tails and
#: touchdown-scorer longshots overstate rare outcomes, and the market's
#: favourite-longshot bias prices them short on top of that, so the two errors
#: compound in the same direction.
MAX_DEFAULT_PRICE = 600

#: Minimum modelled edge for a team-market selection.
MIN_EDGE = 0.035

#: Minimum modelled edge for a player prop. Higher than the team bar on
#: purpose, and for a sharper reason than in hockey: the card is built before
#: inactives (ninety minutes to kickoff), before any confirmation of a
#: quarterback change, and before the roof state of five retractable venues is
#: known. Books reprice on all three. A prop edge must clear a higher bar,
#: never a lower one.
MIN_PROP_EDGE = 0.06

BANKROLL_UNIT_DOLLARS = 25.0
