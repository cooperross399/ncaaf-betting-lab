"""Does the harness find an edge that is really there?

Fifty-three nulls and no evidence the instrument could detect a positive. The
arithmetic in `power.py` answers that on assumptions; this answers it on the
real prices and the real game structure, which is the stronger test — the
arithmetic assumes the estimator is unbiased and its interval honest, and both
of those were false when this lab's sibling shipped an interval sqrt(games) too
narrow.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ncaaf_betting_lab.positive_control import (
    ControlReport,
    ControlResult,
    decimal_odds,
    erf,
    render,
    run,
)


def _bets(games: int = 200, per_game: int = 20) -> pd.DataFrame:
    return pd.DataFrame({
        "american_odds": [-110] * (games * per_game),
        "game_id": [f"g{i // per_game}" for i in range(games * per_game)],
    })


def test_decimal_odds_reads_both_sides_of_the_convention() -> None:
    got = decimal_odds(np.array([-110.0, 100.0, 150.0]))

    assert got[0] == pytest.approx(1 + 100 / 110)
    assert got[1] == pytest.approx(2.0)
    assert got[2] == pytest.approx(2.5)


def test_the_error_function_maps_a_normal_draw_to_a_uniform_one() -> None:
    """Used to give bets in one game a shared shock WITHOUT disturbing each
    bet's marginal win probability — otherwise the clustering would quietly
    change the edge being injected."""
    assert erf(np.array([0.0]))[0] == pytest.approx(0.0, abs=1e-6)
    assert erf(np.array([10.0]))[0] == pytest.approx(1.0, abs=1e-6)
    assert erf(np.array([-10.0]))[0] == pytest.approx(-1.0, abs=1e-6)


def test_an_injected_edge_is_recovered_without_bias() -> None:
    """A biased estimator is worse than a blind one: it is confidently wrong
    in a consistent direction."""
    report = run(_bets(), edges=(0.05,), trials=40, seed=3)

    assert report.results[0].mean_measured == pytest.approx(0.05, abs=0.01)
    assert abs(report.results[0].bias) < 0.01


def test_a_large_edge_is_detected_almost_always() -> None:
    report = run(_bets(), edges=(0.20,), trials=40, seed=3)

    assert report.results[0].detection_rate >= 0.9


def test_the_null_is_not_detected_much_more_than_alpha() -> None:
    """An interval that fires on nothing is how a lab manufactures findings."""
    report = run(_bets(), edges=(0.0,), trials=120, seed=5)

    assert report.results[0].detection_rate <= 0.12


def test_clustering_costs_power() -> None:
    """Bets in one game share a game script. Drawing them independently makes
    the control easier than reality — the first run of this instrument did
    exactly that and reported 98% power at +2%, which was true of a dataset
    nobody has."""
    independent = run(_bets(), edges=(0.02,), trials=60,
                      intra_game_correlation=0.0, seed=9)
    clustered = run(_bets(), edges=(0.02,), trials=60,
                    intra_game_correlation=0.30, seed=9)

    assert (clustered.results[0].detection_rate
            < independent.results[0].detection_rate)


def test_clustering_does_not_disturb_the_injected_edge() -> None:
    """The shared shock changes the correlation, never the marginal."""
    clustered = run(_bets(), edges=(0.05,), trials=60,
                    intra_game_correlation=0.30, seed=9)

    assert clustered.results[0].mean_measured == pytest.approx(0.05, abs=0.015)


def test_an_over_corrected_interval_is_called_out_rather_than_praised() -> None:
    """0% false positives is not a careful interval, it is one that has given
    up power — the ratchet a forever-growing correction produces."""
    report = ControlReport(bets=1000, games=100, results=[
        ControlResult(injected=0.0, trials=100, detected=0,
                      mean_measured=0.0, correction_factor=1.69),
        ControlResult(injected=0.10, trials=100, detected=100,
                      mean_measured=0.10, correction_factor=1.69),
    ])

    text = render(report)

    assert "far too rarely" in text
    assert "over-corrected" in text
    assert "ratchet" in text


def test_a_null_is_reported_as_bounded_rather_than_absolute() -> None:
    """"No edge above the detectable floor" and "no edge" are different
    claims, and only one of them is supported."""
    report = ControlReport(bets=1000, games=100, results=[
        ControlResult(injected=0.0, trials=100, detected=4,
                      mean_measured=0.0, correction_factor=1.0),
        ControlResult(injected=0.02, trials=100, detected=20,
                      mean_measured=0.02, correction_factor=1.0),
        ControlResult(injected=0.10, trials=100, detected=100,
                      mean_measured=0.10, correction_factor=1.0),
    ])

    text = render(report)

    assert "a realistic edge would be missed" in text.lower()
    assert "never as 'no edge'" in text


def test_injecting_nothing_is_an_absence_not_a_pass() -> None:
    text = render(ControlReport())

    assert "absence, not a pass" in text
    assert "remains unvalidated" in text
