#!/usr/bin/env python3
"""Record the opener study into the cumulative ledger. Spends nothing.

    PYTHONPATH=src python scripts/record_opener_study.py

Two groups, kept under separate search names because they were bought under
different terms.

**`opener-study` — the four hypotheses pre-registered** in
`docs/preregistered_opener_study.md`, under the names fixed there before any of
them could be graded against a result.

**`opener-study-unregistered` — ten further looks that were actually put to the
data.** The pre-registration is explicit about the price of these: "swapping the
definition after seeing `books <= 2` fail is a second look at the same question.
If one is ever run it is a NEW LEDGER ENTRY and the correction is re-derived."
They were run. Recording them is following that rule rather than inventing a
policy, and the direction of the error matters: an unrecorded look makes every
later interval too NARROW, which is the one failure this ledger exists to
prevent. Every result in this study is a null or a no-demonstrated-edge, so a
wider correction cannot manufacture a finding here — it can only make the
absences plainer.

What is deliberately NOT recorded: the adjudication's data-integrity re-runs of
the registered statistics on a sample filtered for corrupt rows. Those are the
same hypotheses on the same seasons — one degree of freedom, not two, exactly as
`Hypothesis.key()` defines it — and they produced no new claim about an edge,
only a fragility statement about an existing one. A reviewer who disagrees
should append them; the count moves 92 -> 95 and no verdict in the write-up
changes.

The ledger is append-only. Recording raises the bar for everything this lab
tests afterwards, which is the intended cost.
"""

from __future__ import annotations

from pathlib import Path

from ncaaf_betting_lab.experiment_ledger import (
    LEDGER_FILENAME,
    Hypothesis,
    load,
    render,
    save,
)

LEDGER = Path("data/outputs") / LEDGER_FILENAME
LEDGER_MD = Path("data/outputs/experiment_ledger.md")
SEASONS = (2021, 2022, 2023, 2024, 2025)
TESTED_ON = "2026-09-05"

REGISTERED: tuple[tuple[str, str], ...] = (
    (
        "control-close-beats-open",
        "PASSES as registered, with no margin. D = mean(e_open^2) - mean(e_close^2) "
        "= +3.9891 pts^2 (RMSE 15.4059 -> 15.2759), n = 3,857 spread games over 77 "
        "(season, week) clusters, SE 1.0325, z 3.8635; interval excludes zero on the "
        "pre-registered positive side. Two qualifications travel with the pass: the "
        "measured D sits BELOW the design's own 80% power floor (realized power "
        "66.9%), and dropping 32 of 3,857 games (0.83%) whose raw feed carries a "
        "per-book sign inconsistency takes D to +3.1019 (n = 3,825, SE 0.9568) with "
        "an interval that INCLUDES zero. Not quoted as an edge.",
    ),
    (
        "ratings-vs-open",
        "no demonstrated edge; slope -0.014418, SE 0.007673, n = 3,117 games over 62 "
        "clusters, interval includes zero. Sign NEGATIVE against a registered "
        "POSITIVE. Separately, the upper bound bounds the market's revision toward "
        "the ratings at about 0.12 pts of line move at the top decile of "
        "disagreement (9.97 pts). CLV question, not a profit question: this data "
        "carries no price on the move.",
    ),
    (
        "ratings-vs-open-outcome",
        "no demonstrated edge; slope -0.0461, SE 0.0393, n = 3,117 games over 62 "
        "clusters, interval includes zero. Sign NEGATIVE against a registered "
        "POSITIVE. The interval's upper bound sits below the profitable_slope of "
        "0.1509 (= 1.5 / (1.28 x sd(disagree_open) 7.7639)), so a paying slope is "
        "ruled out on all games; the 80% power criterion nonetheless FAILS (floor "
        "above 0.1509), so the ruling-out is the realized interval speaking rather "
        "than a design guaranteed to have seen a paying slope. Reproduces Step 5's "
        "shape against the close: the opener is not measurably softer.",
    ),
    (
        "segment-heterogeneity",
        "ABSENCE, not a null, as pre-declared. Registered statistic run at "
        "adjudication (the study had substituted a different one): delta = "
        "slope_thin - slope_thick = -0.0327, quadrature SE 0.1598; thin (books <= 2) "
        "n = 161 over 25 clusters slope -0.1236, thick (books >= 4) n = 774 over 18 "
        "clusters slope -0.0910, books == 3 (n = 2,182) excluded as the registered "
        "tie. Interval includes zero and the sign is NEGATIVE against a registered "
        "POSITIVE. Detectable floor 0.687 against a thin-arm profitable_slope of "
        "0.1423 — the design could not have seen a paying effect. Newly measured "
        "confound: 715 of the 774 thick-arm games are 2022, so the thin/thick "
        "contrast is largely a season contrast.",
    ),
)

UNREGISTERED: tuple[tuple[str, str], ...] = (
    (
        "control-close-beats-open / TOTAL market",
        "not pre-registered (the control was registered on the spread). D = +4.8750 "
        "pts^2, SE 1.1902, n = 3,862 over 77 clusters, excludes zero positive-side; "
        "measured D below its own 80% floor (realized power 74.8%).",
    ),
    (
        "control-close-beats-open / moved games only",
        "not pre-registered; reported by the study as descriptive. D = +4.5860 "
        "pts^2, SE 1.1751, n = 3,355 of 3,857 (the 502 games whose line never moved "
        "carry a paired D of exactly 0).",
    ),
    (
        "ratings-vs-open-outcome / early season weeks 1-4",
        "no demonstrated edge; slope -0.1524, SE 0.0542, n = 941 over 16 clusters. "
        "Floor 0.2314 above its own profitable_slope 0.1439 — an absence.",
    ),
    (
        "ratings-vs-open-outcome / late season weeks 5+",
        "no demonstrated edge and nothing ruled out; slope +0.0069, SE 0.0482, n = "
        "2,176 over 46 clusters, upper bound above its own profitable_slope 0.1548. "
        "Unresolved, exactly as against the close.",
    ),
    (
        "segment substitute / mean abs line move, weeks 1-4 vs 5+",
        "not pre-registered; a substituted segment definition and a substituted "
        "statistic. Difference +0.2446 pts, SE 0.1192, n = 3,857; interval includes "
        "zero. Floor 0.5089 pts, above the point estimate.",
    ),
    (
        "segment substitute / mean abs line move, books <= 3 vs > 3",
        "not pre-registered; the median split the pre-registration declined. "
        "Difference +0.2865 pts, SE 0.0989, n = 3,857; interval includes zero at the "
        "corrected critical value (nominal z 2.90 would have cleared 1.96). 2,188 of "
        "3,857 games sit exactly at the median, so the arms barely differ.",
    ),
    (
        "segment substitute / mean abs line move, |close| >= 14 vs < 14",
        "not pre-registered. Difference +0.0133 pts, SE 0.0561, n = 3,857; interval "
        "includes zero. Best-powered of the substituted splits and the flattest.",
    ),
    (
        "segment substitute / mean abs line move, books <= 2 vs >= 4",
        "not pre-registered: the registered SEGMENTS but a substituted STATISTIC "
        "(mean absolute move, not the H2 slope difference). Difference +0.2927 pts, "
        "SE 0.2604, n = 1,669; interval includes zero. Floor 1.1115 pts is most of "
        "the 1.44-pt mean move in the whole sample.",
    ),
    (
        "resid_open on market_move, all games",
        "not pre-registered, and substantially a re-run of the recorded "
        "line-movement-as-a-detector instrument. slope - 1 = -0.0570, SE 0.0994, n = "
        "3,857 over 77 clusters; interval includes zero. The raw slope of ~1.0 is "
        "MECHANICAL — market_move is an additive term of resid_open — so a "
        "zero-exclusion there is arithmetic, not evidence. Recorded conservatively.",
    ),
    (
        "resid_open on market_move, early-season arm",
        "not pre-registered AND post-hoc selected: the arm was chosen after seeing "
        "which segment moved most, and the interval does not account for that "
        "selection. slope - 1 = -0.0964, SE 0.1374, n = 1,154 over 20 clusters; "
        "interval includes zero. Floor 0.5865 above the 0.5091 that would pay — an "
        "absence.",
    ),
)


def entries(search: str, rows: tuple[tuple[str, str], ...]) -> list[Hypothesis]:
    return [
        Hypothesis(
            search=search, name=name, tested_on=TESTED_ON, seasons=SEASONS,
            outcome=outcome,
        )
        for name, outcome in rows
    ]


def main() -> None:
    ledger = load(LEDGER)
    before, before_factor = ledger.count, ledger.correction_factor()
    added_registered = ledger.record(*entries("opener-study", REGISTERED))
    added_extra = ledger.record(*entries("opener-study-unregistered", UNREGISTERED))
    save(ledger, LEDGER)
    LEDGER_MD.write_text(render(ledger), encoding="utf-8")
    after, after_factor = ledger.count, ledger.correction_factor()
    print(f"before                     {before:>3} hypotheses  x{before_factor:.4f}  "
          f"critical value {1.96 * before_factor:.4f}")
    print(f"opener-study               +{added_registered:>2}  (pre-registered)")
    print(f"opener-study-unregistered  +{added_extra:>2}  (looks actually taken)")
    print(f"after                      {after:>3} hypotheses  x{after_factor:.4f}  "
          f"critical value {1.96 * after_factor:.4f}")
    print(f"detectable-edge floor      ({1.96 * after_factor:.4f} + 0.8416) x SE = "
          f"{1.96 * after_factor + 0.8416:.4f} x SE   (80% power)")
    print("\nby search:")
    for search, count in sorted(ledger.by_search().items(), key=lambda kv: -kv[1]):
        print(f"  {search:<28} {count:>3}")


if __name__ == "__main__":
    main()
