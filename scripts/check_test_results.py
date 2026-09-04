#!/usr/bin/env python3
"""Fail the build on a skip, an xfail, an empty run, or a missing guard module.

    python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"

`python -m pytest -q` exits 0 on a SKIP and on an XFAIL. Green then means "the
suite did not object" rather than "the suite passed", which is the fail-open
case .github/workflows/tests.yml exists to prevent. This script is what closes
it.

A zero-collection run is NOT that case: pytest returns 5 (EXIT_NOTESTSCOLLECTED)
and the step's shell catches it. The empty-evidence checks below earn their
place for a different reason — this gate is invoked under `if: always()`, so it
also runs when the junit.xml is absent, truncated because the run died partway,
or stale from an earlier step. In none of those does an exit code reach this
script at all, and "the file said nothing" must never read as "nothing was
wrong".

There is no allowlist, no environment variable, no flag and no sentinel file
that tolerates a skip, and there will not be one. Commit 01095e2 ("A test that
cannot run yet skips loudly rather than passing quietly") is the argument: a
temporary skip is a permanent one, and an exemption list is how the second one
gets added without anybody having to make the case for it.

That sentence is a claim about behaviour, and what checks it observes
DEPENDENCE rather than access. `tests/test_check_test_results.py` runs this
file in a DIFFERENTIAL SWEEP: one subprocess per arm, every arm handed the same
one-skip junit and differing only in ambient input — the full environment
against an empty one, PYTHONHASHSEED across many values, PYTHONDONTWRITEBYTECODE,
PYTHONWARNINGS, PYTHONPATH, PYTHONOPTIMIZE, PYTHONUTF8, the working directory,
and plausible sentinel files sitting in it — and it requires the exit code and
the report (paths normalised out) to be IDENTICAL in every arm. That sweep, and
not any frozenset of accessor names, is what enforces the paragraph above; see
`_sweep_arms` and `test_the_gate_answers_the_same_however_it_was_started`
there. It is blind to spelling by construction, and to accessors too: reading
`os.environ`, a from-import alias, the module registry, a sentinel file, or the
builtin `hash()` of a token — which consumes a seed the interpreter chose
before this file was compiled and touches no attribute any walk can classify —
all show up the same way, as an arm that disagrees.

Two narrower layers sit beside it, and they earn their place by naming what
they find rather than reporting a bare disagreement. `_probe` runs this file
with `os.environ` replaced by a recording object and the file-opening
primitives wrapped, and reports the variable read and the path opened.
`_capability_findings` reads the AST and holds this file to the imports it
actually needs — including the NAMES a from-import binds, because the module
list alone permits `from pathlib import os`: every module re-exports what it
imported, so allowing `pathlib` was allowing `os` under any name until that
rule was written.

What none of that reaches, said plainly because a gate described as closed is a
gate nobody re-checks: a waiver keyed on a literal token no arm draws — a
particular sentinel filename, a junit path suffix, a word inside the skip
message, or a `hash()` predicate selective enough that no sampled seed
satisfies it — is invisible to a sweep, because every arm takes the same
branch. Nor does any of it reach a waiver keyed on the SHAPE of the evidence
rather than on anything ambient: `if len(cases) > 5: skips = []` was measured
green through every layer. Those are written down in the known-gaps list at the
top of that test file, and they are the reason review still has to read
`check()`.

REQUIRED_MODULES is the other half, and it is aimed at a specific failure.
`git rm tests/test_no_secrets_committed.py tests/test_no_sibling_lab_import.py`
DROPS EVERY TEST IN TWO FILES AND STAYS GREEN. Deleting both hard-rule guards
makes the build GREENER, and pytest has no way to say so. Counting what ran is
the only way a deletion reads as red instead of as a smaller green.

No integer is quoted for that drop. The size of it is whatever
`pytest --collect-only -q tests/test_no_secrets_committed.py
tests/test_no_sibling_lab_import.py` reports today. An earlier revision cited an
absolute ("118 passed, 1 skipped") and it went stale inside one session; the
revision after that cited a delta instead and called the delta the durable half
of the measurement, and the delta went stale too. Neither form survives
concurrent work on the guards. Name the commit a count was taken at, or quote
no count.

Standard library only, and nothing from src/: the workflow step invokes this
with no PYTHONPATH, and the gate has to still run and still report when the
package itself is broken.

One thing this file cannot see: a NON-STRICT xpass. pytest writes it into the
XML as an ordinary passing testcase carrying no marker at all, so no reader of
the XML can tell it from a pass. A strict xpass is written as a <failure> and
caught below, and `xfail_strict = true` in pyproject.toml is the only reason
the xpass half of this gate is reachable at all. Note the width of that
dependency: the setting is the DEFAULT and only the default, so removing it
blinds this gate entirely AND a single `@pytest.mark.xfail(strict=False)`
blinds it for that test while the setting stays put. Either way this script
goes on reporting a clean run while xpasses stream past it, and nothing here
can detect that. The fix lives in pyproject.toml and in the markers; this
script cannot be it, and saying so beats implying a gate that is not there.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.etree.ElementTree import Element

#: Every module that must show up in the evidence AND must have contributed at
#: least one testcase. Checked against the classnames the XML actually records,
#: so a guard that is deleted, renamed, or edited down to zero collected tests
#: fails here instead of quietly shrinking the pass count. Adding a guard means
#: adding it here too — an unlisted test file is protected by nothing.
REQUIRED_MODULES: tuple[str, ...] = (
    "tests/test_no_secrets_committed.py",
    "tests/test_no_sibling_lab_import.py",
    "tests/test_league_registry_is_the_only_place.py",
    "tests/test_contract_strings.py",
    "tests/test_workflows.py",
    "tests/test_check_test_results.py",
    "tests/test_check_ledger_append_only.py",
)


def module_key(module: str) -> str:
    """`tests/test_contract_strings.py` -> `tests.test_contract_strings`.

    pytest records classnames dotted, relative to rootdir and without the
    suffix, and appends the class for a test defined inside one
    (`tests.test_x.TestGroup`). Comparing the manifest's paths raw would match
    nothing ever, which is a gate that fails on every run — and a gate that
    always fails is one somebody deletes to get a green build.
    """
    return module.removesuffix(".py").replace("/", ".")


def _describe(case: Element, child: Element) -> str:
    """One offending test, named well enough to act on without opening the XML."""
    ident = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
    kind = child.get("type") or child.tag
    message = (child.get("message") or "").strip() or "(no message recorded)"
    return f"{ident or '(unnamed testcase)'} [{kind}] {message}"


def check(path: Path) -> tuple[list[str], str]:
    """Return (reasons this run is not a pass, one-line summary of what ran).

    An empty reason list is the only thing that counts as a pass. Every early
    return here is a case where the evidence itself is missing or unreadable,
    and those return no summary because nothing was verified.
    """
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        return ([f"{path} does not exist. The suite recorded no evidence, so "
                 "there is nothing to check and this run is not a pass."], "")
    except OSError as exc:
        return ([f"{path} could not be read ({exc}). A gate that cannot open "
                 "its evidence has checked nothing."], "")
    except ET.ParseError as exc:
        # A zero-byte junit.xml lands here as well as a truncated one: both mean
        # the run died partway, which pytest's exit code may not have carried.
        return ([f"{path} is not parseable XML ({exc}). A truncated or empty "
                 "evidence file is a run that did not finish."], "")

    # junit_family decides whether the root is <testsuites> or a bare
    # <testsuite>; accept either rather than depending on a pytest default.
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return ([f"{path} contains no <testsuite> element. It is XML, but it "
                 "is not a junit report, so it proves nothing."], "")

    cases = [case for suite in suites for case in suite.iter("testcase")]

    problems: list[str] = []
    skips: list[str] = []
    xfails: list[str] = []
    failures: list[str] = []
    errors: list[str] = []

    for case in cases:
        for child in case:
            if child.tag == "skipped":
                # pytest.xfail, pytest.skip, "collection skipped", and older
                # pytest's strict-xpass all arrive as <skipped>. Every one of
                # them is a test that did not run and did not pass, so the
                # bucket is split for the report only — never for the verdict.
                if child.get("type") == "pytest.xfail":
                    xfails.append(_describe(case, child))
                else:
                    skips.append(_describe(case, child))
            elif child.tag == "failure":
                failures.append(_describe(case, child))
            elif child.tag == "error":
                errors.append(_describe(case, child))

    if skips:
        problems.append(
            f"{len(skips)} skipped test(s). A skip is a gate that passes when "
            "it should fail. Resolve it or delete it; there is no third option "
            "and no exemption list:\n  " + "\n  ".join(skips)
        )
    if xfails:
        problems.append(
            f"{len(xfails)} xfail/xpass test(s). An expected failure is a known "
            "bug the build stopped mentioning:\n  " + "\n  ".join(xfails)
        )
    if failures:
        problems.append(
            f"{len(failures)} failed test(s):\n  " + "\n  ".join(failures)
        )
    if errors:
        problems.append(
            f"{len(errors)} errored test(s). An error is a failure — a guard "
            "that cannot run has not passed:\n  " + "\n  ".join(errors)
        )

    # Counted from the elements, not trusted from the attributes: a hand-edited
    # or half-written file can claim tests="139" while carrying none.
    recorded = 0
    for suite in suites:
        raw = suite.get("tests")
        if raw is not None and raw.lstrip("-").isdigit():
            recorded += int(raw)
    if not cases:
        problems.append(
            f"0 testcases recorded in {path} (the report claims {recorded}). A "
            "run that collected nothing must never read as a pass — that is the "
            "fail-open case this gate exists for."
        )
    elif recorded == 0:
        problems.append(
            f"{len(cases)} testcase element(s) present but the report totals "
            "tests=0. The evidence contradicts itself and cannot be trusted."
        )

    # A skipped-at-collection or import-broken module is recorded with an empty
    # classname and the module in name= (verified against pytest's own output),
    # so it counts as present-and-contributing-nothing rather than as deleted.
    # The distinction is worth keeping: the two have different fixes.
    seen: set[str] = set()
    for case in cases:
        classname = case.get("classname") or ""
        if classname:
            seen.add(classname)
        else:
            seen.add(case.get("name") or "")

    per_module: dict[str, int] = {}
    for module in REQUIRED_MODULES:
        key = module_key(module)
        # `key + "."` and not startswith(key) alone: `tests.test_workflows_v2`
        # must not be allowed to stand in for `tests.test_workflows`.
        count = sum(
            1 for case in cases
            if (case.get("classname") or "") == key
            or (case.get("classname") or "").startswith(key + ".")
        )
        per_module[module] = count
        if count:
            continue
        if key in seen:
            problems.append(
                f"{module} is recorded but contributed 0 tests. It was skipped "
                "at collection or failed to import; either way the guard did "
                "not run."
            )
        else:
            problems.append(
                f"{module} contributed 0 tests and appears in no recorded "
                "classname. It was deleted, renamed, or collects nothing — "
                "which would otherwise make this build greener by removing a "
                "guard."
            )

    leanest = min(per_module, key=lambda m: per_module[m]) if per_module else ""
    summary = (
        f"{len(cases)} testcases recorded across {len(seen)} classnames "
        f"({recorded} reported by the run): {len(skips)} skipped, "
        f"{len(xfails)} xfailed, {len(failures)} failed, {len(errors)} errored. "
        f"{len(REQUIRED_MODULES)} required modules checked, thinnest is "
        f"{leanest} at {per_module.get(leanest, 0)} tests."
    )
    return problems, summary


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0] if argv else 'check_test_results.py'} "
              "<junit.xml>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    problems, summary = check(path)

    if problems:
        # stderr, and every reason at once: a gate that reports the first
        # problem only gets fixed one round-trip at a time.
        print(f"FAIL {path}: this run does not count as a pass.", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        if summary:
            print(summary, file=sys.stderr)
        return 1

    print(f"PASS {path}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
