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
import re
import unicodedata
from collections.abc import Iterable, Mapping
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
        found = self.aliases.get(text.casefold())
        if found is None:
            found = self.aliases.get(fold(text), UNRESOLVED)
        return found

    def is_fbs(self, resolved: str) -> bool:
        return resolved in self.teams

    def __len__(self) -> int:
        return len(self.teams)


_PUNCTUATION = re.compile(r"[.'’`]")
_SPACES = re.compile(r"\s+")


def fold(name: object) -> str:
    """A name reduced to what two spellings of one team share.

    Accents, apostrophes, full stops, case and runs of whitespace go, and a
    hyphen reads as a space; nothing else does. `San José State` and `San Jose State`, `Hawai'i` and `Hawaii`,
    `St. Thomas` and `St Thomas` fold together. `Miami` and `Miami (OH)` do
    NOT — the parenthesis is identity, and folding it away would put two
    schools behind one key.
    """
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _PUNCTUATION.sub("", text).replace("-", " ")
    return _SPACES.sub(" ", text).strip().casefold()


#: Fields of the teams file that are a NAME for the team. The abbreviation is
#: deliberately absent: across all college teams it is not unique (`OSU` is
#: Ohio State and Ohio State Newark), and the provider never sends one.
_NAME_FIELDS = ("school", "alt_name1", "alt_name2", "alt_name3")


def _aliases_for(names: Iterable[str], mascot: str) -> set[str]:
    """Every folded spelling a provider might send for one team.

    The provider names a college team as school plus mascot — `Alabama Crimson
    Tide` — where the schedule feed says `Alabama`. Both are generated, along
    with `State`/`St` variants, because the provider and the feed disagree on
    that abbreviation for a dozen schools and a mismatch reads as an unknown
    team rather than as a spelling.
    """
    out: set[str] = set()
    for name in names:
        base = fold(name)
        if not base:
            continue
        bases = {base}
        if base.endswith(" state"):
            bases.add(base[: -len(" state")] + " st")
        if base.endswith(" st"):
            bases.add(base + "ate")
        for variant in bases:
            out.add(variant)
            if mascot:
                out.add(f"{variant} {fold(mascot)}")
    return out


@dataclass
class MembershipBuild:
    """What `build_membership` wrote, and what it refused to write."""

    path: Path
    fbs_teams: int
    other_teams: int
    #: Aliases that would have named two different teams, dropped from BOTH.
    #: A collision resolved by whichever row came first is a team silently
    #: priced as another one; resolved by neither it is a name the card
    #: reports as unmatched, which a human can fix in one line.
    collisions: tuple[str, ...]


def build_membership(
    league: League,
    raw_dir: Path,
    *,
    season: int,
    fbs: Mapping[str, str],
    teams: Iterable[Mapping[str, str]],
    extra_aliases: Mapping[str, str] | None = None,
) -> MembershipBuild:
    """Write this season's membership cache from the schedule and the names file.

    `fbs` is `{team id: schedule name}` for every team the season's own
    schedule places in FBS — the only source of classification. `teams` is the
    names file, which supplies mascots and alternate names and classifies
    nothing: a team it lists that this season's schedule does not place in FBS
    is written as non-FBS, so it resolves to `FCS` and lands in the unrated
    bucket rather than being priced.

    `extra_aliases` maps a provider spelling to a team id, for the names the
    generated variants miss. It comes from a reviewed file, never a guess.
    """
    by_id = {str(row.get("team_id", "")).strip(): row for row in teams}
    targets: dict[str, set[str]] = {}

    def claim(alias: str, team_id: str) -> None:
        targets.setdefault(alias, set()).add(team_id)

    for team_id, name in fbs.items():
        row = by_id.get(team_id, {})
        names = [name] + [str(row.get(field, "")) for field in _NAME_FIELDS]
        for alias in _aliases_for(names, str(row.get("mascot", ""))):
            claim(alias, team_id)
    for team_id, row in by_id.items():
        if not team_id or team_id in fbs:
            continue
        names = [str(row.get(field, "")) for field in _NAME_FIELDS]
        for alias in _aliases_for(names, str(row.get("mascot", ""))):
            claim(alias, team_id)
    for alias, team_id in (extra_aliases or {}).items():
        folded = fold(alias)
        if folded:
            # A reviewed alias is a decision, so it replaces whatever the
            # generator thought rather than colliding with it.
            targets[folded] = {str(team_id).strip()}

    collisions = tuple(sorted(a for a, ids in targets.items() if len(ids) > 1))
    path = membership_path(league, raw_dir, season=season)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for alias, ids in sorted(targets.items()):
        if len(ids) != 1:
            continue
        (team_id,) = tuple(ids)
        if team_id in fbs:
            name, classification = fbs[team_id], "fbs"
        else:
            name = str(by_id.get(team_id, {}).get("school", "")) or team_id
            classification = "other"
        rows.append(
            {"team_id": team_id, "name": name, "classification": classification,
             "alias": alias, "abbreviation": ""}
        )
    # FBS teams with no surviving alias still need a row, or the team would
    # vanish from `Membership.teams` and every fixture it plays would read as
    # unresolved for a reason nobody could see.
    present = {row["team_id"] for row in rows}
    for team_id, name in fbs.items():
        if team_id not in present:
            rows.append({"team_id": team_id, "name": name, "classification": "fbs",
                         "alias": "", "abbreviation": ""})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["team_id", "name", "classification", "alias", "abbreviation"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return MembershipBuild(
        path=path,
        fbs_teams=len(fbs),
        other_teams=len({r["team_id"] for r in rows} - set(fbs)),
        collisions=collisions,
    )


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
