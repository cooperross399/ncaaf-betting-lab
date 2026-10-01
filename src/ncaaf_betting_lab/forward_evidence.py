"""Freeze what the model said before kickoff, settle it after, accumulate.

The historical backtest re-prices past games with walk-forward fits, which is
honest but reconstructed. This is the stronger thing: **the opinion the live
card actually held, written down before kickoff, settled against the box score
after, and never revised.**

**Ported from the sibling NFL lab's `forward_evidence.py`**, with settlement
rewritten for college football: there are no player props here, and a game is
found by the schedule feed's `game_id`, frozen beside the opinion when it is
written, never by a team-name string. The 2026 schedule feed holds 888 games.
Historical college prices could be bought later, but **forward evidence cannot
be back-dated.** Every week the pipeline is not freezing opinions is a week of
clean out-of-sample data that is gone permanently, which is why this organ is
built before the models are good.

## Three stages, each idempotent

**Snapshot.** After the card prices a slate, every priced row is written to
`data/archive/priced_snapshots/{league date}.csv` with the model's
probability, the edge against the price as sold, and the gates in force. A
snapshot is evidence and is **never overwritten**: the first opinion of the
day stands, because the card's opinion repriced at a better moment is not the
card's opinion any more.

**Settle.** Once a snapshot day's games are final, each row is settled from
the schedule feed the rest of this lab reads — a second copy would be how the
next join bug starts. Settled rows append to the ledger; a row whose game
never produced a result inside the patience window, or whose market has no
in-season settlement source (the first-half markets), is recorded
**unsettleable**, counted, never guessed.

**Report.** Per-market accumulating intervals in the house vocabulary, sample
sizes beside every number, and "no demonstrated edge" in those words while it
is true — which it will be for a long time; `power.py` gives the arithmetic.

## Intervals are clustered by game, not by bet

The spread, the total and both team totals on one game are the same afternoon
seen four ways. A naive
binomial interval over correlated bets is **narrower than the truth**, and a
narrow interval is exactly how "no demonstrated edge" turns into a claim. So
the interval is computed on **per-game** returns, which is the unit that is
close to independent.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from ncaaf_betting_lab.config import PROCESSED_DIR
from ncaaf_betting_lab.data.cfbfastr import Game
from ncaaf_betting_lab.fixtures import Match
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.season import clean_text


SNAPSHOT_DIRNAME = "priced_snapshots"
LEDGER_FILENAME = "forward_evidence.csv"

#: Days to keep waiting for a result before recording a row unsettleable. A
#: postponed college game is usually replayed within the week or cancelled; a
#: fortnight without a final score means the row will never settle against the
#: game it priced.
PATIENCE_DAYS = 14

WON, LOST, PUSH, VOID, UNSETTLEABLE = "won", "lost", "push", "void", "unsettleable"

SNAPSHOT_COLUMNS = (
    "snapshot_date",
    # The schedule feed's id for the game, resolved when the opinion was
    # frozen, and whether the feed's home team is the provider's away team.
    # Settlement reads these and nothing else to find the game.
    "game_id",
    "flipped",
    "commence_time",
    "home_team",
    "away_team",
    "market",
    "selection",
    "line",
    "american_odds",
    "book",
    "model_probability",
    "edge",
    "gates_in_force",
)

LEDGER_COLUMNS = SNAPSHOT_COLUMNS + ("settled_at", "outcome", "actual", "profit_units")

#: Markets settled from the final score. The first-half markets are absent on
#: purpose: no in-season half-time score source exists (`docs/build_order.md`,
#: 1.2), so they are recorded unsettleable rather than settled on a guess.
TEAM_SETTLEMENT = frozenset(
    {
        "moneyline",
        "spread",
        "alternate_spread",
        "total_points",
        "alternate_total_points",
        "team_total",
        "alternate_team_total",
    }
)


def _is_empty(path: Path) -> bool:
    """Whether a snapshot holds no frozen opinions.

    Rows, not existence. A header-only CSV exists and is worth nothing.
    """
    try:
        return len(pd.read_csv(path)) == 0
    except (OSError, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError):
        # An unreadable snapshot is not evidence either, and refusing to
        # overwrite it would lock the day on a corrupt file.
        return True


def snapshots_dir(archive_dir: Path) -> Path:
    return Path(archive_dir) / SNAPSHOT_DIRNAME


def ledger_path(processed_dir: Path | None = None) -> Path:
    """Where the card writes the forward ledger, and so where every reader reads it.

    In the sibling NFL lab, readers once disagreed about this path: a watchdog
    read a folder nothing wrote and every played day read as lost. One
    function, so no reader here can pick a second spelling.
    """
    base = PROCESSED_DIR if processed_dir is None else Path(processed_dir)
    return base / LEDGER_FILENAME


def american_to_implied(odds: float) -> float:
    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return -odds / (-odds + 100.0)


def profit_on_win(odds: float, stake: float = 1.0) -> float:
    odds = float(odds)
    return stake * (odds / 100.0 if odds > 0 else 100.0 / -odds)


def write_snapshot(
    prices: pd.DataFrame,
    probabilities: Mapping[tuple, float],
    *,
    key_for,
    matches: Mapping[tuple[str, str], Match],
    gates_in_force: str,
    snapshot_date: str,
    archive_dir: Path,
) -> Path | None:
    """Freeze today's priced opinions. Returns None when one already stands.

    `key_for(row, market, selection, line)` is the card's own key function,
    passed in rather than imported by both sides — the probability map and the
    snapshot must agree on the key **by construction**, not by both happening
    to import the same helper.

    `matches` maps the provider's `(home, away)` strings to the schedule game
    `fixtures.describe` found. A priced row with no match is not frozen: it
    could never be settled, and an opinion that cannot settle is not evidence.
    """
    directory = snapshots_dir(archive_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{snapshot_date}.csv"
    if target.exists() and not _is_empty(target):
        # The first opinion of the day stands. Two snapshots for one day would
        # let the flattering one be the one that settles.
        return None
    # ...but the first *opinion*, not the first *file*. An empty snapshot is
    # not an opinion. The sibling NFL lab's first live run wrote one on a day
    # with no games; on a real game day the same thing happens whenever the
    # early run fetched nothing, and the day would be locked empty. The
    # evidence cannot be created later.

    rows: list[dict[str, object]] = []
    for row in prices.itertuples():
        market = clean_text(getattr(row, "market", ""))
        selection = clean_text(getattr(row, "selection", "")).lower()
        line_value = getattr(row, "line", None)
        try:
            line = (
                None
                if line_value is None or pd.isna(line_value)
                else float(line_value)
            )
        except (TypeError, ValueError):
            line = None
        probability = probabilities.get(
            key_for(row, market=market, selection=selection, line=line)
        )
        if probability is None:
            continue
        home = clean_text(getattr(row, "home_team", ""))
        away = clean_text(getattr(row, "away_team", ""))
        match = matches.get((home, away))
        if match is None:
            continue
        odds = getattr(row, "american_odds", None)
        try:
            implied = american_to_implied(float(odds))
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "snapshot_date": snapshot_date,
                "game_id": str(match.game.game_id),
                "flipped": bool(match.flipped),
                "commence_time": clean_text(getattr(row, "commence_time", "")),
                "home_team": home,
                "away_team": away,
                "market": market,
                "selection": selection,
                "line": line,
                "american_odds": odds,
                "book": clean_text(getattr(row, "book", "")),
                "model_probability": probability,
                "edge": probability - implied,
                "gates_in_force": gates_in_force,
            }
        )
    frame = pd.DataFrame(rows, columns=list(SNAPSHOT_COLUMNS))
    frame.to_csv(target, index=False)
    return target


@dataclass
class SettlementResult:
    settled: pd.DataFrame
    unsettleable: int = 0
    voided: int = 0
    notes: list[str] = field(default_factory=list)


def _flag(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    try:
        return bool(value) and not pd.isna(value)
    except (TypeError, ValueError):
        return False


def settle_snapshot(
    snapshot: pd.DataFrame,
    *,
    games: Iterable[Game],
    as_of: date,
    settled_at: str | None = None,
) -> SettlementResult:
    """Settle one day's frozen opinions against the schedule feed's results.

    A row finds its game by the `game_id` frozen beside it — never by
    re-resolving team names, which could resolve differently a week later.
    Scores are read from the provider's side through `flipped`, so a neutral-
    site game where the two disagree about who is home settles the side that
    was priced.

    A day is settled **as a unit**: a partially settled day would let the
    early games into the ledger and leave the late ones out, and the late
    window is a systematically different set of fixtures.
    """
    stamp = settled_at or datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []
    result = SettlementResult(settled=pd.DataFrame(columns=list(LEDGER_COLUMNS)))
    if snapshot.empty:
        return result

    by_id = {str(game.game_id): game for game in games}
    pending_days: set[str] = set()
    for row in snapshot.itertuples():
        game = by_id.get(_game_id(getattr(row, "game_id", "")))
        if game is None or not game.has_result:
            elapsed = _days_since(clean_text(getattr(row, "snapshot_date", "")), as_of)
            if elapsed is not None and elapsed < PATIENCE_DAYS:
                pending_days.add(str(row.snapshot_date))
    if pending_days:
        # Not settled, and not recorded as anything else either: the whole day
        # waits for its last game rather than entering the ledger in part.
        result.notes.append(
            f"{len(pending_days)} day(s) still waiting on a result: "
            + ", ".join(sorted(pending_days))
        )

    for row in snapshot.itertuples():
        day = clean_text(getattr(row, "snapshot_date", ""))
        if day in pending_days:
            continue
        record = dict(row._asdict())
        record.pop("Index", None)
        record["settled_at"] = stamp
        game = by_id.get(_game_id(record.get("game_id", "")))
        if game is None or not game.has_result:
            record.update(
                {"outcome": UNSETTLEABLE, "actual": None, "profit_units": 0.0}
            )
            result.unsettleable += 1
            rows.append(record)
            continue
        home_score, away_score = float(game.home_points), float(game.away_points)
        if _flag(record.get("flipped")):
            home_score, away_score = away_score, home_score
        outcome, actual = _settle_row(record, home_score, away_score)
        record["actual"] = actual
        record["outcome"] = outcome
        if outcome == WON:
            record["profit_units"] = profit_on_win(record["american_odds"])
        elif outcome == LOST:
            record["profit_units"] = -1.0
        else:
            # A push and a void both return the stake. They are recorded
            # separately because they mean different things: a push is a
            # result, a void is a bet that never existed.
            record["profit_units"] = 0.0
            if outcome == VOID:
                result.voided += 1
            if outcome == UNSETTLEABLE:
                result.unsettleable += 1
        rows.append(record)

    result.settled = pd.DataFrame(rows, columns=list(LEDGER_COLUMNS))
    return result


def _game_id(value) -> str:
    """`401752702.0` read back from a CSV is the same game as `401752702`."""
    text = clean_text(value)
    return text[:-2] if text.endswith(".0") else text


def _days_since(day: str, as_of: date) -> int | None:
    try:
        return (as_of - date.fromisoformat(str(day)[:10])).days
    except ValueError:
        return None


def _settle_row(
    record: dict, home_score: float, away_score: float
) -> tuple[str, float | None]:
    market = str(record.get("market", ""))
    if market not in TEAM_SETTLEMENT:
        # The first-half markets, and anything unknown. No guess.
        return UNSETTLEABLE, None
    line = record.get("line")
    if line is not None and isinstance(line, float) and math.isnan(line):
        line = None
    return _settle_team(
        market, str(record.get("selection", "")), line, home_score, away_score
    )


def _settle_team(
    market: str, selection: str, line, home_score: float, away_score: float
) -> tuple[str, float | None]:
    if market == "moneyline":
        if home_score == away_score:
            # A college game cannot end level: overtime decides it. A level
            # final score is a data error or an abandoned game, and is
            # recorded as such rather than graded as a push.
            return UNSETTLEABLE, 0.0
        winner = "home" if home_score > away_score else "away"
        return (WON if selection == winner else LOST), home_score - away_score
    if line is None:
        return UNSETTLEABLE, None
    line = float(line)
    if market in {"spread", "alternate_spread"}:
        if selection not in {"home", "away"}:
            return UNSETTLEABLE, None
        margin = (home_score - away_score) if selection == "home" else (
            away_score - home_score
        )
        adjusted = margin + line
        if adjusted == 0:
            return PUSH, margin
        return (WON if adjusted > 0 else LOST), margin
    if market in {"total_points", "alternate_total_points"}:
        if selection not in {"over", "under"}:
            return UNSETTLEABLE, None
        combined = home_score + away_score
        if combined == line:
            return PUSH, combined
        over = combined > line
        return (WON if (over == (selection == "over")) else LOST), combined
    if market in {"team_total", "alternate_team_total"}:
        if "_" not in selection:
            return UNSETTLEABLE, None
        which, direction = selection.rsplit("_", 1)
        if which not in {"home", "away"} or direction not in {"over", "under"}:
            return UNSETTLEABLE, None
        score = home_score if which == "home" else away_score
        if score == line:
            return PUSH, score
        over = score > line
        return (WON if (over == (direction == "over")) else LOST), score
    return UNSETTLEABLE, None


def append_ledger(settled: pd.DataFrame, ledger_path: Path) -> int:
    """Append settled rows, never duplicating a day already recorded.

    ## Why the schema is checked rather than concatenated and hoped over

    `pd.concat` over frames that disagree on columns fills the gap with NaN,
    silently, in both directions. That is how `run_availability_cost.py` lost
    two of three seasons of injury designations in this very repository: the
    2022-2024 files had no `season_type` column, `concat` gave those rows NaN,
    and `frame[frame["season_type"] == "REG"] `is False for NaN — 5,794 rows
    survived of 23,575. Nothing failed, because the unmatched rows fell into a
    fail-open default and the report agreed with itself.

    This ledger is the worst place in the repository for that. It is
    append-only, it **cannot be back-dated**, and `CLAUDE.md` calls it "the
    only evidence that can still grow". It already holds **132,856 rows across
    seven game days** and gains a slate every week of the season.

    Add a column to `LEDGER_COLUMNS` and every one of those historical rows
    gets NaN for it. The four readers below all filter on `outcome`, which has
    been declared since the start — but the next one to filter on a newly
    added column would silently report on recent rows only, and the reading
    would be wrong in whichever direction that column correlates with time.

    Guarded now because the file's columns still match `LEDGER_COLUMNS`
    exactly, so the check passes on today's ledger and costs nothing. Every
    game day makes it more expensive to add.

    Two rules, ported from the golf lab where the same shape was found:

    * A column the ledger holds that `LEDGER_COLUMNS` does not is **refused**
      when it carries any value, because writing the union back would either
      drop recorded evidence or keep a column nothing maintains.
    * Both sides are reindexed to the declared schema before concatenating, so
      a newly added column is NaN by decision and visible here rather than a
      side effect of `concat` — and the file's column ORDER cannot drift.
    """
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if settled.empty:
        return 0
    if ledger_path.is_file():
        existing = pd.read_csv(ledger_path)
        stale = [
            column for column in existing.columns
            if column not in LEDGER_COLUMNS and existing[column].notna().any()
        ]
        if stale:
            raise ValueError(
                f"{ledger_path} holds column(s) {stale} that LEDGER_COLUMNS no "
                "longer declares, and they carry data. Appending would write a "
                "frame that either drops them or keeps a column nothing "
                "maintains. This ledger cannot be back-dated, so the mismatch "
                "is refused rather than reconciled by guess."
            )
        already = set(existing["snapshot_date"].astype(str))
        settled = settled[~settled["snapshot_date"].astype(str).isin(already)]
        if settled.empty:
            return 0
        combined = pd.concat(
            [existing.reindex(columns=list(LEDGER_COLUMNS)),
             settled.reindex(columns=list(LEDGER_COLUMNS))],
            ignore_index=True,
        )
    else:
        combined = settled.reindex(columns=list(LEDGER_COLUMNS))
    combined.to_csv(ledger_path, index=False)
    return len(settled)


def interval_by_game(ledger: pd.DataFrame) -> tuple[float, float, float, int, int]:
    """`(roi, low, high, bets, games)` with the interval clustered by game.

    Clustered because the selections inside one game are not independent. A
    naive per-bet interval is narrower than the truth, and a narrow interval
    is how "no demonstrated edge" quietly becomes a claim.
    """
    staked = ledger[ledger["outcome"].isin({WON, LOST, PUSH})]
    if staked.empty:
        return 0.0, 0.0, 0.0, 0, 0
    staked = staked.assign(
        _game=staked["snapshot_date"].astype(str)
        + " "
        + staked["away_team"].astype(str)
        + "@"
        + staked["home_team"].astype(str)
    )
    # The pair of names and the day, not the frozen game id: two rows of one
    # game always share both, and keying on the names keeps this function
    # usable on a frame that has no id column.
    per_game = staked.groupby("_game").agg(
        profit=("profit_units", "sum"), bets=("profit_units", "size")
    )
    total_bets = int(per_game["bets"].sum())
    games = len(per_game)
    if not total_bets:
        return 0.0, 0.0, 0.0, 0, games
    roi = float(per_game["profit"].sum() / total_bets)
    if games < 2:
        return roi, float("-inf"), float("inf"), total_bets, games
    # Standard error of the mean per-bet return, from between-game variation.
    #
    # The cluster-robust standard error of a RATIO estimator, which is what a
    # pooled ROI is: total profit over total bets, where games contribute
    # unequal numbers of bets, as the sibling NFL lab's `props_backtest._interval`
    # computes it.
    #
    # The NFL lab's first version of this function divided by `games` twice
    # and was sqrt(games) too narrow; it was ported here after that fix, and a
    # test against a bootstrap over games holds it.
    residuals = per_game["profit"] - roi * per_game["bets"]
    mean_bets = total_bets / games
    variance = float((residuals**2).sum() / (games * (games - 1)))
    standard_error = math.sqrt(max(variance, 0.0)) / mean_bets
    return roi, roi - 1.96 * standard_error, roi + 1.96 * standard_error, total_bets, games


# -- reading the ledger back ------------------------------------------------


def render_ledger(
    ledger: pd.DataFrame,
    league: League,
    *,
    settlement_suspects: frozenset[str] = frozenset(),
    minimum_bets: int = 200,
    families: int | None = None,
) -> str:
    """What the accumulated ledger supports, in the house vocabulary.

    Everything the historical work learned applies here and has to be applied
    *here*, not remembered: a settlement suspect's number is not evidence, an
    interval including zero is "no demonstrated edge" in those words, and a
    family correction across the markets reported is not optional because
    something always looks profitable by chance.

    No college price has been bought, so the ledger is the only priced
    evidence this lab has at all, and a mistake in reading it compounds for a
    season.
    """
    from statistics import NormalDist

    lines: list[str] = []
    add = lines.append
    add(f"# Forward evidence — {league.title}")
    add("")
    if ledger.empty:
        add(
            "**The ledger is empty.** No opinion has settled yet. That is an "
            "absence, not a result, and no number is offered in its place."
        )
        return "\n".join(lines) + "\n"

    settled = ledger[ledger["outcome"].isin({WON, LOST, PUSH})]
    voided = ledger[ledger["outcome"] == VOID]
    unsettleable = ledger[ledger["outcome"] == UNSETTLEABLE]
    days = sorted(set(ledger["snapshot_date"].astype(str)))

    add(
        f"**{len(ledger):,} frozen opinion(s) across {len(days)} day(s)**, "
        f"{days[0]} to {days[-1]}. {len(settled):,} settled, "
        f"{len(voided):,} voided (stake returned), "
        f"{len(unsettleable):,} unsettleable."
    )
    add("")
    add(
        "Every opinion here was frozen **before kickoff and never repriced**. "
        "No historical college price has been bought, so this is the only "
        "priced evidence the lab has."
    )
    add("")

    markets = sorted(set(settled["market"].astype(str)))
    # Across the CUMULATIVE count of everything this lab has ever tested when
    # the caller supplies it, not just the markets in this week's table. A
    # report that corrects across its own twelve rows, every week, for a
    # season, is correcting across twelve when the true family is hundreds —
    # and at a nominal 5% level roughly one look in twenty clears by chance.
    families = max(families if families is not None else len(markets), 1)
    factor = NormalDist().inv_cdf(1 - (0.05 / families) / 2) / 1.96

    add("| Market | Bets | Games | ROI | 95% interval | Family-corrected | Reading |")
    add("|:-------|-----:|------:|----:|:-------------|:-----------------|:--------|")
    for market in markets:
        rows = settled[settled["market"].astype(str) == market]
        roi, low, high, bets, games = interval_by_game(rows)
        half = (high - low) / 2 if math.isfinite(high - low) else float("inf")
        clow, chigh = roi - half * factor, roi + half * factor
        if market in settlement_suspects:
            reading = (
                "**not evidence** — this market is a settlement suspect; its "
                "return measures a disagreement between sources, not an edge"
            )
        elif bets < minimum_bets:
            reading = f"**not enough evidence** — {bets} bets, below {minimum_bets}"
        elif clow <= 0.0 <= chigh:
            reading = "**no demonstrated edge**"
        elif roi > 0.0:
            reading = "interval excludes zero, **positive**"
        else:
            # The direction is not decoration. Without it a market losing
            # money beyond chance printed the same words as one making it,
            # and "interval excludes zero" reads to anyone as good news. The
            # NHL lab shipped exactly this bug in its claims document, where
            # a replicated LOSS produced a headline that a market had
            # survived and replicated.
            reading = "interval excludes zero, **negative**"
        add(
            f"| `{market}` | {bets:,} | {games:,} | {roi:+.1%} | "
            f"{low:+.1%} to {high:+.1%} | {clow:+.1%} to {chigh:+.1%} | "
            f"{reading} |"
        )

    pooled_roi, pooled_low, pooled_high, pooled_bets, pooled_games = interval_by_game(
        settled[~settled["market"].astype(str).isin(settlement_suspects)]
    )
    add("")
    # The pooled line gets the same three guards every row above it gets.
    # Without them Week 1 prints a bold ROI over a handful of bets with no
    # reading at all, which is the single most quotable number in the file
    # and the least supported.
    #
    # And corrected across the same family every market row above it gets.
    # The pooled line was judged on its RAW interval while every row above was
    # judged on a corrected one, and the paragraph below then told the reader
    # the numbers were family-corrected. At the live factor that is an interval
    # 1.69x too narrow on the single most quotable sentence in the file: a
    # pooled +6.0% reading "interval excludes zero, positive" is -3.7% to
    # +15.7% once corrected, which any single market would report as no
    # demonstrated edge.
    pooled_half = (pooled_high - pooled_low) / 2 * factor
    pooled_clow, pooled_chigh = pooled_roi - pooled_half, pooled_roi + pooled_half
    if pooled_bets < minimum_bets:
        pooled_reading = (
            f"**not enough evidence** — {pooled_bets:,} bets, below "
            f"{minimum_bets}"
        )
    elif pooled_clow <= 0.0 <= pooled_chigh:
        pooled_reading = "**no demonstrated edge**"
    elif pooled_roi > 0.0:
        pooled_reading = "interval excludes zero, **positive**"
    else:
        pooled_reading = "interval excludes zero, **negative**"
    add(
        f"**Pooled, excluding settlement suspects: {pooled_roi:+.1%} over "
        f"{pooled_bets:,} bets across {pooled_games:,} games**, "
        f"family-corrected interval "
        f"{pooled_clow:+.1%} to {pooled_chigh:+.1%} — {pooled_reading}."
    )
    if settlement_suspects:
        add("")
        add(
            "Excluded as settlement suspects: "
            + ", ".join(f"`{m}`" for m in sorted(settlement_suspects))
            + ". A market settled on a different quantity from the one priced "
            "produces a constant offset, which replicates perfectly and looks "
            "exactly like an edge."
        )
    add("")
    add(
        "Intervals are clustered by game because selections inside one game "
        f"are not independent, and family-corrected across the {families} "
        "market(s) reported, or across the cumulative family when one is "
        "supplied. Unsettleable rows are excluded from the return rather than "
        "counted as losses."
    )
    return "\n".join(lines) + "\n"
