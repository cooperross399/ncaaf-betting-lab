"""Who took the snaps at quarterback, game by game, from free play-level data.

**There is no confirmed-starter feed for college football.** The NFL has
inactives ninety minutes before kickoff; college has nothing league-wide. So
this module answers the closest question that free data can answer before a
game: *did a different quarterback take most of the dropbacks last time out?*

The source is cfbfastR's `player_stats/csv/player_stats_{season}.csv`, one row
per play with the passer, receiver, rusher and defender credited by id. It is a
file download like the schedule — no key, no rate limit — and the current
season's file is updated as games are played (measured 2026-10-09: 2026 carries
weeks 1-5, 700 games, 87,546 plays).

## Definitions, fixed in `docs/preregistered_nightly_form.md`

* A **dropback** is a play carrying a completion, an incompletion, an
  interception thrown or a sack taken. It is credited to that player and to the
  row's `team`.
* A game's **starter** for a team is the player with the most dropbacks.
* A team's **incumbent** before a game is the player who started the most of
  its earlier games this season, ties to the more recent.
* **`qb_changed`** is True when the team has two or more earlier games this
  season and its most recent one was started by someone other than the
  incumbent. None when the team has fewer than two, or no play data.

The flag reads finished games only, so it is knowable before kickoff. It does
not say who will start; nothing free does.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import BASE_URL
from ncaaf_betting_lab.leagues import League

PLAYER_STATS_URL = BASE_URL + "/player_stats/csv/player_stats_{season}.csv"
PLAYER_STATS_FILENAME = "player_stats_{season}.csv"

#: Each column names the player credited with one kind of dropback.
DROPBACK_COLUMNS = (
    ("completion_player_id", "completion_player"),
    ("incompletion_player_id", "incompletion_player"),
    ("interception_thrown_player_id", "interception_thrown_player"),
    ("sack_taken_player_id", "sack_taken_player"),
)

#: Earlier games this season a team needs before an incumbent means anything.
MINIMUM_EARLIER_GAMES = 2


def player_stats_path(league: League, raw_dir: Path, *, season: int) -> Path:
    return (
        Path(raw_dir) / league.data_dir_segment / "player_stats"
        / PLAYER_STATS_FILENAME.format(season=season)
    )


def fetch_player_stats(
    league: League, raw_dir: Path, *, season: int, timeout: int = 180
) -> Path:
    """Download one season's play-level player file. Spends no credits.

    Written to a temporary path and moved only on success, for the reason
    `cfbfastr.fetch_schedule` gives.
    """
    target = player_stats_path(league, raw_dir, season=season)
    target.parent.mkdir(parents=True, exist_ok=True)
    url = PLAYER_STATS_URL.format(season=season)
    staging = target.with_suffix(".partial")
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed host
        staging.write_bytes(response.read())
    if staging.stat().st_size == 0:
        staging.unlink(missing_ok=True)
        raise OSError(f"{url} returned an empty file; nothing was written.")
    staging.replace(target)
    return target


def game_starters(plays: pd.DataFrame) -> pd.DataFrame:
    """One row per (game, team): the starter and his dropbacks.

    `plays` needs `game_id`, `team` and the `DROPBACK_COLUMNS`. A team-game
    with no dropback at all (a feed gap, or a game played entirely on the
    ground) has no row, which reads downstream as no data rather than as a
    change.
    """
    credited = []
    for id_column, name_column in DROPBACK_COLUMNS:
        if id_column not in plays.columns:
            raise KeyError(f"player stats carry no `{id_column}` column")
        part = plays[["game_id", "team", id_column, name_column]].rename(
            columns={id_column: "player_id", name_column: "player"}
        )
        credited.append(part)
    dropbacks = pd.concat(credited, ignore_index=True)
    ids = pd.to_numeric(dropbacks["player_id"], errors="coerce")
    dropbacks = dropbacks.assign(player_id=ids).dropna(subset=["player_id"])
    if dropbacks.empty:
        return pd.DataFrame(columns=["game_id", "team", "player_id", "player", "dropbacks"])
    dropbacks["player_id"] = dropbacks["player_id"].astype("int64").astype(str)
    dropbacks["game_id"] = (
        pd.to_numeric(dropbacks["game_id"], errors="coerce").astype("Int64").astype(str)
    )
    counts = (
        dropbacks.groupby(["game_id", "team", "player_id"])
        .agg(player=("player", "first"), dropbacks=("player", "size"))
        .reset_index()
        .sort_values(["game_id", "team", "dropbacks", "player_id"], ascending=[True, True, False, True])
    )
    return counts.drop_duplicates(["game_id", "team"]).reset_index(drop=True)


def load_starters(league: League, raw_dir: Path, *, season: int) -> pd.DataFrame:
    """`game_starters` for one season's file. Raises when it is absent."""
    path = player_stats_path(league, raw_dir, season=season)
    if not path.is_file():
        raise FileNotFoundError(f"No player stats at {path}.")
    wanted = {"game_id", "team"} | {c for pair in DROPBACK_COLUMNS for c in pair}
    plays = pd.read_csv(path, usecols=lambda c: c in wanted, low_memory=False)
    return game_starters(plays)


@dataclass(frozen=True)
class StarterState:
    """What a team's quarterback history says before its next game."""

    last_starter: str | None
    incumbent: str | None
    earlier_games: int

    @property
    def qb_changed(self) -> bool | None:
        if self.earlier_games < MINIMUM_EARLIER_GAMES or self.last_starter is None:
            return None
        return self.last_starter != self.incumbent


def state_before(history: list[str]) -> StarterState:
    """From a team's starters this season, oldest first, before its next game.

    Entries are player names (or ids); an empty string is a game with no play
    data and breaks the chain: the flag becomes None rather than guessing.
    """
    if not history:
        return StarterState(None, None, 0)
    if any(not starter for starter in history):
        return StarterState(None, None, len(history))
    counts = Counter(history)
    best = max(counts.values())
    # Ties to the more recent: scan newest first.
    incumbent = next(s for s in reversed(history) if counts[s] == best)
    return StarterState(history[-1], incumbent, len(history))
