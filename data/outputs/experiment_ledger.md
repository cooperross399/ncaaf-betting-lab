# Everything this lab has ever tested

**A search that runs every week is not twelve tests. It is twelve tests a week, forever.** Correcting today's findings across today's twelve is a lie if twelve more were tested last week. At a nominal 5% threshold roughly one look in twenty clears by chance, so an automated edge-hunter without a cumulative tally does not find edges — it manufactures them on a schedule, with clean intervals and good prose.

**21 distinct hypotheses tested.** Any new 95% interval must be widened by **x1.55** before it means what it says.

| Search | Hypotheses |
|:---|---:|
| steps-2-to-5 | 12 |
| margin-architecture | 5 |
| margin-shape | 4 |

| # | Search | Hypothesis | Seasons | Tested | Outcome |
|---:|:---|:---|:---|:---|:---|
| 1 | margin-shape | kernel bandwidth 0.5 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 2 | margin-shape | kernel bandwidth 0.7 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 3 | margin-shape | kernel bandwidth 0.9 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 4 | margin-shape | kernel bandwidth 1.2 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | 0.5 chosen on held-out 2025; +0.069 nats vs normal |
| 5 | steps-2-to-5 | book implied margin dispersion | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 6 | steps-2-to-5 | book vs correctly-scaled normal | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 7 | steps-2-to-5 | implied SD vs spread size | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 8 | steps-2-to-5 | underdog moneyline exploit | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 9 | steps-2-to-5 | line movement on model disagreement | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 10 | steps-2-to-5 | line movement on shape disagreement | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 11 | steps-2-to-5 | total movement | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 12 | steps-2-to-5 | movement power floor | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 13 | steps-2-to-5 | outlier vs consensus sweep | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 14 | steps-2-to-5 | outlier control: both sides bet | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 15 | steps-2-to-5 | outlier control: single book | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 16 | steps-2-to-5 | outlier control: stale lines | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | no demonstrated edge; all inside detectable floors |
| 17 | margin-architecture | shape from unconditional margins | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | spread-conditioning is the fix; the shape itself is not demonstrated |
| 18 | margin-architecture | shape from residuals | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | spread-conditioning is the fix; the shape itself is not demonstrated |
| 19 | margin-architecture | shape conditioned on spread bucket | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | spread-conditioning is the fix; the shape itself is not demonstrated |
| 20 | margin-architecture | bandwidth 0.4 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | spread-conditioning is the fix; the shape itself is not demonstrated |
| 21 | margin-architecture | bandwidth 0.8 | 2021, 2022, 2023, 2024, 2025 | 2026-09-03 | spread-conditioning is the fix; the shape itself is not demonstrated |

The correction is Bonferroni on the cumulative count — conservative on purpose. Holm and Benjamini-Hochberg need every p-value in hand at once, and this lab's tests arrive one week at a time over a season. A correction that can be computed incrementally and is slightly too wide beats one that is exactly right and cannot be computed until the season is over.

**This is not a substitute for a held-out season.** A correction widens an interval; it cannot tell you whether a result reproduces. Replication remains the bar.
