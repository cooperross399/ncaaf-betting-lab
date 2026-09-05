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


#: A book's spread is INVERTED when its number is about the negative of what
#: every other book quotes for the same side. Two guards keep this from firing
#: on an honest disagreement: the consensus must be far enough from pick'em
#: that a sign is meaningful at all, and the candidate must be much closer to
#: MINUS the others than to the others.
INVERSION_TOLERANCE = 0.5
INVERSION_SEPARATION = 1.0
PICKEM_GUARD = 1.0
MINIMUM_BOOKS_TO_JUDGE_A_SIGN = 3


def inverted_rows(closing: "pd.Series") -> list:
    """Index labels whose spread sits on the opposite convention to the rest.

    THE DEFECT THIS EXISTS FOR, measured on the shipped feed. Game 401331447
    (2021 wk14, Michigan at Iowa, neutral site, final Michigan 42 - Iowa 3):
    Bovada quotes the Iowa row at -12.0 close / -10.5 open while teamrankings,
    consensus and William Hill all quote it at +12.0. Michigan won by 39, so
    +12 is the honest sign and Bovada's row is backwards.

    That alone would be survivable -- the median of four ignores one outlier.
    What was not survivable is that `close_consensus` was the median over all
    four books and `open_consensus` was the median over the ONLY book carrying
    an opener, which was the inverted one. The two consensuses landed on
    opposite conventions and the game recorded a 22.5-point line move: 10.6
    standard deviations of the move distribution, and 1,721 of the 15,386
    pts^2 that the whole close-beats-open control was built from.

    42 book-rows across 39 games are inverted in the 2021-2025 feed, and in 37
    of those the inverted book is the only one quoting an opener.

    The rows are DROPPED, never corrected. Flipping a sign to what it "should
    have" been is fabricating a price, and a price that cannot be read stays
    missing.
    """
    numbers = closing.dropna()
    if len(numbers) < MINIMUM_BOOKS_TO_JUDGE_A_SIGN:
        return []
    if abs(float(numbers.median())) < PICKEM_GUARD:
        # Near pick'em, -0.5 and +0.5 are not opposite conventions, they are
        # two books disagreeing about a coin flip.
        return []
    bad = []
    for label, value in numbers.items():
        others = numbers.drop(label)
        if others.empty:
            continue
        centre = float(others.median())
        if abs(value + centre) <= INVERSION_TOLERANCE and abs(value - centre) > INVERSION_SEPARATION:
            bad.append(label)
    return bad


#: The largest within-book move any TWO books ever agreed on, measured across
#: 2021-2025 on 4,300 book-moves that had at least one peer within a point:
#:
#:   p50 1.00   p90 3.00   p99 6.50   p99.9 12.35   max 15.00
#:   moves above 15.00 with a corroborating peer: ZERO
#:
#: So a move larger than this has never been seen twice. It is an empirical
#: ceiling, not a chosen one, and it is the only threshold in this file that
#: was not derivable from a single game.
LARGEST_CORROBORATED_MOVE = 15.0

#: How close two books must be before one vouches for the other. The median
#: disagreement between books on the same game's move is 1.00 point, so a
#: peer inside a point is agreeing rather than coinciding.
CORROBORATION_WINDOW = 1.0


def uncorroborated_openers(moves: "pd.Series") -> list:
    """Index labels whose opener implies a move no other book will vouch for.

    THE DEFECT. Some openers in this feed are simply wrong rather than
    inverted. Game 401524046 (2023 wk10, Oregon State at Colorado): Bovada
    quotes the Colorado row at close 13.0 and open -23.5, a 36.5-point move,
    while DraftKings has 13.5 / 11.5 -- a 2-point move. Game 401531907 has
    Bovada at close -1.0 and open -35.0. Both are internally consistent inside
    the bad book, so `within_book_move` cannot see them: the move is real
    arithmetic on a fabricated price.

    WHY A MAGNITUDE THRESHOLD ALONE WOULD BE WRONG. Game 401754586 (2025 wk11,
    Florida State at Clemson) carries a genuine 15-point move: DraftKings and
    ESPN Bet BOTH quote -16.5 open and -1.5 close. A rule that dropped large
    moves would delete it, and deleting real data to remove fake data is a
    worse trade than leaving the fake data in.

    So the test is CORROBORATION, and magnitude only decides what needs
    corroborating. A move is refused when it is larger than any move two books
    have ever agreed on AND no book agrees with this one. Where a single book
    quotes the game, there is nobody to agree, so the ceiling stands alone --
    which is the honest position: an unprecedented move on one book's word is
    not evidence, it is an anecdote.

    Refused openers are DROPPED, never adjusted. There is no number to correct
    them to.
    """
    numbers = moves.dropna()
    refused = []
    for label, move in numbers.items():
        if abs(move) <= LARGEST_CORROBORATED_MOVE:
            continue
        peers = numbers.drop(label)
        vouched = (peers - move).abs().le(CORROBORATION_WINDOW).any()
        if not vouched:
            refused.append(label)
    return refused


def within_book_move(group: "pd.DataFrame") -> float | None:
    """The median move among books that quote BOTH an open and a close.

    `line_move` used to be `close_consensus - open_consensus`: a difference
    between two medians taken over DIFFERENT SETS OF BOOKS, since a book with
    no opener still votes on the close. That is a cross-book quantity wearing
    the name of a within-book one, and it is what let one inverted row become
    a 22.5-point "move".

    A move measured inside a single book cannot be a convention collision,
    because both halves come from the same quoting side. Where no book carries
    both, the move is NOT reconstructed from the two consensuses -- it is
    missing, and it stays missing.
    """
    both = group.dropna(subset=["_close", "_open"])
    if both.empty:
        return None
    moves = both["_close"] - both["_open"]
    refused = uncorroborated_openers(moves)
    if refused:
        moves = moves.drop(index=refused)
    if moves.empty:
        # Every book quoting both halves was refused. The move is unknown, and
        # an unknown move is missing rather than zero.
        return None
    return float(moves.median())


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
        group = group.assign(
            _close=pd.to_numeric(group["lines"], errors="coerce"),
            _open=pd.to_numeric(group["opening_lines"], errors="coerce"),
        )
        if market == "spread":
            backwards = inverted_rows(group["_close"])
            if backwards:
                group = group.drop(index=backwards)
            # An opener no other book will vouch for is dropped from the LEVEL
            # as well as from the move. Refusing it only inside
            # within_book_move left `open_consensus` as the median of a real
            # opener and a fabricated one: game 401524046 read -6.0, midway
            # between DraftKings' 11.5 and Bovada's -23.5. The move was right
            # and the level it moved from was invented.
            refused = uncorroborated_openers(group["_close"] - group["_open"])
            if refused:
                group.loc[refused, "_open"] = float("nan")
        closing = group["_close"].dropna()
        opening = group["_open"].dropna()
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
            # Measured inside a book, never across two. See within_book_move.
            "line_move": within_book_move(group),
        })
    table = pd.DataFrame(rows)
    if table.empty:
        print("Nothing joined.", file=sys.stderr)
        return 2
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
