"""The nightly form rating, the quarterback flag, and the card section that shows them."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from ncaaf_betting_lab.data.cfbfastr import Game
from ncaaf_betting_lab.data.starters import StarterState, game_starters, state_before
from ncaaf_betting_lab.models import form
from ncaaf_betting_lab.reports import form_context

ROOT = Path(__file__).resolve().parents[1]
START = datetime(2025, 8, 30, 17, tzinfo=timezone.utc)


def _game(i: int, home: str, away: str, margin: float, *, when: datetime, season: int = 2025) -> Game:
    return Game(
        game_id=str(1000 + i), season=season, week=1 + i // 10, season_type="regular",
        start_date=when.isoformat().replace("+00:00", "Z"), completed=True,
        neutral_site=True, home_team=home, away_team=away, home_division="fbs",
        away_division="fbs", home_points=30.0 + max(margin, 0), away_points=30.0 - min(margin, 0),
        home_id=home, away_id=away,
    )


def _league(n: int, *, recent_flip: bool) -> pd.DataFrame:
    """A beats B by 10 for most of history; optionally B beats A lately."""
    games = []
    teams = [f"T{k}" for k in range(8)]
    for i in range(n):
        when = START + timedelta(days=i)
        h, a = teams[i % 8], teams[(i + 3) % 8]
        games.append(_game(i, h, a, 0.0, when=when))
    for j in range(40):
        when = START + timedelta(days=n + j)
        late = recent_flip and j >= 30
        games.append(_game(n + j, "A", "B", -10.0 if late else 10.0, when=when))
    return form.games_frame(games)


def test_too_little_history_prints_no_rating() -> None:
    frame = _league(10, recent_flip=False)
    assert form.fit(frame, season=2025, as_of=START + timedelta(days=400)) is None


def test_the_rating_reads_margins_and_home_field_zero_on_neutral() -> None:
    frame = _league(form.MINIMUM_HISTORY, recent_flip=False)
    ratings = form.fit(frame, season=2025, as_of=START + timedelta(days=400))
    assert ratings is not None
    assert ratings.margin("A", "B", neutral=True) == pytest.approx(10.0, abs=1.5)
    assert ratings.margin("A", "nobody", neutral=True) is None


def test_recent_games_outweigh_old_ones() -> None:
    """The point of the module: last night counts more than September."""
    steady = form.fit(_league(form.MINIMUM_HISTORY, recent_flip=False), season=2025,
                      as_of=START + timedelta(days=400))
    flipped = form.fit(_league(form.MINIMUM_HISTORY, recent_flip=True), season=2025,
                       as_of=START + timedelta(days=400))
    assert flipped.margin("A", "B", neutral=True) < steady.margin("A", "B", neutral=True) - 3


def test_a_game_after_as_of_is_never_read() -> None:
    frame = _league(form.MINIMUM_HISTORY, recent_flip=True)
    cut = frame["kickoff"].iloc[-11]
    early = form.fit(frame, season=2025, as_of=cut)
    trimmed = form.fit(frame[frame["kickoff"] < cut], season=2025, as_of=cut)
    assert early.ratings == trimmed.ratings


def test_margins_are_capped() -> None:
    frame = _league(form.MINIMUM_HISTORY, recent_flip=False)
    frame.loc[frame["home"] == "A", "margin"] = 70.0
    ratings = form.fit(frame, season=2025, as_of=START + timedelta(days=400))
    assert ratings.margin("A", "B", neutral=True) <= form.MARGIN_CAP + 0.5


def test_a_summer_counts_as_the_offseason_not_thirty_six_weeks() -> None:
    frame = pd.DataFrame(
        {
            "kickoff": [datetime(2024, 8, 31, tzinfo=timezone.utc), datetime(2024, 12, 7, tzinfo=timezone.utc),
                        datetime(2025, 8, 30, tzinfo=timezone.utc)],
            "season": [2024, 2024, 2025],
        }
    )
    ages = form.season_clock(frame, 2025, datetime(2025, 8, 30, tzinfo=timezone.utc))
    assert ages[1] == pytest.approx(form.OFFSEASON_WEEKS, abs=0.01)
    assert ages[0] == pytest.approx(form.OFFSEASON_WEEKS + 14.0, abs=0.01)
    assert ages[2] == pytest.approx(0.0)


def test_the_starter_is_the_player_with_the_most_dropbacks() -> None:
    plays = pd.DataFrame(
        {
            "game_id": [1, 1, 1, 1, 1],
            "team": ["X"] * 5,
            "completion_player_id": [10, 10, None, None, 20],
            "completion_player": ["Ten", "Ten", None, None, "Twenty"],
            "incompletion_player_id": [None, None, 20, None, None],
            "incompletion_player": [None, None, "Twenty", None, None],
            "interception_thrown_player_id": [None, None, None, 20, None],
            "interception_thrown_player": [None, None, None, "Twenty", None],
            "sack_taken_player_id": [None] * 5,
            "sack_taken_player": [None] * 5,
        }
    )
    row = game_starters(plays).iloc[0]
    assert (row["player_id"], row["dropbacks"]) == ("20", 3)


def test_a_missing_dropback_column_raises_rather_than_reading_as_no_passes() -> None:
    with pytest.raises(KeyError):
        game_starters(pd.DataFrame({"game_id": [1], "team": ["X"]}))


@pytest.mark.parametrize(
    ("history", "changed"),
    [
        ([], None),
        (["a"], None),
        (["a", "a"], False),
        (["a", "a", "b"], True),
        (["a", "b"], False),  # a tie goes to the more recent: b is the incumbent
        (["a", "a", ""], None),  # a game with no play data breaks the chain
    ],
)
def test_qb_changed(history: list[str], changed: bool | None) -> None:
    assert state_before(history).qb_changed is changed


def test_the_card_section_says_it_moves_no_probability() -> None:
    row = form_context.GameContext(
        label="B @ A", market_margin=-3.0, form_margin=2.0,
        home_qb=StarterState("a", "a", 3), away_qb=StarterState("c", "b", 3),
        home_qb_name="Alpha", away_qb_name="Charlie",
    )
    text = form_context.render([row], None, starters_through=None)
    assert "do not move any probability" in text
    assert "+5.0" in text
    assert "**changed last game** (Charlie)" in text
    assert "No form rating" in text
    assert "was not available this run" in text


def test_the_probabilities_do_not_read_the_form_rating() -> None:
    """Context until it beats the price: the pricing module must not import it."""
    source = (ROOT / "src/ncaaf_betting_lab/reports/card_pricing.py").read_text()
    imported = {
        alias.name if isinstance(node, ast.Import) else f"{node.module}.{alias.name}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = ("models.form", "form_context", "starters")
    assert not [name for name in imported if name.endswith(forbidden)]
