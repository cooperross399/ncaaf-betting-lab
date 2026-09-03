"""Does the edge survive at a price you could actually get?

The backtest takes the **best available** price across every book quoting a
wager. That is what a card does — it shops. But it means a measured edge could
be three very different things:

1. **A real disagreement with the market.** It survives at the consensus price
   and at most individual books.
2. **A line-shopping premium.** It exists only as the maximum of N quotes and
   vanishes at any single book. Real in the sense that the price existed, and
   it needs an account at whichever book was softest that day.
3. **One soft book's mistake.** That is a fact about the book, not the market,
   and books that price like that get sharper, get limited, or leave.

These decide whether a number is a strategy, an operational requirement, or a
curiosity — and no test that only looks at the best price can tell them apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


#: A book needs this many of a market's bets before its ROI is reported. Below
#: it the number is noise wearing a book's name.
MINIMUM_BOOK_BETS = 400


def to_implied(odds: pd.Series) -> pd.Series:
    """American odds to implied probability."""
    positive = odds > 0
    out = pd.Series(0.0, index=odds.index, dtype="float64")
    out[positive] = 100.0 / (odds[positive] + 100.0)
    out[~positive] = odds[~positive].abs() / (odds[~positive].abs() + 100.0)
    return out


def from_implied(probability: pd.Series) -> pd.Series:
    """Implied probability back to American odds.

    Needed because **American odds cannot be averaged.** They are
    discontinuous around plus and minus a hundred and nothing exists between
    them, so the median of [-110, +105] is -2.5, which is not a price — and
    the median of a symmetric pair is zero, which divided into a payout is
    infinity. The first version of this report printed `+inf%` in eight rows.

    Probabilities are continuous and average correctly, so the aggregation
    happens there and the result is converted back once.
    """
    probability = probability.clip(1e-6, 1 - 1e-6)
    favourite = probability >= 0.5
    out = pd.Series(0.0, index=probability.index, dtype="float64")
    out[favourite] = -100.0 * probability[favourite] / (1 - probability[favourite])
    out[~favourite] = 100.0 * (1 - probability[~favourite]) / probability[~favourite]
    return out


def profit(odds: pd.Series, outcome: pd.Series) -> pd.Series:
    """Units returned per unit staked, at the given price."""
    payout = pd.Series(0.0, index=odds.index, dtype="float64")
    positive = odds > 0
    payout[positive] = odds[positive] / 100.0
    payout[~positive] = 100.0 / odds[~positive].abs()
    result = pd.Series(-1.0, index=odds.index, dtype="float64")
    result[outcome == "won"] = payout[outcome == "won"]
    result[outcome == "push"] = 0.0
    return result


@dataclass
class BookResult:
    book: str
    bets: int
    roi: float


@dataclass
class MarketSensitivity:
    market: str
    best_of_n_roi: float = 0.0
    best_of_n_bets: int = 0
    consensus_roi: float = 0.0
    consensus_bets: int = 0
    books: list[BookResult] = field(default_factory=list)

    @property
    def books_positive(self) -> int:
        return sum(1 for book in self.books if book.roi > 0)

    def reading(self) -> str:
        if not self.books:
            return "no book quoted enough of this market to say"
        share = self.books_positive / len(self.books)
        if self.consensus_roi > 0 and share >= 0.6:
            return (
                f"**survives** — {self.consensus_roi:+.1%} at the consensus "
                f"price and positive at {self.books_positive} of "
                f"{len(self.books)} books"
            )
        if self.consensus_roi <= 0 and share < 0.4:
            # "Shopping premium" means the edge exists ONLY at the best of N
            # quotes. That claim requires the best of N to actually be
            # positive. Without this check a market losing money at the
            # consensus AND at the best price available anywhere was still
            # described as having an edge you could shop for — the most
            # flattering possible reading of a market that loses at every
            # price a human could take.
            if self.best_of_n_roi > 0:
                return (
                    f"**a shopping premium** — {self.consensus_roi:+.1%} at "
                    f"the consensus, {self.best_of_n_roi:+.1%} at the best of "
                    f"{len(self.books)} books, and positive at only "
                    f"{self.books_positive} of them. The edge is the maximum "
                    "of N quotes, not a disagreement with the market"
                )
            return (
                f"**loses at every price** — {self.consensus_roi:+.1%} at the "
                f"consensus and {self.best_of_n_roi:+.1%} even at the best of "
                f"{len(self.books)} books. There is no price at which this "
                "market was profitable, so there is nothing to shop for"
            )
        return (
            f"mixed — {self.consensus_roi:+.1%} at the consensus, positive at "
            f"{self.books_positive} of {len(self.books)} books"
        )


def measure(bets: pd.DataFrame, prices: pd.DataFrame) -> list[MarketSensitivity]:
    """`bets` from the backtest; `prices` the card-time rows for every book."""
    if bets.empty or prices.empty:
        return []
    keys = ["event_id", "market", "player", "selection", "line"]
    left = bets[bets["outcome"] != "void"].copy()
    left["line"] = pd.to_numeric(left["line"], errors="coerce")
    quotes = prices[keys + ["american_odds", "book"]].copy()
    quotes["line"] = pd.to_numeric(quotes["line"], errors="coerce")

    joined = left[keys + ["outcome", "profit"]].merge(quotes, on=keys, how="inner")
    if joined.empty:
        return []
    joined["book_profit"] = profit(joined["american_odds"], joined["outcome"])

    results: list[MarketSensitivity] = []
    for market, group in joined.groupby("market"):
        original = left[left["market"] == market]
        entry = MarketSensitivity(
            market=str(market),
            best_of_n_roi=float(original["profit"].mean()),
            best_of_n_bets=len(original),
        )
        # The consensus: the median quote for each wager. The closest thing to
        # *the* price, and the one thing shopping cannot improve.
        #
        # Taken in probability space and converted back, because American odds
        # cannot be averaged — see `from_implied`.
        group = group.assign(_implied=to_implied(group["american_odds"]))
        consensus = group.groupby(keys + ["outcome"], as_index=False)[
            "_implied"
        ].median()
        consensus["american_odds"] = from_implied(consensus["_implied"])
        consensus["profit"] = profit(consensus["american_odds"], consensus["outcome"])
        entry.consensus_roi = float(consensus["profit"].mean())
        entry.consensus_bets = len(consensus)

        for book, rows in group.groupby("book"):
            if len(rows) < MINIMUM_BOOK_BETS:
                continue
            entry.books.append(
                BookResult(book=str(book), bets=len(rows), roi=float(rows["book_profit"].mean()))
            )
        entry.books.sort(key=lambda b: -b.roi)
        results.append(entry)
    results.sort(key=lambda m: -m.best_of_n_roi)
    return results


def render(results: list[MarketSensitivity], *, coverage: str = "") -> str:
    lines: list[str] = []
    add = lines.append
    add("# Does the edge survive at a price you could actually get?")
    add("")
    # What the numbers are measured over, stated before any of them. A report
    # that does not say what it covers reads as covering everything.
    if coverage:
        add(coverage)
        add("")
    add(
        "The backtest takes the **best available** price across every book "
        "quoting a wager, which is what a card does. But a measured edge can "
        "be three different things: a real disagreement with the market, a "
        "line-shopping premium that exists only as the maximum of N quotes, "
        "or one soft book's mistake. Those decide whether a number is a "
        "strategy, an operational requirement, or a curiosity."
    )
    add("")
    add(
        "The **consensus** column is the median quote per wager — the closest "
        "thing to *the* price, and the one thing shopping cannot improve."
    )
    add("")
    add("| Market | Bets | Best of N | Consensus | Books positive | Reading |")
    add("|:-------|-----:|----------:|----------:|:---------------|:--------|")
    for entry in results:
        add(
            f"| `{entry.market}` | {entry.best_of_n_bets:,} | "
            f"{entry.best_of_n_roi:+.1%} | {entry.consensus_roi:+.1%} | "
            f"{entry.books_positive}/{len(entry.books)} | {entry.reading()} |"
        )
    add("")
    for entry in results:
        if not entry.books:
            continue
        add(f"### `{entry.market}` by book")
        add("")
        add("| Book | Bets | ROI |")
        add("|:-----|-----:|----:|")
        for book in entry.books:
            add(f"| {book.book} | {book.bets:,} | {book.roi:+.1%} |")
        add("")
    add(
        f"A book needs {MINIMUM_BOOK_BETS} bets in a market before its ROI is "
        "reported; below that the number is noise wearing a book's name."
    )
    return "\n".join(lines) + "\n"
