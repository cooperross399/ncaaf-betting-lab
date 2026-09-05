"""H1 of the opener study: does rating-vs-OPEN disagreement predict the LINE MOVE?

    PYTHONPATH=src .venv/bin/python scripts/run_opener_h1_line_move.py

Pre-registered in docs/preregistered_opener_study.md before any slope was
computed. This script measures one hypothesis and fits nothing of its own: the
ratings come from `ratings_residual.fit_ratings` and the slope and its
cluster-robust standard error come from `ratings_residual.regress`, both reused
exactly as Step 5 ran them.

In home-margin space throughout:

    forecast_open  = -open_consensus     # the opener's forecast of home margin
    forecast_close = -close_consensus    # the close's forecast of home margin
    market_move    = forecast_close - forecast_open = -line_move
    disagree_open  = rating_margin - forecast_open

and the regression is `market_move` on `disagree_open`, clustered by
(season, week). A POSITIVE slope means the market moved TOWARD the ratings.

THIS IS A CLV QUESTION, NOT A PROFIT QUESTION. There is no price on the move in
this data. A positive slope would show the ratings anticipate the market's own
revision; beating the close is necessary for profit and is not sufficient, and
no result here may be written up as an edge.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.experiment_ledger import load as load_ledger
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.ratings_residual import (
    MINIMUM_HISTORY,
    Z_POWER,
    fit_ratings,
    regress,
)

SEASONS = (2021, 2022, 2023, 2024, 2025)
LINES = Path("data/processed/line_table.csv")
#: This study records four hypotheses of its own; the pre-registration fixes
#: every interval here at the INCLUSIVE count (78 + 4 = 82).
THIS_STUDY_HYPOTHESES = 4


def check_conventions(spreads: pd.DataFrame) -> None:
    """Re-verify the sign conventions on this run's own data. Never assumed."""
    have_open = spreads.dropna(subset=["open_consensus", "line_move"])
    print("-- sign conventions, re-checked on this run --")
    print(
        f"corr(-close_consensus, margin) = "
        f"{np.corrcoef(-spreads['close_consensus'], spreads['margin'])[0, 1]:+.4f}"
        f", n = {len(spreads):,}"
    )
    print(
        f"corr(-open_consensus, margin)  = "
        f"{np.corrcoef(-have_open['open_consensus'], have_open['margin'])[0, 1]:+.4f}"
        f", n = {len(have_open):,}"
    )
    print(
        f"mean(margin - (-open_consensus)) = "
        f"{(have_open['margin'] + have_open['open_consensus']).mean():+.4f} pts"
        f", n = {len(have_open):,}"
    )
    recomputed = have_open["close_consensus"] - have_open["open_consensus"]
    mismatches = int((np.abs(recomputed - have_open["line_move"]) > 1e-9).sum())
    print(
        f"line_move == close_consensus - open_consensus: "
        f"{len(have_open) - mismatches:,} of {len(have_open):,} exact "
        f"({mismatches} mismatches)"
    )
    print(
        f"sd(line_move) = {have_open['line_move'].std():.4f} pts, "
        f"n = {len(have_open):,}; "
        f"positive {int((have_open['line_move'] > 0).sum()):,}, "
        f"negative {int((have_open['line_move'] < 0).sum()):,}, "
        f"zero {int((have_open['line_move'] == 0).sum()):,}"
    )
    print(
        f"openers missing on {int(spreads['open_consensus'].isna().sum())} of "
        f"{len(spreads):,} spread rows — dropped, never imputed"
    )
    print()


def games_with_prices() -> pd.DataFrame:
    """Step 5's game set, with the opener carried alongside (NaN where absent)."""
    lines = pd.read_csv(LINES, dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].set_index("game_id")
    check_conventions(spreads)
    rows = []
    for season in SEASONS:
        schedule = load_schedule(NCAAF, Path("data/raw"), season=season)
        for game in rateable_games(schedule):
            if not game.has_result or game.game_id not in spreads.index:
                continue
            price = spreads.loc[game.game_id]
            opener = price["open_consensus"]
            rows.append(
                {
                    "season": game.season,
                    "week": game.week,
                    "home": game.home_team,
                    "away": game.away_team,
                    "neutral": game.neutral_site,
                    "margin": float(game.margin),
                    # Both consensus fields are the HOME handicap, so the
                    # price's own forecast of the home margin is its negative.
                    "forecast_close": -float(price["close_consensus"]),
                    "forecast_open": (
                        float("nan") if pd.isna(opener) else -float(opener)
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["season", "week"]).reset_index(drop=True)


def walk_forward(games: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Price each week with ratings fitted strictly on earlier games.

    History is the full close-priced set — identical to Step 5 — so the ratings
    are the same ratings. A game only enters the ANALYSIS if it has an opener.
    """
    rows: list[dict] = []
    dropped_no_opener = 0
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
                if pd.isna(game["forecast_open"]):
                    dropped_no_opener += 1
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
                        # regress() reads "resid" as the left-hand side; here
                        # the left-hand side is the market's own revision.
                        "resid": game["forecast_close"] - game["forecast_open"],
                        "disagree": rating_margin - game["forecast_open"],
                    }
                )
    return pd.DataFrame(rows), dropped_no_opener


def main() -> None:
    games = games_with_prices()
    priced, dropped = walk_forward(games)
    if priced.empty:
        raise SystemExit("no games were priced — an absence, not a null")

    ledger = load_ledger(Path("data/outputs/experiment_ledger.json"))
    # The four are already IN the ledger (recorded 2026-09-05), so extra= would
    # count them twice. It was correct when the ledger stood at 88 and is not now.
    factor = ledger.correction_factor()
    test = regress(priced, "H1 market move on rating-vs-open", correction_factor=factor)
    low, high = test.interval
    sd_disagree = float(priced["disagree"].std())
    sd_move = float(priced["resid"].std())
    floor = (test.critical_value + Z_POWER) * test.standard_error

    print("-- H1: does rating-vs-OPEN disagreement predict the LINE MOVE? --")
    print(f"ledger before this study      : {ledger.count} hypotheses")
    print(
        f"correction applied (inclusive): {ledger.count} "
        f"hypotheses, x{factor:.4f}, critical value {test.critical_value:.4f}"
    )
    print(f"n (games priced, with opener) : {test.games:,}")
    print(f"  dropped for a missing opener: {dropped}")
    print(f"  (season, week) clusters     : {priced.groupby(['season','week']).ngroups}")
    print(f"sd(disagree_open)             : {sd_disagree:.4f} pts, n = {test.games:,}")
    print(f"sd(market_move)               : {sd_move:.4f} pts, n = {test.games:,}")
    print(f"slope                         : {test.slope:+.6f}")
    print(f"cluster-robust SE (by week)   : {test.standard_error:.6f}")
    print(f"95% interval, CORRECTED       : [{low:+.6f}, {high:+.6f}]")
    print(f"excludes zero                 : {test.excludes_zero}")
    print(
        f"detectable floor (80% power)  : {floor:.6f} "
        f"= ({test.critical_value:.4f} + {Z_POWER:.4f}) x {test.standard_error:.6f}"
    )
    print(
        "reading                       : "
        + (
            "interval excludes zero — the market moves "
            + ("TOWARD" if test.slope > 0 else "AWAY FROM")
            + " the ratings"
            if test.excludes_zero
            else "no demonstrated edge"
        )
    )
    top_decile = 1.28 * sd_disagree
    print()
    print(f"-- the same numbers on the scale of points, n = {test.games:,} --")
    print(
        f"top-decile disagreement cutoff = 1.28 x {sd_disagree:.4f} = "
        f"{top_decile:.4f} pts"
    )
    print(f"  slope           {test.slope:+.6f} -> {test.slope * top_decile:+.4f} pts of move there")
    print(f"  interval low    {low:+.6f} -> {low * top_decile:+.4f} pts")
    print(f"  interval high   {high:+.6f} -> {high * top_decile:+.4f} pts")
    print(f"  detectable floor {floor:.6f} -> {floor * top_decile:.4f} pts")
    print(
        "  a HALF-POINT tick of move at the top decile is a slope of "
        f"{0.5 / top_decile:.4f}; a QUARTER-point is {0.25 / top_decile:.4f}"
    )
    print()
    print(
        "CLV, NOT PROFIT. There is no price on the move in this data. Predicting "
        "the move means getting a better number than the close, which is "
        "NECESSARY for profit and NOT SUFFICIENT. Nothing here is an edge, and "
        "no bet is placed or automated."
    )


if __name__ == "__main__":
    main()
