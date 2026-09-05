"""POSITIVE CONTROL: does the CLOSE beat the OPEN as a forecast?

Pre-registered in `docs/preregistered_opener_study.md` under the name
`control-close-beats-open`. This runs FIRST and everything else in the opener
study depends on it.

    statistic  D = mean(e_open^2) - mean(e_close^2)
    direction  POSITIVE, fixed in advance -- the close must be the better forecast
    SE         cluster-robust, grouped by (season, week)
    interval   at the CORRECTED critical value (ledger 78 + this study's 4 = 82)
    floor      (critical value + z_0.80) x SE, the smallest D detectable at 80% power

The comparison is PAIRED: the same game supplies both forecasts, so the game's
own enormous outcome noise (sd(margin) = 20.3) cancels in the difference. An
unpaired or ROI-shaped test of the same question would be a fraction of the
power.

If this control FAILS, every null in H1-H3 is uninterpretable and is reported
as an absence rather than a finding.

Nothing here fits a model, and nothing here places or automates a bet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from ncaaf_betting_lab.experiment_ledger import load as load_ledger

ROOT = Path(__file__).resolve().parents[1]
LINE_TABLE = ROOT / "data/processed/line_table.csv"
LEDGER = ROOT / "data/outputs/experiment_ledger.json"

#: This study registers four hypotheses of its own and pays for them, which is
#: the lab's established convention (scripts/record_step5_and_backfill_ledger.py).
#: The ledger is NOT written here -- that is the adjudicator's job.
STUDY_HYPOTHESES = 4

#: z for 80% power. Detectable effect = (critical value + this) x SE.
Z_POWER = NormalDist().inv_cdf(0.80)


@dataclass(frozen=True)
class PairedMSETest:
    """mean(e_open^2) - mean(e_close^2), with a week-clustered standard error."""

    label: str
    games: int
    clusters: int
    mse_open: float
    mse_close: float
    delta: float
    standard_error: float
    critical_value: float

    @property
    def interval(self) -> tuple[float, float]:
        half = self.critical_value * self.standard_error
        return (self.delta - half, self.delta + half)

    @property
    def excludes_zero(self) -> bool:
        low, high = self.interval
        return low > 0.0 or high < 0.0

    @property
    def excludes_zero_on_the_positive_side(self) -> bool:
        """The pre-registered direction. A significant NEGATIVE D fails too."""
        return self.interval[0] > 0.0

    @property
    def detectable_delta(self) -> float:
        """Smallest D this design could see at 80% power, at the CORRECTED
        critical value. Computing it at 1.96 while quoting intervals at 3.43 is
        how an underpowered design gets read as a null."""
        return (self.critical_value + Z_POWER) * self.standard_error

    def points_equivalent(self, delta: float) -> float:
        """A squared-error gap D, restated as the RMSE points it is worth.

        rmse_open - rmse_close when the close's MSE is held at its measured
        value. Points are the unit this lab's thresholds are written in.
        """
        return float(np.sqrt(max(self.mse_close + delta, 0.0)) - np.sqrt(self.mse_close))

    @property
    def realized_power(self) -> float:
        """Power this design had, AT THE EFFECT IT MEASURED.

        The floor is the effect detectable at 80%. When the measured effect
        lands BELOW that floor the design cleared zero with less than 80%
        probability of doing so again, and saying "it passed" without saying
        this would overstate how repeatable the pass is.
        """
        if self.standard_error <= 0:
            return float("nan")
        return NormalDist().cdf(abs(self.delta) / self.standard_error - self.critical_value)

    @property
    def power_is_marginal(self) -> bool:
        """Passed, but with the measured effect under the design's own floor."""
        return abs(self.delta) < self.detectable_delta

    def reading(self) -> str:
        if self.excludes_zero_on_the_positive_side:
            if self.power_is_marginal:
                return (
                    "PASSES -- the close is measurably the better forecast, "
                    "but the measured effect is SMALLER than the design's own "
                    "80% floor, so the pass has no power to spare"
                )
            return "PASSES -- the close is measurably the better forecast"
        if self.interval[1] < 0.0:
            return (
                "FAILS, and in the WRONG DIRECTION -- the interval excludes "
                "zero on the negative side"
            )
        return "no demonstrated edge -- the interval includes zero"


def clustered_mean(values: np.ndarray, clusters: pd.Series) -> tuple[float, float, int]:
    """Mean of `values` and its cluster-robust standard error.

    The one-sample analogue of the cluster-robust sandwich in
    `ratings_residual.regress`: regress values on an intercept, sum the scores
    within each (season, week) cell, and square the cell sums rather than the
    individual residuals. The same market prices every game in a week and the
    errors move together, so the individual-observation SE would be too narrow.
    """
    n = len(values)
    mean = float(values.mean())
    centred = values - mean
    frame = pd.DataFrame({"_e": centred, "_g": clusters.to_numpy()})
    meat = float(sum(float(g["_e"].sum()) ** 2 for _, g in frame.groupby("_g")))
    return mean, float(np.sqrt(meat)) / n, int(frame["_g"].nunique())


def paired_mse_test(
    frame: pd.DataFrame,
    label: str,
    forecast_open: np.ndarray,
    forecast_close: np.ndarray,
    outcome: np.ndarray,
    *,
    critical_value: float,
) -> PairedMSETest:
    e_open = outcome - forecast_open
    e_close = outcome - forecast_close
    paired = e_open**2 - e_close**2
    cells = frame["season"].astype(str) + "-" + frame["week"].astype(str)
    delta, se, clusters = clustered_mean(paired, cells)
    return PairedMSETest(
        label=label,
        games=len(frame),
        clusters=clusters,
        mse_open=float((e_open**2).mean()),
        mse_close=float((e_close**2).mean()),
        delta=delta,
        standard_error=se,
        critical_value=critical_value,
    )


def verify_conventions(spread: pd.DataFrame, total: pd.DataFrame) -> None:
    """Re-check the signs on THIS run rather than trusting the pre-registration.

    A flipped sign here silently inverts the whole result and produces clean
    prose about a fictitious effect.
    """
    print("=" * 78)
    print("0. SIGN CONVENTIONS, re-verified on this run (not taken on trust)")
    print("=" * 78)

    n = len(spread)
    r = float(np.corrcoef(-spread["close_consensus"], spread["margin"])[0, 1])
    print(f"  corr(-close_consensus, margin)      = {r:+.4f}   n={n:,}"
          f"   [inverted reading: {-r:+.4f}]")
    print(f"  mean(margin - (-close_consensus))   = "
          f"{float((spread['margin'] + spread['close_consensus']).mean()):+.4f} pts   n={n:,}"
          f"   [inverted: "
          f"{float((spread['margin'] - spread['close_consensus']).mean()):+.4f}]")

    with_open = spread.dropna(subset=["open_consensus", "line_move"])
    m = len(with_open)
    r_open = float(np.corrcoef(-with_open["open_consensus"], with_open["margin"])[0, 1])
    print(f"  corr(-open_consensus, margin)       = {r_open:+.4f}   n={m:,}"
          f"   [inverted reading: {-r_open:+.4f}]")
    print(f"  mean(margin - (-open_consensus))    = "
          f"{float((with_open['margin'] + with_open['open_consensus']).mean()):+.4f} pts   n={m:,}")
    print("    -> open_consensus is the HOME handicap, SAME convention as close.")

    fav = spread[spread["close_consensus"] < 0]
    dog = spread[spread["close_consensus"] > 0]
    print(f"  home outright win rate, close_consensus < 0: "
          f"{float((fav['margin'] > 0).mean()):.1%}   n={len(fav):,}")
    print(f"  home outright win rate, close_consensus > 0: "
          f"{float((dog['margin'] > 0).mean()):.1%}   n={len(dog):,}")

    recomputed = with_open["close_consensus"] - with_open["open_consensus"]
    bad = int((np.abs(recomputed - with_open["line_move"]) > 1e-9).sum())
    print(f"  line_move == close_consensus - open_consensus on "
          f"{m - bad:,} of {m:,} spread rows (mismatches: {bad})")
    print(f"    line_move > 0 (market moved toward the AWAY team): "
          f"n={int((with_open['line_move'] > 0).sum()):,};  < 0 (toward HOME): "
          f"n={int((with_open['line_move'] < 0).sum()):,};  == 0: "
          f"n={int((with_open['line_move'] == 0).sum()):,}")

    t_open = total.dropna(subset=["open_consensus"])
    r_t = float(np.corrcoef(total["close_consensus"], total["total_points"])[0, 1])
    print(f"  corr(close_consensus, total_points) = {r_t:+.4f}   n={len(total):,}"
          f"   (TOTAL: no sign flip -- the number IS the forecast)")
    print(f"  mean(total_points - close_consensus)= "
          f"{float((total['total_points'] - total['close_consensus']).mean()):+.4f} pts"
          f"   n={len(total):,}")
    print(f"  mean(total_points - open_consensus) = "
          f"{float((t_open['total_points'] - t_open['open_consensus']).mean()):+.4f} pts"
          f"   n={len(t_open):,}")


def main() -> None:
    lines = pd.read_csv(LINE_TABLE, dtype={"game_id": str})
    spread = lines[lines["market"] == "spread"].copy()
    total = lines[lines["market"] == "total"].copy()

    verify_conventions(spread, total)

    ledger = load_ledger(LEDGER)
    before = ledger.count
    after = before + STUDY_HYPOTHESES
    # The four hypotheses are already IN the ledger (recorded 2026-09-05 by
    # scripts/record_opener_study.py). `extra=` was right when the ledger stood
    # at 88 and counts them twice now, which is a correction wider than the
    # truth -- the mirror of the shrinking-ledger defect this lab guards against.
    factor = ledger.correction_factor()
    critical = 1.96 * factor

    print()
    print("=" * 78)
    print("1. THE CORRECTION APPLIED")
    print("=" * 78)
    print(f"  ledger before this study     = {before} hypotheses"
          f"   (x{ledger.correction_factor():.4f}, crit "
          f"{1.96 * ledger.correction_factor():.4f})")
    print(f"  this study registers         = {STUDY_HYPOTHESES}")
    print(f"  ledger (already inclusive)   = {ledger.count} hypotheses")
    print(f"  Bonferroni factor            = x{factor:.4f}")
    print(f"  CRITICAL VALUE for every interval below = {critical:.4f}")
    print(f"  detectable-edge floor        = ({critical:.4f} + {Z_POWER:.4f}) x SE "
          f"= {critical + Z_POWER:.4f} x SE   (80% power)")
    print("  NOTE: the ledger is NOT written by this script.")

    # ------------------------------------------------------------------
    # A missing price stays missing. Drop, then quote the n after the drop.
    # ------------------------------------------------------------------
    sp = spread.dropna(subset=["open_consensus"]).copy()
    to = total.dropna(subset=["open_consensus"]).copy()
    print()
    print(f"  spread rows: {len(spread):,} total, {len(spread) - len(sp):,} with no "
          f"opener DROPPED, {len(sp):,} measured")
    print(f"  total  rows: {len(total):,} total, {len(total) - len(to):,} with no "
          f"opener DROPPED, {len(to):,} measured")

    tests = [
        paired_mse_test(
            sp,
            "SPREAD (home-margin space)",
            forecast_open=-sp["open_consensus"].to_numpy(dtype=float),
            forecast_close=-sp["close_consensus"].to_numpy(dtype=float),
            outcome=sp["margin"].to_numpy(dtype=float),
            critical_value=critical,
        ),
        paired_mse_test(
            to,
            "TOTAL (points space)",
            forecast_open=to["open_consensus"].to_numpy(dtype=float),
            forecast_close=to["close_consensus"].to_numpy(dtype=float),
            outcome=to["total_points"].to_numpy(dtype=float),
            critical_value=critical,
        ),
    ]

    print()
    print("=" * 78)
    print("2. THE POSITIVE CONTROL -- paired, same game supplies both forecasts")
    print("=" * 78)
    for t in tests:
        low, high = t.interval
        print()
        print(f"  --- {t.label}")
        print(f"      n = {t.games:,} games   over {t.clusters} (season, week) clusters")
        print(f"      MSE(open)  = {t.mse_open:9.4f} pts^2   "
              f"RMSE {np.sqrt(t.mse_open):7.4f} pts   n={t.games:,}")
        print(f"      MSE(close) = {t.mse_close:9.4f} pts^2   "
              f"RMSE {np.sqrt(t.mse_close):7.4f} pts   n={t.games:,}")
        print(f"      D = MSE(open) - MSE(close) = {t.delta:+.4f} pts^2   n={t.games:,}")
        print(f"      week-clustered SE          = {t.standard_error:.4f}")
        print(f"      corrected {t.critical_value:.4f}-sigma interval = "
              f"[{low:+.4f}, {high:+.4f}]   n={t.games:,}")
        print(f"      excludes zero? {'YES' if t.excludes_zero else 'NO'}"
              f"   (on the PRE-REGISTERED positive side? "
              f"{'YES' if t.excludes_zero_on_the_positive_side else 'NO'})")
        print(f"      DETECTABLE FLOOR (80% power, corrected) = "
              f"{t.detectable_delta:+.4f} pts^2"
              f"   = {t.points_equivalent(t.detectable_delta):.4f} RMSE pts")
        print(f"      measured D restated in points: "
              f"{t.points_equivalent(t.delta):+.4f} RMSE pts   n={t.games:,}")
        print(f"      z = D / SE = {t.delta / t.standard_error:.4f}   against the "
              f"corrected critical value {t.critical_value:.4f}")
        print(f"      realized power AT the measured effect = {t.realized_power:.1%}"
              f"   (the design's 80% floor is {t.detectable_delta:+.4f} pts^2)")
        print(f"      measured effect below the design's own floor? "
              f"{'YES -- pass has NO power to spare' if t.power_is_marginal else 'no'}")
        print(f"      READING: {t.reading()}")

    # ------------------------------------------------------------------
    # Identity check: e_open^2 - e_close^2 = (-line_move) x (e_open + e_close).
    # If the sign convention were flipped this identity would break, so it is a
    # second, independent guard on the direction.
    # ------------------------------------------------------------------
    e_open = sp["margin"].to_numpy(float) + sp["open_consensus"].to_numpy(float)
    e_close = sp["margin"].to_numpy(float) + sp["close_consensus"].to_numpy(float)
    identity = (-sp["line_move"].to_numpy(float)) * (e_open + e_close)
    worst = float(np.max(np.abs(identity - (e_open**2 - e_close**2))))
    print()
    print("=" * 78)
    print("3. INDEPENDENT SIGN GUARD")
    print("=" * 78)
    print(f"  e_open^2 - e_close^2 == (-line_move) x (e_open + e_close): "
          f"max abs discrepancy {worst:.2e} over n={len(sp):,} spread games")
    print("  (identity holds only if forecast_close - forecast_open = -line_move,")
    print("   i.e. only if open_consensus and close_consensus share the HOME-handicap")
    print("   convention. A flipped opener sign would break it loudly.)")

    # Never-moved games carry D = 0 exactly and dilute nothing but the mean.
    moved = sp[sp["line_move"] != 0]
    print()
    print(f"  games whose line never moved: n={len(sp) - len(moved):,} of {len(sp):,} "
          f"({(len(sp) - len(moved)) / len(sp):.1%}) -- their paired D is exactly 0")
    sub = paired_mse_test(
        moved,
        "SPREAD, moved games only (DESCRIPTIVE, not registered)",
        forecast_open=-moved["open_consensus"].to_numpy(dtype=float),
        forecast_close=-moved["close_consensus"].to_numpy(dtype=float),
        outcome=moved["margin"].to_numpy(dtype=float),
        critical_value=critical,
    )
    print(f"  {sub.label}: D = {sub.delta:+.4f} pts^2, SE {sub.standard_error:.4f}, "
          f"interval [{sub.interval[0]:+.4f}, {sub.interval[1]:+.4f}], n={sub.games:,}")
    print("  This split is DESCRIPTIVE and is NOT a registered hypothesis; it is")
    print("  reported only to show the pooled D is not an artefact of the 13% of")
    print("  games where the two prices are literally the same number.")


if __name__ == "__main__":
    main()
