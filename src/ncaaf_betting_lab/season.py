"""What day a game belongs to, and how CSV-borne text is read.

The provider timestamps a game by kickoff, in UTC. The league timestamps it by
the day it is played. For a Saturday-night kickoff on the west coast those are
different days — a 19:30 Pacific kickoff is 02:30 UTC the following morning —
and joining prices to results on the raw UTC date silently drops them.

The NHL lab measured what that costs when it happens: **69% of every price
bought was discarded**, and what survived was not a random sample — it was the
afternoon games. This module exists so the rule lives in one place, ported
before a single price is fetched rather than after a season of them is lost.
No provider fetch has ever run here, so the rule is still ahead of the cost.

The league's calendar timezone comes from the registry, never from a literal
here.

## What was ported, and what was deliberately left behind

Ported from `../football-betting-lab`'s `season.py` under the port-don't-import
rule in `CLAUDE.md` — deliberately, visibly, in a commit, because the five labs
never import from each other.

Three functions came across: `game_date`, `clean_text` and `row_game_date`.
They are calendar and text handling, they carry no NFL fact, and
`selection.py` cannot be imported without the last two.

**Four did not, and the reason is not tidiness.** `expected_clubs`,
`schedule_path`, `known_regular_season_games` and `schedule_cache_is_complete`
read nflverse feeds, and this lab's settlement source is cfbfastR's committed
CSV. `data/cfbfastr.py` already owns schedule loading here, in cfbfastR's own
column vocabulary — `start_date`, `home_division`, `away_division` — none of
which nflverse has. Porting the nflverse half would have produced a second
calendar for one slate, which is the exact defect the NFL module's own
`schedule_path` docstring was written about after that lab grew it twice.

One more difference worth stating rather than leaving to be discovered:
`row_game_date` reads `commence_time` and then `date`, which are **The Odds
API's** field names, not cfbfastR's. It is for provider price rows. A cfbfastR
schedule row carries `start_date` and goes through `data/cfbfastr.py`, and the
two must not be crossed — a price row and a schedule row are different files
wearing different schemas, and a function that guessed between them would be a
third calendar.
"""

from __future__ import annotations

from datetime import datetime

from ncaaf_betting_lab.leagues import League


def game_date(commence_time: object, league: League) -> str:
    """The league game date for a provider timestamp, as `YYYY-MM-DD`.

    An unparseable value falls back to its leading ten characters, which is
    the best available guess and is never silently better than the input.
    """
    text = str(commence_time or "").strip()
    if not text:
        return ""
    candidate = text.replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError:
        return text[:10]
    if moment.tzinfo is None:
        # No timezone means no conversion is possible, and inventing one would
        # move every night game by a day.
        return text[:10]
    return moment.astimezone(league.timezone).date().isoformat()


def clean_text(value: object) -> str:
    """A CSV-safe string: NaN, None and whitespace all read as empty.

    `str(x or "")` looks like it does this and does not — float NaN is truthy,
    so an empty CSV cell round-trips to the literal string `"nan"`, which then
    matches nothing, resolves nothing, and renders as a player called nan.
    Three copies of that pattern shipped in the NHL lab before its equivalent
    of this function existed, and it was the fifth member of that repository's
    join-vocabulary bug family.
    """
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN without numpy
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def row_game_date(row: object, league: League) -> str:
    """The league game date for a price row: commence time, else its date.

    The fallback exists for hand-built frames; real staged rows always carry a
    commence time. `or` cannot express this, because a NaN commence time is
    truthy and `game_date(nan)` is the string "nan" — which made two fixtures
    between the same clubs on different days share one key.
    """
    commence = clean_text(getattr(row, "commence_time", ""))
    return game_date(commence or clean_text(getattr(row, "date", "")), league)
