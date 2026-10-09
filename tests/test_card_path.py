"""The card path: identity, pricing, the card's bars, the ledger, the feed.

Every test here builds its own fixtures. None reads `data/raw/`, none touches
the network, and none writes inside the checkout: the suite has to pass on a
clean clone with no credential, which is what proves no test depends on a
live provider.
"""

from __future__ import annotations

import importlib.util
import json
import math
import random
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from ncaaf_betting_lab import forward_evidence as fe
from ncaaf_betting_lab.coverage import KICKOFF_UNKNOWN, UNRATED_OPPONENT
from ncaaf_betting_lab.data.cfbfastr import Game
from ncaaf_betting_lab.fixtures import Match, ScheduleIndex, describe
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from ncaaf_betting_lab.models import margin as margin_model
from ncaaf_betting_lab.models import shapes as shape_fit
from ncaaf_betting_lab.models import total as total_model
from ncaaf_betting_lab.providers.odds_api import ROW_COLUMNS, normalize_event
from ncaaf_betting_lab.providers.team_names import (
    FCS,
    UNRESOLVED,
    build_membership,
    fold,
    load_membership,
)
from ncaaf_betting_lab.reports import card_pricing, gameday_card
from ncaaf_betting_lab.selection import selection_key

LEAGUE = league_for(DEFAULT_LEAGUE_KEY)
ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Registered before it runs: a dataclass resolves its own module by name.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def game(game_id="1", home="Alabama", away="Georgia", home_id="333", away_id="61",
         start="2026-10-03T19:30:00.000Z", hp=None, ap=None, tbd=False,
         home_div="fbs", away_div="fbs") -> Game:
    return Game(
        game_id=game_id, season=2026, week=6, season_type="regular",
        start_date=start, completed=hp is not None, neutral_site=False,
        home_team=home, away_team=away, home_division=home_div,
        away_division=away_div, home_points=hp, away_points=ap,
        home_id=home_id, away_id=away_id, start_time_tbd=tbd,
    )


# -- identity ---------------------------------------------------------------


def test_fold_removes_the_spellings_providers_disagree_on() -> None:
    assert fold("Hawai'i Rainbow Warriors") == fold("Hawaii Rainbow Warriors")
    assert fold("Louisiana-Monroe Warhawks") == "louisiana monroe warhawks"
    assert fold("San José State") == "san jose state"


@pytest.fixture
def membership(tmp_path: Path):
    build = build_membership(
        LEAGUE, tmp_path, season=2026,
        fbs={"333": "Alabama", "61": "Georgia", "2229": "Florida International"},
        teams=[
            {"team_id": "333", "school": "Alabama", "mascot": "Crimson Tide"},
            {"team_id": "61", "school": "Georgia", "mascot": "Bulldogs"},
            {"team_id": "2229", "school": "Florida International", "mascot": "Golden Panthers"},
            {"team_id": "2382", "school": "Mercer", "mascot": "Bears"},
        ],
        extra_aliases={"FIU Panthers": "2229"},
    )
    assert build.fbs_teams == 3
    return load_membership(LEAGUE, tmp_path, season=2026)


def test_membership_resolves_by_identity_and_never_guesses(membership) -> None:
    assert membership.resolve("Alabama Crimson Tide") == "333"
    assert membership.resolve("georgia bulldogs") == "61"
    assert membership.resolve("FIU Panthers") == "2229"
    assert membership.resolve("Mercer Bears") == FCS
    assert membership.resolve("Nowhere Owls") == UNRESOLVED
    assert membership.resolve("") == UNRESOLVED


def test_a_missing_membership_cache_raises_rather_than_resolving_nothing(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_membership(LEAGUE, tmp_path, season=2026)


def test_the_schedule_index_matches_by_ids_and_league_date() -> None:
    index = ScheduleIndex([game()], LEAGUE)
    assert index.find("333", "61", "2026-10-03").flipped is False
    # The provider may call the other team home at a neutral site.
    assert index.find("61", "333", "2026-10-03").flipped is True
    # A day either side, never more: a rematch weeks apart is another game.
    assert index.find("333", "61", "2026-10-04") is not None
    assert index.find("333", "61", "2026-10-06") is None


def test_a_late_night_kickoff_belongs_to_its_eastern_day() -> None:
    late = game(start="2026-10-04T02:30:00.000Z")  # 22:30 ET on the 3rd
    index = ScheduleIndex([late], LEAGUE)
    assert index.find("333", "61", "2026-10-03") is not None


def test_describe_refuses_each_fixture_it_cannot_settle(membership) -> None:
    index = ScheduleIndex(
        [game(), game(game_id="2", home="Georgia", away="Florida International",
                      home_id="61", away_id="2229", tbd=True)],
        LEAGUE,
    )
    ok, match = describe("Alabama Crimson Tide", "Georgia Bulldogs", "2026-10-03",
                         membership=membership, schedule=index)
    assert ok.refusal is None and match.game.game_id == "1"
    fcs, _ = describe("Alabama Crimson Tide", "Mercer Bears", "2026-10-03",
                      membership=membership, schedule=index)
    assert fcs.refusal == UNRATED_OPPONENT
    unknown, _ = describe("Nowhere Owls", "Georgia Bulldogs", "2026-10-03",
                          membership=membership, schedule=index)
    assert unknown.refusal == card_pricing.UNRESOLVED
    off_schedule, _ = describe("Georgia Bulldogs", "Alabama Crimson Tide", "2026-11-21",
                               membership=membership, schedule=index)
    assert off_schedule.refusal == card_pricing.UNRESOLVED
    tbd, _ = describe("Georgia Bulldogs", "FIU Panthers", "2026-10-03",
                      membership=membership, schedule=index)
    assert tbd.refusal == KICKOFF_UNKNOWN


# -- the provider adapter ---------------------------------------------------


def test_normalize_event_reads_every_team_market_shape() -> None:
    event = {
        "id": "e1", "home_team": "Alabama Crimson Tide", "away_team": "Georgia Bulldogs",
        "commence_time": "2026-10-04T00:00:00Z",
        "bookmakers": [{
            "key": "dk",
            "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": "Alabama Crimson Tide", "price": -150},
                    {"name": "Georgia Bulldogs", "price": 130}]},
                {"key": "spreads", "outcomes": [
                    {"name": "Alabama Crimson Tide", "price": -110, "point": -3.5},
                    {"name": "Georgia Bulldogs", "price": -110, "point": 3.5}]},
                {"key": "totals", "outcomes": [
                    {"name": "Over", "price": -110, "point": 52.5},
                    {"name": "Under", "price": -110, "point": 52.5}]},
                {"key": "team_totals", "outcomes": [
                    {"name": "Over", "description": "Alabama Crimson Tide", "price": -115, "point": 28.5}]},
                {"key": "player_pass_yds", "outcomes": [{"name": "Over", "price": -110}]},
            ],
        }],
    }
    parsed = normalize_event(event, LEAGUE, fetched_at="t")
    frame = pd.DataFrame(parsed.rows, columns=list(ROW_COLUMNS))
    assert parsed.unparseable == 0
    assert set(frame["market"]) == {"moneyline", "spread", "total_points", "team_total"}
    assert set(frame["date"]) == {"2026-10-03"}  # 20:00 ET
    spread_home = frame[(frame.market == "spread") & (frame.selection == "home")]
    assert float(spread_home["line"].iloc[0]) == -3.5
    assert set(frame[frame.market == "team_total"]["selection"]) == {"home_over"}
    assert (frame["player"] == "").all()


# -- the shapes and the anchor -----------------------------------------------


def synthetic_line_table(seed: int = 7, games: int = 2400) -> pd.DataFrame:
    """Skewed margins, so a mean anchor and a median anchor disagree."""
    rng = random.Random(seed)
    rows = []
    for index in range(games):
        season = 2022 + index % 4
        spread = rng.choice([-17.5, -10.5, -6.5, -3.0, -1.5, 2.5, 7.0, 13.5])
        noise = rng.gauss(0, 13) + (rng.expovariate(1 / 8) - 8 if spread < -7 else 0)
        margin = max(-60, min(60, int(round(-spread + noise))))
        total_line = rng.choice([44.5, 48.5, 52.5, 57.5, 61.5, 67.5])
        total = max(0, int(round(total_line + rng.gauss(0, 15))))
        for market, line in (("spread", spread), ("total", total_line)):
            rows.append({"game_id": str(index), "season": season, "market": market,
                         "close_consensus": line, "margin": margin, "total_points": total})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def shapes():
    return shape_fit.fit(synthetic_line_table(), before_season=2026)


def test_shapes_are_fitted_on_earlier_seasons_only() -> None:
    table = synthetic_line_table()
    assert shape_fit.fit(table, before_season=2024).seasons == (2022, 2023)
    assert shape_fit.fit(table, before_season=2022).games == 0
    assert "No shape was fitted" in shape_fit.fit(table, before_season=2022).summary()


def test_the_total_shape_never_puts_mass_below_zero(shapes) -> None:
    for pmf in shapes.totals.values():
        assert min(pmf) >= 0
        assert math.isclose(sum(pmf.values()), 1.0, rel_tol=1e-6)
    model = total_model.build(shapes.totals, total_line=52.0)
    win, push = model.probability_over(52.0, side="over")
    under, _ = model.probability_over(52.0, side="under")
    assert push > 0 and math.isclose(win + push + under, 1.0, rel_tol=1e-6)


@pytest.mark.parametrize("line", [-17.5, -10.5, -3.0, 2.5, 13.5])
def test_the_anchor_puts_the_consensus_line_at_a_coin_flip(shapes, line) -> None:
    model = card_pricing.anchor_margin(shapes, line)
    win, push = model.probability_cover(line, side="home")
    assert abs(win / (1 - push) - 0.5) < 1e-6
    # And a rung further from the favourite's side is less likely to cover.
    assert model.probability_cover(line - 3, side="home")[0] < win


def test_the_mean_anchor_would_have_disagreed_with_the_line() -> None:
    """The reason the anchor is the median: on a skewed shape the mean-anchored
    model calls the consensus line something other than a coin flip."""
    # A favourite's blowout tail: most mass near +7, a long run out to +40.
    skewed = {m: (0.08 if 0 <= m <= 10 else 0.005) for m in range(-20, 41)}
    norm = sum(skewed.values())
    skewed = {m: p / norm for m, p in skewed.items()}
    shapes = shape_fit.Shapes(margins={margin_model.bucket_for(10.5): skewed})
    mean_anchored = margin_model.build(shapes.margins, implied_margin=10.5)
    win, push = mean_anchored.probability_cover(-10.5, side="home")
    assert abs(win / (1 - push) - 0.5) > 0.05
    anchored = card_pricing.anchor_margin(shapes, -10.5)
    win, push = anchored.probability_cover(-10.5, side="home")
    assert abs(win / (1 - push) - 0.5) < 1e-6


def test_the_total_anchor_puts_the_consensus_total_at_a_coin_flip(shapes) -> None:
    model = card_pricing.anchor_total(shapes, 55.5)
    assert abs(model.probability_over(55.5, side="over")[0] - 0.5) < 1e-6


# -- pricing and the accounting identity -------------------------------------


def staged(rows) -> pd.DataFrame:
    base = {"fetched_at": "t", "event_id": "e", "provider_key": "", "player": "",
            "commence_time": "2026-10-03T19:30:00Z", "date": "2026-10-03"}
    return pd.DataFrame([{**base, **row} for row in rows], columns=list(ROW_COLUMNS))


def slate_rows(home="Alabama Crimson Tide", away="Georgia Bulldogs"):
    rows = []
    for book, shift in (("dk", 0.0), ("fd", 0.5), ("mgm", -0.5)):
        for selection, line in (("home", -6.5 + shift), ("away", 6.5 - shift)):
            rows.append(dict(home_team=home, away_team=away, market="spread",
                             selection=selection, line=line, american_odds=-110, book=book))
        for selection in ("over", "under"):
            rows.append(dict(home_team=home, away_team=away, market="total_points",
                             selection=selection, line=52.5, american_odds=-110, book=book))
    rows += [
        dict(home_team=home, away_team=away, market="moneyline", selection="home",
             line=None, american_odds=-240, book="dk"),
        dict(home_team=home, away_team=away, market="alternate_spread", selection="away",
             line=13.5, american_odds=-105, book="dk"),
        dict(home_team=home, away_team=away, market="team_total", selection="home_over",
             line=28.5, american_odds=-110, book="dk"),
        dict(home_team=home, away_team=away, market="spread_h1", selection="home",
             line=-3.5, american_odds=-110, book="dk"),
        dict(home_team=home, away_team=away, market="mystery", selection="home",
             line=1, american_odds=-110, book="dk"),
    ]
    return rows


def test_every_staged_row_lands_in_exactly_one_bucket(shapes) -> None:
    prices = staged(slate_rows() + slate_rows(home="Mercer Bears"))
    fixtures = {
        ("Alabama Crimson Tide", "Georgia Bulldogs"): card_pricing.Fixture(),
        ("Mercer Bears", "Georgia Bulldogs"): card_pricing.Fixture(UNRATED_OPPONENT, "fcs"),
    }
    probabilities, diagnostics = card_pricing.price_slate(
        prices, LEAGUE, shapes=shapes, fixtures=fixtures
    )
    assert diagnostics.reconciles(), diagnostics.identity_line()
    assert diagnostics.priced == len(prices)
    assert diagnostics.unrated_opponent == len(slate_rows())
    assert diagnostics.no_opinion == 2  # team_total and spread_h1
    assert diagnostics.unparseable == 1  # the unknown market
    assert diagnostics.opinions == len(slate_rows()) - 3
    # One probability per wager, however many books quote it.
    assert len(probabilities) == 10


def test_an_undescribed_fixture_is_unresolved_never_guessed(shapes) -> None:
    _, diagnostics = card_pricing.price_slate(
        staged(slate_rows()), LEAGUE, shapes=shapes, fixtures={}
    )
    assert diagnostics.unresolved == diagnostics.priced and diagnostics.opinions == 0


def test_a_moneyline_has_no_draw(shapes) -> None:
    prices = staged(slate_rows())
    probabilities, _ = card_pricing.price_slate(
        prices, LEAGUE, shapes=shapes,
        fixtures={("Alabama Crimson Tide", "Georgia Bulldogs"): card_pricing.Fixture()},
    )
    row = prices[prices.market == "moneyline"].iloc[0]
    home = probabilities[selection_key(row, market="moneyline", selection="home",
                                       line=None, league=LEAGUE)]
    assert 0.6 < home < 0.85


# -- the card's bars -----------------------------------------------------------


class Policy:
    def __init__(self, allowed=()):
        self.allowed = set(allowed)

    def market_allowed(self, league, market):
        return market in self.allowed

    def refusal_reason(self, league, market):
        return "not allowlisted"


def keyed(prices, probability):
    return {
        selection_key(row, market=row.market, selection=row.selection,
                      line=None if pd.isna(row.line) else float(row.line), league=LEAGUE): probability
        for row in prices.itertuples()
    }


def test_select_applies_every_bar_and_keeps_the_best_price() -> None:
    prices = staged([
        dict(home_team="A", away_team="B", market="spread", selection="home", line=-3.5,
             american_odds=-110, book="dk"),
        dict(home_team="A", away_team="B", market="spread", selection="home", line=-3.5,
             american_odds=+100, book="fd"),
        dict(home_team="A", away_team="B", market="total_points", selection="over", line=50.5,
             american_odds=-200, book="dk"),
    ])
    selections, _ = gameday_card.select(
        prices, keyed(prices, 0.60), LEAGUE, policy=Policy({"spread", "total_points"}), now=NOW
    )
    assert [(s["market"], s["book"], s["odds"]) for s in selections] == [("spread", "fd", 100)]
    nothing, _ = gameday_card.select(
        prices, keyed(prices, 0.60), LEAGUE, policy=Policy(), now=NOW
    )
    assert nothing == []
    thin, _ = gameday_card.select(
        prices, keyed(prices, 0.52), LEAGUE, policy=Policy({"spread"}), now=NOW
    )
    assert thin == []


def test_a_started_game_is_quarantined_not_selected() -> None:
    prices = staged([dict(home_team="A", away_team="B", market="spread", selection="home",
                          line=-3.5, american_odds=100, book="dk",
                          commence_time="2026-10-03T11:00:00Z")])
    selections, pulled = gameday_card.select(
        prices, keyed(prices, 0.7), LEAGUE, policy=Policy({"spread"}), now=NOW
    )
    assert selections == [] and len(pulled) == 1


def test_the_card_says_no_demonstrated_edge_above_every_selection() -> None:
    prices = staged([dict(home_team="A", away_team="B", market="spread", selection="home",
                          line=-3.5, american_odds=100, book="dk")])
    card = gameday_card.build_card(
        prices, LEAGUE, policy=Policy({"spread"}),
        diagnostics=card_pricing.PricingDiagnostics(priced=1, opinions=1),
        now=NOW, slate_date="2026-10-03", refused=["X @ Y — fcs"],
        probabilities=keyed(prices, 0.7),
    )
    text = gameday_card.render(card)
    assert card.decision == "selections"
    assert text.index(gameday_card.NO_DEMONSTRATED_EDGE_NOTE) < text.index("| Game |")
    assert "X @ Y — fcs" in text and "reconciles" in text


# -- the forward ledger ----------------------------------------------------------


def snapshot_frame(rows) -> pd.DataFrame:
    base = {"snapshot_date": "2026-10-03", "game_id": "1", "flipped": False,
            "commence_time": "", "home_team": "Alabama Crimson Tide",
            "away_team": "Georgia Bulldogs", "book": "dk", "model_probability": 0.5,
            "edge": 0.0, "gates_in_force": "", "american_odds": -110}
    return pd.DataFrame([{**base, **row} for row in rows], columns=list(fe.SNAPSHOT_COLUMNS))


def settle(rows, games, as_of=date(2026, 10, 5)):
    return fe.settle_snapshot(snapshot_frame(rows), games=games, as_of=as_of, settled_at="s")


def test_settlement_reads_the_frozen_game_id_and_the_provider_side() -> None:
    final = [game(hp=31.0, ap=24.0)]
    result = settle([
        dict(market="spread", selection="home", line=-6.5),
        dict(market="spread", selection="away", line=7.0),
        dict(market="moneyline", selection="away", line=None),
        dict(market="total_points", selection="over", line=55.0),
        dict(market="team_total", selection="home_over", line=30.5),
        dict(market="spread_h1", selection="home", line=-3.5),
    ], final)
    assert list(result.settled["outcome"]) == [
        fe.WON, fe.PUSH, fe.LOST, fe.PUSH, fe.WON, fe.UNSETTLEABLE
    ]
    flipped = settle([dict(market="moneyline", selection="home", line=None, flipped=True)], final)
    assert list(flipped.settled["outcome"]) == [fe.LOST]


def test_a_day_waits_for_its_last_game_then_gives_up_after_the_patience() -> None:
    games = [game(hp=31.0, ap=24.0), game(game_id="2", hp=None, ap=None)]
    rows = [dict(market="spread", selection="home", line=-6.5),
            dict(market="spread", selection="home", line=-6.5, game_id="2")]
    waiting = settle(rows, games)
    assert waiting.settled.empty and waiting.notes
    late = settle(rows, games, as_of=date(2026, 10, 3 + fe.PATIENCE_DAYS))
    assert list(late.settled["outcome"]) == [fe.WON, fe.UNSETTLEABLE]


def test_write_snapshot_freezes_only_what_can_be_settled(tmp_path: Path) -> None:
    prices = staged([
        dict(home_team="A", away_team="B", market="spread", selection="home", line=-3.5,
             american_odds=-110, book="dk"),
        dict(home_team="C", away_team="D", market="spread", selection="home", line=-3.5,
             american_odds=-110, book="dk"),
    ])
    key = lambda row, *, market, selection, line: selection_key(  # noqa: E731
        row, market=market, selection=selection, line=line, league=LEAGUE)
    path = fe.write_snapshot(
        prices, keyed(prices, 0.55), key_for=key,
        matches={("A", "B"): Match(game=game(), flipped=True)},
        gates_in_force="g", snapshot_date="2026-10-03", archive_dir=tmp_path,
    )
    frozen = pd.read_csv(path)
    assert list(frozen["home_team"]) == ["A"] and bool(frozen["flipped"].iloc[0])
    again = fe.write_snapshot(
        prices, keyed(prices, 0.9), key_for=key,
        matches={("A", "B"): Match(game=game(), flipped=True)},
        gates_in_force="g", snapshot_date="2026-10-03", archive_dir=tmp_path,
    )
    assert again is None  # the first opinion of the day stands


def test_the_interval_is_clustered_by_game() -> None:
    rows = []
    for index in range(20):
        outcome = fe.WON if index % 2 else fe.LOST
        for _ in range(20):
            rows.append({"snapshot_date": "d", "home_team": f"H{index}", "away_team": "A",
                         "outcome": outcome, "profit_units": 1.0 if index % 2 else -1.0})
    roi, low, high, bets, games = fe.interval_by_game(pd.DataFrame(rows))
    assert (bets, games) == (400, 20) and roi == 0.0
    # Twenty perfectly correlated bets per game: the half-width is the game-level
    # one, about 1.96 * 1/sqrt(20) — not the bet-level one, sqrt(20) narrower.
    assert 0.4 < (high - low) / 2 < 0.5


# -- the feed and the script ---------------------------------------------------


def test_the_standdown_retries_a_degraded_day_a_bounded_number_of_times() -> None:
    feed = load_script("card_feed")
    today = "2026-10-03"
    assert feed.standdown_decision(None, today=today).run
    assert feed.standdown_decision({"slate_date": "2026-10-02", "decision": "selections"},
                                   today=today).run
    assert not feed.standdown_decision({"slate_date": today, "decision": "no-slate"},
                                       today=today).run
    degraded = {"slate_date": today, "decision": "degraded", "attempts": 2}
    assert feed.standdown_decision(degraded, today=today).run
    assert not feed.standdown_decision({**degraded, "attempts": 3}, today=today).run
    assert feed.next_status(degraded, today=today, decision="degraded", run_id="r")["attempts"] == 3
    assert feed.next_status(degraded, today="2026-10-04", decision="x", run_id="r")["attempts"] == 1


def test_the_changed_marker_fires_on_a_different_set_only() -> None:
    feed = load_script("card_feed")
    pick = {"game": "A @ B", "market": "spread", "selection": "home", "line": -3.5, "odds": 100}
    assert not feed.selections_changed([pick], [{**pick, "odds": 105}])
    assert feed.selections_changed([pick], [])
    assert feed.selections_changed(None, [pick])
    assert feed.OPERATING_HOME == "NCAAF Betting Lab — Claude Operating Home"
    assert feed.CHANGED_MARKER == "Selections changed"


def test_the_feed_refuses_to_run_without_a_token() -> None:
    feed = load_script("card_feed")
    with pytest.raises(feed.FeedError):
        feed.Feed("owner/repo", "", Path("."))


def test_a_cap_above_the_agreed_one_is_refused_before_anything_runs(tmp_path, monkeypatch) -> None:
    card = load_script("run_gameday_card")
    monkeypatch.setattr(card, "OUTPUTS_DIR", tmp_path)
    assert card.main(["--live", "--credit-cap", str(LEAGUE.daily_credit_cap + 1)]) == 2
    status = json.loads((tmp_path / LEAGUE.output_name("card_run", ".json")).read_text())
    assert status["decision"] == "degraded"


def test_the_registered_cap_is_the_agreed_one() -> None:
    assert LEAGUE.daily_credit_cap == 1_200


def test_a_card_never_backs_both_sides_of_one_game() -> None:
    # The 2026-10-09 card in miniature: both blowouts cleared the bar.
    prices = staged([
        dict(home_team="A", away_team="B", market="alternate_spread", selection="away",
             line=-9.5, american_odds=500, book="dk"),
        dict(home_team="A", away_team="B", market="alternate_spread", selection="away",
             line=-6.5, american_odds=305, book="dk"),
        dict(home_team="A", away_team="B", market="alternate_spread", selection="home",
             line=-14.5, american_odds=556, book="dk"),
        dict(home_team="A", away_team="B", market="total_points", selection="over",
             line=50.5, american_odds=100, book="dk"),
        dict(home_team="C", away_team="D", market="alternate_spread", selection="home",
             line=-14.5, american_odds=556, book="dk"),
    ])
    probability = {
        ("away", -9.5): 0.234, ("away", -6.5): 0.302, ("home", -14.5): 0.205,
        ("over", 50.5): 0.60,
    }
    probabilities = {
        selection_key(row, market=row.market, selection=row.selection,
                      line=float(row.line), league=LEAGUE): probability[(row.selection, row.line)]
        for row in prices.itertuples()
    }
    policy = Policy({"alternate_spread", "total_points"})
    selections, _ = gameday_card.select(prices, probabilities, LEAGUE, policy=policy, now=NOW)
    sides = {(s["game"], s["market"], s["selection"]) for s in selections}
    # B's blowout carries the larger single edge, so B is the side kept; the
    # total is a different question and stands; game C has one side only.
    assert sides == {
        ("B @ A", "alternate_spread", "away"),
        ("B @ A", "total_points", "over"),
        ("D @ C", "alternate_spread", "home"),
    }
    card = gameday_card.build_card(
        prices, LEAGUE, policy=policy,
        diagnostics=card_pricing.PricingDiagnostics(priced=5, opinions=5),
        now=NOW, slate_date="2026-10-03", refused=[], probabilities=probabilities,
    )
    assert [p["game"] for p in card.opposite_side] == ["B @ A"]
    assert "One side per game" in gameday_card.render(card)


def test_one_side_per_game_ignores_row_order_and_reads_team_totals_per_team() -> None:
    picks = [
        dict(game="B @ A", market="team_total", selection="home_over", edge=0.05),
        dict(game="B @ A", market="team_total", selection="away_under", edge=0.04),
        dict(game="B @ A", market="alternate_team_total", selection="home_under", edge=0.06),
        dict(game="B @ A", market="spread", selection="home", edge=0.04),
        dict(game="B @ A", market="moneyline", selection="away", edge=0.04),
        dict(game="B @ A", market="alternate_spread", selection="away", edge=0.01),
    ]
    kept, dropped = gameday_card.one_side_per_game(picks)
    kept_reversed, _ = gameday_card.one_side_per_game(list(reversed(picks)))
    assert sorted(map(id, kept)) == sorted(map(id, kept_reversed))
    # home over and away under agree; home under contradicts home over and wins on edge.
    assert {(p["market"], p["selection"]) for p in kept} == {
        ("team_total", "away_under"), ("alternate_team_total", "home_under"),
        ("moneyline", "away"), ("alternate_spread", "away"),
    }
    assert len(kept) + len(dropped) == len(picks)
