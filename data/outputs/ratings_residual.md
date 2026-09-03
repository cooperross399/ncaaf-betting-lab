# Do this lab's own ratings add anything the price does not have?

Everything here takes its mean from the market, because the sibling NFL lab found its ratings were a worse forecaster than the price. But a rating can be a bad forecaster and still be a useful **correction**, and that is a different claim. This is its test.

All intervals are corrected for the **78 hypotheses** in the cumulative ledger (Bonferroni, x1.742, critical value 3.41 rather than 1.96).

| Split | Games | Slope | 95% interval (corrected) | Detects | Rules out a paying slope? |
|:---|---:|---:|:---|---:|:---|
| all games | 3,124 | -0.0196 | [-0.1369, +0.0978] | 0.146 | **yes** — interval sits below 0.143 |
| early season (weeks 1-4) | 941 | -0.0971 | [-0.2713, +0.0770] | 0.217 | **yes** — interval sits below 0.143 |
| late season (weeks 5+) | 2,183 | +0.0204 | [-0.1239, +0.1647] | 0.180 | **NO** — interval still holds a slope that would pay |

*Detects* is the smallest slope the split could see at 80% power **at the corrected critical value**. Profitability needs 0.143: bet the top decile of disagreement — 10.5 points, since disagreement has a standard deviation of 8.19 — and a -110 price needs roughly 1.5 points of true edge to clear the vig.

## The honest reading

Every split reads **no demonstrated edge**: no interval excludes zero. But 'no demonstrated edge' and 'ruled out' are different claims, and the splits do not agree on the second one.

**Over all 3,124 games the corrected interval is [-0.1369, +0.0978], which sits entirely below the 0.143 a paying strategy needs.** So the answer to the question actually asked — should ratings re-enter the architecture — is no, and that is the interval speaking rather than a power calculation.

Note the 80% power criterion narrowly *fails* here (0.146 against 0.143). The realized interval is the stronger statement and the one that bears on the decision, but the design had no margin to spare, and one more season of hypotheses in the ledger would take it away.

**Not settled everywhere.** late season (weeks 5+) (n=2,183) has an upper bound of +0.1647, above 0.143. That split has not ruled out a slope that would pay, and no claim should be made there in either direction.

The ratings disagree with the closing spread by a standard deviation of **8.19 points** — a great deal — and the measured slope is small and negative. Ratings do not re-enter the architecture, but this is a bound, not a proof of zero.
