# Steps 2-5: no demonstrated edge

**Nothing in steps 2 through 4 is worth pursuing as a bet.** Every candidate edge either failed
outright, sat inside an interval that covers zero, or sat inside an interval the design was never
wide enough to resolve. The single actionable finding is internal and costs money rather than making
it: this lab's margin model prices a fixture at a dispersion of **20.5-21.9 points when the truth is
15.3**, and its held-out advantage over a normal is bought entirely by scale, not by the empirical
shape Step 1 credited.

Three summary claims, each measured:

- **The books are coherent.** All 25 books measured — 3 modern, 22 legacy including PINNACLE, across
  20 seasons — price moneylines consistent with their own spreads under a margin SD of 13.7-16.8.
  None is exploitable: the largest book-versus-realised gap is 2.30 points of implied SD, and the
  design could only have seen 4.19.
- **The market's revision is unpredictable by anything this lab owns.** The regressor Step 3 was
  specified around is identically zero (the model takes its mean from the price), and the one thing
  the model does own — the shape — moves the line by -0.050 points per point of disagreement
  (n=3,773, CI -0.129 to +0.029) against an injection-verified floor of 0.103.
- **Outlier betting is a middling artefact.** The +1.9% to +5.5% ROIs in Step 4 come from a
  three-book roster where 54-59% of qualifying game-markets get **both sides** bet, from one book
  (DraftKings alone +6.65%; without it -0.41%), and from two seasons. Every cell's detectable floor
  (+7.95% to +38.59% ROI) is above the effect it is trying to see.

**Step 5 is not covered by this document.** No Step 5 results were returned to this write-up, and the
Step 4 results table was truncated mid-entry at the price-control cell. Everything below Step 4's
seventh result is reported from the step's own summary text only, with no numbers attached, and is
flagged as such. Do not read the absence of a Step 5 verdict as a Step 5 null.

---

## Experiment ledger

The ledger stood at **4 hypotheses (x1.27)** before these steps. Spend:

| Step | Hypotheses | Running total | Correct factor at that point | Factor the step actually used |
|:---|---:|---:|---:|---:|
| prior (margin-shape bandwidth sweep) | 4 | 4 | x1.274 | x1.274 |
| Step 2 — book-implied margin dispersion | 4 | 8 | x1.395 | x1.395 |
| Step 3 — line movement as detector | 4 | 12 | x1.462 | x1.40 |
| Step 4 — book vs consensus | 54 | 66 | x1.718 | x1.70 (counted 58: prior + own, omitting Steps 2-3) |
| Step 5 — ratings as a residual | 3 | 69 | x1.723 | x1.742 (ledger backfilled to 78; conservative) |

**New cumulative count: 66 known hypotheses. New correction factor: x1.718** (Bonferroni,
z = 3.3678 vs 1.9600). 66 is a floor, not a count, until Step 5's spend is recorded.

Two intervals in this document are narrower than they should be: Step 3's carry x1.40 where x1.462
was due (4.5% too narrow), and Step 4's carry x1.70 where x1.718 was due (1.1% too narrow). Neither
correction flips a verdict — every affected result was already a null or already inside its floor —
but every positive-looking cell in Step 4 is fractionally wider than printed, never narrower.

The on-disk ledger at `/Users/cooperross/Projects/ncaaf-betting-lab/data/outputs/experiment_ledger.json`
read 4 / x1.27 and was stale by 62 hypotheses; it has since been backfilled to 78 / x1.742.

---

## Step 2 — What margin distribution makes each book's spread and moneyline coherent

**Verdict: no demonstrated edge in any book. The mispriced distribution is this lab's own.**

### The benchmark in the brief is the wrong object

The brief asks whether book-implied SD differs from "the realised 20.13". That 20.13 is the
**unconditional** margin SD (reproduced exactly: 20.133 on n=1,606 games, 2024-25), and the
spread-versus-moneyline inversion recovers a **conditional** dispersion. The variance decomposition
is exact:

    var(margin) 412.3  =  var(implied margin) 180.3  +  var(residual) 233.8  =  414.1

The correct benchmark is the **15.29-point dispersion of margin about the closing spread**
(n=3,864, CI [14.81, 15.77] at x1.395; probit-through-origin 15.02). Comparing 14.9 to 20.13 would
have manufactured a five-point "books are under-dispersed" finding out of a category error.

### What each book actually implies

| Book | Seasons | n (game-book rows) | Implied margin SD | Interval (x1.395) | Identified floor |
|:---|:---|---:|---:|:---|:---|
| Bovada | 2021-25 | 3,581 | 14.96 (mult 16.27, power 13.94) | [14.85, 15.07] | +/-1.17 pts — set by devig choice, not n |
| DraftKings | 2023-25 | 2,182 | 14.74 (mult 15.83, power 13.98) | [14.62, 14.85] | +/-1.0 pts |
| ESPN Bet | 2024-25 | 1,472 | 14.69 (mult 15.92, power 13.72) | [14.52, 14.86] | +/-1.1 pts |
| PINNACLE | 2006-19 | 8,260 | 14.80 (mult 15.58, power 14.27) | [14.74, 14.86] | +/-0.8 pts |
| 22 legacy books | 2006-19 | 112,556 rows | 13.75 to 15.52, median 14.65 | — | no book reaches 20 under any devig (max 16.79) |

The devig method moves the pooled implied SD from 13.91 to 16.06 — **2.15 points** — while the entire
between-book spread is **0.27 points**. Per-book SD differences are real in the sampling sense and
meaningless in the substantive one. Any claim of the form "book X uses a different distribution"
dies on that arithmetic alone.

Era confound checked on the 1,357 games all three modern books quote: Bovada 14.93 [14.75, 15.11],
DraftKings 14.63 [14.53, 14.72], ESPN Bet 14.55 [14.40, 14.69]. Ordering survives, magnitude shrinks,
paired within-game devigged probabilities differ by +0.0039 (Bovada vs DK) and +0.0004 (DK vs ESPN).

### The nulls, with floors

| Test | n | Result | Detectable floor |
|:---|---:|:---|:---|
| Is any book a worse forecaster than a correctly-scaled normal off its own spread? | 7,235 | Bovada -0.00051, DraftKings +0.00295, ESPN Bet -0.00036 nats/game vs normal(15.29); all intervals cover zero | **0.004 nats/game per book.** A 3-point SD error would show as ~0.02 nats — this test could have seen one |
| Does implied SD vary with abs(spread)? Books say yes, realised says nothing | 7,235 books / 3,864 realised | books sigma = 12.79 + 0.1145*abs(imp) (identical in PINNACLE 2006-19: 12.26 -> 16.03); realised = 14.44 + 0.0334*abs(imp), CI [-0.127, +0.194] | **slope 0.16/point.** The books' 0.115 is inside the noise — **underpowered**, not confirmatory |
| Exploit the largest gap: underdog moneylines at abs(spread) 3-10 | 2,912 bets | **ROI -5.17%** [-16.05%, +5.71%]; claimed EV was +6.1% | **12.9% ROI**, i.e. the book would have to be wrong by **4.19 points** of implied SD. Observed gap: **2.30** |

The signature test is worth stating precisely because it is the only shared non-normal fingerprint:
implied SD rises from ~12.8 at abs(spread) 4 to ~16 at abs(spread) 28, in every book, stable across
20 years. It is **not resolvable** at 3,864 games — the realised slope's interval covers both zero
and every book's slope. And the realised favourite win rate at abs(spread) 6-10 (0.7310 +/- 0.0155,
n=2,912 population) lands on the **books'** number 0.7268, not the flat normal's 0.6963.

### The finding that is real, and is internal

`src/ncaaf_betting_lab/models/margin.py` builds its shape from the **unconditional** margin
distribution and tilts it, so it carries a dispersion of **20.45 at implied margin 0 rising to 21.92
at implied margin 21** (normal-equivalent 22.6 at implied 14-28) — six points above every book and
6.6 above realised. On held-out 2025 (n=797), scored as proper PMFs over integer margins:

| Comparison | Value (nats/game) | t | Interval (x1.395) |
|:---|---:|---:|:---|
| lab shape vs normal(20.3) — the Step 1 claim | **+0.0632** | 1.87 | [-0.029, +0.156] — **covers zero** |
| normal(15.4) vs normal(20.3) — pure rescale | **+0.0736** | **6.92** | [+0.045, +0.103] |
| lab shape vs normal(15.4) — what the shape adds | **-0.0105** | -0.31 | — |

Detectable floor: **0.047 nats/game** at n=797 with x1.395. The shape claim sits below it; the scale
claim clears it 1.6x. **The scale is the entire Step 1 result.** The residual about the close has
excess kurtosis 0.065 and skew -0.022 and matches a normal at every quantile to 1 point, so there is
no shape left to harvest.

Two corollaries. First, the module's stated rationale — "margin dispersion scales with the total,
which is the college-specific half of this design" — conditions on the wrong thing: across total
buckets the SD of the **implied** margin rises 10.5 -> 14.6 while the SD of the **residual** does not
move (14.96 / 15.34 / 15.33 / 15.29, n=3,864). Second, the over-dispersion is not harmless: betting
the model's own +EV moneylines at posted prices lost **-9.2% over 6,128 bets** while the model
claimed +24.4%.

### Kills that landed on the way

- **Devig method.** Multiplicative, additive, Shin and power/odds-ratio all run. Shin proved
  algebraically identical to additive for a two-outcome market (verified numerically — not a bug).
- **Missing spread odds.** The modern feed has *no* spread odds at all (100% NaN for
  `market_type='spread'`, 2021-25), so the inversion had to assume the quoted spread is the median.
  Tested where it can be tested — 2006-19 has real spread odds — and across 22 books / 112,556 rows
  the true devigged spread price moves implied SD by at most **0.08 points** (PINNACLE: 0.00).
- **Home-side orientation.** Resolved three ways; parsing `game_desc` "Away@Home" matched
  `line_table` on all 3,864 games with mean absolute difference **exactly 0.00**. The abbr->team_id
  route disagreed on 8 games because the feed's `home_team_id`/`away_team_id` are swapped relative to
  its own `game_desc` there (Army-Navy 2021, LSU-FSU 2022, all neutral sites). Home-side spread
  median is -3.5, not 0. Separately dropped 58 of 7,310 rows (0.79%, 45 of them Bovada) where a
  book's spread and its own moneyline disagree on who is favoured.
- **Killed the step's own best result.** A first pass had a residual-shaped model beating
  normal(15.4) by +0.1668 nats/game at t=11. Artefact: the residual PMF lived on a rounded
  half-integer grid while the competitors lived on integer margins, pocketing a factor of ~2 in grid
  mass. Rebuilt on integer margins: advantage collapsed to **-0.0331 nats (t=-1.24)**.
- **`power.detectable_edge` hard-codes `PER_BET_SD = 1.0`** (`power.py:46`), valid at -110 and not
  for moneylines. Measured per-bet SD on these selections is 1.20-1.95, so every moneyline floor the
  module reports is 20-95% too small. All floors above are rescaled.

---

## Step 3 — Line movement as a powered detector

**Verdict: the question as specified is not answerable, and the answerable version is a powered null
on spreads and an underpowered null on totals.**

### The specified regressor does not exist

"Model implied margin - open" is **identically zero**: max abs(model mean - open) = 9.99e-07,
sd 5.4e-07 (n=3,773 spreads; n=3,862 totals, max 9.92e-07). That is the bisection tolerance in
`tilt_to_mean`, not information. `margin.py` takes `implied_margin` from the market by construction,
so the lab has **no number of its own** with which to anticipate a revision. A regressor with zero
variance has no slope, and no sample size fixes it. This is an identity, not a null — Step 3 as
written was asking whether the market anticipates itself.

The lab also ships **no total model at all**; the direct analog (kernel-smoothed empirical
total-points PMF, bw 0.5, fallback 0.03, LOSO by season) had to be built for this step, so the totals
result tests something the lab does not own.

### The one thing the model does own: the shape

| Market | n | beta (pts of movement per pt of disagreement) | Interval (x1.40) | within-R2 | Detectable floor | Reading |
|:---|---:|---:|:---|---:|:---|:---|
| Spread — shape fair-point offset | 3,773 | **-0.0500** | [-0.1286, +0.0285] | 0.00092 | **abs(beta) >= 0.1027** = 0.126 pts of movement per 1sd (1.23 pts) of disagreement = 0.387% of movement variance | powered null |
| Total — shape fair-total offset | 3,862 | **-0.3017** | [-0.7438, +0.1403] | 0.00096 | **abs(beta) >= 0.5781** (5.6x the spread floor) | underpowered |
| Spread, with a cubic in the open controlled | 3,773 | +0.0144 | [-0.0850, +0.1139] | — | abs(beta) >= 0.130 | null, sign flips |
| Total, with a cubic in the open controlled | 3,862 | -0.0195 | [-0.5955, +0.5564] | — | abs(beta) >= 0.753 | null, sign flips |

The spread floor is **verified by injection, not assumed**: a planted slope of 0.10 was detected in
78% of 400 draws, 0.20 in 100%, and a within-season shuffle placebo false-positives at 0.50% against
a nominal 1.25%. The totals floor is the honest reason that result means less — injection detects a
planted 0.20 only 9% of the time and 0.50 only 72%, because the total shape offset is essentially a
constant (mean -0.87 pts, **sd 0.24**) that the intercept absorbs. In variance terms the two floors
are indistinguishable (0.387% vs 0.425%), so the weakness is the regressor, not the detector.

The shape offset is in any case a deterministic transform of the open line (R2 0.306 spread, 0.293
total on a cubic in the open), so it cannot beat the market by construction.

### The detector is real, and the power premise is now measured

| Check | n | Result | Floor |
|:---|---:|:---|:---|
| Positive control: does the close beat the open? | 3,857 | spread RMSE 15.406 -> 15.276 (**MSE reduction +3.99 +/- 3.017**); total 15.908 -> 15.755 (+4.88 +/- 3.276). Both exclude zero | MSE reduction >= 3.02 pts^2 |
| Over/under-reaction: close residual on its own movement | 3,857 | beta = -0.057 (spread), +0.033 (total) — the close fully absorbs its revision | — |
| Power premise, measured not asserted | 3,773 | sd(movement) 2.01 vs sd(open's realised error) 15.41 -> **variance ratio 58.7x**; MDE 0.1027 on movement vs 0.8541 on outcomes -> movement needs **69.1x fewer games** (totals 55.7x / 56.2x) | outcome regression itself: beta = -0.453, [-1.106, +0.200], floor abs(beta) >= 0.854 |
| The objective, for scale: settled P&L floor | 3,773 | **+5.82% ROI** at 1 bet/game (+4.19% at 2), rho = 0.036 | **+5.82% ROI = 1.67 points of line value.** Nothing smaller is visible to P&L over five complete seasons |

One point of line value is 3.48% ROI, computed from the lab's own empirical shape (cover-probability
density 0.0182/pt at implied margin +4, total 53), not a rule of thumb. The brief's ~100-vs-15,000
framing is directionally right; the measured ratio at this sample is **69x, not 150x**.

### Artefacts found in the data itself

- **`open_consensus` and `close_consensus` are medians over different book sets.** Only **46.9%** of
  2021-25 spread rows carry an opening line, and coverage is book-specific: Bovada 99.7%,
  DraftKings 92.0%, ESPN Bet 82.3%, William Hill / consensus / teamrankings / numberfire **0.0%**.
  Rebuilt from books quoting *both* numbers: corr 0.943 (spread) / 0.977 (total), mean abs
  discrepancy 0.26 pts, 8.8% of games off by more than half a point, 40.7% of games resting on a
  single book. **The contamination flips the headline sign**: naive `line_move` gives beta = +0.0453
  [-0.0348, +0.1254]; matched-book gives -0.0500. Every result above uses matched-book.
- **The brief's description of the feed is wrong for the window in use.** "34 books including
  PINNACLE" is true of 2006-2025 and false of 2021-2025: PINNACLE's last season is **2019**, and the
  in-window list is 10 labels, three of which are not sportsbooks — `consensus` (an aggregate) plus
  `numberfire` and `teamrankings` (projection sites). They supply **23.9%** of closing spread quotes
  and sit inside the lab's market median (median shifts on 13.1% of games, mean shift 0.049 pts, max
  12.0 pts). So `close_consensus` is partly somebody else's model, and **there is no sharp book
  in-window to build a lead-lag control from**.
- **The placebo failed on totals before fixed effects** — mean beta +0.306 with an 11.25%
  false-positive rate against a nominal 1.25%, because 20.8% of the total regressor's variance is
  between-season against the spread's 0.7%. Season-week FE restores it (0.75% / 0.50%), so the FE
  spec is the honest one and the un-FE totals interval was too narrow.
- Robustness sweep changed nothing: LOSO shape fitting, half-point fair handicap (spread -0.044,
  total -0.096), trimming abs(movement) <= 7, per-season betas with no persistence
  (+0.024 / +0.003 / -0.156 / +0.002 / -0.137), five clustering schemes with the widest reported.

---

## Step 4 — Book versus consensus (Kaunitz-style outlier betting)

**Verdict: no demonstrated edge. The strategy cannot be built as Kaunitz built it, and what can be
built is a middling artefact of a three-book roster.**

Note: **this step's results table was truncated in the payload**, at the price-control entry. Results
1-7 below are complete; everything after is reported from the step's summary text with no numbers.

### Why the design cannot be reproduced

In the results-bearing window (2021-2025) the feed carries **3-7 sources a season, not 34**, so every
leave-one-out consensus in the real-book variant is the midpoint of exactly **two** other books.
Spread and total **odds are 100% missing**, so Kaunitz's "plausible price" filter is unrunnable; a
live `money_line` at the same book on the same game was substituted.

### The sweep, with floors

| Cell | n bets | n games | ROI | Interval (x1.70) | Detectable floor | Reading |
|:---|---:|---:|---:|:---|---:|:---|
| Pooled spread+total, abs(d) >= 1.0 — the most powerful cell available | 2,754 | 1,186 | +1.94% (53.4% of decided) | [-2.13%, +6.01%] | **+7.95%** | underpowered |
| Spread, abs(d) >= 1.0 | 1,324 | 694 | +3.14% | [-2.58%, +8.86%] | **+11.47%** | underpowered |
| Spread, abs(d) >= 2.0 | 414 | 271 | +4.72% | [-7.76%, +17.20%] | **+20.51%** | underpowered |
| Total, abs(d) >= 1.0 | 1,430 | 805 | +0.83% | [-5.03%, +6.68%] | **+11.04%** | underpowered |
| Total, abs(d) >= 3.0 — the best-looking cell in the sweep | 117 | 96 | +14.22% | [-11.30%, +39.74%] | **+38.59%** — could not have detected a true +30% | not a strategy (~23 bets/year) |
| Kaunitz-faithful: one bet per game-market at the single most extreme book, abs(d) >= 1.5 | 763 | 636 | +3.00% | [-8.20%, +14.20%] | **+15.11%** | underpowered |
| True one-sided only (drop game-markets where both sides qualify), abs(d) >= 1.5 | 353 | 330 | **-2.63%** | [-18.98%, +13.73%] | **+22.21%** | sign flips |

Across the full 0.5-to-3.0 sweep on both markets the ROIs run +0.8% to +5.5% and **every clustered
interval straddles zero** at the honest multiplicity correction. Seeing a true +2% edge would need
roughly **36,000 bets**; the largest cell this design can build is **2,754 bets over 1,186 games**.

### Why the +3-5% is not an edge

Three independent decompositions, each sufficient on its own:

1. **It is one book.** DraftKings alone returns +6.65% at abs(d) >= 1.0; excluding it, the strategy
   returns **-0.41%**.
2. **It is two seasons.** 2023 returns **-0.12%** on 46% of the sample.
3. **It is middling, not outlier betting.** **54-59%** of qualifying game-markets get **both sides**
   bet — the structural consequence of a 3-book roster, where the low book and the high book are each
   an outlier against the median of the other two. Removing the middles flips the sign to -2.63%
   (n=353).

Stale lines are **not** the explanation — per the step summary, both stale proxies straddle zero and
disagree in sign — but that is a null from an unpowered control, not an acquittal.

**Hypotheses spent: 54.** That is the single largest contributor to the lab's correction factor, and
it bought nothing.

---

## Step 5 — do this lab's own ratings add anything on top of the market?

**Verdict: no demonstrated edge, and over the full sample the corrected interval also rules out a
slope that would pay. Ratings do not re-enter the architecture. The late-season split does not
support that second claim and is left open.**

Ratings fitted walk-forward (least squares on margin against team indicators plus a home-field term,
on games strictly earlier than the week being priced; ridge 3.0, home field +2.78 pts), then the only
question that matters: does the rating's disagreement with the closing spread predict the residual,
actual margin minus implied margin? Clustered by week. Full detail in
`data/outputs/ratings_residual.md`.

| Split | Games | Slope | 95% interval (x1.742) | Detects | Rules out a paying slope? |
|:---|---:|---:|:---|---:|:---|
| all games | 3,124 | -0.0196 | [-0.1369, +0.0978] | 0.146 | yes - interval sits below 0.143 |
| early season (weeks 1-4) | 941 | -0.0971 | [-0.2713, +0.0770] | 0.217 | yes |
| late season (weeks 5+) | 2,183 | +0.0204 | [-0.1239, +0.1647] | 0.180 | **no** |

The ratings disagree with the close by a standard deviation of **8.19 points** and none of it
predicts what the price got wrong. Profitability would need a slope of **0.143**: bet the top decile
of disagreement (10.5 points) and a -110 price needs roughly 1.5 points of true edge to clear the vig.

**A correction to my own first write-up of this step.** I initially reported the design as comfortably
powered - detecting 0.096 against a 0.143 threshold - and called the null "worth having". That
computed power at the nominal critical value of 1.96 while quoting intervals at the lab's corrected
3.41. At the honest correction the detectable slope is **0.146, above the 0.143 that would pay**, so
the 80% power criterion narrowly fails. What survives is the realized interval, which for the full
sample sits entirely below 0.143 - a stronger and more direct statement than a power calculation, and
the one the decision rests on. The design had no margin to spare.

**Hypotheses spent: 3.**

### Hypothesis spend, restated

The on-disk ledger read **21** because Step 4's 54-cell sweep was logged as four named families
rather than as cells. It has been backfilled - Step 4's grid reconstructed as six thresholds x three
markets x three variants = 54, matching the reported spend, and labelled a reconstruction rather than
a transcript in every entry - and Step 5's three splits recorded.

**The ledger now stands at 78 hypotheses, correction factor x1.742** (critical value 3.4136). It is
no longer stale, and `ratings_residual.py` reads the factor from it rather than pinning a constant,
so future spend tightens this conclusion automatically instead of leaving a stale number behind.

---

## What would have had to be true

Nothing survived, so there is no surviving result to defend. What each step would have needed:

**Step 2 — for a book to be exploitable.** A book's devigged moneyline would have had to imply a
margin dispersion differing from the realised 15.29 by more than **4.19 points**, which is the gap
that 2,912 underdog moneylines can resolve at 80% power. The observed gap at the widest point of the
sweep was **2.30 points**, and the resulting bets returned **-5.17%**. Equivalently: the realised
favourite win rate at abs(spread) 6-10 would have had to land near the flat model's 0.6963 rather
than the books' 0.7268. It landed at **0.7310 +/- 0.0155** — on the books' number. Separately, for
the abs(spread) signature to be a real mispricing rather than a shared convention, the realised slope
would have had to exceed **0.16 per point**; it is 0.033 with an interval covering zero and covering
every book.

**Step 2 — for the Step 1 architecture claim to stand.** The empirical shape would have had to beat a
normal **carrying the residual SD**. It does not: lab shape vs normal(15.4) is **-0.0105 nats/game
(t=-0.31)** on 797 held-out games, and the entire +0.0755-nat headline is reproduced by rescaling a
normal from 20.3 to 15.4 (+0.0736, t=6.92). Treat "+0.0755 nats vs a normal" as **unreplicated**
until the comparison normal carries the residual SD.

**Step 3 — for movement to be predictable.** The lab would first have had to own a mean of its own.
`margin.py` does not — its docstring says ratings "may still earn their way in later as a residual...
a hypothesis to test, not an architecture to assume", and that residual does not exist. Given a real
model mean, the coefficient would have had to exceed **0.103 points of movement per point of
disagreement** on spreads (78% detection at 0.10 by injection) or **0.578** on totals. Observed:
-0.050 and -0.302, both covering zero, both flipping sign when a cubic in the open is controlled.

**Step 4 — for outlier betting to be a strategy.** It would have had to survive removing DraftKings
(it does not: -0.41%), survive removing the middles (it does not: -2.63%), and be measured on a book
roster deep enough that a leave-one-out consensus is not the midpoint of two quotes. At three books,
"outlier versus consensus" and "one side of a middle" are the same selection. And it would have
needed roughly **36,000 bets** to see a true +2% — 13x the largest cell this feed can build.

---

## What to do next, and what is now closed

### Worth doing

1. **Rebuild the margin shape on the residual about the close, not on raw margins.** This is the one
   defect the analysis actually established, it is cheap, and it is worth ~0.074 nats/game on
   held-out data — larger than the shape claim it replaces. Re-derive the key-number claims in that
   frame; the current key-number table is measured on unconditional margins and does not transfer.
2. **Re-condition on the right variable.** Drop the total-bucket conditioning. Across total buckets
   the residual SD is flat (14.96 / 15.34 / 15.33 / 15.29, n=3,864) while the implied-margin SD moves
   10.5 -> 14.6. The module's "college-specific half of this design" is conditioning on the market,
   not on the dispersion.
3. **Fix `power.py:46`.** `PER_BET_SD = 1.0` is valid at -110 only. Measured per-bet SD on moneyline
   selections is 1.20-1.95, so every moneyline floor the module reports is 20-95% too small — it has
   been telling this lab it can see edges it cannot.
4. **Stop using `line_table`'s `line_move` as a measured quantity.** Only 46.9% of spread rows carry
   an open, coverage is book-specific, and the naive version flips the sign of the headline
   coefficient. Rebuild movement from books quoting both numbers, or do not use it.
5. **Record Step 5's results and its hypothesis spend**, then restate the correction factor. The
   on-disk ledger is stale by 62 hypotheses and every future interval computed from it will be too
   narrow.
6. **Decide whether this lab gets a model mean of its own.** Everything downstream — Step 3, any
   closing-line-value work, any bet selection that is not a pure shape play — is undefined until it
   does. Until then the lab can only ever agree with the price.

### Ruled out

- **Book-versus-book moneyline arbitrage on implied dispersion.** 25 books over 20 years agree to
  within 0.27 points; the devig choice moves the answer 8x further than the book choice does. There
  is nothing here to trade.
- **The 20.13 framing.** Any future analysis comparing an inverted implied SD to the unconditional
  margin SD is a category error. The number is 15.29.
- **Predicting line movement from this lab's model.** Not underpowered — undefined, because the
  regressor is a column of zeros.
- **Outlier-versus-consensus betting on this feed.** Not "unproven at current n" but structurally
  unbuildable: 3-7 sources, no spread/total odds, and a selection rule that bets both sides of the
  majority of qualifying markets.
- **Any conclusion resting on the brief's data description.** PINNACLE is absent after 2019, and 24%
  of in-window closing quotes come from an aggregate and two projection sites. There is no sharp book
  in this window.
- **Judging any of this by settled P&L.** The floor is **+5.82% ROI** (1.67 points of line value)
  over five complete seasons at 1 bet/game. Below that, profit and loss is blind, and every number in
  Step 4 sits below it.