"""Closing-line value: did the price move toward the bet or away from it?

## Why this matters more here than anywhere else

An NFL season is 272 games. The detection arithmetic says roughly six hundred
bets separate a real +8% edge from zero, so a season of results is barely a
signal and half a season is none. **CLV is the fastest honest signal available
at these sample sizes** — it measures whether the market agreed with the model
by the time it stopped arguing, and it converges far faster than profit does.

It is also the check that stops a good run being mistaken for a good model:

> **A winning record with negative CLV is variance.** A losing record with
> positive CLV is a model that was right and unlucky. Both sentences are
> printed in those words wherever the numbers support them.

## What is compared to what

The backtest takes the **best available** card-time price, because that is what
a card would reach across nine books. So the fair comparison is the **best
available closing price** — comparing a best-of-nine entry against a single
book's close would manufacture CLV out of shopping.

CLV is reported in probability points: `closing_implied − card_implied`. A
positive number means the price you took implied a lower probability than the
close did, which is the direction that pays.

## The window has to be wide enough for a line to move

Measured on the first three seasons bought: **55.7% of wagers had an identical
price at T-60 and T-5**, and among the 44% that moved, the model's selections
went **exactly 50/50**. (The 55.7% is a property of the prices and stands; the
50/50 was computed before the cross-season settlement fix, on selections that
have since changed. It is kept because it is the observation that bought the
wider window, and the wider window is what the report now uses.)

That is a real null over that window and it is also a weak test, because the
window is 55 minutes. A prop line mostly does not move in the last hour; the
argument the market is having about it happens over days. Reading a near-zero
mean CLV across a 55-minute window as "the model has no information" would be
reading the window rather than the model.

So CLV is measured against the **earliest** snapshot bought, not merely an
earlier one, and the gap is printed beside the number. A CLV figure without
its window is not a result.

## What it cannot do

CLV cannot make a losing model profitable, and a market with no closing
snapshot has no CLV — that is an absence, counted and named, never a zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ncaaf_betting_lab.forward_evidence import american_to_implied
from ncaaf_betting_lab.reports.props_backtest import (
    CARD_TIME,
    CLOSING,
    MINIMUM_BETS,
    best_price_per_selection,
    label_snapshots,
)


#: The columns that make two rows the same wager at two moments.
MATCH_KEYS = ("event_id", "market", "player", "selection", "line")

#: Below this, a mean CLV is not "positive" or "negative" — it is nothing.
#: Half a probability point. With a hundred thousand bets almost any
#: departure from zero is *statistically* distinguishable, and two hundredths
#: of a point still cannot matter to anyone. The first version of this report
#: called +0.02% "positive CLV, consistent with the return", which is a
#: sentence that reads like a confirmation and contains none.
MATERIAL_CLV = 0.005


@dataclass
class MarketCLV:
    market: str
    bets: int = 0
    matched: int = 0
    mean_clv: float = 0.0
    positive_share: float = 0.0
    roi: float = 0.0
    #: Wagers whose price actually changed between the two snapshots, and the
    #: share of those that moved **toward** the bet. This is the legible
    #: number: a mean CLV of +0.06 probability points is hard to read, and
    #: "the line moved toward these bets 51% of the time" is not.
    movers: int = 0
    moved_toward: float = 0.0

    @property
    def unmatched(self) -> int:
        return self.bets - self.matched

    def reading(self) -> str:
        """The sentence the numbers support, in the words the brief fixes."""
        # Three points either side of a half. With ten thousand movers, 48%
        # is statistically distinguishable from 50% and still is not a
        # direction anyone should read anything into — the same trap the
        # material-CLV threshold exists for, one level up.
        if self.movers >= MINIMUM_BETS and abs(self.moved_toward - 0.5) <= 0.03:
            return (
                f"**the market is indifferent** — of {self.movers:,} prices "
                f"that moved, {self.moved_toward:.0%} moved toward the bet. "
                "A model with information moves the line toward it more than "
                "half the time"
            )
        if self.matched < MINIMUM_BETS:
            return (
                f"**not enough evidence** — {self.matched} matched bets, below "
                f"the {MINIMUM_BETS} declared in advance"
            )
        if abs(self.mean_clv) < MATERIAL_CLV:
            if self.roi > 0.02:
                return (
                    f"**no measurable CLV** ({self.mean_clv:+.2%}) beside a "
                    f"{self.roi:+.1%} return — the market did not move toward "
                    "these bets"
                )
            return f"**no measurable CLV** ({self.mean_clv:+.2%})"
        if self.roi > 0 and self.mean_clv < 0:
            return (
                "**a winning record with negative CLV is variance** — the "
                "market moved away from these bets"
            )
        if self.roi < 0 and self.mean_clv > 0:
            return (
                "a losing record with positive CLV — the model was on the "
                "right side of the move and the results did not follow"
            )
        if self.mean_clv > 0:
            return "positive CLV, consistent with the return"
        return "negative CLV, consistent with the return"


@dataclass
class CLVResult:
    markets: list[MarketCLV] = field(default_factory=list)
    matched: int = 0
    unmatched: int = 0
    closing_available: bool = True

    @property
    def pooled(self) -> MarketCLV:
        pooled = MarketCLV(market="all markets pooled")
        for entry in self.markets:
            pooled.bets += entry.bets
            pooled.matched += entry.matched
        pooled.movers = sum(e.movers for e in self.markets)
        if pooled.movers:
            pooled.moved_toward = (
                sum(e.moved_toward * e.movers for e in self.markets) / pooled.movers
            )
        if pooled.matched:
            weighted = sum(e.mean_clv * e.matched for e in self.markets)
            pooled.mean_clv = weighted / pooled.matched
            pooled.positive_share = (
                sum(e.positive_share * e.matched for e in self.markets) / pooled.matched
            )
            pooled.roi = (
                sum(e.roi * e.bets for e in self.markets) / max(pooled.bets, 1)
            )
        return pooled


def closing_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """The best available closing price for every wager, one row each."""
    labelled = label_snapshots(prices)
    if "phase" not in labelled.columns:
        return labelled.iloc[0:0]
    closes = labelled[labelled["phase"] == CLOSING]
    if closes.empty:
        return closes
    return best_price_per_selection(closes)


def measure(bets: pd.DataFrame, prices: pd.DataFrame) -> CLVResult:
    """CLV for every bet that has a closing price to compare against."""
    result = CLVResult()
    closes = closing_prices(prices)
    if closes.empty:
        result.closing_available = False
        result.unmatched = len(bets)
        return result
    if bets.empty:
        return result

    lookup = closes.copy()
    lookup["line"] = pd.to_numeric(lookup["line"], errors="coerce")
    lookup = lookup.set_index(list(MATCH_KEYS))["american_odds"].to_dict()

    frame = bets.copy()
    frame["line"] = pd.to_numeric(frame["line"], errors="coerce")
    frame["closing_odds"] = [
        lookup.get(
            (row.event_id, row.market, row.player, row.selection, row.line)
        )
        for row in frame.itertuples()
    ]
    matched = frame.dropna(subset=["closing_odds"]).copy()
    staked_all = frame[frame["outcome"] != "void"]
    result.matched = int((matched["outcome"] != "void").sum())
    result.unmatched = len(staked_all) - result.matched
    if matched.empty:
        return result

    matched["card_implied"] = matched["odds"].map(american_to_implied)
    matched["closing_implied"] = matched["closing_odds"].map(american_to_implied)
    matched["clv"] = matched["closing_implied"] - matched["card_implied"]

    for market in sorted(frame["market"].unique()):
        # Counted on the same population, or the table reports more matches
        # than bets — which it did, in every row, because `matched` included
        # voided bets and `bets` did not. A number larger than its own
        # denominator is the kind of thing a reader spots and then stops
        # trusting the rest of the table.
        staked = frame[(frame["market"] == market) & (frame["outcome"] != "void")]
        subset = matched[
            (matched["market"] == market) & (matched["outcome"] != "void")
        ]
        entry = MarketCLV(market=market, bets=len(staked), matched=len(subset))
        if len(subset):
            entry.mean_clv = float(subset["clv"].mean())
            entry.positive_share = float((subset["clv"] > 0).mean())
            moved = subset[subset["clv"] != 0]
            entry.movers = len(moved)
            if entry.movers:
                entry.moved_toward = float((moved["clv"] > 0).mean())
        if len(staked):
            entry.roi = float(staked["profit"].sum() / len(staked))
        result.markets.append(entry)
    return result


def render(result: CLVResult) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Closing-line value")
    add("")
    if not result.closing_available:
        add(
            "**No closing snapshot has been bought**, so there is no CLV to "
            f"report for any of {result.unmatched:,} bets. That is an absence, "
            "counted and named, and it is not a zero."
        )
        return "\n".join(lines) + "\n"

    add(
        "CLV is the fastest honest signal at these sample sizes. An NFL season "
        "is 272 games and roughly six hundred bets separate a real +8% edge "
        "from zero, so a season of results is barely a signal — but whether "
        "the market agreed with the model by the time it stopped arguing "
        "converges far faster."
    )
    add("")
    add(
        "The backtest takes the **best available** card-time price across nine "
        "books, so the comparison is the **best available closing price**. "
        "Comparing a best-of-nine entry against a single book's close would "
        "manufacture CLV out of shopping."
    )
    add("")
    add(
        f"{result.matched:,} bets matched a closing price; "
        f"{result.unmatched:,} did not and are excluded rather than counted "
        "as zero CLV."
    )
    add("")
    add("| Market | Bets | Matched | Moved | Toward | Mean CLV | ROI | Reading |")
    add("|:-------|-----:|--------:|------:|-------:|---------:|----:|:--------|")
    for entry in sorted(result.markets, key=lambda m: -m.matched):
        if not entry.matched:
            add(
                f"| `{entry.market}` | {entry.bets:,} | 0 | — | — | "
                f"{entry.roi:+.1%} | no closing price matched |"
            )
            continue
        add(
            f"| `{entry.market}` | {entry.bets:,} | {entry.matched:,} | "
            f"{entry.movers:,} | {entry.moved_toward:.0%} | "
            f"{entry.mean_clv:+.2%} | {entry.roi:+.1%} | {entry.reading()} |"
        )
    pooled = result.pooled
    add(
        f"| **pooled** | {pooled.bets:,} | {pooled.matched:,} | "
        f"{pooled.movers:,} | {pooled.moved_toward:.0%} | "
        f"{pooled.mean_clv:+.2%} | {pooled.roi:+.1%} | {pooled.reading()} |"
    )
    add("")
    add(
        "Mean CLV is in probability points: positive means the price taken "
        "implied a lower probability than the close did, which is the "
        "direction that pays. **CLV cannot make a losing model profitable**, "
        "and it is reported beside the return rather than instead of it."
    )
    add("")
    add(
        "**`Moved` and `Toward` are the numbers to read.** A price that did "
        "not change carries no information either way, so the question is "
        "what the ones that did change did. A model with information moves "
        "the line toward it more than half the time."
    )
    add("")
    add(
        f"A mean below **{MATERIAL_CLV:.1%}** reads as *no measurable CLV*, "
        "not as positive or negative. With this many bets almost any "
        "departure from zero is statistically distinguishable and two "
        "hundredths of a point still cannot matter to anyone."
    )
    return "\n".join(lines) + "\n"
