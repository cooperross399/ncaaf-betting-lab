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

#: Total buckets the empirical margin shape is conditioned on, with the
#: measured margin sd for each. Boundaries chosen from the measurement above,
#: not from intuition, and deliberately coarse: four buckets over 1,606 games
#: is about 400 apiece, which is enough for a shape and not enough for more.
TOTAL_BUCKETS: tuple[tuple[float, float], ...] = (
    (0.0, 45.0),
    (45.0, 55.0),
    (55.0, 65.0),
    (65.0, 1000.0),
)

#: Widest tilt allowed before the model refuses. A tilt this large is being
#: asked to move an empirical shape further than the data supports, and the
#: honest answer is no opinion rather than a confident extrapolation.
MAX_TILT_POINTS = 35.0


def bucket_for(total: float) -> tuple[float, float]:
    for low, high in TOTAL_BUCKETS:
        if low <= total < high:
            return (low, high)
    return TOTAL_BUCKETS[-1]


def empirical_margin_pmf(margins: list[int]) -> dict[int, float]:
    """The observed margin distribution, unsmoothed.

    Unsmoothed on purpose: smoothing is what a normal approximation does, and
    the whole point here is the lumps a normal cannot represent.
    """
    if not margins:
        return {}
    counts: dict[int, int] = {}
    for margin in margins:
        counts[int(margin)] = counts.get(int(margin), 0) + 1
    total = sum(counts.values())
    return {k: v / total for k, v in sorted(counts.items())}


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
    total: float,
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
    bucket = bucket_for(total)
    pmf = margins_by_bucket.get(bucket)
    if not pmf:
        raise KeyError(
            f"No empirical margin shape for total bucket {bucket}. A shape "
            "borrowed from another bucket would price this game with the wrong "
            "dispersion — measured college margin sd runs 16.1 at low totals "
            "to 22.7 at high ones."
        )
    return MarginModel(
        pmf=tilt_to_mean(pmf, implied_margin),
        implied_margin=implied_margin,
        total=total,
    )
