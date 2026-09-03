"""The ratings-residual test, and the guards that keep its null honest."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ncaaf_betting_lab.ratings_residual import (
    PROFITABLE_SLOPE,
    ResidualTest,
    fit_ratings,
    regress,
    render,
)


def frame(disagree, resid, *, weeks=None):
    n = len(disagree)
    weeks = weeks if weeks is not None else list(range(n))
    return pd.DataFrame(
        {"disagree": disagree, "resid": resid, "season": [2024] * n, "week": weeks}
    )


def test_recovers_a_slope_that_is_really_there():
    """Positive control: inject signal, the regression must find it."""
    rng = np.random.default_rng(11)
    disagree = rng.normal(0, 8.0, 4000)
    resid = 0.30 * disagree + rng.normal(0, 15.0, 4000)
    test = regress(frame(disagree, resid, weeks=rng.integers(1, 15, 4000)), "control")
    assert test.slope == pytest.approx(0.30, abs=0.05)
    assert test.excludes_zero


def test_finds_nothing_when_there_is_nothing():
    """Negative control: pure noise must not manufacture a slope."""
    rng = np.random.default_rng(12)
    disagree = rng.normal(0, 8.0, 4000)
    resid = rng.normal(0, 15.0, 4000)
    test = regress(frame(disagree, resid, weeks=rng.integers(1, 15, 4000)), "null")
    assert not test.excludes_zero
    assert "no demonstrated edge" in test.reading()


def test_ratings_reproduce_a_margin_they_were_built_from():
    """A team 10 points better must rate about 10 points better."""
    history = pd.DataFrame(
        [
            {"home": "A", "away": "B", "margin": 10.0, "neutral": True},
            {"home": "B", "away": "A", "margin": -10.0, "neutral": True},
        ]
        * 30
    )
    ratings, _ = fit_ratings(history)
    assert ratings["A"] - ratings["B"] == pytest.approx(10.0, abs=0.5)


def test_home_field_is_separated_from_team_strength():
    """Equal teams playing home-and-home must show the edge as home field."""
    history = pd.DataFrame(
        [
            {"home": "A", "away": "B", "margin": 3.0, "neutral": False},
            {"home": "B", "away": "A", "margin": 3.0, "neutral": False},
        ]
        * 30
    )
    ratings, home_field = fit_ratings(history)
    assert home_field == pytest.approx(3.0, abs=0.3)
    assert ratings["A"] - ratings["B"] == pytest.approx(0.0, abs=0.3)


def test_ridge_does_not_shrink_the_home_field_term():
    """Home field IS identified, so it must not be penalised toward zero."""
    history = pd.DataFrame(
        [{"home": "A", "away": "B", "margin": 3.0, "neutral": False}] * 4
        + [{"home": "B", "away": "A", "margin": 3.0, "neutral": False}] * 4
    )
    _, home_field = fit_ratings(history)
    assert home_field > 2.5


def test_a_null_too_weak_to_matter_says_so_instead_of_claiming_nothing_is_there():
    """The guard that stops an underpowered design being read as a finding."""
    weak = ResidualTest("thin", 40, 0.01, 0.20)
    assert not weak.could_have_seen_a_profitable_slope
    assert "underpowered" in weak.reading()
    assert "no demonstrated edge" not in weak.reading()

    strong = ResidualTest("full", 3124, -0.0196, 0.0344)
    assert strong.could_have_seen_a_profitable_slope
    assert "no demonstrated edge" in strong.reading()


def test_the_profitability_threshold_is_above_what_the_measured_design_can_see():
    """The whole claim that the real null means something."""
    measured = ResidualTest("all games", 3124, -0.0196, 0.0344)
    assert measured.detectable_slope < PROFITABLE_SLOPE


def test_clustering_by_week_widens_the_interval():
    """Games in a week share their ratings, so their errors move together."""
    rng = np.random.default_rng(13)
    weeks = np.repeat(np.arange(60), 50)
    shock = rng.normal(0, 6.0, 60)[weeks]
    disagree = rng.normal(0, 8.0, len(weeks)) + shock
    resid = shock * 1.5 + rng.normal(0, 10.0, len(weeks))
    clustered = regress(frame(disagree, resid, weeks=weeks), "clustered")
    naive_x = disagree - disagree.mean()
    naive_se = np.sqrt(
        ((resid - clustered.slope * naive_x - resid.mean()) ** 2 * naive_x**2).sum()
    ) / (naive_x @ naive_x)
    assert clustered.standard_error > naive_se


def test_no_measurement_renders_as_an_absence_not_a_null():
    assert "Nothing was measured" in render([], disagreement_sd=8.0, ledger_count=78)
    assert "no demonstrated edge" not in render([], disagreement_sd=8.0, ledger_count=78)


def test_render_states_the_sample_size_beside_every_number():
    body = render(
        [ResidualTest("all games", 3124, -0.0196, 0.0344)],
        disagreement_sd=8.19,
        ledger_count=78,
    )
    assert "3,124" in body
    assert "no demonstrated edge" in body


def test_all_neutral_history_stays_solvable():
    """An empty home-field column must not make the system singular."""
    history = pd.DataFrame(
        [
            {"home": "A", "away": "B", "margin": 10.0, "neutral": True},
            {"home": "B", "away": "A", "margin": -10.0, "neutral": True},
        ]
        * 30
    )
    ratings, home_field = fit_ratings(history)
    assert home_field == pytest.approx(0.0, abs=1e-9)
    assert ratings["A"] - ratings["B"] == pytest.approx(10.0, abs=0.5)


def test_a_split_that_only_barely_clears_the_power_bar_says_so():
    """A design that detects 0.1428 against a 0.143 threshold is not a clean null."""
    barely = ResidualTest("early", 941, -0.0971, 0.0510)
    assert barely.could_have_seen_a_profitable_slope
    assert barely.power_is_marginal
    assert "only barely powered" in barely.reading()

    comfortable = ResidualTest("all games", 3124, -0.0196, 0.0344)
    assert not comfortable.power_is_marginal
    assert comfortable.reading() == "**no demonstrated edge**"


def test_power_is_computed_at_the_corrected_critical_value_not_the_nominal_one():
    """The bug this module shipped with for twenty minutes.

    Quoting intervals at 3.41 while computing power at 1.96 lets an
    underpowered design read as a clean null.
    """
    nominal = ResidualTest("all games", 3124, -0.0196, 0.0344)
    corrected = ResidualTest("all games", 3124, -0.0196, 0.0344, 1.7417)
    assert nominal.detectable_slope < PROFITABLE_SLOPE
    assert corrected.detectable_slope > PROFITABLE_SLOPE
    assert corrected.detectable_slope > nominal.detectable_slope


def test_correction_widens_the_interval():
    nominal = ResidualTest("x", 3124, -0.0196, 0.0344)
    corrected = ResidualTest("x", 3124, -0.0196, 0.0344, 1.7417)
    assert corrected.interval[1] > nominal.interval[1]
    assert corrected.interval[0] < nominal.interval[0]


def test_ruling_out_a_paying_slope_is_separate_from_excluding_zero():
    """The two claims the report must not conflate."""
    settled = ResidualTest("all games", 3124, -0.0196, 0.0344, 1.7417)
    assert not settled.excludes_zero
    assert settled.rules_out_a_profitable_slope

    unsettled = ResidualTest("late", 2183, 0.0204, 0.0423, 1.7417)
    assert not unsettled.excludes_zero
    assert not unsettled.rules_out_a_profitable_slope


def test_report_says_plainly_when_a_split_has_not_ruled_out_a_paying_slope():
    body = render(
        [
            ResidualTest("all games", 3124, -0.0196, 0.0344, 1.7417),
            ResidualTest("late season (weeks 5+)", 2183, 0.0204, 0.0423, 1.7417),
        ],
        disagreement_sd=8.19,
        ledger_count=78,
    )
    assert "Not settled everywhere" in body
    assert "late season (weeks 5+)" in body
    assert "bound, not a proof of zero" in body


def test_report_states_the_correction_it_used():
    body = render(
        [ResidualTest("all games", 3124, -0.0196, 0.0344, 1.7417)],
        disagreement_sd=8.19,
        ledger_count=78,
    )
    assert "78 hypotheses" in body
    assert "1.742" in body


def test_the_table_prints_the_detectable_slope_so_power_is_never_a_bare_flag():
    body = render(
        [ResidualTest("all games", 3124, -0.0196, 0.0344)],
        disagreement_sd=8.19,
        ledger_count=78,
    )
    assert "Detects" in body
    assert "0.096" in body
