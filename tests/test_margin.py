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
    bucket_for,
    MAX_TILT_POINTS,
    SPREAD_BUCKETS,
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
    return {bucket: _lumpy() for bucket in SPREAD_BUCKETS}


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


def test_the_shape_is_conditioned_on_the_SPREAD_not_the_total() -> None:
    """The error this file shipped for a day.

    Conditioning on the total left the shape carrying UNCONDITIONAL dispersion
    of ~20.5, when the dispersion given a known spread is 15.29. Ninety-two per
    cent of that version's apparent win over a normal was the benchmark being
    wrong the same way.
    """
    shapes = {b: _lumpy() for b in SPREAD_BUCKETS}

    # Two fixtures with the same total and very different spreads must draw
    # from different buckets; the total must not enter the choice at all.
    assert bucket_for(-3.5) != bucket_for(-21.0)
    near = build(shapes, implied_margin=3.5, total=52.0)
    far = build(shapes, implied_margin=3.5, total=70.0)
    assert near.pmf == far.pmf


def test_a_bucket_with_no_shape_refuses_rather_than_borrowing_one() -> None:
    """A borrowed shape prices at the wrong dispersion AND puts its key-number
    mass in the wrong place — the two failures this file exists to avoid."""
    with pytest.raises(KeyError, match="wrong dispersion"):
        build({SPREAD_BUCKETS[0]: _lumpy()}, implied_margin=10.0, total=52.0)


def test_an_extreme_implied_margin_is_refused() -> None:
    """Tilting an empirical shape 40 points is extrapolation wearing a
    measurement's clothes. No opinion is the honest answer."""
    with pytest.raises(ValueError, match="No opinion"):
        build(_shapes(), implied_margin=MAX_TILT_POINTS + 1, total=52.0)


def test_a_target_outside_the_support_is_refused() -> None:
    with pytest.raises(ValueError, match="outside the support"):
        tilt_to_mean({0: 0.5, 1: 0.5}, 5.0)


def test_bucket_boundaries_are_closed_below_and_open_above() -> None:
    assert bucket_for(2.9) == (0.0, 3.0)
    assert bucket_for(3.0) == (3.0, 7.0)
    assert bucket_for(999.0) == SPREAD_BUCKETS[-1]
    assert bucket_for(-999.0) == SPREAD_BUCKETS[0]


def test_an_empty_history_yields_no_shape_rather_than_a_flat_one() -> None:
    """A flat margin distribution is a confident claim that every scoreline is
    equally likely, which is the opposite of no information."""
    assert empirical_margin_pmf([]) == {}
