"""Inject an edge of known size and check the lab finds it.

Fifty-three hypotheses, every one returning "no demonstrated edge", and no
evidence anywhere that the harness can detect an edge that exists. `power.py`
answers that arithmetically. This answers it **empirically**, which is the
stronger test: the arithmetic assumes the estimator is unbiased and its
interval is honest, and those are exactly the things that were wrong when this
lab shipped an interval that was sqrt(games) too narrow.

## How an edge is injected

A bet at decimal odds `d` pays `d - 1` on a win and `-1` on a loss, so its
expected return at true win probability `p` is `p*d - 1`. To manufacture a
known edge `e`, set

    p_true = (1 + e) / d

and draw the outcome from `Bernoulli(p_true)`. Every real price, every real
game grouping and every real bet count is preserved; only the outcomes are
resampled. The result is a dataset whose true edge is exactly `e` and whose
correlation structure is the lab's own.

`e = 0` is the null and must be detected about 5% of the time. Anything else is
a broken interval, and a broken interval is what makes a run of nulls
meaningless.

## What a failure means

If the lab misses an edge it should see at this `n`, the harness is broken and
every null it has ever reported is uninformative. If the lab *finds* an edge at
`e = 0` more than about one time in twenty, its intervals are too narrow and
every finding it has ever reported is suspect. Both are worth knowing before a
fifty-fourth hypothesis is tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

#: Two-sided level the lab quotes.
ALPHA = 0.05

#: Replications per injected edge. Enough to estimate a detection rate to
#: within a few points, which is all the precision the question needs.
DEFAULT_TRIALS = 200


def erf(values: np.ndarray) -> np.ndarray:
    """Vectorised error function, so a normal draw becomes a uniform one.

    Hand-rolled because this venv has no scipy, and the alternative — mapping
    the latent shock through ranks — would distort the marginal win
    probability and quietly change the edge being injected.
    """
    x = np.asarray(values, dtype=float)
    sign = np.sign(x)
    z = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * z)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741
           + t * (-1.453152027 + t * 1.061405429))))
    return sign * (1.0 - poly * np.exp(-z * z))


def decimal_odds(american: np.ndarray) -> np.ndarray:
    value = np.asarray(american, dtype=float)
    return np.where(value < 0, 1.0 + 100.0 / np.abs(value), 1.0 + value / 100.0)


@dataclass(frozen=True)
class ControlResult:
    """One injected edge, and how often the lab saw it."""

    injected: float
    trials: int
    detected: int
    mean_measured: float
    correction_factor: float

    @property
    def detection_rate(self) -> float:
        return self.detected / self.trials if self.trials else 0.0

    @property
    def bias(self) -> float:
        """Measured minus injected. A biased estimator is worse than a blind
        one, because it is confidently wrong in a consistent direction."""
        return self.mean_measured - self.injected


@dataclass
class ControlReport:
    bets: int = 0
    games: int = 0
    results: list[ControlResult] = field(default_factory=list)

    @property
    def false_positive_rate(self) -> float | None:
        for entry in self.results:
            if entry.injected == 0.0:
                return entry.detection_rate
        return None

    @property
    def is_sound(self) -> bool:
        """The null must be detected near ALPHA, and a large edge must be found.

        Both halves matter. An interval that never fires is useless and an
        interval that always fires is worse.
        """
        false_positive = self.false_positive_rate
        if false_positive is None or false_positive > 0.12:
            return False
        big = [r for r in self.results if r.injected >= 0.10]
        return bool(big) and all(r.detection_rate >= 0.70 for r in big)


def _clustered_interval(
    profit: np.ndarray, games: np.ndarray, correction_factor: float
) -> tuple[float, float, float]:
    """The lab's own interval: cluster-robust ratio estimator, corrected."""
    frame = pd.DataFrame({"profit": profit, "game": games})
    per_game = frame.groupby("game")["profit"].agg(["sum", "size"])
    total = int(per_game["size"].sum())
    count = len(per_game)
    roi = float(per_game["sum"].sum() / total)
    if count < 2:
        return roi, float("-inf"), float("inf")
    residual = per_game["sum"] - roi * per_game["size"]
    mean_bets = total / count
    variance = float((residual**2).sum() / (count * (count - 1)))
    error = (variance**0.5) / mean_bets * correction_factor
    return roi, roi - 1.96 * error, roi + 1.96 * error


def run(
    bets: pd.DataFrame,
    *,
    edges: tuple[float, ...] = (0.0, 0.02, 0.05, 0.10, 0.20),
    trials: int = DEFAULT_TRIALS,
    correction_factor: float = 1.0,
    intra_game_correlation: float = 0.0,
    seed: int = 0,
) -> ControlReport:
    """Resample outcomes at each injected edge and count detections.

    `bets` needs `american_odds` and a game identifier column named `game_id`.
    Every real price and grouping is kept; only outcomes are redrawn.

    `intra_game_correlation` must be **measured, not assumed**. Drawing every
    bet independently makes the control far easier than reality: the first run
    of this instrument did exactly that and reported 98% power at +2%, which
    was true of a dataset nobody has. Bets in one game share a game script, and
    `power.measured_correlation` reads the real figure off the real bets — 0.036
    for NFL props, which is a design effect of 4.8x rather than the 50x a
    guessed 0.5 implies.

    Correlated outcomes are built through a shared latent shock per game, so
    the injected edge is preserved exactly while the draws inside a game move
    together.
    """
    if bets.empty:
        return ControlReport()
    odds = decimal_odds(bets["american_odds"].to_numpy())
    games = bets["game_id"].astype(str).to_numpy()
    generator = np.random.default_rng(seed)

    report = ControlReport(bets=len(bets), games=len(set(games)))
    for edge in edges:
        probability = np.clip((1.0 + edge) / odds, 0.0, 1.0)
        # A shared latent shock per game gives bets in one game a common
        # component without disturbing each bet's marginal win probability, so
        # the injected edge survives the clustering exactly.
        codes = pd.factorize(games)[0]
        weight = float(np.sqrt(max(intra_game_correlation, 0.0)))
        detected = 0
        measured: list[float] = []
        for _ in range(trials):
            if weight > 0:
                shock = generator.standard_normal(codes.max() + 1)[codes]
                latent = weight * shock + np.sqrt(1 - weight**2) * generator.standard_normal(len(odds))
                # Uniform via the normal CDF, so the marginal stays uniform and
                # P(win) is still exactly `probability`.
                uniform = 0.5 * (1.0 + erf(latent / np.sqrt(2)))
            else:
                uniform = generator.random(len(odds))
            won = uniform < probability
            profit = np.where(won, odds - 1.0, -1.0)
            roi, low, high = _clustered_interval(profit, games, correction_factor)
            measured.append(roi)
            if low > 0.0 or high < 0.0:
                detected += 1
        report.results.append(
            ControlResult(
                injected=edge,
                trials=trials,
                detected=detected,
                mean_measured=float(np.mean(measured)),
                correction_factor=correction_factor,
            )
        )
    return report


def render(report: ControlReport) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Can this lab see an edge that is really there?")
    add("")
    add(
        "Fifty-three hypotheses, every one returning **no demonstrated edge**, "
        "and until now no evidence the harness could detect one that existed. "
        "A harness that cannot is guaranteed to report a null whether or not "
        "there is something to find."
    )
    add("")
    if not report.results:
        add(
            "**Nothing was injected.** That is an absence, not a pass: the "
            "harness remains unvalidated and every null it has reported is "
            "uninformative."
        )
        return "\n".join(lines) + "\n"
    add(
        f"Outcomes resampled at a known true edge on the real prices and real "
        f"game structure — **{report.bets:,} bets across {report.games:,} "
        f"games** — so the correct answer is known and only the outcomes move."
    )
    add("")
    add("| Injected edge | Measured (mean) | Bias | Detected | Detection rate |")
    add("|---:|---:|---:|---:|---:|")
    for entry in report.results:
        add(
            f"| {entry.injected:+.0%} | {entry.mean_measured:+.2%} | "
            f"{entry.bias:+.3%} | {entry.detected}/{entry.trials} | "
            f"{entry.detection_rate:.0%} |"
        )
    add("")
    false_positive = report.false_positive_rate
    if false_positive is not None:
        add(
            f"**At a true edge of zero the lab fired {false_positive:.0%} of "
            f"the time**, against the {ALPHA:.0%} it should. "
            + (
                "**That is far too rarely.** An interval that never fires "
                "falsely is not a careful interval, it is an over-corrected "
                "one, and the power it gives up is real: the cumulative "
                "multiple-testing correction now costs more than the false "
                "positives it prevents. This is the ratchet — a correction "
                "that grows with every hypothesis tested guarantees that "
                "nothing ever ships, and it is a design choice rather than a "
                "fact about the market."
                if false_positive < 0.02
                else "That is the interval behaving."
                if false_positive <= 0.12
                else "**That is too often: the intervals are too narrow, and "
                "every finding this lab has reported is suspect.**"
            )
        )
        add("")
        weak = [
            r for r in report.results
            if 0.0 < r.injected <= 0.03 and r.detection_rate < 0.80
        ]
        if weak:
            worst = min(weak, key=lambda r: r.injected)
            add(
                f"**And a realistic edge would be missed.** At a true "
                f"{worst.injected:+.0%} this design found it "
                f"{worst.detection_rate:.0%} of the time — so a null here "
                f"rules out a large edge and says nothing about a "
                f"{worst.injected:+.0%} one. Any null must be read as "
                "'no edge above the detectable floor', never as 'no edge'."
            )
            add("")
    if report.is_sound:
        add(
            "**The harness is sound.** It finds a large edge reliably and "
            "does not invent one from noise, so a null from it is a statement "
            "about the market rather than about the instrument — within the "
            "detectable range `power.py` reports, and not below it."
        )
    else:
        add(
            "**The harness did not pass.** Either it misses an edge it should "
            "see at this sample size, or it invents one too often. Until that "
            "is fixed, every null this lab has produced is uninformative and "
            "no new hypothesis is worth testing."
        )
    add("")
    add(
        "This validates the **estimator and its interval**. It cannot validate "
        "the settlement, the join or the prices — those have their own "
        "instruments, and each of them has caught a real defect."
    )
    return "\n".join(lines) + "\n"
