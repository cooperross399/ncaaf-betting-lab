"""What last night's games and quarterbacks say about today's slate — as context.

The card's probabilities are anchored on the books' consensus line
(`reports/card_pricing.py`). This section sits beside them and shows the two
things the lab learns from each night's results:

* the **form rating** (`models/form.py`), refitted every run from every
  finished FBS-vs-FBS game, recent games weighing most; and
* the **quarterback flag** (`data/starters.py`): whether a team's last game was
  started by someone other than its usual quarterback.

**Neither moves a probability.** Both were measured against 2022-2025 closing
and opening lines before they reached the card and returned no demonstrated
edge (`data/outputs/nightly_form.md`), so they are printed as what they are: a
description of how teams are playing, which the price already carries. Printing
them beside the price is what lets the forward record say whether that stays
true this season.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from ncaaf_betting_lab.data.cfbfastr import Game
from ncaaf_betting_lab.data.starters import StarterState, state_before
from ncaaf_betting_lab.models import form

HEADING = "## Form and quarterbacks — context, not an opinion"


@dataclass(frozen=True)
class GameContext:
    label: str
    market_margin: float | None
    form_margin: float | None
    home_qb: StarterState
    away_qb: StarterState
    home_qb_name: str = ""
    away_qb_name: str = ""

    @property
    def disagreement(self) -> float | None:
        if self.market_margin is None or self.form_margin is None:
            return None
        return self.form_margin - self.market_margin


def starter_states(
    season_games: Iterable[Game],
    starters: pd.DataFrame | None,
    *,
    before: datetime,
) -> dict[str, tuple[StarterState, str]]:
    """Each team's quarterback state before `before`, with its last starter's name.

    Keyed by team id. Every finished game of the team this season counts, FCS
    opponents included, because a quarterback change against an FCS side is
    still a change.
    """
    if starters is None or starters.empty:
        return {}
    by_game = {
        (str(row.game_id), str(row.team)): (str(row.player_id), str(row.player))
        for row in starters.itertuples()
    }
    history: dict[str, list[str]] = defaultdict(list)
    names: dict[str, str] = {}
    finished = [
        g for g in season_games
        if g.has_result and g.start_date and form._kickoff(g.start_date) < before
    ]
    for game in sorted(finished, key=lambda g: g.start_date):
        for team_id, team_name in ((game.home_id, game.home_team), (game.away_id, game.away_team)):
            if not team_id:
                continue
            player_id, player = by_game.get((game.game_id, team_name), ("", ""))
            history[team_id].append(player_id)
            if player:
                names[team_id] = player
    return {
        team: (state_before(starts), names.get(team, ""))
        for team, starts in history.items()
    }


def build(
    slate: Mapping[str, tuple[Game, float | None]],
    ratings: form.FormRatings | None,
    quarterbacks: Mapping[str, tuple[StarterState, str]],
) -> list[GameContext]:
    """`slate` maps a game label to the game and the market's home margin."""
    empty = StarterState(None, None, 0)
    rows = []
    for label, (game, market_margin) in sorted(slate.items()):
        form_margin = None
        if ratings is not None and game.is_fbs_only:
            form_margin = ratings.margin(
                game.home_id or game.home_team,
                game.away_id or game.away_team,
                neutral=bool(game.neutral_site),
            )
        rows.append(
            GameContext(
                label=label,
                market_margin=market_margin,
                form_margin=form_margin,
                home_qb=quarterbacks.get(game.home_id, (empty, ""))[0],
                away_qb=quarterbacks.get(game.away_id, (empty, ""))[0],
                home_qb_name=quarterbacks.get(game.home_id, (empty, ""))[1],
                away_qb_name=quarterbacks.get(game.away_id, (empty, ""))[1],
            )
        )
    return rows


def _margin(value: float | None) -> str:
    return "—" if value is None else f"{value:+.1f}"


def _qb(state: StarterState, name: str) -> str:
    changed = state.qb_changed
    if changed is None:
        return "no read"
    who = f" ({name})" if name else ""
    return f"**changed last game**{who}" if changed else f"same{who}"


def render(
    rows: list[GameContext],
    ratings: form.FormRatings | None,
    *,
    starters_through: str | None,
) -> str:
    lines = [HEADING, ""]
    lines.append(
        "Refitted this run from every finished FBS-vs-FBS game, recent games "
        "weighing most. **These numbers do not move any probability above**: "
        "measured on 2022-2025 they added nothing to the closing or opening "
        "line (`data/outputs/nightly_form.md`), so they are a description of "
        "how teams are playing, not an edge."
    )
    lines.append("")
    if ratings is None:
        lines.append(
            f"**No form rating** — fewer than {form.MINIMUM_HISTORY} finished "
            "games were available to fit it."
        )
    else:
        lines.append(
            f"Form rating fitted on {ratings.games:,} games through "
            f"{ratings.as_of:%Y-%m-%d %H:%M} UTC; home field "
            f"{ratings.home_field:+.1f} points."
        )
    lines.append(
        "Quarterback reads come from cfbfastR's play-level file"
        + (f", which runs through {starters_through}" if starters_through else ", which was not available this run")
        + ". **No free source names the coming game's starter**, and no "
        "league-wide college injury feed exists; a change flag means a "
        "different quarterback took most of the dropbacks last time out."
    )
    lines.append("")
    if not rows:
        lines.append("No game on this slate resolved to the schedule.")
        return "\n".join(lines) + "\n"
    lines.append("| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |")
    lines.append("|:---|---:|---:|---:|:---|:---|")
    for row in rows:
        lines.append(
            f"| {row.label} | {_margin(row.market_margin)} | {_margin(row.form_margin)} | "
            f"{_margin(row.disagreement)} | {_qb(row.home_qb, row.home_qb_name)} | {_qb(row.away_qb, row.away_qb_name)} |"
        )
    return "\n".join(lines) + "\n"
