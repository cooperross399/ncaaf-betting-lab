"""Whether a null means anything, which depends entirely on the design.

Fifty-three hypotheses across this lab and its NFL sibling, every one returning
"no demonstrated edge", and not once did either check that it could detect an
edge that existed. A harness that cannot is guaranteed to report a null whether
or not one is there, with clean intervals and careful prose.
"""

from __future__ import annotations

import pytest

from ncaaf_betting_lab.power import (
    detectable_edge,
    render,
    requirement,
)


def test_a_smaller_edge_needs_more_bets() -> None:
    assert requirement(0.01, intra_game_correlation=0.036).independent_bets > requirement(0.05, intra_game_correlation=0.036).independent_bets


def test_the_multiple_testing_correction_raises_the_requirement() -> None:
    """The cumulative ledger widens intervals by x1.69 today and grows. That
    is honest, and it also means every additional hypothesis makes the next
    one harder to demonstrate — a ratchet worth seeing in numbers."""
    plain = requirement(0.02, correction_factor=1.0, intra_game_correlation=0.036).independent_bets
    corrected = requirement(0.02, correction_factor=1.69, intra_game_correlation=0.036).independent_bets

    assert corrected > plain * 1.5


def test_clustering_inflates_the_requirement_by_the_design_effect() -> None:
    """Bets inside one game share its result. Ninety-six props on a game carry
    nowhere near ninety-six bets' worth of information."""
    independent = requirement(0.02, bets_per_game=1.0, intra_game_correlation=0.5)
    clustered = requirement(0.02, bets_per_game=96.0, intra_game_correlation=0.5)

    assert independent.design_effect == pytest.approx(1.0)
    assert clustered.design_effect > 40
    assert clustered.clustered_bets > independent.clustered_bets * 40


def test_uncorrelated_bets_carry_full_information() -> None:
    """The floor case: rho = 0 means the design effect vanishes, whatever the
    bets per game."""
    assert requirement(0.02, bets_per_game=96.0,
                       intra_game_correlation=0.0).design_effect == pytest.approx(1.0)


def test_a_detectable_edge_floor_is_reported_for_a_season() -> None:
    """The number that must sit beside every null. A college season of 760
    games cannot see a realistic edge at all."""
    floor = detectable_edge(760, correction_factor=1.69, intra_game_correlation=0.036, bets_per_game=3.0)

    assert floor > 0.05, "a season should not be able to detect a small edge"


def test_more_games_lower_the_floor() -> None:
    assert detectable_edge(
        5000, intra_game_correlation=0.036, bets_per_game=3.0
    ) < detectable_edge(500, intra_game_correlation=0.036, bets_per_game=3.0)


def test_an_edge_of_zero_or_less_is_refused() -> None:
    """Asking how many bets detect a zero edge is asking for infinity, and
    returning a number would invite someone to quote it."""
    with pytest.raises(ValueError, match="positive"):
        requirement(0.0, intra_game_correlation=0.036)
    with pytest.raises(ValueError, match="positive"):
        requirement(-0.02, intra_game_correlation=0.036)


def test_the_report_says_a_null_without_this_table_is_not_a_finding() -> None:
    text = render(correction_factor=1.69, games_per_season=760,
                  intra_game_correlation=0.036, bets_per_game=3.0)

    assert "could this lab have seen an edge" in text.lower()
    assert "not a finding" in text
    assert "the design speaking, not the market" in text


def test_the_report_refuses_to_claim_there_is_no_edge() -> None:
    """The distinction the whole module exists for: "we could not see one" is
    not "there is not one"."""
    text = render(correction_factor=1.69, games_per_season=760,
                  intra_game_correlation=0.036, bets_per_game=3.0)

    assert "does not say there is no edge" in text


def test_the_correlation_must_be_measured_and_not_defaulted() -> None:
    """The first version of this module defaulted to 0.5 on intuition, which
    made a +2% edge look like it needed 80 NFL seasons. Measured on the real
    bets it is 0.036 — a design effect of 4.8x rather than 50x, and a
    completely different conclusion about what the lab can see.

    So there is no default. A caller must pass what it measured.
    """
    with pytest.raises(TypeError):
        requirement(0.02)  # type: ignore[call-arg]


def test_the_measured_correlation_matches_a_hand_computation() -> None:
    """Two games, perfectly split: every bet in game A wins, every bet in game
    B loses. That is maximal clustering and must read near 1."""
    import pandas as pd

    from ncaaf_betting_lab.power import measured_correlation

    profit = pd.Series([1.0] * 20 + [-1.0] * 20)
    game = pd.Series(["a"] * 20 + ["b"] * 20)

    assert measured_correlation(profit, game) > 0.9


def test_uncorrelated_bets_measure_near_zero() -> None:
    import numpy as np
    import pandas as pd

    from ncaaf_betting_lab.power import measured_correlation

    rng = np.random.default_rng(0)
    profit = pd.Series(rng.choice([1.0, -1.0], 4000))
    game = pd.Series([f"g{i // 20}" for i in range(4000)])

    assert measured_correlation(profit, game) < 0.05
