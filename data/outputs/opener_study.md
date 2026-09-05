# Does the OPENING line leave anything on the table?

Adjudication of the four-hypothesis study pre-registered in `docs/preregistered_opener_study.md`. Every interval below is quoted at the **corrected critical value 3.4584** — Bonferroni x1.7645 on the **92 distinct hypotheses** now in `data/outputs/experiment_ledger.json`, read live at run time. Every detectable-edge floor is **4.3000 x SE**, the smallest effect the design could see at 80% power *at that same critical value*. No measured number below is typed into this prose; all of it is rendered by `scripts/render_opener_study.py`.

---

## The control, first, because everything else depends on it

**The pre-registered positive control PASSES — and it passes with no margin in either of the two ways a result can have margin.** On the spread the close beats the open by D = mean(e_open²) − mean(e_close²) = **+3.5636 pts²**, n = **3,851 games** over 76 `(season, week)` clusters, corrected interval **[+0.3386, +6.7885]**, which excludes zero on the pre-registered positive side (z = 3.8215 against 3.4584). In points that is RMSE 15.3792 -> 15.2629, an improvement of **0.1163 points**, 0.76% of RMSE, on n = 3,851.

So by the threshold fixed in advance the control has passed, and the nulls in H1–H3 are interpretable rather than uninterpretable. Two qualifications are mandatory and they travel with the pass everywhere it is quoted.

**No power to spare.** The measured D sits *below* the design's own 80% floor of +4.0098 pts² (n = 3,851) — restated in points, the smallest forecast improvement this design could reliably detect is 0.1304 RMSE points and it measured 0.1163. That is arithmetically consistent with the interval excluding zero, but it means a replication would clear the corrected bar well under four times in five.

**Robustness, and this is what the re-run changed.** The pass leans on a thin tail of games, and part of that tail was never a market move at all but a defect in the feed. See *The opener is dirtier than the study assumed* below: dropping **32 of 3,851 games (0.83%)** whose raw rows cannot be read as a home handicap takes D to +3.2050 pts² (n = 3,821) with an interval of [+0.0397, +6.3704] — which **still excludes zero**. On the pre-fix table the same exclusion collapsed the interval across zero, and that fragility is why the study was re-run; it is gone.

The honest one-line verdict: **the instrument can just barely see the one effect known to be present in this data, and it no longer depends on the 32 unreadable rows to see it.** The margin is in the power, not in the data quality: the measured D still sits below the design's own 80% floor. Every null in H1–H3 must therefore be read against its own floor. None of them is a clean null and this report does not present one as such.

**A pass is not an edge and is not quoted as one.** 0.1163 RMSE points is roughly a tenth of the 1.5 points a -110 price needs to clear the vig. Nothing here is bettable, no bet was placed and none was automated.

| Control | n (games) | Clusters | D (pts²) | SE | Corrected interval | Excludes zero | 80% floor |
|:---|---:|---:|---:|---:|:---|:---|---:|
| spread — **the registered control** | 3,851 | 76 | +3.5636 | 0.9325 | [+0.3386, +6.7885] | yes, positive side | +4.0098 |
| total — *not registered* | 3,862 | 77 | +4.8750 | 1.1902 | [+0.7588, +8.9912] | yes, positive side | +5.1179 |
| spread, moved games only — *not registered* | 3,297 | 76 | +4.0686 | 1.1023 | [+0.2565, +7.8808] | yes, positive side | +4.7399 |

The total market is reported because it was run, not because it was registered: RMSE 15.9085 -> 15.7545 on n = 3,862. Its measured D also sits below its own floor of +5.1179. The moved-games row exists only to show the pooled D is not an artefact of the 554 games (14.4% of n = 3,851) whose line never moved and whose paired D is exactly zero.

---

## The sign convention, verified independently against the raw feed

A silently inverted spread turns a null into a finding and back again, so this was re-derived from the settlement source rather than taken from the pre-registration. Five fixtures were pulled back to `data/raw/ncaaf/betting/cfb_line_odds.csv.gz` and the schedule files, including a neutral-site game and the two most extreme handicaps in the table; on every one, `margin` equals `home_points - away_points` from the schedule, and `close_consensus` equals the median of the **home team's own rows** in the raw feed.

| Check | Value | n | The inverted reading |
|:---|---:|---:|---:|
| `corr(-close_consensus, margin)` | +0.6582 | 3,864 | -0.6582 |
| `corr(-open_consensus, margin)` | +0.6513 | 3,851 | -0.6513 |
| `mean(margin - (-close_consensus))` | +0.0964 pts | 3,864 | +8.4020 pts |
| `mean(margin - (-open_consensus))` | +0.0164 pts | 3,851 | — |
| home outright win rate, `close_consensus < 0` | 75.1% | 2,395 | — |
| home outright win rate, `close_consensus > 0` | 31.0% | 1,462 | — |
| `line_move == close - open` mismatches | 1548 | 3,851 | — |
| `corr(close_consensus, total_points)` (no sign flip) | +0.3735 | 3,864 | — |

**`open_consensus` carries the same HOME-handicap convention as `close_consensus`**, so the price's forecast of the home margin is the negative of each. `line_move` is positive on n = 1,726 games (the market moved toward the AWAY team), negative on n = 1,571 and exactly zero on n = 554. 7 games closed pick'em. Every figure in the pre-registration's conventions table reproduces exactly.

One correction to the study's own account. The positive-control script offers `e_open² - e_close² == (-line_move) x (e_open + e_close)` as an *independent* sign guard. It is not independent: `line_move` is defined in `scripts/build_line_table.py` as `close_consensus - open_consensus`, so that identity is algebra and holds whatever convention the opener is on. What actually establishes the convention is the correlation and bias table above plus the fixture-level trace to the raw feed. The conclusion is unchanged; the guard is weaker than advertised.

---

## The opener is dirtier than the study assumed

This is the adjudication's own finding and it was not in the pre-registration. `open_consensus` is a median over whichever books' `opening_lines` were populated, and in a small number of games those rows cannot be read as a home handicap at all.

* **A.** 36 book-rows of 5,969, on 29 distinct games, carry a single book's own opening and closing numbers with **opposite signs**, both at least 3 points from pick'em — implied swings of 6.0 to 36.5 points inside one book.
* **B.** 14 book-rows of 11,233, on 13 distinct games, close on the **opposite convention to the rest of that game's own book panel**; on 3 of those games the opener comes only from such a row, so `open_consensus` and `close_consensus` are on different conventions and `line_move` is roughly `-2 x close_consensus`.

The pre-registration's own worked example is one of them. `game_id 401331447` (2021 wk14, Michigan at Iowa, neutral site, Michigan won 42-3) is cited there as *"the largest move toward an away team in the table"* at +22.5 points. Traced back to the feed: three books close Iowa +12.0 and Bovada closes Iowa -12.0, and Bovada is the only book with an opening number, so `open_consensus` is -10.5 on one convention while `close_consensus` is +12.0 on the other. The 22.5-point "move" is a sign disagreement of roughly 2 x 11.25.

That example no longer resolves, and its not resolving is the point. `scripts/build_line_table.py` now drops the inverted row; it was the only book quoting an opener on that game, so 401331447 carries no opener at all and the 22.5-point move is gone from the table. The figure quoted above is from the pre-fix build, recorded here because the defect is why this study was re-run.

Nothing is repaired. A price that cannot be read is treated the way the lab treats a missing one — dropped, never inverted into what it "should have" been — because repairing it would be fabricating a price.

| Positive control, spread | n | Dropped | D (pts²) | SE | Corrected interval | Excludes zero |
|:---|---:|---:|---:|---:|:---|:---|
| published — nothing dropped | 3,851 | 0 | +3.5636 | 0.9325 | [+0.3386, +6.7885] | yes |
| drop B — opener sourced only from a panel-inconsistent book row | 3,850 | 1 | +3.4927 | 0.9412 | [+0.2376, +6.7478] | yes |
| drop A — a book's own open and close signs oppose | 3,822 | 29 | +3.2765 | 0.9066 | [+0.1412, +6.4117] | yes |
| drop A and B together | 3,821 | 30 | +3.2050 | 0.9153 | [+0.0397, +6.3704] | yes |

**H1 and H2 are robust to this; the control is not.** Both slopes keep their sign, their magnitude and their verdict at every rung. The control keeps its pass when either signature is dropped alone and loses it when both are dropped together — 32 games, 0.83% of the sample. A delete-one-cluster jackknife over all 76 weeks, by contrast, never breaks the pass, so this is not a week effect: it is a handful of individual rows. Note the direction — the corrupt rows *inflate* the apparent open-to-close improvement, so the true gap between the two prices is probably smaller than +3.5636 pts², which makes the market's own revision worth even less than the 0.1163 RMSE points quoted above.

---

## H1 — do the ratings anticipate the market's own revision?

`regress(market_move on disagree_open)`, clustered by `(season, week)`, where `market_move = -line_move`. Direction fixed in advance: POSITIVE.

**No demonstrated edge.** Slope **-0.018636**, cluster-robust SE 0.005793, n = **3,115 games** over 62 clusters, corrected interval **[-0.0387, +0.0014]**, which includes zero. The sign is NEGATIVE against a registered POSITIVE, but zero is inside the interval, so no anti-correlation is demonstrated either.

**Interpretable, not an absence — and it goes further than a null.** The detectable floor is 0.024912 (n = 3,115), which sits below the 0.0503 a half-point tick of movement at the top decile of disagreement would represent, so the design could have seen an effect of the size that would matter. Separately from the null, the interval's upper bound of +0.001400 corresponds to at most **+0.01 points of line move** at the top decile (9.95 points, sd(disagree_open) = 7.7713, n = 3,115). A market revision toward these ratings of even a quarter-point tick (0.0251) is ruled out. "No demonstrated edge" and "ruled out" are different claims and both are available here, so both are made.

**This is a CLV statement, not a profit statement.** The data carries no price on the move, which is why the pre-registration deliberately set no profitability threshold here. Predicting the move would mean getting a better number than the close, which is necessary for profit and not sufficient. Nothing here is an edge.

---

## H2 — do the ratings predict the result off the opener?

The Step 5 instrument with the opener in place of the close. `profitable_slope = 1.5 / (1.28 x sd(disagree_open) 7.7566) = **0.1511**` — the formula was registered in advance and the value is measured on this sample. Disagreement with the opener is *tighter* than with the close (7.7566 against the published 8.19), which raises the bar rather than lowering it.

| Split | n | Clusters | Slope | SE | Corrected interval | Reading | 80% floor | Own threshold |
|:---|---:|---:|---:|---:|:---|:---|---:|---:|
| all games | 3,115 | 62 | -0.0494 | 0.0394 | [-0.1855, +0.0867] | **no demonstrated edge** | 0.1692 | 0.1511 |
| early season (weeks 1-4) | 939 | 16 | -0.1489 | 0.0564 | [-0.3438, +0.0461] | **no demonstrated edge** | 0.2424 | 0.1438 |
| late season (weeks 5+) | 2,176 | 46 | +0.0000 | 0.0480 | [-0.1659, +0.1659] | **no demonstrated edge** | 0.2063 | 0.1551 |

**No demonstrated edge on all three splits** — every corrected interval includes zero, in those words. Three further statements, which are different from that one and from each other, and which do not hold in the same places.

1. **A paying slope is ruled out on all games** (upper bound +0.0867 < 0.1511) and on the early-season split (+0.0461 < 0.1438). It is **not** ruled out late season: upper bound +0.1659 against its own 0.1551, n = 2,176. Nothing should be claimed there in either direction — the same split Step 5 left unresolved against the close.
2. **The 80% power criterion fails everywhere.** Every floor (0.1692 / 0.2424 / 0.2063) sits above the threshold that would matter. So the all-games ruling-out is the realized interval speaking, not a design that could be trusted in advance to have seen a paying slope. **Report the ruling-out and the power failure together; either alone misleads.**
3. **The direction failed.** Registered POSITIVE, measured -0.0494 on all games and -0.1489 early season (n = 939) — the split the pre-registration named as the likeliest place for a soft opener. The intervals include zero, so this is a failed prediction and not a demonstrated reversal, and it must not be re-narrated as a finding about the market overreacting to ratings.

This **contradicts nothing already established and adds nothing to it**. Step 5 found ratings-vs-close slope -0.0196 on n = 3,124 with the same shape: no demonstrated edge, a paying slope ruled out on all games, late season unresolved. Against the opener the shape repeats. **The opener is not measurably softer than the close for this instrument, and ratings do not re-enter the architecture.**

---

## H3 — is the opener softer where few books quote?

**The registered H3 was not run by the study, and is run here.** `docs/preregistered_opener_study.md` registers `segment-heterogeneity` as the H2 regression in each arm with `delta = slope_thin - slope_thick`, over `thin = books <= 2` and `thick = books >= 4`, with `books == 3` excluded as the tie *"fixed now so it cannot be moved later"*. `scripts/run_opener_segment_softness.py` measured a different statistic (mean absolute line move) over three different segment definitions, two of which the pre-registration had named and expressly declined. Those splits are reported below because they were run, and they are recorded in the ledger as unregistered looks; the registered statistic is this one.

| Arm | n | Clusters | Slope | SE | Corrected interval | 80% floor | Own threshold |
|:---|---:|---:|---:|---:|:---|---:|---:|
| thin (`books <= 2`) | 192 | 38 | -0.1581 | 0.1074 | [-0.5295, +0.2133] | 0.4618 | 0.1492 |
| thick (`books >= 4`) | 772 | 18 | -0.0957 | 0.1102 | [-0.4768, +0.2853] | 0.4738 | 0.1736 |
| **delta = thin − thick** | 964 | 50 | -0.0623 | 0.1539 | [-0.5944, +0.4697] | 0.6616 | 0.1492 |

**This is an ABSENCE, not a null, exactly as pre-declared.** The interval on delta includes zero — no demonstrated edge — but the detectable floor of 0.6616 sits far above the 0.1492 a paying strategy in the thin arm would need, so a design that could not have seen the effect did not see it. The sign is NEGATIVE against a registered POSITIVE. The excluded tie holds n = 2,151 games, more than both arms together.

**A confound the pre-registration did not record, measured here.** The thick arm is 714 2022 games out of 772 (92%), by season {2022: 714, 2023: 49, 2025: 9}; the thin arm is {2022: 11, 2023: 96, 2024: 30, 2025: 55}. The number of books in this feed is largely a property of the *season*, not of the game, so the registered thin-versus-thick contrast is mostly a 2023-2025-versus-2022 contrast wearing a liquidity label. The thick arm spans only 18 clusters and the thin arm 38, both under the 30-50 a cluster-robust SE needs; the quadrature SE additionally assumes the arms are independent, which games sharing a week make only approximately true. The interval is reported with all of that attached rather than quoted clean.

### The substituted splits, reported because they were run

Mean absolute line move, thinner arm minus thicker, n = games in both arms.

| Split | Thin mean (n) | Thick mean (n) | Difference | SE | Corrected interval | Reading | 80% floor |
|:---|---:|---:|---:|---:|:---|:---|---:|
| weeks 1-4 vs weeks 5+ | 1.5350 (1,151) | 1.2844 (2,700) | +0.2506 | 0.1058 | [-0.1154, +0.6166] | **no demonstrated edge** | 0.4551 |
| books <= 3 vs books > 3 | 1.4377 (2,352) | 1.2362 (1,499) | +0.2016 | 0.0922 | [-0.1175, +0.5206] | **no demonstrated edge** | 0.3967 |
| \|close\| >= 14 vs < 14 | 1.4005 (1,156) | 1.3416 (2,695) | +0.0590 | 0.0517 | [-0.1199, +0.2379] | **no demonstrated edge** | 0.2224 |
| books <= 2 vs books >= 4 | 1.7487 (194) | 1.2362 (1,499) | +0.5126 | 0.2679 | [-0.4139, +1.4390] | **no demonstrated edge** | 1.1519 |

**No demonstrated edge on any of them.** Every point estimate has the registered sign — the thinner arm moved more in all four — and that is four correlated views of one dataset rather than four votes: the same n = 3,851 games are re-partitioned each time. Every floor exceeds its own point estimate. The closest, `books <= 3` vs `> 3`, is a nominal z of 2.18 — it would have cleared an uncorrected 1.96 and does not clear 3.4584. That gap is the multiplicity ratchet doing its job, and the honest statement is that it has demonstrated nothing. That split is also barely a contrast: the median `books` is 3 and most of the sample sits exactly on it.

One further result of the study's Part 2 needs stating so nobody quotes it: regressing the opener's residual on the line move returns a slope of 1.0 **mechanically**, because `resid_open = e_close + market_move` identically, so the regressor is an additive term of the dependent variable. Its zero-exclusion is arithmetic, not evidence. The quantity that means anything is `slope - 1`, which is algebraically the slope of the *closing* residual on the move — this lab's already-recorded line-movement-as-a-detector instrument, which reads no demonstrated edge.

---

## Multiplicity: what this study cost

| | Count | Factor | Critical value |
|:---|---:|---:|---:|
| Before this study | 78 | x1.7417 | 3.4136 |
| Pre-registered hypotheses recorded | +4 | | |
| Unregistered looks actually taken, recorded | +10 | | |
| **After — what every interval here is quoted at** | 92 | x1.7645 | 3.4584 |

The pre-registration fixed **3.4272** in advance, on the assumption that this study would spend exactly its registered four. It spent fourteen. The pre-registration is explicit about the price of the extra ones — *"if one is ever run it is a NEW LEDGER ENTRY and the correction is re-derived"* — so they are recorded, under the separate search name `opener-study-unregistered` so a reader can always tell which four were bought in advance. **No verdict in this report changes between 3.4272 and 3.4584**: the control's z of 3.8215 clears both, and every other interval includes zero at both. Under-recording would have made every later interval too narrow, which is the single failure the ledger exists to prevent; over-recording can only make an absence plainer, and every result here is an absence or a null.

**The recorder has the self-derived-floor defect, confirmed by running it rather than by reading it.** `ExperimentLedger.save()` refuses a shrinking write by re-loading the target file and comparing lengths — but the recorder pattern loads that same file, appends in memory and saves the same object back, so the floor it is guarded against is derived from the same load. Measured: hand-delete an entry from the tracked JSON, run the recorder pattern, and the write is accepted silently, the deleted hypothesis is gone, and the printed correction is unremarkable. The guard cannot fire from any caller in this repository. What does catch it is `scripts/check_ledger_append_only.py`, which compares against the base commit rather than against the file it is about to overwrite; run against the pre-study ledger it reports all base entries present and the new ones appended. So the property holds in CI and not at runtime, and no caller should be trusted to enforce it locally.

**One consequence of recording, flagged rather than acted on.** `scripts/run_ratings_residual.py` reads the correction live, by design — its own docstring says this is so that adding hypotheses tightens its conclusion automatically rather than leaving a stale constant behind. So `data/outputs/ratings_residual.md`, which was rendered at 78 hypotheses, is now stale against a re-run at 92. Checked before flagging: at 3.4584 the Step 5 all-games interval becomes about [-0.1386, +0.0994] and its detectable slope about 0.148, so it still rules out the 0.143 that would pay and its power criterion still narrowly fails — **no Step 5 verdict changes**. The file is left untouched here because re-rendering another study's published record is not an adjudicator's call to make unasked.

**A live hazard left in the tree for review, not fixed here.** Three of the study's scripts derive their critical value as `correction_factor(extra=4)` against the live ledger. That was correct while the ledger stood at 78. Now that these entries are recorded the same call reads 92 + 4 = 96 and silently over-corrects. `scripts/run_opener_ratings_residual.py` avoided this by pinning the value as a constant; the other three should do the same or drop `extra`.

---

## What would be needed to settle what is unsettled

None of the following is a plan to bet. Each is the size of the measurement that would be required before anything here could be called settled, and in two cases the answer is that this lab's data cannot settle it at all.

**H2, all games — to make the null a finding rather than a realized-interval statement.** The floor must fall from 0.1692 to the 0.1511 that would pay, so the SE must fall from 0.0394 to 0.0351. If the cluster-robust SE scales as 1/sqrt(n), that is about **3,908 games**, roughly **1.0 more seasons** of FBS-vs-FBS football beyond the 3,115 in hand. The ratchet bites here: testing again adds hypotheses, which raises the critical value, which raises the floor — so the requirement grows slightly every time it is re-asked, and the honest figure is 'at least' that many.

**H2, late season — the only split that has ruled nothing out.** Upper bound +0.1659 on n = 2,176, above its own 0.1551. It needs the same order of additional seasons, and it is the one place in this study where a future look is defensible rather than a second bite.

**H3 — not settleable with this feed.** The thin arm accrues about 48 games per season. Bringing its floor (0.4618) down to its own threshold (0.1492) needs roughly **1,838 thin-arm games**, on the order of **34 more seasons**. That is not a sample-size problem to be waited out. It needs a different instrument: a real per-book price feed with timestamps and a quoted side, so that "thin" means *books actually quoting when the number posted* rather than *books present in the settled feed*. **The lab does not have that data.** No provider fetch has ever run here, no price has been bought, and no market is known to be quoted by anybody.

**H1 — bounded, and the remaining gap is small.** The design already rules out a quarter-point revision toward the ratings. To resolve a quarter-point *effect* rather than bound it, the floor would need to reach 0.0251, about **3,060 games** (-0.1 more seasons). Worth noting only because it is a CLV question; there is still no price on the move.

**The control's robustness — a data problem, not a sample-size problem.** More seasons of the same feed will import the same defect at the same rate. What would settle it is per-book opening prices with an unambiguous side attribution and a timestamp — again, data the lab does not have. In the meantime the 32 identified games should be treated as missing prices by anything downstream that uses `open_consensus` or `line_move`.

---

## The standing verdict, unchanged

Five instruments had already been run against the closing line and every one read no demonstrated edge. This study adds a sixth, seventh and eighth reading against the **opening** line — H1, H2 and H3 — and **every one of them reads no demonstrated edge as well**, with H3 an absence rather than a null and H2's power criterion failing on every split. The one thing this study did demonstrate is that the close is a better forecast than the open by 0.1163 RMSE points (n = 3,851), which is a description of a market converging toward efficiency and is roughly a tenth of what a -110 price costs. **No edge was found, none is claimed, no bet was placed and none was automated.**

