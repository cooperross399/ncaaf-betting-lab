# Pre-registration: does the OPENING line leave anything on the table?

**Written 2026-09-05. Nothing below has been tested. No slope in this study has
been computed.** This file exists so that the directions, the statistics, the
segment definitions and the thresholds are on the record before any of them
could be graded against a result.

Five instruments have now been run against the **closing** line and every one
reads *no demonstrated edge*: margin shape, implied dispersion, line movement as
a detector, book-versus-consensus outlier betting, and this lab's own
walk-forward ratings as a residual (`data/outputs/ratings_residual.md`, slope
-0.0196 on n = 3,124 games, corrected interval [-0.1369, +0.0978]). The close is
the sharpest number the feed carries. **This study asks a different question:
whether the number the market posts *first* is softer than the one it settles
on.**

---

## 0. The ground this stands on, measured before anything was registered

### 0.1 Sign conventions, verified by inspection

Established by pulling four real fixtures back to the raw feed and to the
schedule file. The definitions are:

| Field | Meaning, verified | Direction |
|:---|:---|:---|
| `margin` | `home_points - away_points` from the schedule | positive = home won |
| `close_consensus` (spread) | the **HOME handicap** at close | negative = home favoured |
| `open_consensus` (spread) | the **HOME handicap** at open — *same convention* | negative = home favoured |
| `line_move` (spread) | `close_consensus - open_consensus`, exact on **3,857 of 3,857** rows | **positive = the home handicap ROSE = home got more points = the market moved TOWARD THE AWAY TEAM** |
| `close_consensus` (total) | the total itself, not a handicap | no sign flip |

The price's own forecast of the home margin is **`-close_consensus`** (and
`-open_consensus` at the opener). Whole-table confirmation, n stated on each:

* `corr(-close_consensus, margin) = +0.6580`, n = 3,864. The inverted reading
  gives `-0.6580` — a wrong sign is not subtle here, but it is silent.
* `mean(margin - (-close_consensus)) = +0.0976` points, n = 3,864. The inverted
  reading gives **+8.4008** points of fictitious bias.
* `corr(-open_consensus, margin) = +0.6500`, n = 3,857;
  `mean(margin - (-open_consensus)) = +0.0048` points, n = 3,857. The opener
  carries the same convention as the close.
* Home teams with a **negative** `close_consensus` won outright **75.0%**
  (n = 2,394); with a **positive** one, **31.1%** (n = 1,463); 7 games closed
  pick'em. A negative home handicap is the home favourite.
* `line_move > 0` on n = 1,754 spread games, `< 0` on n = 1,601, `== 0` on
  n = 502.

**The one-row-per-side trap was re-confirmed, not assumed.** Every fixture
inspected carries both the home row and the away row in the raw feed, with equal
and opposite numbers; the median across both sides is **+0.00** on every one of
the four. `scripts/build_line_table.py` filters to `abbr == home_team` before
taking a median, which is why the table is not a column of pick'ems.

### 0.2 The ledger, before this study

Read from `data/outputs/experiment_ledger.json` via
`experiment_ledger.correction_factor()`:

| | Count | Bonferroni factor | Critical value |
|:---|---:|---:|---:|
| **Before this study** | **78** | **x1.7417** | **3.4136** |
| After this study records its 4 | 82 | **x1.7486** | **3.4272** |

By search: steps-2-to-5 66, margin-architecture 5, margin-shape 4,
ratings-residual 3. All 78 entries are distinct keys; nothing is double-counted.

**Every interval in this study will be quoted at the critical value 3.4272**,
not 1.96 and not 3.4136. The lab's established convention (see
`scripts/record_step5_and_backfill_ledger.py`, which recorded Step 5's three
hypotheses and then reported them at the inclusive count of 78) is that a study
pays for its own hypotheses. Four hypotheses is the whole budget; there is no
sweep, because a sweep would buy a wider correction than any finding here could
survive.

### 0.3 The data's shape

`data/processed/line_table.csv`, `game_id` read as `str`:

| Figure | Value |
|:---|---:|
| Rows | 7,728 |
| Distinct games | 3,864 (spread 3,864 + total 3,864) |
| Seasons | 2021 (732), 2022 (734), 2023 (792), 2024 (798), 2025 (808) |
| Weeks | 1–16 |
| `(season, week)` cluster cells | 77 (median 53 games per week, min 1, max 94) |
| `open_consensus` coverage | 7,719 / 7,728 = **99.8835%** (spread 3,857/3,864; total 3,862/3,864) |
| `line_move` coverage | 7,719 / 7,728 = 99.8835% |
| Median `books` | **3** (mean 3.377, min 1, max 5, n = 7,728) |
| `books` distribution | 1: 25, 2: 409, 3: 4,267, 4: 2,683, 5: 344 |
| **sd(`line_move`), spread** | **2.1264 pts** (n = 3,857; mean +0.1239, median 0.00, mean abs 1.436, 13.0% zero) |
| **sd(`line_move`), total** | **2.1772 pts** (n = 3,862; mean -0.4244, median -0.50, mean abs 1.669, 8.6% zero) |
| sd(`close_consensus`), spread | 13.4291 (n = 3,864); sd(`open_consensus`) 13.1939 (n = 3,857) |
| sd(`margin`) | 20.3053 (n = 3,864) |
| Median close_max − close_min, spread | 0.50 pts (n = 3,864) |

The nine rows with no opener are all 2022: seven spread
(401403964, 401404026, 401404144, 401405148, 401415272, 401426384, 401426386)
and two total (401404048, 401426618). **A missing price stays missing.** They
are dropped from any test that needs an opener, and the n is quoted after the
drop, never before.

**The line moves by a standard deviation of 2.13 points on the spread.** That is
the entire size of the thing this study is measuring, against a residual whose
standard deviation is 20.3. Nothing here can be large.

---

## 1. The four hypotheses, with directions fixed

Common definitions, in **home-margin space** throughout:

```
forecast_open  = -open_consensus          # the opener's forecast of home margin
forecast_close = -close_consensus         # the close's forecast of home margin
e_open  = margin - forecast_open          # the opener's error
e_close = margin - forecast_close         # the close's error
disagree_open = rating_margin - forecast_open   # ratings minus the OPENER
resid_open    = e_open                          # the opener's error, again
market_move   = forecast_close - forecast_open = -line_move
```

`rating_margin` comes from `ratings_residual.fit_ratings` — least squares on
home/away indicators plus a home-field term, **fitted strictly on earlier
games**, `RIDGE = 3.0`, `MINIMUM_HISTORY = 300`. Every slope comes from
`ratings_residual.regress`, which is OLS with a **cluster-robust standard error
grouped by `(season, week)`**. Both are reused as they stand; neither is
rewritten for this study.

**Sample.** H1–H3 run on the walk-forward priced set, which begins in 2022
because 2021 is burned as history. The prior study priced **3,124 games** on
this design; up to 7 of those lose their opener, so the analysis sample is **at
most 3,124 and expected near 3,117. The exact n is measured at run time and
quoted beside every number.** The positive control does not need ratings and
runs on all **3,857** spread games that have an opener.

**Every interval is quoted at the corrected critical value 3.4272.** Every null
carries its **detectable-edge floor**, `(3.4272 + 0.8416) x SE = 4.2688 x SE`,
the smallest effect the design could see at 80% power at that critical value.
**A null whose floor sits above its own threshold is an absence, not a finding,
and will be reported in those words.**

**The profitability threshold is a formula, fixed now, not a number chosen
later.** Bet the top decile of disagreement — a cutoff of `1.28 x sd(disagree)`
— and a -110 price needs roughly 1.5 points of true edge to clear the vig, so

```
profitable_slope = 1.5 / (1.28 x sd(disagree_open))
```

This is the same arithmetic that produced the 0.143 in `ratings_residual.py`
(1.5 / (1.28 x 8.19) = 0.1431). The standard deviation it takes is measured on
this study's own sample against the **opener**, which is a different number from
8.19 and is not yet known. The formula is what is registered; the value it
returns will be reported beside the result.

---

### control-close-beats-open — POSITIVE CONTROL

> Does the close beat the open at all?

* **Statistic.** `Δ = mean(e_open²) - mean(e_close²)` over spread games with an
  opener, with a standard error clustered by `(season, week)`.
* **Direction, fixed in advance: POSITIVE.** The close must be the better
  forecast. Hours of money and information separate the two prices.
* **Threshold.** The control **passes** only if the corrected interval on Δ
  **excludes zero on the positive side** at critical value 3.4272.
* **What a failure means.** If the control fails, **every null in H1–H3 is
  uninterpretable** and will be reported as an absence: an instrument that
  cannot detect the one effect known to exist here has not measured anything.
  This is reported first, before any other result, and it is not skipped if it
  is inconvenient.
* **What a pass does NOT mean.** A pass says the closing number is better than
  the opening number. It says nothing about whether the gap is *bettable*, and
  it will not be quoted as an edge.
* n at run time: expected 3,857.

### ratings-vs-open — H1

> Does rating-vs-OPEN disagreement predict the line move?

* **Statistic.** `regress(market_move on disagree_open)`, clustered by
  `(season, week)`. Note `market_move = -line_move`: a positive coefficient
  means the market moved **toward** the ratings.
* **Direction, fixed in advance: POSITIVE.** If the ratings hold information the
  opener lacked and the market later finds it, the line moves toward the
  ratings. A slope of 1.0 would mean the market converges on the ratings
  entirely by close; a slope of 0 means the ratings say nothing about where the
  number goes.
* **Threshold.** Zero-exclusion at critical value 3.4272.
* **There is no profitability threshold here, deliberately.** This data carries
  no price *on the move*. **An interval that excludes zero here demonstrates
  that the ratings anticipate the market's own revision — it does NOT
  demonstrate an edge and must not be written up as one.** It is a mechanism
  test.
* n at run time: at most 3,124, expected near 3,117.

### ratings-vs-open-outcome — H2

> Does rating-vs-OPEN disagreement predict the RESULT?

* **Statistic.** `regress(resid_open on disagree_open)`, clustered by
  `(season, week)`. This is the Step 5 instrument with the **opener** in place
  of the close.
* **Direction, fixed in advance: POSITIVE.** A positive slope means the ratings
  carry information the opener had not yet priced.
* **Thresholds, both reported.**
  1. Zero-exclusion at critical value 3.4272 — "no demonstrated edge" otherwise,
     in those words.
  2. `profitable_slope = 1.5 / (1.28 x sd(disagree_open))` — whether the
     interval's upper bound clears what a paying strategy needs, and whether the
     detectable floor `4.2688 x SE` sits below it. Against the **close** this
     threshold was 0.143 and the design's floor was 0.146 — it narrowly failed.
     **The same failure is likely here and will be stated plainly if it
     happens.**
* **Registered limitation.** Betting an opener requires being at the book when
  it posts, at whatever limit is offered then. Nothing measured here
  demonstrates that such a bet was available or fillable. This is a measurement,
  not a strategy, and no bet will be placed or automated.
* n at run time: at most 3,124, expected near 3,117.

### segment-heterogeneity — H3

> Is the opener softer in thin segments?

* **Segment definition, fixed in advance, taken literally: thinness is the
  number of books quoting the game.**
  * **thin = `books <= 2`**
  * **thick = `books >= 4`**
  * `books == 3` is the median and is **excluded from both arms** as the tie.
    Fixed now so it cannot be moved later.
* **Statistic.** Run the H2 regression separately in each arm with the same
  `regress`, and report `Δ = slope_thin - slope_thick` with the two
  cluster-robust standard errors added in quadrature.
* **Direction, fixed in advance: POSITIVE.** A softer opener where few books
  quote means the ratings' disagreement pays off *more* there.
* **Threshold.** Zero-exclusion on Δ at critical value 3.4272, plus the
  `profitable_slope` formula applied to the thin arm's own slope and its own
  `sd(disagree_open)`.
* **Pre-declared, before any result: this test is expected to return an absence
  rather than a null.** Measured now, in the walk-forward window (2022–2025) and
  on spread games with an opener: the thin arm holds **162 games spread over
  only 25 `(season, week)` clusters** (2022: 11, 2023: 83, 2024: 21, 2025: 47),
  against **776 games** in the thick arm. Two consequences are registered here
  so they cannot be discovered later and presented as insight:
  1. A 162-game arm has a standard error roughly **4.4x** the full sample's, so
     its detectable floor will land far above any threshold that would pay.
     **A null from this arm is an absence, not a finding.**
  2. **Twenty-five clusters is below the 30–50 a cluster-robust standard error
     needs to be trustworthy.** The interval on Δ is itself uncertain, and it
     will be reported with that caveat attached rather than quoted clean.
* **No fallback definition is registered.** Better-powered proxies for thinness
  exist in this table — book disagreement at close (`close_max - close_min >= 1`
  splits 1,107 against 1,241) and early-season weeks (1,154 against 2,703). Both
  were measured while writing this file and **neither is being adopted**, because
  swapping the definition after seeing `books <= 2` fail is a second look at the
  same question. If one is ever run it is a **new ledger entry** and the
  correction is re-derived.

---

## 2. The correction that will be applied

| | Count | Factor | Critical value |
|:---|---:|---:|---:|
| Ledger before | 78 | x1.7417 | 3.4136 |
| **This study's four hypotheses** | **+4** | | |
| **Ledger after — what every interval here is quoted at** | **82** | **x1.7486** | **3.4272** |

Detectable-edge floor at that critical value: **`4.2688 x SE`** (80% power,
`z = 0.8416`).

The four entries are recorded under the search name **`opener-study`** with
seasons `(2021, 2022, 2023, 2024, 2025)` and names
`control-close-beats-open`, `ratings-vs-open`, `ratings-vs-open-outcome`,
`segment-heterogeneity`. The ledger is append-only and enforced twice; recording
them raises the bar for everything this lab tests afterwards, which is the
intended cost.

## 3. Standing rules this study runs under

* Never fabricate a price, a line, a result or a status. **A missing price stays
  missing** — the nine rows without an opener are dropped and the n is quoted
  after the drop.
* **The sample size is stated beside every measured number.** A number without
  an n is not a result.
* **An interval that includes zero means "no demonstrated edge"** — those exact
  words, never "promising" or "directionally encouraging". And "no demonstrated
  edge" is not "ruled out"; those are separate claims made separately.
* **Every null carries its detectable-edge floor.** A null from an underpowered
  design is an absence, not a finding, and saying so is mandatory.
* **Walk-forward only.** Anything fitted on a game uses strictly earlier games.
* **Never pool leagues.** NCAAF alone. No NFL figure is evidence about anything
  here.
* **Cluster by `(season, week)`.** One model prices a whole week and its errors
  move together.
* **No bet is placed and none is automated.** This is measurement.

## 4. What could still go wrong, registered as a risk rather than discovered as a surprise

1. **The consensus opener is a median across books whose opening prices arrive at
   different times, and 34 books' worth of `opening_lines` are missing far more
   often than closing ones.** `open_consensus` is a median of whatever opened,
   not a single book's first number at a single moment. Any "opener" result is a
   result about that composite.
2. **`books` counts books present in the feed for the game, not books quoting at
   the moment of open.** It is a proxy for thinness, and H3's segments inherit
   that looseness.
3. **The line move is small — sd 2.13 points on the spread, n = 3,857 — and 13.0%
   of games do not move at all.** H1 is asking a small quantity to be predicted.
4. **The ledger's Step 5 entries quote *nominal* intervals** (e.g. "CI [-0.0869,
   +0.0478]") while `ratings_residual.md` quotes the *corrected* ones
   ([-0.1369, +0.0978]) for the same fit. The two are not in conflict, but a
   later reader could take the ledger's narrower figure for the corrected one.
   Noted here; not edited, because the ledger is append-only.
5. **H3 as specified spends a ledger slot for an answer that is probably an
   absence.** It widens the correction for every hypothesis this lab tests
   afterwards. That cost is being paid knowingly, and it is recorded here rather
   than justified afterwards.
