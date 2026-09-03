"""Record Step 5's spend, and backfill the 45 cells the ledger never counted.

The ledger read 21 hypotheses. The steps-2-to-5 write-up put the true count at
66, because I logged Step 4's 54-cell sweep as four named families rather than
as the cells it actually ran. A ledger that undercounts reports a correction
that is too small, and every interval computed from it is too narrow. That is
the exact failure the ledger exists to prevent, so it gets fixed here rather
than noted.

Step 4's grid is **reconstructed**, not transcribed: six thresholds (0.5 to 3.0)
x three markets (spread, total, pooled) x three variants (real-book consensus,
Kaunitz-faithful single most extreme book, true one-sided) = 54, matching the
spend the write-up reports. The reconstruction is labelled as one in every entry
so nobody later mistakes it for a transcript of what ran.
"""

from __future__ import annotations

from pathlib import Path

from ncaaf_betting_lab.experiment_ledger import Hypothesis, load, save

LEDGER = Path("data/outputs/experiment_ledger.json")
SEASONS = (2021, 2022, 2023, 2024, 2025)
TESTED_ON = "2026-09-03"

STEP_4_OUTCOME = (
    "no demonstrated edge; every cell inside its detectable floor "
    "(reconstructed grid cell — see docs, not a transcript)"
)


def step_4_cells() -> list[Hypothesis]:
    cells = []
    for variant in ("real-book consensus", "kaunitz single most extreme", "true one-sided"):
        for market in ("spread", "total", "pooled"):
            for threshold in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
                cells.append(
                    Hypothesis(
                        search="steps-2-to-5",
                        name=f"step4 {variant} / {market} / abs(d)>={threshold:.1f}",
                        tested_on=TESTED_ON,
                        seasons=SEASONS,
                        outcome=STEP_4_OUTCOME,
                    )
                )
    return cells


STEP_5 = [
    Hypothesis(
        search="ratings-residual",
        name=f"walk-forward ratings disagreement predicts residual — {split}",
        tested_on=TESTED_ON,
        seasons=SEASONS,
        outcome=outcome,
    )
    for split, outcome in [
        ("all games", "no demonstrated edge; slope -0.0196, CI [-0.0869, +0.0478], detects 0.096"),
        ("early season weeks 1-4", "no demonstrated edge, barely powered; slope -0.0971, detects 0.143"),
        ("late season weeks 5+", "no demonstrated edge; slope +0.0204, CI [-0.0625, +0.1033], detects 0.118"),
    ]
]


def main() -> None:
    ledger = load(LEDGER)
    before, before_factor = ledger.count, ledger.correction_factor()
    backfilled = ledger.record(*step_4_cells())
    step5 = ledger.record(*STEP_5)
    save(ledger, LEDGER)
    print(f"before        {before:>3} hypotheses  x{before_factor:.3f}")
    print(f"step 4 backfill  +{backfilled:>2}")
    print(f"step 5           +{step5:>2}")
    print(f"after         {ledger.count:>3} hypotheses  x{ledger.correction_factor():.3f}")
    print("\nby search:")
    for search, count in sorted(ledger.by_search().items(), key=lambda kv: -kv[1]):
        print(f"  {search:<24} {count:>3}")


if __name__ == "__main__":
    main()
