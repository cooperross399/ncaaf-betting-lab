# The build order

**Written 2026-09-03. The season is already running.** Week 0 was played on
2026-08-29/30 — 8 FBS games, all final and all settled in the schedule file
today. Week 1 opens this evening. **880 of the 888 FBS regular-season games on
the calendar are still ahead**, across 57 remaining game days to 2026-12-12
(measured from `data/raw/ncaaf/schedules/cfb_schedules_2026.csv`, 888 rows,
fetched 2026-09-03).

Eight games of forward evidence are already gone and cannot be recovered. That
is 0.9% of the season, which is small — and it is the whole argument for the
order below, because the same sentence is true of every week this lab spends
building a model instead of freezing an opinion.

---

## 0. Why college, said without optimism

The NFL lab is finished. Its honest result, on 816 games and 5.67M bought
price rows, is **no demonstrated edge across seven independent instruments**,
with 0 of 18 markets clearing bars declared in advance and every family-
corrected interval including zero
(`../football-betting-lab/docs/what_we_can_and_cannot_claim.md`,
`docs/what_a_rename_would_have_broken.md`). Three headline findings were
retracted after defects were found in the harness that produced them.

**The reason to try college is structural, not modelling.** There are 138 FBS
teams in 2026 against 32 NFL clubs, and 888 FBS regular-season games against
272 — so any given college game carries a small fraction of the attention,
the liquidity and the sharp money that every NFL game carries. That is a
hypothesis about *markets*, not about this model.

**Nothing about the NFL result suggests the model is good.** It is the same
model. Its priced record is: moneyline −6.2% over 1,923 bets, spread −1.9%
over 1,886, total −1.8% over 1,708, every interval including zero
(`../football-betting-lab/docs/what_we_can_and_cannot_claim.md`). If it is
carried across unchanged and college turns out to be a thinner market, the
most likely outcome is that it loses more slowly. **This document contains no
claim, forecast or expectation that any market here will be profitable**, and
no report this lab writes may contain one until a measurement says so.

The second structural fact cuts the other way and has to be said in the same
breath: **college is a harder settlement and identity problem than the NFL by
a wide margin**, and most of what follows is about that, not about edges.

---

## 1. What is different from the NFL, and must not be inherited

This is the whole risk of a port. The NFL machinery is good code and its
premises are NFL premises. Every one of these was measured against real
college data on 2026-09-03, not assumed.

### 1.1 The shape of the season

| | NFL 2026 | FBS 2026 | Source |
|:--|--:|--:|:--|
| Games | 272 | **888** (+ postseason, not yet published) | `cfb_schedules_2026.csv`, 888 rows |
| Game days | 57 | **58** | same, ET-bucketed |
| Busiest slate | 16 | **80** (2026-09-12; then 71, 68, 65) | same |
| Median games per day | ~5 | **3** | same; 34 of 58 days have ≤3 games |
| Weekdays played | 3 | **7** (Sat 751, Fri 66, Thu 34, Tue 18, Wed 15, Sun 3, Mon 1) | same |
| Kickoff spread, ET | ~10 hours | **11:00 to 23:00** | same, 487 non-TBD games |
| Kickoff time unknown | ~0 | **401 of 888 (45.2%) `start_time_tbd`** | same |
| Kickoff's UTC date ≠ its ET date | rare | **134 of 888 (15.1%)** | same |
| Clubs | 32, fixed | **138 in 2026; 136 in 2025; 134 in 2024** | `cfb_schedules_{2024,2025,2026}.csv` |

Consequences, each of which is a specific NFL assumption that is now false:

- **`daily_credit_cap` was derived from a 16-game slate.** The worst college
  day is 80 games. Against this lab's registry today (3 bulk + 7 per-event
  team keys, tier 1+2) that day needs **563 credits**; the cap is set to
  **4,000**, which is 7.1x headroom and safe — but it is currently *asserted*,
  and it must be recorded as **derived** from the real schedule and the real
  market list, and re-derived whenever either changes. A cap that clips the
  biggest Saturday freezes a biased subset of the season's most important
  slate into a ledger that can never be re-made.
- **One freeze per ledger day is wrong here.** A single daily freeze holds one
  price for a noon kickoff and an 11pm kickoff twelve hours apart. The freeze
  has to be per kickoff window, not per day.
- **Any horizon computed on a UTC date silently drops the late window.** 134
  games a season have a UTC date one day ahead of their ET date. This is the
  same failure family that cost the NHL lab 69% of every price it bought.
- **45.2% of kickoffs are placeholders.** The kickoff guard, the day-as-unit
  rule and every lead-time calculation would key on a time that is not a time.
  A TBD kickoff is an *unknown*, and the guard must treat it as it treats a
  missing one — not as a value.
- **The staleness thresholds are NFL-shaped.** `THIN_SNAPSHOT_ROWS = 25` and a
  five-day settlement grace were calibrated on 13–16 games in three windows. A
  median college day is 3 games; a watchdog carrying those numbers flags every
  Tuesday as a failed run and stops being read.

### 1.2 The settlement surface is smaller, and one arm of it is missing in season

The NFL lab settles every half and quarter market from nflverse play-by-play
filtered on `qtr`. **College has no in-season play-by-play and no in-season
linescore asset at all.** Probed 2026-09-03:

| Asset | HTTP |
|:--|:--|
| `.../espn_cfb_linescores/linescores_2026.csv.gz` | **404** |
| `.../cfbfastR_cfb_pbp/play_by_play_2026.parquet` | **404** |
| `.../ncaa_mfb_linescore/ncaa_mfb_linescore_2026.csv.gz` | **404** |
| `.../espn_cfb_linescores/linescores_2025.csv.gz` | 200 (28.7 KB gz) |

So `h2h_h1`, `spreads_h1` and `totals_h1` — three of this lab's ten wired
markets — **cannot be settled from cached static assets during the season they
are bet in.** They are `DEFERRED` with the 404s
as the recorded reason, or they come from a live keyed API call, which is a
different architecture. Section 3 argues that choice.

### 1.3 The free priced instrument is not the one the NFL lab has

The NFL lab's first and deepest priced test is the closing spread, total and
both moneylines carried in the nflverse schedule file back to 1999. **The
college schedule file carries no price columns at all.** The nearest free
equivalent is a separate file, and it has a structural break.

`sportsdataverse/cfbfastR-data` → `betting/csv/cfb_line_odds.csv.gz`
(7.05 MB, **1,183,529 rows**, downloaded and analysed 2026-09-03):

| Seasons | Spread rows | Spread rows carrying odds | Games with a priced spread |
|:--|--:|--:|--:|
| 2006–2019 | 416,185 | **416,185** | **10,047** |
| 2020–2025 | 40,286 | **0** | **0** |

| Season | Games with a priced moneyline | Books |
|:--|--:|:--|
| 2021 | 739 | — |
| 2022 | 740 | — |
| 2023 | 795 | — |
| 2024 | 831 | — |
| 2025 | **868** | ESPN Bet, Bovada, DraftKings (+ a `Draft Kings` spelling variant, 128 rows) |

Two facts, both load-bearing:

1. **The modern free instrument is moneyline-only**, 2021–2025, ~3,973 games,
   three books. Spread and total lines exist for those seasons with **no juice
   on a single row**. Assuming −110 to compute an ROI would be fabricating a
   number, which the house rules forbid outright.
2. **The deep free instrument is 2006–2019**, ~10,047 games with a fully
   priced spread across many books — deeper per season than anything buyable
   — and it describes a sport that no longer exists. It predates the transfer
   portal, NIL, the 12-team playoff and three rounds of realignment. It is a
   real instrument and every use of it must carry that sentence.

A walk-forward fit that spans 2019→2020 is fitted across two different
populations of *prices*, not just of teams.

### 1.4 The identity surface is 4x larger and has no abbreviations

`providers/team_names.py` in the NFL lab assumes a closed, one-to-one,
32-entry abbreviation map. In the college schedule feed, **3 of 138 FBS teams
carry an abbreviation at all** (measured 2026-09-03 from the sportsdataverse
release asset). Teams join on full names, and four FBS names carry characters
that break naive uppercasing and matching: `Hawai'i`, `Miami (OH)`,
`San José State`, `Texas A&M`.

Across the full college universe the map is not even one-to-one — `OSU` is
both Ohio State and Ohio State Newark — so a name-keyed map is safe *only* if
its universe is FBS-only, which is exactly the choice that makes every FCS
opponent unresolvable. Section 4 is about that.

### 1.5 `(season, week)` is not a key, and neither is a game count

The 2025 file carries 86 postseason rows, numbered weeks 1, 13 and 14 — and
**all 86 collide with a regular-season `(season, week)`** (verified
2026-09-03). Postseason `week` restarts at 1, so bowl games silently merge
with September.

Worse for any completeness check: the 2026 file today contains **zero
postseason rows** (`season_type` is `regular` for all 888). 2024 had 54, 2025
had 86. The season's true game count is not knowable until December. Any
invariant of the form "a complete schedule has N games" or "names N clubs" is
wrong by construction — FBS membership was 134 / 136 / 138 across 2024 / 2025
/ 2026 and gained two teams this year alone.

### 1.6 The distribution is not the NFL's

- **There are no draws.** NCAA overtime has decided every level game since
  1996, so `h2h_3_way` is deferred with that reason recorded. The NFL market's
  settlement prose ("ties are possible and settle as a push") is simply false
  here.
- **Overtime is a different game**: alternating possessions from the 25, with
  mandatory two-point tries from the second period. It appears in the 2025
  linescore file as periods 5 (90 rows) and 6 (28 rows). A full-game total
  includes that shootout.
- **A half can still end level**, because the overtime rule does not apply to
  it.
- **Whether 3 and 7 are still the key numbers is an open question.** The exact-
  push machinery assumes NFL lumpiness and must be re-measured before it is
  reused.
- **`PRIOR_GAMES = 17.0`** is a whole NFL season of shrinkage. Applied to a
  college team with three games it keeps 15% of the team's own signal against
  forty-point talent gaps, which is not caution — it is an assertion that the
  team is average.

### 1.7 The provider is not one sport key

The Odds API splits college football across `americanfootball_ncaaf`,
`americanfootball_ncaaf_fcs` (created 2026-08-28, essentially no history) and
`americanfootball_ncaaf_championship_winner`. The provider states that FCS
games appeared under the main key *before* the 2026/27 season and under the
separate key from it. So **a historical purchase on `americanfootball_ncaaf`
covering 2020–2025 buys a mixed FBS+FCS pool that the live 2026 fetch is not
drawn from.** `League.provider_sport_key` is one string; it cannot express
that, and the discipline test bans the `americanfootball_` prefix anywhere
else in the tree.

---

## What this lab starts with, that the NFL lab earned the hard way

Every one of these is a defect that cost the NFL or NHL lab real time or real
money. **None of them is rediscovered here. Each is a precondition of the
first commit that touches its area.**

1. **Settlement joins on identity, never on name strings.** `game_id`,
   `home_id`, `away_id` — the columns the feed already carries. Demonstrated
   below: the 2025 linescore join on `(game_id, team_id)` reconciles **1,868
   of 1,868 team-games exactly**. Names are for display only.
2. **One function builds every join key.** `selection_key()` is called by both
   sides of every join and by the fixtures. The NHL lab's join-vocabulary bug
   family reached five members; two hand-built copies of a key are how it
   starts every time.
3. **Every event is matched to its own season, from its own kickoff.** The
   cross-season settlement defect manufactured the NFL lab's largest retracted
   finding. A price row's season is derived from that row's kickoff, never
   from the file it arrived in, and a regression test pins it.
4. **Intervals are clustered by game, never by bet.** The spread, the total
   and both team totals on one game are one afternoon seen four ways. A naive
   binomial interval over correlated bets is narrower than the truth, and a
   narrow interval is exactly how "no demonstrated edge" turns into a claim.
5. **A cumulative, append-only experiment ledger.** A search that runs every
   week is not twelve tests, it is twelve tests a week forever. The correction
   factor grows with the count and the ledger cannot shrink.
6. **No measured number is hardcoded in prose.** Every report renders from its
   run record, and a test fails the build when a document and its report
   disagree. Improving a sentence must never cost a credit spend.
7. **`unrated_opponent` is a named bucket in the accounting identity**, not a
   silent league-average price. Section 4.
8. **The kickoff guard, fail-closed, from day one**, including on TBD and
   unparseable start times. The EPL lab retrofitted its equivalent, which
   means every card before the retrofit was unguarded and unrecheckable.
9. **`DEFERRED_MARKETS` carries a reason for every market not asked for**, so
   "the books do not quote this" and "we never asked" can never look alike.
10. **`retained=None` means unprobed** — not `False`, which would be a
    finding, and not `True`, which would be a guess.
11. **Nothing is allowlisted, and nothing is bet without a human receipt.**
    Claude prepares the evidence bundle and stops. Its honest default is
    *not supported*.

---

## 2. The build order

Each step names what it produces and how you know it worked. Steps 1–6 are the
evidence organ. **No model is fitted until step 7**, and the card makes no
recommendations at any step in this document.

### Step 1 — The settlement source, wired and reconciled *(largely done)*

**Produces.** `data/cfbfastr.py` fetching
`schedules/csv/cfb_schedules_{season}.csv` from `cfbfastR-data`, with
`REQUIRED_COLUMNS` enforced, results read from `home_points`/`away_points`
gated on `completed`, and `home_division`/`away_division` carried through.

**Known to have worked when.** A completed season reconciles: every completed
FBS-involved game has both scores populated, and the count of completed games
in the file matches the count of games whose kickoff has passed. Today: **8 of
8** games played before 2026-09-03 are complete. Cross-checked against the
independent `sportsdataverse-data` release asset — 3,679 rows across all four
divisions, **126 completed** — which agrees exactly on the FBS subset.

### Step 2 — Identity, and the FBS/FCS refusal

**Produces.** A per-season FBS membership set read *from the schedule file*,
never from a constant. `team_names.py` mapping provider names to team **ids**,
with unresolved names returned to the caller and never guessed. `coverage.py`
turning "do we know both these teams?" into a precondition with its own
accounting bucket.

**Known to have worked when.** The 2026 membership set has 138 entries, 2025
has 136, 2024 has 134, all derived. Every one of the 127 FBS-vs-FCS 2026
fixtures lands in `unrated_opponent` and **not** in `no_opinion`. A synthetic
fixture naming a team with no rating raises or refuses; it never prices.
`Hawai'i`, `Miami (OH)`, `San José State` and `Texas A&M` round-trip through
the map unchanged.

### Step 3 — `selection_key()`, the league-date rule, and the kickoff guard

**Produces.** One key function used by both sides of every join. `game_date()`
bucketing by ET, not UTC. A guard that quarantines a selection whose start
time is past, missing, unparseable, **or `start_time_tbd`**.

**Known to have worked when.** Re-bucketing the 2026 schedule moves exactly
**134 games** off their UTC date, and a fixture asserting that count fails if
the rule is ever reverted. A TBD-kickoff fixture is quarantined, with the
quarantine reason distinguishable from "already started". The 86 postseason
rows in the 2025 file do not collide with regular-season rows under the key.

### Step 4 — Odds staging, fail-closed, allowlisting nothing

**Produces.** The provider adapter writing to `data/staging/`, which the card
cannot read. Eligibility per market, keyed `the_odds_api:ncaaf`. A PR gate.
`markets.py` with `DEFERRED_MARKETS` reasons for `h2h_3_way` (no draw exists),
the quarter ladder (not until halves are measured), player props (out of
scope, Cooper, 2026-08-28) and outrights.

**Known to have worked when.** A market with no allowlist entry cannot reach a
card in any test. The first live fetch's per-day spend is recorded and
compared against the derived cap. The registry discipline test passes: no
`americanfootball_` literal outside `leagues.py`.

### Step 5 — The credit cap, derived rather than asserted

**Produces.** `scripts/estimate_credit_cost.py` reading the real 2026 schedule
and the real market registry, writing `data/outputs/credit_cost.md`, and the
cap in `leagues.py` set from its output with the derivation recorded.

**Known to have worked when.** The script reproduces, from the committed
schedule, exactly these figures for the registry as it stands on 2026-09-03:

| | Season total | Worst day (80 games, 2026-09-12) |
|:--|--:|--:|
| Tier 1 (3 bulk + 3 per-event) | 2,838 | **243** |
| Tier 1+2 (3 bulk + 7 per-event) | 6,390 | **563** |

The cap of 4,000 is then either confirmed with that derivation attached or
lowered to a stated multiple of 563. **A number in the registry with no script
behind it is the defect this step exists to close.**

### Step 6 — The forward-evidence organ. This is the product.

**Produces.** Snapshot → settle → report, per kickoff window rather than per
day. Snapshots are never overwritten. Settlement reads the same tables the
historical measurement reads. A game with no result inside the patience window
is recorded `unsettleable` and **counted**, never guessed. Intervals clustered
by game. `data/outputs/ncaaf_forward_evidence.md` saying "no demonstrated
edge" in those words while it is true.

**Known to have worked when.** The accounting identity balances on every run:
`priced = no_opinion + unrated_opponent + below_threshold + unparseable +
ambiguous + bets`. A frozen day re-settled twice produces byte-identical
output. On the first 80-game Saturday, the number of frozen rows and the
number settled are both reported and their difference is explained by name,
not by absence.

**This step ships before the model is good, and if something above it is not
ready, the thing that ships is snapshot-and-settle with a cruder model still.**
Forward evidence cannot be back-dated. Eight games are already gone.

### Step 7 — The first model, deliberately crude, and honest about it

**Produces.** A team model from scores, rest and neutral-site status, fitted
walk-forward on games strictly earlier than the one being priced, with
`PRIOR_GAMES` re-derived for college rather than inherited, and coverage
enforced as a precondition. An explicit, recorded decision on FBS-vs-FCS games
in the fit (section 4), taken through the verdicts door with a measurement
behind it.

**Known to have worked when.** It produces an opinion on FBS-vs-FBS fixtures
and **refuses** on all 127 FBS-vs-FCS ones — 38 of them on 2026-09-05 alone.
The refusals appear as a number in every report. Its fitted score distribution
is shown against the empirical one it claims to describe. It exists to produce an opinion worth freezing, not to
be believed.

### Step 8 — The instruments, before any result is believed

Built here **before** the findings they would kill, because in the NFL lab
every positive result was an artefact and each was killed by an instrument
written *after* the finding it destroyed.

| Instrument | Catches |
|:--|:--|
| Null baseline | A broken harness. Betting every priced selection must lose. |
| Settlement-agreement screen | Settling a different quantity from the one priced. A constant offset replicates perfectly and survives every other check. |
| Price sensitivity | An edge that exists only as the maximum of N quotes, or at one soft book. This matters more here: 2025 free prices come from **three** books. |
| Held-out replication | A result that holds only on the season it was found in. |
| Experiment ledger | The multiplicity of a search that runs every week. |
| Slate coverage | A starved or truncated fetch that looks like an unquoted market. Thresholds re-derived for a 3-game median day. |
| Forward evidence | Everything above, out of sample, at 888 games a season. |

**Known to have worked when.** Each runs on synthetic data with a known
planted defect and finds it. The slate-coverage watchdog does not fire on a
median Tuesday.

### Step 9 — The free priced backtests, in order of honesty

1. **Moneyline, 2021–2025, ~3,973 games, three books in 2025.** The only
   modern free priced test that exists. Reported with the book count beside
   every figure.
2. **Spread and total, 2006–2019, ~10,047 priced games.** Deep, free, and
   about a different era of college football. Every use carries that sentence.
3. **Never a −110 assumption.** 40,286 spread rows and 39,978 total rows from
   2020–2025 carry no odds. They supply line values and never returns.

**Known to have worked when.** The backtest refuses to compute an ROI on any
row with no price, and the count of refused rows is printed.

### Step 10 — The retention probe, then a costed purchase

College retention is **unknown**, not absent. Every market carries
`retained=None`. The NFL's 7,280-credit probe measured `americanfootball_nfl`
and transfers nothing: Group-of-Five books quote far thinner ladders on a
Tuesday-night MAC game than any book quotes on any NFL game.

**Produces.** A probe on a stratified sample of past FBS events, then a
purchase sized from what it finds and re-costed before it is spent. Both are
credit spends and therefore Cooper's, with the number agreed first.

**Known to have worked when.** Every conclusion rolls up to the *market*, not
the provider key — the NFL probe found three featured keys returning nothing
while their alternate ladders had them, and the reverse case in the same data.
The report re-renders from the run record without re-spending.

### Step 11 — Measurement discipline, then stop

Family-wise correction across every market tested, reported beside the raw
figure. Minimum samples declared in advance. Replication on held-out seasons.
Then the allowlist evidence bundle, per market, with its honest default of
**not supported**. Claude prepares all of it and stops. **Cooper signs or does
not, and nothing is bet without that receipt.**

---

## 3. The settlement source: the decision, argued and costed

This was the largest open question and it splits cleanly in two.

### 3.1 Final score, moneyline, spread, total, team total — decided

**Source: `cfbfastR-data`, `schedules/csv/cfb_schedules_{season}.csv`, over
HTTPS from `raw.githubusercontent.com`.** No key, no quota, no rate limit,
re-fetchable, auditable, and it carries `home_division`/`away_division` per
game — which is what lets this lab decline a fixture rather than guess at it.

The alternative front door, `sportsdataverse-data` release assets at
`releases/download/cfb_schedules/cfb_schedules_{season}.csv.gz`, is the exact
nflverse URL shape on the same host and is **also** fresh (last built
2026-09-02; 3,679 rows for 2026 across fbs/fcs/ii/iii; 126 completed as of
2026-09-03). It carries `home_abbreviation`, `away_abbreviation`, `status`,
`fbs_game` and the playoff bracket columns that the committed CSV lacks.

**Both were fetched and compared on 2026-09-03. On the FBS subset they agree
exactly** — same 761 FBS-vs-FBS and 127 FBS-vs-FCS games, same 8 completed.
The committed CSV is the source of record because it is FBS-scoped already and
its column set is the one the adapter validates; **the release asset is kept
as the reconciliation source**, and a disagreement between them is a finding,
not a fallback.

**Cost: zero credits, zero keys.**

### 3.2 First half — not decided by default, decided deliberately

There is no free cached first-half source for the season in progress. Three
candidates, all probed 2026-09-03:

| Option | In-season? | Key | Quota | Licence | Verdict |
|:--|:--|:--|:--|:--|:--|
| Release linescore / pbp assets | **No — 2026 assets 404** | none | none | `cfbfastR-data` has **no licence** (`license: null`); `sportsdataverse-data` is MIT, a code licence on a data repo | Backtest only |
| CollegeFootballData `/games` | Yes (`homeLineScores`/`awayLineScores`) | **Bearer token** | **1,000 calls/month free** | Terms permit commercial and betting use | The only real in-season option |
| ESPN scoreboard (keyless) | Yes | none | none stated | **No published terms or licence** | Diagnostic only |

**The arithmetic is not the obstacle.** One `/games?year=&week=&classification=fbs`
call per week is roughly 20 calls a season; re-polling daily across 58 game
days is roughly 120. Against 1,000 free calls a month, first-half settlement
is affordable several times over. What it costs is architectural:

- a **second secret** in CI, where the existing secrets guard recognises only
  the 32-hex Odds API shape;
- a **live network call inside the settlement path**, which the "caching is a
  correctness rule" design exists to keep out;
- and a supply chain where the free mirror the backtest depends on is a bulk
  redistribution of CFBD data that CFBD's own terms prohibit — so that door
  can close on someone else's decision, mid-season, with no notice.

**ESPN is rejected as a source of record on two grounds.** It has no licence,
and it silently truncates. Re-probed 2026-09-03 on
`scoreboard?dates=20250906&groups=80`, varying only `limit`:

| `limit` | Events returned |
|--:|--:|
| *(omitted)* | 80 |
| 25 | **50** |
| 50 | 80 |
| 100 | 80 |
| 200 | 80 |
| 300 | 80 |
| 1000 | **25** |

All seven were HTTP 200 with no error and no warning. A fetcher passing a
generous `limit` would freeze 25 of 80 games and report a healthy slate. That
is this lab's own silent-shortfall failure family, pre-loaded.

**The decision.** The `*_h1` markets stay **`DEFERRED`, with the three 404s as
the recorded reason**, until either (a) a 2026 linescore asset appears, or (b)
Cooper approves a CFBD key, at which point `/games` becomes the half source
and the live-call exception is written into the adapter's docstring rather
than discovered in it. **A market that cannot be settled is never priced** —
the halves sit unpriced rather than accumulating unsettleable rows.

### 3.3 Why the half arithmetic is trusted when it does become available

The 2025 linescore asset was downloaded and joined to the 2025 schedule on
2026-09-03, **on `(game_id, team_id)` — identity, not names**:

- 7,782 linescore rows, periods 1–4 at 1,916 team-games each, period 5 at 90
  and period 6 at 28 (overtime);
- joined to **934** completed FBS-involved 2025 games;
- **1,868 of 1,868 team-games** sum exactly to the recorded final score;
- **0 mismatches, 0 missing.**

So first half = period 1 + period 2 is arithmetically safe. **The constraint is
publication timing, not data quality** — and that difference must be stated
everywhere it matters, because it means a backtest can settle halves exactly
while the forward ledger cannot.

### 3.4 What history costs, and the one place college is cheaper than the NFL

Derived 2026-09-03 from the committed schedules and this lab's own registry.

**Per-event historical** (10x, one snapshot per event, 1 region, plus one
listing per game day, against 888 events / 58 days):

| | Credits |
|:--|--:|
| Tier 1 (3 per-event keys) | **26,698** |
| Tier 1+2 (7 per-event keys) | **62,218** |

**Slate-level historical** is billed flat — `10 × markets × regions`,
regardless of how many games the snapshot returns. One whole-slate snapshot of
`h2h`+`spreads`+`totals` costs **30 credits whether it holds 16 games or 128.**
Counting distinct `(day, ET kickoff hour)` slots so every kickoff window is
caught:

| Season | Kickoff slots | Cost, one snapshot per slot |
|:--|--:|--:|
| 2024 | 277 | **8,310** |
| 2025 | 276 | **8,280** |

Compare: buying the same three markets per event for 2025 is 10 × 3 × 934 =
**28,020**. The slate endpoint is **3.4x cheaper for the identical data**, and
because it is flat-billed, the FCS contamination in the pre-2026
`americanfootball_ncaaf` pool **costs nothing** rather than spending 10x
credits per unsettleable FCS game.

**So the purchase recommendation is the reverse of the NFL's.** Buy featured
team markets slate-wise and deep — six seasons at one snapshot per kickoff slot
is roughly 50,000 credits, half a month of quota — and buy the per-event
ladders, team totals and halves only for the seasons and slates a probe says
are actually quoted. The NFL lab's whole tier-1 season cost ~99,000 credits;
this is a fraction of it for a longer, wider price history.

**None of this is approved.** Every credit spend is Cooper's, with the number
agreed first.

---

## 4. The FBS/FCS problem, and how the lab refuses rather than guesses

### 4.1 The defect, in two lines of inherited code

`models/scoring.py` in the NFL lab reads `self.offence.get(team, 0.0)` and
`self.defence.get(opponent, 0.0)`. **A team with no rating is not an error and
not a missing value — it is assigned exactly zero, which by construction means
exactly league average.**

In the NFL that is nearly unreachable: 32 clubs, all rated, every week. In
college it is the normal case for weeks 1–3 and **permanent for every FCS
opponent**. There are **127 such games in 2026 — 14.3% of the slate** — and
books quote them. The failure is silent: the lab would price Alabama against a
two-win FCS side at roughly a field goal while the market is −45, produce
plausible numbers, raise no error, and write no `no_opinion` row.

### 4.2 How this lab refuses

**Coverage is a precondition, checked before pricing.** Both sides of a fixture
must be present in `ratings.offence` and `ratings.defence` with at least
`MINIMUM_RATED_GAMES` behind them. A fixture that fails lands in
`unrated_opponent`, **a distinct named bucket in the accounting identity** —
never in `no_opinion`.

The distinction is the whole point. `no_opinion` says *this lab looked and had
nothing to say*. `unrated_opponent` says *this lab does not know these teams*.
On 2026-09-05 — the first full Saturday, 68 games — **38 of them are
FBS-vs-FCS**. Those 38 refusals must be visible as a number rather than as an
absence, and an absence is exactly what the inherited code would produce.

The refusal is also **classification-aware and happens before freezing, never
at settlement**. If an FCS opponent were merely dropped at settlement time, the
day would still be stamped into the ledger and that day's return computed on
the FBS-vs-FBS subset only — a selection bias on the season's most important
slate, arriving through the day-as-unit rule.

### 4.3 The second-order problem, which has no default answer

Whatever the lab does about FBS-vs-FCS games **in the ratings fit** is wrong by
default:

- **Include them**, and every FBS offence rating is inflated by a 63–3 win over
  an opponent the model cannot rate, poisoning the fit for all 138 teams for
  the whole season. This is worse than the pricing bug, because it corrupts
  every game rather than 127 of them.
- **Exclude them**, and every team that opened against an FCS opponent carries
  one fewer rated game, so its weeks 2–3 rating sits nearer league average —
  for exactly the teams that scheduled a cupcake, which is not random.

**Neither is chosen in a docstring.** It goes through the verdicts door as a
recorded decision with a measurement behind it, and the alternative — an
explicit FCS-strength term fitted as its own parameter — is measured against
both, on the priced test, not on calibration.

### 4.4 Why the identity map must carry classification

An FBS-only abbreviation map can be made one-to-one — ESPN abbreviations are
unique across 138 of 138 FBS teams (`docs/what_a_rename_would_have_broken.md`)
— but the schedule feed supplies an abbreviation for only **3 of 138**, so that
map is built and maintained here rather than read. Across the ~760 college
football teams it is not one-to-one at all: `OSU` is Ohio State and Ohio State
Newark; the locations `Charlotte` and `Troy` each collide with a non-FBS
school. So a name-keyed map is safe **only** on an FBS-only universe.

Therefore: the registry carries **classification alongside the name**, the club
set means "FBS members *this season*" and is keyed by season, and it is read
from the schedule file rather than written down. Membership moved 134 → 136 →
138 across three seasons; a constant would be wrong in at least one direction
every July.

**And the results feed must still include FCS opponents.** An FBS-only results
fetch means every FBS-vs-FCS game resolves to nothing, and after the patience
window every frozen row on it is recorded `UNSETTLEABLE`. The exclusion belongs
at pricing time, on a known classification — not at settlement, as a lookup
that happens to miss.

---

## 5. What is ported unchanged, and what must be rewritten

### Ported essentially unchanged

These are sport-agnostic and were earned. They carry over because the standards
do not change when the sport does.

| Module / rule | Why it survives |
|:--|:--|
| `leagues.py` — the registry as the only place a league fact lives | A portability device. It is what made this port possible at all. |
| `selection.py` / `selection_key()` and the outcome vocabulary | The join-vocabulary bug family is not a football problem. |
| `experiment_ledger.py` | Multiplicity arithmetic is sport-independent. Append-only, and it cannot shrink. |
| `kickoff.py` — the fail-closed start-time guard | Unchanged in logic; **extended** to treat `start_time_tbd` as unconfirmed. |
| `staging_provider_policy.py` — allowlist nothing, fail closed, PR gate | Unchanged. |
| `verdicts.py` — the recorded-decision door | Unchanged. |
| The forward-evidence three-stage shape: freeze, settle, never reprice | Unchanged in shape. Its **cadence** is rewritten (below). |
| The reports' house vocabulary: sample size beside every number; "no demonstrated edge" in those words; calibration can rule out and never rule in; where a priced test exists, it decides | Unchanged, and non-negotiable. |
| `test_no_secrets_committed.py`, `test_contract_strings.py`, `test_league_registry_is_the_only_place.py` | Unchanged, except the secrets guard must learn a second key shape if CFBD is approved. |

### Must be rewritten, not renamed

| NFL component | Why a rename fails | What replaces it |
|:--|:--|:--|
| `data/nflverse.py` | `ALLOWED_HOST = "github.com"` rejects `raw.githubusercontent.com`, where the schedule and the free price file both live. Only one feed has a college analogue at all — `pbp`, `player_stats`, `rosters`, `weekly_rosters`, `depth_charts`, `injuries`, `snap_counts` have none in season. | `data/cfbfastr.py`, already written, with its own host allowlist and `REQUIRED_COLUMNS`. |
| `is_provisional()` | Encodes "NFL corrections land Mon–Wed, Thursday's copy is clean". College latency runs the other way: a Saturday-night slate settles no sooner than Sunday morning UTC. | A college-measured staleness rule, with the observed publication lag recorded rather than assumed. |
| `season.expected_clubs()` / `schedule_cache_is_complete()` | A fixed club count is wrong by construction under realignment (134/136/138), and the 2026 file has no postseason rows yet, so a game count is unknowable mid-season. | Per-season membership derived from the schedule, and a completeness check that reasons about *coverage of played dates*, not totals. |
| `known_regular_season_games()` | Matches `game_type == "REG"`, reads `gameday`, uppercases abbreviations. College uses `season_type == "regular"`, an ISO-8601 UTC `start_date`, and has no usable abbreviation column. `(season, week)` collides — all 86 of 2025's postseason rows sit on a regular-season week number. | A screen keyed on `game_id`, with `season_type` read explicitly. |
| `providers/team_names.py` | 32 entries, closed, one-to-one, abbreviation-keyed. | Name→id resolution, FBS-only universe, classification carried, per season, unresolved names returned to the caller. |
| `models/scoring.py` `.get(team, 0.0)` | Silently prices an unknown team as league average. | `coverage.py` as a precondition, `unrated_opponent` in the identity, `PRIOR_GAMES` re-derived. |
| `daily_credit_cap = 1_800` | Derived from a 16-game slate. | Derived from the 80-game slate and the real registry: **563** at tier 1+2 today. |
| The one-freeze-per-day ledger cadence; `THIN_SNAPSHOT_ROWS = 25`; `SETTLEMENT_GRACE_DAYS = 5` | Calibrated on 13–16 games in three windows. A college median day is 3 games; Saturdays run 11:00–23:00 ET. | Freeze per kickoff window; thresholds re-derived from the college day distribution. |
| `moneyline_3_way` and the moneyline settlement prose | No draw exists in college. The prose ("ties settle as a push") is false. | `h2h_3_way` deferred with that reason recorded in `markets.py`. |
| The `*_h1` / `*_q*` settlement path | Wired to nflverse `pbp` filtered on `qtr`. No college pbp or linescore for the season in progress. | Deferred with the 404s recorded, or CFBD `/games` on Cooper's approval. Section 3.2. |
| The NFL's closing-line backtest as instrument #1 | The college schedule file has no price columns; 2020–2025 spread and total rows carry zero odds. | Moneyline 2021–2025 (~3,973 games, 3 books) and spread/total 2006–2019 (~10,047 games, different era), both labelled. |
| The NFL retention answer | Measured on `americanfootball_nfl`. | `retained=None` on every market until a college probe runs. |
| Key-number push machinery assuming 3 and 7 | College scoring lumpiness is unmeasured here. | Re-measure before reuse. |

---

## 6. What is not negotiable

- **Nothing is allowlisted. Nothing is bet.** Claude prepares the evidence
  bundle and stops; its honest default is *not supported*; Cooper signs or does
  not.
- **Every credit spend is Cooper's**, with the number agreed before it is
  spent.
- **A number without a sample size is not a result.**
- **An interval that includes zero means "no demonstrated edge"** — those exact
  words, not "promising".
- **No claim in this repository may suggest an edge exists before a
  measurement says so.** This document makes none.

The one thing that is certain: every claim this lab will ever make about
college football rests on evidence that does not exist yet. The first of it is
being played tonight, which is why the evidence organ is steps 1–6 and the
model is step 7.
