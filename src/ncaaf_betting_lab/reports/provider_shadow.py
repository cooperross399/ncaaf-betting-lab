"""A live fetch that writes only to staging.

Ported from the sibling NFL lab's `reports/provider_shadow.py`. What changed is
the screen in the middle, because a college slate is a different shape: sixty
or more games on a Saturday, a third of them against opponents this lab has no
shape for, and nearly half of the season's kickoffs still flagged to be
announced a week out.

## The screens that run before a per-event credit is spent

**The horizon window, in the league's own date.** The events list returns
every upcoming game. The per-event fetch is windowed to the league days being
priced. The NFL version compared an Eastern game date with the UTC date of
the run, so a run after 20:00 ET looked one day ahead; here both sides are the
league's date.

**The fixture screen.** Every in-window event goes through
`fixtures.describe`, the same function the card and settlement use: both
names must resolve to this season's teams by identity, both must be FBS, the
game must be on the schedule, and its kickoff must be set. Only events that
pass are fetched per event, so an FCS opponent or an unscheduled exhibition
costs nothing past the bulk call. Every refusal is **counted and named**,
never quietly dropped.

The bulk call is still billed for the whole slate (`markets x regions`
whatever comes back), and every event it returns is staged, refused or not, so
the card's accounting identity can show the refused rows as buckets rather
than as an absence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ncaaf_betting_lab.fixtures import Match, ScheduleIndex, describe
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.markets import bulk_provider_keys, per_event_provider_keys
from ncaaf_betting_lab.providers.odds_api import (
    ROW_COLUMNS,
    STAGING_PRICES_FILENAME,
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    Spend,
    normalize_event,
)
from ncaaf_betting_lab.providers.team_names import UNRESOLVED, Membership
from ncaaf_betting_lab.reports.card_pricing import Fixture
from ncaaf_betting_lab.season import game_date

#: The per-event markets kept when the provider refuses the full list with a
#: 422: the ladders this lab prices. The half and team-total markets carry no
#: opinion yet, so they are the ones a degraded run gives up.
CORE_PER_EVENT_KEYS = ("alternate_spreads", "alternate_totals")


@dataclass
class ShadowRun:
    """What one live fetch saw, spent, and refused."""

    league_key: str
    fetched_at: str
    horizon_days: int
    window_start: str = ""
    events_listed: int = 0
    events_in_window: int = 0
    events_fetched: int = 0
    events_priced: int = 0
    refused: list[str] = field(default_factory=list)
    unresolved_names: set[str] = field(default_factory=set)
    #: Keyed by the provider's own `(home, away)` strings, for every
    #: in-window event, refused or not. The card prices from this.
    fixtures: dict[tuple[str, str], Fixture] = field(default_factory=dict)
    matches: dict[tuple[str, str], Match] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    unparseable: int = 0
    reasons: Counter = field(default_factory=Counter)
    spend: Spend = field(default_factory=Spend)
    stopped_early: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=list(ROW_COLUMNS))

    def summary_line(self) -> str:
        return (
            f"{len(self.rows):,} staged row(s) from {self.events_priced} of "
            f"{self.events_in_window} in-window event(s) "
            f"({self.events_listed} listed); {self.events_fetched} passed the "
            f"fixture screen and were fetched per event; "
            f"{len(self.refused)} refused; {self.unparseable} unparseable. "
            f"{self.spend.summary_line()}"
        )


def window_days(start: date, horizon_days: int) -> set[str]:
    return {
        date.fromordinal(start.toordinal() + offset).isoformat()
        for offset in range(max(int(horizon_days), 1))
    }


def run_shadow(
    provider: OddsApiProvider,
    league: League,
    *,
    membership: Membership,
    schedule: ScheduleIndex,
    horizon_days: int = 1,
    credit_cap: int,
    now: datetime | None = None,
    slate_date: str | None = None,
    tier: int = 1,
) -> ShadowRun:
    """Fetch the slate for the league day(s) starting `slate_date` (default today).

    "Today" is the league's date, never the UTC one: a run at 21:00 ET is
    still the same college Saturday.
    """
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = (
        date.fromisoformat(slate_date)
        if slate_date
        else moment.astimezone(league.timezone).date()
    )
    run = ShadowRun(
        league_key=league.key,
        fetched_at=moment.isoformat(),
        horizon_days=horizon_days,
        window_start=start.isoformat(),
    )
    days = window_days(start, horizon_days)

    try:
        events = provider.list_events()
    except ProviderError as exc:
        run.errors.append(str(exc))
        return run
    run.events_listed = len(events)

    in_window = [
        event for event in events
        if game_date(event.get("commence_time", ""), league) in days
    ]
    run.events_in_window = len(in_window)

    wanted: list[dict[str, Any]] = []
    for event in in_window:
        home = str(event.get("home_team", "")).strip()
        away = str(event.get("away_team", "")).strip()
        day = game_date(event.get("commence_time", ""), league)
        fixture, match = describe(
            home, away, day, membership=membership, schedule=schedule
        )
        run.fixtures[(home, away)] = fixture
        if match is not None:
            run.matches[(home, away)] = match
        for name in (home, away):
            if membership.resolve(name) == UNRESOLVED:
                run.unresolved_names.add(name)
        if fixture.refusal is not None:
            run.refused.append(f"{day} {away} @ {home} — {fixture.reason}")
            continue
        wanted.append(event)

    if not in_window:
        return run

    try:
        bulk = provider.fetch_bulk(
            bulk_provider_keys(tier), spend=run.spend, credit_cap=credit_cap
        )
    except CreditCapReached as exc:
        run.stopped_early = str(exc)
        return run
    except ProviderError as exc:
        run.errors.append(f"bulk fetch: {exc}")
        bulk = []

    in_window_ids = {str(event.get("id", "")) for event in in_window}
    payloads = [event for event in bulk if str(event.get("id", "")) in in_window_ids]

    per_event = per_event_provider_keys(tier)
    core = tuple(k for k in per_event if k in CORE_PER_EVENT_KEYS) or per_event
    markets = per_event
    for event in wanted if per_event else []:
        event_id = str(event.get("id", ""))
        try:
            extra = provider.fetch_event_odds(
                event_id, markets, spend=run.spend, credit_cap=credit_cap
            )
        except CreditCapReached as exc:
            run.stopped_early = str(exc)
            break
        except ProviderError as exc:
            # A 422 refuses the market LIST, so it would refuse it for every
            # remaining event too. Fall back once to the ladders this lab
            # prices and say what was dropped: a bounded, stated loss rather
            # than every per-event market silently gone for the season.
            if "422" in str(exc) and markets != core:
                dropped = sorted(set(markets) - set(core))
                markets = core
                run.errors.append(
                    "the provider refused the full per-event market list with "
                    f"a 422, so this run fell back to {list(core)} and dropped "
                    f"{dropped}. Those markets are absent from this run, not "
                    "empty."
                )
                try:
                    extra = provider.fetch_event_odds(
                        event_id, markets, spend=run.spend, credit_cap=credit_cap
                    )
                except CreditCapReached as cap_exc:
                    run.stopped_early = str(cap_exc)
                    break
                except ProviderError as retry_exc:
                    run.errors.append(f"event {event_id}: {retry_exc}")
                    continue
            else:
                run.errors.append(f"event {event_id}: {exc}")
                continue
        run.events_fetched += 1
        if extra:
            payloads.append(extra)

    seen_events: set[str] = set()
    for payload in payloads:
        parsed = normalize_event(payload, league, fetched_at=run.fetched_at)
        run.rows.extend(parsed.rows)
        run.unparseable += parsed.unparseable
        run.reasons.update(parsed.reasons)
        if parsed.rows:
            seen_events.add(str(payload.get("id", "")))
    run.events_priced = len(seen_events)
    return run


def write_staging(run: ShadowRun, staging_dir: Path) -> Path:
    """Write the staged table."""
    staging_dir = Path(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    path = staging_dir / STAGING_PRICES_FILENAME
    run.frame.to_csv(path, index=False)
    return path


def render(run: ShadowRun, league: League) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Provider fetch — {league.title}")
    add("")
    add(
        f"Fetched {run.fetched_at}, league day(s) from {run.window_start}, "
        f"horizon {run.horizon_days} day(s)."
    )
    add("")
    add(run.summary_line())
    if run.refused:
        add("")
        add(f"## Refused before the per-event fetch ({len(run.refused)})")
        add("")
        add(
            "Counted and named, never quietly dropped. A refused game is not "
            "a pass on it: this lab has no opinion it is entitled to hold."
        )
        add("")
        for label in run.refused:
            add(f"- {label}")
    if run.unresolved_names:
        add("")
        add("## Team names that did not resolve")
        add("")
        add(
            "Reported rather than guessed at. A name here belongs in "
            "`data/manual/provider_team_aliases.csv` once a human has checked "
            "which team it is."
        )
        add("")
        for name in sorted(run.unresolved_names):
            add(f"- `{name}`")
    if run.rows:
        frame = run.frame
        add("")
        add("## What was staged")
        add("")
        add("| Market | Rows | Books | Events |")
        add("|:-------|-----:|------:|-------:|")
        for market, group in frame.groupby("market"):
            add(
                f"| `{market}` | {len(group):,} | {group['book'].nunique()} | "
                f"{group['event_id'].nunique()} |"
            )
    if run.reasons:
        add("")
        add("## Outcomes this lab could not parse")
        add("")
        for reason, count in run.reasons.most_common():
            add(f"- {count} x {reason}")
    if run.stopped_early:
        add("")
        add(f"> **Stopped early.** {run.stopped_early}")
    for error in run.errors:
        add("")
        add(f"> {error}")
    return "\n".join(lines) + "\n"
