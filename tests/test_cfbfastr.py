"""The settlement source, and the column that solves the hardest problem.

There is no nflverse for college football. Choosing what replaces it was the
largest open question in this lab, and the answer is cfbfastR's committed data
— chosen over the same project's REST API because a file download has no rate
limit and can be re-fetched and compared, and over anything else because it
carries `home_division`/`away_division` per game.

That column is why 127 of 888 games in 2026 can be declined rather than
silently priced with a league-average opponent on the field.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from ncaaf_betting_lab.data.cfbfastr import (
    FBS,
    REQUIRED_COLUMNS,
    Game,
    fbs_teams,
    load_schedule,
    rateable_games,
    schedule_path,
)
from ncaaf_betting_lab.config import PROCESSED_DIR
from ncaaf_betting_lab.leagues import NCAAF


def _game(**kw) -> Game:
    base = dict(
        game_id="1", season=2026, week=1, season_type="regular",
        start_date="2026-08-30T16:00:00.000Z", completed=True,
        neutral_site=False, home_team="Ohio State", away_team="Michigan",
        home_division=FBS, away_division=FBS,
        home_points=31.0, away_points=24.0,
    )
    return Game(**{**base, **kw})


def _write(tmp_path: Path, rows: list[dict], *, columns=None) -> Path:
    path = schedule_path(NCAAF, tmp_path, season=2026)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(columns or sorted(REQUIRED_COLUMNS))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    return path


def _row(**kw) -> dict:
    base = dict(
        game_id="1", season=2026, week=1, season_type="regular",
        start_date="2026-08-30T16:00:00.000Z", completed="TRUE",
        neutral_site="FALSE", home_team="Ohio State", away_team="Michigan",
        home_division="fbs", away_division="fbs",
        home_points=31, away_points=24,
    )
    return {**base, **kw}


def test_an_fbs_versus_fcs_game_is_not_rateable() -> None:
    """The whole reason this source was chosen. 127 of 888 games in 2026 put an
    FBS team against an opponent with no rating, and each one must be declined
    rather than priced with a league-average team on the field."""
    game = _game(away_team="Mercer", away_division="fcs")

    assert not game.is_fbs_only
    assert rateable_games([game]) == []


def test_an_fbs_versus_fbs_game_is_rateable() -> None:
    assert _game().is_fbs_only
    assert len(rateable_games([_game()])) == 1


def test_the_rateable_split_is_reported_rather_than_silently_dropped() -> None:
    """A caller must be able to say how many games it declined. A silent drop
    and a slate with fewer games look identical."""
    games = [_game(), _game(away_team="Mercer", away_division="fcs")]

    assert len(games) - len(rateable_games(games)) == 1


def test_fbs_membership_comes_from_the_schedule_itself() -> None:
    """Derived from the fixtures rather than a separate file, so the club set
    and the games cannot disagree — and it is season-keyed by construction,
    which matters because FBS membership moved by two teams this year."""
    games = [
        _game(home_team="Ohio State", away_team="Michigan"),
        _game(home_team="Ohio State", away_team="Mercer", away_division="fcs"),
    ]

    assert fbs_teams(games) == ("Michigan", "Ohio State")


def test_margin_and_total_are_read_from_the_final_score() -> None:
    game = _game(home_points=31.0, away_points=24.0)

    assert game.margin == 7.0
    assert game.total == 55.0


def test_an_unfinished_game_offers_no_result_rather_than_a_zero() -> None:
    """A game that has not been played has no margin. Returning 0.0 would be a
    tie nobody played, and college football cannot tie."""
    game = _game(completed=False, home_points=None, away_points=None)

    assert not game.has_result
    assert game.margin is None
    assert game.total is None


def test_completed_but_scoreless_is_still_no_result() -> None:
    """`completed` true with missing points is a feed mid-update, not a 0-0."""
    assert not _game(completed=True, home_points=None).has_result


def test_a_missing_schedule_raises_rather_than_returning_nothing(tmp_path) -> None:
    """An empty schedule and a season with no games look identical downstream,
    and this lab's sibling shipped that confusion twice."""
    with pytest.raises(FileNotFoundError, match="Fetch it"):
        load_schedule(NCAAF, tmp_path, season=2026)


def test_a_schedule_missing_a_required_column_raises(tmp_path) -> None:
    """A file without `home_division` is not a smaller schedule — it is a
    different file, and every FBS/FCS decision downstream would be a guess."""
    columns = sorted(REQUIRED_COLUMNS - {"home_division"})
    _write(tmp_path, [_row()], columns=columns)

    with pytest.raises(ValueError, match="home_division"):
        load_schedule(NCAAF, tmp_path, season=2026)


def test_a_real_row_round_trips(tmp_path) -> None:
    _write(tmp_path, [_row(), _row(game_id="2", away_team="Mercer",
                                   away_division="fcs")])

    games = load_schedule(NCAAF, tmp_path, season=2026)

    assert len(games) == 2
    assert games[0].is_fbs_only
    assert not games[1].is_fbs_only
    assert games[0].home_points == 31.0


def test_the_elo_column_is_not_among_the_required_ones() -> None:
    """`home_pregame_elo` is present in the file and deliberately unused: a
    rating this lab did not fit is one it cannot explain, walk forward, or hold
    a verdict on."""
    assert not any("elo" in column for column in REQUIRED_COLUMNS)


def test_a_completed_season_file_carries_every_division() -> None:
    """The trap that a raw row count walks into.

    2024's file holds 3,801 games of which only 920 involve an FBS team — the
    rest are Division III (2,446), Division II (1,804) and FCS-only fixtures.
    2026's holds 888, all FBS-involving. Two different populations wearing one
    schema, and a fit that loaded a season and trained on it would train on
    Division III for the historical seasons and not for the current one.
    """
    from ncaaf_betting_lab.data.cfbfastr import fbs_involving_games

    games = [
        _game(),
        _game(away_team="Mercer", away_division="fcs"),
        _game(home_team="Kenyon", away_team="Oberlin",
              home_division="iii", away_division="iii"),
    ]

    assert len(fbs_involving_games(games)) == 2
    assert not games[2].involves_fbs


def test_involving_fbs_is_not_the_same_question_as_rateable() -> None:
    """One asks whether this lab could ever care; the other whether it can
    price. An FBS-vs-FCS game answers yes to the first and no to the second."""
    from ncaaf_betting_lab.data.cfbfastr import fbs_involving_games

    game = _game(away_team="Mercer", away_division="fcs")

    assert len(fbs_involving_games([game])) == 1
    assert rateable_games([game]) == []


# --------------------------------------------------------------------------
# The sign-collision defect in scripts/build_line_table.py.

def _builder():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import build_line_table

    return build_line_table


def test_an_inverted_book_row_is_found() -> None:
    """The measured defect: one book quotes the home row backwards.

    Game 401331447 (2021 wk14, Michigan at Iowa, neutral site, final 42-3):
    Bovada quotes Iowa at -12.0 while teamrankings, consensus and William Hill
    all quote it at +12.0. Michigan won by 39, so +12 is the honest sign.
    """
    build = _builder()
    closing = pd.Series([-12.0, 12.0, 12.0, 12.0])
    assert build.inverted_rows(closing) == [0]


def test_an_honest_disagreement_is_not_an_inversion() -> None:
    """Books differing by a point are not on opposite conventions, and a rule
    that says they are would drop most of the feed."""
    build = _builder()
    assert build.inverted_rows(pd.Series([12.0, 12.5, 13.0, 11.5])) == []
    assert build.inverted_rows(pd.Series([-6.5, -7.0, -6.0])) == []


def test_a_pickem_is_never_called_an_inversion() -> None:
    """Near zero, -0.5 and +0.5 are two books disagreeing about a coin flip,
    not two conventions. Without this guard the rule fires on real games."""
    build = _builder()
    assert build.inverted_rows(pd.Series([-0.5, 0.5, 0.5])) == []


def test_two_books_are_too_few_to_judge_a_sign() -> None:
    """With one number either side, there is no majority to be wrong about."""
    build = _builder()
    assert build.inverted_rows(pd.Series([-12.0, 12.0])) == []


def test_the_move_is_measured_inside_a_book() -> None:
    """`close_consensus - open_consensus` was a difference between medians over
    DIFFERENT book sets, since a book with no opener still votes on the close.
    One inverted row then became a 22.5-point move. A move measured inside a
    book cannot be a convention collision."""
    build = _builder()
    group = pd.DataFrame({"_close": [12.0, 12.0, 13.0], "_open": [10.5, 11.0, None]})
    assert build.within_book_move(group) == pytest.approx(1.25)


def test_a_move_no_book_can_evidence_is_missing_not_reconstructed() -> None:
    """Where no book carries both halves, the move is NOT rebuilt from the two
    consensuses. A price that cannot be read stays missing."""
    build = _builder()
    group = pd.DataFrame({"_close": [12.0, 12.0], "_open": [None, None]})
    assert build.within_book_move(group) is None


def test_the_shipped_table_carries_no_sign_collision() -> None:
    """The regression, against the real table rather than a fixture.

    Before the fix the table held a 22.5-point move on 401331447 -- 10.6
    standard deviations, and 1,721 of the 15,386 pts^2 the close-beats-open
    control was built from. The game is still present; its opener is not,
    because the only book quoting one quoted it backwards.
    """
    table = pd.read_csv(PROCESSED_DIR / "line_table.csv", dtype={"game_id": str})
    spread = table[table["market"] == "spread"]
    assert not spread.empty, "no spread rows; this test would pass vacuously"

    collision = spread[spread["line_move"].abs() >= 20]
    assert collision.empty, (
        "a line move of 20+ points is a sign collision, not a market move: "
        f"{collision[['game_id', 'open_consensus', 'close_consensus', 'line_move']].to_dict('records')}"
    )

    game = spread[spread["game_id"] == "401331447"]
    assert len(game) == 1, "401331447 should still be in the table"
    assert pd.isna(game.iloc[0]["open_consensus"]), (
        "401331447's only opener came from the inverted book and must be missing"
    )
