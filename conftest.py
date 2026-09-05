"""The half of the skip gate that runs INSIDE pytest, where the junit cannot see.

`scripts/check_test_results.py` grades the junit file after the run. That is the
right place for most of the verdict, and it is measured to catch more than the
comments used to say: a module-level `pytest.skip(allow_module_level=True)` and
a module-level `pytest.importorskip` BOTH reach junit.xml as
`<testcase classname="" name="tests.test_x"><skipped message="collection
skipped">`, and the gate exits 1 on them (measured on a three-module synthetic
tree, pytest 9.1.1: 1 passed, 2 skipped, `python -m pytest` exit 0, gate exit 1
— reproduced by `tests/test_the_guards_exist.py::
test_a_collection_phase_skip_is_not_a_pass`).

Two things that grading leaves open, and this file is both of them.

FIRST: `python -m pytest -q` on its own still exits 0 over that same tree. The
junit half only works when something reads the junit, so anybody running the
suite by hand — which is how nearly every run of this suite actually happens —
gets a green exit code over a permanently skipped guard.
`pytest_collectreport` is where a CollectReport arrives; `pytest_runtest_logreport`
never sees one, which is why a runtest-phase hook would not have closed this.

SECOND, and it is the one the junit CANNOT close: the run can be narrowed
before it starts. `--deselect tests/test_no_secrets_committed.py::
test_no_tracked_file_assigns_a_real_credential` written into `addopts` in
pyproject.toml, or into `PYTEST_ADDOPTS`, removes one hard-rule guard and
leaves every other check green. Measured on this repository at 4454b20 under
`python -m pytest -q`: one deselected test, everything else passing, and
`scripts/check_test_results.py` exits 0, because the manifest floors a module
at ONE recorded testcase and the module still had hundreds. The evidence file
records the tests that ran and never the ones the configuration removed, so no
reader of that file can notice — the observation has to happen here, in the
process that was handed the configuration.

So this file OBSERVES rather than spells. `pytest_configure` asks the live
`config` what it actually received; the census in
`pytest_collection_modifyitems` compares the test functions each required guard
module DEFINES, read with `ast`, against the ones pytest still holds after
pytest's own deselection hooks have run. `trylast` is a preference in pytest's
hook ordering and not a guarantee of running last, which is gap 5 in
`tests/test_the_guards_exist.py::test_known_gaps_that_still_get_through`.

Neither is a text match on a command line, which is what makes them indifferent
to how the flags were spelled or assembled. Three routes that defeat a text
match were run against this file at 5072f97, each as `python -m pytest -q` in a
git-backed copy of this repository, and each exited 1 naming what pytest had
received: `-k` where `--deselect` was banned; `addopts = "--runxfail"` in
pyproject.toml; and a `sitecustomize.py` on PYTHONPATH setting `PYTEST_ADDOPTS`
before pytest starts. What is NOT claimed is a route nobody has tried: this
file observes the options in `NARROWING_OPTIONS`, any `addopts` at all and any
`PYTEST_ADDOPTS` at all, and it observes them at `pytest_configure` — a plugin
that removes tests later is the census's job, and gap 5 in
`tests/test_the_guards_exist.py` says which shape of that still gets past it.

WHAT THIS FILE DOES NOT DO, said plainly:

* It cannot see a guard test DELETED from source. The census reads the same
  file pytest collected, so removing the function removes it from both sides.
  That deletion is what `git` review and `REQUIRED_MODULES` are for, and
  `REQUIRED_MODULES` only floors a module at one testcase, so a source deletion
  of some-but-not-all of a guard's tests is caught by neither. It is written
  down in `tests/test_the_guards_exist.py`'s known-gaps test rather than
  implied shut.
* It cannot see a PARAMETER dropped from a parametrised test: the census
  compares function names, and `test_x[a]` and `test_x[b]` are one name.
* Its own deletion is a red build only because `tests/test_the_guards_exist.py`
  reads this file and drives it, and that module is in `REQUIRED_MODULES` — so
  deleting both is the two-file edit that gets past it, exactly as deleting a
  guard and its manifest entry always was.
"""

from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent

#: The name pytest reads flags out of when no command line carries them. There
#: is no synonym for it, so the name is the thing.
PYTEST_ADDOPTS = "PYTEST_ADDOPTS"

#: What is asked of the live `config`, and why each one is here. These are the
#: inputs that make the junit unable to account for the suite: every one of them
#: removes tests BEFORE anything is recorded, so the evidence file agrees with
#: itself while describing a smaller run than the one CI claims to have made.
#: `maxfail` is not here — it truncates a run that has already started failing,
#: and the failure is what turns the build red anyway.
NARROWING_OPTIONS: tuple[tuple[str, str], ...] = (
    ("deselect", "--deselect removes named tests before collection finishes"),
    ("keyword", "-k selects a subset by substring"),
    ("markexpr", "-m selects a subset by marker"),
    ("ignore", "--ignore drops a path"),
    ("ignore_glob", "--ignore-glob drops a family of paths"),
)


def _required_modules() -> tuple[str, ...]:
    """The gate's manifest, loaded from the gate rather than copied.

    Two lists that must agree is one list that will not. The gate is stdlib-only
    and defines nothing at import time but constants and functions, so importing
    it here costs nothing and runs nothing.
    """
    script = PROJECT_ROOT / "scripts" / "check_test_results.py"
    spec = importlib.util.spec_from_file_location("_gate_manifest", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"{script} could not be loaded, so the required-module census has "
            "no manifest to work from. A census with no manifest checks "
            "nothing, and nothing checked is not a pass."
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.REQUIRED_MODULES)


def expected_test_names(source: str, filename: str) -> set[str]:
    """Every test function `source` DEFINES, by the name pytest will give it.

    Module-level `def test_*` and methods of a `class Test*`, which is every
    shape this repository uses. Written as a function of the source text so
    `tests/test_the_guards_exist.py` can drive it on a synthetic module and
    watch it come back short.
    """
    tree = ast.parse(source, filename=filename)
    names: set[str] = set()

    def functions(body: list[ast.stmt]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test"):
                    names.add(node.name)

    functions(tree.body)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            functions(node.body)
    return names


def collected_names(nodeids: list[str]) -> dict[str, set[str]]:
    """`{module path: {test function name}}` out of what pytest is holding.

    The parametrisation is stripped, so `test_x[a]` and `test_x[b]` both count
    as `test_x`; the census is a floor on FUNCTIONS, and it says so rather than
    implying it covers parameters.
    """
    found: dict[str, set[str]] = {}
    for nodeid in nodeids:
        pieces = nodeid.split("::")
        if len(pieces) < 2:
            continue
        module = pieces[0]
        name = pieces[-1].split("[", 1)[0]
        found.setdefault(module, set()).add(name)
    return found


def census_findings(
    required: tuple[str, ...], nodeids: list[str], root: Path, *,
    restricted: bool = False,
) -> list[str]:
    """Which required guard modules are holding fewer tests than they define.

    `restricted` is for the run somebody types by hand:
    `pytest tests/test_margin.py` selects one module on purpose, and a census
    that failed it would be a rule enforced by deleting the rule. In that run
    the census still applies to every required module the positional DID
    select, so narrowing inside a selected module is still caught; what it
    stops doing is calling the unselected modules missing.

    The CI invocation cannot take that branch: `check_the_suite_is_never_
    narrowed` and `check_the_suite_line_carries_only_whitelisted_arguments` in
    tests/test_workflows.py both reject a positional on the pytest line, so the
    suite step always runs unrestricted, and an unrestricted run censuses
    everything.
    """
    collected = collected_names(nodeids)
    findings: list[str] = []
    for module in required:
        if restricted and module not in collected:
            continue
        path = root / module
        if not path.is_file():
            findings.append(
                f"{module} is in the gate's REQUIRED_MODULES and is not on "
                "disk. A guard that is not there has not run."
            )
            continue
        expected = expected_test_names(
            path.read_text(encoding="utf-8"), str(path)
        )
        missing = sorted(expected - collected.get(module, set()))
        if missing:
            findings.append(
                f"{module} defines {len(expected)} test function(s) and pytest "
                f"is holding {len(collected.get(module, set()))} of them. "
                f"Missing: {', '.join(missing)}. Something narrowed this run "
                "before it started, and the junit file it writes will account "
                "only for the tests that survived."
            )
    return findings


def _received_narrowing(config: pytest.Config) -> list[str]:
    """What pytest ACTUALLY received, asked of the live config object.

    Not a scan of `sys.argv` and not a scan of any file: `addopts` in
    pyproject.toml, `PYTEST_ADDOPTS` in the environment and a `-c` pointed at a
    second ini all arrive here as ordinary parsed options, however they were
    spelled or assembled.
    """
    findings: list[str] = []
    for option, why in NARROWING_OPTIONS:
        try:
            value = config.getoption(option)
        except ValueError:  # pragma: no cover - option gone from pytest
            findings.append(
                f"pytest no longer offers the {option!r} option, so this "
                "observation is not being made. An unasked question is not an "
                "answer of no."
            )
            continue
        if value:
            findings.append(f"pytest received {option}={value!r}: {why}.")

    addopts = config.inicfg.get("addopts")
    if addopts:
        findings.append(
            f"the ini file sets addopts={addopts!r}. pytest reads it as if the "
            "flags had been typed, so every rule that reads the workflow's "
            "command line sees a clean invocation over a narrowed run."
        )
    environment = os.environ.get(PYTEST_ADDOPTS)
    if environment:
        findings.append(
            f"{PYTEST_ADDOPTS}={environment!r} is set in the environment. It "
            "narrows the run with no command line and no ini entry to read."
        )
    return findings


def _fail(reason: str, findings: list[str]) -> None:
    body = "\n  ".join(findings)
    pytest.exit(f"{reason}\n  {body}", returncode=1)


def pytest_configure(config: pytest.Config) -> None:
    findings = _received_narrowing(config)
    if findings:
        _fail(
            "This run was narrowed before it started, so its result cannot "
            "stand for the suite:",
            findings,
        )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """The census, run LAST so it sees what survived every deselection hook.

    `trylast` is the whole point: `--deselect` and `-k` do their work in this
    same hook, and a census that ran first would count the tests they are about
    to remove.
    """
    findings = census_findings(
        _required_modules(),
        [item.nodeid for item in items],
        PROJECT_ROOT,
        restricted=sorted(config.args) != sorted(config.getini("testpaths")),
    )
    if findings:
        _fail("A required guard module is not running in full:", findings)


def pytest_collectreport(report: pytest.CollectReport) -> None:
    """Collection-phase skips, which `pytest_runtest_logreport` never sees.

    A module-level skip or importorskip produces a CollectReport, not a
    TestReport. pytest prints it in the summary and exits 0.
    """
    if report.skipped:
        _COLLECTION_SKIPS.append(f"{report.nodeid or '<root>'}: {report.longrepr}")


_COLLECTION_SKIPS: list[str] = []


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _COLLECTION_SKIPS:
        return
    print(
        "A module was skipped at collection. A skip is a gate that passes when "
        "it should fail, and pytest's own exit code is 0 over it:",
    )
    for entry in _COLLECTION_SKIPS:
        print(f"  {entry}")
    session.exitstatus = 1
