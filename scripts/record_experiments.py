#!/usr/bin/env python3
"""Record hypotheses into the cumulative ledger. Spends nothing.

    PYTHONPATH=src python scripts/record_experiments.py --backfill

Every search this lab runs appends here, and the correction factor it hands
back grows with the count. Run with `--backfill` once to seed it with what has
already been tested; after that each search records its own.
"""

from __future__ import annotations

import argparse
from datetime import date

from ncaaf_betting_lab.config import OUTPUTS_DIR
from ncaaf_betting_lab.experiment_ledger import (
    LEDGER_FILENAME,
    Hypothesis,
    load,
    render,
    save,
)

#: Everything put to the bought population before the ledger existed. Recorded
#: so the correction starts from the truth rather than from zero — a lab that
#: has tested forty things and counts one is worse off than one that never
#: corrected at all, because it reports a number that looks careful.
BACKFILL: tuple[tuple[str, tuple[str, ...], tuple[int, ...], str], ...] = (
    # This lab's own tally starts empty. The NFL lab's 53 hypotheses were
    # tested against a different sport on different data and buy nothing here —
    # importing them would inflate this lab's correction with other people's
    # searching.
)



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--search", default="")
    parser.add_argument("--hypotheses", nargs="*", default=[])
    parser.add_argument("--seasons", type=int, nargs="*", default=[])
    parser.add_argument("--outcome", default="")
    parser.add_argument("--tested-on", default=date.today().isoformat())
    args = parser.parse_args(argv)

    path = OUTPUTS_DIR / LEDGER_FILENAME
    ledger = load(path)
    before = ledger.count

    if args.backfill:
        for search, names, seasons, outcome in BACKFILL:
            ledger.record(*[
                Hypothesis(search=search, name=name, tested_on=args.tested_on,
                           seasons=seasons, outcome=outcome)
                for name in names
            ])
    if args.search and args.hypotheses:
        ledger.record(*[
            Hypothesis(
                search=args.search, name=name, tested_on=args.tested_on,
                seasons=tuple(args.seasons), outcome=args.outcome or "recorded",
            )
            for name in args.hypotheses
        ])

    save(ledger, path)
    (OUTPUTS_DIR / "experiment_ledger.md").write_text(render(ledger), encoding="utf-8")
    print(
        f"{ledger.count} distinct hypotheses (+{ledger.count - before}). "
        f"Any new 95% interval widens by x{ledger.correction_factor():.2f}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
