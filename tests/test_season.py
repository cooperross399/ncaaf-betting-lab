"""The league game date, and the text rule that keeps a key from matching "nan".

`season.py` was ported into this repository so `selection_key()` could be
imported at all, and a port with no test of its own is a port nobody has
checked. These are the two rules it carries, and each one is a bug the NHL lab
paid for:

* **the league date, not the UTC one.** Joining on the raw UTC date discarded
  69% of every price that lab bought, and the survivors were the afternoon
  games — a biased sample that looked like a small one;
* **NaN is not text.** `str(x or "")` on an empty CSV cell yields the literal
  string `"nan"`, because float NaN is truthy. That was the fifth member of
  that lab's join-vocabulary bug family.

The last test here is the one that says why the module exists: it drives both
rules through `selection_key()` and shows two fixtures between the same clubs
on different days keeping two keys.

The timezone comes from the registry on every assertion. Writing
`America/New_York` here would be a league fact outside `leagues.py`, and it
would also make these tests pass for the wrong reason the day the registry
changed.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from ncaaf_betting_lab.season import clean_text, game_date, row_game_date
from ncaaf_betting_lab.selection import HOME, selection_key

LEAGUE = league_for(DEFAULT_LEAGUE_KEY)


@dataclass
class Row:
    """A staged price row, in the provider's field names and not cfbfastR's."""

    commence_time: object = ""
    date: object = ""
    home_team: str = ""
    away_team: str = ""
    player: object = ""


# ---------------------------------------------------------------------------
# game_date
# ---------------------------------------------------------------------------


def test_a_late_kickoff_belongs_to_the_day_it_was_played() -> None:
    """The whole point of the module, in one assertion.

    A 22:30 Eastern kickoff on the Friday is 02:30 UTC on the Saturday. The
    game was played on the Friday, and a join on the UTC date files it under a
    day the league never played it.
    """
    assert game_date("2026-09-12T02:30:00Z", LEAGUE) == "2026-09-11"


def test_the_zone_is_applied_and_not_a_fixed_offset() -> None:
    """Two kickoffs at the same UTC clock time, either side of the DST change.

    2026-11-01 is a Sunday, so a 03:30 UTC kickoff in September is read at
    UTC-4 and one in November at UTC-5. Both land on the previous day here,
    which is the answer either offset would give — so the test that matters is
    that the module asks the registry's `ZoneInfo` rather than subtracting a
    constant, and an hour that differs between the two is what shows it.
    """
    september = "2026-09-12T03:30:00Z"
    november = "2026-11-08T03:30:00Z"
    assert game_date(september, LEAGUE) == "2026-09-11"
    assert game_date(november, LEAGUE) == "2026-11-07"
    # The same wall clock in the league's own zone is a different UTC hour
    # across the boundary. A fixed -4 would put the November game at 23:30 on
    # the 7th and a fixed -5 would put the September one at 22:30 on the 11th;
    # only a real zone gives both.
    assert game_date("2026-11-08T04:30:00Z", LEAGUE) == "2026-11-07"
    assert game_date("2026-09-12T04:30:00Z", LEAGUE) == "2026-09-12"


@pytest.mark.parametrize("text", ["2026-09-12T02:30:00Z", "2026-09-12T02:30:00+00:00"])
def test_the_z_suffix_and_the_offset_are_the_same_timestamp(text: str) -> None:
    assert game_date(text, LEAGUE) == "2026-09-11"


def test_a_naive_timestamp_is_not_converted() -> None:
    """No timezone means no conversion is possible.

    Assuming one would move every night game by a day, and it would do it
    silently. The leading ten characters are the input's own answer, which is
    never better than the input and never pretends to be.
    """
    assert game_date("2026-09-11T23:00:00", LEAGUE) == "2026-09-11"


def test_an_unparseable_value_falls_back_to_its_leading_ten_characters() -> None:
    assert game_date("2026-09-11 not a timestamp", LEAGUE) == "2026-09-11"
    assert game_date("nonsense", LEAGUE) == "nonsense"


@pytest.mark.parametrize("value", ["", "   ", None])
def test_an_absent_timestamp_is_an_empty_date(value: object) -> None:
    """Empty, and never today's date. A guessed date is a key that matches."""
    assert game_date(value, LEAGUE) == ""


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [float("nan"), "nan", "NaN", "  NAN  ", None, "", "  "])
def test_every_spelling_of_absent_reads_as_empty(value: object) -> None:
    """Including the float, which is the one `str(x or "")` gets wrong.

    float NaN is truthy, so the idiom that looks like it does this yields the
    literal string "nan" — which matches nothing, resolves nothing, and renders
    as a player called nan.
    """
    assert clean_text(value) == ""


def test_real_text_survives_with_its_whitespace_stripped() -> None:
    assert clean_text("  Ohio State  ") == "Ohio State"
    assert clean_text(0) == "0"
    assert clean_text(False) == "False"


def test_a_name_that_merely_contains_nan_is_not_emptied() -> None:
    """The rule is the whole value, not a substring.

    `Nanette` and `Fernando Nanez` are text. A containment check here would
    delete real names, and a deleted name is an empty key component that
    matches every other empty one.
    """
    assert clean_text("Nanette") == "Nanette"
    assert clean_text("Hernandez") == "Hernandez"


# ---------------------------------------------------------------------------
# row_game_date
# ---------------------------------------------------------------------------


def test_the_commence_time_is_preferred() -> None:
    row = Row(commence_time="2026-09-12T02:30:00Z", date="2026-09-12")
    assert row_game_date(row, LEAGUE) == "2026-09-11"


def test_a_row_with_only_a_date_falls_back_to_it() -> None:
    """Hand-built frames carry a date and no commence time."""
    assert row_game_date(Row(date="2026-09-11"), LEAGUE) == "2026-09-11"


def test_a_nan_commence_time_falls_back_instead_of_becoming_the_string_nan() -> None:
    """The bug `or` cannot express, asserted directly.

    A NaN commence time is truthy, so `commence_time or date` selects the NaN
    and `game_date` returns "nan" — one key shared by every fixture whose
    commence time failed to round-trip, which is how two games between the same
    clubs on different days became one bet.
    """
    row = Row(commence_time=float("nan"), date="2026-09-11")
    assert row_game_date(row, LEAGUE) == "2026-09-11"
    assert row_game_date(Row(commence_time="nan", date="2026-09-11"), LEAGUE) == (
        "2026-09-11"
    )


def test_a_row_carrying_neither_has_no_date() -> None:
    assert row_game_date(Row(), LEAGUE) == ""


# ---------------------------------------------------------------------------
# What the two rules are for
# ---------------------------------------------------------------------------


def test_two_fixtures_between_the_same_clubs_keep_two_keys() -> None:
    """The reason `selection_key` takes the league date at all.

    A staged file spans days: the bulk endpoint returns every upcoming game,
    and two meetings between the same clubs are two different bets whose
    kickoffs the guard has to judge separately. Joined on the UTC date, the
    late one moves onto the next day and stops matching its own probability.
    """
    friday_night = Row(
        commence_time="2026-09-12T02:30:00Z", home_team="Ohio State", away_team="Michigan"
    )
    saturday_night = Row(
        commence_time="2026-09-13T02:30:00Z", home_team="Ohio State", away_team="Michigan"
    )
    key = dict(market="spreads", selection=HOME, line=-3.5, league=LEAGUE)
    first = selection_key(friday_night, **key)
    second = selection_key(saturday_night, **key)
    assert first != second
    assert first[-1] == "2026-09-11" and second[-1] == "2026-09-12"


def test_an_absent_player_does_not_become_a_player_called_nan() -> None:
    """`selection_key` sends `player` through `clean_text` before anything else.

    A team market has no player. If a NaN round-trip made it the string "nan",
    every team-market key in the file would carry it — and would still join,
    against the other side's "nan", which is a key agreeing with itself about
    nothing.
    """
    row = Row(
        commence_time="2026-09-12T02:30:00Z",
        home_team="Ohio State",
        away_team="Michigan",
        player=float("nan"),
    )
    assert selection_key(
        row, market="spreads", selection=HOME, line=-3.5, league=LEAGUE
    )[1] == ""
