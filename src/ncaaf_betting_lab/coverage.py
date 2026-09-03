"""Whether this lab knows enough about a fixture to hold an opinion on it.

**The single most dangerous line the NFL lab could have lent this one** is
`ratings.offence.get(team, 0.0)`. It reads a team's rating and, when the team
is unknown, returns league average — silently, with no error and no marker. In
the NFL that is nearly unreachable: 32 clubs, all rated, every week. In college
football it is the normal case for weeks 1-3 and permanent for every FCS
opponent, of which there are hundreds.

An unrated team priced as average is not a small error. Mercer is not an average
FBS team, and a model that says so will happily take the over.

So coverage is a **precondition**, checked before pricing rather than patched
after it, and a fixture that fails lands in its own named bucket in the
accounting identity. `unrated_opponent` is deliberately NOT `no_opinion`: the
first says "this lab does not know these teams", the second says "this lab
looked and had nothing to say", and forty-eight skipped games on a Week 1
Saturday must be visible as a number rather than as an absence.

## Why a games-played floor as well as presence

`PRIOR_GAMES` in the NFL model is 17 — a whole season — so a team with three
games carries about 15% of its own signal and 85% of the league's. That is
right for the NFL, where the league mean is a good prior and the spread of
true strength is narrow. It is wrong here: college talent gaps run to forty
points, so a heavily shrunk rating is not a cautious estimate of a team, it is
an assertion that the team is average, which is the same failure in slower
motion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Games a team needs before this lab will price a fixture it is in. Declared
#: here rather than discovered: with forty-point talent gaps, a rating shrunk
#: most of the way to the league mean is an assertion of averageness, not a
#: cautious estimate.
MINIMUM_RATED_GAMES = 3

#: The bucket a fixture with no known kickoff lands in.
#:
#: **401 of 888 games in 2026 (45.2%) carry `start_time_tbd`**, and the
#: placeholder timestamp beside it is not a kickoff — it is a guess the feed is
#: honest enough to flag. Weeks 1-3 have none; from week 4 onward roughly forty
#: a week are TBD.
#:
#: You cannot guard a kickoff you do not know. Everything downstream keys on
#: it: the kickoff guard that refuses a started game, the league-date rule that
#: decides which ledger day a game belongs to, and every lead-time calculation.
#: A game frozen against a placeholder may already have kicked — and college ET
#: kickoffs span 00:00 to 23:59, with 42 games at 22:00 or later, so a TBD that
#: resolves across midnight moves to a different ledger day AFTER the opinion
#: is frozen, in a ledger that never reprices.
KICKOFF_UNKNOWN = "kickoff_tbd"

#: The bucket an uncoverable fixture lands in. A distinct name, because
#: "we do not know these teams" and "we looked and had nothing to say" are
#: different facts and the accounting identity must be able to tell them apart.
UNRATED_OPPONENT = "unrated_opponent"


@dataclass(frozen=True)
class Coverage:
    """What is known about one fixture's two teams."""

    home: str
    away: str
    home_games: int | None
    away_games: int | None
    #: Whether the feed flagged this game's start time as still to be decided.
    kickoff_tbd: bool = False

    @property
    def missing(self) -> tuple[str, ...]:
        """Teams with no rating at all — typically FCS opponents."""
        out = []
        if self.home_games is None:
            out.append(self.home)
        if self.away_games is None:
            out.append(self.away)
        return tuple(out)

    @property
    def thin(self) -> tuple[str, ...]:
        """Teams rated, but on too few games to price against a 40-point gap."""
        out = []
        for team, games in ((self.home, self.home_games), (self.away, self.away_games)):
            if games is not None and games < MINIMUM_RATED_GAMES:
                out.append(team)
        return tuple(out)

    @property
    def is_priceable(self) -> bool:
        return not self.missing and not self.thin and not self.kickoff_tbd

    def reason(self) -> str:
        """Why this fixture is not priceable, in words a card can print.

        Never a bare "no opinion". A reader has to be able to tell an FCS
        opponent from a Week 2 team from a game whose kickoff nobody has set
        from a model that simply disagreed with nothing.
        """
        if self.kickoff_tbd:
            return (
                "kickoff is still to be announced, so it cannot be guarded, "
                "dated to a ledger day, or given a lead time — and a game "
                "frozen against a placeholder may already have kicked"
            )
        if self.missing:
            return (
                f"{' and '.join(self.missing)} carries no rating — most likely "
                "an FCS opponent, and pricing it would put a league-average "
                "team on the field"
            )
        if self.thin:
            names = " and ".join(
                f"{t} ({g} game{'s' if g != 1 else ''})"
                for t, g in ((self.home, self.home_games), (self.away, self.away_games))
                if t in self.thin
            )
            return (
                f"{names} below the {MINIMUM_RATED_GAMES}-game floor; a rating "
                "shrunk this far toward the league mean asserts the team is "
                "average rather than estimating it"
            )
        return ""


def check(
    home: str,
    away: str,
    games_played: dict[str, int],
    *,
    kickoff_tbd: bool = False,
) -> Coverage:
    """Coverage for one fixture. `games_played` is rated games per team."""
    return Coverage(
        home=home,
        away=away,
        home_games=games_played.get(home),
        away_games=games_played.get(away),
        kickoff_tbd=bool(kickoff_tbd),
    )


@dataclass
class CoverageTally:
    """How a slate divided, for the accounting identity."""

    priceable: int = 0
    missing_rating: int = 0
    thin_rating: int = 0
    kickoff_unknown: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            self.priceable
            + self.missing_rating
            + self.thin_rating
            + self.kickoff_unknown
        )

    def record(self, coverage: Coverage) -> None:
        if coverage.is_priceable:
            self.priceable += 1
        elif coverage.kickoff_tbd:
            # Checked before the rating buckets: a game nobody can date is not
            # a rating problem, and calling it one would hide 45% of the
            # season behind the wrong explanation.
            self.kickoff_unknown += 1
            self.reasons.append(coverage.reason())
        elif coverage.missing:
            self.missing_rating += 1
            self.reasons.append(coverage.reason())
        else:
            self.thin_rating += 1
            self.reasons.append(coverage.reason())

    def summary(self) -> str:
        if not self.total:
            return "**No fixture was checked.** That is an absence, not a pass."
        if self.priceable == self.total:
            return f"All {self.total} fixture(s) have both teams rated."
        return (
            f"**{self.priceable} of {self.total} fixture(s) priceable.** "
            f"{self.missing_rating} carry a team with no rating at all "
            f"(`{UNRATED_OPPONENT}`), {self.thin_rating} a team below the "
            f"{MINIMUM_RATED_GAMES}-game floor, {self.kickoff_unknown} have no "
            f"announced kickoff (`{KICKOFF_UNKNOWN}`). These are counted, not "
            "dropped: a skipped game must be visible as a number rather than "
            "as an absence."
        )
