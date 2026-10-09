#!/usr/bin/env python3
"""Measure the nightly form rating and the starter flag against the price.

    PYTHONPATH=src python scripts/run_nightly_form.py

Runs the three hypotheses registered in `docs/preregistered_nightly_form.md`
on 2022-2025, with 2021 as history only. Spends nothing: the schedules, the
line table and the play-level player files are all free downloads
(`scripts/fetch_ncaaf_data.py --with-player-stats`, `scripts/build_line_table.py`).

Writes `data/outputs/nightly_form.json` (the run record) and renders
`data/outputs/nightly_form.md` from it.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from ncaaf_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.data.starters import load_starters, state_before
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.models import form
from ncaaf_betting_lab.ratings_residual import regress

HISTORY_SEASONS = (2021, 2022, 2023, 2024, 2025)
PRICED_SEASONS = (2022, 2023, 2024, 2025)

#: The ledger stood at 92 when the study was registered; its three hypotheses
#: make 95. Pinned, so a later ledger entry cannot move this study's intervals.
FAMILY = 95
CRITICAL = NormalDist().inv_cdf(1 - (0.05 / FAMILY) / 2)
Z_POWER = NormalDist().inv_cdf(0.80)

#: A starter flag pays at a coefficient of this many points, registered.
QB_PAYING_POINTS = -1.5

LEAGUE_DAY = NCAAF.timezone
RECORD = OUTPUTS_DIR / "nightly_form.json"
REPORT = OUTPUTS_DIR / "nightly_form.md"


def league_day_start(kickoff: datetime) -> datetime:
    """Midnight Eastern on the kickoff's Eastern date, in UTC."""
    local = kickoff.astimezone(LEAGUE_DAY).date()
    return datetime.combine(local, time(0, 0), LEAGUE_DAY).astimezone(timezone.utc)


def load_games() -> pd.DataFrame:
    games = []
    for season in HISTORY_SEASONS:
        games.extend(rateable_games(load_schedule(NCAAF, RAW_DIR, season=season)))
    return form.games_frame(games)


def attach_lines(frame: pd.DataFrame) -> pd.DataFrame:
    lines = pd.read_csv(PROCESSED_DIR / "line_table.csv", dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].set_index("game_id")
    frame = frame.join(spreads[["close_consensus", "open_consensus"]], on="game_id")
    # The spread is the HOME handicap; the price's forecast of the home margin
    # is its negative (`docs/preregistered_opener_study.md`, 0.1).
    frame["implied_close"] = -frame["close_consensus"]
    frame["implied_open"] = -frame["open_consensus"]
    return frame


def form_margins(frame: pd.DataFrame) -> pd.Series:
    """Each priced game's form margin, fitted on earlier league days only."""
    out = pd.Series(np.nan, index=frame.index)
    priced = frame[frame["season"].isin(PRICED_SEASONS)]
    days = priced.groupby(priced["kickoff"].map(league_day_start))
    for as_of, games in days:
        season = int(games["season"].iloc[0])
        ratings = form.fit(frame, season=season, as_of=as_of)
        if ratings is None:
            continue
        for i, game in games.iterrows():
            value = ratings.margin(game["home"], game["away"], neutral=game["neutral"])
            if value is not None:
                out[i] = value
    return out


def qb_flags(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict]:
    """`qb_changed` for each side of each game, knowable before kickoff."""
    home_flag = pd.Series(np.nan, index=frame.index)
    away_flag = pd.Series(np.nan, index=frame.index)
    coverage = {"team_games": 0, "matched": 0}
    for season in HISTORY_SEASONS:
        starters = load_starters(NCAAF, RAW_DIR, season=season)
        by_game = {
            (row.game_id, row.team): row.player_id for row in starters.itertuples()
        }
        history: dict[str, list[str]] = defaultdict(list)
        season_games = frame[frame["season"] == season].sort_values("kickoff")
        for i, game in season_games.iterrows():
            for side, flags in (("home", home_flag), ("away", away_flag)):
                team = game[side]
                changed = state_before(history[team]).qb_changed
                flags[i] = np.nan if changed is None else float(changed)
            for side in ("home", "away"):
                coverage["team_games"] += 1
                starter = by_game.get((game["game_id"], game[f"{side}_name"]), "")
                coverage["matched"] += bool(starter)
                history[game[side]].append(starter)
    return home_flag, away_flag, coverage


def cluster_key(frame: pd.DataFrame) -> pd.Series:
    """(season, season_type, week) as one integer per season: postseason week
    1 is not regular-season week 1."""
    return frame["week"] + np.where(frame["season_type"] == "postseason", 100, 0)


def measure(frame: pd.DataFrame, x: str, y: str, label: str) -> dict:
    data = frame.dropna(subset=[x, y])
    data = pd.DataFrame(
        {
            "season": data["season"],
            "week": cluster_key(data),
            "disagree": data[x],
            "resid": data[y],
        }
    )
    test = regress(data, label)
    late = data[data["season"] == 2025]
    test_2025 = regress(late, label + " (2025)")
    half = CRITICAL * test.standard_error
    return {
        "label": label,
        "games": int(len(data)),
        "clusters": int(data.groupby(["season", "week"]).ngroups),
        "slope": test.slope,
        "standard_error": test.standard_error,
        "interval": [test.slope - half, test.slope + half],
        "detectable": (CRITICAL + Z_POWER) * test.standard_error,
        "regressor_sd": float(data["disagree"].std()),
        "regressor_nonzero": int((data["disagree"] != 0).sum()),
        "slope_2025": test_2025.slope,
        "games_2025": int(len(late)),
    }


def main() -> None:
    frame = attach_lines(load_games())
    frame["form_margin"] = form_margins(frame)
    frame["disagree_close"] = frame["form_margin"] - frame["implied_close"]
    frame["disagree_open"] = frame["form_margin"] - frame["implied_open"]
    frame["resid_close"] = frame["margin"] - frame["implied_close"]
    frame["resid_open"] = frame["margin"] - frame["implied_open"]
    home_flag, away_flag, coverage = qb_flags(frame)
    frame["qb_signed"] = home_flag - away_flag
    priced = frame[frame["season"].isin(PRICED_SEASONS)]

    results = {
        "form-ratings-vs-close": measure(priced, "disagree_close", "resid_close", "form ratings vs close"),
        "form-ratings-vs-open": measure(priced, "disagree_open", "resid_open", "form ratings vs open"),
        "qb-change-vs-close": measure(priced, "qb_signed", "resid_close", "QB change vs close"),
    }
    for key in ("form-ratings-vs-close", "form-ratings-vs-open"):
        r = results[key]
        r["paying"] = 1.5 / (1.28 * r["regressor_sd"])
        r["direction"] = "positive"
    results["qb-change-vs-close"]["paying"] = QB_PAYING_POINTS
    results["qb-change-vs-close"]["direction"] = "negative"

    with_form = priced.dropna(subset=["form_margin", "implied_close"])
    record = {
        "measured_on": datetime.now(timezone.utc).date().isoformat(),
        "family": FAMILY,
        "critical_value": CRITICAL,
        "seasons": list(PRICED_SEASONS),
        "constants": {
            "half_life_weeks": form.HALF_LIFE_WEEKS,
            "offseason_weeks": form.OFFSEASON_WEEKS,
            "margin_cap": form.MARGIN_CAP,
            "ridge": form.RIDGE,
            "minimum_history": form.MINIMUM_HISTORY,
        },
        "forecast": {
            "games": int(len(with_form)),
            "mae_form": float((with_form["margin"] - with_form["form_margin"]).abs().mean()),
            "mae_close": float((with_form["margin"] - with_form["implied_close"]).abs().mean()),
            "corr_form_close": float(with_form["form_margin"].corr(with_form["implied_close"])),
        },
        "starter_coverage": coverage,
        "flagged_team_games": int(((home_flag == 1) | (away_flag == 1))[priced.index].sum()),
        "results": results,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    body = render(record)
    REPORT.write_text(body)
    print(body)


def verdict(r: dict) -> dict:
    low, high = r["interval"]
    positive = r["direction"] == "positive"
    registered_side = low > 0 if positive else high < 0
    excludes = low > 0 or high < 0
    sign_2025 = r["slope_2025"] > 0 if positive else r["slope_2025"] < 0
    powered = r["detectable"] <= abs(r["paying"])
    rules_out_paying = high < r["paying"] if positive else low > r["paying"]
    return {
        "excludes_zero": excludes,
        "registered_side": registered_side,
        "sign_2025": sign_2025,
        "powered": powered,
        "rules_out_paying": rules_out_paying,
        "ships": registered_side and sign_2025 and powered,
    }


def render(record: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Does a rating that learns from last night beat the price?")
    add("")
    add(
        "Registered before it ran in `docs/preregistered_nightly_form.md`. "
        f"Seasons {record['seasons'][0]}-{record['seasons'][-1]} priced, 2021 as "
        f"history. Every interval is at the Bonferroni critical value for "
        f"**{record['family']} hypotheses** ({record['critical_value']:.2f}, not "
        "1.96), clustered by season, season type and week."
    )
    add("")
    add("| Hypothesis | Games | Slope | 95% interval (corrected) | Detects | Pays at | 2025 alone | Reading |")
    add("|:---|---:|---:|:---|---:|---:|---:|:---|")
    for key, r in record["results"].items():
        v = verdict(r)
        low, high = r["interval"]
        if v["ships"]:
            reading = "**clears every registered bar**"
        elif v["excludes_zero"] and not v["registered_side"]:
            reading = "interval excludes zero on the **wrong** side"
        elif not v["excludes_zero"]:
            reading = "**no demonstrated edge**"
        else:
            reading = "registered side, but fails the 2025 or power bar"
        if v["rules_out_paying"]:
            reading += "; the interval rules out what pays"
        elif not v["powered"]:
            reading += "; underpowered, so what pays is not ruled out"
        add(
            f"| `{key}` | {r['games']:,} | {r['slope']:+.4f} | "
            f"[{low:+.4f}, {high:+.4f}] | {r['detectable']:.3f} | "
            f"{r['paying']:+.3f} | {r['slope_2025']:+.4f} (n = {r['games_2025']:,}) | {reading} |"
        )
    add("")
    f = record["forecast"]
    add(
        f"**As a forecaster**, over {f['games']:,} games the form rating's mean "
        f"absolute error on the margin is **{f['mae_form']:.2f} points** against "
        f"the closing line's **{f['mae_close']:.2f}**; the two correlate at "
        f"{f['corr_form_close']:+.3f}."
    )
    add("")
    c = record["starter_coverage"]
    q = record["results"]["qb-change-vs-close"]
    add(
        f"**Starter coverage.** {c['matched']:,} of {c['team_games']:,} "
        f"team-games 2021-2025 matched a starter in the play-level file. "
        f"{record['flagged_team_games']:,} priced team-games carried a "
        f"quarterback change, and {q['regressor_nonzero']:,} of {q['games']:,} "
        "games had a change on exactly one side, which is all the starter test "
        "can learn from."
    )
    add("")
    ships = [k for k, r in record["results"].items() if verdict(r)["ships"]]
    add("## What this means for the card")
    add("")
    if ships:
        add(
            "Cleared every registered bar: " + ", ".join(f"`{k}`" for k in ships)
            + ". That earns a proposal to put it into the price, made separately "
            "and reviewed, not a silent change here."
        )
    else:
        add(
            "**Nothing cleared the registered bars, so nothing enters the price.** "
            "The rating and the starter flag go on the card as context beside the "
            "consensus line, and the probabilities stay anchored on it. A rating "
            "that learns nightly is a description of how teams are playing; this "
            "table says the closing price already carries it."
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
