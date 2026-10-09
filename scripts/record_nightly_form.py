#!/usr/bin/env python3
"""Record the nightly-form study into the cumulative ledger. Spends nothing.

    PYTHONPATH=src python scripts/record_nightly_form.py

The three hypotheses registered in `docs/preregistered_nightly_form.md`, under
the names fixed there, with outcomes read from the run record
(`data/outputs/nightly_form.json`) rather than typed here — a number in this
file would be a second copy that nothing compares with the first.

No unregistered look was taken: the study ran its three regressions and its
registered 2025 sign check, and nothing else was put to the data.

**`experiment_ledger.md` is deliberately not re-rendered.** The allowlist
receipt for this lab cites it, by checksum, as evidence; the policy gate fails
the build when cited evidence changes under a receipt, and refreshing a
receipt's evidence is Cooper's decision, not a script's. The JSON is the
record and the Ledger Guard checks it; the Markdown trails it until then.
"""

from __future__ import annotations

import json
from pathlib import Path

from ncaaf_betting_lab.experiment_ledger import (
    LEDGER_FILENAME,
    Hypothesis,
    load,
    save,
)

OUTPUTS = Path("data/outputs")
LEDGER = OUTPUTS / LEDGER_FILENAME
RECORD = OUTPUTS / "nightly_form.json"
SEARCH = "nightly-form"


def outcome(name: str, r: dict) -> str:
    low, high = r["interval"]
    excludes = low > 0 or high < 0
    head = "interval excludes zero" if excludes else "no demonstrated edge"
    return (
        f"{head}; slope {r['slope']:+.4f}, SE {r['standard_error']:.4f}, "
        f"n = {r['games']:,} games over {r['clusters']} clusters, corrected "
        f"interval [{low:+.4f}, {high:+.4f}]; registered {r['direction'].upper()}, "
        f"pays at {r['paying']:+.3f}, detects {r['detectable']:.3f}; 2025 alone "
        f"{r['slope_2025']:+.4f} (n = {r['games_2025']:,})."
    )


def main() -> None:
    record = json.loads(RECORD.read_text())
    seasons = tuple(record["seasons"])
    ledger = load(LEDGER)
    before = ledger.count
    added = ledger.record(
        *(
            Hypothesis(
                search=SEARCH, name=name, tested_on=record["measured_on"],
                seasons=seasons, outcome=outcome(name, result),
            )
            for name, result in record["results"].items()
        )
    )
    save(ledger, LEDGER)
    print(
        f"{before} -> {ledger.count} hypotheses (+{added}), "
        f"x{ledger.correction_factor():.4f}"
    )


if __name__ == "__main__":
    main()
