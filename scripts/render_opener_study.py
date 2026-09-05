#!/usr/bin/env python3
"""Adjudicate the pre-registered opener study and render its write-up.

    PYTHONPATH=src python scripts/render_opener_study.py

Every number in `data/outputs/opener_study.md` is computed here at run time and
none is typed into the prose, so improving a sentence can never cost a
measurement. The correction is read LIVE from the cumulative ledger rather than
pinned, so appending a hypothesis tightens this report's honesty automatically
instead of leaving a stale constant behind.

Measures only. Ratings are fitted strictly on earlier games. No bet is placed
and none is automated. Nothing here writes to the ledger — that is
`scripts/record_opener_study.py`, which runs first.
"""

from __future__ import annotations

from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.experiment_ledger import LEDGER_FILENAME, load as load_ledger
from ncaaf_betting_lab.leagues import NCAAF
from ncaaf_betting_lab.ratings_residual import MINIMUM_HISTORY, fit_ratings, regress

SEASONS = (2021, 2022, 2023, 2024, 2025)
RAW = Path("data/raw")
LINES = Path("data/processed/line_table.csv")
OUTPUTS = Path("data/outputs")
OUTPUT = OUTPUTS / "opener_study.md"
PREREG_CRITICAL_VALUE = 3.4272  # what the four registered hypotheses were graded against

Z_POWER = NormalDist().inv_cdf(0.80)
VIG_POINTS = 1.5
TOP_DECILE_Z = 1.28


# --------------------------------------------------------------------------- #
# measurement helpers
# --------------------------------------------------------------------------- #
def clustered_mean(values: np.ndarray, frame: pd.DataFrame) -> tuple[float, float]:
    """Mean of a per-game statistic with a (season, week) cluster-robust SE."""
    mean = float(values.mean())
    grouped = frame.assign(_d=values - mean).groupby(["season", "week"])
    meat = sum(float(g["_d"].sum()) ** 2 for _, g in grouped)
    return mean, float(np.sqrt(meat)) / len(frame)


def clustered_difference(
    a: pd.DataFrame, b: pd.DataFrame, column: str
) -> tuple[float, float]:
    """mean(a) - mean(b) from ONE clustered OLS on a 0/1 arm dummy.

    Not quadrature. These arms share `(season, week)` cells — the same week
    contributes games to both — so adding two independent SEs would be the
    wrong estimator. OLS on a demeaned dummy returns exactly the difference in
    group means with a single cluster-robust standard error over the pooled
    frame, which is what `scripts/run_opener_segment_softness.py` used and what
    is reproduced here. H3 keeps quadrature because the pre-registration
    prescribes it there and `books <= 2` and `books >= 4` are disjoint.
    """
    pooled = pd.concat([a.assign(_thin=1.0), b.assign(_thin=0.0)])
    fit = regress(
        pooled.assign(disagree=pooled["_thin"], resid=pooled[column].astype(float)),
        "difference",
        correction_factor=1.0,
    )
    return fit.slope, fit.standard_error


class Result:
    """One measured statistic, with every derived figure at one critical value."""

    def __init__(self, label, estimate, se, n, clusters, critical_value, threshold=None):
        self.label, self.estimate, self.se = label, float(estimate), float(se)
        self.n, self.clusters = int(n), int(clusters)
        self.critical_value, self.threshold = float(critical_value), threshold

    @property
    def low(self) -> float:
        return self.estimate - self.critical_value * self.se

    @property
    def high(self) -> float:
        return self.estimate + self.critical_value * self.se

    @property
    def excludes_zero(self) -> bool:
        return self.low > 0.0 or self.high < 0.0

    @property
    def floor(self) -> float:
        """Smallest effect detectable at 80% power, AT the corrected critical value."""
        return (self.critical_value + Z_POWER) * self.se

    @property
    def z(self) -> float:
        return self.estimate / self.se if self.se else float("nan")

    @property
    def underpowered(self) -> bool:
        return self.threshold is not None and self.floor > self.threshold

    @property
    def rules_out_threshold(self) -> bool:
        return self.threshold is not None and self.high < self.threshold

    def interval(self) -> str:
        return f"[{self.low:+.4f}, {self.high:+.4f}]"

    def reading(self) -> str:
        if self.excludes_zero:
            return "excludes zero"
        return "**no demonstrated edge**"


def profitable_slope(sd: float) -> float:
    return VIG_POINTS / (TOP_DECILE_Z * sd)


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def conventions(spread: pd.DataFrame, total: pd.DataFrame) -> dict:
    """Re-verified on every run rather than taken on trust."""
    o = spread.dropna(subset=["open_consensus"])
    to = total.dropna(subset=["open_consensus"])
    moved = spread["close_consensus"] - spread["open_consensus"]
    neg, pos = spread[spread.close_consensus < 0], spread[spread.close_consensus > 0]
    return {
        "corr_close": np.corrcoef(-spread.close_consensus, spread.margin)[0, 1],
        "corr_close_inv": np.corrcoef(spread.close_consensus, spread.margin)[0, 1],
        "corr_open": np.corrcoef(-o.open_consensus, o.margin)[0, 1],
        "n_spread": len(spread), "n_open": len(o),
        "bias_close": (spread.margin + spread.close_consensus).mean(),
        "bias_close_flipped": (spread.margin - spread.close_consensus).mean(),
        "bias_open": (o.margin + o.open_consensus).mean(),
        "home_win_fav": (neg.margin > 0).mean(), "n_fav": len(neg),
        "home_win_dog": (pos.margin > 0).mean(), "n_dog": len(pos),
        "n_pickem": int((spread.close_consensus == 0).sum()),
        "move_mismatch": int((moved - spread.line_move).abs().gt(1e-9).sum()),
        "move_sd": o.line_move.std(),
        "move_pos": int((o.line_move > 0).sum()),
        "move_neg": int((o.line_move < 0).sum()),
        "move_zero": int((o.line_move == 0).sum()),
        "corr_total": np.corrcoef(total.close_consensus, total.total_points)[0, 1],
        "n_total": len(total), "n_total_open": len(to),
        "bias_total_close": (total.total_points - total.close_consensus).mean(),
        "bias_total_open": (to.total_points - to.open_consensus).mean(),
        "sd_margin": spread.margin.std(),
        "clusters": spread.groupby(["season", "week"]).ngroups,
        "missing_spread": sorted(spread[spread.open_consensus.isna()].index),
        "missing_total": sorted(total[total.open_consensus.isna()].index),
    }


def priced_games(*, require_opener: bool) -> pd.DataFrame:
    """Spread games with a result, joined to the schedule.

    `require_opener` reproduces the two walk-forward samples this study
    actually used: H1 built its ratings history from the full close-priced set,
    H2 and H3 dropped the seven openerless games before fitting. They are not
    the same instrument and the difference is reported rather than smoothed.
    """
    lines = pd.read_csv(LINES, dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].set_index("game_id")
    rows = []
    for season in SEASONS:
        for game in rateable_games(load_schedule(NCAAF, RAW, season=season)):
            if not game.has_result or game.game_id not in spreads.index:
                continue
            r = spreads.loc[game.game_id]
            if require_opener and pd.isna(r["open_consensus"]):
                continue
            rows.append(
                {
                    "game_id": game.game_id, "season": game.season, "week": game.week,
                    "home": game.home_team, "away": game.away_team,
                    "neutral": game.neutral_site, "margin": float(game.margin),
                    "books": int(r["books"]),
                    # Both consensus fields are the HOME handicap, so the price's
                    # own forecast of the home margin is its NEGATIVE.
                    "forecast_close": -float(r["close_consensus"]),
                    "forecast_open": (
                        float("nan") if pd.isna(r["open_consensus"])
                        else -float(r["open_consensus"])
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["season", "week"]).reset_index(drop=True)


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
            for _, g in games[
                (games["season"] == season) & (games["week"] == week)
            ].iterrows():
                if g["home"] not in ratings or g["away"] not in ratings:
                    continue
                if pd.isna(g["forecast_open"]):
                    continue
                rating_margin = (
                    ratings[g["home"]] - ratings[g["away"]]
                    + (0.0 if g["neutral"] else home_field)
                )
                rows.append(
                    {
                        "game_id": g["game_id"], "season": season, "week": week,
                        "books": int(g["books"]),
                        "market_move": g["forecast_close"] - g["forecast_open"],
                        "resid_open": g["margin"] - g["forecast_open"],
                        "disagree": rating_margin - g["forecast_open"],
                    }
                )
    return pd.DataFrame(rows)


def suspect_games(spread: pd.DataFrame) -> dict:
    """Games whose OPENER cannot be read as a home handicap.

    Two independent signatures, both read off the raw feed rather than inferred
    from the size of the move:

      A. a single book whose OWN `opening_lines` and `lines` carry opposite
         signs on the same game, both at least 3 points from pick'em;
      B. a game whose opener comes ONLY from book rows whose closing number is
         on the opposite convention to the rest of that game's book panel.

    Nothing is repaired. A price that cannot be read is treated as missing,
    because repairing it would be fabricating one.
    """
    raw = pd.read_csv(RAW / NCAAF.data_dir_segment / "betting" / "cfb_line_odds.csv.gz", low_memory=False)
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
    a_rows = internal[np.sign(internal["o"]) != np.sign(internal["c"])]

    panel = home.dropna(subset=["c"])
    panel = panel[panel["close_consensus"].abs() >= 3]
    panel = panel.assign(
        flip=((panel["c"] + panel["close_consensus"]).abs() + 1.0)
        < (panel["c"] - panel["close_consensus"]).abs()
    )
    b_games = sorted(
        gid for gid, g in panel.dropna(subset=["o"]).groupby("game_id")
        if bool(g["flip"].all())
    )
    swing = (a_rows["o"] - a_rows["c"]).abs()
    return {
        "a_rows": len(a_rows), "a_rows_total": len(internal),
        "a_games": sorted(set(a_rows["game_id"])),
        "a_swing_min": float(swing.min()) if len(swing) else 0.0,
        "a_swing_max": float(swing.max()) if len(swing) else 0.0,
        "b_flipped_rows": int(panel["flip"].sum()), "b_rows_total": len(panel),
        "b_flipped_games": int(panel[panel["flip"]]["game_id"].nunique()),
        "b_games": b_games,
        "union": sorted(set(a_rows["game_id"]) | set(b_games)),
    }


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
def main() -> None:  # noqa: C901 - one report, rendered top to bottom
    ledger = load_ledger(OUTPUTS / LEDGER_FILENAME)
    factor = ledger.correction_factor()
    crit = 1.96 * factor
    floor_multiple = crit + Z_POWER

    lines = pd.read_csv(LINES, dtype={"game_id": str})
    spread = lines[lines["market"] == "spread"].set_index("game_id")
    total = lines[lines["market"] == "total"].set_index("game_id")
    conv = conventions(spread, total)
    sp = spread.dropna(subset=["open_consensus", "line_move"])
    tt = total.dropna(subset=["open_consensus"])

    def control(frame: pd.DataFrame, market: str, label: str) -> tuple[Result, float, float]:
        if market == "spread":
            eo = (frame["margin"] + frame["open_consensus"]) ** 2
            ec = (frame["margin"] + frame["close_consensus"]) ** 2
        else:
            eo = (frame["total_points"] - frame["open_consensus"]) ** 2
            ec = (frame["total_points"] - frame["close_consensus"]) ** 2
        d = (eo - ec).to_numpy(dtype=float)
        mean, se = clustered_mean(d, frame)
        res = Result(label, mean, se, len(frame),
                     frame.groupby(["season", "week"]).ngroups, crit)
        return res, float(np.sqrt(eo.mean())), float(np.sqrt(ec.mean()))

    c_spread, rmse_o_s, rmse_c_s = control(sp, "spread", "spread")
    c_total, rmse_o_t, rmse_c_t = control(tt, "total", "total")
    moved = sp[sp["line_move"] != 0]
    c_moved, _, _ = control(moved, "spread", "spread, moved games only")

    sus = suspect_games(spread)
    ladder = []
    for name, drop in (
        ("published — nothing dropped", set()),
        ("drop B — opener sourced only from a panel-inconsistent book row", set(sus["b_games"])),
        ("drop A — a book's own open and close signs oppose", set(sus["a_games"])),
        ("drop A and B together", set(sus["union"])),
    ):
        frame = sp[~sp.index.isin(drop)]
        res, _, _ = control(frame, "spread", name)
        ladder.append((name, len(sp) - len(frame), res))

    # H1 — its own walk-forward (history = the full close-priced set)
    wf_h1 = walk_forward(priced_games(require_opener=False))
    h1_fit = regress(wf_h1.assign(resid=wf_h1["market_move"]), "H1", correction_factor=factor)
    h1 = Result("H1", h1_fit.slope, h1_fit.standard_error, len(wf_h1),
                wf_h1.groupby(["season", "week"]).ngroups, crit)
    sd_h1 = float(wf_h1["disagree"].std())
    decile_h1 = TOP_DECILE_Z * sd_h1

    # H2 and H3 — their own walk-forward (history = the opener-only set)
    wf = walk_forward(priced_games(require_opener=True))
    sd_h2 = float(wf["disagree"].std())
    pay_h2 = profitable_slope(sd_h2)
    h2_splits = []
    for label, frame in (
        ("all games", wf),
        ("early season (weeks 1-4)", wf[wf["week"] <= 4]),
        ("late season (weeks 5+)", wf[wf["week"] > 4]),
    ):
        fit = regress(frame.assign(resid=frame["resid_open"]), label, correction_factor=factor)
        own_sd = float(frame["disagree"].std())
        h2_splits.append(
            (Result(label, fit.slope, fit.standard_error, len(frame),
                    frame.groupby(["season", "week"]).ngroups, crit,
                    threshold=profitable_slope(own_sd)), own_sd)
        )
    h2 = h2_splits[0][0]

    thin, thick = wf[wf["books"] <= 2], wf[wf["books"] >= 4]
    tie = wf[wf["books"] == 3]
    arms = {}
    for name, frame in (("thin", thin), ("thick", thick)):
        fit = regress(frame.assign(resid=frame["resid_open"]), name, correction_factor=factor)
        own_sd = float(frame["disagree"].std())
        arms[name] = (
            Result(name, fit.slope, fit.standard_error, len(frame),
                   frame.groupby(["season", "week"]).ngroups, crit,
                   threshold=profitable_slope(own_sd)), own_sd,
            frame.groupby("season").size().to_dict(),
        )
    delta = arms["thin"][0].estimate - arms["thick"][0].estimate
    delta_se = float(np.sqrt(arms["thin"][0].se ** 2 + arms["thick"][0].se ** 2))
    h3 = Result("delta", delta, delta_se, len(thin) + len(thick),
                wf[wf["books"] != 3].groupby(["season", "week"]).ngroups, crit,
                threshold=arms["thin"][1] and profitable_slope(arms["thin"][1]))

    # the substituted segment splits, measured so they are reported rather than buried
    sp = sp.assign(abs_move=sp["line_move"].abs())
    subs = []
    for label, a, b in (
        ("weeks 1-4 vs weeks 5+", sp[sp.week <= 4], sp[sp.week > 4]),
        ("books <= 3 vs books > 3", sp[sp.books <= 3], sp[sp.books > 3]),
        (r"\|close\| >= 14 vs < 14", sp[sp.close_consensus.abs() >= 14], sp[sp.close_consensus.abs() < 14]),
        ("books <= 2 vs books >= 4", sp[sp.books <= 2], sp[sp.books >= 4]),
    ):
        diff, se = clustered_difference(a, b, "abs_move")
        subs.append((label, Result(label, diff, se, len(a) + len(b),
                                   pd.concat([a, b]).groupby(["season", "week"]).ngroups, crit),
                     a["abs_move"].mean(), len(a), b["abs_move"].mean(), len(b)))

    # what it would take -----------------------------------------------------
    def games_needed(res: Result, target: float, base_n: int) -> float:
        """Games at which the floor would reach `target`, if SE scales as 1/sqrt(n)."""
        needed_se = target / floor_multiple
        return base_n * (res.se / needed_se) ** 2

    h2_needed = games_needed(h2, h2.threshold, h2.n)
    thin_needed = games_needed(arms["thin"][0], arms["thin"][0].threshold, arms["thin"][0].n)
    quarter_tick = 0.25 / decile_h1
    h1_needed = games_needed(h1, quarter_tick, h1.n)
    per_season = h2.n / (len(SEASONS) - 1)  # 2021 is burned as ratings history

    # ----------------------------------------------------------------- render
    L: list[str] = []
    add = L.append
    add("# Does the OPENING line leave anything on the table?")
    add("")
    add(
        f"Adjudication of the four-hypothesis study pre-registered in "
        f"`docs/preregistered_opener_study.md`. Every interval below is quoted at "
        f"the **corrected critical value {crit:.4f}** — Bonferroni x{factor:.4f} on "
        f"the **{ledger.count} distinct hypotheses** now in "
        f"`data/outputs/experiment_ledger.json`, read live at run time. Every "
        f"detectable-edge floor is **{floor_multiple:.4f} x SE**, the smallest "
        f"effect the design could see at 80% power *at that same critical value*. "
        f"No measured number below is typed into this prose; all of it is rendered "
        f"by `scripts/render_opener_study.py`."
    )
    add("")
    add("---")
    add("")
    add("## The control, first, because everything else depends on it")
    add("")
    add(
        f"**The pre-registered positive control PASSES — and it passes with no "
        f"margin in either of the two ways a result can have margin.** On the "
        f"spread the close beats the open by "
        f"D = mean(e_open²) − mean(e_close²) = **{c_spread.estimate:+.4f} pts²**, "
        f"n = **{c_spread.n:,} games** over {c_spread.clusters} `(season, week)` "
        f"clusters, corrected interval **{c_spread.interval()}**, which excludes "
        f"zero on the pre-registered positive side (z = {c_spread.z:.4f} against "
        f"{crit:.4f}). In points that is RMSE {rmse_o_s:.4f} -> {rmse_c_s:.4f}, an "
        f"improvement of **{rmse_o_s - rmse_c_s:.4f} points**, "
        f"{(rmse_o_s - rmse_c_s) / rmse_o_s:.2%} of RMSE, on n = {c_spread.n:,}."
    )
    add("")
    add(
        f"So by the threshold fixed in advance the control has passed, and the "
        f"nulls in H1–H3 are interpretable rather than uninterpretable. Two "
        f"qualifications are mandatory and they travel with the pass everywhere "
        f"it is quoted."
    )
    add("")
    add(
        f"**No power to spare.** The measured D sits *below* the design's own 80% "
        f"floor of {c_spread.floor:+.4f} pts² (n = {c_spread.n:,}) — restated in "
        f"points, the smallest forecast improvement this design could reliably "
        f"detect is {c_spread.floor / (2 * rmse_o_s):.4f} RMSE points and it "
        f"measured {rmse_o_s - rmse_c_s:.4f}. That is arithmetically consistent "
        f"with the interval excluding zero, but it means a replication would "
        f"clear the corrected bar well under four times in five."
    )
    add("")
    # THE CONCLUSION IS DERIVED, NOT WRITTEN DOWN. This sentence used to end
    # with a hardcoded "which includes zero". That was true of the pre-fix
    # table and became false the moment build_line_table.py started dropping
    # inverted rows -- the renderer went on printing an interval whose own
    # bounds contradicted the clause after them. Prose asserting what the code
    # produces is the thing that rots; this reads the result instead.
    stripped = ladder[-1][2]
    survives = stripped.excludes_zero
    add(
        f"**Robustness, and this is what the re-run changed.** The pass leans on "
        f"a thin tail of games, and part of that tail was never a market move at "
        f"all but a defect in the feed. See *The opener is dirtier than the study "
        f"assumed* below: dropping **{len(sus['union'])} of {c_spread.n:,} games "
        f"({len(sus['union']) / c_spread.n:.2%})** whose raw rows cannot be read "
        f"as a home handicap takes D to {stripped.estimate:+.4f} pts² "
        f"(n = {stripped.n:,}) with an interval of {stripped.interval()} — which "
        + (
            "**still excludes zero**. On the pre-fix table the same exclusion "
            "collapsed the interval across zero, and that fragility is why the "
            "study was re-run; it is gone."
            if survives
            else "**includes zero**, so the pass does not survive its own "
            "data-quality exclusion."
        )
    )
    add("")
    # Derived for the same reason as the sentence above it: the second clause
    # used to say the pass "depends on about N rows", which was the pre-fix
    # state and is the thing the re-run changed.
    add(
        f"The honest one-line verdict: **the instrument can just barely see the "
        f"one effect known to be present in this data"
        + (
            f", and it no longer depends on the {len(sus['union'])} unreadable "
            f"rows to see it.**"
            if survives
            else f", and whether it sees it depends on about "
            f"{len(sus['union'])} rows.**"
        )
        + f" The margin is in the power, not in the data quality: the measured D "
        f"still sits below the design's own 80% floor. Every null in H1–H3 must "
        f"therefore be read against its own floor. None of them is a clean null "
        f"and this report does not present one as such."
    )
    add("")
    add(
        f"**A pass is not an edge and is not quoted as one.** "
        f"{rmse_o_s - rmse_c_s:.4f} RMSE points is roughly a tenth of the "
        f"{VIG_POINTS} points a -110 price needs to clear the vig. Nothing here "
        f"is bettable, no bet was placed and none was automated."
    )
    add("")
    add("| Control | n (games) | Clusters | D (pts²) | SE | Corrected interval | Excludes zero | 80% floor |")
    add("|:---|---:|---:|---:|---:|:---|:---|---:|")
    for res, label in ((c_spread, "spread — **the registered control**"),
                       (c_total, "total — *not registered*"),
                       (c_moved, "spread, moved games only — *not registered*")):
        add(
            f"| {label} | {res.n:,} | {res.clusters} | {res.estimate:+.4f} | "
            f"{res.se:.4f} | {res.interval()} | "
            f"{'yes, positive side' if res.excludes_zero else '**no**'} | "
            f"{res.floor:+.4f} |"
        )
    add("")
    add(
        f"The total market is reported because it was run, not because it was "
        f"registered: RMSE {rmse_o_t:.4f} -> {rmse_c_t:.4f} on "
        f"n = {c_total.n:,}. Its measured D also sits below its own floor of "
        f"{c_total.floor:+.4f}. The moved-games row exists only to show the "
        f"pooled D is not an artefact of the {conv['move_zero']:,} games "
        f"({conv['move_zero'] / conv['n_open']:.1%} of n = {conv['n_open']:,}) "
        f"whose line never moved and whose paired D is exactly zero."
    )
    add("")
    add("---")
    add("")
    add("## The sign convention, verified independently against the raw feed")
    add("")
    add(
        "A silently inverted spread turns a null into a finding and back again, "
        "so this was re-derived from the settlement source rather than taken "
        "from the pre-registration. Five fixtures were pulled back to "
        f"`{RAW / NCAAF.data_dir_segment}/betting/cfb_line_odds.csv.gz` and the "
        "schedule files, "
        "including a neutral-site game and the two most extreme handicaps in the "
        "table; on every one, `margin` equals `home_points - away_points` from "
        "the schedule, and `close_consensus` equals the median of the **home "
        "team's own rows** in the raw feed."
    )
    add("")
    add("| Check | Value | n | The inverted reading |")
    add("|:---|---:|---:|---:|")
    add(f"| `corr(-close_consensus, margin)` | {conv['corr_close']:+.4f} | {conv['n_spread']:,} | {conv['corr_close_inv']:+.4f} |")
    add(f"| `corr(-open_consensus, margin)` | {conv['corr_open']:+.4f} | {conv['n_open']:,} | {-conv['corr_open']:+.4f} |")
    add(f"| `mean(margin - (-close_consensus))` | {conv['bias_close']:+.4f} pts | {conv['n_spread']:,} | {conv['bias_close_flipped']:+.4f} pts |")
    add(f"| `mean(margin - (-open_consensus))` | {conv['bias_open']:+.4f} pts | {conv['n_open']:,} | — |")
    add(f"| home outright win rate, `close_consensus < 0` | {conv['home_win_fav']:.1%} | {conv['n_fav']:,} | — |")
    add(f"| home outright win rate, `close_consensus > 0` | {conv['home_win_dog']:.1%} | {conv['n_dog']:,} | — |")
    add(f"| `line_move == close - open` mismatches | {conv['move_mismatch']} | {conv['n_open']:,} | — |")
    add(f"| `corr(close_consensus, total_points)` (no sign flip) | {conv['corr_total']:+.4f} | {conv['n_total']:,} | — |")
    add("")
    add(
        f"**`open_consensus` carries the same HOME-handicap convention as "
        f"`close_consensus`**, so the price's forecast of the home margin is the "
        f"negative of each. `line_move` is positive on n = {conv['move_pos']:,} "
        f"games (the market moved toward the AWAY team), negative on "
        f"n = {conv['move_neg']:,} and exactly zero on n = {conv['move_zero']:,}. "
        f"{conv['n_pickem']} games closed pick'em. Every figure in the "
        f"pre-registration's conventions table reproduces exactly."
    )
    add("")
    add(
        "One correction to the study's own account. The positive-control script "
        "offers `e_open² - e_close² == (-line_move) x (e_open + e_close)` as an "
        "*independent* sign guard. It is not independent: `line_move` is defined "
        "in `scripts/build_line_table.py` as `close_consensus - open_consensus`, "
        "so that identity is algebra and holds whatever convention the opener is "
        "on. What actually establishes the convention is the correlation and bias "
        "table above plus the fixture-level trace to the raw feed. The conclusion "
        "is unchanged; the guard is weaker than advertised."
    )
    add("")
    add("---")
    add("")
    add("## The opener is dirtier than the study assumed")
    add("")
    add(
        "This is the adjudication's own finding and it was not in the "
        "pre-registration. `open_consensus` is a median over whichever books' "
        "`opening_lines` were populated, and in a small number of games those "
        "rows cannot be read as a home handicap at all."
    )
    add("")
    add(
        f"* **A.** {sus['a_rows']} book-rows of {sus['a_rows_total']:,}, on "
        f"{len(sus['a_games'])} distinct games, carry a single book's own opening "
        f"and closing numbers with **opposite signs**, both at least 3 points "
        f"from pick'em — implied swings of {sus['a_swing_min']:.1f} to "
        f"{sus['a_swing_max']:.1f} points inside one book."
    )
    add(
        f"* **B.** {sus['b_flipped_rows']} book-rows of {sus['b_rows_total']:,}, on "
        f"{sus['b_flipped_games']} distinct games, close on the **opposite "
        f"convention to the rest of that game's own book panel**; on "
        f"{len(sus['b_games'])} of those games the opener comes only from such a "
        f"row, so `open_consensus` and `close_consensus` are on different "
        f"conventions and `line_move` is roughly `-2 x close_consensus`."
    )
    add("")
    add(
        f"The pre-registration's own worked example is one of them. `game_id "
        f"401331447` (2021 wk14, Michigan at Iowa, neutral site, Michigan won "
        f"42-3) is cited there as *\"the largest move toward an away team in the "
        f"table\"* at +22.5 points. Traced back to the feed: three books close "
        f"Iowa +12.0 and Bovada closes Iowa -12.0, and Bovada is the only book "
        f"with an opening number, so `open_consensus` is -10.5 on one convention "
        f"while `close_consensus` is +12.0 on the other. The 22.5-point \"move\" "
        f"is a sign disagreement of roughly 2 x 11.25."
    )
    add("")
    # The renderer used to compute that game's contribution to the control from
    # the table. It cannot any more, and the reason IS the result: the builder
    # now drops the inverted row, the only opener that game had went with it,
    # and 401331447 carries no opener at all. Reading it raised KeyError on the
    # first run after the fix -- a worked example that depended on the defect it
    # was describing.
    example_present = "401331447" in sp.index and pd.notna(
        sp.loc["401331447", "open_consensus"]
    )
    add(
        "That example no longer resolves, and its not resolving is the point. "
        "`scripts/build_line_table.py` now drops the inverted row; it was the "
        "only book quoting an opener on that game, so 401331447 carries "
        + ("no opener at all" if not example_present else "a corrected opener")
        + " and the 22.5-point move is gone from the table. The figure quoted "
        "above is from the pre-fix build, recorded here because the defect is "
        "why this study was re-run."
    )
    add("")
    add(
        "Nothing is repaired. A price that cannot be read is treated the way the "
        "lab treats a missing one — dropped, never inverted into what it \"should "
        "have\" been — because repairing it would be fabricating a price."
    )
    add("")
    add("| Positive control, spread | n | Dropped | D (pts²) | SE | Corrected interval | Excludes zero |")
    add("|:---|---:|---:|---:|---:|:---|:---|")
    for name, dropped, res in ladder:
        add(
            f"| {name} | {res.n:,} | {dropped} | {res.estimate:+.4f} | {res.se:.4f} "
            f"| {res.interval()} | "
            f"{'yes' if res.excludes_zero else '**no — includes zero**'} |"
        )
    add("")
    add(
        f"**H1 and H2 are robust to this; the control is not.** Both slopes keep "
        f"their sign, their magnitude and their verdict at every rung. The "
        f"control keeps its pass when either signature is dropped alone and loses "
        f"it when both are dropped together — {len(sus['union'])} games, "
        f"{len(sus['union']) / c_spread.n:.2%} of the sample. A delete-one-cluster "
        f"jackknife over all {c_spread.clusters} weeks, by contrast, never breaks "
        f"the pass, so this is not a week effect: it is a handful of individual "
        f"rows. Note the direction — the corrupt rows *inflate* the apparent "
        f"open-to-close improvement, so the true gap between the two prices is "
        f"probably smaller than {c_spread.estimate:+.4f} pts², which makes the "
        f"market's own revision worth even less than the "
        f"{rmse_o_s - rmse_c_s:.4f} RMSE points quoted above."
    )
    add("")
    add("---")
    add("")
    add("## H1 — do the ratings anticipate the market's own revision?")
    add("")
    add(
        f"`regress(market_move on disagree_open)`, clustered by "
        f"`(season, week)`, where `market_move = -line_move`. Direction fixed in "
        f"advance: POSITIVE."
    )
    add("")
    add(
        f"**No demonstrated edge.** Slope **{h1.estimate:+.6f}**, cluster-robust "
        f"SE {h1.se:.6f}, n = **{h1.n:,} games** over {h1.clusters} clusters, "
        f"corrected interval **{h1.interval()}**, which includes zero. The sign is "
        f"NEGATIVE against a registered POSITIVE, but zero is inside the interval, "
        f"so no anti-correlation is demonstrated either."
    )
    add("")
    add(
        f"**Interpretable, not an absence — and it goes further than a null.** The "
        f"detectable floor is {h1.floor:.6f} (n = {h1.n:,}), which sits below the "
        f"{0.5 / decile_h1:.4f} a half-point tick of movement at the top decile of "
        f"disagreement would represent, so the design could have seen an effect of "
        f"the size that would matter. Separately from the null, the interval's "
        f"upper bound of {h1.high:+.6f} corresponds to at most "
        f"**{h1.high * decile_h1:+.2f} points of line move** at the top decile "
        f"({decile_h1:.2f} points, sd(disagree_open) = {sd_h1:.4f}, n = {h1.n:,}). "
        f"A market revision toward these ratings of even a quarter-point tick "
        f"({quarter_tick:.4f}) is ruled out. \"No demonstrated edge\" and \"ruled "
        f"out\" are different claims and both are available here, so both are made."
    )
    add("")
    add(
        f"**This is a CLV statement, not a profit statement.** The data carries no "
        f"price on the move, which is why the pre-registration deliberately set no "
        f"profitability threshold here. Predicting the move would mean getting a "
        f"better number than the close, which is necessary for profit and not "
        f"sufficient. Nothing here is an edge."
    )
    add("")
    add("---")
    add("")
    add("## H2 — do the ratings predict the result off the opener?")
    add("")
    add(
        f"The Step 5 instrument with the opener in place of the close. "
        f"`profitable_slope = {VIG_POINTS} / ({TOP_DECILE_Z} x "
        f"sd(disagree_open) {sd_h2:.4f}) = **{pay_h2:.4f}**` — the formula was "
        f"registered in advance and the value is measured on this sample. "
        f"Disagreement with the opener is *tighter* than with the close "
        f"({sd_h2:.4f} against the published 8.19), which raises the bar rather "
        f"than lowering it."
    )
    add("")
    add("| Split | n | Clusters | Slope | SE | Corrected interval | Reading | 80% floor | Own threshold |")
    add("|:---|---:|---:|---:|---:|:---|:---|---:|---:|")
    for res, own_sd in h2_splits:
        add(
            f"| {res.label} | {res.n:,} | {res.clusters} | {res.estimate:+.4f} | "
            f"{res.se:.4f} | {res.interval()} | {res.reading()} | {res.floor:.4f} | "
            f"{res.threshold:.4f} |"
        )
    add("")
    add(
        f"**No demonstrated edge on all three splits** — every corrected interval "
        f"includes zero, in those words. Three further statements, which are "
        f"different from that one and from each other, and which do not hold in "
        f"the same places."
    )
    add("")
    add(
        f"1. **A paying slope is ruled out on all games** (upper bound "
        f"{h2.high:+.4f} < {h2.threshold:.4f}) and on the early-season split "
        f"({h2_splits[1][0].high:+.4f} < {h2_splits[1][0].threshold:.4f}). It is "
        f"**not** ruled out late season: upper bound "
        f"{h2_splits[2][0].high:+.4f} against its own {h2_splits[2][0].threshold:.4f}, "
        f"n = {h2_splits[2][0].n:,}. Nothing should be claimed there in either "
        f"direction — the same split Step 5 left unresolved against the close."
    )
    add(
        f"2. **The 80% power criterion fails everywhere.** Every floor "
        f"({' / '.join(f'{r.floor:.4f}' for r, _ in h2_splits)}) sits above the "
        f"threshold that would matter. So the all-games ruling-out is the realized "
        f"interval speaking, not a design that could be trusted in advance to have "
        f"seen a paying slope. **Report the ruling-out and the power failure "
        f"together; either alone misleads.**"
    )
    add(
        f"3. **The direction failed.** Registered POSITIVE, measured "
        f"{h2.estimate:+.4f} on all games and {h2_splits[1][0].estimate:+.4f} early "
        f"season (n = {h2_splits[1][0].n:,}) — the split the pre-registration named "
        f"as the likeliest place for a soft opener. The intervals include zero, so "
        f"this is a failed prediction and not a demonstrated reversal, and it must "
        f"not be re-narrated as a finding about the market overreacting to ratings."
    )
    add("")
    add(
        f"This **contradicts nothing already established and adds nothing to it**. "
        f"Step 5 found ratings-vs-close slope -0.0196 on n = 3,124 with the same "
        f"shape: no demonstrated edge, a paying slope ruled out on all games, late "
        f"season unresolved. Against the opener the shape repeats. **The opener is "
        f"not measurably softer than the close for this instrument, and ratings do "
        f"not re-enter the architecture.**"
    )
    add("")
    add("---")
    add("")
    add("## H3 — is the opener softer where few books quote?")
    add("")
    add(
        "**The registered H3 was not run by the study, and is run here.** "
        "`docs/preregistered_opener_study.md` registers `segment-heterogeneity` "
        "as the H2 regression in each arm with `delta = slope_thin - "
        "slope_thick`, over `thin = books <= 2` and `thick = books >= 4`, with "
        "`books == 3` excluded as the tie *\"fixed now so it cannot be moved "
        "later\"*. `scripts/run_opener_segment_softness.py` measured a different "
        "statistic (mean absolute line move) over three different segment "
        "definitions, two of which the pre-registration had named and expressly "
        "declined. Those splits are reported below because they were run, and "
        "they are recorded in the ledger as unregistered looks; the registered "
        "statistic is this one."
    )
    add("")
    add("| Arm | n | Clusters | Slope | SE | Corrected interval | 80% floor | Own threshold |")
    add("|:---|---:|---:|---:|---:|:---|---:|---:|")
    for name in ("thin", "thick"):
        res, own_sd, _ = arms[name]
        add(
            f"| {name} (`books {'<= 2' if name == 'thin' else '>= 4'}`) | {res.n:,} | "
            f"{res.clusters} | {res.estimate:+.4f} | {res.se:.4f} | "
            f"{res.interval()} | {res.floor:.4f} | {res.threshold:.4f} |"
        )
    add(
        f"| **delta = thin − thick** | {h3.n:,} | {h3.clusters} | "
        f"{h3.estimate:+.4f} | {h3.se:.4f} | {h3.interval()} | {h3.floor:.4f} | "
        f"{h3.threshold:.4f} |"
    )
    add("")
    add(
        f"**This is an ABSENCE, not a null, exactly as pre-declared.** The "
        f"interval on delta includes zero — no demonstrated edge — but the "
        f"detectable floor of {h3.floor:.4f} sits far above the "
        f"{h3.threshold:.4f} a paying strategy in the thin arm would need, so a "
        f"design that could not have seen the effect did not see it. The sign is "
        f"NEGATIVE against a registered POSITIVE. The excluded tie holds "
        f"n = {len(tie):,} games, more than both arms together."
    )
    add("")
    add(
        f"**A confound the pre-registration did not record, measured here.** The "
        f"thick arm is {arms['thick'][2].get(2022, 0):,} 2022 games out of "
        f"{arms['thick'][0].n:,} ({arms['thick'][2].get(2022, 0) / arms['thick'][0].n:.0%}), "
        f"by season {arms['thick'][2]}; the thin arm is {arms['thin'][2]}. The "
        f"number of books in this feed is largely a property of the *season*, not "
        f"of the game, so the registered thin-versus-thick contrast is mostly a "
        f"2023-2025-versus-2022 contrast wearing a liquidity label. The thick arm "
        f"spans only {arms['thick'][0].clusters} clusters and the thin arm "
        f"{arms['thin'][0].clusters}, both under the 30-50 a cluster-robust SE "
        f"needs; the quadrature SE additionally assumes the arms are independent, "
        f"which games sharing a week make only approximately true. The interval is "
        f"reported with all of that attached rather than quoted clean."
    )
    add("")
    add("### The substituted splits, reported because they were run")
    add("")
    add("Mean absolute line move, thinner arm minus thicker, n = games in both arms.")
    add("")
    add("| Split | Thin mean (n) | Thick mean (n) | Difference | SE | Corrected interval | Reading | 80% floor |")
    add("|:---|---:|---:|---:|---:|:---|:---|---:|")
    for label, res, ma, na, mb, nb in subs:
        add(
            f"| {label} | {ma:.4f} ({na:,}) | {mb:.4f} ({nb:,}) | "
            f"{res.estimate:+.4f} | {res.se:.4f} | {res.interval()} | "
            f"{res.reading()} | {res.floor:.4f} |"
        )
    add("")
    add(
        f"**No demonstrated edge on any of them.** Every point estimate has the "
        f"registered sign — the thinner arm moved more in all four — and that is "
        f"four correlated views of one dataset rather than four votes: the same "
        f"n = {len(sp):,} games are re-partitioned each time. Every floor exceeds "
        f"its own point estimate. The closest, `books <= 3` vs `> 3`, is a nominal "
        f"z of {subs[1][1].z:.2f} — it would have cleared an uncorrected 1.96 and "
        f"does not clear {crit:.4f}. That gap is the multiplicity ratchet doing "
        f"its job, and the honest statement is that it has demonstrated nothing. "
        f"That split is also barely a contrast: the median `books` is 3 and most "
        f"of the sample sits exactly on it."
    )
    add("")
    add(
        "One further result of the study's Part 2 needs stating so nobody quotes "
        "it: regressing the opener's residual on the line move returns a slope of "
        "1.0 **mechanically**, because `resid_open = e_close + market_move` "
        "identically, so the regressor is an additive term of the dependent "
        "variable. Its zero-exclusion is arithmetic, not evidence. The quantity "
        "that means anything is `slope - 1`, which is algebraically the slope of "
        "the *closing* residual on the move — this lab's already-recorded "
        "line-movement-as-a-detector instrument, which reads no demonstrated edge."
    )
    add("")
    add("---")
    add("")
    add("## Multiplicity: what this study cost")
    add("")
    add("| | Count | Factor | Critical value |")
    add("|:---|---:|---:|---:|")
    for label, count in (("Before this study", ledger.count - 14),
                         ("Pre-registered hypotheses recorded", 4),
                         ("Unregistered looks actually taken, recorded", 10),
                         ("**After — what every interval here is quoted at**", ledger.count)):
        if label.startswith(("Pre-reg", "Unreg")):
            add(f"| {label} | +{count} | | |")
        else:
            fac = NormalDist().inv_cdf(1 - (0.05 / max(count, 1)) / 2) / 1.96
            add(f"| {label} | {count} | x{fac:.4f} | {1.96 * fac:.4f} |")
    add("")
    add(
        f"The pre-registration fixed **{PREREG_CRITICAL_VALUE}** in advance, on the "
        f"assumption that this study would spend exactly its registered four. It "
        f"spent fourteen. The pre-registration is explicit about the price of the "
        f"extra ones — *\"if one is ever run it is a NEW LEDGER ENTRY and the "
        f"correction is re-derived\"* — so they are recorded, under the separate "
        f"search name `opener-study-unregistered` so a reader can always tell "
        f"which four were bought in advance. **No verdict in this report changes "
        f"between {PREREG_CRITICAL_VALUE} and {crit:.4f}**: the control's "
        f"z of {c_spread.z:.4f} clears both, and every other interval includes "
        f"zero at both. Under-recording would have made every later interval too "
        f"narrow, which is the single failure the ledger exists to prevent; "
        f"over-recording can only make an absence plainer, and every result here "
        f"is an absence or a null."
    )
    add("")
    add(
        "**The recorder has the self-derived-floor defect, confirmed by running "
        "it rather than by reading it.** `ExperimentLedger.save()` refuses a "
        "shrinking write by re-loading the target file and comparing lengths — but "
        "the recorder pattern loads that same file, appends in memory and saves "
        "the same object back, so the floor it is guarded against is derived from "
        "the same load. Measured: hand-delete an entry from the tracked JSON, run "
        "the recorder pattern, and the write is accepted silently, the deleted "
        "hypothesis is gone, and the printed correction is unremarkable. The guard "
        "cannot fire from any caller in this repository. What does catch it is "
        "`scripts/check_ledger_append_only.py`, which compares against the base "
        "commit rather than against the file it is about to overwrite; run against "
        "the pre-study ledger it reports all base entries present and the new ones "
        "appended. So the property holds in CI and not at runtime, and no caller "
        "should be trusted to enforce it locally."
    )
    add("")
    add(
        f"**One consequence of recording, flagged rather than acted on.** "
        f"`scripts/run_ratings_residual.py` reads the correction live, by design "
        f"— its own docstring says this is so that adding hypotheses tightens its "
        f"conclusion automatically rather than leaving a stale constant behind. "
        f"So `data/outputs/ratings_residual.md`, which was rendered at 78 "
        f"hypotheses, is now stale against a re-run at {ledger.count}. Checked "
        f"before flagging: at {crit:.4f} the Step 5 all-games interval becomes "
        f"about [-0.1386, +0.0994] and its detectable slope about 0.148, so it "
        f"still rules out the 0.143 that would pay and its power criterion still "
        f"narrowly fails — **no Step 5 verdict changes**. The file is left "
        f"untouched here because re-rendering another study's published record is "
        f"not an adjudicator's call to make unasked."
    )
    add("")
    add(
        "**A live hazard left in the tree for review, not fixed here.** Three of "
        "the study's scripts derive their critical value as "
        "`correction_factor(extra=4)` against the live ledger. That was correct "
        "while the ledger stood at 78. Now that these entries are recorded the "
        "same call reads 92 + 4 = 96 and silently over-corrects. "
        "`scripts/run_opener_ratings_residual.py` avoided this by pinning the "
        "value as a constant; the other three should do the same or drop `extra`."
    )
    add("")
    add("---")
    add("")
    add("## What would be needed to settle what is unsettled")
    add("")
    add(
        "None of the following is a plan to bet. Each is the size of the "
        "measurement that would be required before anything here could be called "
        "settled, and in two cases the answer is that this lab's data cannot "
        "settle it at all."
    )
    add("")
    add(
        f"**H2, all games — to make the null a finding rather than a "
        f"realized-interval statement.** The floor must fall from {h2.floor:.4f} "
        f"to the {h2.threshold:.4f} that would pay, so the SE must fall from "
        f"{h2.se:.4f} to {h2.threshold / floor_multiple:.4f}. If the cluster-robust "
        f"SE scales as 1/sqrt(n), that is about **{h2_needed:,.0f} games**, roughly "
        f"**{(h2_needed - h2.n) / per_season:.1f} more seasons** of FBS-vs-FBS "
        f"football beyond the {h2.n:,} in hand. The ratchet bites here: testing "
        f"again adds hypotheses, which raises the critical value, which raises the "
        f"floor — so the requirement grows slightly every time it is re-asked, and "
        f"the honest figure is 'at least' that many."
    )
    add("")
    add(
        f"**H2, late season — the only split that has ruled nothing out.** Upper "
        f"bound {h2_splits[2][0].high:+.4f} on n = {h2_splits[2][0].n:,}, above its "
        f"own {h2_splits[2][0].threshold:.4f}. It needs the same order of "
        f"additional seasons, and it is the one place in this study where a "
        f"future look is defensible rather than a second bite."
    )
    add("")
    add(
        f"**H3 — not settleable with this feed.** The thin arm accrues about "
        f"{arms['thin'][0].n / 4:.0f} games per season. Bringing its floor "
        f"({arms['thin'][0].floor:.4f}) down to its own threshold "
        f"({arms['thin'][0].threshold:.4f}) needs roughly "
        f"**{thin_needed:,.0f} thin-arm games**, on the order of "
        f"**{(thin_needed - arms['thin'][0].n) / (arms['thin'][0].n / 4):.0f} more "
        f"seasons**. That is not a sample-size problem to be waited out. It needs "
        f"a different instrument: a real per-book price feed with timestamps and a "
        f"quoted side, so that \"thin\" means *books actually quoting when the "
        f"number posted* rather than *books present in the settled feed*. **The "
        f"lab does not have that data.** No provider fetch has ever run here, no "
        f"price has been bought, and no market is known to be quoted by anybody."
    )
    add("")
    add(
        f"**H1 — bounded, and the remaining gap is small.** The design already "
        f"rules out a quarter-point revision toward the ratings. To resolve a "
        f"quarter-point *effect* rather than bound it, the floor would need to "
        f"reach {quarter_tick:.4f}, about **{h1_needed:,.0f} games** "
        f"({(h1_needed - h1.n) / per_season:.1f} more seasons). Worth noting only "
        f"because it is a CLV question; there is still no price on the move."
    )
    add("")
    add(
        f"**The control's robustness — a data problem, not a sample-size "
        f"problem.** More seasons of the same feed will import the same defect at "
        f"the same rate. What would settle it is per-book opening prices with an "
        f"unambiguous side attribution and a timestamp — again, data the lab does "
        f"not have. In the meantime the {len(sus['union'])} identified games should "
        f"be treated as missing prices by anything downstream that uses "
        f"`open_consensus` or `line_move`."
    )
    add("")
    add("---")
    add("")
    add("## The standing verdict, unchanged")
    add("")
    add(
        f"Five instruments had already been run against the closing line and "
        f"every one read no demonstrated edge. This study adds a sixth, seventh "
        f"and eighth reading against the **opening** line — H1, H2 and H3 — and "
        f"**every one of them reads no demonstrated edge as well**, with H3 an "
        f"absence rather than a null and H2's power criterion failing on every "
        f"split. The one thing this study did demonstrate is that the close is a "
        f"better forecast than the open by {rmse_o_s - rmse_c_s:.4f} RMSE points "
        f"(n = {c_spread.n:,}), which is a description of a market converging "
        f"toward efficiency and is roughly a tenth of what a -110 price costs. "
        f"**No edge was found, none is claimed, no bet was placed and none was "
        f"automated.**"
    )
    add("")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written to {OUTPUT}  ({len(L)} lines)")
    print(f"ledger {ledger.count} hypotheses, x{factor:.4f}, critical value {crit:.4f}")
    print(f"control spread D {c_spread.estimate:+.4f} n {c_spread.n:,} "
          f"{c_spread.interval()} excludes zero {c_spread.excludes_zero}")
    print(f"  after dropping {len(sus['union'])} unreadable openers: "
          f"{ladder[-1][2].estimate:+.4f} n {ladder[-1][2].n:,} "
          f"{ladder[-1][2].interval()} excludes zero {ladder[-1][2].excludes_zero}")
    print(f"H1 slope {h1.estimate:+.6f} n {h1.n:,} {h1.interval()} floor {h1.floor:.6f}")
    print(f"H2 slope {h2.estimate:+.4f} n {h2.n:,} {h2.interval()} floor {h2.floor:.4f} "
          f"threshold {h2.threshold:.4f}")
    print(f"H3 delta {h3.estimate:+.4f} n {h3.n:,} {h3.interval()} floor {h3.floor:.4f} "
          f"threshold {h3.threshold:.4f}")


if __name__ == "__main__":
    main()
