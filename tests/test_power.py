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
    assert requirement(0.01).independent_bets > requirement(0.05).independent_bets


def test_the_multiple_testing_correction_raises_the_requirement() -> None:
    """The cumulative ledger widens intervals by x1.69 today and grows. That
    is honest, and it also means every additional hypothesis makes the next
    one harder to demonstrate — a ratchet worth seeing in numbers."""
    plain = requirement(0.02, correction_factor=1.0).independent_bets
    corrected = requirement(0.02, correction_factor=1.69).independent_bets

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
    floor = detectable_edge(760, correction_factor=1.69, bets_per_game=3.0)

    assert floor > 0.05, "a season should not be able to detect a small edge"


def test_more_games_lower_the_floor() -> None:
    assert detectable_edge(5000) < detectable_edge(500)


def test_an_edge_of_zero_or_less_is_refused() -> None:
    """Asking how many bets detect a zero edge is asking for infinity, and
    returning a number would invite someone to quote it."""
    with pytest.raises(ValueError, match="positive"):
        requirement(0.0)
    with pytest.raises(ValueError, match="positive"):
        requirement(-0.02)


def test_the_report_says_a_null_without_this_table_is_not_a_finding() -> None:
    text = render(correction_factor=1.69, games_per_season=760)

    assert "could this lab have seen an edge" in text.lower()
    assert "not a finding" in text
    assert "the design speaking, not the market" in text


def test_the_report_refuses_to_claim_there_is_no_edge() -> None:
    """The distinction the whole module exists for: "we could not see one" is
    not "there is not one"."""
    text = render(correction_factor=1.69, games_per_season=760)

    assert "does not say there is no edge" in text
