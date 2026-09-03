"""Schedules, results and FBS membership, from cfbfastR's committed data.

**There is no nflverse for college football**, and choosing what replaces it was
the largest open question in this lab. The answer is `sportsdataverse/
cfbfastR-data`, which commits CSV and parquet directly to a public repository —
the same shape as an nflverse release asset, and with the same properties that
made it the right choice there:

* **free**, with no API key and no rate limit, because it is a file download
  rather than an API call;
* **re-fetchable**, so nothing has to be hoarded;
* and **auditable**, because the file a number came from can be fetched again
  and compared.

The alternative was collegefootballdata.com's REST API, which is the same
project's own service. It is good, and it is capped at **1,000 calls per
calendar month on the free tier** with suspension for overage. That is
survivable for bulk endpoints and it is an unnecessary constraint to accept for
data that is also published as files.

## What one file gives us

`schedules/csv/cfb_schedules_{season}.csv` — 888 rows for 2026 — carries the
whole settlement surface for team markets:

    home_points / away_points   final score: moneyline, spread, total, team total
    completed                   whether the result is final
    start_date                  kickoff, for the league-date rule and the guard
    week / season_type          regular season, conference championship, bowl
    neutral_site                no home advantage to apply
    home_division/away_division FBS or FCS, per team, per game

That last pair is the one that matters most, and it is why this source was
chosen over any that omits it. **The FBS/FCS problem is solved by a column**
rather than by a second fetch and a name match: 127 of 888 games in 2026 (14%
of the slate) put an FBS team against a non-FBS opponent, and every one of them
is a fixture this lab must decline to price rather than silently rate as
average.

## What it does not give us, stated rather than discovered

**No line scores.** There is no half-time column here, so the `*_h1` markets in
`markets.py` cannot be settled from this file. They stay unpriceable until a
half-time source exists, and a market that cannot be settled is never priced —
the NFL lab's rule, and the reason its half markets sat in `no_opinion` for
months rather than accumulating unsettleable rows in the ledger.

**`home_pregame_elo` is somebody else's model.** It is present, it is tempting,
and it is not used. A rating this lab did not fit is a rating it cannot explain,
walk forward, or hold a verdict on.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

from ncaaf_betting_lab.leagues import League

#: Where the files live. Pinned to `main` deliberately: this repository commits
#: data rather than tagging releases, so there is no version to pin to, and a
#: fetch records what it saw rather than pretending to be reproducible.
BASE_URL = (
    "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main"
)
SCHEDULE_URL = BASE_URL + "/schedules/csv/cfb_schedules_{season}.csv"

SCHEDULE_FILENAME = "cfb_schedules_{season}.csv"

#: The division string cfbfastR writes for top-tier college football.
FBS = "fbs"

#: Columns a schedule must carry to be usable. A file missing one of these is
#: not a smaller schedule, it is a different file — and the failure of a rename
#: is exactly the failure of assuming a column is there.
REQUIRED_COLUMNS = frozenset({
    "game_id", "season", "week", "season_type", "start_date", "completed",
    "neutral_site", "home_team", "away_team", "home_points", "away_points",
    "home_division", "away_division",
})


@dataclass(frozen=True)
class Game:
    """One scheduled or finished college football game."""

    game_id: str
    season: int
    week: int
    season_type: str
    start_date: str
    completed: bool
    neutral_site: bool
    home_team: str
    away_team: str
    home_division: str
    away_division: str
    home_points: float | None
    away_points: float | None

    @property
    def involves_fbs(self) -> bool:
        """Either side in FBS.

        The population this lab could ever care about, and NOT the same thing
        as the file's contents. A completed season's file carries every
        division: 2024 holds 3,801 games of which only 920 involve an FBS team,
        the rest being Division III (2,446), Division II (1,804) and FCS-only
        fixtures. The current season's file holds FBS-involving games only —
        888 for 2026, all of them.

        So the two files are different populations wearing the same schema, and
        a fit that loaded a season and trained on it would train on Division
        III for the historical seasons and not for the current one. Filter
        before counting anything, or the counts are not comparable.
        """
        return FBS in (self.home_division, self.away_division)

    @property
    def is_fbs_only(self) -> bool:
        """Both sides in FBS.

        The rateable population. 761 of 888 games in 2026; the other 127 put an
        FBS team against an opponent this lab has no rating for and must
        decline rather than price.
        """
        return self.home_division == FBS and self.away_division == FBS

    @property
    def has_result(self) -> bool:
        return (
            bool(self.completed)
            and self.home_points is not None
            and self.away_points is not None
        )

    @property
    def margin(self) -> float | None:
        if not self.has_result:
            return None
        return float(self.home_points) - float(self.away_points)

    @property
    def total(self) -> float | None:
        if not self.has_result:
            return None
        return float(self.home_points) + float(self.away_points)


def schedule_path(league: League, raw_dir: Path, *, season: int) -> Path:
    return (
        Path(raw_dir)
        / league.data_dir_segment
        / "schedules"
        / SCHEDULE_FILENAME.format(season=season)
    )


def fetch_schedule(
    league: League, raw_dir: Path, *, season: int, timeout: int = 60
) -> Path:
    """Download one season's schedule. Spends no provider credits.

    Written to a temporary path and moved only on success. A failed download
    that leaves a truncated file behind is indistinguishable from a season with
    fewer games, and the reader has no way to tell.
    """
    target = schedule_path(league, raw_dir, season=season)
    target.parent.mkdir(parents=True, exist_ok=True)
    url = SCHEDULE_URL.format(season=season)
    staging = target.with_suffix(".partial")
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed host
        staging.write_bytes(response.read())
    if staging.stat().st_size == 0:
        staging.unlink(missing_ok=True)
        raise OSError(f"{url} returned an empty file; nothing was written.")
    staging.replace(target)
    return target


def _to_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text.upper() in {"NA", "NAN", "NULL"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_bool(value: object) -> bool:
    return str(value or "").strip().upper() in {"TRUE", "1", "T", "YES"}


def load_schedule(league: League, raw_dir: Path, *, season: int) -> list[Game]:
    """One season's games.

    Raises when the file is absent or malformed rather than returning an empty
    list. A slate where nothing loads is indistinguishable from a slate with no
    games, and this lab's sibling shipped that confusion twice.
    """
    path = schedule_path(league, raw_dir, season=season)
    if not path.is_file():
        raise FileNotFoundError(
            f"No {season} schedule at {path}. Fetch it with "
            "`scripts/fetch_ncaaf_data.py --seasons {season}` before anything "
            "reads a fixture: an empty schedule and a season with no games "
            "look identical downstream."
        )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"{path} is missing {sorted(missing)}. A file without these is "
                "not a smaller schedule, it is a different file."
            )
        games = []
        for row in reader:
            games.append(
                Game(
                    game_id=str(row["game_id"]).strip(),
                    season=int(float(row["season"])),
                    week=int(float(row["week"])),
                    season_type=str(row["season_type"]).strip(),
                    start_date=str(row["start_date"]).strip(),
                    completed=_to_bool(row["completed"]),
                    neutral_site=_to_bool(row["neutral_site"]),
                    home_team=str(row["home_team"]).strip(),
                    away_team=str(row["away_team"]).strip(),
                    home_division=str(row["home_division"]).strip().lower(),
                    away_division=str(row["away_division"]).strip().lower(),
                    home_points=_to_float(row["home_points"]),
                    away_points=_to_float(row["away_points"]),
                )
            )
    return games


def fbs_teams(games: list[Game]) -> tuple[str, ...]:
    """Every FBS team named in a season's schedule.

    Derived from the games rather than from a separate membership file, so the
    club set and the fixtures cannot disagree — and it is season-keyed by
    construction, which matters because FBS membership moved by two teams this
    year.
    """
    teams: set[str] = set()
    for game in games:
        if game.home_division == FBS:
            teams.add(game.home_team)
        if game.away_division == FBS:
            teams.add(game.away_team)
    return tuple(sorted(teams))


def fbs_involving_games(games: list[Game]) -> list[Game]:
    """Games with at least one FBS team.

    The first filter anything should apply, because a completed season's file
    carries every division and the current season's does not. Without it,
    "games this season" means 3,801 for 2024 and 888 for 2026 — two different
    questions with one name.
    """
    return [g for g in games if g.involves_fbs]


def rateable_games(games: list[Game]) -> list[Game]:
    """FBS-vs-FBS games only — the population a rating can be fitted on.

    Whether FBS-vs-FCS games should also inform the fit is an open question with
    no good default: include them and every FBS offence rating is inflated by a
    63-3 win over an overmatched opponent; exclude them and every team that
    opened against one carries a game less of history, so weeks 2-3 ratings sit
    near league average for exactly the teams that scheduled a cupcake.

    That decision goes through the verdicts door with a measurement behind it.
    Until one exists, this returns the conservative set and the caller is told
    how many games it dropped.
    """
    return [g for g in games if g.is_fbs_only]
