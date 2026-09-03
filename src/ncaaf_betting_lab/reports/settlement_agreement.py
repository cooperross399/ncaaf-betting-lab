"""Does what this lab settles on agree with what the books priced?

## The failure this exists to catch

A market's line is set near the outcome's median. So if this lab's settlement
source and the book's settlement source are the same thing, the realised
outcome should land above the line about half the time, and the **median
outcome should sit on the line**.

When it does not, every bet in that market is scored against a different
quantity from the one that was priced — and the resulting "edge" is a
constant, which means it **replicates perfectly across seasons and looks
exactly like a stable finding.**

That is not hypothetical. `tackles_assists` returned +16% across three
seasons, survived split-half, fragility and a family correction, and had no
closing-line value at all. The explanation was that nflverse's defensive
charting records about half a tackle per player-game fewer than whatever the
books settle on: at a +0.5 offset the edge vanishes completely and both sides
return the vig. Replication cannot protect against a systematic settlement
offset, because a constant offset replicates by construction.

## The diagnostic

The naive version — "the over rate should be near 50%" — is wrong, and its
first run said so loudly: it flagged `anytime_td`, where a 13% over rate is
exactly right because the line is 0.5 and most players do not score, and it
flagged the yardage markets on an absolute median gap of 2.5 yards against a
37-yard line.

So the comparison is to the **price**, not to a half. For each featured
wager both sides are quoted, so the two prices devig to the market's own
implied over probability. That is what the outcome should match, market by
market, whatever the line and whatever the base rate:

    realised over rate  vs  devigged implied over rate

A market whose realised rate sits well below what it was priced at is being
settled on a smaller quantity than the one the book priced. The gap is
reported in probability points and is directly comparable across markets that
have nothing else in common.

A settlement suspect's measured edge is not evidence of anything until an
independent source settles the question.

## Which markets are suspect by construction

Anything whose settlement involves charting judgement rather than a count off
the play. Tackles and assists are attributed inconsistently between sources;
half-sacks are apportioned differently; receptions and yards are not.
`CHARTING_DEPENDENT` names them, and the report says so beside the numbers —
because "the two suspect markets are the two that showed an edge" is a
sentence a reader should be able to check rather than take on trust.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

#: Markets whose settled value depends on how a source charts a play, rather
#: than on a count the play itself determines.
CHARTING_DEPENDENT: frozenset[str] = frozenset(
    {"tackles_assists", "solo_tackles", "sacks", "defensive_interceptions"}
)

#: How far the realised over rate may sit from the devigged price before the
#: market is a suspect, in probability points. Deliberately loose: this is a
#: screen, not a test, and a screen that fires on everything is ignored. Four
#: points is already larger than any edge this lab could plausibly have.
IMPLIED_GAP_TOLERANCE = 0.04

#: Below this many wagers a market is not screened at all, because a rate
#: computed on a handful of lines says nothing.
MINIMUM_WAGERS = 200


@dataclass
class MarketAgreement:
    market: str
    wagers: int = 0
    over_rate: float = 0.0
    implied_over: float = 0.0
    charting_dependent: bool = False

    @property
    def gap(self) -> float:
        """Realised minus priced, in probability points."""
        return self.over_rate - self.implied_over

    @property
    def worth_to_one_side(self) -> float:
        """Roughly what this gap hands a strategy that leans one way.

        A wager at about even money returns roughly two units of ROI for every
        unit of probability the outcome is mispriced by, so a three-point gap
        is worth about six points of return to anything that consistently
        takes the side the gap favours.

        This is why "agrees with the price" is not "contributes nothing". A
        market can sit inside the screen's tolerance and still be handing a
        one-sided model most of its measured return.
        """
        return abs(self.gap) * 2.0

    @property
    def screened(self) -> bool:
        return self.wagers >= MINIMUM_WAGERS

    @property
    def suspect(self) -> bool:
        return self.screened and abs(self.gap) > IMPLIED_GAP_TOLERANCE

    def reading(self) -> str:
        if not self.wagers:
            return "no featured lines matched to a result"
        if not self.screened:
            return f"not screened — {self.wagers} wagers, below {MINIMUM_WAGERS}"
        if not self.suspect:
            return "agrees with the price"
        direction = "below" if self.gap < 0 else "above"
        note = (
            f"**settlement suspect** — outcomes land {abs(self.gap):.0%} "
            f"{direction} what the price implied"
        )
        if self.charting_dependent:
            note += "; this market settles on a charted quantity"
        return note


@dataclass
class AgreementResult:
    markets: list[MarketAgreement] = field(default_factory=list)

    @property
    def suspects(self) -> list[MarketAgreement]:
        return [m for m in self.markets if m.suspect]


def measure(featured: pd.DataFrame) -> AgreementResult:
    """`featured` needs `market`, `line`, `actual`, `implied_over` per wager.

    `implied_over` is the market's own devigged probability of the over, from
    the two quoted sides. Comparing the outcome to that rather than to a half
    is what makes a 0.5-line touchdown market and a 37-yard receiving market
    answerable by the same screen.
    """
    result = AgreementResult()
    if featured.empty:
        return result
    for market, group in featured.groupby("market"):
        rows = group.dropna(subset=["line", "actual", "implied_over"])
        if rows.empty:
            result.markets.append(MarketAgreement(market=str(market)))
            continue
        decided = rows[rows["actual"] != rows["line"]]
        result.markets.append(
            MarketAgreement(
                market=str(market),
                wagers=len(rows),
                over_rate=(
                    float((decided["actual"] > decided["line"]).mean())
                    if len(decided)
                    else 0.0
                ),
                implied_over=float(rows["implied_over"].mean()),
                charting_dependent=str(market) in CHARTING_DEPENDENT,
            )
        )
    result.markets.sort(key=lambda m: (not m.suspect, m.market))
    return result


def render(result: AgreementResult) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Does settlement agree with what the books priced?")
    add("")
    add(
        "Both sides of a featured line are quoted, so the two prices devig to "
        "the market's own probability of the over. **That is what the outcome "
        "should match** — not a half, which would flag a 0.5-line touchdown "
        "market where a 13% over rate is exactly right. Where the realised "
        "rate sits well below the priced one, every bet in that market is "
        "scored against a smaller quantity than the book priced."
    )
    add("")
    add(
        "**That failure replicates perfectly across seasons**, because a "
        "constant offset is constant. It is the one defect that survives every "
        "check a backtest can run on itself, which is why this screen exists "
        "and why it runs before any result is believed."
    )
    add("")
    add(
        "| Market | Featured wagers | Priced over | Realised over | Gap | "
        "Worth to a one-sided model | Charted | Reading |"
    )
    add("|:-------|----------------:|------------:|--------------:|----:|--------------------------:|:--------|:--------|")
    for entry in result.markets:
        add(
            f"| `{entry.market}` | {entry.wagers:,} | {entry.implied_over:.0%} | "
            f"{entry.over_rate:.0%} | {entry.gap:+.0%} | "
            f"{entry.worth_to_one_side:.0%} | "
            f"{'yes' if entry.charting_dependent else 'no'} | {entry.reading()} |"
        )
    add("")
    suspects = result.suspects
    if suspects:
        charting = [m for m in suspects if m.charting_dependent]
        add(
            f"**{len(suspects)} market(s) are settlement suspects**"
            + (
                f", and {len(charting)} of them settle on a charted quantity: "
                + ", ".join(f"`{m.market}`" for m in charting)
                + "."
                if charting
                else "."
            )
        )
        add("")
        add(
            "A settlement suspect's measured edge is **not evidence of "
            "anything** until an independent source settles the question. It "
            "is not a small caveat: an offset of half a unit was enough to "
            "turn a three-season, family-corrected, split-half-stable +16% "
            "into the vig."
        )
    elif result.markets:
        add("**No market is a settlement suspect.**")
    else:
        # An empty screen is not a pass. It printed "no market is a settlement
        # suspect" over an empty table once, after a reshaped price frame
        # dropped the kickoff column and every event failed its season match:
        # the exact screen that exists to catch a silent mis-settlement,
        # reporting a clean bill of health because it had measured nothing.
        add(
            "**This screen measured nothing, and that is a fault, not a "
            "pass.** No market cleared the minimum featured-wager count, so "
            "nothing here has been screened for settlement disagreement and "
            "no result downstream of it should be believed. Check that the "
            "price frame reaching this script still carries both sides and "
            "its kickoff."
        )
    add("")
    add(
        "**Passing the screen is not a clean bill of health.** A wager at "
        "about even money returns roughly two units of ROI per unit of "
        "probability the outcome is mispriced by, so the *worth* column is "
        "what each gap hands a model that consistently takes the side it "
        "favours. A three-point gap is inside the tolerance and worth six "
        "points of return, which can be most of a market's measured edge."
    )
    add("")
    add(
        f"The screen fires when the realised over rate sits more than "
        f"{IMPLIED_GAP_TOLERANCE:.0%} from the devigged price, on at least "
        f"{MINIMUM_WAGERS} featured wagers. Loose on purpose: four points is "
        "already larger than any edge this lab could plausibly have, and a "
        "screen that fires on everything is ignored."
    )
    return "\n".join(lines) + "\n"


def suspects_and_screened(report: str) -> tuple[set[str], set[str]]:
    """Read a rendered screen back: what it flagged, and what it looked at.

    Two sets, not one. A market the screen never examined is absent from both,
    and a caller testing only `market not in suspects` prints it as a pass
    reading "agrees with the devigged price" — an approval bar cleared by
    never having been measured. That is the same shape as the artefact that
    already cost this lab its headline finding twice, so the distinction is
    kept here rather than re-derived by each reader.
    """
    suspects: set[str] = set()
    screened: set[str] = set()
    for line in report.splitlines():
        if not line.startswith("| `"):
            continue
        name = line.split("`")[1]
        screened.add(name)
        if "settlement suspect" in line:
            suspects.add(name)
    return suspects, screened

