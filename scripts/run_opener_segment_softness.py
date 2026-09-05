"""H3 (segment softness): is the OPENER softer where nobody is looking?

    PYTHONPATH=src .venv/bin/python scripts/run_opener_segment_softness.py

Two halves.

**Part 1 — how much did the market have to correct the opener?** The measure is
`mean |line_move|`, the absolute distance from the opening consensus to the
closing consensus. Three pre-registered splits, three directions fixed in
advance (the *thinner* half moves MORE in each):

  (a) early season, weeks 1-4, versus late, weeks 5+
  (b) few books quoting versus many, split at the median of `books`
  (c) large spreads, |close_consensus| >= 14, versus small

Each difference gets a `(season, week)`-clustered interval at the corrected
critical value, and its detectable-edge floor beside it.

A fourth arm-pair is reported alongside (b): `books <= 2` versus `books >= 4`
with the median excluded, which is the definition actually written into
`docs/preregistered_opener_study.md`. It is reported because substituting a
different books split for the registered one *without saying so* is exactly the
definition-swap the pre-registration forbids. Both are reported whatever they
say; neither was chosen after seeing the other.

**Part 2 — does the correction go anywhere?** A segment where the line moves a
lot is only interesting if the movement predicts the result. Within the arm with
the largest mean absolute move, regress the opener's residual on the move.

**And the trap in Part 2, stated before its number is read.** In home-margin
space

    resid_open = margin - forecast_open
               = (margin - forecast_close) + (forecast_close - forecast_open)
               = e_close + market_move

so `regress(resid_open on market_move)` has a slope of **1.0 mechanically**,
even when the move is pure noise, because `market_move` is a literal additive
term of the dependent variable. Testing that slope against **zero** tests
nothing: it asks whether the move moved. The economically meaningful null is
**slope = 1**, and `slope - 1` is algebraically the slope of `e_close` on the
move — which is the line-movement-as-a-detector instrument this lab already ran
against the close and already reported as no demonstrated edge. Both numbers are
printed. Only the second one is a claim.

Nothing here places or automates a bet. Nothing here is fitted on a game.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ncaaf_betting_lab.experiment_ledger import load as load_ledger
from ncaaf_betting_lab.ratings_residual import Z_POWER, ResidualTest, regress

LINE_TABLE = Path("data/processed/line_table.csv")
LEDGER = Path("data/outputs/experiment_ledger.json")

#: Hypotheses this study adds to the ledger. The pre-registration fixes four,
#: and every interval below is quoted at the *inclusive* count, per the lab's
#: convention in scripts/record_step5_and_backfill_ledger.py.
STUDY_HYPOTHESES = 4

#: Points of true edge a -110 price needs before it clears the vig.
VIG_POINTS = 1.5

#: z at the top decile: bet only the tenth of games where the signal is largest.
TOP_DECILE_Z = 1.28

#: The large-spread cutoff, fixed in advance.
BLOWOUT_CUTOFF = 14.0


@dataclass(frozen=True)
class Arm:
    """One half of one split."""

    split: str
    label: str
    games: int
    mean_abs_move: float
    thin: bool


def load_spreads() -> pd.DataFrame:
    """Spread rows that carry an opener. A missing price stays missing."""
    lines = pd.read_csv(LINE_TABLE, dtype={"game_id": str})
    spreads = lines[lines["market"] == "spread"].copy()
    before = len(spreads)
    spreads = spreads.dropna(subset=["open_consensus", "line_move"]).copy()
    dropped = before - len(spreads)

    # Convention, re-verified here rather than trusted. Both consensuses are the
    # HOME handicap, so the price's forecast of the home margin is the negative.
    #
    # line_move is NO LONGER close_consensus - open_consensus, and this guard
    # used to demand that it was. It fired correctly when the builder changed:
    # a difference between two medians taken over DIFFERENT SETS OF BOOKS is a
    # cross-book quantity, and one inverted row could turn it into a 22.5-point
    # "move". build_line_table.within_book_move now takes the median of per-book
    # moves among books quoting both halves, which is the quantity this script
    # wanted all along -- the distance the market actually travelled.
    #
    # What is still checked is that the two remain the same SIGN CONVENTION, by
    # correlation rather than by identity. They must agree strongly; if the
    # opener were ever flipped this would go negative and the run would stop.
    agreement = float(
        spreads["line_move"].corr(spreads["close_consensus"] - spreads["open_consensus"])
    )
    if not agreement > 0.5:
        raise SystemExit(
            f"line_move correlates {agreement:+.4f} with close - open. They are "
            "measured differently on purpose, but a within-book move and a "
            "cross-book difference must still point the same way; this does not."
        )
    print(f"  line_move vs (close - open): corr {agreement:+.4f}, n = {len(spreads):,} "
          f"-- measured differently (within-book vs cross-book), same convention")

    spreads["forecast_open"] = -spreads["open_consensus"]
    spreads["forecast_close"] = -spreads["close_consensus"]
    spreads["e_open"] = spreads["margin"] - spreads["forecast_open"]
    spreads["e_close"] = spreads["margin"] - spreads["forecast_close"]
    # In home-margin space the market's revision is the NEGATIVE of line_move.
    spreads["market_move"] = -spreads["line_move"]
    spreads["abs_move"] = spreads["line_move"].abs()
    spreads.attrs["dropped_for_no_opener"] = dropped
    return spreads


def difference_in_means(
    frame: pd.DataFrame, mask_thin: pd.Series, label: str, factor: float
) -> ResidualTest:
    """mean|move| in the thin half minus the thick half, clustered by week.

    Reuses `ratings_residual.regress` unchanged: OLS on a demeaned 0/1 dummy
    gives exactly the difference in group means, and the cluster-robust meat is
    the same construction the rest of the lab uses.
    """
    work = frame.assign(
        disagree=mask_thin.astype(float), resid=frame["abs_move"].astype(float)
    )
    return regress(work, label, correction_factor=factor)


def floor_of(test: ResidualTest) -> float:
    """Smallest effect this design could see at 80% power, at the corrected
    critical value. (3.4272 + 0.8416) x SE."""
    return (test.critical_value + Z_POWER) * test.standard_error


def splits(spreads: pd.DataFrame) -> list[tuple[str, str, pd.Series, str, pd.Series]]:
    """(split name, thin label, thin mask, thick label, thick mask).

    Directions are fixed in advance: the THIN arm is the one registered to move
    MORE. Three splits, plus the pre-registration's own books definition.
    """
    books_median = float(spreads["books"].median())
    return [
        (
            "(a) season stage",
            "early (weeks 1-4)",
            spreads["week"] <= 4,
            "late (weeks 5+)",
            spreads["week"] >= 5,
        ),
        (
            f"(b) books, split at the median ({books_median:.0f})",
            f"few books (<= {books_median:.0f})",
            spreads["books"] <= books_median,
            f"many books (> {books_median:.0f})",
            spreads["books"] > books_median,
        ),
        (
            "(c) spread size",
            f"large (|close| >= {BLOWOUT_CUTOFF:.0f})",
            spreads["close_consensus"].abs() >= BLOWOUT_CUTOFF,
            f"small (|close| < {BLOWOUT_CUTOFF:.0f})",
            spreads["close_consensus"].abs() < BLOWOUT_CUTOFF,
        ),
        (
            "(b-prereg) books <= 2 vs >= 4, median excluded",
            "thin (books <= 2)",
            spreads["books"] <= 2,
            "thick (books >= 4)",
            spreads["books"] >= 4,
        ),
    ]


def main() -> None:
    spreads = load_spreads()
    ledger = load_ledger(LEDGER)
    # The four hypotheses are already IN the ledger (recorded 2026-09-05 by
    # scripts/record_opener_study.py). `extra=` was right when the ledger stood
    # at 88 and counts them twice now, which is a correction wider than the
    # truth -- the mirror of the shrinking-ledger defect this lab guards against.
    factor = ledger.correction_factor()
    critical = 1.96 * factor

    print("=" * 78)
    print("H3 — is the opener softer in thin segments?")
    print("=" * 78)
    print(f"line_table: {LINE_TABLE}")
    print(
        f"spread rows with an opener: n = {len(spreads):,} "
        f"(dropped for a missing opener: {spreads.attrs['dropped_for_no_opener']}; "
        "a missing price stays missing)"
    )
    print(
        f"(season, week) clusters: {spreads.groupby(['season', 'week']).ngroups}; "
        f"seasons {sorted(spreads['season'].unique())}"
    )
    print(
        f"sd(line_move) = {spreads['line_move'].std():.4f} pts, "
        f"mean|line_move| = {spreads['abs_move'].mean():.4f} pts, "
        f"never moved: {(spreads['line_move'] == 0).mean():.1%}, n = {len(spreads):,}"
    )
    print(
        f"ledger: {ledger.count} hypotheses before, +{STUDY_HYPOTHESES} this study "
        f"= {ledger.count + STUDY_HYPOTHESES}; Bonferroni x{factor:.4f}; "
        f"critical value {critical:.4f}; floor = {critical + Z_POWER:.4f} x SE"
    )
    print()

    print("-" * 78)
    print("PART 1 — mean absolute line move by segment")
    print("Registered direction in all splits: the THINNER half moves MORE (positive).")
    print("-" * 78)

    arms: list[Arm] = []
    for split, thin_label, thin_mask, thick_label, thick_mask in splits(spreads):
        used = spreads[thin_mask | thick_mask]
        thin_here = thin_mask[used.index]
        test = difference_in_means(used, thin_here, split, factor)
        thin = spreads[thin_mask]
        thick = spreads[thick_mask]
        low, high = test.interval
        direction = "AS REGISTERED" if test.slope > 0 else "AGAINST the registered direction"
        print()
        print(f"{split}")
        print(
            f"  {thin_label:<28} mean|move| = {thin['abs_move'].mean():.4f} pts, "
            f"n = {len(thin):,}, clusters = {thin.groupby(['season','week']).ngroups}"
        )
        print(
            f"  {thick_label:<28} mean|move| = {thick['abs_move'].mean():.4f} pts, "
            f"n = {len(thick):,}, clusters = {thick.groupby(['season','week']).ngroups}"
        )
        print(
            f"  difference (thin - thick) = {test.slope:+.4f} pts, "
            f"SE = {test.standard_error:.4f}, n = {test.games:,}"
        )
        print(
            f"  corrected interval [{low:+.4f}, {high:+.4f}]  ->  "
            + (
                "interval EXCLUDES zero"
                if test.excludes_zero
                else "**no demonstrated edge** (interval includes zero)"
            )
        )
        print(
            f"  detectable floor {floor_of(test):.4f} pts at 80% power; "
            f"sign of the point estimate is {direction}"
        )
        for label, frame, is_thin in (
            (thin_label, thin, True),
            (thick_label, thick, False),
        ):
            arms.append(
                Arm(split, label, len(frame), float(frame["abs_move"].mean()), is_thin)
            )

    print()
    print("-" * 78)
    print("PART 2 — does the correction predict the RESULT?")
    print("-" * 78)
    biggest = max(arms, key=lambda a: a.mean_abs_move)
    print(
        f"Arm with the largest mean absolute move, across every arm measured "
        f"above: {biggest.split} / {biggest.label}, "
        f"mean|move| = {biggest.mean_abs_move:.4f} pts, n = {biggest.games:,}"
    )

    masks: dict[tuple[str, str], pd.Series] = {}
    for split, thin_label, thin_mask, thick_label, thick_mask in splits(spreads):
        masks[(split, thin_label)] = thin_mask
        masks[(split, thick_label)] = thick_mask
    segment = spreads[masks[(biggest.split, biggest.label)]]

    for name, frame in (("all spread games with an opener", spreads), (f"{biggest.split} / {biggest.label}", segment)):
        work = frame.assign(disagree=frame["market_move"], resid=frame["e_open"])
        test = regress(work, name, correction_factor=factor)
        sd_move = float(frame["market_move"].std())
        profitable = VIG_POINTS / (TOP_DECILE_Z * sd_move)
        low, high = test.interval
        excess = test.slope - 1.0
        floor = floor_of(test)
        print()
        print(f"  {name}  (n = {test.games:,}, clusters = {frame.groupby(['season','week']).ngroups})")
        print(f"    sd(market_move) = {sd_move:.4f} pts")
        print(
            f"    slope of resid_open on market_move = {test.slope:+.4f}, "
            f"SE = {test.standard_error:.4f}"
        )
        print(f"    corrected interval vs ZERO      [{low:+.4f}, {high:+.4f}]")
        print(
            "      -> a slope of 1.0 here is MECHANICAL (market_move is an additive "
            "term of resid_open). Testing against zero is not a test."
        )
        print(
            f"    slope MINUS 1 (= slope of e_close on the move, the real null) "
            f"= {excess:+.4f}"
        )
        print(
            f"    corrected interval vs ONE       "
            f"[{low - 1.0:+.4f}, {high - 1.0:+.4f}]  ->  "
            + (
                "interval EXCLUDES one"
                if (low > 1.0 or high < 1.0)
                else "**no demonstrated edge** (interval includes one)"
            )
        )
        print(
            f"    detectable floor {floor:.4f} at 80% power; a paying strategy needs "
            f"{profitable:.4f} (= {VIG_POINTS} / ({TOP_DECILE_Z} x {sd_move:.4f}))"
        )
        print(
            "    -> "
            + (
                "the design COULD have seen a paying slope"
                if floor <= profitable
                else "**UNDERPOWERED** — the floor sits above what would pay, so this "
                "is an ABSENCE, not a finding"
            )
        )

    print()
    print("No bet was placed and none was automated. The ledger was not written to.")


if __name__ == "__main__":
    main()
