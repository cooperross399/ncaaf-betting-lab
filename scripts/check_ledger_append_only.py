#!/usr/bin/env python3
"""Refuse a diff that removes or rewrites a hypothesis the base already recorded.

    python scripts/check_ledger_append_only.py --base BASE.json --head HEAD.json
    python scripts/check_ledger_append_only.py --base-absent --head HEAD.json

`ExperimentLedger.save()` raises when a ledger would shrink, but it only sees
writes that travel through the code, and `scripts/record_experiments.py` loads
the ledger and saves that same object back to the same path — so
`len(new) == len(existing)` on every run and the runtime shrink guard can never
fire. Delete an entry from the tracked JSON by hand and the recorder re-renders
it without complaint, `git diff --exit-code` stays clean, and the printed
correction factor comes out byte-identical. Nothing in the repository notices.
This script is the half that reads the base commit, so a removal has to get
past a comparison rather than past a no-op.

A count check alone is not that comparison. Drop the hypothesis that failed,
append a fresh one in its place, and the count is unchanged while the
correction now rests on a family that quietly lost its most inconvenient
member. So the merge key is (search, name, seasons) — the same key
`Hypothesis.key()` uses — and every surviving key must still carry the base's
`outcome` and `tested_on` verbatim.

Nor is a key-by-key comparison that comparison on its own. Reduce each side to
one record per key and a side that disagrees with ITSELF reads as clean.
Measured by running this script: base `[X]` against head `[X, A('no
demonstrated edge'), A('+2.1% ROI, significant')]` exited 0 and reported the
contradictory pair as an append; the next run inherited both, and dropping the
later copy exited 0 as well — the count was held up by the copy that stayed,
the key was still present, and the survivor matched the record the base side
had frozen. So `contradictions()` runs over BOTH sides *before* the comparison:
a ledger may not hold two records under one key that disagree about what was
found. That is not an append, it is a contradiction, and whichever copy
survives the next run is a choice nobody recorded.

What that pass does not reach is not described here, because a docstring is not
a check. It is asserted by running this script, in
`test_known_gaps_that_still_get_through` in
`tests/test_check_ledger_append_only.py`: contradictions are read on
`FROZEN_FIELDS` only, an appended hypothesis is taken on trust whatever it
claims to have found, `--base` is believed to be the base, and the merge key is
literal — the same span written `[2021, 2022]` and `[2022, 2021]` is two keys,
so a pair split across the two spellings never meets.

Standard library only. The workflow step runs this without `PYTHONPATH=src`,
so it cannot import `ncaaf_betting_lab`; the correction arithmetic below is
deliberately duplicated from `experiment_ledger.py` rather than imported.

Nothing in the workflow holds the two copies together. Its re-render step runs
`scripts/record_experiments.py`, which imports the package and never reads this
file: set `ALPHA` here to 0.10 with the package left at 0.05 and that step
still prints its usual count, `git diff --exit-code` still passes, and both
tracked ledger files come back byte-identical — green, over a gate quoting an
arithmetic the lab does not use. The only thing that notices is
`test_the_scripts_arithmetic_matches_the_package` in
`tests/test_check_ledger_append_only.py`, which may import the package and
holds `ALPHA` and `correction_factor` against it directly. Drift either value
and that test is what goes red.

There is no `--force`, no allowlist and no environment waiver. A gate with a
waiver is a gate that will be waived.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import NormalDist

#: The nominal two-sided level every interval in this lab is quoted at. Same
#: value as `experiment_ledger.ALPHA`; see the module docstring for why it is
#: restated instead of imported.
ALPHA = 0.05

#: The fields an entry must carry to be a record of anything. `seasons` is
#: handled separately because it is a list of ints rather than a string.
TEXT_FIELDS = ("search", "name", "tested_on", "outcome")

#: What the base and the head must agree on for a hypothesis that appears in
#: both. The key identifies the test; these say what it found and when — which
#: is the part an edit would rewrite to make a failure look like a finding.
FROZEN_FIELDS = ("outcome", "tested_on")


class LedgerError(Exception):
    """A ledger that cannot be read or trusted. Always a failure, never a skip:
    "I could not read it" and "it was fine" must not share an exit code."""


def correction_factor(count: int) -> float:
    """Bonferroni on the cumulative count, as `ExperimentLedger` computes it.

    Restated here because this script runs without the package on the path.
    The value is printed, not enforced *here*, so a drift between the two would
    otherwise show up only as a number disagreeing with the rendered ledger in
    the same job log. `test_the_scripts_arithmetic_matches_the_package` holds
    this function against `ExperimentLedger.correction_factor` directly — the
    test suite may import the package even though this script may not.
    """
    families = max(count, 1)
    if families == 1:
        return 1.0
    return NormalDist().inv_cdf(1 - (ALPHA / families) / 2) / 1.96


def read_ledger(path: Path, side: str) -> list[dict]:
    """The `hypotheses` list, or a `LedgerError` naming what was wrong.

    Every rejection here is a rejection of a file that could still be *some*
    valid JSON. What these checks buy is the message, not the verdict: delete
    them and the bad ledgers below do not slip through green, they crash or
    misreport.

    Drop the `TEXT_FIELDS` presence check and an entry missing `outcome`
    travels on to `compare()`, which raises `KeyError: 'outcome'` reading it —
    a traceback about a dict, out of a step whose job is to say what happened
    to a hypothesis. Drop the `isinstance(entry, dict)` check and a bare-string
    entry does something worse than it looks: `field not in entry` is substring
    containment on a str, so the plain case is refused as "missing 'search'" —
    a complaint about one field, for a value that has no fields at all — while
    a string that happens to contain each field name as a substring gets past
    even that and raises `TypeError: string indices must be integers` at
    `entry[field]`, the same error `key()` raises on it.

    So each check here exists to turn a crash or a misdirected complaint into a
    `LedgerError` that names the side, the entry index and the field, which is
    what a reviewer reads off a red run.
    """
    if not path.is_file():
        raise LedgerError(f"the {side} ledger {path} does not exist")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LedgerError(f"the {side} ledger {path} could not be read: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        # A zero-byte file lands here too, which matters: an empty ledger that
        # parsed as zero hypotheses would read as a clean comparison against
        # nothing.
        raise LedgerError(
            f"the {side} ledger {path} is not parseable JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise LedgerError(
            f"the {side} ledger {path} is a {type(payload).__name__}, not a JSON "
            "object with a 'hypotheses' key"
        )
    entries = payload.get("hypotheses")
    if not isinstance(entries, list):
        raise LedgerError(
            f"the {side} ledger {path} has no 'hypotheses' list "
            f"(found {type(entries).__name__})"
        )
    for index, entry in enumerate(entries):
        where = f"{side} entry {index}"
        if not isinstance(entry, dict):
            raise LedgerError(
                f"{where} is a {type(entry).__name__}, not an object"
            )
        for field in TEXT_FIELDS:
            if field not in entry:
                raise LedgerError(f"{where} is missing '{field}'")
            if not isinstance(entry[field], str):
                raise LedgerError(
                    f"{where} has '{field}' as a {type(entry[field]).__name__}, "
                    "not a string"
                )
        if "seasons" not in entry:
            raise LedgerError(f"{where} is missing 'seasons'")
        seasons = entry["seasons"]
        if not isinstance(seasons, list):
            raise LedgerError(
                f"{where} has 'seasons' as a {type(seasons).__name__}, not a list"
            )
        for season in seasons:
            # A bool season keys *equal* to the int, not differently:
            # ('s', 'n', (True,)) == ('s', 'n', (1,)) and the two hash alike,
            # so `key()` cannot tell them apart. That is the failure this
            # catches — a season rewritten from 1 to `true` passes the
            # comparison in `compare()` as the very same hypothesis, so the
            # edit is invisible to the gate and the entry it produces is a
            # season nobody wrote. And `isinstance(True, int)` is True, so a
            # plain int check would admit it; the bool has to be named.
            if not isinstance(season, int) or isinstance(season, bool):
                raise LedgerError(
                    f"{where} has a season that is a {type(season).__name__}, "
                    "not an int"
                )
    return entries


def key(entry: dict) -> tuple[str, str, tuple[int, ...]]:
    """What makes two entries the same test — `Hypothesis.key()` restated.

    Seasons are part of it: the same question asked of a different span is a
    different look at the data and costs its own degree of freedom.
    """
    return (entry["search"], entry["name"], tuple(entry["seasons"]))


def describe(entry_key: tuple[str, str, tuple[int, ...]]) -> str:
    search, name, seasons = entry_key
    span = ", ".join(str(season) for season in seasons) or "no seasons"
    return f"{search} / {name} ({span})"


def contradictions(
    entries: list[dict], side: str
) -> tuple[list[str], dict[tuple[str, str, tuple[int, ...]], dict]]:
    """Every place one side disagrees with itself, and its first record per key.

    A ledger may not hold two records under one key that disagree about what
    was found. The key says they are the same test; `FROZEN_FIELDS` say they
    found different things. That is not an append, it is a contradiction, and
    whichever copy survives the next run is a choice nobody recorded.

    This runs over both sides and before the base/head comparison, because that
    comparison cannot see it: `compare()` reduces each side to one record per
    key, so a contradictory pair arrives as a single record and reads as clean.
    Measured, not reasoned — see the module docstring for the base and head
    that exited 0 with the pair intact, and for the erasure that exited 0 after
    it.

    The map handed back is the first record under each key on this side, and it
    is the same object `compare()` uses as `base_by_key`. Built here and
    returned rather than rebuilt there, because two maps built by two loops can
    disagree about which record is the base's — and that disagreement is the
    whole of what this function exists to remove.
    """
    problems: list[str] = []
    first_by_key: dict[tuple[str, str, tuple[int, ...]], dict] = {}
    first_index: dict[tuple[str, str, tuple[int, ...]], int] = {}
    for index, entry in enumerate(entries):
        entry_key = key(entry)
        first = first_by_key.setdefault(entry_key, entry)
        if first is entry:
            first_index[entry_key] = index
            continue
        for field in FROZEN_FIELDS:
            if entry[field] != first[field]:
                problems.append(
                    f"the {side} ledger contradicts itself: "
                    f"{describe(entry_key)} — '{field}' is {first[field]!r} in "
                    f"{side} entry {first_index[entry_key]} and "
                    f"{entry[field]!r} in {side} entry {index}. One key, two "
                    "answers to what the test found: whichever copy survives "
                    "the next run is a choice nobody recorded."
                )
    return problems, first_by_key


def compare(base: list[dict], head: list[dict]) -> tuple[list[str], int]:
    """Every way the head betrays the base, and how many keys were checked.

    Returns the problems rather than raising on the first, so a reviewer sees
    the whole edit in one run instead of one entry per push.
    """
    problems: list[str] = []

    # Before anything is compared across sides, each side has to agree with
    # itself. A contradiction that lands here is not caught later: the loops
    # below see one record per base key, so the pair reads as a clean append,
    # and the run after it can delete either copy.
    base_problems, base_by_key = contradictions(base, "base")
    head_problems, _ = contradictions(head, "head")
    problems.extend(base_problems)
    problems.extend(head_problems)

    if len(head) < len(base):
        problems.append(
            f"the ledger falls from {len(base)} entries to {len(head)}. It is "
            "append-only: the tests that failed are what make a surviving one "
            "unlikely to be chance, and a ledger that can shrink reports a "
            "correction smaller than the truth."
        )

    # `base_by_key` is the first record per key that `contradictions()` already
    # built. First occurrence wins there, which is safe only because a later
    # base record that disagreed with it has already been reported above; on
    # its own, "first wins" is how the base quietly forgets the copy it did not
    # freeze. The head side keeps every entry sharing a key, so a copy that
    # agrees with its neighbours and disagrees with the base is still named.
    head_by_key: dict[tuple[str, str, tuple[int, ...]], list[dict]] = {}
    for entry in head:
        head_by_key.setdefault(key(entry), []).append(entry)

    compared = 0
    for entry_key, base_entry in base_by_key.items():
        matches = head_by_key.get(entry_key)
        if not matches:
            problems.append(f"removed from the ledger: {describe(entry_key)}")
            continue
        compared += 1
        for head_entry in matches:
            for field in FROZEN_FIELDS:
                if head_entry[field] != base_entry[field]:
                    # The count can be untouched and this still fires. Swapping
                    # a failed outcome for a successful one keeps the family
                    # size and destroys what the family was evidence of.
                    problems.append(
                        f"rewritten in the ledger: {describe(entry_key)} — "
                        f"'{field}' was {base_entry[field]!r}, is now "
                        f"{head_entry[field]!r}"
                    )
    return problems, compared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    origin = parser.add_mutually_exclusive_group(required=True)
    # Exactly one, and neither is a default. "There was no ledger at the base"
    # is a claim the caller has to make on purpose; it must never be what the
    # script assumes when it was handed nothing.
    origin.add_argument(
        "--base",
        type=Path,
        help="the ledger as it stands at the base commit",
    )
    origin.add_argument(
        "--base-absent",
        action="store_true",
        help="there was no ledger at the base commit — an honest first commit",
    )
    parser.add_argument(
        "--head",
        type=Path,
        required=True,
        help="the ledger as it stands on this branch",
    )
    args = parser.parse_args(argv)

    try:
        head = read_ledger(args.head, "head")
        base = read_ledger(args.base, "base") if args.base is not None else None
    except LedgerError as exc:
        print(f"Ledger check FAILED: {exc}", file=sys.stderr)
        return 1

    # First line, because the workflow's Summarise step takes `head -n 1` of
    # this output. The count is the sample size the factor is derived from, so
    # the two travel together the way they do everywhere else in this lab.
    distinct = len({key(entry) for entry in head})
    print(
        f"{distinct} distinct hypotheses in the head ledger ({len(head)} entries). "
        f"Any new 95% interval widens by x{correction_factor(distinct):.2f}."
    )

    if base is None:
        # No base is not no check on this: there is nothing to compare the head
        # against, but the head can still disagree with itself, and a first
        # commit is exactly where a contradictory pair would be planted so that
        # every later run inherits it as history.
        problems, _ = contradictions(head, "head")
        compared = 0
    else:
        problems, compared = compare(base, head)
        if not problems and compared == 0:
            # The fail-open case. A base was handed over and not one of its
            # hypotheses was checked against the head, so this run is evidence
            # of nothing — and a check that compared nothing must not report
            # green.
            problems.append(
                "base was present but nothing was compared "
                f"({len(base)} base entries, {len(head)} head entries)"
            )

    if problems:
        # stdout is a pipe in the workflow (`| tee`) and therefore block
        # buffered, while stderr is not. Without this the failure prints above
        # the count it is about, and the log reads as if a different ledger was
        # measured from the one that was rejected.
        sys.stdout.flush()
        print("Ledger check FAILED. The ledger is append-only.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if base is None:
        print("No ledger at the base commit: first-commit state, nothing to compare.")
        return 0

    print(
        f"{compared} base hypotheses compared, all present with an identical "
        f"outcome and tested_on. {len(head) - len(base)} appended."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
