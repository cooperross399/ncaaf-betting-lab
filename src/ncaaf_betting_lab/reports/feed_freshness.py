"""Is every feed the card depends on current enough to hold an opinion?

A stale feed does not fail. It answers, and it answers with last week's truth —
a roster that has not seen a trade, a depth chart that still lists the injured
starter, an injury report from before Friday's practice. The card prices it,
freezes it into the ledger, and the ledger is **never revised**. So a stale feed
does not cost a run; it writes a wrong opinion into the one record this lab
cannot correct.

Graded on **content, not file age**. A file rewritten this morning with last
week's rows is stale and its mtime says fresh — that is the ordinary failure
when a fetch succeeds against an upstream that has not published yet. So each
feed declares what it must *contain* to be current: the season it should cover,
the week it should reach, and how many clubs it should name.

The 2026 season has not started, so several of these are legitimately empty
before Week 1. An absence before kickoff and an absence after it are different
facts, and the report says which one it is looking at.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

#: All 32 clubs, or the feed is missing teams rather than merely being thin.
#: Read from the league registry by the caller — never hardcoded here.
OK = "current"
STALE = "STALE"
MISSING = "MISSING"
NOT_YET = "not due yet"


@dataclass(frozen=True)
class FeedState:
    """One cached feed, and whether it can answer today's question."""

    name: str
    #: What the card would get wrong if this were stale. Stated per feed
    #: because "refresh the feeds" is not an instruction anyone can act on.
    consequence: str
    present: bool
    covers_season: bool
    reaches_week: int | None
    expected_week: int | None
    clubs: int
    expected_clubs: int
    due: bool = True

    @property
    def state(self) -> str:
        if not self.due:
            return NOT_YET
        if not self.present:
            return MISSING
        if not self.covers_season:
            return STALE
        if self.expected_clubs and self.clubs < self.expected_clubs:
            return STALE
        if (
            self.expected_week is not None
            and self.reaches_week is not None
            and self.reaches_week < self.expected_week
        ):
            return STALE
        return OK

    @property
    def blocks_an_opinion(self) -> bool:
        return self.state in {STALE, MISSING}


@dataclass
class FreshnessResult:
    as_of: str = ""
    week: int | None = None
    feeds: list[FeedState] = field(default_factory=list)

    @property
    def blocking(self) -> list[FeedState]:
        return [f for f in self.feeds if f.blocks_an_opinion]

    @property
    def is_ready(self) -> bool:
        return bool(self.feeds) and not self.blocking


def expected_week(day_to_week: dict[str, int], as_of: date) -> int | None:
    """The latest SEASON WEEK whose games have kicked off.

    A week number, not a count of game days — the first version returned the
    number of days played, so a full season asked the feeds to reach "week 57"
    and every one of them read as stale. Counting the wrong unit is the kind of
    fault that produces a plausible number rather than an error.

    From the schedule rather than from a calendar rule: the NFL week does not
    start on a fixed weekday. Week 1 2026 opens on a Wednesday because
    Thursday's game is in Australia, and a rule that assumed otherwise would
    ask for a feed a day early every time a slate moved.
    """
    played = [w for day, w in day_to_week.items() if day <= as_of.isoformat()]
    return max(played) if played else None


def render(result: FreshnessResult) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Can the card hold an opinion today?")
    add("")
    add(
        "A stale feed does not fail — it answers, with last week's truth. The "
        "card prices that, freezes it into the forward ledger, and **the ledger "
        "is never revised**. A stale feed does not cost a run; it writes a "
        "wrong opinion into the one record this lab cannot correct."
    )
    add("")
    add(
        "Graded on **content, not file age**. A file rewritten this morning "
        "with last week's rows is stale and its timestamp says fresh, which is "
        "the ordinary failure when a fetch succeeds against an upstream that "
        "has not published yet."
    )
    add("")
    if not result.feeds:
        add(
            "**No feed was checked.** That is an absence, not a pass, and "
            "nothing downstream of it should be believed."
        )
        return "\n".join(lines) + "\n"

    if result.is_ready:
        add(f"**Ready.** All {len(result.feeds)} feed(s) are current.")
    else:
        add(
            f"**Not ready** — {len(result.blocking)} of {len(result.feeds)} "
            "feed(s) cannot answer today's question."
        )
    add("")
    add("| Feed | State | Reaches | Expected | Clubs | What a stale copy costs |")
    add("|:---|:---|---:|---:|---:|:---|")
    for feed in result.feeds:
        add(
            f"| `{feed.name}` | {feed.state} | "
            f"{feed.reaches_week if feed.reaches_week is not None else '—'} | "
            f"{feed.expected_week if feed.expected_week is not None else '—'} | "
            f"{feed.clubs}/{feed.expected_clubs} | {feed.consequence} |"
        )
    add("")
    if result.blocking:
        add(
            "**Each blocking feed names its own consequence above**, because "
            "'refresh the feeds' is not an instruction anyone can act on at "
            "07:00 on a game day. Fetch with "
            "`scripts/fetch_football_data.py --seasons <season>`."
        )
        add("")
    add(
        "A feed marked *not due yet* is one whose season has not started. "
        "**An absence before kickoff and an absence after it are different "
        "facts**, and reading the first as the second would block every run in "
        "the preseason."
    )
    return "\n".join(lines) + "\n"
