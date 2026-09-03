"""The one function that builds every join key, and the vocabulary it uses.

The NHL lab's join-vocabulary bug family reached **five members** and cost
weeks. Every one of them was two hand-built copies of a key disagreeing:

1. provider team names against league abbreviations;
2. UTC dates against league game dates — 69% of every bought price silently
   discarded, and the survivors were systematically the afternoon games;
3. `home -1.5` against `home_minus`;
4. three-way outcomes staged in the provider's vocabulary instead of this
   lab's, so every downstream join missed;
5. a CSV round-trip turning an empty player into the string `"nan"` on one
   side of a hand-built key.

So there is one `selection_key`, both sides of every join call it, and the
fixtures call it too. A key that is absent means **no modelled opinion**,
which is different from a probability of zero, and every caller treats it as
different.

## The vocabulary, fixed here so two spellings can never mean one bet

The provider's outcome names are not this lab's. A row staged in the
provider's vocabulary misses every join, silently. Worse — and this is the
NHL lab's anytime-scorer bug — **two spellings of one bet become two keys**,
the card stakes the same wager twice, publishes it as two independent best
bets at two different prices, and freezes it into the forward ledger twice.

Anytime touchdown is the football version of that trap. The provider prices
it as a yes/no market; this lab prices it as total touchdowns scored **over
0.5**, in the same vocabulary as every other prop, because it is the same bet
and it settles identically.
"""

from __future__ import annotations

from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.season import clean_text, row_game_date


# Team-market selections.
HOME = "home"
AWAY = "away"
DRAW = "draw"
OVER = "over"
UNDER = "under"
HOME_OVER = "home_over"
HOME_UNDER = "home_under"
AWAY_OVER = "away_over"
AWAY_UNDER = "away_under"

#: Anytime touchdown is total touchdowns scored over this line. One name for
#: one thing, so the two cannot disagree on the same card.
ANYTIME_TD_LINE = 0.5

#: Every selection string this lab recognises. A staged row carrying anything
#: else is unparseable and is counted as such — never guessed at.
KNOWN_SELECTIONS: frozenset[str] = frozenset(
    {HOME, AWAY, DRAW, OVER, UNDER, HOME_OVER, HOME_UNDER, AWAY_OVER, AWAY_UNDER}
)


def selection_key(
    row: object,
    *,
    market: str,
    selection: str,
    line: float | None,
    league: League,
) -> tuple:
    """The one key both sides of the price/probability join build.

    `player` goes through `clean_text` before anything else, because a CSV
    round-trip turns an empty field into NaN — which is truthy, so
    `str(x or "")` yields the literal string `"nan"` and quietly matches
    nothing forever.

    The **league game date** is a component because a staged file spans days:
    the bulk endpoint returns every upcoming game, and two fixtures between
    the same clubs are two different bets whose kickoffs the guard must judge
    separately. It is the *league* date, not the UTC one — a Sunday-night
    kickoff is Monday in UTC, and joining on that discards it.
    """
    return (
        str(market),
        clean_text(getattr(row, "player", "")).casefold(),
        str(getattr(row, "home_team", "")),
        str(getattr(row, "away_team", "")),
        str(selection),
        None if line is None else float(line),
        row_game_date(row, league),
    )


def normalise_line(value: object) -> float | None:
    """A line as a float, or None when there is not one.

    None rather than 0.0. A moneyline has no line, and a line of zero is a
    pick'em — two different things that a falsy check would merge.
    """
    if value is None:
        return None
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def team_selection(outcome_name: str, home_team: str, away_team: str) -> str | None:
    """`home`, `away`, `draw`, or None when the outcome names neither club.

    None rather than a guess. The provider names the sides after the clubs,
    and a row staged under the club's name misses every downstream join — the
    fourth member of the bug family, and the one that was hardest to see
    because nothing errored.
    """
    name = clean_text(outcome_name)
    if not name:
        return None
    if name == clean_text(home_team):
        return HOME
    if name == clean_text(away_team):
        return AWAY
    if name.casefold() in {"draw", "tie"}:
        return DRAW
    return None


def over_under_selection(outcome_name: str) -> str | None:
    name = clean_text(outcome_name).casefold()
    if name in {"over", "o"}:
        return OVER
    if name in {"under", "u"}:
        return UNDER
    return None


def team_total_selection(
    outcome_name: str, description: str, home_team: str, away_team: str
) -> str | None:
    """`home_over` … `away_under`.

    Both clubs arrive under one provider key, the side in the outcome's
    description and Over/Under in its name. Staged in this lab's vocabulary,
    for the same reason the three-way is.
    """
    side = over_under_selection(outcome_name)
    if side is None:
        return None
    club = clean_text(description)
    if club == clean_text(home_team):
        return f"home_{side}"
    if club == clean_text(away_team):
        return f"away_{side}"
    return None


def yes_no_selection(outcome_name: str) -> str | None:
    """`over` for Yes, `under` for No — never `yes`, never `no`.

    This is the NHL lab's anytime-scorer bug, ported as a rule rather than
    rediscovered. Both spellings price identically and settle identically, but
    `selection_key` carries the selection string, so two spellings are two
    keys. The card staked one wager twice, published it as two independent
    best bets at two different prices, and froze it into the ledger twice.
    """
    name = clean_text(outcome_name).casefold()
    if name == "yes":
        return OVER
    if name == "no":
        return UNDER
    return None
