# Everything this lab has ever tested

**A search that runs every week is not twelve tests. It is twelve tests a week, forever.** Correcting today's findings across today's twelve is a lie if twelve more were tested last week. At a nominal 5% threshold roughly one look in twenty clears by chance, so an automated edge-hunter without a cumulative tally does not find edges — it manufactures them on a schedule, with clean intervals and good prose.

**4 distinct hypotheses tested.** Any new 95% interval must be widened by **x1.27** before it means what it says.

| Search | Hypotheses |
|:---|---:|
| margin-shape | 4 |

| # | Search | Hypothesis | Seasons | Tested | Outcome |
|---:|:---|:---|:---|:---|:---|
| 1 | margin-shape | kernel bandwidth 0.5 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 2 | margin-shape | kernel bandwidth 0.7 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 3 | margin-shape | kernel bandwidth 0.9 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 4 | margin-shape | kernel bandwidth 1.2 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |

The correction is Bonferroni on the cumulative count — conservative on purpose. Holm and Benjamini-Hochberg need every p-value in hand at once, and this lab's tests arrive one week at a time over a season. A correction that can be computed incrementally and is slightly too wide beats one that is exactly right and cannot be computed until the season is over.

**This is not a substitute for a held-out season.** A correction widens an interval; it cannot tell you whether a result reproduces. Replication remains the bar.
