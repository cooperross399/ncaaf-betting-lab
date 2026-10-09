"""A team rating that learns from last night's games.

The card's centre is the market's consensus line, and nothing in it updates
inside a season (`reports/card_pricing.py`). This module is the rating that
does: refitted from every finished FBS-vs-FBS game each time the card runs, with
recent games weighing more than old ones and blowouts capped.

**It is context, not an opinion, until it beats the price.** The estimator and
the bar it has to clear were fixed before it was measured
(`docs/preregistered_nightly_form.md`), and the result is in
`data/outputs/nightly_form.md`. Step 5 found the equal-weight version of this
rating adds nothing to the closing price (`data/outputs/ratings_residual.md`).

## The estimator

Weighted ridge least squares of capped margin on home and away team indicators
plus a home-field term (zero on neutral sites). A game weighs
`0.5 ** (age / HALF_LIFE_WEEKS)`, where age runs on a **season clock**: weeks
inside a season count as weeks, and each off-season crossed counts as
`OFFSEASON_WEEKS`. Without that compression a summer would be thirty-six weeks,
every game before it would weigh almost nothing, and the ridge penalty would
pull every team to zero at week 1.

Teams are keyed by the feed's own id, never a spelling.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import Game

#: Fixed in `docs/preregistered_nightly_form.md`. Changing any of these is a
#: new ledger entry, not a tweak.
HALF_LIFE_WEEKS = 6.0
OFFSEASON_WEEKS = 8.0
MARGIN_CAP = 28.0
RIDGE = 3.0
MINIMUM_HISTORY = 300


def _kickoff(start_date: str) -> datetime:
    return datetime.fromisoformat(str(start_date).replace("Z", "+00:00"))


def games_frame(games: Iterable[Game]) -> pd.DataFrame:
    """Finished FBS-vs-FBS games as the frame the fit reads."""
    rows = [
        {
            "game_id": g.game_id,
            "season": int(g.season),
            "season_type": g.season_type,
            "week": int(g.week),
            "kickoff": _kickoff(g.start_date),
            "home": g.home_id or g.home_team,
            "away": g.away_id or g.away_team,
            "home_name": g.home_team,
            "away_name": g.away_team,
            "neutral": bool(g.neutral_site),
            "margin": float(g.margin),
        }
        for g in games
        if g.is_fbs_only and g.has_result and g.start_date
    ]
    columns = [
        "game_id", "season", "season_type", "week", "kickoff", "home", "away",
        "home_name", "away_name", "neutral", "margin",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    return frame.sort_values("kickoff").reset_index(drop=True)


def season_clock(history: pd.DataFrame, season: int, moment: datetime) -> np.ndarray:
    """Each game's age in season-clock weeks, measured from `moment` in `season`.

    A season's length is measured from its own first to its last kickoff, so a
    game in an earlier season is aged by what was left of its season, the full
    length of every season in between, an off-season per boundary, and the
    elapsed part of the current one.
    """
    kickoffs = history["kickoff"]
    seasons = history["season"].astype(int)
    starts = kickoffs.groupby(seasons).min()
    ends = kickoffs.groupby(seasons).max()
    current_start = starts.get(season, moment)
    elapsed_now = max((moment - current_start).total_seconds(), 0.0) / 604800.0

    ages = np.empty(len(history))
    for i, (kickoff, game_season) in enumerate(zip(kickoffs, seasons)):
        if game_season == season:
            ages[i] = (moment - kickoff).total_seconds() / 604800.0
            continue
        rest_of_its_season = (ends[game_season] - kickoff).total_seconds() / 604800.0
        between = sum(
            (ends[s] - starts[s]).total_seconds() / 604800.0
            for s in range(game_season + 1, season)
            if s in starts.index
        )
        crossings = season - game_season
        ages[i] = rest_of_its_season + between + crossings * OFFSEASON_WEEKS + elapsed_now
    return np.maximum(ages, 0.0)


@dataclass(frozen=True)
class FormRatings:
    """Points better than an average FBS team on a neutral field."""

    ratings: dict[str, float]
    home_field: float
    games: int
    as_of: datetime

    def margin(self, home: str, away: str, *, neutral: bool) -> float | None:
        """The rating's home margin, or None when either team is unrated."""
        if home not in self.ratings or away not in self.ratings:
            return None
        return self.ratings[home] - self.ratings[away] + (0.0 if neutral else self.home_field)


def fit(history: pd.DataFrame, *, season: int, as_of: datetime) -> FormRatings | None:
    """Ratings from every game in `history` that kicked off before `as_of`.

    None below `MINIMUM_HISTORY` games: a rating that is mostly the ridge prior
    is noise about noise, and the card says so rather than printing it.
    """
    past = history[history["kickoff"] < as_of]
    if len(past) < MINIMUM_HISTORY:
        return None
    weights = 0.5 ** (season_clock(past, season, as_of) / HALF_LIFE_WEEKS)
    teams = sorted(set(past["home"]) | set(past["away"]))
    index = {team: i for i, team in enumerate(teams)}
    rows = np.arange(len(past))
    design = np.zeros((len(past), len(teams) + 1))
    design[rows, past["home"].map(index).to_numpy()] += 1.0
    design[rows, past["away"].map(index).to_numpy()] -= 1.0
    design[:, -1] = (~past["neutral"].astype(bool)).to_numpy(dtype=float)
    target = np.clip(past["margin"].to_numpy(dtype=float), -MARGIN_CAP, MARGIN_CAP)

    weighted = design * weights[:, None]
    normal = design.T @ weighted + RIDGE * np.eye(design.shape[1])
    if design[:, -1].any():
        # Home field is identified whenever a game is not neutral, so it is not
        # shrunk — the same reasoning as `ratings_residual.fit_ratings`.
        normal[-1, -1] -= RIDGE
    beta = np.linalg.solve(normal, weighted.T @ target)
    return FormRatings(
        ratings={team: float(beta[index[team]]) for team in teams},
        home_field=float(beta[-1]),
        games=len(past),
        as_of=as_of,
    )
