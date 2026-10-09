# Does a rating that learns from last night beat the price?

Registered before it ran in `docs/preregistered_nightly_form.md`. Seasons 2022-2025 priced, 2021 as history. Every interval is at the Bonferroni critical value for **95 hypotheses** (3.47, not 1.96), clustered by season, season type and week.

| Hypothesis | Games | Slope | 95% interval (corrected) | Detects | Pays at | 2025 alone | Reading |
|:---|---:|---:|:---|---:|---:|---:|:---|
| `form-ratings-vs-close` | 3,126 | +0.0018 | [-0.1119, +0.1155] | 0.141 | +0.136 | -0.0114 (n = 806) | **no demonstrated edge**; the interval rules out what pays |
| `form-ratings-vs-open` | 3,117 | +0.0071 | [-0.1163, +0.1305] | 0.153 | +0.140 | -0.0143 (n = 806) | **no demonstrated edge**; the interval rules out what pays |
| `qb-change-vs-close` | 2,322 | -0.0559 | [-1.8695, +1.7578] | 2.254 | -1.500 | +0.4820 (n = 628) | **no demonstrated edge**; underpowered, so what pays is not ruled out |

**As a forecaster**, over 3,126 games the form rating's mean absolute error on the margin is **13.65 points** against the closing line's **12.00**; the two correlate at +0.831.

**Starter coverage.** 7,618 of 7,728 team-games 2021-2025 matched a starter in the play-level file. 610 priced team-games carried a quarterback change, and 525 of 2,322 games had a change on exactly one side, which is all the starter test can learn from.

## What this means for the card

**Nothing cleared the registered bars, so nothing enters the price.** The rating and the starter flag go on the card as context beside the consensus line, and the probabilities stay anchored on it. A rating that learns nightly is a description of how teams are playing; this table says the closing price already carries it.
