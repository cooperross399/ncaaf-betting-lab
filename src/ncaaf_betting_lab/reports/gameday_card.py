"""The card. Gating and presentation, and no pricing.

Ported from the sibling NFL lab's `reports/gameday_card.py`, team markets
only. Pricing lives in `card_pricing`, so a gate cannot be bypassed by a
pricing path.

## What a selection here is, said before anyone reads one

All ten college markets are allowlisted, by a receipt Claude signed on
Cooper's written instruction on 2026-09-28 (`CLAUDE.md`, *The one receipt
Claude wrote*). That receipt records an owner's decision, **not a finding**:
no college price had been fetched when it was signed, and every measured
result in this lab is a null. So this card can print selections, and every
one of them is **an opinion that cleared the bars, with no demonstrated
edge**. The card says so above the table, every time, in those words.

## The order the gates run in

1. **The fixture screen** — both teams resolved by identity, both FBS, the
   game on the schedule with a kickoff set. Refusals are buckets in the
   accounting identity, never silent.
2. **Market eligibility** — the policy, read through `market_allowed`.
3. **An opinion** — a missing key is *no opinion*, which is not zero.
4. **The edge and price bars** — `MIN_EDGE`, the juice bar, the longest price.
5. **Kickoff** — a started game, or one whose start cannot be confirmed, is
   quarantined.

Every exclusion is **counted and named**. An excluded market is never a pass,
an avoid, or a no-value call.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from ncaaf_betting_lab.config import MAX_DEFAULT_JUICE, MAX_DEFAULT_PRICE, MIN_EDGE
from ncaaf_betting_lab.forward_evidence import american_to_implied
from ncaaf_betting_lab.kickoff import QUARANTINE_HEADING, judge, partition
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.markets import MARKETS_BY_KEY
from ncaaf_betting_lab.reports.card_pricing import PricingDiagnostics
from ncaaf_betting_lab.season import clean_text
from ncaaf_betting_lab.selection import normalise_line, selection_key
from ncaaf_betting_lab.staging_provider_policy import StagingProviderPolicy

#: The sentence every selection table sits under. Contract-ish: tests match
#: it, and it must never soften into something that reads like a tip.
NO_DEMONSTRATED_EDGE_NOTE = (
    "**Every selection below has no demonstrated edge.** Each cleared the "
    "card's bars, which is not a prediction. The markets are allowlisted by "
    "an owner's decision rather than by a measurement: no priced test of "
    "this model against college prices exists, and every result this lab "
    "has measured is a null."
)

#: What a card with no eligible market leads with.
ACCUMULATING_NOTE = (
    "This card is **accumulating evidence, not making recommendations.**"
)


@dataclass
class CardResult:
    league: League
    generated_at: str
    slate_date: str
    games: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    quarantined: list[tuple[str, str]] = field(default_factory=list)
    market_states: dict[str, str] = field(default_factory=dict)
    diagnostics: PricingDiagnostics = field(default_factory=PricingDiagnostics)
    selections: list[dict] = field(default_factory=list)
    shapes_summary: str = ""
    frozen_rows: int = 0
    ledger_rows: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def decision(self) -> str:
        """One word for the run summary and the card-feed status file."""
        if not self.games:
            return "no-slate"
        if self.selections:
            return "selections"
        return "no-selections"


def select(
    prices: pd.DataFrame,
    probabilities: Mapping[tuple, float],
    league: League,
    *,
    policy: StagingProviderPolicy,
    now: datetime,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Every wager that clears every bar, and everything the guard pulled.

    One wager can be quoted by many books. The best price is taken **after**
    every bar, so a bar is never cleared by a price the card would not have
    used.
    """
    if prices.empty:
        return [], []

    best: dict[tuple, dict] = {}
    quarantined: list[tuple[str, str]] = []
    pulled: set[str] = set()
    for row in prices.itertuples():
        market_key = clean_text(getattr(row, "market", ""))
        if market_key not in MARKETS_BY_KEY or not policy.market_allowed(
            league, market_key
        ):
            continue
        selection = clean_text(getattr(row, "selection", "")).lower()
        line = normalise_line(getattr(row, "line", None))
        probability = probabilities.get(
            selection_key(
                row, market=market_key, selection=selection, line=line, league=league
            )
        )
        if probability is None:
            continue
        try:
            odds = int(float(getattr(row, "american_odds")))
        except (TypeError, ValueError):
            continue
        if odds < MAX_DEFAULT_JUICE or odds > MAX_DEFAULT_PRICE:
            continue
        edge = probability - american_to_implied(odds)
        if edge < MIN_EDGE:
            continue
        label = (
            f"{clean_text(getattr(row, 'away_team', ''))} @ "
            f"{clean_text(getattr(row, 'home_team', ''))}"
        )
        kickoff = judge(getattr(row, "commence_time", ""), now=now)
        if not kickoff.plays:
            tag = f"{label} — `{market_key}`"
            if tag not in pulled:
                pulled.add(tag)
                quarantined.append((tag, kickoff.reason))
            continue
        key = (market_key, selection, line, label)
        candidate = {
            "game": label,
            "market": market_key,
            "selection": selection,
            "line": line,
            "odds": odds,
            "book": clean_text(getattr(row, "book", "")),
            "model_probability": probability,
            "edge": edge,
        }
        if key not in best or odds > best[key]["odds"]:
            best[key] = candidate

    selections = sorted(best.values(), key=lambda item: -item["edge"])
    return selections, quarantined


def build_card(
    prices: pd.DataFrame,
    league: League,
    *,
    policy: StagingProviderPolicy,
    diagnostics: PricingDiagnostics,
    now: datetime,
    slate_date: str,
    refused: list[str],
    probabilities: Mapping[tuple, float] | None = None,
    shapes_summary: str = "",
) -> CardResult:
    result = CardResult(
        league=league,
        generated_at=now.isoformat(),
        slate_date=slate_date,
        refused=list(refused),
        diagnostics=diagnostics,
        shapes_summary=shapes_summary,
    )
    if prices.empty:
        return result

    result.games = sorted(
        {
            f"{row.away_team} @ {row.home_team}"
            for row in prices[["home_team", "away_team"]].drop_duplicates().itertuples()
        }
    )
    for market in sorted(set(prices["market"].astype(str))):
        if policy.market_allowed(league, market):
            result.market_states[market] = "eligible"
        else:
            result.market_states[market] = policy.refusal_reason(league, market)

    # The guard runs over the whole slate whether or not anything selects, so
    # its absence is never the reason a started game got through.
    _, quarantined = partition(
        [
            {
                "commence_time": row.commence_time,
                "label": f"{row.away_team} @ {row.home_team}",
            }
            for row in prices[
                ["home_team", "away_team", "commence_time"]
            ].drop_duplicates().itertuples()
        ],
        now=now,
    )
    result.quarantined = [
        (str(item["label"]), verdict.reason) for item, verdict in quarantined
    ]
    if probabilities:
        selections, pulled = select(
            prices, probabilities, league, policy=policy, now=now
        )
        result.selections = selections
        result.quarantined.extend(pulled)
    return result


def render(result: CardResult) -> str:
    lines: list[str] = []
    add = lines.append
    league = result.league
    add(f"# {league.title} card — {result.slate_date}")
    add("")
    eligible = sorted(m for m, s in result.market_states.items() if s == "eligible")
    if eligible:
        add(
            f"**{len(eligible)} market(s) are allowlisted**: "
            + ", ".join(f"`{m}`" for m in eligible)
            + ". The approval records an owner's decision, not a measurement."
        )
    else:
        add(ACCUMULATING_NOTE)
    if result.shapes_summary:
        add("")
        add(result.shapes_summary)

    if not result.games:
        add("")
        add(
            f"**No {league.title} games were priced for {result.slate_date}.** "
            "That is an absence, not a fault, and not a no-value call."
        )
    else:
        add("")
        add(f"## Slate ({len(result.games)} game(s) staged)")
        add("")
        add(", ".join(result.games))

        add("")
        add("## Selections")
        add("")
        if result.selections:
            add(NO_DEMONSTRATED_EDGE_NOTE)
            add("")
            add("| Game | Market | Selection | Line | Price | Book | Model | Edge |")
            add("|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|")
            for pick in result.selections:
                line = "—" if pick.get("line") is None else f"{pick['line']:+g}"
                add(
                    f"| {pick['game']} | `{pick['market']}` | "
                    f"{pick['selection']} | {line} | {int(pick['odds']):+d} | "
                    f"{pick['book']} | {pick['model_probability']:.1%} | "
                    f"{pick['edge']:+.1%} |"
                )
            add("")
            add(
                "The spread, the total and any ladder rung on one game are one "
                "afternoon seen several ways. They are never staked as "
                "independent, and their edges are never summed."
            )
        elif eligible:
            add(
                "**None.** Markets are allowlisted, but nothing cleared every "
                "bar today. That is a genuine judgement about markets that "
                "were priced and modelled."
            )
        else:
            add(
                "**None.** Not a pass, not an avoid, and not a no-value call — "
                "no market is allowlisted, so the card may not select."
            )

    excluded = {m: s for m, s in result.market_states.items() if s != "eligible"}
    if excluded:
        add("")
        add("## Markets excluded from selection, and why")
        add("")
        add("An excluded market is never a pass, an avoid, or a no-value call.")
        add("")
        grouped: dict[str, list[str]] = {}
        for market, state in sorted(excluded.items()):
            grouped.setdefault(state, []).append(market)
        for state, markets in grouped.items():
            add(f"- {', '.join(f'`{m}`' for m in markets)} — {state}")

    if result.refused:
        add("")
        add(f"## Games this lab holds no opinion on ({len(result.refused)})")
        add("")
        add(
            "Refused by the fixture screen. Not a pass on the game: this lab "
            "has no opinion it is entitled to hold on it."
        )
        add("")
        for label in result.refused:
            add(f"- {label}")

    if result.quarantined:
        add("")
        add(f"## {QUARANTINE_HEADING}")
        add("")
        for label, reason in result.quarantined:
            add(f"- **{label}** — {reason}")

    add("")
    add("## The accounting identity")
    add("")
    add(f"`{result.diagnostics.identity_line()}`")
    if result.diagnostics.reasons:
        add("")
        for reason, count in result.diagnostics.reasons.most_common(10):
            add(f"- {count} x {reason}")
    if not result.diagnostics.reconciles():
        add("")
        add(
            "> **The identity does not reconcile.** A row fell out for a "
            "reason nobody counted, and that is a bug rather than a slate."
        )

    add("")
    add("## Forward evidence")
    add("")
    add(
        f"{result.frozen_rows:,} opinion(s) frozen for {result.slate_date}; "
        f"{result.ledger_rows:,} row(s) in the settled ledger. Frozen before "
        "kickoff, settled after, never repriced."
    )
    for note in result.notes:
        add("")
        add(f"> {note}")
    return "\n".join(lines) + "\n"
