"""Step 5: fit ratings walk-forward and ask whether they beat the closing price.

    python scripts/run_ratings_residual.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.experiment_ledger import load as load_ledger
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.ratings_residual import (
    MINIMUM_HISTORY,
    fit_ratings,
    regress,
    render,
)

SEASONS = (2021, 2022, 2023, 2024, 2025)
OUTPUT = Path("data/outputs/ratings_residual.md")


def games_with_a_close() -> pd.DataFrame:
    lines = pd.read_csv("data/processed/line_table.csv", dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].set_index("game_id")
    rows = []
    for season in SEASONS:
        schedule = load_schedule(NCAAF, Path("data/raw"), season=season)
        for game in rateable_games(schedule):
            if not game.has_result or game.game_id not in spreads.index:
                continue
            rows.append(
                {
                    "season": game.season,
                    "week": game.week,
                    "home": game.home_team,
                    "away": game.away_team,
                    "neutral": game.neutral_site,
                    "margin": float(game.margin),
                    # close_consensus is the HOME handicap, so the price's own
                    # forecast of the home margin is its negative.
                    "implied": -float(spreads.loc[game.game_id, "close_consensus"]),
                }
            )
    return pd.DataFrame(rows).sort_values(["season", "week"]).reset_index(drop=True)


def walk_forward(games: pd.DataFrame) -> pd.DataFrame:
    """Price each week with ratings fitted strictly on earlier games."""
    rows = []
    for season in SEASONS[1:]:
        for week in sorted(games.loc[games["season"] == season, "week"].unique()):
            history = games[
                (games["season"] < season)
                | ((games["season"] == season) & (games["week"] < week))
            ]
            if len(history) < MINIMUM_HISTORY:
                continue
            ratings, home_field = fit_ratings(history)
            current = games[(games["season"] == season) & (games["week"] == week)]
            for _, game in current.iterrows():
                if game["home"] not in ratings or game["away"] not in ratings:
                    continue
                rating_margin = (
                    ratings[game["home"]]
                    - ratings[game["away"]]
                    + (0.0 if game["neutral"] else home_field)
                )
                rows.append(
                    {
                        "season": season,
                        "week": week,
                        "resid": game["margin"] - game["implied"],
                        "disagree": rating_margin - game["implied"],
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    games = games_with_a_close()
    priced = walk_forward(games)
    if priced.empty:
        raise SystemExit("no games were priced — an absence, not a null")
    ledger = load_ledger(Path("data/outputs/experiment_ledger.json"))
    factor = ledger.correction_factor()
    tests = [
        regress(priced, "all games", correction_factor=factor),
        regress(priced[priced["week"] <= 4], "early season (weeks 1-4)", correction_factor=factor),
        regress(priced[priced["week"] > 4], "late season (weeks 5+)", correction_factor=factor),
    ]
    body = render(
        tests,
        disagreement_sd=float(priced["disagree"].std()),
        ledger_count=ledger.count,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(body)
    print(body)
    print(f"written to {OUTPUT}")


if __name__ == "__main__":
    main()
