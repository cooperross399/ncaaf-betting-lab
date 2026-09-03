"""Was every game day of a finished week frozen, and did it settle?

**The forward ledger is the only evidence this lab can still gather.** The
bought population is complete — the provider serves props only after
2023-05-03 and every event has been bought — and the free closing-line series
is fixed. What is left is 272 regular-season games a season across 57 game
days, and **it cannot be back-dated**: a Sunday that was never frozen is sample
that does not exist and cannot be made to.

That is what this watches. It is not a health check on a workflow; it is an
inventory of the asset. A run that dies quietly, a provider that returns
nothing, a guard that stands down on the wrong day — each of them costs a game
day, and none of them announces itself as a loss. The card feed looks the same
afterwards either way.

Read it against the schedule, not against what was fetched: the question is
"which days *should* have an opinion", and only the schedule knows that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

#: A snapshot with fewer rows than this is treated as a thin day rather than a
#: real one. A game day with three frozen opinions is not a slate; it is a run
#: that fetched almost nothing and wrote what it had.
THIN_SNAPSHOT_ROWS = 25

#: Days after kickoff before an unsettled day is a fault rather than a wait.
#: nflverse revises defensive counting stats between Monday and Wednesday, so
#: settlement deliberately lags; beyond this the row will never settle.
SETTLEMENT_GRACE_DAYS = 5


@dataclass(frozen=True)
class DayCoverage:
    """One scheduled game day, and what the lab actually holds for it."""

    day: str
    games: int
    frozen_rows: int
    settled_rows: int
    days_since: int

    @property
    def was_frozen(self) -> bool:
        return self.frozen_rows > 0

    @property
    def is_thin(self) -> bool:
        return 0 < self.frozen_rows < THIN_SNAPSHOT_ROWS

    @property
    def awaiting_settlement(self) -> bool:
        return self.days_since <= SETTLEMENT_GRACE_DAYS

    @property
    def state(self) -> str:
        if not self.was_frozen:
            return "LOST" if not self.awaiting_settlement else "not yet frozen"
        if self.is_thin:
            return "thin"
        if self.settled_rows > 0:
            return "settled"
        return "awaiting settlement" if self.awaiting_settlement else "UNSETTLED"


@dataclass
class CoverageResult:
    days: list[DayCoverage] = field(default_factory=list)

    @property
    def lost(self) -> list[DayCoverage]:
        """Game days that will never have an opinion. The only real failure."""
        return [d for d in self.days if d.state == "LOST"]

    @property
    def thin(self) -> list[DayCoverage]:
        return [d for d in self.days if d.is_thin]

    @property
    def unsettled(self) -> list[DayCoverage]:
        return [d for d in self.days if d.state == "UNSETTLED"]

    @property
    def is_intact(self) -> bool:
        return not self.lost and not self.thin and not self.unsettled


def measure(
    *,
    scheduled: dict[str, int],
    snapshot_rows: dict[str, int],
    settled_rows: dict[str, int],
    as_of: date,
) -> CoverageResult:
    """Compare the schedule against what was frozen and settled.

    `scheduled` maps a game date to its game count and is the authority: a day
    absent from it is not a day, and a day present in it that nothing was
    frozen for is a hole.
    """
    result = CoverageResult()
    for day in sorted(scheduled):
        try:
            since = (as_of - date.fromisoformat(day)).days
        except ValueError:
            continue
        if since < 0:
            # In the future. Nothing is owed for it yet.
            continue
        result.days.append(
            DayCoverage(
                day=day,
                games=int(scheduled[day]),
                frozen_rows=int(snapshot_rows.get(day, 0)),
                settled_rows=int(settled_rows.get(day, 0)),
                days_since=since,
            )
        )
    return result


def scheduled_days(games: pd.DataFrame, *, season: int) -> dict[str, int]:
    """Game date -> game count, for one regular season."""
    if games.empty:
        return {}
    frame = games[games["season"].astype(int) == int(season)]
    if "game_date" not in frame.columns:
        return {}
    counts = frame["game_date"].astype(str).str[:10].value_counts()
    return {str(day): int(n) for day, n in counts.items() if len(str(day)) == 10}


def snapshot_row_counts(directory: Path) -> dict[str, int]:
    """Game date -> frozen rows, from the snapshot archive."""
    counts: dict[str, int] = {}
    if not directory.is_dir():
        return counts
    for path in sorted(directory.glob("*.csv")):
        try:
            counts[path.stem] = max(len(pd.read_csv(path)), 0)
        except (pd.errors.EmptyDataError, OSError):
            counts[path.stem] = 0
    return counts


def settled_row_counts(ledger: pd.DataFrame) -> dict[str, int]:
    if ledger.empty or "snapshot_date" not in ledger.columns:
        return {}
    counts = ledger["snapshot_date"].astype(str).value_counts()
    return {str(day): int(n) for day, n in counts.items()}


def render(result: CoverageResult, *, season: int) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Is the {season} forward ledger intact?")
    add("")
    add(
        "**The forward ledger is the only evidence this lab can still gather.** "
        "The bought population is complete and the closing-line series is "
        "fixed. What is left is 272 games a season across 57 game days, and it "
        "**cannot be back-dated** — a game day that was never frozen is sample "
        "that does not exist and cannot be made to."
    )
    add("")
    if not result.days:
        add(
            "**No scheduled game day has passed yet.** That is an absence, not "
            "a fault, and nothing is owed."
        )
        return "\n".join(lines) + "\n"

    if result.is_intact:
        add(
            f"**Intact.** All {len(result.days)} game day(s) played so far were "
            "frozen and settled."
        )
    else:
        parts = []
        if result.lost:
            parts.append(f"**{len(result.lost)} game day(s) LOST**")
        if result.thin:
            parts.append(f"{len(result.thin)} thin")
        if result.unsettled:
            parts.append(f"{len(result.unsettled)} unsettled past the grace window")
        add("**Not intact** — " + ", ".join(parts) + ".")
    add("")
    add("| Game day | Games | Frozen rows | Settled rows | Days since | State |")
    add("|:---|---:|---:|---:|---:|:---|")
    for day in result.days:
        add(
            f"| {day.day} | {day.games} | {day.frozen_rows:,} | "
            f"{day.settled_rows:,} | {day.days_since} | {day.state} |"
        )
    add("")
    if result.lost:
        add(
            "**A LOST day is the one failure this organ cannot survive.** It "
            "means no opinion was frozen before those kickoffs and none can be "
            "now. The games are played; the evidence is not recoverable. Find "
            "out why the run did not produce a snapshot before the next game "
            "day, because whatever caused it will still be there."
        )
        add("")
    if result.thin:
        add(
            f"**A thin day has fewer than {THIN_SNAPSHOT_ROWS} frozen rows**, "
            "which is a run that fetched almost nothing and wrote what it had "
            "rather than a real slate. It is not lost, but it is not a day's "
            "evidence either, and it will read as one in any pooled number."
        )
        add("")
    if result.unsettled:
        add(
            f"**An unsettled day past {SETTLEMENT_GRACE_DAYS} days** has frozen "
            "opinions that never became evidence. Settlement deliberately lags "
            "— nflverse revises defensive counting stats between Monday and "
            "Wednesday — but beyond the window the row will never settle."
        )
        add("")
    add(
        "Read against the **schedule**, never against what was fetched. The "
        "question is which days should have an opinion, and only the schedule "
        "knows that: a check that compares the ledger to itself reports a day "
        "that never ran as a day that had nothing to say."
    )
    return "\n".join(lines) + "\n"
