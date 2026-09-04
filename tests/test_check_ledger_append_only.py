"""The append-only gate, exercised without pushing a PR.

`.github/workflows/ledger-guard.yml` is the only place this script runs for
real, and a workflow can only be tested by merging it. So the comparison lives
in a script and the script's failures live here: every one of these cases is an
edit that reaches `main` today. The removal case is not hypothetical —
`scripts/record_experiments.py` loads and saves the same ledger object to the
same path, so the runtime shrink guard in `save()` sees `len(new) ==
len(existing)` every run and cannot fire; a hand-deleted hypothesis re-renders
clean and prints an unchanged correction factor.

The tests that matter most are the equal-count ones. A gate that only counts
passes an edit that drops the failure and appends a replacement, and that edit
is the one someone would actually make.

The duplicate-key shape belongs to that family and is the least obvious member:
one base entry, several head entries under its key, one of them disagreeing
about the outcome. The count grew, the key is still there, and both the loop
over *every* match in `compare()` and the contradiction pass reject it. Where
the rewrite sits among the copies is parametrized, because a loop truncated to
one end still catches the copy it happens to reach and would otherwise look
pinned.

Its worse relative is the pair that never touches a base key at all: two head
records under ONE NEW key that disagree with each other. Nothing is removed,
nothing is rewritten, the count only grows — and the gate used to report it as
a clean append, after which either copy could be deleted by the next run. That
is what `contradictions()` refuses on both sides, and what
`test_a_contradictory_pair_cannot_land` and
`test_an_inherited_contradiction_cannot_be_resolved_by_erasure` pin from both
ends: the pair cannot land, and if one is already there it cannot be quietly
settled.

`test_known_gaps_that_still_get_through` is the other half of that honesty. It
runs the script over the edits it still passes and asserts the exit code is 0,
so what this gate does not cover is a recorded fact that goes red when it
changes, rather than a sentence in a docstring that nobody re-checks.

This file is also the only thing holding the script's `ALPHA` and Bonferroni
factor against the package's. The workflow's re-render step runs
`scripts/record_experiments.py`, which imports the package and never reads the
script, so a value drifted in the script leaves that step green — see
`test_the_scripts_arithmetic_matches_the_package`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

#: Loaded by path: `scripts/` is not a package and is not on `pythonpath`, and
#: the workflow invokes the file the same way — as a script, with no package
#: import available to it.
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_ledger_append_only.py"
_spec = importlib.util.spec_from_file_location("check_ledger_append_only", _SCRIPT)
assert _spec is not None and _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

#: The asymmetry that makes the duplication testable: the *script* cannot
#: import the package (the workflow step runs it without `PYTHONPATH=src`), but
#: this test file can, because pytest puts `src` on the path — `pythonpath =
#: ["src"]` in pyproject. So the two copies of the arithmetic get held against
#: each other here, in `test_the_scripts_arithmetic_matches_the_package`.
from ncaaf_betting_lab import experiment_ledger  # noqa: E402


def entry(
    name: str,
    *,
    search: str = "margin-shape",
    seasons: tuple[int, ...] = (2021, 2022),
    tested_on: str = "2026-09-03",
    outcome: str = "no demonstrated edge",
) -> dict:
    return {
        "search": search,
        "name": name,
        "tested_on": tested_on,
        "seasons": list(seasons),
        "outcome": outcome,
    }


def write(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps({"hypotheses": entries}, indent=2) + "\n", encoding="utf-8")
    return path


def run(tmp_path: Path, base: list[dict] | None, head: list[dict]) -> int:
    head_path = write(tmp_path / "head.json", head)
    if base is None:
        return check.main(["--base-absent", "--head", str(head_path)])
    base_path = write(tmp_path / "base.json", base)
    return check.main(["--base", str(base_path), "--head", str(head_path)])


THREE = [entry("bandwidth 0.5"), entry("bandwidth 0.7"), entry("bandwidth 0.9")]


def test_a_clean_append_passes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = run(tmp_path, THREE, THREE + [entry("bandwidth 1.2")])

    assert code == 0
    out = capsys.readouterr().out
    assert "3 base hypotheses compared" in out


def test_the_first_line_carries_the_count_beside_the_factor(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The workflow's Summarise step does `head -n 1` on this output, and the
    lab's rule is that no measured number travels without its sample size."""
    run(tmp_path, THREE, THREE)

    first = capsys.readouterr().out.splitlines()[0]
    assert "3 distinct hypotheses" in first
    # The literal, not `check.correction_factor(3)`. Printing the value and
    # expecting the value from the same call holds for whatever that call
    # returns, which is exactly the drift this file exists to catch. Three
    # distinct hypotheses at ALPHA = 0.05 give 1.2214182652135255.
    assert "x1.22" in first


def test_the_scripts_arithmetic_matches_the_package() -> None:
    """The guard that makes the duplication safe.

    `check_ledger_append_only` restates `ALPHA` and the Bonferroni factor
    instead of importing them, because the workflow step runs the script
    without `PYTHONPATH=src`. Nothing else in the repository compares the two
    copies, so a change to `experiment_ledger.ALPHA` or to
    `ExperimentLedger.correction_factor` would leave the gate quoting the old
    arithmetic in the same job log as the new ledger. This is that comparison.
    """
    assert check.ALPHA == experiment_ledger.ALPHA

    empty = experiment_ledger.ExperimentLedger()
    # An empty ledger counts zero, so `extra` is the whole family size — the
    # same argument the script's module-level `correction_factor` takes.
    assert empty.count == 0
    for count in range(0, 201):
        assert check.correction_factor(count) == empty.correction_factor(
            extra=count
        ), f"the two correction factors disagree at count={count}"


def test_a_removal_fails_even_when_the_count_grew(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Drop one, append two. `len(head) >= len(base)` holds and the ledger has
    still lost a degree of freedom it was corrected against."""
    head = THREE[:2] + [entry("bandwidth 1.2"), entry("bandwidth 1.5")]

    code = run(tmp_path, THREE, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "removed from the ledger" in err
    assert "bandwidth 0.9" in err


def test_a_count_decrease_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = run(tmp_path, THREE, THREE[:2])

    assert code == 1
    err = capsys.readouterr().err
    assert "falls from 3 entries to 2" in err


def test_an_equal_count_outcome_swap_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The subtle attack: same key, same count, a failure turned into a
    finding. A gate that only compares lengths reports green on this."""
    head = list(THREE)
    head[1] = entry("bandwidth 0.7", outcome="+2.1% ROI, significant")

    code = run(tmp_path, THREE, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err
    assert "'outcome'" in err


def duplicated_head(rewritten_at: int) -> list[dict]:
    """Three head entries under one key, one of them rewritten.

    `compare()` keeps the first base entry per key and *every* head entry that
    shares it, which is the branch this shape exists to exercise: two records
    under one key that disagree about what the test found is the ambiguity a
    rewrite needs. Which copy carries the rewrite is parametrized because a
    loop that stops early still catches the rewrite it happens to reach —
    `matches[:1]` passes a last-position rewrite and `matches[-1:]` passes a
    first-position one, and neither truncation is visible from a single
    position.

    This shape now trips `contradictions()` as well, since the copies disagree
    with each other. The asserts below stay on the `rewritten in the ledger`
    line specifically, so they keep pinning the match loop rather than sliding
    over to whichever check happens to fire first.
    """
    copies = [entry("bandwidth 0.5") for _ in range(3)]
    copies[rewritten_at] = entry("bandwidth 0.5", outcome="+2.1% ROI, significant")
    return copies


@pytest.mark.parametrize("rewritten_at", [0, 1, 2])
def test_a_duplicate_key_rewrite_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture, rewritten_at: int
) -> None:
    """The attack the gate exists for, wearing a duplicate key.

    The count never falls — one base entry becomes three head entries — and the
    key is still present, so both the shrink check and the removal check are
    satisfied. What changed is that one of the copies now reports a finding
    where the base recorded a failure. Only the loop over every match rejects
    this; truncate it and this edit reaches `main` with a green tick.
    """
    base = [entry("bandwidth 0.5")]

    code = run(tmp_path, base, duplicated_head(rewritten_at))

    assert code == 1
    err = capsys.readouterr().err
    rewrites = [line for line in err.splitlines() if "rewritten in the ledger" in line]
    assert rewrites, err
    assert "'outcome'" in err
    # Both sides of the swap, in the order the message claims: "was X, is now
    # Y". A report that names the two outcomes but not which one the base held
    # tells a reviewer nothing about the direction of the edit. Read off the
    # rewrite line rather than off the whole of stderr: every other line here
    # names those same two outcomes, so a whole-stderr `index()` comparison
    # would be satisfied by a line that makes no claim about direction at all.
    for line in rewrites:
        assert "'no demonstrated edge'" in line
        assert "'+2.1% ROI, significant'" in line
        assert line.index("'no demonstrated edge'") < line.index(
            "'+2.1% ROI, significant'"
        )


def test_duplicating_an_entry_verbatim_is_not_itself_a_rewrite(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The control for the test above.

    Three identical copies pass, so the failure there is the disagreement
    between copies and not the mere presence of duplicates — without this, a
    guard that refused every duplicate key would look like it had pinned the
    branch. It also pins the count line for the shape: repeated entries are one
    distinct hypothesis and cost one degree of freedom, while the entry count
    that the distinct count was drawn from travels beside it.
    """
    base = [entry("bandwidth 0.5")]
    head = [entry("bandwidth 0.5") for _ in range(3)]

    code = run(tmp_path, base, head)

    assert code == 0
    out = capsys.readouterr().out
    assert "1 distinct hypotheses in the head ledger (3 entries)" in out
    # One family corrects by nothing; three entries under one key must not
    # widen an interval by pretending to be three looks at the data.
    assert "x1.00" in out
    assert "1 base hypotheses compared" in out


#: The pair the gate used to wave through, and the reason it could. Two records
#: under ONE key that disagree about what was found is not an append: the key
#: says they are the same test, the outcomes say they found different things,
#: and nothing in the file says which one is the record. Measured on the
#: unmutated script before `contradictions()` existed — base `[X]` against a
#: head holding `[X]` and both of these exited 0 and reported the pair as
#: appended, and the run after it could delete either copy.
POISONED = [
    entry("bandwidth 0.7"),
    entry("bandwidth 0.7", outcome="+2.1% ROI, significant"),
]


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_a_contradictory_pair_cannot_land(
    tmp_path: Path, capsys: pytest.CaptureFixture, order: tuple[int, int]
) -> None:
    """The head may not disagree with itself about what a test found.

    Nothing here is removed and nothing is rewritten against the base — the
    base does not even hold this key. The count only grows. Every other check
    in the script is therefore satisfied, which is exactly why this was the
    shape that got through: `compare()` reduces the head to one record per key
    before it compares anything, so the pair arrives as a single record.

    Both orders, because the comparison is between a later copy and the first
    and a check written in one direction would pass whichever arrangement it
    happened to be handed.
    """
    head = [entry("bandwidth 0.5")] + [POISONED[i] for i in order]

    code = run(tmp_path, [entry("bandwidth 0.5")], head)

    assert code == 1
    err = capsys.readouterr().err
    assert "the head ledger contradicts itself" in err
    # The key, both values and where each one sits. A reviewer cannot act on
    # "there is a contradiction somewhere"; the message has to say which
    # hypothesis, which field, and which two records.
    assert "margin-shape / bandwidth 0.7 (2021, 2022)" in err
    assert "'outcome'" in err
    assert "'no demonstrated edge'" in err
    assert "'+2.1% ROI, significant'" in err
    assert "head entry 1" in err
    assert "head entry 2" in err


@pytest.mark.parametrize("survivor", [0, 1])
def test_an_inherited_contradiction_cannot_be_resolved_by_erasure(
    tmp_path: Path, capsys: pytest.CaptureFixture, survivor: int
) -> None:
    """The second half of the attack, and the reason the pass runs on the base.

    Once a contradictory pair is in the base, deleting whichever copy you
    dislike is invisible to every other check: the count is held up by the copy
    that stayed, the key is still present, and the survivor matches the record
    the base side froze. Measured on the unmutated script, base `[X, A('no
    demonstrated edge'), A('+2.1% ROI, significant')]` against head `[X, A, A]`
    keeping the first copy exited 0. Keeping the *second* was refused, and only
    by accident: it disagreed with the copy `setdefault` happened to freeze.
    A gate whose verdict depends on which contradictory record came first is
    not deciding anything.

    So the base is checked against itself too, and both erasures are refused —
    not because the survivor is wrong, but because the pair should never have
    been in the base and this script is not the place that gets settled
    silently.
    """
    base = [entry("bandwidth 0.5")] + POISONED
    head = [entry("bandwidth 0.5"), POISONED[survivor], dict(POISONED[survivor])]

    code = run(tmp_path, base, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "the base ledger contradicts itself" in err
    assert "base entry 1" in err
    assert "base entry 2" in err


def test_a_contradiction_is_refused_on_the_first_commit_path(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`--base-absent` is where a pair would be planted so it arrives as history.

    There is nothing to compare a first commit against, but a first commit can
    still disagree with itself, and the run after it inherits whatever landed.
    No base is not no check.
    """
    code = run(tmp_path, None, [entry("bandwidth 0.5")] + POISONED)

    assert code == 1
    err = capsys.readouterr().err
    assert "the head ledger contradicts itself" in err
    # And it must not also report the clean first-commit line: a run that says
    # both "FAILED" and "nothing to compare" reads as a gate that shrugged.
    assert "first-commit state" not in capsys.readouterr().out


def test_a_contradiction_about_tested_on_is_a_contradiction_too(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Both frozen fields, not just the interesting one.

    Re-dating one copy of a pair is the same trick as re-outcoming it: two
    records claiming the same test ran on two different days, and no way to
    say which look the correction is counting.
    """
    head = [
        entry("bandwidth 0.5"),
        entry("bandwidth 0.5", tested_on="2026-10-01"),
    ]

    code = run(tmp_path, [entry("bandwidth 0.5")], head)

    assert code == 1
    err = capsys.readouterr().err
    assert "the head ledger contradicts itself" in err
    assert "'tested_on'" in err
    assert "'2026-09-03'" in err
    assert "'2026-10-01'" in err


def test_every_later_copy_is_reported_not_just_the_first_disagreement(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Three copies, three different outcomes, two contradictions named.

    A pass that stopped at the first disagreement would report one line and
    look identical from the exit code, leaving a reviewer to fix the copy they
    were shown and push again into the same red.
    """
    head = [
        entry("bandwidth 0.5"),
        entry("bandwidth 0.7"),
        entry("bandwidth 0.7", outcome="+2.1% ROI, significant"),
        entry("bandwidth 0.7", outcome="+9.9% ROI, significant"),
    ]

    code = run(tmp_path, [entry("bandwidth 0.5")], head)

    assert code == 1
    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if "contradicts itself" in line]
    assert len(lines) == 2, err
    # Each later copy is measured against the first, and each names its own
    # position, so the two lines are two distinct records rather than one
    # complaint printed twice.
    assert "head entry 2" in lines[0] and "'+2.1% ROI, significant'" in lines[0]
    assert "head entry 3" in lines[1] and "'+9.9% ROI, significant'" in lines[1]


def test_verbatim_duplicates_are_still_not_a_contradiction(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The control for the pass, distinct from the control for the match loop.

    Copies that agree are a redundant ledger, not a dishonest one. Without
    this, a pass that refused every repeated key would look like it had pinned
    the branch while actually refusing the shape
    `test_duplicating_an_entry_verbatim_is_not_itself_a_rewrite` requires to
    pass — and the two would only be caught disagreeing by whichever ran last.
    """
    base = [entry("bandwidth 0.5")]
    head = [entry("bandwidth 0.5") for _ in range(4)]

    assert run(tmp_path, base, head) == 0
    assert "contradicts itself" not in capsys.readouterr().err


def test_the_rewrite_message_quotes_the_record_the_comparison_used(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """First occurrence wins on the base side, and the message has to say so.

    Once the base contradicts itself the run is red whichever copy the map
    froze: over 4,000 randomized base/head pairs, swapping the base map from
    first-wins to last-wins changed no exit code and changed only which record
    the `rewritten in the ledger` line quotes as "was" — and every one of those
    differing runs was on a base that already contradicted itself. That is
    still worth pinning: on such a run stderr already carries a contradiction
    line naming both base values, and a rewrite line quoting the *other* one
    hands the reviewer two different "base" outcomes with nothing to say which
    the comparison actually used.
    """
    base = [
        entry("bandwidth 0.7"),
        entry("bandwidth 0.7", outcome="+2.1% ROI, significant"),
    ]
    head = [entry("bandwidth 0.7", outcome="+9.9% ROI, significant")]

    code = run(tmp_path, base, head)

    assert code == 1
    err = capsys.readouterr().err
    rewrites = [line for line in err.splitlines() if "rewritten in the ledger" in line]
    assert rewrites, err
    for line in rewrites:
        assert "was 'no demonstrated edge'" in line
        assert "was '+2.1% ROI, significant'" not in line


def test_known_gaps_that_still_get_through(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """What this gate does NOT catch, asserted by running it rather than said.

    Every case below exits 0 today. That is the point of writing them down
    here: a limitation recorded as a passing assertion goes red the day it is
    closed and has to be re-read, while a limitation recorded in a docstring
    quietly becomes a false claim. None of these is a waiver — nothing here
    turns a red run green — they are the edges of the guarantee.

    If one of these starts failing, the gate got stronger: delete the case and
    move the sentence out of the "does not" list, do not weaken the check.
    """
    # 1. Contradictions are read on FROZEN_FIELDS only. Two records under one
    #    key that disagree about anything else are not seen. Today's entries
    #    carry nothing else, so this is latent rather than live — and it goes
    #    live the day the ledger records the sample size beside the outcome,
    #    which is the discipline this lab holds everywhere else.
    loud = entry("bandwidth 0.5")
    loud["games"] = "n = 3864"
    quiet = entry("bandwidth 0.5")
    quiet["games"] = "n = 12"
    assert run(tmp_path, [entry("bandwidth 0.5")], [loud, quiet]) == 0

    # 2. An appended hypothesis is taken on trust, whatever it claims to have
    #    found. This gate compares the head to the base; it has no way to know
    #    whether a test that appears for the first time was ever run. Inventing
    #    a finding is not an edit to the base and nothing here can see it.
    assert (
        run(
            tmp_path,
            THREE,
            THREE + [entry("bandwidth 1.2", outcome="+9.9% ROI, significant")],
        )
        == 0
    )

    # 3. `--base` is believed. Hand the same file to both flags and every
    #    comparison is satisfied by construction, whatever the file says.
    #    Resolving the true base ref is the workflow's job, and its own hard
    #    stop when it cannot; from inside this script the two are
    #    indistinguishable.
    invented = write(
        tmp_path / "head.json",
        [entry("bandwidth 0.5", outcome="+9.9% ROI, significant")],
    )
    assert check.main(["--base", str(invented), "--head", str(invented)]) == 0

    # 4. The merge key is literal, so the same test written two ways is two
    #    keys and the pair never meets. `[2021, 2022]` and `[2022, 2021]` are
    #    the same span and key differently; so do names that differ by
    #    whitespace. Found by attacking the pass, not by reading it. Not closed
    #    here on purpose: `key()` restates `Hypothesis.key()`, which is order-
    #    sensitive too, and normalising only this copy would put the gate's
    #    idea of a distinct hypothesis — and so the correction factor it prints
    #    — out of step with the ledger the lab actually keeps.
    spans = entry("bandwidth 0.7")
    reordered = entry(
        "bandwidth 0.7", seasons=(2022, 2021), outcome="+2.1% ROI, significant"
    )
    assert run(tmp_path, [entry("bandwidth 0.5")],
               [entry("bandwidth 0.5"), spans, reordered]) == 0
    spaced = entry("bandwidth 0.7 ", outcome="+2.1% ROI, significant")
    assert run(tmp_path, [entry("bandwidth 0.5")],
               [entry("bandwidth 0.5"), spans, spaced]) == 0

    capsys.readouterr()


def test_an_equal_count_tested_on_swap_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Re-dating a test is how an old look gets laundered into a fresh one."""
    head = list(THREE)
    head[0] = entry("bandwidth 0.5", tested_on="2026-10-01")

    code = run(tmp_path, THREE, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err
    assert "'tested_on'" in err


def test_a_missing_head_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """An absent head is a broken check, not an empty ledger."""
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(
        ["--base", str(base_path), "--head", str(tmp_path / "nowhere.json")]
    )

    assert code == 1
    assert "does not exist" in capsys.readouterr().err


def test_a_blank_head_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A zero-byte file must not read as zero hypotheses, which would look like
    a clean comparison against nothing."""
    head_path = tmp_path / "head.json"
    head_path.write_text("", encoding="utf-8")
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert "not parseable JSON" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{not json", "not parseable JSON"),
        ('["a", "b"]', "not a JSON object"),
        ('{"hypotheses": {}}', "no 'hypotheses' list"),
        ('{"hypotheses": ["bandwidth 0.5"]}', "not an object"),
        ('{"entries": []}', "no 'hypotheses' list"),
    ],
)
def test_a_malformed_head_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture, payload: str, expected: str
) -> None:
    head_path = tmp_path / "head.json"
    head_path.write_text(payload, encoding="utf-8")
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert expected in capsys.readouterr().err


def test_an_entry_missing_outcome_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Without `outcome` there is nothing to hold constant, and every
    comparison against that entry would agree with anything."""
    stripped = entry("bandwidth 0.5")
    del stripped["outcome"]
    head_path = write(tmp_path / "head.json", [stripped])
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert "missing 'outcome'" in capsys.readouterr().err


def test_a_mistyped_season_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Seasons are half the merge key: `"2021"` and `2021` key differently, so
    a string season is a hypothesis that can never be matched again."""
    bad = entry("bandwidth 0.5")
    bad["seasons"] = ["2021"]
    head_path = write(tmp_path / "head.json", [bad])
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert "not an int" in capsys.readouterr().err


def test_a_bool_season_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`true` is the mistyped season the key comparison cannot see.

    A string season keys differently and so can never be matched again; a bool
    keys *identically* to 1, which is worse — the asserts below are the reason
    `read_ledger` names bools instead of trusting `isinstance(season, int)`.
    """
    assert check.key({"search": "s", "name": "n", "seasons": [True]}) == check.key(
        {"search": "s", "name": "n", "seasons": [1]}
    )

    bad = entry("bandwidth 0.5")
    bad["seasons"] = [True]
    head_path = write(tmp_path / "head.json", [bad])
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert "not an int" in capsys.readouterr().err


#: `read_ledger` refuses a malformed `seasons` in four distinct ways: the field
#: is present, it is a list, its items are ints, and those ints are not bools.
#: A case per way, because deleting one of them does not make the ledger pass —
#: it makes a neighbouring step print the wrong thing, or makes the run die on
#: a dict operation, and both of those look like "still red" from a distance.
#: The message each case asserts is what tells those apart.
_ABSENT = object()


@pytest.mark.parametrize(
    ("seasons", "expected"),
    [
        # Presence: delete this step and `entry["seasons"]` raises
        # `KeyError: 'seasons'` a couple of lines later, inside `read_ledger`.
        pytest.param(_ABSENT, "is missing 'seasons'", id="absent"),
        # A list, not merely something iterable. Delete this step and a string
        # or a dict iterates into characters or keys and is reported as "a
        # season that is a str, not an int" — a complaint about an item, for a
        # field that has no items — while a number or a null raises
        # `TypeError: ... is not iterable` at the loop below.
        pytest.param("2021", "has 'seasons' as a str, not a list", id="string"),
        pytest.param(2021, "has 'seasons' as a int, not a list", id="number"),
        pytest.param({"2021": 1}, "has 'seasons' as a dict, not a list", id="object"),
        pytest.param(None, "has 'seasons' as a NoneType, not a list", id="null"),
        # Ints inside it: `"2021"` and `2021` key differently, so a string
        # season is a hypothesis that can never be matched again.
        pytest.param(["2021"], "has a season that is a str, not an int", id="str-season"),
        pytest.param([2021, None], "has a season that is a NoneType, not an int", id="null-season"),
        # And not a bool, which keys *identically* to 1 — see
        # `test_a_bool_season_fails` for why that is the worse of the two.
        pytest.param([True], "has a season that is a bool, not an int", id="bool-season"),
    ],
)
def test_every_seasons_branch_refuses_its_own_bad_input(
    tmp_path: Path, capsys: pytest.CaptureFixture, seasons: object, expected: str
) -> None:
    """Seasons are half the merge key, so every way of writing them wrong is a
    way of writing a hypothesis that cannot be compared to the one it replaced.
    Each case here is refused by exactly one step of that validation, and names
    the mistake it actually made."""
    bad = entry("bandwidth 0.5")
    if seasons is _ABSENT:
        del bad["seasons"]
    else:
        bad["seasons"] = seasons
    head_path = write(tmp_path / "head.json", [bad])
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert expected in capsys.readouterr().err


def test_base_absent_passes_on_a_valid_head(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    code = run(tmp_path, None, THREE)

    assert code == 0
    out = capsys.readouterr().out
    assert "3 distinct hypotheses" in out
    assert "first-commit state" in out


def test_base_absent_still_validates_the_head(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """No base is not no check. A malformed head is a failure on this branch
    too, or the first-commit path becomes the way past validation."""
    head_path = tmp_path / "head.json"
    head_path.write_text('{"hypotheses": [{"search": "s"}]}', encoding="utf-8")

    code = check.main(["--base-absent", "--head", str(head_path)])

    assert code == 1
    assert "missing 'name'" in capsys.readouterr().err


def test_a_base_that_compared_nothing_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A base with no entries parses, keeps the count check happy, and lets the
    loop run zero times. Nothing was verified, so nothing may be reported."""
    code = run(tmp_path, [], THREE)

    assert code == 1
    assert "base was present but nothing was compared" in capsys.readouterr().err


def test_neither_origin_flag_is_refused(tmp_path: Path) -> None:
    """The base state must be stated, never defaulted: a caller who forgets the
    flag must not get the branch that compares nothing."""
    head_path = write(tmp_path / "head.json", THREE)

    with pytest.raises(SystemExit) as excinfo:
        check.main(["--head", str(head_path)])

    assert excinfo.value.code == 2


def test_both_origin_flags_are_refused(tmp_path: Path) -> None:
    head_path = write(tmp_path / "head.json", THREE)
    base_path = write(tmp_path / "base.json", THREE)

    with pytest.raises(SystemExit) as excinfo:
        check.main(
            ["--base", str(base_path), "--base-absent", "--head", str(head_path)]
        )

    assert excinfo.value.code == 2


@pytest.mark.parametrize("waiver", ["--force", "--allow", "--skip"])
def test_no_waiver_flag_exists(tmp_path: Path, waiver: str) -> None:
    """A gate with a waiver is a gate that will be waived, so the absence of one
    is part of the contract rather than a coding-style preference."""
    head_path = write(tmp_path / "head.json", THREE[:2])
    base_path = write(tmp_path / "base.json", THREE)

    with pytest.raises(SystemExit) as excinfo:
        check.main(["--base", str(base_path), "--head", str(head_path), waiver])

    assert excinfo.value.code == 2


def test_no_environment_variable_turns_a_shrink_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The env is not an input here. Anything that reads it is a way to make a
    red run green from the workflow file, which is where the edit would land."""
    for name in ("LEDGER_GUARD", "SKIP_LEDGER_CHECK", "FORCE", "CI", "ALLOW_SHRINK"):
        monkeypatch.setenv(name, "1")

    assert run(tmp_path, THREE, THREE[:2]) == 1


def test_the_real_ledger_passes_against_itself(capsys: pytest.CaptureFixture) -> None:
    """The tracked ledger has to be readable by its own guard, and comparing it
    with itself is the append-of-nothing case the workflow sees on a PR that
    does not touch it."""
    tracked = _SCRIPT.resolve().parents[1] / "data" / "outputs" / "experiment_ledger.json"

    code = check.main(["--base", str(tracked), "--head", str(tracked)])

    assert code == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert "distinct hypotheses in the head ledger" in first
