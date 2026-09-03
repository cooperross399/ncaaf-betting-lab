"""How many bets it takes to see an edge, and whether this lab can see one at all.

Fifty-three hypotheses have been tested across this lab and its NFL sibling.
Every one returned "no demonstrated edge". **Not once has either lab checked
that it can detect an edge that genuinely exists.**

That is a hole, and it is the specific hole that makes a long run of nulls
uninformative: a harness that cannot detect a true +2% is guaranteed to report
"no demonstrated edge" whether or not one is there, and it will do so with
clean intervals and careful prose. Fifty-three of those is not fifty-three
pieces of evidence. It may be one broken instrument, used fifty-three times.

## The arithmetic that motivated this

A -110 bet pays +0.909 or -1. At a true edge `e`, the per-bet return has mean
`e` and standard deviation near 1, so detecting `e` at 80% power and 5%
two-sided needs roughly `(1.96 + 0.84)^2 / e^2` INDEPENDENT bets — about 14,000
at e = 2%. Bets inside one game are not independent, and this lab's cumulative
multiple-testing correction currently widens intervals by x1.69, which raises
the requirement by that factor squared.

College football supplies roughly 760 FBS-vs-FBS games a season.

So the honest question is not "did we find an edge" but **"could we have?"** —
and it has to be answered per hypothesis, in advance, or a null means nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import pandas as pd

#: Two-sided significance the lab quotes everywhere.
ALPHA = 0.05

#: Power to detect. 80% is the convention; it also means a true edge is missed
#: one time in five, which is worth saying out loud when a null is reported.
POWER = 0.80

#: Standard deviation of the per-bet return at a price near -110. A won bet
#: pays +0.909, a lost one -1, so with p near 0.5 the SD is close to 0.95-1.00.
#: Using 1.0 is very slightly conservative and avoids implying a precision the
#: input does not have.
PER_BET_SD = 1.0


@dataclass(frozen=True)
class PowerRequirement:
    """What it would take to see an edge of a given size."""

    edge: float
    correction_factor: float
    intra_game_correlation: float
    bets_per_game: float

    @property
    def independent_bets(self) -> int:
        """Bets needed if every bet were its own independent observation."""
        z_alpha = NormalDist().inv_cdf(1 - ALPHA / 2) * self.correction_factor
        z_power = NormalDist().inv_cdf(POWER)
        return int(((z_alpha + z_power) * PER_BET_SD / self.edge) ** 2 + 0.999)

    @property
    def design_effect(self) -> float:
        """How much clustering inflates the requirement.

        Bets inside one game share its result, so `m` bets on a game carry
        `1 + (m - 1) * rho` bets' worth of information, not `m`.
        """
        return 1.0 + (self.bets_per_game - 1.0) * self.intra_game_correlation

    @property
    def clustered_bets(self) -> int:
        return int(self.independent_bets * self.design_effect + 0.999)

    @property
    def games(self) -> int:
        return int(self.clustered_bets / max(self.bets_per_game, 1e-9) + 0.999)

    def seasons(self, games_per_season: int) -> float:
        return self.games / max(games_per_season, 1)


def measured_correlation(profit: pd.Series, game: pd.Series) -> float:
    """The intra-game correlation of bet returns, from the data.

    **Measure this; do not guess it.** The first version of this module
    defaulted to 0.5 on intuition, which made a +2% edge look like it needed 80
    NFL seasons. Measured on the real bets it is **0.036** — a design effect of
    4.8x rather than 50x, and a completely different conclusion about what the
    lab can see.

    One-way ANOVA estimator, which handles the unequal cluster sizes a real
    slate produces.
    """
    frame = pd.DataFrame({"profit": pd.to_numeric(profit, errors="coerce"),
                          "game": game.astype(str)}).dropna()
    if frame.empty:
        return 0.0
    grouped = frame.groupby("game")["profit"]
    sizes = grouped.size()
    means = grouped.mean()
    total, clusters = len(frame), len(sizes)
    if clusters < 2 or total <= clusters:
        return 0.0
    grand = float(frame["profit"].mean())
    between = float((sizes * (means - grand) ** 2).sum()) / (clusters - 1)
    within = float(
        ((frame["profit"] - frame.groupby("game")["profit"].transform("mean")) ** 2).sum()
    ) / (total - clusters)
    k0 = (total - float((sizes**2).sum()) / total) / (clusters - 1)
    denominator = between + (k0 - 1) * within
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, (between - within) / denominator))


def requirement(
    edge: float,
    *,
    correction_factor: float = 1.0,
    intra_game_correlation: float,
    bets_per_game: float = 3.0,
) -> PowerRequirement:
    """Bets needed to detect `edge` (as a decimal, e.g. 0.02 for +2%)."""
    if edge <= 0:
        raise ValueError("An edge to detect must be positive.")
    return PowerRequirement(
        edge=edge,
        correction_factor=correction_factor,
        intra_game_correlation=intra_game_correlation,
        bets_per_game=bets_per_game,
    )


def detectable_edge(
    games: int,
    *,
    correction_factor: float = 1.0,
    intra_game_correlation: float,
    bets_per_game: float = 3.0,
) -> float:
    """The smallest edge this many games could detect at 80% power.

    The number to quote beside every null. "No demonstrated edge over 800
    games" means nothing until it is paired with "and this design could only
    have seen an edge above X".
    """
    z_alpha = NormalDist().inv_cdf(1 - ALPHA / 2) * correction_factor
    z_power = NormalDist().inv_cdf(POWER)
    design = 1.0 + (bets_per_game - 1.0) * intra_game_correlation
    effective = games * bets_per_game / design
    return float((z_alpha + z_power) * PER_BET_SD / (effective ** 0.5))


def render(
    edges: tuple[float, ...] = (0.01, 0.02, 0.03, 0.05, 0.10),
    *,
    correction_factor: float,
    games_per_season: int,
    intra_game_correlation: float,
    bets_per_game: float = 3.0,
) -> str:
    """The table that has to sit beside any null this lab reports."""
    lines: list[str] = []
    add = lines.append
    add("# Could this lab have seen an edge if there were one?")
    add("")
    add(
        "Fifty-three hypotheses, every one returning **no demonstrated edge**. "
        "That is only evidence if the design could have detected an edge that "
        "existed. A harness that cannot is guaranteed to report a null whether "
        "or not one is there — and to do it with clean intervals and careful "
        "prose."
    )
    add("")
    add(
        f"At {POWER:.0%} power, {ALPHA:.0%} two-sided, with the cumulative "
        f"multiple-testing correction of **x{correction_factor:.2f}** applied, "
        f"assuming **{bets_per_game:.0f} bets per game** correlated at "
        f"**{intra_game_correlation:.2f}** within a game:"
    )
    add("")
    add("| True edge | Independent bets | Clustered bets | Games | Seasons |")
    add("|---:|---:|---:|---:|---:|")
    for edge in edges:
        need = requirement(
            edge,
            correction_factor=correction_factor,
            intra_game_correlation=intra_game_correlation,
            bets_per_game=bets_per_game,
        )
        add(
            f"| {edge:+.0%} | {need.independent_bets:,} | "
            f"{need.clustered_bets:,} | {need.games:,} | "
            f"{need.seasons(games_per_season):.1f} |"
        )
    add("")
    floor = detectable_edge(
        games_per_season,
        correction_factor=correction_factor,
        intra_game_correlation=intra_game_correlation,
        bets_per_game=bets_per_game,
    )
    add(
        f"**One season of {games_per_season:,} games can only detect an edge "
        f"above {floor:+.1%}.** Anything smaller is invisible to settled "
        "profit and loss here, however many seasons are pooled, because the "
        "correction grows as fast as the sample does."
    )
    add("")
    add(
        "**This does not say there is no edge. It says settled results cannot "
        "answer the question at these sample sizes**, and a null reported "
        "without this table beside it is not a finding — it is the design "
        "speaking, not the market."
    )
    return "\n".join(lines) + "\n"
