"""The kickoff guard: a started game can never appear as a play.

Built in from day one, because the EPL lab retrofitted its equivalent after a
card carried a fixture that had already kicked off. Retrofitting a guard means
every card before it was unguarded, and there is no way to go back and
re-check them.

## What it does

Every selection is checked against the provider's `commence_time` for its
game. A selection is quarantined — moved out of best bets, leans and passes
into a section headed **"Already started — no longer plays"** — when either of
these is true:

1. The game's start time is at or before the moment the card is generated.
2. The game's start time **cannot be confirmed**: missing, blank, unparseable,
   or carrying no timezone.

Its stake is removed with it. A quarantined selection is not a pass, not an
avoid, and not a no-value call; it is a bet that is no longer available.

## Why ambiguity falls on the not-a-play side

The two failure directions are not symmetric.

Letting a started game through produces a card recommending a bet nobody can
place, at a price that no longer exists, and — worse — a bet whose result may
already be partly known. That is the failure that destroys trust in every
other line on the card.

Pulling a game that had not actually started costs one missed bet on a card
listing dozens, and the card says exactly why it was pulled, so the loss is
visible and recoverable in seconds.

So a missing or unparseable start time is treated as **started**. It is not
treated as "probably fine".

## What it deliberately does not do

It does not consult the schedule feed's kickoff time. That would be a second
source of truth about whether a bet is placeable, and the two could disagree.
The provider's `commence_time` is the one that matters, because the provider
is the one selling the price. If the provider's time is wrong, the guard is
wrong in the safe direction.

It does not apply a grace period. A game that started sixty seconds ago is
started.

It compares in UTC, always. Every comparison is between timezone-aware
instants; a naive datetime is a bug, not a fallback.

## One football-specific wrinkle, named rather than discovered later

American football's in-game markets are heavily traded, so a provider response
during a game legitimately carries live prices with a `commence_time` in the
past. Those are real, purchasable bets — and this lab still refuses them,
because it prices pre-game distributions and settles from a final boxscore.
A live price judged by a pre-game model is a model being asked a question it
was never fitted to answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone


#: The heading a quarantined selection is moved under. Exact wording: the card
#: template and its tests both match it, and it must never read as a verdict
#: on the bet's value.
QUARANTINE_HEADING = "Already started — no longer plays"

STARTED = "started"
UNCONFIRMED = "unconfirmed"
PLAYABLE = "playable"


@dataclass(frozen=True)
class KickoffVerdict:
    """Whether one selection's game is still ahead of us, and how sure we are."""

    state: str
    reason: str
    commence_time: str = ""

    @property
    def plays(self) -> bool:
        return self.state == PLAYABLE

    @property
    def is_no_value_call(self) -> bool:
        """Always False. Exists so the answer is written down, not assumed.

        A quarantined selection is not a model opinion. Anything rendering a
        card can ask, get False, and put it under the quarantine heading
        rather than under passes.
        """
        return False


def parse_commence_time(value: object) -> datetime | None:
    """A timezone-aware instant, or None.

    None for anything that is not unambiguously an instant: blank, malformed,
    or — importantly — a naive datetime. A naive timestamp is not "probably
    UTC". Assuming a zone for it would move a Sunday-night kickoff across a
    date boundary, which is the same class of error that discarded 69% of the
    NHL lab's bought prices.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc)


def judge(commence_time: object, *, now: datetime) -> KickoffVerdict:
    """Whether a game with this start time may still be bet."""
    if now.tzinfo is None:
        # A naive "now" would compare against aware instants and raise, or
        # worse, be silently coerced somewhere upstream. Refuse it here.
        raise ValueError(
            "The kickoff guard compares timezone-aware instants. A naive "
            "`now` is a bug, not a fallback."
        )
    text = str(commence_time or "").strip()
    moment = parse_commence_time(commence_time)
    if moment is None:
        return KickoffVerdict(
            state=UNCONFIRMED,
            reason=(
                "The start time could not be confirmed — it is missing, "
                "unparseable, or carries no timezone. Ambiguity falls on the "
                "not-a-play side, so the stake is removed."
            ),
            commence_time=text,
        )
    if moment <= now.astimezone(timezone.utc):
        return KickoffVerdict(
            state=STARTED,
            reason=(
                f"Kickoff was {moment.isoformat()}, at or before this card was "
                "generated. The bet is no longer available at the price shown."
            ),
            commence_time=text,
        )
    return KickoffVerdict(
        state=PLAYABLE,
        reason=f"Kickoff is {moment.isoformat()}, still ahead.",
        commence_time=text,
    )


def partition(
    selections: list[Mapping[str, object]], *, now: datetime
) -> tuple[list[Mapping[str, object]], list[tuple[Mapping[str, object], KickoffVerdict]]]:
    """Split selections into those that still play and those quarantined.

    Returns `(plays, quarantined)`. The quarantined half carries its verdict
    so the card can print the reason beside each one — a quarantine with no
    stated reason is indistinguishable from a pick that was silently dropped.
    """
    plays: list[Mapping[str, object]] = []
    quarantined: list[tuple[Mapping[str, object], KickoffVerdict]] = []
    for selection in selections:
        verdict = judge(selection.get("commence_time"), now=now)
        if verdict.plays:
            plays.append(selection)
        else:
            quarantined.append((selection, verdict))
    return plays, quarantined
