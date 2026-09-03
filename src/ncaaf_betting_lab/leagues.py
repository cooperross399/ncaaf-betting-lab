"""The league registry. Every league-specific fact lives here and nowhere else.

This lab is **college football, and only college football.** The NFL lives in
its own repository (`../football-betting-lab`) and the two share no code — a
deliberate choice, and a costly one, recorded in `CLAUDE.md`.

The registry stays anyway, and it is not ceremony. It is what keeps the
league-specific facts — sport key, market list, calendar, timezone, credit cap,
verdict path — in one place rather than scattered through the code, which is
exactly what made this machinery portable from the NFL lab in the first place.
It is a **portability** device rather than a multi-league one. A discipline test
(`tests/test_league_registry_is_the_only_place.py`) fails the build when one
appears, because the alternative — noticing during the NCAAF build — is
noticing after the cost has been paid.

## What "per league" means, precisely

Models are **fitted** per league. Measurements are **reported** per league.
Verdicts are **recorded** per league. Receipts and allowlist entries are
**signed** per league. Nothing is pooled across the two labs: ~134 FBS teams
with forty-point talent gaps and 32 near-parity NFL clubs do not share a
distribution, and a figure computed across both describes neither.

**And nothing from the NFL lab's measurements carries over as evidence.** Its
result — no demonstrated edge across seven instruments, on 816 games and 5.67M
bought price rows — says nothing about this league. The machinery ports; the
findings do not.

A shared or hierarchical model across the two labs is not forbidden — it is
*unproven*, and it would require the two repositories to exchange data, which
today they do not.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class League:
    """One league: what it is called, where its data comes from, what it costs."""

    #: The key used everywhere inside this repository. Also the directory
    #: segment under `data/` and the prefix on every output file, so two
    #: leagues can never write over each other's evidence.
    key: str
    #: Human title for reports.
    title: str
    #: The Odds API sport key. The provider's vocabulary, not ours.
    provider_sport_key: str
    #: The data-source adapter module that supplies schedules, results,
    #: rosters and player logs. Named rather than imported so the registry
    #: stays importable without pulling every adapter into every process.
    data_adapter: str
    #: The registry of markets this league prices. Per league because the
    #: provider serves NFL and NCAAF from the same key list but the books
    #: quote wildly different subsets, and "unquoted" must never be
    #: confused with "not asked for".
    market_registry: str
    #: The league's own calendar timezone. A game belongs to the day it is
    #: played in this zone, not to its UTC date.
    timezone: ZoneInfo
    #: Hard per-day credit cap. Not advisory: the fetch spends front-to-back
    #: and stops. Set from the league's own worst slate, so it can never
    #: starve one.
    daily_credit_cap: int
    #: Provider name in the staging policy. Allowlisting a market for one
    #: league never allowlists it for another, so the policy is keyed by
    #: `{provider}:{league}` and this is the league half.
    policy_provider_name: str = "the_odds_api"

    @property
    def data_dir_segment(self) -> str:
        """Where this league's data lives under `data/raw`, `data/processed`."""
        return self.key

    def output_name(self, stem: str, suffix: str) -> str:
        """`ncaaf_forward_evidence.md` — never a bare `forward_evidence.md`.

        An unprefixed output is a file two leagues would both write, and the
        second one to run would silently become the record.
        """
        return f"{self.key}_{stem}{suffix}"

    def verdict_dir(self, outputs_dir: Path) -> Path:
        return Path(outputs_dir) / self.key

    def policy_key(self) -> str:
        """The allowlist entry this league's card consults.

        Keyed by league on purpose: approving `player_pass_yds` in the NFL
        says nothing about approving it in college football, where the
        distribution, the roster churn and the books' own coverage are all
        different. One receipt, one league.
        """
        return f"{self.policy_provider_name}:{self.key}"


#: College football. The only league this lab builds.
#:
#: **Team markets only.** Cooper ruled college player props out of scope on
#: 2026-08-28 and has not reversed it. That is a large simplification and it is
#: recorded in the registry rather than only in a document, because the
#: registry is what a session reads before building: it removes the transfer
#: portal, opt-outs and a per-player college data join from the critical path
#: entirely, and cuts the credit cost of a college Saturday by roughly four
#: fifths.
NCAAF = League(
    key="ncaaf",
    title="NCAAF",
    provider_sport_key="americanfootball_ncaaf",
    # There is no nflverse for college football, and choosing what replaces it
    # was the largest open question here. cfbfastR commits CSV directly to a
    # public repository — a file download, so no API key and no rate limit —
    # and its schedule carries `home_division`/`away_division` per game, which
    # is what lets this lab decline the 127 of 888 fixtures that put an FBS
    # team against an opponent it has no rating for. The same project's REST
    # API is capped at 1,000 calls a month on the free tier and omits nothing
    # this needs; the files are simply better. See data/cfbfastr.py.
    data_adapter="ncaaf_betting_lab.data.cfbfastr",
    market_registry="ncaaf_betting_lab.markets",
    # Games run from Hawaii to the east coast and kick from Tuesday night to
    # Saturday midnight. Eastern is the calendar the schedule is published in;
    # it is not a claim that the day is shaped like an NFL Sunday.
    timezone=ZoneInfo("America/New_York"),
    # PROVISIONAL, and marked so. The NFL cap was derived by
    # `scripts/estimate_credit_cost.py` from its real schedule and its real
    # market list; neither exists here yet. A college Saturday carries far more
    # games than an NFL Sunday, so this will move — and a cap below the worst
    # slate starves the fetch, which looks identical in the reports to a market
    # nobody quotes. Derive it before the first live run.
    daily_credit_cap=4_000,
)

LEAGUES: dict[str, League] = {NCAAF.key: NCAAF}

#: The default, and the only entry. A caller that needs a league and does not
#: say which gets this one.
DEFAULT_LEAGUE_KEY = NCAAF.key


def league_for(key: str) -> League:
    """The league, or an error naming what exists.

    Raises rather than defaulting: a typo that silently priced the wrong
    league would put one league's opinions in another's ledger, and the
    ledger is never revised.
    """
    try:
        return LEAGUES[key]
    except KeyError:
        raise KeyError(
            f"No league {key!r}. This lab knows: {', '.join(sorted(LEAGUES))}. "
            "The NFL lives in its own repository."
        ) from None


def league_keys() -> tuple[str, ...]:
    return tuple(sorted(LEAGUES))
