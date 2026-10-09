#!/usr/bin/env python3
"""Produce the card, freeze its opinions, and settle the days that are final.

    PYTHONPATH=src python scripts/run_gameday_card.py --live --credit-cap 1200 --tier 2

Ported from the sibling NFL lab's script of the same name. Without `--live`
nothing is fetched and no credit is spent; the card is built from whatever is
already staged, which is how the whole path is exercised without a
credential.

**The cap is Cooper's, agreed 2026-10-01: 1,200 credits a day, all ten
markets** (`data/outputs/ncaaf_credit_cost.md`). A run with a higher cap
than the league's registered one is refused, so a typo in a workflow cannot
spend past what was agreed.

The order is the one the NFL lab earned: refuse on a thin quota rather than
half-fetch; a fetch that recorded any error publishes `degraded`, never
`no-slate`, because a quiet night is the one decision that is invisible by
design; a rehearsal never touches the evidence.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from ncaaf_betting_lab.config import (
    ARCHIVE_DIR,
    OUTPUTS_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    STAGING_DIR,
)
from ncaaf_betting_lab.data.cfbfastr import load_schedule
from ncaaf_betting_lab.fixtures import Match, ScheduleIndex, describe
from ncaaf_betting_lab.forward_evidence import (
    append_ledger,
    ledger_path as forward_ledger_path,
    settle_snapshot,
    snapshots_dir,
    write_snapshot,
)
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from ncaaf_betting_lab.models import shapes as shape_fit
from ncaaf_betting_lab.providers.env_file import load_provider_env, redact
from ncaaf_betting_lab.providers.odds_api import (
    STAGING_PRICES_FILENAME,
    OddsApiProvider,
    ProviderError,
    sufficient_quota,
)
from ncaaf_betting_lab.providers.team_names import load_membership
from ncaaf_betting_lab.data import starters as starter_data
from ncaaf_betting_lab.models import form
from ncaaf_betting_lab.reports import form_context, gameday_card, provider_shadow
from ncaaf_betting_lab.reports.card_pricing import Fixture, consensus, price_slate
from ncaaf_betting_lab.season import game_date
from ncaaf_betting_lab.selection import selection_key
from ncaaf_betting_lab.staging_provider_policy import StagingProviderPolicy

#: Written by `scripts/build_line_table.py`. Named here rather than imported,
#: because a script importing another script is a coupling nothing tests.
LINE_TABLE_FILENAME = "line_table.csv"


def describe_slate(
    prices: pd.DataFrame, *, league, membership, schedule: ScheduleIndex
) -> tuple[dict[tuple[str, str], Fixture], dict[tuple[str, str], Match], list[str]]:
    """Every staged fixture, screened by identity, in one place."""
    fixtures: dict[tuple[str, str], Fixture] = {}
    matches: dict[tuple[str, str], Match] = {}
    refused: list[str] = []
    if prices.empty:
        return fixtures, matches, refused
    columns = ["home_team", "away_team", "commence_time"]
    for home, away, commence in prices[columns].drop_duplicates().itertuples(index=False):
        home, away = str(home), str(away)
        if (home, away) in fixtures:
            continue
        day = game_date(commence, league)
        fixture, match = describe(
            home, away, day, membership=membership, schedule=schedule
        )
        fixtures[(home, away)] = fixture
        if match is not None:
            matches[(home, away)] = match
        if fixture.refusal is not None:
            refused.append(f"{away} @ {home} — {fixture.reason}")
    return fixtures, matches, sorted(refused)


#: What a run records about itself for `scripts/card_feed.py`. Written on every
#: exit, so a run that stopped is read as degraded rather than as nothing.
RUN_STATUS_STEM = "card_run"


def main(argv: list[str] | None = None) -> int:
    state: dict = {"decision": "degraded", "selections": []}
    try:
        code = _main(argv, state)
    finally:
        _write_status(state)
    return code


def _write_status(state: dict) -> None:
    import json

    league = league_for(state.get("league", DEFAULT_LEAGUE_KEY))
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name(RUN_STATUS_STEM, ".json")).write_text(
        json.dumps(state, indent=2, default=str) + "\n", encoding="utf-8"
    )


def _main(argv: list[str] | None, state: dict) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument("--horizon-days", type=int, default=1)
    parser.add_argument("--credit-cap", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--slate-date", default="")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument(
        "--rehearsal-date",
        default="",
        help=(
            "Shorthand the workflow uses: a non-empty date means --rehearsal "
            "--slate-date DATE, and an empty one means a real run. Taken here "
            "rather than branched on in shell, so the workflow step stays one "
            "command whose failure cannot be swallowed by a conditional."
        ),
    )
    args = parser.parse_args(argv)
    if args.rehearsal_date.strip():
        args.rehearsal = True
        args.slate_date = args.rehearsal_date.strip()

    league = league_for(args.league)
    state["league"] = league.key
    now = datetime.now(timezone.utc)
    today = game_date(now.isoformat(), league)
    slate_date = args.slate_date or today
    state["slate_date"] = slate_date

    # A live run pricing any date but today must say it is a rehearsal:
    # freezing a snapshot for a future slate would make the real run that day
    # find one already standing and leave it there.
    if args.live and args.slate_date and args.slate_date != today and not args.rehearsal:
        print(
            "::error::--slate-date other than today on a live run needs "
            "--rehearsal, or the rehearsal's snapshot would stand in for the "
            "real day's.",
            file=sys.stderr,
        )
        return 2
    archive_dir = (
        ARCHIVE_DIR.parent / "rehearsal_archive" if args.rehearsal else ARCHIVE_DIR
    )
    if args.live:
        if args.credit_cap <= 0:
            print("::error::--live requires a positive --credit-cap.", file=sys.stderr)
            return 2
        if args.credit_cap > league.daily_credit_cap:
            print(
                f"::error::--credit-cap {args.credit_cap} is above the agreed "
                f"{league.daily_credit_cap:,} a day. Raising it is Cooper's "
                "decision, recorded in the registry, not a flag.",
                file=sys.stderr,
            )
            return 2

    try:
        membership = load_membership(league, RAW_DIR, season=args.season)
        schedule_games = load_schedule(league, RAW_DIR, season=args.season)
    except (FileNotFoundError, OSError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        print("decision=degraded")
        return 1
    schedule = ScheduleIndex(schedule_games, league)

    # -- prices ----------------------------------------------------------
    if args.live:
        horizon_days = args.horizon_days
        if slate_date != today:
            horizon_days = max(
                horizon_days,
                (date.fromisoformat(slate_date) - date.fromisoformat(today)).days + 1,
            )
        load_provider_env()
        try:
            provider = OddsApiProvider(league)
            ok, note = sufficient_quota(provider.quota(), args.credit_cap)
            print(note)
            if not ok:
                print(f"::error::{note}", file=sys.stderr)
                return 2
            run = provider_shadow.run_shadow(
                provider,
                league,
                membership=membership,
                schedule=schedule,
                horizon_days=horizon_days,
                credit_cap=args.credit_cap,
                now=now,
                slate_date=today,
                tier=args.tier,
            )
        except ProviderError as exc:
            print(redact(f"The fetch failed: {exc}"), file=sys.stderr)
            print("decision=degraded")
            return 1
        provider_shadow.write_staging(run, STAGING_DIR)
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUTS_DIR / league.output_name("provider_fetch", ".md")).write_text(
            provider_shadow.render(run, league), encoding="utf-8"
        )
        print(run.summary_line())
        if run.errors or run.stopped_early:
            for note in list(run.errors) + (
                [f"stopped early: {run.stopped_early}"] if run.stopped_early else []
            ):
                print(f"::error::{redact(note)}", file=sys.stderr)
            print("decision=degraded")
            print(
                "The fetch did not complete, so this run is degraded and no "
                "card is published from a partial slate."
            )
            return 1

    prices = _read(STAGING_DIR / STAGING_PRICES_FILENAME)
    if prices.empty:
        prices = pd.DataFrame(
            columns=["market", "home_team", "away_team", "commence_time", "date"]
        )
    # Only this slate reaches the card. The staged file can span days, and
    # tomorrow's games priced into today's snapshot would freeze opinions the
    # card never held for that day.
    if "date" in prices.columns:
        prices = prices[prices["date"].astype(str) == slate_date].copy()

    # -- the opinion -----------------------------------------------------
    shapes = shape_fit.fit(
        _read(PROCESSED_DIR / LINE_TABLE_FILENAME), before_season=args.season
    )
    fixtures, matches, refused = describe_slate(
        prices, league=league, membership=membership, schedule=schedule
    )
    probabilities, diagnostics = price_slate(
        prices, league, shapes=shapes, fixtures=fixtures
    )

    policy = StagingProviderPolicy.load()
    card = gameday_card.build_card(
        prices,
        league,
        policy=policy,
        diagnostics=diagnostics,
        now=now,
        slate_date=slate_date,
        refused=refused,
        probabilities=probabilities,
        shapes_summary=shapes.summary(),
    )

    # -- freeze, then settle --------------------------------------------
    frozen = write_snapshot(
        prices,
        probabilities,
        key_for=lambda row, *, market, selection, line: selection_key(
            row, market=market, selection=selection, line=line, league=league
        ),
        matches=matches,
        gates_in_force=policy.summary_line(league),
        snapshot_date=slate_date,
        archive_dir=archive_dir,
    )
    if frozen is None:
        card.notes.append(
            f"A snapshot for {slate_date} already stands and was not "
            "overwritten. The first opinion of the day is the one that settles."
        )
    else:
        card.frozen_rows = len(_read(frozen))

    ledger_path = forward_ledger_path()
    if not args.rehearsal:
        settled = settle_pending(
            schedule_games, ledger_path, archive_dir=ARCHIVE_DIR, as_of=now.date()
        )
        if settled:
            card.notes.append(f"Settled {settled} snapshot day(s) into the ledger.")
    card.ledger_rows = len(_read(ledger_path))

    if args.rehearsal:
        card.notes.append(
            "**This is a rehearsal.** The snapshot went to a rehearsal archive "
            "and nothing was settled."
        )
    report = gameday_card.render(card) + "\n" + form_section(
        prices, matches, league=league, season=args.season, now=now
    )
    if args.rehearsal:
        report = "> **REHEARSAL — not a card.**\n\n" + report
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("gameday_card", ".md")).write_text(
        report, encoding="utf-8"
    )
    print()
    print(report)
    decision = "rehearsal" if args.rehearsal else card.decision
    state.update(
        decision=decision,
        selections=[
            {k: pick[k] for k in ("game", "market", "selection", "line", "odds", "book", "edge")}
            for pick in card.selections
        ],
        frozen_rows=card.frozen_rows,
        ledger_rows=card.ledger_rows,
    )
    print(f"decision={decision}")
    return 0


#: Seasons of results the form rating reads. Its half-life makes anything older
#: weigh almost nothing, and step 5's history began in 2021 too.
FORM_HISTORY_SEASONS = 5


def form_section(prices, matches, *, league, season: int, now: datetime) -> str:
    """The form rating and quarterback flags for this slate, as context.

    A failure here never degrades the card — the probabilities do not read it —
    but it is never silent either: the section says it failed and why.
    """
    try:
        history: list = []
        for year in range(season - FORM_HISTORY_SEASONS, season + 1):
            try:
                history.extend(load_schedule(league, RAW_DIR, season=year))
            except (FileNotFoundError, OSError):
                continue
        frame = form.games_frame(history)
        ratings = form.fit(frame, season=season, as_of=now)
        try:
            starters = starter_data.load_starters(league, RAW_DIR, season=season)
        except (FileNotFoundError, OSError, KeyError, ValueError):
            starters = None
        season_games = [g for g in history if g.season == season]
        quarterbacks = form_context.starter_states(season_games, starters, before=now)
        through = None
        if starters is not None and not starters.empty:
            played = {
                g.game_id: g.start_date[:10] for g in season_games if g.start_date
            }
            days = [played[i] for i in starters["game_id"].astype(str) if i in played]
            through = max(days) if days else None
        slate = {}
        for (home, away), match in matches.items():
            rows = prices[
                (prices["home_team"].astype(str) == home)
                & (prices["away_team"].astype(str) == away)
            ]
            line = consensus(rows, "spread", "home")
            # The provider's home handicap; flipped when the feed's home team
            # is the provider's away team.
            market = None if line is None else (line if match.flipped else -line)
            game = match.game
            slate[f"{game.away_team} @ {game.home_team}"] = (game, market)
        rows = form_context.build(slate, ratings, quarterbacks)
        return form_context.render(rows, ratings, starters_through=through)
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        print(f"::warning::form context failed: {exc}", file=sys.stderr)
        return (
            f"{form_context.HEADING}\n\n**Not available this run** — "
            f"{type(exc).__name__}: {exc}. The prices and selections above do "
            "not read it.\n"
        )


def settle_pending(games, ledger_path: Path, *, archive_dir: Path, as_of: date) -> int:
    """Settle every snapshot day not already in the ledger, each as a unit."""
    directory = snapshots_dir(archive_dir)
    if not directory.is_dir():
        return 0
    ledger = _read(ledger_path)
    already = (
        set(ledger["snapshot_date"].astype(str))
        if "snapshot_date" in ledger.columns
        else set()
    )
    settled_days = 0
    for path in sorted(directory.glob("*.csv")):
        day = path.stem
        if day in already or day >= as_of.isoformat():
            continue
        snapshot = _read(path)
        if snapshot.empty:
            continue
        result = settle_snapshot(snapshot, games=games, as_of=as_of)
        if append_ledger(result.settled, ledger_path):
            settled_days += 1
    return settled_days


def _read(path: Path) -> pd.DataFrame:
    """Read a CSV, treating an empty or unreadable one as empty.

    A zero-byte file is a real state — `git show > file` creates one when the
    show fails — and pandas raises on it.
    """
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError):
        print(f"::warning::{path.name} could not be parsed; treating it as empty.")
        return pd.DataFrame()


if __name__ == "__main__":
    raise SystemExit(main())
