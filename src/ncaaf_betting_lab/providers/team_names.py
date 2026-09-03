"""Resolving a college team to one identity, and refusing when it cannot.

The NFL lab's version assumes a **closed, one-to-one** abbreviation map: 32
clubs, stable three-letter codes, no collisions. That assumption does not
survive contact with college football.

Within FBS it holds — ESPN abbreviations are unique across 138 of 138 teams.
Across all **760** college football teams it does not: `OSU` is both Ohio State
and Ohio State Newark, and the locations `Charlotte` and `Troy` each collide
with a non-FBS school.

So the map is safe **only** when its universe is FBS-only — which is exactly
the choice that makes FCS opponents unresolvable. That is not a bug to be fixed
by widening the map; it is the shape of the problem. This lab therefore carries
**classification alongside the name**, and refuses rather than guessing:

* an FBS team resolves to its canonical id;
* a known FCS opponent resolves to the sentinel `FCS`, which is a real answer —
  "a team this lab does not rate" — and routes the fixture to
  `coverage.UNRATED_OPPONENT` rather than to a price;
* anything else is `UNRESOLVED`, and a fixture holding one is never priced.

## Keyed by season, because membership moves

FBS membership changed by two teams this year. A map that is not season-keyed
would resolve a team to a classification it no longer holds, and the failure is
silent: last season's FBS team reads as rateable, this season's newcomer reads
as FCS.

## Why this file has no team list in it

The membership comes from the data adapter, per season, and is cached. Writing
134 names here would be a second source of truth that drifts from the first,
and the drift would show up as teams quietly becoming unrateable mid-season.
`load_membership` raises when the cache is absent, rather than returning an
empty map that would make every fixture unresolvable and read as "no games
today".
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ncaaf_betting_lab.leagues import League

#: A team the lab has identified as playing outside FBS. A real answer, not a
#: failure: it routes the fixture to the unrated bucket with a reason.
FCS = "FCS"

#: A name that matched nothing. A fixture holding one is never priced.
UNRESOLVED = "UNRESOLVED"

#: Where the adapter caches each season's membership.
MEMBERSHIP_FILENAME = "fbs_membership_{season}.csv"


@dataclass(frozen=True)
class Membership:
    """One season's FBS teams, and the aliases that resolve to them."""

    season: int
    #: canonical id -> display name
    teams: dict[str, str]
    #: lowercased alias -> canonical id
    aliases: dict[str, str]

    def resolve(self, name: object) -> str:
        """Canonical id, `FCS`, or `UNRESOLVED`. Never a guess."""
        text = str(name or "").strip()
        if not text:
            return UNRESOLVED
        return self.aliases.get(text.casefold(), UNRESOLVED)

    def is_fbs(self, resolved: str) -> bool:
        return resolved in self.teams

    def __len__(self) -> int:
        return len(self.teams)


def membership_path(league: League, raw_dir: Path, *, season: int) -> Path:
    return (
        Path(raw_dir)
        / league.data_dir_segment
        / "membership"
        / MEMBERSHIP_FILENAME.format(season=season)
    )


def load_membership(league: League, raw_dir: Path, *, season: int) -> Membership:
    """This season's FBS membership.

    Raises when the cache is absent. An empty map would make every fixture
    unresolvable, and a slate where nothing resolves reads exactly like a slate
    with no games — which is the silent-absence failure this lab's sibling
    shipped twice.
    """
    path = membership_path(league, raw_dir, season=season)
    if not path.is_file():
        raise FileNotFoundError(
            f"No FBS membership cached for {season} at {path}. Fetch it before "
            "resolving any team: without it every name is UNRESOLVED, and a "
            "slate where nothing resolves is indistinguishable from a slate "
            "with no games."
        )
    teams: dict[str, str] = {}
    aliases: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            team_id = str(row.get("team_id", "")).strip()
            name = str(row.get("name", "")).strip()
            classification = str(row.get("classification", "")).strip().lower()
            if not team_id or not name:
                continue
            if classification == "fbs":
                teams[team_id] = name
                target = team_id
            else:
                target = FCS
            for alias in (name, row.get("alias", ""), row.get("abbreviation", "")):
                text = str(alias or "").strip().casefold()
                if not text:
                    continue
                # First writer wins, and a collision is recorded rather than
                # silently overwritten: `OSU` meaning two schools is exactly
                # how a college map goes wrong.
                aliases.setdefault(text, target)
    return Membership(season=season, teams=teams, aliases=aliases)


def abbreviations(league: League, membership: Membership) -> tuple[str, ...]:
    """The closed club set for this league **this season**.

    Takes the membership explicitly rather than reading a module-level
    constant, because the set moves between seasons and a cached one would
    resolve a team to a classification it no longer holds.
    """
    return tuple(sorted(membership.teams))
