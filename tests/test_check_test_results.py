"""The skip gate, exercised on XML instead of on a merged workflow.

The one place this gate runs for real is the `.github/workflows/tests.yml` step
whose command is `python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"`
— cited by its command and not by its position, because a step that gains a
neighbour renumbers every citation that counted steps. A workflow can only be
tested by merging it, so the logic lives in a script and the script's cases
live here, which is the reason the workflow comment gives for it being a script
and not an inline heredoc: "a gate that can drop a case deserves a test".

The case that matters most is not the clean pass. It is the pair at the bottom:
a required module that vanished, and one that is still listed but ran nothing.
Both are what `git rm tests/test_no_secrets_committed.py` looks like from
inside the evidence file, and both make the build GREENER — deleting the two
hard-rule guards drops every test in two files and still exits 0 — which is
exactly the trade the manifest exists to refuse. NO INTEGER IS QUOTED FOR THAT
DROP, in either half of it. The size of it is whatever
`pytest --collect-only -q tests/test_no_secrets_committed.py
tests/test_no_sibling_lab_import.py` reports today. An earlier revision quoted
an absolute ("118 passed") and it went stale inside its own session; the
revision after that quoted a delta instead, said in as many words that the
delta was the durable half, and the delta went stale too. Neither form is
durable. A number that has to be re-measured is not written down here.

The escape-hatch section below is deliberately NOT a text match on the script.
A guard that greps for spellings proves only that those spellings are absent,
and the two versions that did so were each defeated within hours by a
rewording. Nor is it, any longer, a check on which ACCESSORS the script uses:
that framing lost too, to `hash("waive") % 7 == 3`, which touches no `sys`
attribute, no `os`, no file and no argv, and which no rule can forbid without
forbidding a builtin every program may use. What is asserted now is that the
script's ANSWER does not move when its ambient input does — see `_sweep_arms`
and the comment block above it.

WHAT STILL GETS THROUGH, measured by splicing each of these into `check()` and
running this file against the result. Written down because a guard described as
closed is a guard nobody re-checks, and because three rounds have now been lost
by believing a docstring:

* A waiver keyed on a literal token nobody sampled — `skips = [s for s in skips
  if "zq7v" not in s]`, or `if str(path).endswith(".waive.xml")`. Both read
  nothing from outside the evidence, so no probe can see them, and the two
  sweeps that close their shape (`test_nothing_written_inside_a_skipped_element
  _can_excuse_it`, `test_the_verdict_follows_the_bytes_and_not_the_filename`)
  can only draw from tokens they generate. This is the residue, and it is the
  reason review still has to read `check()`.
* A waiver keyed on a value of a swept input that no arm happens to draw. The
  differential sweep varies each ambient over a FINITE set of arms, so it
  catches a waiver that fires for a fraction p of the values in a dimension
  with probability 1 - (1 - p)**N over that dimension's N arms, and misses it
  otherwise. The hash-seed dimension is where that bites: `hash_seed_selective`
  in `_SWEEP_HATCHES` is `hash("waive") % 7 == 3`, measured green through both
  sides of `_probe` and every AST rule, and exiting 0 on a one-skip junit; it is
  caught here only because that dimension's arm count is set well above 1/p for
  its p. A `hash()` predicate satisfied by one seed in a million survives this
  sweep: `hash("waive") % 1000003 == 7` was spliced in and measured, and it
  returned the same answer in every arm the sweep runs (the sample size is
  `_HASH_ARM_COUNT` seeds plus the other dimensions' arms, and the assertion
  messages print it rather than this docstring quoting a number that moves).
  What keeps that narrow is a tension worth naming: p is both the sweep's
  per-arm chance of catching the waiver AND the fraction of real runs it
  actually waives, so a predicate selective enough to hide here excuses almost
  no build. The exception is a run that PINS the seed — `PYTHONHASHSEED` set in
  the workflow's env would make a one-in-a-million predicate fire every time —
  and that is an edit to `.github/workflows/tests.yml`, which is
  `tests/test_workflows.py`'s to see and not this file's.
  Same shape for the sentinel dimension — a filename no arm creates is
  invisible to it — except there the open-side `_probe` covers the whole family
  by watching the stat() instead of guessing the name.
* Ambient inputs no arm varies at all: the umask, TZ, the uid, resource limits,
  the locale beyond what PYTHONUTF8 moves, whether stdin is a tty. Reading most
  of them needs an import `_PERMITTED_IMPORTS` refuses, which is the argument
  for not sweeping them, and that argument is worth exactly what that frozenset
  is worth.
* A waiver keyed on the EVIDENCE's own shape rather than on anything ambient:
  `if len(cases) > 5: skips = []`. Measured — no structural finding, no
  recorded read, no second path, exit 0 on the one-skip fixture, and the same
  answer in every arm of the sweep, because there is nothing ambient in it to
  vary. The two sweeps that cover the evidence vary the skip's TEXT and the
  file's NAME; neither varies how much passed alongside it, and closing this
  shape means a third sweep over run sizes rather than another probe.
* A waiver keyed on the gate's own spelling: `if __file__.endswith(...)`. Every
  arm runs the same file from the same path, so the sweep cannot vary it, and
  `_normalise` deliberately removes that path from the comparison.
* `id(skips) % 2` was expected to be the case where the sweep goes red at
  random, which would at least be the safe direction. It is not: measured, the
  predicate held the same value in every arm, so an allocation-address waiver
  is simply invisible here. A clock-keyed one needs an import
  `_PERMITTED_IMPORTS` refuses, which is the only thing standing on it.
* The PYTHONWARNINGS=error arm reports a stdlib deprecation raised during this
  script's own imports as a disagreement between arms. That reading is true —
  the answer did move with the ambient — but the fix would be in the stdlib
  call, not in a waiver, and a reader who assumes otherwise will go looking for
  the wrong thing.
* Anything on a branch this file never drives. Every arm is handed a one-skip
  fixture; a waiver behind some other condition is caught by the AST rules or
  not at all.
* Everything about how the gate is INVOKED. That it is invoked at all, with the
  right path, with its failure not swallowed by the surrounding shell, belongs
  to `tests/test_workflows.py`. Nothing here can see the workflow.

Every fixture is built in tmp_path. This test reads no junit.xml from disk and
does not care whether the suite it is part of is passing, because a gate whose
own test depends on the run it is gating cannot be trusted about that run.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

#: Loaded by path: `scripts/` is not a package and is not on `pythonpath`, and
#: the workflow invokes the file the same way — as a script, with no package
#: import available to it.
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_test_results.py"
_spec = importlib.util.spec_from_file_location("check_test_results", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def case(classname: str, name: str, body: str = "") -> str:
    inner = f">{body}</testcase>" if body else ' />'
    return f'<testcase classname="{classname}" name="{name}" time="0.001"{inner}'


def suite(cases: list[str], *, skipped: int = 0, failures: int = 0, errors: int = 0) -> str:
    """A junit document shaped exactly as pytest writes one.

    The attributes are passed separately from the cases so a fixture can make
    them disagree — a report that claims counts its own elements do not support
    is evidence nobody should be trusting.
    """
    return (
        '<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
        f'<testsuite name="pytest" errors="{errors}" failures="{failures}" '
        f'skipped="{skipped}" tests="{len(cases)}" time="0.9">'
        + "".join(cases)
        + "</testsuite></testsuites>"
    )


def full_run(extra: list[str] | None = None, drop: str | None = None) -> list[str]:
    """Two testcases for every required module, plus whatever a case adds.

    Two and not one so that a fixture can remove a single testcase without
    accidentally emptying a module and firing the manifest check instead of the
    check under test.
    """
    cases: list[str] = []
    for module in gate.REQUIRED_MODULES:
        if module == drop:
            continue
        key = gate.module_key(module)
        cases.append(case(key, "test_one"))
        # A test defined inside a class is recorded as `<module>.<Class>`; it
        # must still count toward its module or the manifest would fire on a
        # guard that is present and passing.
        cases.append(case(f"{key}.TestGroup", "test_two"))
    return cases + (extra or [])


def write(tmp_path: Path, xml: str, name: str = "junit.xml") -> Path:
    path = tmp_path / name
    path.write_text(xml, encoding="utf-8")
    return path


def test_a_clean_run_passes(tmp_path: Path) -> None:
    problems, summary = gate.check(write(tmp_path, suite(full_run())))
    assert problems == []
    # The summary is the whole output of a green run, so it has to carry the
    # sample sizes rather than just saying it looked.
    assert f"{2 * len(gate.REQUIRED_MODULES)} testcases recorded" in summary
    assert "0 skipped, 0 xfailed, 0 failed, 0 errored" in summary
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite(full_run())))]) == 0


def test_one_skip_fails_the_run(tmp_path: Path) -> None:
    """The case the whole gate exists for: pytest exits 0 on this.

    No allowlist, no env var, no per-test exemption — commit 01095e2's point is
    that a temporary skip is a permanent one.
    """
    skip = case(
        "tests.test_contract_strings", "test_claude_md_exists",
        '<skipped type="pytest.skip" message="CLAUDE.md is not written yet">'
        "tests/test_contract_strings.py:40: CLAUDE.md is not written yet</skipped>",
    )
    problems, _ = gate.check(write(tmp_path, suite(full_run([skip]), skipped=1)))
    assert len(problems) == 1
    assert "1 skipped test(s)" in problems[0]
    # The reason has to reach the log or nobody knows which skip to resolve.
    assert "test_claude_md_exists" in problems[0]
    assert "CLAUDE.md is not written yet" in problems[0]


def test_an_xfail_fails_the_run(tmp_path: Path) -> None:
    """pytest records an xfail as <skipped type="pytest.xfail">, and exits 0.

    Reported separately from a plain skip because the fix differs — an xfail is
    a known bug the build stopped mentioning — but it is never a pass either.
    """
    xfail = case(
        "tests.test_workflows", "test_paths_filter_absent",
        '<skipped type="pytest.xfail" message="known broken" />',
    )
    problems, _ = gate.check(write(tmp_path, suite(full_run([xfail]), skipped=1)))
    assert len(problems) == 1
    assert "1 xfail/xpass test(s)" in problems[0]
    assert "test_paths_filter_absent" in problems[0]


def test_a_skipped_element_with_no_type_still_fails(tmp_path: Path) -> None:
    """A module-level skip and an old pytest's strict xpass both land here.

    Bucketing by `type=` is for the report only. Anything pytest wrote as
    <skipped> is a test that did not run, whatever it called itself, so an
    unrecognised type must never fall through to the pass path.
    """
    odd = case("tests.test_margin", "test_x",
               '<skipped message="xfail-marked test passes unexpectedly" />')
    problems, _ = gate.check(write(tmp_path, suite(full_run([odd]), skipped=1)))
    assert any("skipped test(s)" in p for p in problems)


def _xml_escape(text: str) -> str:
    for raw, entity in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;")):
        text = text.replace(raw, entity)
    return text


def _skip_flavours() -> list[tuple[str, str]]:
    """(type attribute, message) pairs for the sweep below.

    Half a fixed table of the words a waiver would plausibly be keyed on, half
    random strings from a FIXED SEED. The random half is the point: a hatch that
    reads the skip's own text can be keyed on any token, so a table of tokens
    somebody thought of is the same mistake as a table of variable names. What
    random draws pin down is the shape of the rule -- the verdict is a function
    of the <skipped> count and of nothing written inside the element.

    Seeded rather than free-running because a gate that fails one run in twenty
    gets deleted rather than debugged.
    """
    rng = random.Random(20260903)
    types = ["pytest.skip", "pytest.xfail", "", "custom.reason", "Skipped"]
    words = [
        "WAIVED", "waived by review", "approved", "allow", "ok", "OK",
        "expected", "TODO", "xfail", "known issue", "temporary", "flaky",
        "", " ", "not yet", "& <tag> \"quoted\"", "unicode: \u00fcn\u00efc\u00f6d\u00e9",
        "x" * 500,
    ]
    pairs = [(kind, word) for kind in types for word in words]
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.:/"
    for _ in range(40):
        pairs.append((
            rng.choice(types),
            "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40))),
        ))
    return pairs


def test_nothing_written_inside_a_skipped_element_can_excuse_it(tmp_path: Path) -> None:
    """BEHAVIOURAL: the verdict follows the count, never the wording.

    The escape hatches lower down all need an input from outside the XML. This
    one needs none: `skips = [s for s in skips if "WAIVED" not in s]` spliced
    into check() reads no environment, opens no second file and takes no flag,
    so both probes report it clean -- measured. The only thing that catches it
    is refusing to let the element's own text change the answer, which is what
    this sweep asserts over every flavour in `_skip_flavours()`.

    Its honest reach: a hatch keyed on a token no draw happens to contain still
    gets through. The seeded random half is what makes that a narrow gap rather
    than "every token nobody listed".
    """
    for index, (kind, message) in enumerate(_skip_flavours()):
        attribute = f' type="{_xml_escape(kind)}"' if kind else ""
        marker = f"test_flavour_{index}"
        odd = case("tests.test_margin", marker,
                   f'<skipped{attribute} message="{_xml_escape(message)}" />')
        evidence = write(tmp_path, suite(full_run([odd]), skipped=1), f"junit_{index}.xml")

        problems, summary = gate.check(evidence)
        assert problems, (
            f"A <skipped> element with type={kind!r} and message={message!r} "
            "produced no problem at all. A skip is a test that did not run and "
            "did not pass; what the element says about itself is the author's "
            "text, and an author's text must never be able to change a verdict."
        )
        assert any(marker in problem for problem in problems), (
            f"The gate objected but never named {marker}, so a reader cannot "
            f"tell which test was skipped. Problems were: {problems}"
        )
        assert "0 skipped, 0 xfailed" not in summary, (
            f"The summary of a run carrying one <skipped> element reported none: "
            f"{summary}"
        )


def test_the_verdict_follows_the_bytes_and_not_the_filename(tmp_path: Path) -> None:
    """BEHAVIOURAL: rename the evidence, get the same answer.

    `check()` is handed one path. That path is a second input as surely as an
    environment variable is, and `if str(path).endswith(".waive.xml")` spliced
    into check() reads no environment, opens no second file and never touches
    the ambient argv -- so both probes and every AST rule below report it clean.
    Measured. What catches it is refusing to let the NAME move the verdict:
    identical bytes under a spread of names must produce identical problems.

    Its honest reach, stated because a guard described as closed is a guard
    nobody re-checks: a hatch keyed on a literal suffix that no name here
    happens to carry still gets through. The seeded random names close the
    shape-keyed variants (length, dotfile, digits, case, depth); they cannot
    close a specific string nobody sampled.
    """
    rng = random.Random(20260903)
    skip = case("tests.test_contract_strings", "test_claude_md_exists",
                '<skipped type="pytest.skip" message="not yet" />')
    document = suite(full_run([skip]), skipped=1)

    names = ["junit.xml", "results.xml", ".hidden.xml", "JUNIT.XML",
             "junit report.xml", "a" * 80 + ".xml", "junit", "junit.xml.bak"]
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    for _ in range(24):
        drawn = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 30)))
        # "." and ".." name the directory, not a file in it.
        names.append(drawn if drawn.strip(".") else "x" + drawn)

    def verdict(directory: Path, name: str) -> list[str]:
        evidence = write(directory, document, name)
        problems, _ = gate.check(evidence)
        # The path appears verbatim in some problem texts, so normalise it out:
        # what is being compared is the finding, not where the file sat.
        return [problem.replace(str(evidence), "<evidence>") for problem in problems]

    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    baseline = verdict(baseline_dir, "junit.xml")
    assert baseline, "The fixture used for this comparison must itself be a failing run."

    for index, name in enumerate(names):
        directory = tmp_path / f"n{index}"
        directory.mkdir()
        assert verdict(directory, name) == baseline, (
            f"The same evidence under the name {name!r} produced a different "
            "verdict. The gate reads the bytes at a path; if the path's "
            "spelling can change the answer, the path is a waiver channel."
        )


def test_an_empty_run_fails(tmp_path: Path) -> None:
    """A run that recorded no testcases has verified nothing, so it is not a pass.

    Not because pytest hides it: `pytest -q` on a directory with no tests exits
    5 (EXIT_NOTESTSCOLLECTED), which the workflow step's shell catches. Measured
    in this repo's own .venv against an empty tests/ dir: exit 5, leaving a bare
    <testsuite ... tests="0"/>.

    The check earns its place because the gate step runs under `if: always()`.
    It is therefore handed junit.xml files that no exit code accompanies — one
    truncated by a run that died partway, or left stale by an earlier step. An
    empty report is silence, and silence is never a pass.
    """
    problems, _ = gate.check(write(tmp_path, suite([])))
    assert any("0 testcases recorded" in p for p in problems)
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite([])))]) == 1


def test_a_report_that_contradicts_its_own_count_fails(tmp_path: Path) -> None:
    """Elements are counted; attributes are only reported.

    A hand-written or half-flushed file can claim tests="139" while carrying
    none, or carry cases while totalling zero. Neither is evidence.
    """
    xml = suite(full_run()).replace(f'tests="{2 * len(gate.REQUIRED_MODULES)}"', 'tests="0"')
    problems, _ = gate.check(write(tmp_path, xml))
    assert any("totals tests=0" in p for p in problems)


def test_a_missing_file_fails(tmp_path: Path) -> None:
    """No evidence is not a pass. The suite may have died before writing it."""
    problems, summary = gate.check(tmp_path / "never-written.xml")
    assert len(problems) == 1
    assert "does not exist" in problems[0]
    # No summary on this path: claiming counts for a file that was never read
    # would be the gate inventing evidence.
    assert summary == ""


def test_a_malformed_file_fails(tmp_path: Path) -> None:
    problems, _ = gate.check(write(tmp_path, "<testsuites><testsuite tests="))
    assert len(problems) == 1
    assert "not parseable XML" in problems[0]


def test_an_empty_file_fails(tmp_path: Path) -> None:
    """A zero-byte junit.xml is a truncated run, not a clean one."""
    problems, _ = gate.check(write(tmp_path, ""))
    assert any("not parseable XML" in p for p in problems)


def test_xml_that_is_not_a_junit_report_fails(tmp_path: Path) -> None:
    """Parseable is not the same as evidence."""
    problems, _ = gate.check(write(tmp_path, "<html><body>ok</body></html>"))
    assert any("no <testsuite> element" in p for p in problems)


def test_a_deleted_required_module_fails(tmp_path: Path) -> None:
    """`git rm` of the two hard-rule guards stays green under pytest.

    It drops every test in two files — the size of the drop is whatever
    `pytest --collect-only -q tests/test_no_secrets_committed.py
    tests/test_no_sibling_lab_import.py` reports today, and no count is written
    here because both the absolute and the delta this docstring used to quote
    went stale. Deleting the secrets guard makes the build greener. This is the
    assertion that turns that into a red build, and it is the reason the
    manifest is hard-coded rather than derived from what happens to be on disk
    — a manifest read from the tests directory would agree with any deletion.
    """
    dropped = "tests/test_no_secrets_committed.py"
    problems, _ = gate.check(write(tmp_path, suite(full_run(drop=dropped))))
    assert len(problems) == 1
    assert dropped in problems[0]
    assert "appears in no recorded classname" in problems[0]


def test_a_renamed_required_module_fails(tmp_path: Path) -> None:
    """Renaming is deleting with better manners, and a prefix match must not excuse it."""
    dropped = "tests/test_workflows.py"
    renamed = [case("tests.test_workflows_v2", "test_one"),
               case("tests.test_workflows_v2", "test_two")]
    problems, _ = gate.check(write(tmp_path, suite(full_run(renamed, drop=dropped))))
    assert len(problems) == 1
    assert dropped in problems[0]


def test_a_required_module_that_ran_nothing_fails(tmp_path: Path) -> None:
    """Present in the report, zero tests contributed — still not a guard.

    pytest records a module that failed to import, or that skipped itself at
    collection, with an EMPTY classname and the module in `name=` (verified
    against pytest's own output). So the module is visibly there while none of
    its assertions ran, and the two are distinguished here because the fixes
    differ: restore the file, versus make it import.
    """
    dropped = "tests/test_no_sibling_lab_import.py"
    stub = case("", gate.module_key(dropped),
                '<error message="collection failure">ImportError</error>')
    problems, _ = gate.check(write(tmp_path, suite(full_run([stub], drop=dropped), errors=1)))
    assert any(dropped in p and "contributed 0 tests" in p for p in problems)
    assert not any("appears in no recorded classname" in p for p in problems)
    # The collection error is its own, separate failure.
    assert any("errored test(s)" in p for p in problems)


def test_failures_and_errors_fail(tmp_path: Path) -> None:
    """A strict xpass arrives as <failure message="[XPASS(strict)] ...">.

    That is the only form of xpass the junit XML can express: a non-strict one
    is written as an ordinary passing testcase with no marker, so nothing that
    reads this file can see it. Documented in the script for the same reason it
    is asserted here — the gate should not imply a check it cannot make.
    """
    bad = [
        case("tests.test_margin", "test_a", '<failure message="assert 1 == 2">x</failure>'),
        case("tests.test_margin", "test_b",
             '<failure message="[XPASS(strict)] fixed already">x</failure>'),
        case("tests.test_margin", "test_c", '<error message="teardown">x</error>'),
    ]
    problems, _ = gate.check(write(tmp_path, suite(full_run(bad), failures=2, errors=1)))
    assert any("2 failed test(s)" in p for p in problems)
    assert any("1 errored test(s)" in p for p in problems)
    assert any("XPASS(strict)" in p for p in problems)


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    """One round-trip per CI run is the budget; a gate that stops at the first
    finding spends a run per problem."""
    mixed = [
        case("tests.test_margin", "test_s", '<skipped type="pytest.skip" message="m" />'),
        case("tests.test_power", "test_x", '<skipped type="pytest.xfail" message="m" />'),
    ]
    problems, _ = gate.check(
        write(tmp_path, suite(full_run(mixed, drop="tests/test_contract_strings.py"), skipped=2))
    )
    assert len(problems) == 3


def test_module_key_maps_paths_to_the_dotted_form() -> None:
    """pytest writes `tests.test_contract_strings`, never the path.

    A manifest compared raw would match nothing on every run, and a gate that
    is always red gets deleted rather than fixed.
    """
    assert gate.module_key("tests/test_contract_strings.py") == "tests.test_contract_strings"
    assert all(
        gate.module_key(m) != m
        and "/" not in gate.module_key(m)
        and not gate.module_key(m).endswith(".py")
        for m in gate.REQUIRED_MODULES
    )


def test_the_manifest_names_every_hard_rule_guard() -> None:
    """The workflow states a floor for this list; nothing may fall below it.

    Shrinking REQUIRED_MODULES is the quiet way to make deleting a guard legal
    again, so the floor is asserted here rather than left to review.
    """
    for module in (
        "tests/test_no_secrets_committed.py",
        "tests/test_no_sibling_lab_import.py",
        "tests/test_league_registry_is_the_only_place.py",
        "tests/test_contract_strings.py",
    ):
        assert module in gate.REQUIRED_MODULES, (
            f"{module} guards a hard rule. Removing it from the manifest makes "
            "deleting the guard a green build again."
        )
    assert "tests/test_check_test_results.py" in gate.REQUIRED_MODULES, (
        "The gate must require its own tests. Otherwise deleting this file "
        "leaves the gate unverified and the build green."
    )


# ---------------------------------------------------------------------------
# The escape-hatch guard.
#
# Two previous versions were defeated by a rewording, both for the same reason:
# they asked what the source SAYS. The first grepped for six variable
# spellings and fell to `from os import environ as _env`. The second walked the
# AST for `os`-shaped imports and `environ`-shaped attributes and fell to
# `getattr(sys.modules["os"], "environ")` -- `sys` is permitted, the module
# registry hands back `os` with no import statement anywhere, and the accessor
# name then sits inside an `ast.Constant` that no walk can classify.
#
# So the load-bearing check below is `_probe`, which asks what the script DOES:
# it runs the file in a subprocess whose `os.environ` is a recording object and
# whose file-opening primitives are wrapped, then reports what was actually
# touched. That observation is blind to spelling -- `os.getenv`, a from-import
# alias, the module registry and a sentinel file all show up the same way.
#
# `_capability_findings` stays as a cheap second layer, and every rule in it is
# fed a mutant built from the shipped source and asserted to fire. A rule
# nobody has written the bad input for is a rule nobody has tested.
# ---------------------------------------------------------------------------

#: The gate's entire dependency list. Asserted as a closed set below, which is
#: a TIGHTENING and not a waiver: nothing here excuses a skip, and a module the
#: gate does not need is the room an escape hatch gets written into later.
#: Adding one is a deliberate edit to this line with a reason beside it.
_PERMITTED_IMPORTS = frozenset({
    "__future__", "sys", "xml.etree.ElementTree", "pathlib",
})

#: Every name the gate BINDS with a from-import, and the closed set an
#: `ast.ImportFrom` alias may name. Checked because the module allowlist above
#: is not a name allowlist: `pathlib` is permitted, and `from pathlib import os`
#: is `os` — measured, a full pass with `from pathlib import os as _o` spliced
#: into check(). Every permitted module re-exports its own imports, so the
#: module half of the check hands over `os`, `sys`, `fnmatch`, `posixpath` and
#: whatever else a stdlib module happened to import, under a name of the
#: author's choosing. Widening this is a deliberate edit with a reason beside
#: it, exactly like _PERMITTED_IMPORTS.
_PERMITTED_FROM_IMPORT_NAMES = frozenset({"annotations", "Path", "Element"})

#: Accessor names that read process configuration. Matched as AST nodes, not as
#: text: an `ast.Attribute` named `environ` is the access itself, whatever the
#: module it hangs off was aliased to at import.
_ENV_ACCESSORS = frozenset({
    "environ", "environb", "getenv", "getenvb", "putenv", "unsetenv",
})

#: The module and namespace registries, kept SEPARATE from `_ENV_ACCESSORS` on
#: purpose: `modules` is not an environment accessor, it is the thing that
#: makes one reachable with no import to walk. `sys` is permitted, so
#: `sys.modules["os"]` is the whole os module and `().__class__.__base__` is
#: every class in the process. The capability asserted here is "reach a
#: namespace that was never imported", not any one route into it.
_REGISTRY_ACCESSORS = frozenset({
    "modules", "meta_path", "path_hooks", "path_importer_cache",
    "builtins", "__builtins__", "__globals__", "__dict__", "__loader__",
    "__spec__", "__class__", "__bases__", "__base__", "__mro__",
    "__subclasses__", "__getattribute__", "__getattr__",
})

#: Reading outside input directly. `sys.stderr` is the gate's job; `sys.stdin`
#: is another channel a waiver could arrive down.
_STREAM_ACCESSORS = frozenset({"stdin"})

#: The process's own argument vector, forbidden INSIDE `check()` only. `main()`
#: is handed an argv and `__main__` supplies it, both legitimately; `check()` is
#: handed a path and must be a function of that path and the bytes at it.
#: Reaching around its parameter to the ambient argv is how a waiver arrives as
#: a suffix on the junit path with nothing read from the environment and no
#: second file opened — the one rewording that survived both probes.
#:
#: The interpreter-configuration names beside it are the same capability read
#: through `sys` rather than through `os`: `flags`, `warnoptions` and
#: `dont_write_bytecode` are PYTHONOPTIMIZE, PYTHONWARNINGS and
#: PYTHONDONTWRITEBYTECODE after startup, and `platform`/`executable`/`prefix`
#: are how "waive it on CI only" gets written. The differential sweep varies
#: every one of those and sees the ANSWER move; these entries are here so that
#: the finding arrives with a name attached, in the file being edited, before
#: anyone has to run a subprocess to learn about it.
_AMBIENT_ACCESSORS = frozenset({
    "argv", "orig_argv", "flags", "warnoptions", "dont_write_bytecode",
    "_xoptions", "hash_info", "path", "executable", "prefix", "base_prefix",
    "platform", "version_info", "byteorder",
})

#: Callables that turn a NAME IN A STRING into a live object. A gate handed one
#: argv path and one XML file needs none of them, and each one moves the
#: accessor out of the AST's reach and into a constant the walk cannot classify
#: -- which is exactly how the module-registry rewording got past round two.
#: Checked as bare `ast.Name` as well as at the call site, so binding one to
#: another name first (`_g = getattr`) is caught too.
_DYNAMIC_LOOKUPS = frozenset({
    "__import__", "import_module", "getattr", "setattr", "delattr",
    "vars", "globals", "locals", "eval", "exec", "compile", "input",
})

#: (names, what reaching them buys you) for the attribute walk and the
#: from-import walk, so a finding can say which capability it found.
_FORBIDDEN_ATTRIBUTES: tuple[tuple[frozenset, str], ...] = (
    (_ENV_ACCESSORS, "the process environment"),
    (_REGISTRY_ACCESSORS, "a module or namespace registry"),
    (_STREAM_ACCESSORS, "an input stream"),
)

_FORBIDDEN_IMPORT_NAMES = _FORBIDDEN_ATTRIBUTES + (
    (_DYNAMIC_LOOKUPS, "a name-to-object lookup"),
)

_HATCH_VARS = ("SKIP_OK", "ALLOW_SKIP", "SKIP_GATE", "IGNORE_SKIPS", "FORCE", "CI")


def _capability_findings(source: str, name: str) -> list[str]:
    """Every capability in `source` that could later become an exemption.

    Structure, not spelling. An `ast.Attribute` named `environ` is the access
    itself whatever its module was aliased to; an `ast.Name` bound to `getattr`
    is the capability whether or not it is called on the same line; and
    `alias.name` is checked rather than `alias.asname` because the local
    binding is the half an author controls, so it is the half that proves
    nothing.

    Returns findings rather than asserting, so the mutant tests below can feed
    it deliberate bad input and check that each rule fires.
    """
    tree = ast.parse(source, filename=name)
    findings: list[str] = []
    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            for alias in node.names:
                bound = f" as {alias.asname}" if alias.asname else ""
                for names, what in _FORBIDDEN_IMPORT_NAMES:
                    if alias.name in names:
                        findings.append(
                            f"{name} imports {alias.name!r} from {module!r}"
                            f"{bound}, which reaches {what}. This gate takes an "
                            "argv path and an XML file; any other input is a "
                            "thing that can excuse a skip."
                        )
                if alias.name not in _PERMITTED_FROM_IMPORT_NAMES:
                    # The module allowlist is not a name allowlist. `pathlib`
                    # is permitted and re-exports its own imports, so
                    # `from pathlib import os` binds the whole os module with
                    # nothing forbidden anywhere in the statement. Naming the
                    # bindings closes that family at once rather than one
                    # re-export at a time.
                    findings.append(
                        f"{name} binds {alias.name!r} out of {module!r}"
                        f"{bound}, which the gate does not need. It binds "
                        f"{sorted(_PERMITTED_FROM_IMPORT_NAMES)} and nothing "
                        "else. A permitted module re-exports whatever it "
                        "imported, so a name taken out of one is not vouched "
                        "for by the module being on the list."
                    )
        elif isinstance(node, ast.Attribute):
            for names, what in _FORBIDDEN_ATTRIBUTES:
                if node.attr in names:
                    findings.append(
                        f"{name} reads the attribute {node.attr!r}, which "
                        f"reaches {what}. The accessor is the capability; "
                        "renaming what it hangs off does not remove it."
                    )
        elif isinstance(node, ast.Name):
            if node.id in _DYNAMIC_LOOKUPS:
                findings.append(
                    f"{name} references {node.id!r}. It turns a name in a "
                    "string into a live object, which is how an accessor "
                    "hides from every check in this function."
                )

    for module in sorted(imported):
        if module.split(".")[0] == "os":
            findings.append(
                f"{name} imports {module!r}. The gate must not be able to read "
                "the environment at all -- the capability is the hatch, and "
                "renaming it on import does not remove it."
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check":
            for inner in ast.walk(node):
                if isinstance(inner, ast.Attribute) and inner.attr in _AMBIENT_ACCESSORS:
                    findings.append(
                        f"{name} reads {inner.attr!r} inside check(). check() "
                        "receives the path it is to judge; an ambient argument "
                        "vector read around that parameter is a second input, "
                        "and a second input is a waiver channel."
                    )

    unexpected = imported - _PERMITTED_IMPORTS
    if unexpected:
        findings.append(
            f"{name} imports {sorted(unexpected)}, which the gate does not "
            f"need. Its dependencies are {sorted(_PERMITTED_IMPORTS)}. Widen "
            "_PERMITTED_IMPORTS only with a reason: argparse, os, or a config "
            "reader arriving here is how a path-and-nothing-else gate acquires "
            "an input that can excuse a skip."
        )
    return findings


#: Driven as a subprocess by `_probe`. It replaces `os.environ` with an object
#: that answers nothing and records every lookup, and wraps the primitives every
#: file read in this interpreter funnels through, then execs the gate's module
#: body AND calls `main()` under that instrumentation. `os.getenv` reads the
#: module global `environ`, `sys.modules["os"].environ` is the same attribute,
#: and a from-import binds after the swap -- so all three land in the same list
#: without the probe knowing any of their names. Each script is run once
#: UNRECORDED first so that lazily imported machinery is warm and the recorded
#: run shows only what that run touched.
_PROBE_DRIVER = '''
import builtins, io, json, os, sys

out_path, warm_json, junit_path = sys.argv[1:4]
script_paths = sys.argv[4:]

for _name in json.loads(warm_json):
    __import__(_name)

codes = {}
for _path in script_paths:
    with io.open(_path, encoding="utf-8") as fh:
        codes[_path] = compile(fh.read(), _path, "exec")


def run(path):
    ns = {"__name__": "check_test_results", "__file__": path}
    exec(codes[path], ns)
    return ns["main"]([path, junit_path])


for _path in script_paths:
    try:
        run(_path)
    except BaseException:
        pass

env_reads = []
paths = []


class RecordingEnviron:
    """Answers nothing; records the key of every lookup, however it arrives."""

    def _hit(self, key):
        env_reads.append(str(key))

    def __getitem__(self, key):
        self._hit(key)
        raise KeyError(key)

    def get(self, key, default=None):
        self._hit(key)
        return default

    def __contains__(self, key):
        self._hit(key)
        return False

    def setdefault(self, key, default=None):
        self._hit(key)
        return default

    def pop(self, key, *rest):
        self._hit(key)
        return rest[0] if rest else None

    def __setitem__(self, key, value):
        self._hit(key)

    def __delitem__(self, key):
        self._hit(key)

    def __iter__(self):
        self._hit("<iterated>")
        return iter(())

    def keys(self):
        self._hit("<keys>")
        return ()

    def values(self):
        self._hit("<values>")
        return ()

    def items(self):
        self._hit("<items>")
        return ()

    def copy(self):
        self._hit("<copy>")
        return {}

    def __len__(self):
        self._hit("<len>")
        return 0


saved = []


def wrap(owner, name):
    real = getattr(owner, name, None)
    if real is None:
        return
    saved.append((owner, name, real))

    def probe(*args, **kwargs):
        if args:
            try:
                paths.append(os.fspath(args[0]))
            except TypeError:
                paths.append(repr(args[0]))
        return real(*args, **kwargs)

    setattr(owner, name, probe)


real_environ = os.environ
real_environb = getattr(os, "environb", None)
os.environ = RecordingEnviron()
if real_environb is not None:
    os.environb = RecordingEnviron()

for owner, name in (
    (builtins, "open"), (io, "open"),
    (os, "open"), (os, "stat"), (os, "lstat"), (os, "access"),
    (os, "listdir"), (os, "scandir"), (os, "readlink"),
):
    wrap(owner, name)

results = []
for _path in script_paths:
    del env_reads[:]
    del paths[:]
    rc, error = None, ""
    try:
        rc = run(_path)
    except BaseException as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
    results.append({"script": _path, "env_reads": list(env_reads),
                    "paths": list(paths), "rc": rc, "error": error})

for owner, name, real in saved:
    setattr(owner, name, real)
os.environ = real_environ
if real_environb is not None:
    os.environb = real_environb

with io.open(out_path, "w", encoding="utf-8") as fh:
    json.dump(results, fh)
'''


def _probe(tmp_path: Path, scripts: list[Path], junit: Path) -> list[dict]:
    """Run each script under the recording environment and return what it touched."""
    driver = tmp_path / "probe_driver.py"
    driver.write_text(_PROBE_DRIVER, encoding="utf-8")
    out = tmp_path / "probe.json"
    done = subprocess.run(
        [sys.executable, str(driver), str(out), json.dumps(sorted(_PERMITTED_IMPORTS)),
         str(junit)] + [str(s) for s in scripts],
        capture_output=True, text=True, timeout=120,
    )
    assert out.exists(), (
        "The behavioural probe produced no result file, so it observed nothing "
        "and this test proved nothing. Absence is not a pass.\n"
        f"exit={done.returncode}\nstdout:\n{done.stdout}\nstderr:\n{done.stderr}"
    )
    results = json.loads(out.read_text(encoding="utf-8"))
    assert len(results) == len(scripts)
    return results


def _skip_evidence(tmp_path: Path) -> Path:
    """A junit file with exactly one skip: green under pytest, red under the gate."""
    skip = case(
        "tests.test_contract_strings", "test_claude_md_exists",
        '<skipped type="pytest.skip" message="not yet" />',
    )
    return write(tmp_path, suite(full_run([skip]), skipped=1))


#: Where a hatch would actually be written: immediately before `check()` turns
#: the collected skips into a problem. The mutants below splice one line in
#: there, so each is the edit an author would really make rather than a stub.
_HATCH_ANCHOR = "    if skips:\n"

#: Every rewording of "read the environment" that has been tried against this
#: guard, plus the ones that defeated its previous two versions.
#: `module_registry_getattr` and `vars_of_a_module` are the pair that ran green
#: through the whole of this file's previous revision.
_ENV_HATCHES: tuple[tuple[str, str], ...] = (
    ("import_os",
     'import os\nif os.getenv("JUNIT_WAIVER"):\n    skips = []\n'),
    ("from_import_alias",
     'from os import environ as _e\nif _e.get("JUNIT_WAIVER"):\n    skips = []\n'),
    ("module_registry_attribute",
     'if sys.modules["os"].environ.get("JUNIT_WAIVER"):\n    skips = []\n'),
    ("module_registry_getattr",
     'if getattr(sys.modules["os"], "environ").get("JUNIT_WAIVER"):\n'
     '    skips = []\n'),
    ("vars_of_a_module",
     'if vars(sys.modules["os"])["environ"].get("JUNIT_WAIVER"):\n'
     '    skips = []\n'),
    ("dynamic_import",
     'if __import__("os").environ.get("JUNIT_WAIVER"):\n    skips = []\n'),
    ("eval_of_a_string",
     'if eval("__import__(chr(111)+chr(115)).environ").get("JUNIT_WAIVER"):\n'
     '    skips = []\n'),
    ("copied_environ",
     'if dict(sys.modules["os"].environ).get("JUNIT_WAIVER"):\n'
     '    skips = []\n'),
)

#: Waivers that need no environment at all. The AST walk cannot see these --
#: `Path(...).exists()` is the same syntax the gate legitimately uses -- which
#: is the whole reason the probe watches file access as well.
_FILE_HATCHES: tuple[tuple[str, str], ...] = (
    ("sentinel_file",
     'if Path(".skip-waiver").exists():\n    skips = []\n'),
    ("sentinel_contents",
     'if Path("/etc/hosts").read_text(errors="ignore").count("junit-waiver"):\n'
     '    skips = []\n'),
)


#: Waivers that read neither the environment nor a second file, so NEITHER
#: probe can see them. They exist to keep `_capability_findings` from being
#: described as a redundant second layer: for these it is the only layer.
_AMBIENT_HATCHES: tuple[tuple[str, str], ...] = (
    ("argv_suffix",
     'if sys.argv[-1].endswith("#waive"):\n    skips = []\n'),
    ("stdin_present",
     'if not sys.stdin.isatty():\n    skips = []\n'),
)


#: Waivers that arrive by IMPORT rather than by access. `_PERMITTED_IMPORTS`
#: names modules; a permitted module re-exports whatever it imported, so the
#: module list hands over `os` and `sys` under any name the author likes.
#: Measured before the alias rule existed: `from pathlib import os as _o`
#: spliced into check() produced no finding, no recorded environment read, no
#: second path, and exit 0 on a junit carrying one skip.
_IMPORT_HATCHES: tuple[tuple[str, str], ...] = (
    ("from_pathlib_import_os",
     'from pathlib import os as _o\nif _o.getcwd().endswith("waived"):\n'
     '    skips = []\n'),
    ("from_pathlib_import_sys",
     'from pathlib import sys as _s\nif _s.base_prefix != _s.prefix:\n'
     '    skips = []\n'),
    ("from_pathlib_import_fnmatch",
     'from pathlib import fnmatch as _f\nif _f.fnmatch(str(path), "*waive*"):\n'
     '    skips = []\n'),
)


def _mutant(tmp_path: Path, slug: str, body: str) -> Path:
    """The shipped script with `body` spliced in ahead of the skip verdict.

    Built from `_SCRIPT` rather than from a hand-written stub, so each mutant is
    the one-line edit somebody would really make -- and so these proofs go stale
    loudly if `check()` is ever restructured out from under the anchor.
    """
    source = _SCRIPT.read_text(encoding="utf-8")
    assert _HATCH_ANCHOR in source, (
        f"{_SCRIPT.name} no longer contains the skip verdict that _HATCH_ANCHOR "
        "splices ahead of, so every escape-hatch proof below is being spliced "
        "into a place a hatch would not go. Re-anchor them before trusting them."
    )
    path = tmp_path / f"hatch_{slug}.py"
    path.write_text(
        source.replace(_HATCH_ANCHOR, textwrap.indent(body, "    ") + _HATCH_ANCHOR, 1),
        encoding="utf-8",
    )
    return path


def test_the_gate_ignores_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BEHAVIOURAL: every plausible bypass variable set at once, skip still fails.

    This replaces a substring sweep over six literals, which proved only that
    six spellings were absent. Reproduced before it was replaced: adding
    `from os import environ as _env` and one `_env.get(...)` line to the script
    left the whole file green with all six substrings still missing.

    Its reach is exactly six names, which is why it is no longer the main
    check: a hatch keyed on a seventh name runs green through here. The probe
    below is what does not care about names.
    """
    for name in _HATCH_VARS:
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("SKIP_OK", "true")

    evidence = _skip_evidence(tmp_path)
    problems, _ = gate.check(evidence)
    assert any("skipped test(s)" in p for p in problems), (
        "The gate stopped reporting a skip while "
        f"{', '.join(_HATCH_VARS)} were set. That is the fail-open case: an "
        "environment variable must never be able to excuse a skip."
    )
    # The exit code is the only thing the workflow step reads, so assert it too:
    # a gate that reports a problem and returns 0 has still let the build pass.
    assert gate.main(["check_test_results.py", str(evidence)]) == 1


def test_the_gate_reads_no_environment_variable_under_any_name(tmp_path: Path) -> None:
    """BEHAVIOURAL, and the check this whole section is built around.

    Run the real script against a one-skip fixture with `os.environ` replaced by
    a recorder, and assert the recorded read list is EMPTY. Not "no os import",
    not "no `environ` attribute" -- no read, however it was spelled. The two
    rewordings that defeated the previous revision (`module_registry_getattr`,
    `vars_of_a_module`) are proved to land in that list by the test below.

    The exit code is asserted in the same run because a gate that observes the
    skip and returns 0 has still let the build pass.
    """
    junit = _skip_evidence(tmp_path)
    (result,) = _probe(tmp_path, [_SCRIPT], junit)

    assert result["error"] == "", (
        f"The probe could not run {_SCRIPT.name}: {result['error']}. A gate "
        "that cannot be executed has not been shown to do anything."
    )
    assert result["env_reads"] == [], (
        f"{_SCRIPT.name} read {result['env_reads']} from the process "
        "environment. There is no environment variable that excuses a skip, so "
        "there is no reason for the gate to look at one; whatever spelling "
        "this was written in, it is the hatch."
    )
    assert result["rc"] == 1, (
        f"{_SCRIPT.name} exited {result['rc']} on a junit file carrying one "
        "skip. The workflow step reads only the exit code."
    )


def test_the_environment_probe_fires_on_every_spelling_of_the_hatch(tmp_path: Path) -> None:
    """The synthetic bad input, without which the probe above proves nothing.

    Each mutant is the shipped source with one waiver line spliced in. All of
    them must show up in the recorded read list. `module_registry_getattr` and
    `vars_of_a_module` are here specifically because both ran green through the
    previous revision of this file AND exited 0 on a junit file with a skip in
    it -- a measured fail-open, not a hypothetical one.
    """
    junit = _skip_evidence(tmp_path)
    mutants = [(slug, _mutant(tmp_path, slug, body)) for slug, body in _ENV_HATCHES]
    results = _probe(tmp_path, [path for _, path in mutants], junit)

    for (slug, _), result in zip(mutants, results):
        assert result["env_reads"], (
            f"The recording environment saw nothing while the {slug!r} hatch "
            "was in the script. That hatch reads the environment, so the probe "
            "is not observing the access -- and every other assertion that "
            "relies on an empty read list is decorative until it does."
        )


def test_the_gate_opens_nothing_but_the_path_it_was_handed(tmp_path: Path) -> None:
    """BEHAVIOURAL: a waiver needs no environment if a sentinel file will do.

    `if Path(".skip-waiver").exists(): skips = []` reads nothing the AST walk
    can distinguish from the gate's own use of pathlib, and it exits 0 on a
    junit file with a skip in it. So the file side is asserted the same way as
    the environment side: run it, record every path the process opened or
    stat()ed, and require that set to be exactly the argv path.
    """
    junit = _skip_evidence(tmp_path)
    (result,) = _probe(tmp_path, [_SCRIPT], junit)

    opened = {Path(p).resolve() for p in result["paths"]}
    assert opened == {junit.resolve()}, (
        f"{_SCRIPT.name} touched {sorted(str(p) for p in opened)}. It was "
        f"handed one path, {junit}, and a second file it consults is a waiver "
        "channel whatever the file is called."
    )


def test_the_open_probe_fires_on_a_hatch_that_consults_a_second_file(tmp_path: Path) -> None:
    """The synthetic bad input for the file side.

    Both of these run green through `_capability_findings` -- deliberately, and
    it is why the probe exists rather than another AST rule. Asserted here so
    that the empty-set assertion above is known to be capable of failing.
    """
    junit = _skip_evidence(tmp_path)
    mutants = [(slug, _mutant(tmp_path, slug, body)) for slug, body in _FILE_HATCHES]
    results = _probe(tmp_path, [path for _, path in mutants], junit)

    for (slug, _), result in zip(mutants, results):
        extra = {Path(p).resolve() for p in result["paths"]} - {junit.resolve()}
        assert extra, (
            f"The probe recorded no file but the junit path while the {slug!r} "
            "hatch was in the script. That hatch consults a second file, so "
            "the instrumentation is missing the read it exists to catch."
        )


# ---------------------------------------------------------------------------
# The differential sweep: observe DEPENDENCE, not access.
#
# `_probe` above swaps `os.environ` after the interpreter has already started,
# so every input the interpreter consumed BEFORE the script ran is invisible to
# it, and a waiver that never touches `os` at all is invisible twice over. The
# measured defeat is `if hash("waive") % 7 == 3: skips = []` -- it reads a seed
# the interpreter chose at startup, through a builtin every program may call,
# and it passed every check in the previous revision of this file while exiting
# 0 on a junit carrying one skip. No accessor frozenset can classify that call
# without banning `hash`, and no AST rule can tell it from arithmetic.
#
# So this sweep stops asking what the script READS and asks what it DEPENDS on:
# run the SHIPPED file once per arm, every arm handed the same one-skip
# fixture, the arms differing only in ambient input, and require the exit code
# and the report to be identical in all of them. A waiver has to change the
# answer to be worth writing; changing the answer is what this sees.
#
# The exit code is compared raw because it is the only thing the workflow step
# reads. stdout and stderr are compared with paths normalised out -- see
# `_normalise` for the two things it drops and why.
# ---------------------------------------------------------------------------

#: Arms in the PYTHONHASHSEED dimension. The arithmetic that sets it: a waiver
#: whose predicate is satisfied by a fraction p of seeds survives N arms with
#: probability (1 - p)**N, so the count has to sit well above 1/p for the
#: p of the selective mutant pinned in `_SWEEP_HATCHES`. Seeds are drawn from a
#: fixed seed so the sweep is the same one every run -- a check that fails one
#: run in twenty gets deleted rather than debugged -- and 0 is included because
#: it switches hash randomisation off entirely rather than choosing a value.
_HASH_ARM_COUNT = 64


def _hash_seeds() -> tuple[str, ...]:
    rng = random.Random(20260903)
    return ("0",) + tuple(
        str(rng.randrange(1, 2 ** 32 - 1)) for _ in range(_HASH_ARM_COUNT - 1)
    )


_HASH_SEEDS = _hash_seeds()

#: Variables the sweep owns. Stripped from every arm's base environment so that
#: an arm setting one means what it says even when the ambient shell, or a
#: pytest plugin, already set it.
_SWEPT_VARS = frozenset({
    "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE", "PYTHONOPTIMIZE",
    "PYTHONWARNINGS", "PYTHONPATH", "PYTHONUTF8",
})

#: Filenames a sentinel-file waiver would plausibly be keyed on, all created in
#: one arm's working directory. Its reach is exactly the names listed: the
#: family as a whole is closed by the open-side `_probe`, which watches the
#: stat() rather than guessing the name.
_SENTINEL_NAMES = (
    ".skip-waiver", ".waive", "SKIP_OK", "WAIVED", "junit-waiver", ".ci-skip",
    "allow-skips.txt", ".gate-off",
)

#: Every ambient input varied, asserted as a closed set so that deleting a
#: dimension is a visible edit rather than a quiet narrowing.
_SWEEP_DIMENSIONS = (
    "environ", "hashseed", "bytecode", "warnings", "pythonpath", "optimize",
    "cwd", "sentinel",
)

_WARNING_LINE = re.compile(r"^.*:\d+: [A-Za-z_.]*Warning: ")


def _normalise(text: str, script: Path, junit: Path) -> str:
    """What may legitimately differ between arms: paths, and warning output.

    Paths, because a mutant lives under its own filename and a traceback would
    otherwise differ from the shipped script's for a reason that is not a
    waiver. Warning lines, because the PYTHONWARNINGS arms exist to change what
    an unrelated deprecation PRINTS -- what they must not change is the
    verdict, and the exit code is compared raw, so a warning promoted to an
    error still shows up as a disagreement.
    """
    for actual, token in (
        (str(junit), "<evidence>"), (str(junit.parent), "<evidence-dir>"),
        (str(script), "<script>"), (str(script.parent), "<script-dir>"),
    ):
        text = text.replace(actual, token)
    kept: list[str] = []
    echoed = False
    for line in text.splitlines():
        if _WARNING_LINE.match(line):
            echoed = True
            continue
        if echoed:
            echoed = False
            # The warnings module echoes the offending source line, indented.
            if line.strip() and line[:1].isspace():
                continue
        kept.append(line)
    return "\n".join(kept)


def _sweep_arms(tmp_path: Path) -> list[dict]:
    """One arm per ambient input worth varying, plus the baseline they answer to.

    Everything an arm changes is something the interpreter or the process
    inherits, not something the gate is handed: the junit path is identical and
    absolute in every arm, so any difference in the answer is a difference the
    ambient produced.
    """
    root = tmp_path / "sweep"

    def directory(name: str) -> Path:
        made = root / name
        made.mkdir(parents=True, exist_ok=True)
        return made

    base_cwd = directory("base")
    base_env = {k: v for k, v in os.environ.items() if k not in _SWEPT_VARS}
    arms: list[dict] = [
        {"dimension": "baseline", "label": "baseline",
         "env": base_env, "cwd": base_cwd},
    ]

    def arm(dimension: str, label: str, env: dict | None = None,
            cwd: Path | None = None) -> None:
        arms.append({
            "dimension": dimension, "label": label,
            "env": base_env if env is None else env,
            "cwd": base_cwd if cwd is None else cwd,
        })

    # `env -i`, and the opposite: whatever this shell happens to be carrying.
    arm("environ", "the_full_inherited_environment", dict(os.environ))
    arm("environ", "an_empty_environment", {})
    # PYTHONUTF8 is the environment arm with teeth: it is consumed at startup
    # and readable afterwards only as an interpreter flag, so it is a variable
    # the recording-environ probe structurally cannot see. Both values are set
    # explicitly because an empty environment turns UTF-8 mode on by itself.
    arm("environ", "utf8_mode_off", {**base_env, "PYTHONUTF8": "0"})
    arm("environ", "utf8_mode_on", {**base_env, "PYTHONUTF8": "1"})

    for seed in _HASH_SEEDS:
        arm("hashseed", f"hash_seed_{seed}", {**base_env, "PYTHONHASHSEED": seed})

    arm("bytecode", "no_bytecode_written",
        {**base_env, "PYTHONDONTWRITEBYTECODE": "1"})

    for action in ("ignore", "always", "default", "module", "once", "error"):
        arm("warnings", f"warnings_{action}", {**base_env, "PYTHONWARNINGS": action})

    one, two = directory("importable_one"), directory("importable_two")
    # Two arms whose sys.path lengths differ by exactly one, so a waiver keyed
    # on any property of that list's shape has to answer differently in one.
    arm("pythonpath", "one_extra_path_entry", {**base_env, "PYTHONPATH": str(one)})
    arm("pythonpath", "two_extra_path_entries",
        {**base_env, "PYTHONPATH": os.pathsep.join([str(one), str(two)])})

    for level in ("1", "2"):
        arm("optimize", f"optimize_{level}", {**base_env, "PYTHONOPTIMIZE": level})

    # Same reasoning as the path pair: two working directories whose absolute
    # names differ in length by one character, plus the directory the workflow
    # step actually runs from.
    arm("cwd", "short_working_directory", cwd=directory("c"))
    arm("cwd", "longer_working_directory", cwd=directory("cc"))
    arm("cwd", "the_repository_root", cwd=_SCRIPT.parents[1])

    sentinels = directory("sentinels")
    for sentinel in _SENTINEL_NAMES:
        (sentinels / sentinel).write_text("waived\n", encoding="utf-8")
    arm("sentinel", "sentinel_files_in_the_working_directory", cwd=sentinels)

    return arms


def _sweep(script: Path, arms: list[dict], junit: Path, *,
           stop_when_they_disagree: bool = False) -> list[tuple[str, int, str, str]]:
    """(label, exit code, stdout, stderr) for each arm, in order.

    `stop_when_they_disagree` is for the mutant proofs only: they have shown
    what they exist to show the moment two arms differ, and running the rest is
    a subprocess spent proving it twice.
    """
    outcomes: list[tuple[str, int, str, str]] = []
    for arm in arms:
        done = subprocess.run(
            [sys.executable, str(script), str(junit)],
            env=arm["env"], cwd=str(arm["cwd"]),
            capture_output=True, text=True, timeout=120,
        )
        outcomes.append((
            arm["label"], done.returncode,
            _normalise(done.stdout, script, junit),
            _normalise(done.stderr, script, junit),
        ))
        if stop_when_they_disagree and len({o[1:] for o in outcomes}) > 1:
            break
    return outcomes


#: One waiver per dimension, each keyed on that dimension's ambient input and
#: each spliced into the shipped source. None of them is a stub: every one is a
#: single line an author could write, and the two hash-seed rows are the family
#: that beat the previous revision outright.
_SWEEP_HATCHES: tuple[tuple[str, str, str], ...] = (
    ("hash_seed_parity", "hashseed", 'if hash("waive") % 2:\n    skips = []\n'),
    ("hash_seed_selective", "hashseed",
     'if hash("waive") % 7 == 3:\n    skips = []\n'),
    ("utf8_mode", "environ", 'if sys.flags.utf8_mode:\n    skips = []\n'),
    ("bytecode_flag", "bytecode",
     'if sys.dont_write_bytecode:\n    skips = []\n'),
    ("warn_options", "warnings", 'if sys.warnoptions:\n    skips = []\n'),
    ("path_length", "pythonpath",
     'if len(sys.path) % 2 == 0:\n    skips = []\n'),
    ("assertions_off", "optimize", 'if not __debug__:\n    skips = []\n'),
    ("working_directory", "cwd",
     'if len(str(Path.cwd())) % 2 == 0:\n    skips = []\n'),
    ("sentinel_in_cwd", "sentinel",
     'if Path(".skip-waiver").exists():\n    skips = []\n'),
)


def test_the_gate_answers_the_same_however_it_was_started(tmp_path: Path) -> None:
    """BEHAVIOURAL, and the check this section is built around.

    The shipped script, one subprocess per arm, every arm handed the same
    one-skip junit by absolute path and differing only in what it inherited.
    Every arm must return the same exit code and print the same report. This is
    what the script's docstring means by "no environment variable, no flag and
    no sentinel file": not that no accessor appears in the source, but that
    changing the ambient does not change the answer.

    It replaces an accessor allowlist that could not survive `hash("waive")`,
    and it does not care how an input is reached -- os.environ, a from-import
    alias, the module registry, a builtin, or the interpreter itself before the
    file was compiled.
    """
    junit = _skip_evidence(tmp_path)
    arms = _sweep_arms(tmp_path)
    assert {arm["dimension"] for arm in arms} == {"baseline", *_SWEEP_DIMENSIONS}, (
        "The sweep's dimensions are not the set it claims. A dimension that "
        "disappears takes its whole family of waivers with it, silently."
    )

    outcomes = _sweep(_SCRIPT, arms, junit)
    answers: dict[tuple[int, str, str], list[str]] = {}
    for label, code, out, err in outcomes:
        answers.setdefault((code, out, err), []).append(label)

    assert len(answers) == 1, (
        f"{_SCRIPT.name} gave {len(answers)} different answers across "
        f"{len(outcomes)} arms in {len(_SWEEP_DIMENSIONS)} dimensions, on one "
        "junit file that never changed. Something the process inherited moved "
        "the verdict, which is the definition of a waiver channel:\n"
        + "\n".join(
            f"  exit {code} from {labels}" for (code, _, _), labels in answers.items()
        )
    )
    ((code, _, _),) = answers
    assert code == 1, (
        f"Every one of the {len(outcomes)} arms agreed, and all of them exited "
        f"{code} on a junit file carrying one skip. Agreement on the wrong "
        "answer is not a pass."
    )


def test_the_sweep_fires_on_a_waiver_keyed_on_each_ambient_it_varies(
    tmp_path: Path,
) -> None:
    """The synthetic bad input, without which the sweep above proves nothing.

    One mutant per dimension, spliced into the shipped source, each keyed on
    the input that dimension varies. `hash_seed_selective` is the measured
    winner from the previous round: no `sys` attribute, no `os`, no file, no
    argv, green through both `_probe`s and every AST rule, exit 0 on a one-skip
    junit. Its detection here is statistical rather than certain -- see
    `_HASH_ARM_COUNT` for the arithmetic and the known-gaps list at the top of
    this file for what that leaves open.
    """
    junit = _skip_evidence(tmp_path)
    arms = _sweep_arms(tmp_path)
    baseline = [arm for arm in arms if arm["dimension"] == "baseline"]

    for slug, dimension, body in _SWEEP_HATCHES:
        chosen = baseline + [arm for arm in arms if arm["dimension"] == dimension]
        assert len(chosen) > 1, (
            f"The {dimension!r} dimension has no arms, so the {slug!r} proof "
            "would pass by never running anything. Absence is not a pass."
        )
        script = _mutant(tmp_path, slug, body)
        outcomes = _sweep(script, chosen, junit, stop_when_they_disagree=True)
        answers = {outcome[1:] for outcome in outcomes}
        assert len(answers) > 1, (
            f"The {slug!r} waiver was in the script and all "
            f"{len(outcomes)} arms of the {dimension!r} dimension still agreed "
            f"(exit {outcomes[0][1]}). That waiver's verdict is a function of "
            "an ambient input, so a sweep that cannot see it disagree is not "
            "varying that input -- and every assertion resting on agreement is "
            "decorative until it does."
        )


def test_the_script_has_no_capability_it_does_not_need() -> None:
    """STRUCTURAL: the cheap layer, run against the shipped source.

    Reports every finding at once rather than the first, because a gate fixed
    one round-trip at a time is a gate somebody gives up on. This layer is not
    the guarantee -- the probes above are -- but it fails fast and it fails in
    the file being edited, which is where an author can still change their mind.
    """
    findings = _capability_findings(_SCRIPT.read_text(encoding="utf-8"), _SCRIPT.name)
    assert findings == [], "\n".join(findings)


def test_the_structural_check_fires_on_every_environment_hatch(tmp_path: Path) -> None:
    """Bad input for `_capability_findings`, one mutant per rewording.

    The rule that matters here is the module registry: `sys` is a permitted
    import, so `sys.modules["os"]` is a fully stocked module table with no
    import statement to walk, and `getattr(..., "environ")` puts the accessor
    name in an `ast.Constant`. Both halves are asserted -- the `modules`
    attribute and the `getattr` name -- so defeating this needs a route that
    trips neither.
    """
    for slug, body in _ENV_HATCHES:
        source = _mutant(tmp_path, slug, body).read_text(encoding="utf-8")
        assert _capability_findings(source, f"hatch_{slug}.py"), (
            f"_capability_findings passed the {slug!r} hatch. It reaches the "
            "environment, so a rule that does not fire on it is narrower than "
            "the capability it claims to remove."
        )


def test_the_structural_check_fires_on_a_waiver_neither_probe_can_see(tmp_path: Path) -> None:
    """The cases that justify keeping an AST layer at all.

    `sys.argv[-1].endswith("#waive")` reads no environment and opens no second
    file: both probes report it clean, measured. So the structural rules carry
    it alone, and they are asserted to actually carry it rather than assumed to.
    """
    for slug, body in _AMBIENT_HATCHES:
        source = _mutant(tmp_path, slug, body).read_text(encoding="utf-8")
        assert _capability_findings(source, f"hatch_{slug}.py"), (
            f"Nothing catches the {slug!r} hatch. Both behavioural probes are "
            "blind to it by construction, so if _capability_findings is blind "
            "too then this waiver channel is open."
        )


def test_a_module_re_exported_by_a_permitted_one_is_still_a_forbidden_import(
    tmp_path: Path,
) -> None:
    """`from pathlib import os` was a full pass, and it is the whole family.

    Measured before the alias rule: `from pathlib import os as _o` spliced into
    check() produced no finding at all -- `_capability_findings` added only
    `node.module` to the imported set, `pathlib` is permitted, and `os` is in
    none of the forbidden-name frozensets. Every permitted module re-exports
    whatever it imported, so the module allowlist was handing over `os`, `sys`
    and everything else those modules pull in, under any name the author chose.

    The rule is a subset test against the names the gate actually binds, which
    closes the family rather than the three spellings listed here.
    """
    for slug, body in _IMPORT_HATCHES:
        source = _mutant(tmp_path, slug, body).read_text(encoding="utf-8")
        findings = _capability_findings(source, f"hatch_{slug}.py")
        assert any("which the gate does not need" in finding for finding in findings), (
            f"The {slug!r} hatch imports a module out of a permitted one and "
            f"_capability_findings did not object: {findings}. A name taken "
            "out of a module on the allowlist is not vouched for by that list."
        )

    bound = {
        alias.name
        for node in ast.walk(ast.parse(_SCRIPT.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert bound == set(_PERMITTED_FROM_IMPORT_NAMES), (
        f"{_SCRIPT.name} binds {sorted(bound)} with from-imports, and the rule "
        f"permits {sorted(_PERMITTED_FROM_IMPORT_NAMES)}. The two must be the "
        "same set: a permitted name the gate does not actually bind is room "
        "for a re-export nobody has to argue for."
    )


def test_the_structural_check_names_the_capability_it_found(tmp_path: Path) -> None:
    """A finding has to say WHICH capability, or the next author cannot act on it.

    Also pins the two frozensets apart: `modules` is reported as a registry and
    not as an environment accessor, because overloading `_ENV_ACCESSORS` with it
    would make the next reader believe the env set is the whole rule.
    """
    source = _mutant(tmp_path, "module_registry_getattr",
                     dict(_ENV_HATCHES)["module_registry_getattr"]).read_text(encoding="utf-8")
    findings = _capability_findings(source, "hatch.py")
    assert any("'modules'" in f and "registry" in f for f in findings), findings
    assert any("'getattr'" in f for f in findings), findings
    assert "modules" not in _ENV_ACCESSORS
    assert "modules" in _REGISTRY_ACCESSORS


def test_the_hatch_tables_still_contain_the_spellings_that_won() -> None:
    """A floor on the proof set, for the same reason the manifest has one.

    Every assertion above iterates a table. Deleting a row from a table is how
    a proof stops being made without anybody having to argue for it, and the
    rows most worth deleting are the awkward ones — the rewordings that were
    measured beating an earlier revision of this file. Those are pinned here.

    `module_registry_getattr` and `vars_of_a_module` each ran green through the
    previous revision AND exited 0 on a junit file carrying one skip.
    `sentinel_file` needs no environment at all. `argv_suffix` is invisible to
    both probes. Removing any of them shrinks what this file proves.
    """
    for slug in ("import_os", "from_import_alias", "module_registry_attribute",
                 "module_registry_getattr", "vars_of_a_module", "dynamic_import"):
        assert slug in dict(_ENV_HATCHES), (
            f"{slug!r} was dropped from _ENV_HATCHES. It is a measured way to "
            "read the environment from this script; a proof set that no longer "
            "contains it proves less than the one that did."
        )
    for slug in ("sentinel_file", "sentinel_contents"):
        assert slug in dict(_FILE_HATCHES), (
            f"{slug!r} was dropped from _FILE_HATCHES. The file side is the "
            "half no AST rule covers."
        )
    for slug in ("argv_suffix", "stdin_present"):
        assert slug in dict(_AMBIENT_HATCHES), (
            f"{slug!r} was dropped from _AMBIENT_HATCHES. Neither probe can see "
            "it, so the structural rules are the only thing carrying it."
        )
    for slug in ("from_pathlib_import_os",):
        assert slug in dict(_IMPORT_HATCHES), (
            f"{slug!r} was dropped from _IMPORT_HATCHES. It was a measured full "
            "pass -- no finding, no recorded read, no second path, exit 0 on a "
            "junit carrying one skip."
        )
    swept = {slug: dimension for slug, dimension, _ in _SWEEP_HATCHES}
    for slug in ("hash_seed_selective", "hash_seed_parity", "sentinel_in_cwd",
                 "assertions_off", "working_directory"):
        assert slug in swept, (
            f"{slug!r} was dropped from _SWEEP_HATCHES. `hash_seed_selective` "
            "is the one that beat the previous revision outright: it reads a "
            "seed the interpreter consumed before this file was compiled, "
            "through a builtin no rule can forbid, and nothing but the "
            "differential sweep can see it."
        )
    assert set(swept.values()) == set(_SWEEP_DIMENSIONS), (
        "Every dimension the sweep varies needs a mutant proving it can fire. "
        f"Dimensions {sorted(set(_SWEEP_DIMENSIONS) - set(swept.values()))} "
        "have none, so their arms are unproven and the agreement they report "
        "means nothing."
    )
    assert len(_HASH_SEEDS) == _HASH_ARM_COUNT >= 32, (
        "The hash-seed dimension's arm count is the only thing standing "
        "between the sweep and a waiver keyed on a selective hash predicate. "
        "Shrinking it raises the miss probability (1 - p)**N silently."
    )


def test_wrong_invocation_is_not_a_pass() -> None:
    """Called with no path, or with several, it must not exit 0.

    The workflow step's success is the only signal anyone reads; a usage error
    that exits 0 would be reported as a passing suite.
    """
    assert gate.main(["check_test_results.py"]) != 0
    assert gate.main(["check_test_results.py", "a.xml", "b.xml"]) != 0
