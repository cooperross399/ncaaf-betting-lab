"""Every market this lab prices, and the quantity each settles against.

**Team markets only.** Cooper ruled college player props out of scope on
2026-08-28. That removes the transfer portal, opt-outs and a per-player college
data join from the critical path, and it is why this file is a tenth the length
of the NFL lab's.

## Wired is not quoted, and quoted is not measurable

The NFL lab learned this expensively and it is recorded here so the college lab
does not learn it again. A market listed below is one this repository knows how
to ask for and how to settle. It is **not** a claim that any book quotes it for
college football, and **not** a claim that enough books quote it to measure
anything against. Those are separate facts, established by a retention probe
against real events, in season.

**No retention probe has run for college football.** Every `retained` field
below is `None`, meaning unknown — not `False`, which would be a finding, and
not `True`, which would be a guess. A report that treats an unprobed market as
unavailable is making the `total_2_5` mistake the EPL lab made: it excluded a
market for a season on a coverage check that only looked at the featured key
while the line sat in the alternate ladder the whole time.

## The settlement column is not chosen here

`settles_on` is prose rather than a column name because the college data source
is not nflverse and its schema is not this repository's to assume. Naming a
column here would imply one exists. The adapter names it, and a market whose
settlement cannot be demonstrated against real finished games does not ship.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    """One market: what it is called here, at the provider, and how it settles."""

    #: The name used everywhere inside this repository.
    key: str
    #: The Odds API market key that supplies it.
    provider_key: str
    #: Human label for reports.
    label: str
    #: Always `team` in this lab. Kept so the field exists if props are ever
    #: scoped in, rather than being added later by a session that then has to
    #: touch every construction site.
    kind: str
    #: The quantity a settled result is read from, in words.
    settles_on: str
    #: The selections a complete market must quote. An incomplete market is
    #: excluded rather than half-used: pricing one side of a two-sided market
    #: and calling it a market is how a lab prices a wager nobody offered.
    selections: tuple[str, ...]
    #: Whether the provider serves it from the per-event endpoint. The bulk
    #: three cost `markets x regions` for the whole slate; per-event calls bill
    #: unique markets RETURNED times regions, which is why the ladders are
    #: expensive on a 60-game Saturday and cheap on an NFL Sunday.
    per_event: bool = True
    #: 1 = asked for on the first fetch. 2 = wired and waiting on a probe.
    tier: int = 1
    #: The game segment it settles over.
    period: str = "game"
    #: Whether a book was observed quoting it for college football.
    #: **None means unprobed**, which is the honest state today for all of
    #: them. False would be a finding and True would be a guess.
    retained: bool | None = None


#: The bulk three. One call covers the whole slate, billed markets x regions.
BULK_TEAM_MARKETS: tuple[Market, ...] = (
    Market(
        key="moneyline",
        provider_key="h2h",
        label="Moneyline",
        kind="team",
        settles_on=(
            "final score, home vs away. College football has no ties: every "
            "game level after regulation is decided in overtime, so unlike "
            "the NFL there is no draw outcome to price or settle."
        ),
        selections=("home", "away"),
        per_event=False,
    ),
    Market(
        key="spread",
        provider_key="spreads",
        label="Spread",
        kind="team",
        settles_on=(
            "final margin against the line; a whole-number line pushes "
            "exactly, and whether college margins pile up on 3 and 7 the way "
            "NFL margins do is an open question this lab must measure rather "
            "than inherit"
        ),
        selections=("home", "away"),
        per_event=False,
    ),
    Market(
        key="total_points",
        provider_key="totals",
        label="Total points",
        kind="team",
        settles_on=(
            "home + away final score against the line. College overtime "
            "starts each possession at the opponent's 25-yard line and, from "
            "the third period, is a two-point-conversion shootout — so an "
            "overtime game adds points on a completely different distribution "
            "from an NFL one, and a total settled without modelling that is "
            "settled correctly and PRICED wrongly."
        ),
        selections=("over", "under"),
        per_event=False,
    ),
)

#: The ladders and derived markets. Per-event, and the expensive ones on a
#: Saturday that can carry sixty games.
PER_EVENT_TEAM_MARKETS: tuple[Market, ...] = (
    Market(
        key="alternate_spread",
        provider_key="alternate_spreads",
        label="Alternate spread",
        kind="team",
        settles_on="same as `spread`, every offered rung",
        selections=("home", "away"),
    ),
    Market(
        key="alternate_total_points",
        provider_key="alternate_totals",
        label="Alternate total",
        kind="team",
        settles_on="same as `total_points`, every offered rung",
        selections=("over", "under"),
    ),
    Market(
        key="team_total",
        provider_key="team_totals",
        label="Team total",
        kind="team",
        settles_on="one side's final score against the line",
        selections=("home_over", "home_under", "away_over", "away_under"),
    ),
    Market(
        key="alternate_team_total",
        provider_key="alternate_team_totals",
        label="Alternate team total",
        kind="team",
        settles_on="same as `team_total`, every offered rung",
        selections=("home_over", "home_under", "away_over", "away_under"),
        tier=2,
    ),
    Market(
        key="moneyline_h1",
        provider_key="h2h_h1",
        label="First half moneyline",
        kind="team",
        settles_on=(
            "half-time score, home vs away. **A half CAN end level** — the "
            "overtime rule does not apply to it — and the NFL lab priced a "
            "level half at 0.4% until that was fixed. Whatever the college "
            "rate is, it is not zero and it must be measured."
        ),
        selections=("home", "away"),
        tier=2,
        period="h1",
    ),
    Market(
        key="spread_h1",
        provider_key="spreads_h1",
        label="First half spread",
        kind="team",
        settles_on="half-time margin against the line",
        selections=("home", "away"),
        tier=2,
        period="h1",
    ),
    Market(
        key="total_points_h1",
        provider_key="totals_h1",
        label="First half total",
        kind="team",
        settles_on="half-time combined score against the line",
        selections=("over", "under"),
        tier=2,
        period="h1",
    ),
)

ALL_MARKETS: tuple[Market, ...] = BULK_TEAM_MARKETS + PER_EVENT_TEAM_MARKETS
MARKETS_BY_KEY: dict[str, Market] = {m.key: m for m in ALL_MARKETS}

#: Markets the provider serves that this lab deliberately does not price, each
#: with the reason. An absent market with no reason is indistinguishable from
#: one nobody thought about.
DEFERRED_MARKETS: dict[str, str] = {
    "player_pass_yds": "Player props are out of scope (Cooper, 2026-08-28).",
    "player_rush_yds": "Player props are out of scope (Cooper, 2026-08-28).",
    "player_reception_yds": "Player props are out of scope (Cooper, 2026-08-28).",
    "player_anytime_td": "Player props are out of scope (Cooper, 2026-08-28).",
    "h2h_3_way": (
        "A three-way market needs a draw, and college football has none: "
        "overtime decides every level game. Pricing a draw here would invent "
        "an outcome that cannot occur."
    ),
    "spreads_q1": "Quarter markets wired only after halves are measured.",
    "totals_q1": "Quarter markets wired only after halves are measured.",
    "h2h_q1": "Quarter markets wired only after halves are measured.",
    "outrights": (
        "Season-long futures settle months after they are priced, so they "
        "cannot enter a forward ledger that settles day-as-unit."
    ),
}


def market_for(key: str) -> Market:
    """The market, or an error naming what exists.

    Raises rather than returning None, because a typo that silently priced
    nothing looks exactly like a market no book quoted.
    """
    try:
        return MARKETS_BY_KEY[key]
    except KeyError:
        raise KeyError(
            f"No market {key!r}. Known: {', '.join(sorted(MARKETS_BY_KEY))}. "
            f"Deliberately not priced: {', '.join(sorted(DEFERRED_MARKETS))}."
        ) from None


def market_for_provider_key(provider_key: str) -> Market | None:
    for market in ALL_MARKETS:
        if market.provider_key == provider_key:
            return market
    return None


def bulk_provider_keys(tier: int = 1) -> tuple[str, ...]:
    return tuple(m.provider_key for m in ALL_MARKETS
                 if not m.per_event and m.tier <= tier)


def per_event_provider_keys(tier: int = 1) -> tuple[str, ...]:
    return tuple(m.provider_key for m in ALL_MARKETS
                 if m.per_event and m.tier <= tier)


def markets_in_tier(tier: int) -> tuple[Market, ...]:
    return tuple(m for m in ALL_MARKETS if m.tier <= tier)


def unprobed_markets() -> tuple[Market, ...]:
    """Every market whose college retention is unknown — today, all of them.

    Exposed as a function so a report can say so out loud rather than a reader
    assuming a wired market is an available one.
    """
    return tuple(m for m in ALL_MARKETS if m.retained is None)
