"""The Odds API adapter. Shadow-only by construction.

**Ported from the sibling NFL lab** (`../football-betting-lab`, the same file),
deliberately and visibly, rather than imported — `CLAUDE.md`, "The five labs
never import from each other". Every billing rule and guard below was earned
there and in the NHL lab; the parsing is cut down to team markets, because
college player props are out of scope (Cooper, 2026-08-28).

What this module does: fetch prices, normalise them into long-form rows, and
write them into `data/staging/`. What it does not do, ever: decide anything.
The card cannot read `data/staging/` — it reads only markets a reviewed policy
allowlists. So a fetch can be wrong, incomplete, or surprising without a single
pick changing.

## The credential

Read from `FOOTBALL_ODDS_API_KEY` in the environment — the variable name
`providers/env_file.py` allowlists, inherited from the port. In CI the gameday
workflow maps the repository secret `NCAAF_ODDS_API_KEY` onto it, in the one
step that fetches; locally it comes from a gitignored `.env`. It is never written to a report, a provenance file,
a staged row, or a log line. Every string that reaches a report goes through
`redact`, and `tests/test_no_secrets_committed.py` fails the build if a key
shape ever reaches a tracked file.

**The key is never passed as a command-line argument.** A process list is
world-readable on a shared machine and a CI log echoes commands.

## What a fetch costs

From the provider's own documentation, verified 2026-08-28:

* `/v4/sports` and `/v4/sports/{sport}/events` — **free**.
* `/v4/sports/{sport}/odds` — `markets x regions`, whole slate.
* `/v4/sports/{sport}/events/{id}/odds` — `unique markets **returned** x
  regions`. An asked-for market nobody quotes costs nothing.
* `/v4/sports/{sport}/scores?daysFrom=N` — 2.
* every `/v4/historical/...` equivalent — **10x** the live rate. This lab
  calls none of them; buying history is a separate decision of Cooper's.

Every entry point states its cost before spending it and takes a hard cap, so
a probe cannot become a bill by accident. The cap is checked **before** each
request, against the pessimistic bound, and the real spend is read afterwards
from `x-requests-last` rather than assumed.

## The sport key comes from the league registry

Never from a literal here. That is what makes NCAAF a registry entry rather
than a search-and-replace, and `tests/test_league_registry_is_the_only_place.py`
fails the build if this module ever writes one.
"""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

from ncaaf_betting_lab.leagues import League
from ncaaf_betting_lab.markets import market_for_provider_key
from ncaaf_betting_lab.providers.env_file import redact
from ncaaf_betting_lab.season import game_date
from ncaaf_betting_lab.selection import (
    normalise_line,
    over_under_selection,
    team_selection,
    team_total_selection,
)


API_KEY_ENV = "FOOTBALL_ODDS_API_KEY"
API_BASE_URL_ENV = "FOOTBALL_ODDS_API_BASE_URL"
DEFAULT_API_BASE_URL = "https://api.the-odds-api.com"

#: Only these hosts. A base-URL override is a convenience for testing against a
#: local mock, not a way to point the credential at an arbitrary server.
ALLOWED_API_HOSTS = frozenset({"api.the-odds-api.com", "ipv6-api.the-odds-api.com"})

PROVIDER_KEY = "odds_api"
PROVIDER_NAME = "the_odds_api"
PROVIDER_TYPE = "odds_api"

DEFAULT_REGIONS = "us"

#: The only markets the bulk endpoint will serve. Anything else there makes
#: the provider refuse the whole request with a 422 that names nothing.
BULK_SAFE_MARKETS: frozenset[str] = frozenset({"h2h", "spreads", "totals"})

#: The only response headers that may be recorded. Everything else in a
#: response's headers is either useless here or a place a credential could
#: hide; an allowlist is the safe shape.
SAFE_RESPONSE_HEADERS = (
    "x-requests-remaining",
    "x-requests-used",
    "x-requests-last",
)


class ProviderError(RuntimeError):
    """The provider could not be used. Never carries a credential."""


class MissingCredentialError(ProviderError):
    """No key is available, so nothing live may be attempted."""


class CreditCapReached(ProviderError):
    """The next request could breach the cap, so it was not made."""


Requester = Callable[..., Any]


def _default_requester(url: str, *, params: Mapping[str, str], timeout: float) -> Any:
    return requests.get(url, params=dict(params), timeout=timeout)


@dataclass
class Spend:
    """What a run actually cost, measured rather than estimated."""

    credits_spent: int = 0
    requests_made: int = 0
    quota_remaining: str = ""
    quota_used: str = ""
    #: What the pessimistic pre-flight bound would have predicted, kept so the
    #: two can be compared in the report. A large gap is information: it means
    #: most asked markets are not quoted.
    credits_estimated: int = 0
    notes: list[str] = field(default_factory=list)

    def record(self, headers: Mapping[str, str], *, fallback: int) -> int:
        """Charge one response, preferring the measured cost over the guess.

        A missing `x-requests-last` charges the pessimistic fallback. Guessing
        low would let a run drift past its cap while reporting that it had not.
        """
        self.requests_made += 1
        try:
            actual = int(str(headers.get("x-requests-last", "")).strip())
        except (TypeError, ValueError):
            actual = 0
        if actual <= 0:
            actual = int(fallback)
            self.notes.append(
                "A response carried no `x-requests-last`; charged the "
                f"pessimistic estimate of {fallback} against the cap instead."
            )
        self.credits_spent += actual
        for header, attribute in (
            ("x-requests-remaining", "quota_remaining"),
            ("x-requests-used", "quota_used"),
        ):
            value = str(headers.get(header, "")).strip()
            if value:
                setattr(self, attribute, value)
        return actual

    def summary_line(self) -> str:
        line = (
            f"{self.credits_spent:,} credit(s) actually spent over "
            f"{self.requests_made} request(s)"
        )
        if self.credits_estimated:
            line += (
                f"; the pessimistic pre-flight bound was "
                f"{self.credits_estimated:,}"
            )
        if self.quota_remaining:
            line += f"; {self.quota_remaining} remaining"
        return line + "."


class OddsApiProvider:
    """One door to the provider. Every request in this repository goes through it.

    One door on purpose. Two callers building their own requests is how a
    credential reaches a log, how a cap gets bypassed, and how two copies of
    the billing rules drift apart.
    """

    def __init__(
        self,
        league: League,
        *,
        environment: Mapping[str, str] | None = None,
        requester: Requester | None = None,
        regions: str = DEFAULT_REGIONS,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.league = league
        self.environment = dict(os.environ if environment is None else environment)
        self.requester = requester or _default_requester
        self.regions = (regions or DEFAULT_REGIONS).strip()
        self.timeout_seconds = float(timeout_seconds)
        self._validate_base_url()

    # -- configuration ---------------------------------------------------

    @property
    def api_key(self) -> str:
        return str(self.environment.get(API_KEY_ENV, "")).strip()

    @property
    def base_url(self) -> str:
        return str(
            self.environment.get(API_BASE_URL_ENV) or DEFAULT_API_BASE_URL
        ).strip().rstrip("/")

    @property
    def sport_key(self) -> str:
        """From the registry. Never a literal in this module."""
        return self.league.provider_sport_key

    def _validate_base_url(self) -> None:
        host = (urlparse(self.base_url).hostname or "").lower()
        if host in ALLOWED_API_HOSTS:
            return
        if host in {"localhost", "127.0.0.1", "::1"}:
            # A local mock is the only other permitted target, and only
            # because a test that cannot run offline is a test nobody runs.
            return
        raise ProviderError(
            f"Refusing to send the credential to host {host!r}. Allowed: "
            f"{sorted(ALLOWED_API_HOSTS)} or a localhost mock."
        )

    def _require_credential(self) -> None:
        if not self.api_key:
            raise MissingCredentialError(
                f"A live fetch requires `{API_KEY_ENV}` from the environment, "
                "a gitignored local `.env`, or a GitHub Secret. Never pass the "
                "key as a command argument and never commit it."
            )

    # -- the one request path --------------------------------------------

    def _get(self, url: str, params: Mapping[str, str]) -> tuple[Any, dict[str, str]]:
        try:
            response = self.requester(
                url, params=dict(params), timeout=self.timeout_seconds
            )
        except (requests.RequestException, OSError, TimeoutError) as exc:
            raise ProviderError(
                redact(
                    f"The odds provider could not be reached "
                    f"({type(exc).__name__}). Nothing was written."
                )
            ) from exc
        status = int(getattr(response, "status_code", 0) or 0)
        if status != 200:
            # The status alone, never the URL: the URL carries the key.
            raise ProviderError(
                f"The odds provider returned HTTP {status or 'unknown'}. "
                "Nothing was written."
            )
        try:
            payload = response.json()
        except (AttributeError, TypeError, ValueError) as exc:
            raise ProviderError("The odds provider returned unreadable JSON.") from exc
        headers = getattr(response, "headers", {}) or {}
        safe = {
            name: str(headers.get(name, ""))
            for name in SAFE_RESPONSE_HEADERS
            if headers.get(name) is not None
        }
        return payload, safe

    # -- free endpoints ---------------------------------------------------

    def quota(self) -> dict[str, str]:
        """Remaining and used, from the free `/v4/sports` listing.

        Documented as costing nothing, so this is the cheapest possible answer
        to "how much is left" and to "when does the month reset" — the reset
        shows up as `x-requests-used` falling, which is worth watching for and
        costs nothing to watch.
        """
        self._require_credential()
        _, headers = self._get(
            f"{self.base_url}/v4/sports", {"apiKey": self.api_key}
        )
        return headers

    def list_events(self) -> list[dict[str, Any]]:
        """The upcoming slate. Free, and **upcoming only**.

        Pointing this at a past window returns nothing, which looks exactly
        like "the provider has no data" and is not. This lab buys no past
        slates.
        """
        self._require_credential()
        payload, _ = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/events",
            {"apiKey": self.api_key, "dateFormat": "iso"},
        )
        if not isinstance(payload, list):
            raise ProviderError("The events list is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    # -- live prices ------------------------------------------------------

    def fetch_bulk(
        self, markets: tuple[str, ...], *, spend: Spend, credit_cap: int
    ) -> list[dict[str, Any]]:
        """The featured markets for the whole slate, in one call.

        Billed `markets x regions` regardless of how many events come back,
        which is why the three featured markets are never asked for per event.

        **Only `h2h`, `spreads` and `totals` may be asked here.** The provider
        answers a bulk request containing an alternate ladder or a period
        market with HTTP 422 for the *entire* request — which took down every
        team-market fetch in the NHL lab and looked like an off-season for two
        rounds of debugging, because the season genuinely had not started.
        """
        self._require_credential()
        forbidden = tuple(m for m in markets if m not in BULK_SAFE_MARKETS)
        if forbidden:
            raise ProviderError(
                f"{forbidden} cannot be asked of the bulk endpoint; the "
                "provider refuses the whole request. Ask them per event."
            )
        regions = self._region_count()
        bound = len(markets) * regions
        _guard(spend, credit_cap, bound, "the bulk slate")
        spend.credits_estimated += bound
        payload, headers = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/odds",
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
        )
        spend.record(headers, fallback=bound)
        if not isinstance(payload, list):
            raise ProviderError("The bulk odds response is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    def fetch_event_odds(
        self,
        event_id: str,
        markets: tuple[str, ...],
        *,
        spend: Spend,
        credit_cap: int,
    ) -> dict[str, Any]:
        """One event's non-featured markets.

        Billed `unique markets **returned** x regions`, so an asked-for market
        nobody quotes costs nothing — which is why the alternate ladders are
        carried year-round rather than written off.
        """
        self._require_credential()
        regions = self._region_count()
        bound = len(markets) * regions
        _guard(spend, credit_cap, bound, f"event {event_id}")
        spend.credits_estimated += bound
        payload, headers = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/events/{event_id}/odds",
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
        )
        spend.record(headers, fallback=bound)
        return payload if isinstance(payload, Mapping) else {}

    def _region_count(self) -> int:
        return len([r for r in self.regions.split(",") if r.strip()]) or 1


def sufficient_quota(headers: Mapping[str, str], credit_cap: int) -> tuple[bool, str]:
    """Whether there are enough credits left to start a run at all.

    Refusing is the safe direction. A run that starts with less than its cap
    gets partway through the slate and stops, leaving a snapshot holding the
    games it happened to reach — a biased subset frozen into the ledger as
    though it were the day, and forward evidence cannot be re-made.

    An unreadable header does **not** block the run: the guard exists to catch
    a known shortfall, not to make an unreadable response fatal, and the
    adapter's own cap still cannot be breached.
    """
    remaining = str(headers.get("x-requests-remaining", "")).strip()
    if not remaining.lstrip("-").isdigit():
        return True, (
            "The provider did not report a remaining quota. Proceeding: the "
            "per-request cap still cannot be breached."
        )
    left = int(remaining)
    if left < credit_cap:
        return False, (
            f"{left} credits remain, below the {credit_cap} this run could "
            "spend. Nothing was requested. A partial slate frozen into the "
            "ledger is worse than no card."
        )
    return True, f"{left} credits remain, against a cap of {credit_cap}."


def _guard(spend: Spend, credit_cap: int, bound: int, what: str) -> None:
    """Refuse a request whose pessimistic cost could breach the cap.

    Checked **before** the request, not after. A cap enforced after the spend
    is not a cap; it is a report of how far past it the run went.
    """
    if credit_cap and spend.credits_spent + bound > credit_cap:
        raise CreditCapReached(
            f"Stopping before {what}: it could cost up to {bound} credits, "
            f"{spend.credits_spent} of the {credit_cap}-credit cap are already "
            "spent, and the cap is enforced against the pessimistic bound. "
            "Nothing further was requested."
        )


# -- turning a response into rows -------------------------------------------


STAGING_PRICES_FILENAME = "odds_api_prices_staging.csv"

ROW_COLUMNS = (
    "fetched_at",
    "event_id",
    # The provider key the row came from, kept alongside this lab's market
    # name. A featured line and its alternate ladder are different products
    # at a book, and diagnosing a suspicious return without knowing which one
    # a row came from means guessing.
    "provider_key",
    "commence_time",
    "date",
    "home_team",
    "away_team",
    "market",
    "player",
    "selection",
    "line",
    "american_odds",
    "book",
)


@dataclass
class Normalised:
    """Rows parsed from one response, and what could not be parsed.

    `unparseable` is counted rather than dropped. It is a term in the
    accounting identity the card prints every run —
    `priced = no_opinion + below_threshold + unparseable + ambiguous + bets` —
    and a parser that silently discards what it does not recognise makes that
    identity reconcile while hiding the thing it exists to surface.
    """

    rows: list[dict[str, Any]] = field(default_factory=list)
    unparseable: int = 0
    reasons: Counter = field(default_factory=Counter)

    def note(self, reason: str) -> None:
        self.unparseable += 1
        self.reasons[reason] += 1


def american_price(value: object) -> int | None:
    """An American price, or None. Zero is not a price."""
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return number or None


def normalize_event(
    event: Mapping[str, Any], league: League, *, fetched_at: str
) -> Normalised:
    """Long-form price rows for one event payload.

    **Every book's price is kept.** The card quotes the best reachable book,
    so the staged table has to hold them all; keeping only the best here would
    make "the best price" mean "the best price at the moment of the fetch",
    which is not recoverable afterwards.

    A market this lab does not price is skipped and not counted as
    unparseable: a provider response legitimately carries dozens of them, and
    treating each as a fault would drown the number that matters.
    """
    result = Normalised()
    home = str(event.get("home_team", "")).strip()
    away = str(event.get("away_team", "")).strip()
    if not home or not away:
        result.note("event named no home or away club")
        return result
    commence = str(event.get("commence_time", "")).strip()
    day = game_date(commence, league)

    for bookmaker in event.get("bookmakers", []) or []:
        if not isinstance(bookmaker, Mapping):
            continue
        book = str(bookmaker.get("key") or bookmaker.get("title") or "").strip()
        for market in bookmaker.get("markets", []) or []:
            if not isinstance(market, Mapping):
                continue
            provider_key = str(market.get("key", "")).strip().lower()
            target = market_for_provider_key(provider_key)
            if target is None:
                continue
            for outcome in market.get("outcomes", []) or []:
                if not isinstance(outcome, Mapping):
                    result.note(f"{provider_key}: outcome was not an object")
                    continue
                price = american_price(outcome.get("price"))
                if price is None:
                    result.note(f"{provider_key}: no usable price")
                    continue
                name = str(outcome.get("name", "")).strip()
                description = str(outcome.get("description", "")).strip()
                line = normalise_line(outcome.get("point"))
                selection: str | None

                if target.key in {"team_total", "alternate_team_total"}:
                    selection = team_total_selection(name, description, home, away)
                elif target.selections == ("over", "under"):
                    selection = over_under_selection(name)
                else:
                    selection = team_selection(name, home, away)

                if selection is None:
                    result.note(f"{provider_key}: outcome {name!r} not in this lab's vocabulary")
                    continue
                result.rows.append(
                    {
                        "fetched_at": fetched_at,
                        "event_id": str(event.get("id", "")).strip(),
                        "provider_key": provider_key,
                        "commence_time": commence,
                        "date": day,
                        "home_team": home,
                        "away_team": away,
                        "market": target.key,
                        # Always empty: team markets only. Kept so the
                        # column set matches `selection_key`, which reads it.
                        "player": "",
                        "selection": selection,
                        "line": line,
                        "american_odds": price,
                        "book": book,
                    }
                )
    return result
