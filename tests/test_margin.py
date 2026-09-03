"""Margin probabilities that keep the key numbers, unlike the NFL lab's.

That model convolved two tilted team-score distributions. Measured on its own
2,895 games it put **6.19%** on |margin| = 3 against a realised **14.65%** — a
factor of 2.37 — while its own documentation said the lumps at 3 and 7 survived
and quoted the model's own push rate as if it were a fact about football.

The lumps live on the margin DIAGONALS of the joint, not in a linear
correlation, and a convolution annihilates them. So this model never takes the
margin apart: it tilts an empirical margin distribution directly.
"""

from __future__ import annotations

import numpy as np
import pytest

from ncaaf_betting_lab.models.margin import (
    MAX_TILT_POINTS,
    TOTAL_BUCKETS,
    bucket_for,
    build,
    empirical_margin_pmf,
    tilt_to_mean,
)


def _lumpy() -> dict[int, float]:
    """A margin shape with college-sized lumps at 3 and 7."""
    counts = {}
    for m in range(-40, 41):
        counts[m] = 2
    for m in (3, -3):
        counts[m] = 20
    for m in (7, -7):
        counts[m] = 16
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


def _shapes() -> dict:
    return {bucket: _lumpy() for bucket in TOTAL_BUCKETS}


def test_the_tilt_moves_the_mean_and_keeps_the_lumps() -> None:
    """The whole point. A convolution moves the mean and destroys them."""
    original = _lumpy()
    tilted = tilt_to_mean(original, 7.0)

    xs = np.array(sorted(tilted))
    w = np.array([tilted[int(x)] for x in xs])
    assert float((xs * w).sum()) == pytest.approx(7.0, abs=0.01)
    # 3 and 7 still tower over their neighbours.
    assert tilted[3] > tilted[2] * 4
    assert tilted[7] > tilted[8] * 4


def test_key_number_mass_survives_the_tilt() -> None:
    """Measured on real college data the tilt returns 10.0-10.6% on |m|=3
    against a realised 10.02%. The NFL lab's convolution returned 6.19%
    against a realised 14.65%."""
    model = build(_shapes(), implied_margin=3.0, total=52.0)

    assert model.probability_key_number(3) > model.probability_key_number(4) * 3


def test_a_whole_number_line_pushes_and_a_half_point_does_not() -> None:
    model = build(_shapes(), implied_margin=0.0, total=52.0)

    assert model.probability_cover(-3.0, side="home")[1] > 0
    assert model.probability_cover(-3.5, side="home")[1] == 0


def test_both_sides_and_the_push_account_for_everything() -> None:
    """If they do not, mass is double-counted or dropped — and the NFL lab
    shipped both sides winning the same game once, at +21.6% over 1,695 bets."""
    model = build(_shapes(), implied_margin=2.5, total=52.0)
    home, push = model.probability_cover(-3.0, side="home")
    away, away_push = model.probability_cover(3.0, side="away")

    assert push == pytest.approx(away_push)
    assert home + away + push == pytest.approx(1.0, abs=1e-9)


def test_dispersion_is_conditioned_on_the_total() -> None:
    """Measured college margin sd runs 16.1 at totals under 45 and 22.7 above
    55. One pooled shape would price a 70-point game with a 40-point game's
    dispersion."""
    narrow = {b: _lumpy() for b in TOTAL_BUCKETS}
    wide = dict(narrow)
    wide[(65.0, 1000.0)] = {m: p for m, p in
                            empirical_margin_pmf(list(range(-60, 61))).items()}

    low = build(narrow, implied_margin=0.0, total=40.0)
    high = build(wide, implied_margin=0.0, total=70.0)

    def sd(model):
        xs = np.array(sorted(model.pmf))
        w = np.array([model.pmf[int(x)] for x in xs])
        mu = (xs * w).sum()
        return float(np.sqrt(((xs - mu) ** 2 * w).sum()))

    assert sd(high) > sd(low)


def test_a_bucket_with_no_shape_refuses_rather_than_borrowing_one() -> None:
    """A shape borrowed from another bucket prices the game with the wrong
    dispersion, silently."""
    with pytest.raises(KeyError, match="wrong dispersion"):
        build({TOTAL_BUCKETS[0]: _lumpy()}, implied_margin=0.0, total=70.0)


def test_an_extreme_implied_margin_is_refused() -> None:
    """Tilting an empirical shape 40 points is extrapolation wearing a
    measurement's clothes. No opinion is the honest answer."""
    with pytest.raises(ValueError, match="No opinion"):
        build(_shapes(), implied_margin=MAX_TILT_POINTS + 1, total=52.0)


def test_a_target_outside_the_support_is_refused() -> None:
    with pytest.raises(ValueError, match="outside the support"):
        tilt_to_mean({0: 0.5, 1: 0.5}, 5.0)


def test_bucket_boundaries_are_closed_below_and_open_above() -> None:
    assert bucket_for(44.9) == (0.0, 45.0)
    assert bucket_for(45.0) == (45.0, 55.0)
    assert bucket_for(999.0) == TOTAL_BUCKETS[-1]


def test_an_empty_history_yields_no_shape_rather_than_a_flat_one() -> None:
    """A flat margin distribution is a confident claim that every scoreline is
    equally likely, which is the opposite of no information."""
    assert empirical_margin_pmf([]) == {}
