"""Total-points probabilities: market mean in, measured shape out.

The twin of `margin.py`, built the same way for the same reason. The mean comes
from the market's own total, because this lab's ratings add nothing the
closing price does not already carry (`data/outputs/ratings_residual.md`). The
shape comes from finished college games whose closing total sat in the same
bucket, so a 40-point game is never priced with a 70-point game's dispersion.

## What is measured, and what is not

Measured on 3,864 FBS-vs-FBS games, 2021-2025 (`build_line_table.py`): the
realised total misses the consensus closing total with a standard deviation of
**15.76 points**, against **15.29** for the margin against the spread. So a
college total is about as uncertain as a college spread, which is not what the
NFL's shape would say.

**Not measured:** whether this shape beats a correctly scaled normal on
held-out games. The margin model ran that test and the answer was "not
demonstrated" (+0.0142 nats, interval spanning zero). Nobody has run it for
totals. This module prices whole-number totals from measured mass, which is
the reason it exists, and makes no claim beyond that.

## Overtime is inside the shape, not modelled

A college overtime is a two-point shootout from the 25, and it adds points on
a distribution unlike anything in regulation. Every game in the training
population that went to overtime contributes its final total, overtime
included, so the shape carries overtime at its historical rate. It does not
know which games are more likely to go there.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ncaaf_betting_lab.models.margin import (
    FALLBACK_WEIGHT,
    SMOOTHING_BANDWIDTH,
    tilt_to_mean,
)

#: Closing-total buckets the empirical shape is conditioned on. Chosen so the
#: thinnest holds 483 games in 2021-2025 rather than to any key number: unlike
#: margins, totals have no endgame strategy piling them up on one value.
TOTAL_BUCKETS: tuple[tuple[float, float], ...] = (
    (0.0, 45.0), (45.0, 50.0), (50.0, 55.0), (55.0, 60.0), (60.0, 65.0),
    (65.0, 200.0),
)

#: Same floor as the margin model, for the same reason.
MINIMUM_BUCKET_GAMES = 150

#: Highest total the grid carries. The highest FBS-vs-FBS total 2021-2025 is
#: well inside it; a game beyond it would be a shape asked to extrapolate.
MAX_TOTAL = 160


def bucket_for(total_line: float) -> tuple[float, float]:
    for low, high in TOTAL_BUCKETS:
        if low <= total_line < high:
            return (low, high)
    return TOTAL_BUCKETS[-1] if total_line > 0 else TOTAL_BUCKETS[0]


def empirical_total_pmf(
    totals: list[int],
    *,
    bandwidth: float = SMOOTHING_BANDWIDTH,
    fallback_weight: float = FALLBACK_WEIGHT,
) -> dict[int, float]:
    """Observed totals, lightly smoothed, nothing in range impossible.

    Not `margin.empirical_margin_pmf`, and the difference is the one line that
    matters: that function's broad fallback is centred on ZERO, which is right
    for a margin and would put fallback mass on totals of 0 and below here.
    This one centres it on the sample's own mean.
    """
    if not totals:
        return {}
    counts: dict[int, float] = {}
    for value in totals:
        counts[int(value)] = counts.get(int(value), 0.0) + 1.0
    observed = np.array(sorted(counts), dtype=float)
    weights = np.array([counts[int(x)] for x in observed], dtype=float)
    weights = weights / weights.sum()

    grid = np.arange(0, MAX_TOTAL + 1, dtype=float)
    kernel = np.exp(-0.5 * ((grid[:, None] - observed[None, :]) / bandwidth) ** 2)
    kernel = kernel / np.maximum(kernel.sum(axis=0, keepdims=True), 1e-300)
    smoothed = (kernel * weights[None, :]).sum(axis=1)

    mean = float((weights * observed).sum())
    spread = float(np.sqrt((weights * (observed - mean) ** 2).sum()))
    broad = np.exp(-0.5 * ((grid - mean) / max(spread, 1.0)) ** 2)
    broad = broad / broad.sum()

    blended = (1.0 - fallback_weight) * smoothed + fallback_weight * broad
    blended = blended / blended.sum()
    return {int(x): float(w) for x, w in zip(grid, blended) if w > 1e-9}


@dataclass(frozen=True)
class TotalModel:
    """Total-points probabilities for one fixture, anchored on the market."""

    pmf: dict[int, float]
    total_line: float

    def probability_over(self, line: float, *, side: str) -> tuple[float, float]:
        """`(win, push)` for `over` or `under` at `line`, push mass exact."""
        win = push = 0.0
        for total, probability in self.pmf.items():
            if total == line:
                push += probability
            elif (total > line) == (side == "over"):
                win += probability
        return win, push


def build(
    totals_by_bucket: dict[tuple[float, float], dict[int, float]],
    *,
    total_line: float,
) -> TotalModel:
    """A total model for one fixture, from the market's consensus total."""
    bucket = bucket_for(total_line)
    pmf = totals_by_bucket.get(bucket)
    if not pmf:
        raise KeyError(
            f"No empirical total shape for bucket {bucket}. A shape borrowed "
            "from another bucket prices the game at the wrong dispersion."
        )
    return TotalModel(pmf=tilt_to_mean(pmf, total_line), total_line=total_line)
