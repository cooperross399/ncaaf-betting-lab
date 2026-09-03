#!/usr/bin/env python3
"""Join free college lines to results. Spends nothing.

    PYTHONPATH=src python scripts/build_line_table.py --seasons 2024 2025

cfbfastR publishes 1.18M college line rows for 2006-2025 across 34 books,
including Pinnacle, with BOTH the opening and the closing number. That is the
gate on every market-relative test this lab intends to run, and it is free.

The join key needed normalising: line ids arrive as floats ("401761647.0") and
schedule ids as integers ("401761647"), so a naive merge matched **zero of
3,154** games while looking like a real answer. That is the join-key class of
defect this lab's sibling shipped twice, and it is why the match rate is
asserted rather than assumed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ncaaf_betting_lab.config import PROCESSED_DIR, RAW_DIR
from ncaaf_betting_lab.data.cfbfastr import load_schedule, rateable_games
from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for

LINES_URL = (
    "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main"
    "/betting/csv/cfb_line_odds.csv.gz"
)
LINES_FILENAME = "cfb_line_odds.csv.gz"
OUTPUT_FILENAME = "line_table.csv"

#: Below this the join has silently failed and every number downstream is
#: computed on whatever happened to match. Asserted, not hoped for.
#:
#: Measured from the RATEABLE games to the lines. The line feed carries every
#: division, so the reverse ratio is meaningless and looks like a failure.
MINIMUM_MATCH_RATE = 0.90


def fetch_lines(league, raw_dir: Path, *, timeout: int = 120) -> Path:
    from urllib.request import urlopen

    # The segment comes from the registry. Writing it here was a league literal
    # and the discipline test caught it, which is what it is for.
    target = Path(raw_dir) / league.data_dir_segment / "betting" / LINES_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size > 0:
        return target
    staging = target.with_suffix(".partial")
    with urlopen(LINES_URL, timeout=timeout) as response:  # noqa: S310
        staging.write_bytes(response.read())
    if staging.stat().st_size == 0:
        staging.unlink(missing_ok=True)
        raise OSError("the line feed returned an empty file")
    staging.replace(target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2025])
    args = parser.parse_args(argv)
    league = league_for(args.league)

    path = fetch_lines(league, RAW_DIR)
    lines = pd.read_csv(path, low_memory=False)
    # Normalise before joining. This is the whole reason the match rate is
    # checked below rather than trusted.
    lines["game_id"] = (
        pd.to_numeric(lines["game_id"], errors="coerce").astype("Int64").astype(str)
    )
    lines = lines[lines["season"].isin(args.seasons)]

    games = {}
    for season in args.seasons:
        for game in rateable_games(load_schedule(league, RAW_DIR, season=season)):
            if game.has_result:
                games[game.game_id] = game
    if not games:
        print("No completed FBS-vs-FBS games. Fetch schedules first.", file=sys.stderr)
        return 2

    # The rate that matters runs from the games we WANT to the lines, not the
    # other way. The line feed carries every division — FCS-vs-FCS included —
    # so measuring "what fraction of line games are rateable" answers a
    # question nobody asked and reads as a broken join. The first version of
    # this guard did exactly that and refused a perfectly good table at 50.9%.
    matched = set(lines["game_id"]) & set(games)
    rate = len(matched) / max(len(games), 1)
    if rate < MINIMUM_MATCH_RATE:
        print(
            f"Only {rate:.1%} of rateable games have a line. A join this bad "
            "produces a table that looks complete and describes a subset "
            "nobody chose.",
            file=sys.stderr,
        )
        return 2

    # THE SPREAD FEED CARRIES ONE ROW PER SIDE. Each book writes the game
    # twice — the home handicap and the away handicap, distinguished by `abbr`,
    # the team the number belongs to. Taking a median across both sides
    # collapses every spread to approximately ZERO, and it does it silently:
    # the table looks complete, every game has a number, and the number is a
    # pick'em. The first version of this script did exactly that, and the
    # market-anchored validation downstream was anchored to nothing.
    #
    # Totals carry one row per side too (over and under), but both sides quote
    # the same number, so the median is correct there and only the spread needs
    # this.
    lines["abbr"] = lines["abbr"].astype(str).str.strip()
    rows = []
    for (game_id, market), group in lines.groupby(["game_id", "market_type"]):
        game = games.get(game_id)
        if game is None:
            continue
        if market == "spread":
            group = group[group["abbr"] == game.home_team]
            if group.empty:
                # The home team's own row is what defines the handicap sign.
                # Without it the sign is a guess, and a guessed sign is a
                # backwards spread on every game it touches.
                continue
        closing = pd.to_numeric(group["lines"], errors="coerce").dropna()
        opening = pd.to_numeric(group["opening_lines"], errors="coerce").dropna()
        if closing.empty:
            continue
        rows.append({
            "game_id": game_id,
            "season": game.season,
            "week": game.week,
            "market": market,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "margin": game.margin,
            "total_points": game.total,
            "books": int(group["book"].nunique()),
            # Consensus in line space is the median, which is robust to one
            # book hanging an outlier — and an outlier is exactly what the
            # book-versus-consensus test is looking for.
            "close_consensus": float(closing.median()),
            "close_min": float(closing.min()),
            "close_max": float(closing.max()),
            "open_consensus": float(opening.median()) if not opening.empty else None,
        })
    table = pd.DataFrame(rows)
    if table.empty:
        print("Nothing joined.", file=sys.stderr)
        return 2
    table["line_move"] = table["close_consensus"] - table["open_consensus"]
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / OUTPUT_FILENAME
    table.to_csv(out, index=False)

    print(f"{len(table):,} game-markets over {table.game_id.nunique():,} games "
          f"-> {out}")
    print(f"  join match rate {rate:.1%} (floor {MINIMUM_MATCH_RATE:.0%})")
    for market, group in table.groupby("market"):
        moved = group["line_move"].abs()
        print(f"  {market:<11} {len(group):>5,} games | median {group.books.median():.0f} books"
              f" | line moved a median {moved.median():.2f} pts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
