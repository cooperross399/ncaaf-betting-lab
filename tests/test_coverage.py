"""The gate that stops an unrated team being priced as league average.

The NFL lab reads a rating with `.get(team, 0.0)`: an unknown team comes back
as exactly average, silently, with no error. In the NFL that is nearly
unreachable — 32 clubs, all rated, every week. In college it is the normal case
for weeks 1-3 and permanent for every FCS opponent.

Mercer is not an average FBS team. A model that says so will take the over.
"""

from __future__ import annotations

import pytest

from ncaaf_betting_lab.coverage import (
    MINIMUM_RATED_GAMES,
    UNRATED_OPPONENT,
    CoverageTally,
    check,
)

PLAYED = {"Ohio State": 8, "Michigan": 8, "Toledo": 2, "Akron": MINIMUM_RATED_GAMES}


def test_two_well_rated_teams_are_priceable() -> None:
    assert check("Ohio State", "Michigan", PLAYED).is_priceable


def test_an_unrated_opponent_is_refused_rather_than_priced_as_average() -> None:
    """The whole point. `.get(team, 0.0)` would have returned league average
    and priced the game with no error anywhere."""
    coverage = check("Ohio State", "Mercer", PLAYED)

    assert not coverage.is_priceable
    assert coverage.missing == ("Mercer",)
    assert "no rating" in coverage.reason()


def test_it_does_not_matter_which_side_is_unrated() -> None:
    assert check("Mercer", "Ohio State", PLAYED).missing == ("Mercer",)


def test_both_sides_unrated_names_both() -> None:
    coverage = check("Mercer", "Furman", PLAYED)

    assert coverage.missing == ("Mercer", "Furman")


def test_a_team_below_the_games_floor_is_refused_too() -> None:
    """A rating shrunk most of the way to the league mean is not a cautious
    estimate of a team — it asserts the team is average, which against
    forty-point talent gaps is the same failure in slower motion."""
    coverage = check("Toledo", "Michigan", PLAYED)

    assert not coverage.is_priceable
    assert coverage.thin == ("Toledo",)
    assert f"{MINIMUM_RATED_GAMES}-game floor" in coverage.reason()


def test_exactly_at_the_floor_is_priceable() -> None:
    """The threshold is declared in advance and applied as written, so a
    boundary case cannot drift by re-reading."""
    assert check("Akron", "Michigan", PLAYED).is_priceable


def test_a_missing_rating_is_reported_before_a_thin_one() -> None:
    """An FCS opponent and a Week 2 team are different problems, and the more
    serious one has to be the one the card names."""
    coverage = check("Toledo", "Mercer", PLAYED)

    assert coverage.missing == ("Mercer",)
    assert "no rating" in coverage.reason()


def test_the_tally_counts_skipped_games_rather_than_dropping_them() -> None:
    """Forty-eight skipped games on a Week 1 Saturday must be visible as a
    number. An absence is what a silent drop looks like."""
    tally = CoverageTally()
    for home, away in [("Ohio State", "Michigan"), ("Ohio State", "Mercer"),
                       ("Toledo", "Michigan")]:
        tally.record(check(home, away, PLAYED))

    assert tally.total == 3
    assert (tally.priceable, tally.missing_rating, tally.thin_rating) == (1, 1, 1)
    assert UNRATED_OPPONENT in tally.summary()


def test_the_unrated_bucket_is_not_the_no_opinion_bucket() -> None:
    """"We do not know these teams" and "we looked and had nothing to say" are
    different facts, and an accounting identity that cannot tell them apart
    hides a whole class of skipped game."""
    assert UNRATED_OPPONENT != "no_opinion"


def test_checking_nothing_is_an_absence_not_a_pass() -> None:
    """The failure the NFL lab's settlement screen shipped once: an empty
    table above a sentence that reads as a clean bill of health."""
    summary = CoverageTally().summary()

    assert "absence, not a pass" in summary
    assert "priceable" not in summary.split(".")[0]
