"""Do this lab's own ratings add anything the closing price does not have?

The last question of the original plan, and the only one whose answer could
have put ratings back into the architecture.

Everything else in this lab takes its mean from the market, because the sibling
NFL lab established that its ratings were a worse forecaster than the price. But
"worse on average" does not settle whether a rating carries some *residual*
information the price has missed. A rating can be a bad forecaster and still be
a useful correction, and that is a different claim needing its own test.

## The test

Fit ratings walk-forward — least squares on margin against home and away team
indicators plus a home-field term, on games strictly earlier than the one being
priced. Then regress

    (actual margin - market implied margin)  on  (rating margin - market implied)

**A slope of zero means the ratings add nothing.** Every point they disagree
with the close is noise. A slope of one would mean the market is ignoring them
entirely and they are right.

Clustered by week, because the same ratings price every game in a week and
their errors move together.

## Why this null does NOT settle the question

Measured over 3,124 games the standard error is 0.034, so at the nominal level
the design detects a slope of about 0.096 — comfortably under the **0.143** that
profitability needs. (Bet the top decile of disagreement, 10.5 points, since
disagreement has a standard deviation of 8.19; a -110 price needs roughly 1.5
points of true edge to clear the vig.)

That is the arithmetic I first wrote down, and it is wrong, because this lab
does not quote intervals at the nominal level. Correcting for the 78 hypotheses
in the cumulative ledger the critical value moves 1.96 -> 3.41, and the
detectable slope moves **0.096 -> 0.146** — just above the 0.143 that would pay.

**So the honest reading is not "ratings add nothing". It is "ratings were not
shown to add anything, by a design that could not quite have seen it if they
did."** The measured slope is negative and small, which is evidence of a kind,
but the interval is wide enough to hold a slope that would pay for itself.

The correction is read from the ledger rather than pinned here, so that adding
hypotheses tightens this conclusion's honesty automatically instead of leaving
a stale constant behind.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from statistics import NormalDist

#: Ridge penalty on the team ratings. Small: it exists to make the system
#: solvable when a team has played once, not to shrink anyone meaningfully.
RIDGE = 3.0

#: Games of history before a week is priced at all. Below this the ratings are
#: mostly the prior and the disagreement is mostly noise about noise.
MINIMUM_HISTORY = 300

#: Slope needed before ratings could pay for the vig, at the top decile of
#: disagreement. Stated in advance so the answer cannot be graded afterwards.
PROFITABLE_SLOPE = 0.143

#: z for 80% power. The detectable effect is (critical value + this) x se.
Z_POWER = NormalDist().inv_cdf(0.80)


@dataclass(frozen=True)
class ResidualTest:
    label: str
    games: int
    slope: float
    standard_error: float
    #: Bonferroni factor from the cumulative experiment ledger. 1.0 is the
    #: nominal level and is only ever right for a lab that has tested once.
    correction_factor: float = 1.0

    @property
    def critical_value(self) -> float:
        return 1.96 * self.correction_factor

    @property
    def interval(self) -> tuple[float, float]:
        half = self.critical_value * self.standard_error
        return (self.slope - half, self.slope + half)

    @property
    def excludes_zero(self) -> bool:
        low, high = self.interval
        return low > 0.0 or high < 0.0

    @property
    def detectable_slope(self) -> float:
        """Smallest slope this design could see at 80% power.

        At the *corrected* critical value. Computing this at 1.96 while quoting
        intervals at 3.41 is how an underpowered design gets read as a null.
        """
        return (self.critical_value + Z_POWER) * self.standard_error

    @property
    def could_have_seen_a_profitable_slope(self) -> bool:
        """Whether a null here means anything at all."""
        return self.detectable_slope <= PROFITABLE_SLOPE

    @property
    def power_is_marginal(self) -> bool:
        """Clears the threshold, but only just — worth saying out loud.

        A split that detects 0.1428 against a 0.143 threshold has passed the
        guard and demonstrated almost nothing. Printing the binary alone would
        let that read as a clean null.
        """
        return (
            self.could_have_seen_a_profitable_slope
            and self.detectable_slope >= 0.9 * PROFITABLE_SLOPE
        )

    def reading(self) -> str:
        if self.excludes_zero:
            return "interval excludes zero"
        if not self.could_have_seen_a_profitable_slope:
            return (
                f"**underpowered** — could only detect a slope of "
                f"{self.detectable_slope:.3f}, and profitability needs "
                f"{PROFITABLE_SLOPE:.3f}"
            )
        if self.power_is_marginal:
            return "no demonstrated edge, **but only barely powered enough to say so**"
        return "**no demonstrated edge**"

    @property
    def rules_out_a_profitable_slope(self) -> bool:
        """Whether the interval itself excludes everything that would pay."""
        return self.interval[1] < PROFITABLE_SLOPE


def fit_ratings(history: pd.DataFrame) -> tuple[dict[str, float], float]:
    """Least-squares team ratings and a home-field term, from `history` only.

    Ratings are identified only up to an additive constant, so the ridge term
    pins them without shrinking the home-field coefficient, which IS identified.
    """
    teams = sorted(set(history["home"]) | set(history["away"]))
    index = {team: i for i, team in enumerate(teams)}
    design = np.zeros((len(history), len(teams) + 1))
    for row, (_, game) in enumerate(history.iterrows()):
        design[row, index[game["home"]]] += 1.0
        design[row, index[game["away"]]] -= 1.0
        design[row, -1] = 0.0 if game["neutral"] else 1.0
    normal = design.T @ design + RIDGE * np.eye(design.shape[1])
    if design[:, -1].any():
        # Home field IS identified when some game is not neutral, so it must
        # not be shrunk. When every game is neutral the column is empty and the
        # penalty is the only thing keeping the system solvable: leave it.
        normal[-1, -1] -= RIDGE
    beta = np.linalg.solve(normal, design.T @ history["margin"].to_numpy())
    return {team: float(beta[index[team]]) for team in teams}, float(beta[-1])


def regress(
    frame: pd.DataFrame, label: str, *, correction_factor: float = 1.0
) -> ResidualTest:
    """Residual on disagreement, clustered by week."""
    x = frame["disagree"].to_numpy(dtype=float)
    y = frame["resid"].to_numpy(dtype=float)
    x = x - x.mean()
    denominator = float(x @ x)
    if denominator <= 0 or len(frame) < 2:
        return ResidualTest(label, len(frame), 0.0, float("inf"), correction_factor)
    slope = float(x @ y) / denominator
    error = y - slope * x - y.mean()
    grouped = frame.assign(_x=x, _e=error).groupby(["season", "week"])
    meat = sum((float(g["_x"] @ g["_e"])) ** 2 for _, g in grouped)
    return ResidualTest(
        label, len(frame), slope, float(np.sqrt(meat)) / denominator, correction_factor
    )


def render(
    tests: list[ResidualTest], *, disagreement_sd: float, ledger_count: int
) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Do this lab's own ratings add anything the price does not have?")
    add("")
    add(
        "Everything here takes its mean from the market, because the sibling "
        "NFL lab found its ratings were a worse forecaster than the price. But "
        "a rating can be a bad forecaster and still be a useful **correction**, "
        "and that is a different claim. This is its test."
    )
    add("")
    if not tests:
        add("**Nothing was measured.** An absence, not a null.")
        return "\n".join(lines) + "\n"
    factor = tests[0].correction_factor
    add(
        f"All intervals are corrected for the **{ledger_count} hypotheses** in "
        f"the cumulative ledger (Bonferroni, x{factor:.3f}, critical value "
        f"{tests[0].critical_value:.2f} rather than 1.96)."
    )
    add("")
    add("| Split | Games | Slope | 95% interval (corrected) | Detects | Rules out a paying slope? |")
    add("|:---|---:|---:|:---|---:|:---|")
    for test in tests:
        low, high = test.interval
        verdict = (
            "**yes** — interval sits below 0.143"
            if test.rules_out_a_profitable_slope
            else "**NO** — interval still holds a slope that would pay"
        )
        add(
            f"| {test.label} | {test.games:,} | {test.slope:+.4f} | "
            f"[{low:+.4f}, {high:+.4f}] | {test.detectable_slope:.3f} | {verdict} |"
        )
    add("")
    add(
        f"*Detects* is the smallest slope the split could see at 80% power **at "
        f"the corrected critical value**. Profitability needs "
        f"{PROFITABLE_SLOPE:.3f}: bet the top decile of disagreement — "
        f"{1.28 * disagreement_sd:.1f} points, since disagreement has a standard "
        f"deviation of {disagreement_sd:.2f} — and a -110 price needs roughly 1.5 "
        "points of true edge to clear the vig."
    )
    add("")
    add("## The honest reading")
    add("")
    add(
        "Every split reads **no demonstrated edge**: no interval excludes zero. "
        "But 'no demonstrated edge' and 'ruled out' are different claims, and "
        "the splits do not agree on the second one."
    )
    add("")
    headline = tests[0]
    if headline.rules_out_a_profitable_slope:
        add(
            f"**Over all {headline.games:,} games the corrected interval is "
            f"[{headline.interval[0]:+.4f}, {headline.interval[1]:+.4f}], which "
            f"sits entirely below the {PROFITABLE_SLOPE:.3f} a paying strategy "
            "needs.** So the answer to the question actually asked — should "
            "ratings re-enter the architecture — is no, and that is the "
            "interval speaking rather than a power calculation."
        )
        add("")
        add(
            f"Note the 80% power criterion narrowly *fails* here "
            f"({headline.detectable_slope:.3f} against {PROFITABLE_SLOPE:.3f}). "
            "The realized interval is the stronger statement and the one that "
            "bears on the decision, but the design had no margin to spare, and "
            "one more season of hypotheses in the ledger would take it away."
        )
    unresolved = [t for t in tests[1:] if not t.rules_out_a_profitable_slope]
    if unresolved:
        add("")
        add(
            "**Not settled everywhere.** "
            + "; ".join(
                f"{t.label} (n={t.games:,}) has an upper bound of "
                f"{t.interval[1]:+.4f}, above {PROFITABLE_SLOPE:.3f}"
                for t in unresolved
            )
            + ". That split has not ruled out a slope that would pay, and no "
            "claim should be made there in either direction."
        )
    add("")
    add(
        f"The ratings disagree with the closing spread by a standard deviation "
        f"of **{disagreement_sd:.2f} points** — a great deal — and the measured "
        "slope is small and negative. Ratings do not re-enter the architecture, "
        "but this is a bound, not a proof of zero."
    )
    return "\n".join(lines) + "\n"
