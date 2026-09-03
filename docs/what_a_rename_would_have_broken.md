# What a rename would have broken

The machinery in this lab was ported from `../football-betting-lab`, which is
finished, measured, and found **no demonstrated edge** across seven independent
instruments on 816 games and 5.67M bought price rows. The port was deliberate
and the code is good. **Renaming it would have been a disaster**, and this
document is the list of reasons, established before a line of college data was
fetched.

Two of these were found by auditing the NFL lab and are **already fixed there**
(`football-betting-lab` PR #23). The rest are things this lab must build
differently from the start.

## The headline trap: an unrated team is priced as league average

`scoring.py` reads a team's rating with `.get(team, 0.0)`, for both offence and
defence. **There is no "I do not know this team" state anywhere in the model or
the card.** An unrated opponent does not raise, does not abstain, and does not
land in `no_opinion` — it is silently priced as exactly average.

In the NFL that is nearly unreachable: 32 clubs, all rated, every week. In
college it is the *normal case* for weeks 1–3, and permanent for every FCS
opponent.

**What this lab does instead.** Rating coverage is an explicit precondition:
every priced fixture must have both sides present in `ratings.offence` and
`ratings.defence` with a minimum games-played threshold, and a fixture that
fails lands in a **new named bucket in the accounting identity** —
`unrated_opponent` — never in `no_opinion`. Forty-eight skipped Week 1 games
must be visible as a number, not as an absence.

The same defect starves ordinary FBS teams early. `PRIOR_GAMES = 17.0` is a
whole NFL season; a college team with three games carries only 15% of its own
signal, against forty-point talent gaps.

## The second-order trap: FBS-vs-FCS is wrong whichever way you go

Whatever this lab does about FBS-vs-FCS games in the **ratings** is wrong by
default:

* **Include them** and every FBS offence rating is inflated by a 63–3 win over
  Mercer, poisoning the fit for the whole season.
* **Exclude them** and every team that opened against an FCS opponent has one
  fewer rated game, so weeks 2–3 ratings sit near league average for exactly
  the teams that scheduled a cupcake.

Neither is handled by the ported code, because the NFL has no such games. This
needs a **deliberate, recorded decision** — drop them from the fit, or fit them
with a separate FCS-strength term — and it goes through the verdicts door with
a measurement behind it, not a shrug in a docstring.

## Team identity does not survive the college universe

`team_names.py` assumes a closed, one-to-one abbreviation map. Within FBS that
holds: ESPN abbreviations are unique across 138 of 138 teams. Across all **760**
college football teams it does not — `OSU` is both Ohio State and Ohio State
Newark, and the locations `Charlotte` and `Troy` each collide with a non-FBS
school.

So the ported map is safe **only** if its universe is FBS-only — which is
exactly the choice that makes FCS opponents unresolvable. The registry must
carry **classification alongside the name**, and the club set must mean "FBS
members *this season*", keyed by season: membership changed by two teams this
year.

## Settlement loses half of Week 1 if the results feed is FBS-only

`forward_evidence.py` resolves a result through `team_lookup` and then
`game_index`. An FCS opponent that does not resolve — or a results feed fetched
FBS-only — means the game is never found, and after the patience window every
priced row on it is recorded `UNSETTLEABLE`. On a Week 1 Saturday that is
potentially half the frozen rows.

Worse, it compounds with the day-as-unit rule: the day is stamped into the
ledger while the unresolved rows are dropped, so that day's return is computed
on the **FBS-vs-FBS subset only** — a selection bias on the season's most
important slate.

**The results feed must include FCS opponents, and the classification-aware
exclusion must happen before freezing, never at settlement.**

## The credit cap is sized for sixteen games, not seventy-nine

`daily_credit_cap = 1_800` was derived from the NFL's worst slate: 16
simultaneous games. **A college Saturday is 79.** At the NFL lab's own tier-1+2
team set the worst college day needs **2,057** credits, and at the full
documented team catalogue **3,479**.

Renamed, the cap holds at 1,800, the fetch guard raises partway down the
alphabet of the slate, and the forward ledger freezes a **biased subset of the
biggest Saturday of the season as though it were the day**. The NFL lab names
this as the failure it most fears; it simply cannot see it from sixteen games.

This lab's cap is set to 4,000 and **marked provisional** until derived from a
real college schedule and a real market list.

## The horizon window drops late West Coast games

The shadow report compares an event's **league** date against a **UTC** date.
For the NFL those almost never diverge, because cards are built on Sunday
morning. For college, **150 of 888 games (17%)** have a UTC date different from
their ET date, and kickoffs run to 23:59 ET.

So any run started after 20:00 ET sees the horizon roll to the next UTC day and
**silently drops every remaining late-window West Coast and Hawaii game** — the
same class of silent drop that cost the NHL lab 69% of every price it bought.

## The day-as-unit ledger assumes an NFL-shaped day

The forward ledger's day-as-unit rule, and the slate-coverage watchdog's
`THIN_SNAPSHOT_ROWS = 25` and `SETTLEMENT_GRACE_DAYS = 5`, were all calibrated
against 13–16 games in three kickoff windows with one pre-slate freeze.

A college season is **75 game days whose median is 3 games**, with 48 days of
three or fewer, and Saturdays running 11:00 ET to 23:59 ET. On rename the
watchdog flags nearly every Tuesday and every bowl day as "a run that fetched
almost nothing", and a single daily freeze holds a price **13 hours stale** for
a late window it can never reprice.

## Two watchdogs had stopped watching (fixed in the NFL lab)

`run_feed_freshness.py` read
`len(league.club_abbreviations()) if hasattr(...) else 32` — and `League` has
no such attribute, so the literal fired every time. `season.py` held
`EXPECTED_NFL_CLUBS = 32` outside the registry. Both were correct for the NFL
by accident and would have passed a college schedule that had lost a hundred
teams. Fixed in `football-betting-lab` PR #23, and this lab starts with the
club count read from the registry.

## The NFL's retention answer does not transfer

The NFL's 7,280-credit probe established that all 27 tier-1 markets have
retained history across nine books — measured on `americanfootball_nfl`.
College coverage of alternate ladders, team totals and quarter markets at
Group-of-Five books is **unknown**. Every market in `markets.py` carries
`retained=None`, which means unprobed — not `False`, which would be a finding,
and not `True`, which would be a guess.

Buying a college season on the NFL's probe numbers risks spending ~89,700
credits to discover the ladders were never hung.

## And college football is not the NFL's distribution

Recorded in `markets.py` rather than only here, because the registry is what a
session reads before building:

* **There are no draws.** Every level game is decided in overtime, so
  `h2h_3_way` is deferred — pricing a draw would invent an outcome that cannot
  occur.
* **Overtime is a different distribution.** Possessions start at the
  opponent's 25 and become a two-point shootout from the third period. A total
  settled without modelling that is settled correctly and *priced* wrongly.
* **A half can still end level**, because the overtime rule does not apply to
  it. The NFL lab priced a level half at 0.4% until that was caught.
* **Whether 3 and 7 are still the key numbers is an open question.** The NFL
  model's exact-push machinery assumes NFL lumpiness and must be re-measured,
  not inherited.
