#!/usr/bin/env python3
"""Fetch college schedules and results. Spends no provider credits.

    PYTHONPATH=src python scripts/fetch_ncaaf_data.py --seasons 2026

Downloads files from cfbfastR's committed data. No API key, no rate limit, and
re-runnable — so a number can always be checked against the source it came from.
"""

from __future__ import annotations

import argparse
import sys

from ncaaf_betting_lab.config import RAW_DIR
from ncaaf_betting_lab.data import cfbfastr
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    failures = 0
    for season in args.seasons:
        try:
            path = cfbfastr.fetch_schedule(league, RAW_DIR, season=season)
        except OSError as error:
            print(f"{season}: fetch failed — {error}", file=sys.stderr)
            failures += 1
            continue
        every = cfbfastr.load_schedule(league, RAW_DIR, season=season)
        # A completed season's file carries every division; the current
        # season's carries FBS-involving games only. Reporting raw row counts
        # would compare 3,801 against 888 as though they answered one question.
        games = cfbfastr.fbs_involving_games(every)
        rateable = cfbfastr.rateable_games(games)
        done = [g for g in games if g.has_result]
        print(
            f"{season}: {len(every):,} rows in the file, of which "
            f"{len(games):,} involve an FBS team | "
            f"{len(cfbfastr.fbs_teams(games))} FBS teams | "
            f"{len(rateable):,} rateable (FBS v FBS), "
            f"{len(games) - len(rateable):,} declined as unrateable | "
            f"{len(done):,} with a result"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
