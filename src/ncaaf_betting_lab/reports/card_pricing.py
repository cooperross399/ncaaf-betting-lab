"""Turn staged prices into the probability map the card reads.

Kept apart from the card for the reason the sibling NFL lab gives (its
`reports/card_pricing.py`, from which this is ported): the card's job is gating
and presentation, this module's job is an opinion, and mixing them makes it
possible for a pricing path to bypass a gate.

## What the opinion is, said plainly

**The centre is the market's.** For each fixture the consensus — the median
across books — of the featured spread and the featured total is taken as the
line the market believes is a coin flip, and the measured shape
(`models/shapes.py`) is tilted until covering that line is exactly 50%, pushes
excluded. So on the featured line itself the model agrees with the market by
construction, and its opinion lives in two places only: a book whose line is
away from the consensus, and the alternate ladder rungs, where the measured
shape says how much mass sits between the consensus and a line the book had
to price on its own.

**Why the median and not the mean.** The first version tilted the shape so its
MEAN sat on the line. Measured walk-forward on 2023-2025 closing lines before
it priced anything: on spreads of 7.5 to 14 the mean-anchored shape gave the
underdog **53.0%** to cover the closing line, and the underdog covered
**47.8%** (n = 410 games); on totals it gave the over **48.4%** against a
realised **50.3%** (n = 1,597). College margins are skewed — a favourite's
blowout tail is long — so the mean sits away from the median, and a book's
line sits near the median. (Measured 2026-10-01 by hand, from the line table;
no script regenerates these figures, so treat them as a dated note.) Anchoring
on the mean would have manufactured an
"edge" on every featured underdog out of the shape's skew alone.

That is the architecture step 5 left this lab with: its ratings add nothing
the closing price does not carry (`data/outputs/ratings_residual.md`, 3,124
games, slope interval spanning zero), so they do not supply the mean. Nothing
here is a claim that this opinion makes money. It is an opinion worth freezing
before kickoff, which is what forward evidence needs.

## The accounting identity

Every staged row lands in exactly one bucket, and the card prints the
reconciliation:

    priced = no_opinion + unrated_opponent + kickoff_tbd + unresolved
             + unparseable + opinions

`unrated_opponent` and `kickoff_tbd` are their own buckets, not `no_opinion`,
for the reasons `coverage.py` gives: "we do not know these teams" and "we
looked and had nothing to say" are different facts, and an FCS Saturday must
be visible as a number rather than as an absence.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from ncaaf_betting_lab.coverage import KICKOFF_UNKNOWN, UNRATED_OPPONENT
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.markets import MARKETS_BY_KEY
from ncaaf_betting_lab.models import margin as margin_model
from ncaaf_betting_lab.models import total as total_model
from ncaaf_betting_lab.models.shapes import Shapes
from ncaaf_betting_lab.season import clean_text
from ncaaf_betting_lab.selection import normalise_line, selection_key

ProbabilityMap = dict[tuple, float]

MARGIN_MARKETS = frozenset({"moneyline", "spread", "alternate_spread"})
TOTAL_MARKETS = frozenset({"total_points", "alternate_total_points"})

#: Wired, settleable or not, and with no model. Each carries its reason so a
#: card can say why rather than leaving a gap.
UNMODELLED: dict[str, str] = {
    "team_total": (
        "a team total needs the joint distribution of margin and total, which "
        "this lab has not measured"
    ),
    "alternate_team_total": (
        "a team total needs the joint distribution of margin and total, which "
        "this lab has not measured"
    ),
    "moneyline_h1": (
        "first-half markets have no model, and no in-season half-time score "
        "source exists to settle them (`docs/build_order.md`, 1.2)"
    ),
    "spread_h1": (
        "first-half markets have no model, and no in-season half-time score "
        "source exists to settle them (`docs/build_order.md`, 1.2)"
    ),
    "total_points_h1": (
        "first-half markets have no model, and no in-season half-time score "
        "source exists to settle them (`docs/build_order.md`, 1.2)"
    ),
}

#: Buckets a fixture can be refused into before any row is priced.
UNRESOLVED = "unresolved"
FIXTURE_REFUSALS = (UNRATED_OPPONENT, KICKOFF_UNKNOWN, UNRESOLVED)


@dataclass
class PricingDiagnostics:
    """Every staged row, in exactly one bucket."""

    priced: int = 0
    no_opinion: int = 0
    unrated_opponent: int = 0
    kickoff_tbd: int = 0
    unresolved: int = 0
    unparseable: int = 0
    opinions: int = 0
    reasons: Counter = field(default_factory=Counter)

    BUCKETS = (
        "no_opinion", "unrated_opponent", "kickoff_tbd", "unresolved",
        "unparseable", "opinions",
    )

    def note(self, bucket: str, reason: str) -> None:
        setattr(self, bucket, getattr(self, bucket) + 1)
        self.reasons[reason] += 1

    def reconciles(self) -> bool:
        return self.priced == sum(getattr(self, b) for b in self.BUCKETS)

    def identity_line(self) -> str:
        state = "reconciles" if self.reconciles() else "DOES NOT RECONCILE"
        parts = " + ".join(f"{b} {getattr(self, b):,}" for b in self.BUCKETS)
        return f"priced {self.priced:,} = {parts} — {state}."


@dataclass(frozen=True)
class Fixture:
    """What the card knows about one staged game before pricing it.

    Built by the caller from the membership and the schedule, so identity and
    calendar resolution happen in one place and this module only prices.
    """

    #: `None` when both teams resolved to rated FBS teams and the game is on
    #: this season's schedule with a kickoff set; otherwise the bucket the
    #: fixture's rows go to.
    refusal: str | None = None
    reason: str = ""


def consensus(prices: pd.DataFrame, market: str, selection: str) -> float | None:
    """The median featured line across books, or None when nobody quoted one."""
    if prices.empty:
        return None
    rows = prices[
        (prices["market"].astype(str) == market)
        & (prices["selection"].astype(str) == selection)
    ]
    lines = pd.to_numeric(rows["line"], errors="coerce").dropna()
    if lines.empty:
        return None
    # One line per book first, so a book quoting a line twice cannot outvote
    # the others.
    if "book" in rows.columns:
        per_book = rows.assign(_line=pd.to_numeric(rows["line"], errors="coerce"))
        lines = per_book.dropna(subset=["_line"]).groupby("book")["_line"].median()
    return float(lines.median())


#: How far the anchored mean may sit from the line, in points. Far wider than
#: any skew measured (a few points); a search that needs more is a shape that
#: cannot put half its mass either side of the line, and that is no opinion.
ANCHOR_SEARCH_POINTS = 12.0


def _bisect(cover, low: float, high: float) -> float:
    """The mean at which `cover(mean)` is 0.5, `cover` increasing in mean."""
    if not cover(low) <= 0.5 <= cover(high):
        raise ValueError(
            "no centre within the search range puts half the shape either side "
            "of the consensus line"
        )
    for _ in range(40):
        middle = (low + high) / 2
        if cover(middle) < 0.5:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def anchor_margin(shapes: Shapes, spread_line: float) -> margin_model.MarginModel:
    """The margin model whose home side covers `spread_line` exactly half the time.

    The BUCKET is chosen once, from the consensus line, and only the tilt
    moves. Letting the search re-pick the bucket as the centre moved would
    swap shapes mid-search, and the cover probability would jump at every
    bucket boundary rather than move smoothly.
    """
    implied = -float(spread_line)
    if abs(implied) > margin_model.MAX_TILT_POINTS:
        raise ValueError(
            f"an implied margin of {implied:+.1f} is beyond "
            f"{margin_model.MAX_TILT_POINTS:.0f} points, where the shape is too "
            "thin to tilt honestly"
        )
    bucket = margin_model.bucket_for(implied)
    pmf = shapes.margins.get(bucket)
    if not pmf:
        raise KeyError(f"no margin shape for spread bucket {bucket}")

    def model(mean: float) -> margin_model.MarginModel:
        return margin_model.MarginModel(
            pmf=margin_model.tilt_to_mean(pmf, mean), implied_margin=implied,
            total=0.0,
        )

    def cover(mean: float) -> float:
        return _without_push(*model(mean).probability_cover(spread_line, side="home"))

    return model(
        _bisect(cover, implied - ANCHOR_SEARCH_POINTS, implied + ANCHOR_SEARCH_POINTS)
    )


def anchor_total(shapes: Shapes, total_line: float) -> total_model.TotalModel:
    """The total model whose over at `total_line` lands exactly half the time."""
    line = float(total_line)
    bucket = total_model.bucket_for(line)
    pmf = shapes.totals.get(bucket)
    if not pmf:
        raise KeyError(f"no total shape for bucket {bucket}")

    def model(mean: float) -> total_model.TotalModel:
        return total_model.TotalModel(
            pmf=margin_model.tilt_to_mean(pmf, mean), total_line=line
        )

    def over(mean: float) -> float:
        return _without_push(*model(mean).probability_over(line, side="over"))

    return model(_bisect(over, line - ANCHOR_SEARCH_POINTS, line + ANCHOR_SEARCH_POINTS))


def _without_push(win: float, push: float) -> float:
    """P(win | the bet is not refunded). A push returns the stake."""
    remaining = 1.0 - push
    return win / remaining if remaining > 1e-9 else 0.0


def price_slate(
    prices: pd.DataFrame,
    league: League,
    *,
    shapes: Shapes,
    fixtures: Mapping[tuple[str, str], Fixture],
) -> tuple[ProbabilityMap, PricingDiagnostics]:
    """A probability for every staged row this lab has an opinion on.

    `fixtures` is keyed by the provider's own `(home, away)` strings. A pair
    the caller did not describe is `unresolved`: this module never guesses at
    who is playing.
    """
    probabilities: ProbabilityMap = {}
    diagnostics = PricingDiagnostics()
    if prices.empty:
        return probabilities, diagnostics

    games = prices.groupby(["home_team", "away_team"], sort=True)
    for (home, away), rows in games:
        fixture = fixtures.get((str(home), str(away)))
        if fixture is None:
            fixture = Fixture(UNRESOLVED, f"{away} @ {home} was not resolved")
        margin = total = None
        margin_reason = total_reason = ""
        if fixture.refusal is None:
            spread_line = consensus(rows, "spread", "home")
            if spread_line is None:
                margin_reason = "no featured spread quoted, so no mean to anchor on"
            else:
                try:
                    margin = anchor_margin(shapes, spread_line)
                except (KeyError, ValueError) as exc:
                    margin_reason = f"no margin shape: {exc}"
            total_line = consensus(rows, "total_points", "over")
            if total_line is None:
                total_reason = "no featured total quoted, so no mean to anchor on"
            else:
                try:
                    total = anchor_total(shapes, total_line)
                except (KeyError, ValueError) as exc:
                    total_reason = f"no total shape: {exc}"

        for row in rows.itertuples():
            diagnostics.priced += 1
            if fixture.refusal is not None:
                diagnostics.note(fixture.refusal, fixture.reason)
                continue
            market_key = clean_text(getattr(row, "market", ""))
            selection = clean_text(getattr(row, "selection", "")).lower()
            line = normalise_line(getattr(row, "line", None))
            if market_key not in MARKETS_BY_KEY:
                diagnostics.note("unparseable", f"unknown market `{market_key}`")
                continue
            if market_key in UNMODELLED:
                diagnostics.note("no_opinion", f"`{market_key}`: {UNMODELLED[market_key]}")
                continue
            probability: float | None = None
            if market_key in MARGIN_MARKETS:
                if margin is None:
                    diagnostics.note("no_opinion", margin_reason)
                    continue
                probability = _margin_probability(margin, market_key, selection, line)
            elif market_key in TOTAL_MARKETS:
                if total is None:
                    diagnostics.note("no_opinion", total_reason)
                    continue
                probability = _total_probability(total, selection, line)
            if probability is None:
                diagnostics.note(
                    "unparseable", f"`{market_key}` selection `{selection}` line {line}"
                )
                continue
            probabilities[
                selection_key(
                    row, market=market_key, selection=selection, line=line,
                    league=league,
                )
            ] = probability
            diagnostics.opinions += 1
    return probabilities, diagnostics


def _margin_probability(
    model: margin_model.MarginModel, market: str, selection: str, line: float | None
) -> float | None:
    if selection not in {"home", "away"}:
        return None
    if market == "moneyline":
        # A college game cannot end level — overtime decides it — so the
        # smoothed shape's small mass at zero is not a draw. It is removed
        # from the denominator exactly like a push, which is what it would be.
        return _without_push(*model.probability_cover(0.0, side=selection))
    if line is None:
        return None
    return _without_push(*model.probability_cover(float(line), side=selection))


def _total_probability(
    model: total_model.TotalModel, selection: str, line: float | None
) -> float | None:
    if selection not in {"over", "under"} or line is None:
        return None
    return _without_push(*model.probability_over(float(line), side=selection))
