# Pre-registration: does a rating that learns from last night beat the price?

**Written 2026-10-09. Nothing below has been tested. No slope in this study has
been computed.** Committed before the fit runs, so the directions, the
constants and the threshold for shipping are on the record before any of them
could be graded against a result.

## Why this is a new question and not a re-run of step 5

Cooper asked on 2026-10-09 whether the model learns from the games played each
night, from who starts and from who is hurt. Today it does not: the card takes
its centre from the books' consensus line (`reports/card_pricing.py`,
`anchor_margin` / `anchor_total`) and its shape from seasons strictly before
this one (`models/shapes.py`, `fit(before_season=...)`). Nothing team-specific
enters, and nothing updates inside a season.

Step 5 and the opener study already asked whether this lab's ratings correct
the price, and both read **no demonstrated edge** (`data/outputs/
ratings_residual.md`, slope -0.0196, n = 3,124; `data/outputs/
opener_study.md`). But the ratings those tests used weighted **every past game
equally** — a game from three Septembers ago counted as much as last Saturday —
and let a 63-point blowout count 63 points. That rating cannot see how a team is
playing *now*, which is exactly what Cooper is asking about. A recency-weighted
rating with a margin cap is a different estimator, so it is a new hypothesis and
it is paid for in the ledger.

The prior is unfavourable and is stated so: two tests of ratings against this
price have already returned nulls, and the sibling NFL lab found the same. The
market watches last Saturday too.

## The estimator, fixed now

`src/ncaaf_betting_lab/models/form.py`.

* **Games:** rateable FBS-vs-FBS games with a final score, from the cfbfastR
  schedule the card already fetches every run.
* **Fit:** weighted ridge least squares of capped margin on home and away team
  indicators plus a home-field term (zero on neutral sites).
* **Recency:** each game weighs `0.5 ** (age / HALF_LIFE_WEEKS)`, with
  `HALF_LIFE_WEEKS = 6`. Age runs on a season clock: weeks since the game
  inside a season, plus `OFFSEASON_WEEKS = 8` for each off-season crossed, so a
  summer counts as eight weeks rather than thirty-six and last season's final
  game still carries about a third of the weight of last night's at week 1.
* **Margin cap:** `MARGIN_CAP = 28` points either way.
* **Ridge:** `RIDGE = 3.0` on team ratings, none on home field — the same as
  step 5.
* **Walk-forward:** each game is priced from games that kicked off on an
  earlier calendar day only. Fitted once per game day, which is what a nightly
  update is. No week is priced with fewer than `MINIMUM_HISTORY = 300` games.

None of these four constants will be tuned. A second set of constants would be
a new ledger entry.

## The starter signal, fixed now

`src/ncaaf_betting_lab/data/starters.py`, from cfbfastR's free play-level
`player_stats_{season}.csv` (2021 onward, updated through the current season).

* A **dropback** is a play carrying a completion, incompletion, interception
  thrown or sack taken, credited to that player and the `team` column.
* A game's **starter** for a team is the player with the most dropbacks.
* A team's **incumbent** before a game is the player who started the most of
  its earlier games this season, ties going to the more recent.
* **`qb_changed`** is 1 when the team has at least two earlier games this season
  and the starter of its most recent one is not its incumbent. It is knowable
  before kickoff: it reads only finished games.

What it is not: a confirmed starter for the coming game. No free source names
one. A flag means "a different quarterback took most of the snaps last time
out", which is the closest pre-kickoff fact this data carries.

## The hypotheses — three, each with a direction

Seasons 2022-2025 priced, 2021 as history only, as in step 5. Residual is
`margin - (-close_consensus)` (or `-open_consensus`), sign conventions exactly as
`docs/preregistered_opener_study.md` section 0.1 verified them. Standard errors
clustered by `(season, season_type, week)`.

| Ledger name | Regression | Registered direction |
|:---|:---|:---|
| `form-ratings-vs-close` | close residual on `form margin - close implied` | **positive** |
| `form-ratings-vs-open` | open residual on `form margin - open implied` | **positive** |
| `qb-change-vs-close` | close residual on `qb_changed(home) - qb_changed(away)` | **negative** (the market under-reacts to a starter change) |

`form-ratings-vs-close` is the headline. The card runs between the open and the
close, so the open arm is reported beside it, not instead of it.

**Correction.** The ledger stood at 92 distinct hypotheses when this was
written. These three take it to 95, and every interval here is quoted at the
Bonferroni critical value for 95, pinned as a constant so a later ledger entry
cannot silently move it.

**What pays.** For the ratings, step 5's rule: a slope of
`1.5 / (1.28 * sd(disagreement))`, the slope at which betting the top decile of
disagreement clears a -110 price. For the starter flag: a coefficient of
**-1.5 points** or beyond.

## What would put either one into the price

Only all three of these, decided now:

1. The corrected interval excludes zero **on the registered side**.
2. The point estimate on **2025 alone** has the registered sign.
3. The detectable floor at 80% power is at or below what pays, so the design
   could have seen it.

Short of that, the rating and the flag go on the card as **context** beside the
price — what the lab's nightly rating thinks, and whose quarterback changed —
and the probabilities stay anchored on the consensus line. An interval spanning
zero is reported as **no demonstrated edge**, in those words, and is not
re-narrated afterwards.

## What this cannot reach

**Injuries and resting players.** No free, structured college availability feed
exists. The SEC files availability reports from the Wednesday before a
conference game through 90 minutes before kickoff, the Big Ten files two hours
before, and the College Football Playoff has required them since 2025; the ACC,
Big 12 and Group of Five have no league-wide mandate. Those reports are web
pages and PDFs, not a data file, and none of them has a history this lab could
test against. Commercial feeds exist and cost money, which is Cooper's decision
with a number in front of him, not this study's.
