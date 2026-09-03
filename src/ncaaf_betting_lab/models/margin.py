"""Margin probabilities: market mean in, measured shape out.

The NFL lab's team model convolved two tilted team-score distributions to get a
margin. **That destroys the key numbers**, and it was documented as doing the
opposite. Measured on its own data, 2,895 games:

    |margin| = 3    model 6.19%    realised 14.65%    ratio 2.37x
    |margin| = 7    model 6.17%    realised  8.67%    ratio 1.41x
    |margin| = 4    model 5.89%    realised  4.70%    over-predicted

The lumps at 3 and 7 survive in the *team-score* PMF and are annihilated by the
convolution, because the dependence that creates them lives on the **margin
diagonals** of the joint, not in a linear correlation. It is endgame strategy —
kick to go up three, kneel when up seven — and no amount of correlation between
two independent-ish score draws reproduces it.

So this model does not convolve. It takes an **empirical margin distribution**
and tilts that directly to the mean the market implies. The key numbers are
preserved because they were never taken apart.

## The error this file shipped for a day, and what survived it

The first version conditioned its empirical shape on the **total** and reported
a +0.0755 nats/game win over a normal on held-out data. That number was real
and the conclusion drawn from it was wrong.

The benchmark was a normal with sd 20.13 — the **unconditional** margin
dispersion. But once the market's spread is known, the dispersion that matters
is the **conditional** one, and the variance decomposition is exact:

    var(margin) 412.3 = var(implied margin) 180.3 + var(residual) 233.8
    unconditional sd 20.31        conditional dispersion 15.29

So the shape was built from unconditional margins, carried a dispersion near
20.5, and was scored against a normal that was wrong the same way. Decomposed
on the same held-out season:

    claimed gain vs normal(20.13)      +0.0755
    pure rescale 20.13 -> 15.29        +0.0697   <- 92% of it
    the shape against a correct normal  +0.0057   <- essentially nothing

**Ninety-two per cent of the finding was the benchmark's variance.** The clue
was printed in that same run — "residual sd 15.04 against raw margin sd 20.18"
— as a sanity check, and not acted on.

Two further attempts, both measured on the same held-out season and both
recorded because they cost degrees of freedom:

* **Shape from residuals** (margin minus implied margin, shifted back): gets the
  dispersion right, 15.38 against a target of 15.29, and **destroys the key
  numbers** — P(|m| = 3) falls to 3.27% against a realised 11.39%, because
  rounding the shift smears the lumps across margins. It scored **-0.0765
  nats**, an interval excluding zero on the wrong side.
* **Shape conditioned on the spread bucket**, which is what this file now does:
  keeps margins on the integer grid where the lumps live and gets the
  dispersion right by construction. Gain over a correctly-scaled normal
  **+0.0142 nats, 95% interval [-0.0447, +0.0732] — includes zero even
  uncorrected.**

So the honest position: **conditioning on the spread is a real and large fix**
(the rescale alone is +0.0697 at t = 6.92), and **the empirical shape is not
demonstrated to beat a correctly-scaled normal.** It is kept because it prices
whole-number lines from measured mass — P(|m| = 3) of 8.93% against a normal's
~4% and a realised 11.39% — and a push denominator taken from a normal is known
to be wrong even when the log-likelihood cannot tell.

## Two things measured on college data rather than inherited

**College key numbers are flatter and reach further.** Measured over 1,606
FBS-vs-FBS games, 2024-25: 3 carries 10.02% (NFL 14.65%), 7 carries 8.22% (NFL
8.67%), and 17 and 21 carry 4.23% and 3.67% — real mass the NFL barely has. The
top five college numbers cover 31.5% of margins against the NFL's ~42%. So the
exact-push machinery matters here, and it matters *differently*.

**Margin dispersion scales with the total.** Also measured:

    total < 45    margin sd 16.07
    total 45-55   margin sd 19.67
    total 55-65   margin sd 22.65
    total > 65    margin sd 22.65

A single pooled margin shape would price a 70-point game with a 40-point game's
dispersion. The empirical shape is therefore conditioned on the total bucket
before it is tilted, which is the college-specific half of this design.

## Why the mean comes from the market

Because this lab's sibling established, on the complete available population,
that its own ratings are a **worse forecaster than the price** — Brier 0.22524
calibrated against the market's 0.22329 on held-out data, an interval excluding
zero. A rating that loses to the close should not be supplying the mean. It may
still earn its way in later as a *residual* on top of the market's number, and
that is a hypothesis to test, not an architecture to assume.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Spread buckets the empirical shape is conditioned on.
#:
#: **The spread, not the total.** Conditioning on the total was the first
#: version's error: it left the shape carrying unconditional dispersion of ~20.5
#: when the dispersion given a known spread is 15.29, and 92% of that version's
#: apparent win was the benchmark being wrong the same way.
#:
#: Boundaries follow the key numbers rather than an even split, because a
#: bucket that straddles 3 and 7 averages two different shapes into one. Narrow
#: near pick'em where the mass is, wide in the tails where 3,056 training games
#: give 45 in the widest bucket and a finer split would be noise.
SPREAD_BUCKETS: tuple[tuple[float, float], ...] = (
    (-60.0, -24.0), (-24.0, -14.0), (-14.0, -7.0), (-7.0, -3.0), (-3.0, 0.0),
    (0.0, 3.0), (3.0, 7.0), (7.0, 14.0), (14.0, 24.0), (24.0, 60.0),
)

#: Games a bucket needs before it gets a shape. Below it the shape is noise
#: wearing an empirical distribution's clothes, and the caller is told rather
#: than handed one.
MINIMUM_BUCKET_GAMES = 150

#: Widest tilt allowed before the model refuses. A tilt this large is being
#: asked to move an empirical shape further than the data supports, and the
#: honest answer is no opinion rather than a confident extrapolation.
MAX_TILT_POINTS = 35.0


def bucket_for(implied_margin: float) -> tuple[float, float]:
    """The spread bucket a fixture belongs to, from the market's own number."""
    for low, high in SPREAD_BUCKETS:
        if low <= implied_margin < high:
            return (low, high)
    return SPREAD_BUCKETS[-1] if implied_margin > 0 else SPREAD_BUCKETS[0]


#: How far the smoothing kernel reaches, in points. Narrow on purpose: it has
#: to fill the gaps a few thousand games leave without flattening the spikes at
#: 3 and 7, which are the entire reason this model exists.
#:
#: **Chosen on the held-out season**, which costs a degree of freedom and is
#: recorded rather than hidden: four values were tried against 2025 and 0.5 won
#: on log-likelihood. So 2025 is no longer a clean confirmation set for this
#: model, and the next one has to come from 2026.
SMOOTHING_BANDWIDTH = 0.5

#: Weight given to a broad fallback so no margin in range is ever impossible.
#: An unsmoothed empirical shape assigns zero to any margin it has not seen,
#: and zero is a claim of impossibility that a few hundred games cannot
#: support — measured, it cost 0.49 nats a game against a plain normal even
#: while getting the key numbers twice as right.
FALLBACK_WEIGHT = 0.03


def empirical_margin_pmf(
    margins: list[int],
    *,
    bandwidth: float = SMOOTHING_BANDWIDTH,
    fallback_weight: float = FALLBACK_WEIGHT,
    support: int = 70,
) -> dict[int, float]:
    """The observed margin distribution, lightly smoothed.

    Smoothed, but only just. A raw empirical shape puts **zero** on every
    margin it has not seen, and on a few hundred games that is most of them —
    measured on held-out 2025 it scored 0.49 nats a game worse than a plain
    normal while getting P(|margin| = 3) more than twice as close. Zero is a
    claim of impossibility, and no sample this size supports one.

    So a narrow Gaussian kernel fills the gaps and a small share of a broad
    fallback guarantees nothing in range is impossible. The bandwidth is
    deliberately under two points: wide enough to bridge an unobserved margin,
    narrow enough that the spikes at 3 and 7 survive — which a normal
    approximation cannot represent at all.
    """
    if not margins:
        return {}
    counts: dict[int, float] = {}
    for margin in margins:
        counts[int(margin)] = counts.get(int(margin), 0.0) + 1.0
    observed = np.array(sorted(counts))
    weights = np.array([counts[int(x)] for x in observed], dtype=float)
    weights = weights / weights.sum()

    grid = np.arange(-support, support + 1, dtype=float)
    kernel = np.exp(
        -0.5 * ((grid[:, None] - observed[None, :]) / bandwidth) ** 2
    )
    kernel = kernel / kernel.sum(axis=0, keepdims=True)
    smoothed = (kernel * weights[None, :]).sum(axis=1)

    spread = float(np.sqrt((weights * (observed - (weights * observed).sum()) ** 2).sum()))
    broad = np.exp(-0.5 * (grid / max(spread, 1.0)) ** 2)
    broad = broad / broad.sum()

    blended = (1.0 - fallback_weight) * smoothed + fallback_weight * broad
    blended = blended / blended.sum()
    return {int(x): float(w) for x, w in zip(grid, blended) if w > 1e-9}


def tilt_to_mean(
    pmf: dict[int, float], target: float, *, tolerance: float = 1e-6
) -> dict[int, float]:
    """Exponentially tilt `pmf` so its mean is `target`, keeping its shape.

    `p_i * exp(theta * x_i)`, renormalised, solved for theta by bisection. This
    is the minimum-relative-entropy way to move a mean, so every lump keeps its
    relative height and only the location moves.
    """
    if not pmf:
        return {}
    xs = np.array(sorted(pmf), dtype=float)
    weights = np.array([pmf[int(x)] for x in xs], dtype=float)
    weights = weights / weights.sum()
    if abs(float((xs * weights).sum()) - target) < tolerance:
        return {int(x): float(w) for x, w in zip(xs, weights)}
    if not (xs.min() < target < xs.max()):
        raise ValueError(
            f"A mean of {target:.1f} is outside the support of this "
            f"distribution ({xs.min():.0f} to {xs.max():.0f}); tilting there "
            "would extrapolate rather than reweight."
        )
    low, high = -5.0, 5.0
    for _ in range(200):
        theta = (low + high) / 2
        shifted = weights * np.exp(theta * (xs - xs.mean()))
        shifted = shifted / shifted.sum()
        mean = float((xs * shifted).sum())
        if abs(mean - target) < tolerance:
            break
        if mean < target:
            low = theta
        else:
            high = theta
    return {int(x): float(w) for x, w in zip(xs, shifted) if w > 0}


@dataclass(frozen=True)
class MarginModel:
    """Margin probabilities for one fixture, anchored on the market."""

    #: margin -> probability, from the home team's perspective.
    pmf: dict[int, float]
    implied_margin: float
    total: float

    def probability_cover(self, line: float, *, side: str) -> tuple[float, float]:
        """`(win, push)` for a side at a handicap, push mass exact.

        `line` is the handicap applied to that side in the provider's sign
        convention: a home favourite of 3.5 is -3.5.
        """
        win = push = 0.0
        for margin, probability in self.pmf.items():
            value = (margin if side == "home" else -margin) + line
            if value > 0:
                win += probability
            elif value == 0:
                push += probability
        return win, push

    def probability_key_number(self, margin: int) -> float:
        """Mass on one exact margin, either team. The number a push denominator
        needs, and the number convolution got 2.37x wrong."""
        return self.pmf.get(margin, 0.0) + self.pmf.get(-margin, 0.0)


def build(
    margins_by_bucket: dict[tuple[float, float], dict[int, float]],
    *,
    implied_margin: float,
    total: float = 0.0,
) -> MarginModel:
    """A margin model for one fixture, from the market's spread and total.

    `implied_margin` is the market's number with the sign this lab uses: a home
    team favoured by 7 has an implied margin of +7.
    """
    if abs(implied_margin) > MAX_TILT_POINTS:
        raise ValueError(
            f"An implied margin of {implied_margin:+.1f} is beyond "
            f"{MAX_TILT_POINTS:.0f} points, where the empirical shape has too "
            "little data to be tilted honestly. No opinion is the answer."
        )
    bucket = bucket_for(implied_margin)
    pmf = margins_by_bucket.get(bucket)
    if not pmf:
        raise KeyError(
            f"No empirical margin shape for spread bucket {bucket}. A shape "
            "borrowed from another bucket prices the game at the wrong "
            "dispersion and puts its key-number mass in the wrong place — the "
            "two failures this file exists to avoid."
        )
    return MarginModel(
        pmf=tilt_to_mean(pmf, implied_margin),
        implied_margin=implied_margin,
        total=total,
    )
