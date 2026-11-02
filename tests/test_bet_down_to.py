"""Every pick carries a "bet down to" price (Cooper, 2026-11-01).

"Lets always include a 'bet down to' number." The card lists each selection's
price AND the worst price at which it would still be a selection, so a line
that moves before Cooper bets can be judged against the card's own bar
rather than guessed at.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ncaaf_betting_lab.config import CARD_EDGE_FLOOR, MAX_DEFAULT_JUICE
from ncaaf_betting_lab.forward_evidence import american_to_implied
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from ncaaf_betting_lab.reports.card_pricing import PricingDiagnostics
from ncaaf_betting_lab.reports.gameday_card import (
    CardResult,
    bet_down_to,
    render,
)


def _clears(probability: float, odds: int) -> bool:
    return probability - american_to_implied(odds) > CARD_EDGE_FLOOR


@pytest.mark.parametrize(
    "probability", [0.20, 0.33, 0.45, 0.50, 0.555, 0.56, 0.5601, 0.60, 0.62, 0.66, 0.70]
)
def test_the_bet_down_to_price_is_the_worst_price_that_still_clears(
    probability: float,
) -> None:
    odds = bet_down_to(probability)
    assert odds is not None
    if odds == MAX_DEFAULT_JUICE:
        # Floored: the card refuses anything worse whatever the edge.
        assert _clears(probability, odds)
        return
    assert _clears(probability, odds)
    # One cent worse no longer clears. -101 worse is -102; +100 worse is -101.
    worse = odds - 1 if odds > 100 or odds < -100 else -101
    assert not _clears(probability, worse)


def test_the_bet_down_to_price_never_passes_the_juice_bar() -> None:
    assert bet_down_to(0.90) == MAX_DEFAULT_JUICE


def test_no_price_clears_when_the_model_sits_under_the_bar() -> None:
    assert bet_down_to(CARD_EDGE_FLOOR) is None
    assert bet_down_to(0.01) is None


def test_the_card_prints_each_selection_with_its_bet_down_to() -> None:
    probability, odds = 0.62, -110
    pick = {
        "game": "Georgia @ Alabama",
        "market": "spreads",
        "selection": "Alabama",
        "line": -3.5,
        "odds": odds,
        "book": "draftkings",
        "model_probability": probability,
        "edge": probability - american_to_implied(odds),
        "bet_down_to": bet_down_to(probability),
    }
    # Never better than the price the pick is listed at.
    assert american_to_implied(pick["bet_down_to"]) >= american_to_implied(odds)
    card = CardResult(
        league=league_for(DEFAULT_LEAGUE_KEY),
        generated_at=datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc).isoformat(),
        slate_date="2026-10-03",
        games=[pick["game"]],
        market_states={"spreads": "eligible"},
        diagnostics=PricingDiagnostics(),
        selections=[pick],
    )
    text = render(card)
    assert "| Bet down to |" in text
    assert f"| {pick['bet_down_to']:+d} |" in text
