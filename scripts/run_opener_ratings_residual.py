"""H2 (opener-study): does rating-vs-OPEN disagreement predict the RESULT?

The Step 5 instrument with the OPENING line in place of the closing line.

    PYTHONPATH=src .venv/bin/python scripts/run_opener_ratings_residual.py

Pre-registered at docs/preregistered_opener_study.md (2026-09-05), direction
POSITIVE, before any slope was computed.

    forecast_open = -open_consensus          # opener's forecast of home margin
    resid_open    = margin - forecast_open   # the opener's error
    disagree_open = rating_margin - forecast_open

`regress(resid_open on disagree_open)`, clustered by (season, week).

Ratings come from `ratings_residual.fit_ratings` and the slope from
`ratings_residual.regress`, both reused as they stand. Nothing is refitted here.

Two thresholds, both registered in advance:
  * zero-exclusion at the CORRECTED critical value 3.4272 (ledger 78 + this
    study's own 4 = 82, Bonferroni x1.7486);
  * profitable_slope = 1.5 / (1.28 x sd(disagree_open)) -- the same arithmetic
    that produced 0.143 against the close, with the standard deviation measured
    on THIS sample against the OPENER.

Detectable-edge floor: (3.4272 + 0.8416) x SE = 4.2688 x SE, 80% power at the
corrected critical value.

This script MEASURES. It does not write to the experiment ledger (the
adjudicator's job), and it places and automates no bet.
"""

from __future__ import annotations

from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.ratings_residual import (
    MINIMUM_HISTORY,
    fit_ratings,
    regress,
)

SEASONS = (2021, 2022, 2023, 2024, 2025)

#: Registered in docs/preregistered_opener_study.md section 2. NOT read from the
#: live ledger: the pre-registration fixes the value this study is quoted at
#: (ledger 78 before + this study's own 4 = 82, x1.7486), so a later append
#: cannot silently move the bar this study was graded against.
CRITICAL_VALUE = 3.4272
LEDGER_AFTER = 82
CORRECTION_FACTOR = 1.7486

#: z for 80% power. Floor = (CRITICAL_VALUE + Z_POWER) x SE = 4.2688 x SE.
Z_POWER = NormalDist().inv_cdf(0.80)

#: Points of true edge a -110 price needs to clear the vig.
VIG_POINTS = 1.5

#: Top-decile cutoff of a normal disagreement distribution, in sd units.
TOP_DECILE_Z = 1.28


def profitable_slope(disagreement_sd: float) -> float:
    """Slope that would deliver VIG_POINTS at the top decile of disagreement."""
    return VIG_POINTS / (TOP_DECILE_Z * disagreement_sd)


def games_with_an_opener() -> pd.DataFrame:
    """Spread games carrying a result AND an opening price.

    A missing price stays missing: rows without `open_consensus` are dropped
    here and every n downstream is quoted after the drop.
    """
    lines = pd.read_csv("data/processed/line_table.csv", dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].set_index("game_id")
    rows = []
    dropped_no_opener = 0
    for season in SEASONS:
        schedule = load_schedule(NCAAF, Path("data/raw"), season=season)
        for game in rateable_games(schedule):
            if not game.has_result or game.game_id not in spreads.index:
                continue
            row = spreads.loc[game.game_id]
            if pd.isna(row["open_consensus"]):
                dropped_no_opener += 1
                continue
            rows.append(
                {
                    "game_id": game.game_id,
                    "season": game.season,
                    "week": game.week,
                    "home": game.home_team,
                    "away": game.away_team,
                    "neutral": game.neutral_site,
                    "margin": float(game.margin),
                    # VERIFIED: open_consensus is the HOME handicap, same
                    # convention as close_consensus, so the opener's forecast of
                    # the home margin is its NEGATIVE.
                    "implied_open": -float(row["open_consensus"]),
                }
            )
    frame = pd.DataFrame(rows).sort_values(["season", "week"]).reset_index(drop=True)
    frame.attrs["dropped_no_opener"] = dropped_no_opener
    return frame


def walk_forward(games: pd.DataFrame) -> pd.DataFrame:
    """Price each week with ratings fitted strictly on earlier games.

    Identical in structure to scripts/run_ratings_residual.py; the only change
    is that `implied` is the OPENER rather than the close.
    """
    rows = []
    for season in SEASONS[1:]:  # 2021 is burned as history
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
                        "resid": game["margin"] - game["implied_open"],
                        "disagree": rating_margin - game["implied_open"],
                    }
                )
    return pd.DataFrame(rows)


def report_line(label: str, frame: pd.DataFrame, threshold: float) -> dict:
    """One split, measured. Every figure carries its n."""
    test = regress(frame, label, correction_factor=CORRECTION_FACTOR)
    se = test.standard_error
    half = CRITICAL_VALUE * se
    low, high = test.slope - half, test.slope + half
    floor = (CRITICAL_VALUE + Z_POWER) * se
    return {
        "label": label,
        "n": test.games,
        "clusters": frame.groupby(["season", "week"]).ngroups,
        "slope": test.slope,
        "se": se,
        "low": low,
        "high": high,
        "excludes_zero": low > 0.0 or high < 0.0,
        "floor": floor,
        "rules_out_paying": high < threshold,
        "underpowered": floor > threshold,
        "own_sd": float(frame["disagree"].std()),
    }


def main() -> None:
    games = games_with_an_opener()
    print(
        f"spread games with a result and an opener: n = {len(games):,} "
        f"(dropped for a missing opener: {games.attrs['dropped_no_opener']})"
    )
    priced = walk_forward(games)
    if priced.empty:
        raise SystemExit("no games were priced -- an absence, not a null")

    sd_all = float(priced["disagree"].std())
    threshold = profitable_slope(sd_all)

    print()
    print("=== REGISTERED THRESHOLD, computed BEFORE any slope is printed ===")
    print(f"sd(disagree_open)   = {sd_all:.4f} pts, n = {len(priced):,}")
    print(f"top-decile cutoff   = 1.28 x {sd_all:.4f} = {TOP_DECILE_Z * sd_all:.4f} pts")
    print(
        f"profitable_slope    = 1.5 / (1.28 x {sd_all:.4f}) = {threshold:.4f}"
    )
    print(f"critical value      = {CRITICAL_VALUE} (ledger {LEDGER_AFTER}, x{CORRECTION_FACTOR})")
    print(f"detectable floor    = ({CRITICAL_VALUE} + {Z_POWER:.4f}) x SE = {CRITICAL_VALUE + Z_POWER:.4f} x SE")
    print()

    splits = [
        ("all games", priced),
        ("early season (weeks 1-4)", priced[priced["week"] <= 4]),
        ("late season (weeks 5+)", priced[priced["week"] > 4]),
    ]
    results = [report_line(label, frame, threshold) for label, frame in splits]

    print("=== H2: regress(resid_open on disagree_open), clustered by (season, week) ===")
    header = (
        f"{'split':<26} {'n':>6} {'clus':>5} {'slope':>9} {'SE':>8} "
        f"{'corrected 95% interval':>26} {'floor':>8} {'excl 0':>7} {'rules out pay':>14}"
    )
    print(header)
    for r in results:
        print(
            f"{r['label']:<26} {r['n']:>6,} {r['clusters']:>5} {r['slope']:>+9.4f} "
            f"{r['se']:>8.4f} {'[' + format(r['low'], '+.4f') + ', ' + format(r['high'], '+.4f') + ']':>26} "
            f"{r['floor']:>8.4f} {str(r['excludes_zero']):>7} {str(r['rules_out_paying']):>14}"
        )
    print()
    for r in results:
        sd = r["own_sd"]
        own = profitable_slope(sd)
        verdict = (
            "interval EXCLUDES zero"
            if r["excludes_zero"]
            else "no demonstrated edge (interval includes zero)"
        )
        power = (
            f"UNDERPOWERED -- floor {r['floor']:.4f} sits ABOVE the {threshold:.4f} that would pay; "
            "this is an absence, not a finding"
            if r["underpowered"]
            else f"powered -- floor {r['floor']:.4f} sits below the {threshold:.4f} that would pay"
        )
        ruled = (
            f"RULES OUT a paying slope (upper bound {r['high']:+.4f} < {threshold:.4f})"
            if r["rules_out_paying"]
            else f"does NOT rule out a paying slope (upper bound {r['high']:+.4f} >= {threshold:.4f})"
        )
        print(f"{r['label']} (n = {r['n']:,}, {r['clusters']} week clusters):")
        print(f"  {verdict}")
        print(f"  {ruled}")
        print(f"  {power}")
        print(
            f"  split's own sd(disagree_open) = {sd:.4f}, "
            f"its own profitable_slope = {own:.4f}"
        )
        print()

    print("H2 places no bet and automates none. It writes nothing to the ledger.")


if __name__ == "__main__":
    main()
