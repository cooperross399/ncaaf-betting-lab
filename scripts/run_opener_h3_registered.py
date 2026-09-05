#!/usr/bin/env python3
"""H3 AS PRE-REGISTERED, plus the data-integrity audit the study did not run.

    PYTHONPATH=src python scripts/run_opener_h3_registered.py

Two jobs, both belonging to the adjudication rather than to a new search.

**1. The registered H3.** `docs/preregistered_opener_study.md` registers
`segment-heterogeneity` as: run the H2 regression — `resid_open` on
`disagree_open`, cluster-robust by `(season, week)` — separately in
`thin = books <= 2` and `thick = books >= 4`, with `books == 3` EXCLUDED as the
tie, and report `delta = slope_thin - slope_thick` with the two standard errors
added in quadrature. `scripts/run_opener_segment_softness.py` ran a different
statistic (mean absolute line move) over different segments, so the registered
statistic had no measured value. It does now.

**2. The sign-flip audit.** The raw feed carries per-book rows whose home-side
sign disagrees with the rest of the panel on the same game, and whose own
opening and closing numbers are on opposite conventions. `open_consensus` is a
median over whichever books opened, so where the only opener comes from such a
row the resulting `line_move` is roughly `-2 x close_consensus` — a sign error
wearing the costume of a market move. This measures how much of the positive
control rests on those rows.

Measures only. Fits nothing on a game it then prices. Writes nothing to the
ledger, places no bet and automates none.
"""

from __future__ import annotations

from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.ratings_residual import MINIMUM_HISTORY, fit_ratings, regress

SEASONS = (2021, 2022, 2023, 2024, 2025)
LINES = Path("data/processed/line_table.csv")
RAW = Path("data/raw")

#: Fixed by the pre-registration, section 2. Quoted here so the registered
#: hypothesis is graded against the bar that was set before it was run.
CRITICAL_VALUE = 3.4272
Z_POWER = NormalDist().inv_cdf(0.80)
VIG_POINTS = 1.5
TOP_DECILE_Z = 1.28


def profitable_slope(sd: float) -> float:
    return VIG_POINTS / (TOP_DECILE_Z * sd)


def priced_games() -> pd.DataFrame:
    """Spread games with a result and an opener, carrying `books`.

    Identical to scripts/run_opener_ratings_residual.py's set — a missing price
    stays missing, so the seven openerless rows are dropped and every n below
    is quoted after the drop.
    """
    lines = pd.read_csv(LINES, dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].set_index("game_id")
    rows, dropped = [], 0
    for season in SEASONS:
        for game in rateable_games(load_schedule(NCAAF, RAW, season=season)):
            if not game.has_result or game.game_id not in spreads.index:
                continue
            row = spreads.loc[game.game_id]
            if pd.isna(row["open_consensus"]):
                dropped += 1
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
                    "books": int(row["books"]),
                    # open_consensus is the HOME handicap, so the opener's
                    # forecast of the home margin is its NEGATIVE.
                    "implied_open": -float(row["open_consensus"]),
                }
            )
    frame = pd.DataFrame(rows).sort_values(["season", "week"]).reset_index(drop=True)
    frame.attrs["dropped_no_opener"] = dropped
    return frame


def walk_forward(games: pd.DataFrame) -> pd.DataFrame:
    """Price each week with ratings fitted strictly on earlier games."""
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
                        "books": int(game["books"]),
                        "resid": game["margin"] - game["implied_open"],
                        "disagree": rating_margin - game["implied_open"],
                    }
                )
    return pd.DataFrame(rows)


def arm(frame: pd.DataFrame, label: str) -> dict:
    test = regress(frame, label, correction_factor=1.0)
    sd = float(frame["disagree"].std())
    half = CRITICAL_VALUE * test.standard_error
    return {
        "label": label,
        "n": len(frame),
        "clusters": frame.groupby(["season", "week"]).ngroups,
        "slope": test.slope,
        "se": test.standard_error,
        "low": test.slope - half,
        "high": test.slope + half,
        "floor": (CRITICAL_VALUE + Z_POWER) * test.standard_error,
        "sd": sd,
        "pay": profitable_slope(sd),
    }


def show(a: dict) -> None:
    print(
        f"  {a['label']:<26} n = {a['n']:>5,}  clusters = {a['clusters']:>3}  "
        f"slope = {a['slope']:+.4f}  SE = {a['se']:.4f}"
    )
    print(
        f"  {'':<26} corrected interval [{a['low']:+.4f}, {a['high']:+.4f}]  "
        f"floor {a['floor']:.4f}  sd(disagree_open) {a['sd']:.4f}  "
        f"profitable_slope {a['pay']:.4f}"
    )


def registered_h3(priced: pd.DataFrame) -> None:
    print("=" * 78)
    print("H3 AS PRE-REGISTERED — segment-heterogeneity")
    print("thin = books <= 2, thick = books >= 4, books == 3 EXCLUDED as the tie")
    print("statistic: delta = slope_thin - slope_thick, SEs added in quadrature")
    print("direction fixed in advance: POSITIVE. critical value", CRITICAL_VALUE)
    print("=" * 78)
    thin = arm(priced[priced["books"] <= 2], "thin (books <= 2)")
    thick = arm(priced[priced["books"] >= 4], "thick (books >= 4)")
    tie = priced[priced["books"] == 3]
    show(thin)
    show(thick)
    print(
        f"  excluded tie (books == 3): n = {len(tie):,} over "
        f"{tie.groupby(['season', 'week']).ngroups} clusters — in neither arm"
    )
    for name, a in (("thin", thin), ("thick", thick)):
        by_season = (
            priced[priced["books"] <= 2 if name == "thin" else priced["books"] >= 4]
            .groupby("season")
            .size()
            .to_dict()
        )
        print(f"  {name} arm by season: {by_season}")

    delta = thin["slope"] - thick["slope"]
    se = float(np.sqrt(thin["se"] ** 2 + thick["se"] ** 2))
    half = CRITICAL_VALUE * se
    low, high = delta - half, delta + half
    floor = (CRITICAL_VALUE + Z_POWER) * se
    print()
    print(f"  DELTA = slope_thin - slope_thick = {delta:+.4f}")
    print(f"  quadrature SE = sqrt({thin['se']:.4f}^2 + {thick['se']:.4f}^2) = {se:.4f}")
    print(f"  corrected interval at {CRITICAL_VALUE}: [{low:+.4f}, {high:+.4f}]")
    excludes = low > 0 or high < 0
    print(f"  excludes zero: {excludes}")
    print(f"  sign as registered (POSITIVE): {delta > 0}")
    print(f"  DETECTABLE FLOOR (80% power, corrected) = {floor:.4f}")
    print(
        f"  thin arm's own profitable_slope = {thin['pay']:.4f}; "
        f"floor {thin['floor']:.4f} -> "
        f"{'ABSENCE (floor above what would pay)' if thin['floor'] > thin['pay'] else 'powered'}"
    )
    print(
        f"  delta floor {floor:.4f} vs thin arm's profitable_slope {thin['pay']:.4f} -> "
        f"{'ABSENCE' if floor > thin['pay'] else 'powered'}"
    )
    if not excludes:
        print("  READING: no demonstrated edge (interval includes zero)")
    print(
        "  Twenty-five-ish clusters is below the 30-50 a cluster-robust SE needs; "
        "the quadrature SE also assumes the arms are independent, which games "
        "sharing a week make only approximately true. Reported with that caveat, "
        "not quoted clean."
    )


def flip_audit() -> None:
    print()
    print("=" * 78)
    print("DATA-INTEGRITY AUDIT — per-book sign disagreement in the raw feed")
    print("=" * 78)
    lt = pd.read_csv(LINES, dtype={"game_id": str})
    spread = lt[lt["market"] == "spread"].set_index("game_id")
    raw = pd.read_csv(
        RAW / NCAAF.data_dir_segment / "betting" / "cfb_line_odds.csv.gz", low_memory=False
    )
    raw["game_id"] = (
        pd.to_numeric(raw["game_id"], errors="coerce").astype("Int64").astype(str)
    )
    raw["abbr"] = raw["abbr"].astype(str).str.strip()
    raw = raw[(raw["market_type"] == "spread") & raw["game_id"].isin(spread.index)]
    raw = raw.merge(
        spread[["home_team", "close_consensus"]], left_on="game_id", right_index=True
    )
    home = raw[raw["abbr"] == raw["home_team"]].copy()
    home["c"] = pd.to_numeric(home["lines"], errors="coerce")
    home["o"] = pd.to_numeric(home["opening_lines"], errors="coerce")

    internal = home.dropna(subset=["o", "c"])
    internal = internal[(internal["o"].abs() >= 3) & (internal["c"].abs() >= 3)]
    bad_internal = internal[np.sign(internal["o"]) != np.sign(internal["c"])]
    print(
        f"  (A) book-rows whose OWN open and close carry opposite signs "
        f"(both |.| >= 3): {len(bad_internal):,} of {len(internal):,} rows, on "
        f"{bad_internal['game_id'].nunique()} distinct games"
    )

    panel = home.dropna(subset=["c"])
    panel = panel[panel["close_consensus"].abs() >= 3]
    flipped = ((panel["c"] + panel["close_consensus"]).abs() + 1.0) < (
        panel["c"] - panel["close_consensus"]
    ).abs()
    panel = panel.assign(flip=flipped)
    print(
        f"  (B) book-rows whose CLOSE is on the opposite convention to the rest "
        f"of the panel: {int(panel['flip'].sum()):,} of {len(panel):,}, on "
        f"{panel[panel['flip']]['game_id'].nunique()} distinct games"
    )

    openers = panel.dropna(subset=["o"])
    only_flipped = sorted(
        gid for gid, g in openers.groupby("game_id") if bool(g["flip"].all())
    )
    print(
        f"  (C) games whose opener comes ONLY from a sign-flipped book row: "
        f"{len(only_flipped)}  -> {only_flipped}"
    )
    suspect = set(only_flipped) | set(bad_internal["game_id"])
    have = spread.dropna(subset=["open_consensus", "line_move"])
    suspect = sorted(suspect & set(have.index))
    print(
        f"  SUSPECT SET = (A) union (C) = {len(suspect)} of {len(have):,} spread "
        f"games with an opener ({len(suspect) / len(have):.2%})"
    )
    sus = have.loc[suspect]
    keep = have.loc[~have.index.isin(suspect)]
    print(
        f"    mean |line_move|  suspect {sus['line_move'].abs().mean():.3f} pts "
        f"(n = {len(sus)})   rest {keep['line_move'].abs().mean():.3f} pts "
        f"(n = {len(keep):,})"
    )
    print(
        f"    sd(line_move)     all {have['line_move'].std():.4f} "
        f"(n = {len(have):,})   rest {keep['line_move'].std():.4f} (n = {len(keep):,})"
    )

    def control(frame: pd.DataFrame) -> tuple[float, float, int, int]:
        eo = (frame["margin"] + frame["open_consensus"]) ** 2
        ec = (frame["margin"] + frame["close_consensus"]) ** 2
        d = (eo - ec).to_numpy(dtype=float)
        mean = float(d.mean())
        grouped = frame.assign(_d=d - mean).groupby(["season", "week"])
        meat = sum(float(g["_d"].sum()) ** 2 for _, g in grouped)
        return mean, float(np.sqrt(meat)) / len(frame), len(frame), grouped.ngroups

    print()
    print("  THE POSITIVE CONTROL, RE-RUN WITH THE SUSPECT ROWS DROPPED")
    for label, frame in (("as published (all)", have), ("suspect rows dropped", keep)):
        d, se, n, g = control(frame)
        half = CRITICAL_VALUE * se
        floor = (CRITICAL_VALUE + Z_POWER) * se
        print(
            f"    {label:<24} D = {d:+.4f} pts^2  SE {se:.4f}  n = {n:,}  "
            f"clusters {g}  interval [{d - half:+.4f}, {d + half:+.4f}]  "
            f"excludes zero: {d - half > 0}  floor {floor:.4f}  z = {d / se:.4f}"
        )
    d_s, se_s, n_s, _ = control(sus)
    print(
        f"    {'the suspect rows alone':<24} D = {d_s:+.4f} pts^2  n = {n_s}  "
        f"— {len(sus)} games carrying "
        f"{d_s * n_s / (control(have)[0] * len(have)):.1%} of the pooled D"
    )


def main() -> None:
    games = priced_games()
    print(
        f"spread games with a result and an opener: n = {len(games):,} "
        f"(dropped for a missing opener: {games.attrs['dropped_no_opener']})"
    )
    priced = walk_forward(games)
    print(
        f"walk-forward priced set: n = {len(priced):,} over "
        f"{priced.groupby(['season', 'week']).ngroups} (season, week) clusters"
    )
    print(
        f"books distribution in the priced set: "
        f"{priced['books'].value_counts().sort_index().to_dict()}"
    )
    print()
    registered_h3(priced)
    flip_audit()
    print()
    print("No bet was placed and none was automated. Nothing was written to the ledger.")


if __name__ == "__main__":
    main()
