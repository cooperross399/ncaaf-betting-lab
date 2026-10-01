#!/usr/bin/env python3
"""What the card costs per league day, from the real schedule. Spends nothing.

    PYTHONPATH=src python scripts/estimate_credit_cost.py --season 2026 --tier 2

The bound per day is the one `providers/odds_api._guard` enforces before any
request: the bulk call at `bulk markets x regions`, plus `per-event markets x
regions` for every game that passes the fixture screen. Only FBS-vs-FBS games
pass it, so only they are counted per event. The real bill is lower, because a
per-event call is billed on markets RETURNED and an unquoted market costs
nothing; the bound is what the cap has to clear, not what will be spent.

Writes `data/outputs/ncaaf_credit_cost.md`.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date

from ncaaf_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from ncaaf_betting_lab.data.cfbfastr import load_schedule
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from ncaaf_betting_lab.markets import bulk_provider_keys, per_event_provider_keys
from ncaaf_betting_lab.providers.odds_api import DEFAULT_REGIONS
from ncaaf_betting_lab.season import game_date


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--tier", type=int, default=2)
    parser.add_argument("--from-date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    league = league_for(args.league)

    regions = len([r for r in DEFAULT_REGIONS.split(",") if r.strip()]) or 1
    bulk = len(bulk_provider_keys(args.tier)) * regions
    per_event = len(per_event_provider_keys(args.tier)) * regions

    fbs_only: Counter = Counter()
    every_game: Counter = Counter()
    for game in load_schedule(league, RAW_DIR, season=args.season):
        day = game_date(game.start_date, league)
        if day < args.from_date:
            continue
        every_game[day] += 1
        if game.is_fbs_only:
            fbs_only[day] += 1

    bounds = {day: bulk + per_event * fbs_only[day] for day in every_game}
    worst_day = max(bounds, key=bounds.get) if bounds else ""
    worst = bounds.get(worst_day, 0)
    total = sum(bounds.values())
    cap = league.daily_credit_cap

    lines = [
        f"# Credit cost — {league.title} {args.season}",
        "",
        f"Computed from the cfbfastR schedule for league days from "
        f"{args.from_date}, tier {args.tier}: {len(bulk_provider_keys(args.tier))} "
        f"bulk market(s) and {len(per_event_provider_keys(args.tier))} per-event "
        f"market(s), {regions} region(s).",
        "",
        f"- **{len(bounds)} league days** carrying **{sum(every_game.values()):,} "
        f"games**, of which **{sum(fbs_only.values()):,} are FBS-vs-FBS** and "
        "fetched per event.",
        f"- Per-day bound: {bulk} for the bulk call plus {per_event} per "
        "FBS-vs-FBS game.",
        f"- **Worst day: {worst_day}, {fbs_only.get(worst_day, 0)} games, "
        f"bound {worst:,} credits.**",
        f"- Rest of the scheduled season, bound: **{total:,} credits**.",
        "",
        f"**The registered cap is {cap:,} a day** "
        f"({cap / worst:.1f}x the worst day)" if worst else
        f"**The registered cap is {cap:,} a day.**",
        "",
        "Agreed by Cooper on 2026-10-01 for all ten markets, against an "
        "earlier estimate of about twice the worst Saturday. A cap below the "
        "worst slate stops the fetch part-way through it, which reads in a "
        "report exactly like a market nobody quoted, so this file is "
        "regenerated rather than trusted.",
        "",
        "**Not in this figure:** conference championship and bowl games that "
        "the schedule feed does not list yet. They add per-event cost in "
        "December and are counted when they appear.",
        "",
        "| League day | Games | FBS-vs-FBS | Bound |",
        "|:--|--:|--:|--:|",
    ]
    for day in sorted(bounds):
        lines.append(f"| {day} | {every_game[day]} | {fbs_only[day]} | {bounds[day]:,} |")
    report = "\n".join(lines) + "\n"

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUTS_DIR / league.output_name("credit_cost", ".md")
    target.write_text(report, encoding="utf-8")
    print(report)
    if worst > cap:
        print(f"::error::the worst day's bound {worst} exceeds the cap {cap}.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
