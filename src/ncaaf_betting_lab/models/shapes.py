"""Fit the margin and total shapes the card prices from, walk-forward.

Both shapes come from `data/processed/line_table.csv`, which
`scripts/build_line_table.py` builds by joining cfbfastR's free closing lines
to finished FBS-vs-FBS games. A shape used to price a game in season S is
fitted on seasons strictly before S, so nothing the card prices has seen the
season it is pricing.

The spread in that table is the HOME team's handicap (`build_line_table.py`
keeps only the home row, because averaging both sides collapses every spread
to zero). So the market's implied home margin is the negative of the closing
consensus. Verified 2026-10-01 rather than assumed: over 3,864 games
2021-2025, `corr(-close_consensus, margin)` is +0.658.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ncaaf_betting_lab.models import margin as margin_model
from ncaaf_betting_lab.models import total as total_model


@dataclass
class Shapes:
    """Every bucket's shape, and the buckets refused for want of games."""

    margins: dict[tuple[float, float], dict[int, float]] = field(default_factory=dict)
    totals: dict[tuple[float, float], dict[int, float]] = field(default_factory=dict)
    #: bucket -> games, for every bucket below the floor. Printed on the card,
    #: so a fixture with no opinion says which bucket was too thin.
    thin_margin_buckets: dict[tuple[float, float], int] = field(default_factory=dict)
    thin_total_buckets: dict[tuple[float, float], int] = field(default_factory=dict)
    seasons: tuple[int, ...] = ()
    games: int = 0

    def summary(self) -> str:
        if not self.games:
            return (
                "**No shape was fitted** — the line table is missing or holds no "
                "season before this one, so no fixture can be priced."
            )
        span = f"{min(self.seasons)}-{max(self.seasons)}"
        line = (
            f"Shapes fitted on {self.games:,} finished FBS-vs-FBS games, "
            f"{span}: {len(self.margins)} of {len(margin_model.SPREAD_BUCKETS)} "
            f"spread buckets and {len(self.totals)} of "
            f"{len(total_model.TOTAL_BUCKETS)} total buckets carry enough games."
        )
        thin = [
            f"spread {low:+g} to {high:+g} ({n} games)"
            for (low, high), n in sorted(self.thin_margin_buckets.items())
        ] + [
            f"total {low:g} to {high:g} ({n} games)"
            for (low, high), n in sorted(self.thin_total_buckets.items())
        ]
        if thin:
            line += (
                " Below the floor, so fixtures there get no opinion: "
                + "; ".join(thin) + "."
            )
        return line


def fit(table: pd.DataFrame, *, before_season: int) -> Shapes:
    """Shapes from every game in `table` played in a season before `before_season`."""
    shapes = Shapes()
    required = {"season", "market", "close_consensus", "margin", "total_points"}
    if table.empty or not required <= set(table.columns):
        return shapes
    history = table[pd.to_numeric(table["season"], errors="coerce") < int(before_season)]
    history = history.dropna(subset=["close_consensus", "margin", "total_points"])
    if history.empty:
        return shapes
    shapes.seasons = tuple(sorted(int(s) for s in history["season"].unique()))

    spreads = history[history["market"] == "spread"]
    shapes.games = int(spreads["game_id"].nunique()) if "game_id" in spreads else len(spreads)
    implied = -spreads["close_consensus"].astype(float)
    for low, high in margin_model.SPREAD_BUCKETS:
        rows = spreads[(implied >= low) & (implied < high)]
        if len(rows) < margin_model.MINIMUM_BUCKET_GAMES:
            shapes.thin_margin_buckets[(low, high)] = len(rows)
            continue
        shapes.margins[(low, high)] = margin_model.empirical_margin_pmf(
            [int(m) for m in rows["margin"]]
        )

    totals = history[history["market"] == "total"]
    line = totals["close_consensus"].astype(float)
    for low, high in total_model.TOTAL_BUCKETS:
        rows = totals[(line >= low) & (line < high)]
        if len(rows) < total_model.MINIMUM_BUCKET_GAMES:
            shapes.thin_total_buckets[(low, high)] = len(rows)
            continue
        shapes.totals[(low, high)] = total_model.empirical_total_pmf(
            [int(t) for t in rows["total_points"]]
        )
    return shapes
