"""Which schedule game a provider fixture is, by identity and never by spelling.

The provider names a college game `Alabama Crimson Tide` at `Georgia Bulldogs`;
the schedule feed says `Alabama` and `Georgia` and carries team ids. Every
join between the two — deciding whether a fixture is priceable, and settling
it after — goes through this module, so there is one answer to "which game is
this" rather than two that drift (`docs/build_order.md`, "Settlement joins on
identity, never on name strings").

## Home and away can disagree, and that is not an error

At a neutral site the provider and the feed may each call a different team
the home side. The provider's orientation is the one the PRICE uses, so every
opinion and every settled row is read from the provider's side. The match
records whether the two disagree (`flipped`) and settlement reads the feed's
scores through it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from ncaaf_betting_lab.coverage import KICKOFF_UNKNOWN, UNRATED_OPPONENT
from ncaaf_betting_lab.data.cfbfastr import Game
from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.providers.team_names import FCS, UNRESOLVED, Membership
from ncaaf_betting_lab.reports.card_pricing import UNRESOLVED as UNRESOLVED_BUCKET
from ncaaf_betting_lab.reports.card_pricing import Fixture
from ncaaf_betting_lab.season import game_date


@dataclass(frozen=True)
class Match:
    game: Game
    #: True when the feed's home team is the provider's AWAY team.
    flipped: bool

    def provider_scores(self) -> tuple[float, float] | None:
        """`(provider home score, provider away score)`, or None before a result."""
        if not self.game.has_result:
            return None
        home, away = float(self.game.home_points), float(self.game.away_points)
        return (away, home) if self.flipped else (home, away)


class ScheduleIndex:
    """One season's games, indexed by the pair of team ids and the league date."""

    def __init__(self, games: Iterable[Game], league: League) -> None:
        self.league = league
        self._by_pair: dict[frozenset[str], list[tuple[str, Game]]] = {}
        for game in games:
            if not game.home_id or not game.away_id:
                continue
            day = game_date(game.start_date, league)
            self._by_pair.setdefault(
                frozenset({game.home_id, game.away_id}), []
            ).append((day, game))

    def find(self, home_id: str, away_id: str, day: str) -> Match | None:
        """The game these two teams play on `day`, or within a day of it.

        A day either side, because a placeholder kickoff can sit across
        midnight from the real one. Never wider: two meetings of one pair in a
        season (a rematch in a conference title game) are weeks apart, and a
        wider window would settle one against the other — the cross-season
        defect the sibling NFL lab shipped, at a smaller scale.
        """
        candidates = self._by_pair.get(frozenset({home_id, away_id}), [])
        if not candidates or not day:
            return None
        try:
            target = date.fromisoformat(day[:10])
        except ValueError:
            return None
        for offset in (0, -1, 1):
            wanted = (target + timedelta(days=offset)).isoformat()
            for game_day, game in candidates:
                if game_day == wanted:
                    return Match(game=game, flipped=game.home_id != home_id)
        return None


def describe(
    home: str,
    away: str,
    day: str,
    *,
    membership: Membership,
    schedule: ScheduleIndex,
) -> tuple[Fixture, Match | None]:
    """Whether a provider fixture may be priced, and the game it is."""
    home_id, away_id = membership.resolve(home), membership.resolve(away)
    label = f"{away} @ {home}"
    unresolved = [n for n, r in ((home, home_id), (away, away_id)) if r == UNRESOLVED]
    if unresolved:
        return Fixture(
            UNRESOLVED_BUCKET,
            f"{' and '.join(unresolved)} matched no known team; a fixture "
            "holding an unmatched name is never priced",
        ), None
    unrated = [n for n, r in ((home, home_id), (away, away_id)) if r == FCS]
    if unrated:
        return Fixture(
            UNRATED_OPPONENT,
            f"{' and '.join(unrated)} is not an FBS team this season, and the "
            "shapes were measured on FBS-vs-FBS games only",
        ), None
    match = schedule.find(home_id, away_id, day)
    if match is None:
        return Fixture(
            UNRESOLVED_BUCKET,
            f"{label} on {day} is not on this season's schedule, so it could "
            "never be settled",
        ), None
    if match.game.start_time_tbd:
        return Fixture(
            KICKOFF_UNKNOWN,
            f"{label}: the schedule still flags the kickoff as to be "
            "announced, so it cannot be guarded or dated to a ledger day",
        ), match
    return Fixture(), match
