"""The guards that are not workflows and not the gate script: that they run.

Every other guard file in this repository asks whether a rule holds. This one
asks whether the machinery that enforces the rules is still there and still
does what its prose says, and it does that by RUNNING it — a synthetic tree
under a real pytest, a real git repository under the real resolve step — rather
than by reading it.

Four things live here, and each closes a hole that was measured open at 4454b20
rather than imagined:

* A TRACKED FILE CAN SHADOW THE SUITE. `python -m pytest` puts the working
  directory ahead of site-packages, so a tracked `pytest.py` at the repository
  root is the module `-m` finds. Measured on this repository: `pytest.py`
  holding `raise SystemExit(0)` made `python -m pytest -q` exit 0 having
  collected nothing; the identical tree with `PYTHONSAFEPATH=1` ran 529 tests.
  A `sitecustomize.py` on a declared PYTHONPATH is worse, because it runs
  BEFORE pytest and can set `PYTEST_ADDOPTS`: measured, `src/sitecustomize.py`
  plus the `PYTHONPATH=src` the ledger-guard workflow declares deselected a
  hard-rule credential guard, and the junit gate exited 0 over the result.
* A COLLECTION-PHASE SKIP IS INVISIBLE TO A RUNTEST-PHASE HOOK. It is NOT
  invisible to the junit gate — measured, and asserted below rather than
  assumed — but `python -m pytest -q` on its own exits 0 over it, and that is
  how most runs of this suite happen.
* A RUN CAN BE NARROWED BEFORE IT STARTS. `--deselect` in `addopts` removes one
  guard test and leaves the junit self-consistent; the gate's manifest floors a
  module at one recorded testcase, and the module still had hundreds.
* THE LEDGER GUARD WAS RED ON EVERY BRANCH'S FIRST PUSH. Fail-closed on an
  all-zeros base, which is honest and teaches people to ignore the check.

The last three are driven, not read: the conftest is copied into a synthetic
tree and a real pytest is run against it, and the resolve step is lifted out of
the workflow with `yaml.safe_load` and run against a real temporary git
repository. A guard that greps for a spelling proves only that the spelling is
absent.

This module is in `scripts/check_test_results.py`'s REQUIRED_MODULES, which is
what makes deleting it a red build rather than a smaller green one — and it is
what makes deleting the root `conftest.py` red too, because the tests below
read that file and drive it.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFTEST = PROJECT_ROOT / "conftest.py"
WORKFLOWS = PROJECT_ROOT / ".github" / "workflows"

#: Basenames the interpreter will import INSTEAD of the real thing when the
#: directory holding them is on `sys.path`. `pytest` and `coverage` because
#: `python -m X` resolves X against `sys.path` and the checkout is first;
#: `sitecustomize` and `usercustomize` because `site` imports them by name at
#: interpreter startup, before any argument is looked at.
SHADOWING_BASENAMES = frozenset(
    {"pytest.py", "coverage.py", "sitecustomize.py", "usercustomize.py"}
)

#: The same family as a package rather than a module. A directory named
#: `pytest/` with an `__init__.py` shadows the installed distribution exactly as
#: `pytest.py` does.
SHADOWING_DIRECTORIES = frozenset({"pytest", "coverage"})


def _conftest():
    """The repository's root conftest, loaded by path so its helpers can be
    driven directly. Loaded rather than imported by name: pytest has already
    imported it under a name of its own choosing, and re-importing it would be
    a second module object whose state has nothing to do with the run."""
    spec = importlib.util.spec_from_file_location("_root_conftest", CONFTEST)
    assert spec is not None and spec.loader is not None, (
        f"{CONFTEST} could not be loaded. The in-process half of the skip gate "
        "is not there, and its absence must be a red build rather than a "
        "quieter one."
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tracked_paths() -> list[str]:
    """Every tracked path, from git. `check=True` so "I could not ask" is a
    failure rather than an empty answer that reads like a clean one."""
    done = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [entry for entry in done.stdout.split("\0") if entry]


def declared_pythonpath_entries() -> set[str]:
    """Every directory this repository puts on `sys.path`, from the parse.

    Three sources, because the entry that matters is the one that is really
    set, not the one that is set in the shape a rule happened to look for:
    `env:` mappings at any level of either workflow, the `PYTHONPATH=src
    python ...` prefix assignment ledger-guard.yml actually uses, and
    pyproject's `[tool.pytest.ini_options] pythonpath`, which is what puts
    `src` in front of site-packages for the suite itself.

    `""` is in the set because `python -m` puts the working directory there
    with nobody declaring anything.
    """
    entries = {""}
    for path in sorted(WORKFLOWS.glob("*.yml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for mapping in _mappings(document):
            environment = mapping.get("env")
            if isinstance(environment, dict):
                for key, value in environment.items():
                    if str(key).strip().upper() == "PYTHONPATH":
                        entries.update(str(value).split(":"))
            run = mapping.get("run")
            if isinstance(run, str):
                for line in run.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("PYTHONPATH="):
                        value = stripped[len("PYTHONPATH="):].split()[0]
                        entries.update(value.strip("\'\"").split(":"))
    configuration = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    declared = (
        configuration.get("tool", {})
        .get("pytest", {})
        .get("ini_options", {})
        .get("pythonpath", [])
    )
    entries.update(str(entry) for entry in declared)
    return {entry.strip("/") for entry in entries}


def _mappings(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _mappings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _mappings(value)


def shadowing_files(tracked: list[str], prefixes: set[str]) -> list[str]:
    """Tracked files whose basename shadows, sitting directly on a path entry."""
    return sorted(
        entry for entry in tracked
        if Path(entry).name in SHADOWING_BASENAMES
        and str(Path(entry).parent).strip("./") in prefixes
    )


def shadowing_directories(tracked: list[str], prefixes: set[str]) -> list[str]:
    """Tracked files inside a directory that shadows a package on a path entry."""
    found = []
    for entry in tracked:
        pieces = Path(entry).parts
        for prefix in prefixes:
            root = Path(prefix).parts if prefix else ()
            if pieces[: len(root)] != root or len(pieces) <= len(root):
                continue
            if pieces[len(root)] in SHADOWING_DIRECTORIES:
                found.append(entry)
    return sorted(found)


def test_no_tracked_file_can_shadow_the_suite() -> None:
    """No tracked file sits on a path entry under a name the interpreter would
    import over the real one.

    Asserted over `git ls-files` and not over the working tree: an untracked
    `pytest.py` is somebody's scratch file, and a TRACKED one is a change that
    reached main and turned every later CI run into `SystemExit(0)`.

    It is scoped to the DIRECTORIES that are actually on `sys.path` rather than
    to every directory in the repository, because
    `src/ncaaf_betting_lab/coverage.py` is a real module of this package and
    shadows nothing: `src` is the path entry, so the name that would collide is
    `src/coverage.py`. A rule that rejected the package's own module would be a
    rule somebody deletes.
    """
    tracked = tracked_paths()
    assert tracked, (
        "git reported no tracked files at all, so this test compared nothing. "
        "An absence is not a pass."
    )
    prefixes = declared_pythonpath_entries()
    assert prefixes, "no path entry was resolved, so nothing was checked"
    offenders = shadowing_files(tracked, prefixes)
    assert not offenders, (
        f"Tracked files on a path entry ({sorted(prefixes)}) that shadow the "
        f"suite's own machinery: {offenders}. `python -m pytest` searches the "
        "working directory before site-packages, so a tracked `pytest.py` IS "
        "the suite; `site` imports `sitecustomize` by name at startup, before "
        "any flag is read, and it can set PYTEST_ADDOPTS for the run that "
        "follows. Measured: `src/sitecustomize.py` plus the `PYTHONPATH=src` "
        "ledger-guard.yml declares deselected a hard-rule credential guard, "
        "and the junit gate exited 0 over the result."
    )


def test_no_tracked_directory_shadows_an_installed_package() -> None:
    """The package spelling of the same shadow: `pytest/__init__.py` on a path
    entry is the distribution `-m` finds."""
    prefixes = declared_pythonpath_entries()
    assert prefixes, "no path entry was resolved, so nothing was checked"
    offenders = shadowing_directories(tracked_paths(), prefixes)
    assert not offenders, (
        f"Tracked files under a directory that shadows an installed package on "
        f"a path entry ({sorted(prefixes)}): {offenders}."
    )


def _synthetic_tree(tmp_path: Path, modules: dict[str, str]) -> Path:
    """A miniature repository with this repo's conftest at its root.

    The conftest is COPIED rather than re-implemented, so these tests go stale
    loudly if it is edited out from under them, and the copy's manifest is
    pointed at the synthetic tree's own guard module.
    """
    root = tmp_path / "tree"
    (root / "tests").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "check_test_results.py").write_text(
        'REQUIRED_MODULES = ("tests/test_guard.py",)\n', encoding="utf-8"
    )
    (root / "conftest.py").write_text(
        CONFTEST.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )
    for name, source in modules.items():
        (root / "tests" / name).write_text(textwrap.dedent(source), encoding="utf-8")
    return root


def _run_pytest(root: Path, *arguments: str, environment: dict | None = None):
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env.update(environment or {})
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )


GUARD_MODULE = """
    def test_one():
        assert True

    def test_two():
        assert True
"""


@pytest.mark.parametrize(
    "body",
    [
        'import pytest\npytest.skip("no data", allow_module_level=True)\n\n'
        "def test_three():\n    assert True\n",
        'import pytest\npytest.importorskip("a_module_that_is_not_installed_xyz")\n\n'
        "def test_three():\n    assert True\n",
    ],
    ids=["module-level-skip", "module-level-importorskip"],
)
def test_a_collection_phase_skip_is_not_a_pass(tmp_path: Path, body: str) -> None:
    """Both module-level shapes, run, and the exit code read.

    `pytest_runtest_logreport` never sees either of these: a module skipped at
    collection produces a CollectReport, and no test report is ever made. Before
    the root conftest existed, `python -m pytest -q` exited 0 on this tree while
    printing the skip in its own summary — which is precisely "a gate that
    passes when it should fail".

    The junit half is asserted in the same run, because the claim that the gate
    catches these was worth checking rather than repeating: pytest writes a
    collection skip into junit.xml as `<testcase classname=""
    name="tests.test_skipped"><skipped message="collection skipped">`.
    """
    root = _synthetic_tree(
        tmp_path, {"test_guard.py": GUARD_MODULE, "test_skipped.py": body}
    )
    junit = tmp_path / "junit.xml"
    done = _run_pytest(root, f"--junit-xml={junit}")
    assert done.returncode == 1, (
        "A module skipped at collection left pytest reporting success.\n"
        f"exit={done.returncode}\n{done.stdout}\n{done.stderr}"
    )
    assert "skipped at collection" in done.stdout, done.stdout

    gate = PROJECT_ROOT / "scripts" / "check_test_results.py"
    graded = subprocess.run(
        [sys.executable, str(gate), str(junit)],
        capture_output=True, text=True, cwd=root, timeout=60,
    )
    assert graded.returncode == 1, (
        "The junit gate exited 0 over a collection-phase skip. The claim that "
        "the evidence file records these is what the conftest's docstring "
        f"rests on.\n{graded.stdout}\n{graded.stderr}"
    )
    assert "skipped test(s)" in graded.stderr, graded.stderr


def test_a_clean_synthetic_tree_passes(tmp_path: Path) -> None:
    """The control. Without it, "the tree exited 1" would prove nothing —
    the exit could be coming from the harness rather than from the defect."""
    root = _synthetic_tree(tmp_path, {"test_guard.py": GUARD_MODULE})
    done = _run_pytest(root)
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    assert "2 passed" in done.stdout, done.stdout


@pytest.mark.parametrize(
    "narrowing",
    [
        {"arguments": ("--deselect", "tests/test_guard.py::test_one")},
        {"arguments": ("-k", "two")},
        {"arguments": ("--ignore", "tests/test_guard.py")},
        {"environment": {"PYTEST_ADDOPTS": "--deselect tests/test_guard.py::test_one"}},
        {"addopts": "--deselect tests/test_guard.py::test_one"},
    ],
    ids=["deselect", "keyword", "ignore", "environment", "ini-addopts"],
)
def test_a_run_narrowed_before_it_started_is_not_a_pass(
    tmp_path: Path, narrowing: dict
) -> None:
    """Five routes to one hole, all observed rather than pattern-matched.

    The ini and environment routes are the ones that matter: neither appears on
    any command line, so every rule in tests/test_workflows.py that reads the
    workflow sees a clean invocation. Measured on this repository at 4454b20
    with the ini route: `527 passed, 1 deselected`, and
    `scripts/check_test_results.py` exited 0 — the junit records the tests that
    ran and never the ones the configuration removed.
    """
    root = _synthetic_tree(tmp_path, {"test_guard.py": GUARD_MODULE})
    if "addopts" in narrowing:
        (root / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\n"
            'testpaths = ["tests"]\n'
            f'addopts = "{narrowing["addopts"]}"\n',
            encoding="utf-8",
        )
    done = _run_pytest(
        root,
        *narrowing.get("arguments", ()),
        environment=narrowing.get("environment"),
    )
    assert done.returncode == 1, (
        "The run was narrowed and pytest still reported success.\n"
        f"exit={done.returncode}\n{done.stdout}\n{done.stderr}"
    )


def test_the_census_counts_the_tests_a_module_defines(tmp_path: Path) -> None:
    """The census's own arithmetic, driven directly.

    `--deselect` is refused before collection now, so the census is the belt
    for a narrowing that arrives some other way — a plugin, a second conftest,
    a future pytest option nobody has banned. Its input is a list of nodeids,
    so it can be handed a short one without inventing a plugin.
    """
    conftest = _conftest()
    module = tmp_path / "tests" / "test_guard.py"
    module.parent.mkdir(parents=True)
    module.write_text(textwrap.dedent(GUARD_MODULE), encoding="utf-8")

    assert conftest.expected_test_names(
        textwrap.dedent(GUARD_MODULE), "test_guard.py"
    ) == {"test_one", "test_two"}

    complete = [
        "tests/test_guard.py::test_one",
        "tests/test_guard.py::test_two[a]",
        "tests/test_guard.py::test_two[b]",
    ]
    assert conftest.census_findings(("tests/test_guard.py",), complete, tmp_path) == []

    short = ["tests/test_guard.py::test_two[a]"]
    findings = conftest.census_findings(("tests/test_guard.py",), short, tmp_path)
    assert findings and "test_one" in findings[0], findings
    assert conftest.census_findings(("tests/test_missing.py",), complete, tmp_path), (
        "a required module that is not on disk must be a finding: a guard that "
        "is not there has not run"
    )


def test_the_conftest_hooks_this_repository_depends_on_are_declared() -> None:
    """The three hook names, present as functions in the loaded module.

    This is a spelling check and it is labelled one. It exists so that a
    conftest edited down to nothing fails HERE, beside the tests that drive it,
    rather than silently making every driven test above pass for the wrong
    reason — those run a copy of this file, so a conftest that lost a hook
    would show up there too, one confusing failure at a time.
    """
    conftest = _conftest()
    for hook in (
        "pytest_configure",
        "pytest_collection_modifyitems",
        "pytest_collectreport",
    ):
        assert callable(getattr(conftest, hook, None)), (
            f"{CONFTEST} no longer defines {hook}()."
        )


# --------------------------------------------------------------------------
# The Ledger Guard's base resolution, run against a real repository.
# --------------------------------------------------------------------------


def _resolve_step() -> str:
    document = yaml.safe_load(
        (WORKFLOWS / "ledger-guard.yml").read_text(encoding="utf-8")
    )
    steps = document["jobs"]["append_only"]["steps"]
    for step in steps:
        if step.get("id") == "base":
            return step["run"]
    raise AssertionError(
        "ledger-guard.yml has no step with `id: base`, so the base-resolution "
        "tests below are driving nothing. An absence is not a pass."
    )


def _git(root: Path, *arguments: str) -> str:
    done = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True,
    )
    return done.stdout.strip()


def _repository_with_a_branch(tmp_path: Path) -> tuple[Path, str]:
    """An origin holding `main`, and a clone sitting on a branch off it."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "guard@example.invalid")
    _git(origin, "config", "user.name", "guard")
    (origin / "ledger.json").write_text("{}\n", encoding="utf-8")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", "base")
    base = _git(origin, "rev-parse", "HEAD")

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    _git(clone, "config", "user.email", "guard@example.invalid")
    _git(clone, "config", "user.name", "guard")
    _git(clone, "checkout", "-q", "-b", "side")
    (clone / "ledger.json").write_text('{"a": 1}\n', encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "side work")
    return clone, base


def _drive_resolve(clone: Path, tmp_path: Path, before: str) -> subprocess.CompletedProcess:
    script = tmp_path / "resolve.sh"
    script.write_text(_resolve_step(), encoding="utf-8")
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    environment = dict(os.environ)
    environment.update(
        {
            "EVENT_NAME": "push",
            "PUSH_BEFORE_SHA": before,
            "PR_BASE_SHA": "",
            "GITHUB_OUTPUT": str(output),
        }
    )
    done = subprocess.run(
        ["bash", str(script)],
        cwd=clone, capture_output=True, text=True, env=environment, timeout=120,
    )
    done.stdout += "\n" + output.read_text(encoding="utf-8")
    return done


def test_a_branchs_first_push_resolves_to_the_merge_base(tmp_path: Path) -> None:
    """The all-zeros `before`, driven rather than reasoned about.

    Measured at 4454b20 against this same repository: the step exited 1 with
    "Cannot resolve the base commit 0000…". Fail-closed was right and the
    outcome was that every new branch's first push was red, which teaches
    people to ignore the check — and an ignored check is a removed one.

    The answer is not "pass anyway": it is that a base EXISTS in that case, and
    it is the commit the branch left main at.
    """
    clone, base = _repository_with_a_branch(tmp_path)
    done = _drive_resolve(clone, tmp_path, "0" * 40)
    assert done.returncode == 0, (
        "A branch's first push is still a red Ledger Guard.\n"
        f"{done.stdout}\n{done.stderr}"
    )
    assert f"sha={base}" in done.stdout, (
        "The first push resolved to something other than the merge-base with "
        f"origin/main ({base}).\n{done.stdout}"
    )


def test_an_unresolvable_base_is_still_a_hard_stop(tmp_path: Path) -> None:
    """The half that must NOT have been widened by the fix above.

    A force-pushed-away sha and a shallow clone both arrive as a base that
    cannot be read, and "I could not read the prior ledger" must never take the
    same branch as "there was no prior ledger".
    """
    clone, _ = _repository_with_a_branch(tmp_path)
    done = _drive_resolve(clone, tmp_path, "b" * 40)
    assert done.returncode == 1, (
        f"An unresolvable base was accepted.\n{done.stdout}\n{done.stderr}"
    )
    assert "broken guard" in done.stdout + done.stderr


def test_an_ordinary_push_still_compares_against_what_it_says(tmp_path: Path) -> None:
    """The accepting direction: a real `before` is used as given, not replaced
    by the merge-base. A fix that quietly rewrote every base would be a guard
    comparing a range nobody pushed."""
    clone, base = _repository_with_a_branch(tmp_path)
    done = _drive_resolve(clone, tmp_path, base)
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    assert f"sha={base}" in done.stdout, done.stdout


# --------------------------------------------------------------------------
# What still gets through.
# --------------------------------------------------------------------------


def test_known_gaps_that_still_get_through() -> None:
    """Asserted so that closing one turns this red and the sentence gets
    rewritten, instead of a docstring outliving the fix.

    Each of these was run against the guards above and observed to pass.
    """
    conftest = _conftest()
    guard = "def test_one():\n    pass\n\ndef test_two():\n    pass\n"

    # 1. A guard test DELETED from source. The census reads the same file
    #    pytest collected, so removing the function removes it from both sides.
    #    The gate's manifest floors a module at ONE recorded testcase, so a
    #    module that loses all but one of its tests is still "present and
    #    contributing".
    shrunk = "def test_one():\n    pass\n"
    assert conftest.expected_test_names(shrunk, "m.py") == {"test_one"}
    assert conftest.census_findings.__doc__, "census_findings lost its contract"

    # 2. A PARAMETER dropped from a parametrised test. The census compares
    #    function names, and `test_x[a]` and `test_x[b]` are one name.
    assert conftest.collected_names(["tests/m.py::test_x[a]"]) == {
        "tests/m.py": {"test_x"}
    }

    # 3. A test renamed in the same commit that stops running it. Both sides
    #    move together, exactly as a deletion does.
    renamed = guard.replace("test_two", "test_deux")
    assert conftest.expected_test_names(renamed, "m.py") == {"test_one", "test_deux"}

    # 4. This module and the root conftest deleted TOGETHER. REQUIRED_MODULES
    #    turns the first half red; the manifest entry is the second edit, and
    #    two deliberate edits have always been the shape that gets past a
    #    manifest.
    gate = PROJECT_ROOT / "scripts" / "check_test_results.py"
    assert "tests/test_the_guards_exist.py" in gate.read_text(encoding="utf-8"), (
        "This module is not in the gate's manifest, so deleting it would make "
        "the build greener rather than redder."
    )

    # 5. A pytest PLUGIN that deselects in a hook registered after this
    #    repository's `trylast` one. `trylast` is a preference in pytest's
    #    ordering, not a guarantee of being last, and a plugin installed by
    #    requirements.txt runs inside the same process. Nothing here can see
    #    that; what limits it is that requirements.txt is a reviewed file and
    #    the workflow installs from it and nothing else.
    #
    # 6. An UNTRACKED shadow written by an earlier workflow step. The tracked
    #    half is refused above and `PYTHONSAFEPATH: '1'` on the suite step
    #    covers the working-directory half, but a step that wrote
    #    `sitecustomize.py` onto a directory named in PYTHONPATH would still be
    #    imported at startup. tests.yml sets no PYTHONPATH on the suite step
    #    today, which is what makes this narrow, and
    #    `check_the_gate_reads_the_evidence_this_run_wrote` would not see it
    #    because it names no junit path.
    assert "PYTHONSAFEPATH" in (WORKFLOWS / "tests.yml").read_text(
        encoding="utf-8"
    ), "the suite step no longer declares PYTHONSAFEPATH, so gap 6 is wider"

    # 7. The FIRST push of `main` itself. The all-zeros base resolves to
    #    `git merge-base HEAD origin/main`, which on that push is HEAD, so the
    #    ledger is compared against itself and passes trivially. That is the
    #    honest first-commit state — there is no earlier ledger to compare
    #    against — but it is a pass produced by an empty comparison rather than
    #    by a checked one, and it is worth knowing which.
    #
    # 8. Everything about whether the required contexts are still REQUIRED.
    #    `test_the_required_status_check_contexts_still_exist` pins the job
    #    names; branch protection lives outside the repository and no test here
    #    can read it.


def test_the_shadow_rule_flags_what_it_names() -> None:
    """The synthetic bad input, without which the two rules above prove only
    that this repository happens to be clean today.

    Every entry here was measured on this repository before being written down:
    a root `pytest.py` made `python -m pytest -q` exit 0 with nothing collected,
    and `src/sitecustomize.py` under `PYTHONPATH=src` deselected a hard-rule
    credential guard while the junit gate exited 0. The last two are the
    negative direction — the package's own module, and a name that shadows
    nothing — because a rule that flags everything is a rule that gets deleted.
    """
    prefixes = {"", "src"}
    assert shadowing_files(["pytest.py"], prefixes) == ["pytest.py"]
    assert shadowing_files(["coverage.py"], prefixes) == ["coverage.py"]
    assert shadowing_files(["src/sitecustomize.py"], prefixes) == [
        "src/sitecustomize.py"
    ]
    assert shadowing_files(["src/usercustomize.py"], prefixes) == [
        "src/usercustomize.py"
    ]
    assert shadowing_files(["src/ncaaf_betting_lab/coverage.py"], prefixes) == []
    assert shadowing_files(["scripts/build_line_table.py"], prefixes) == []
    assert shadowing_directories(["pytest/__init__.py"], prefixes) == [
        "pytest/__init__.py"
    ]
    assert shadowing_directories(["src/coverage/__init__.py"], prefixes) == [
        "src/coverage/__init__.py"
    ]
    assert shadowing_directories(["src/ncaaf_betting_lab/reports/clv.py"], prefixes) == []


def test_the_path_entries_include_the_ones_ci_really_declares() -> None:
    """`src` has to come out of the parse, or the rules above are scoped to the
    repository root and the `sitecustomize` half is not covered at all."""
    entries = declared_pythonpath_entries()
    assert "" in entries and "src" in entries, entries


#: The job names branch protection lists as required status checks. A required
#: context is matched by NAME, so renaming a job silently removes the
#: requirement: the named check never reports, and a check that never reports
#: is a check nobody is waiting for. Nothing inside a repository can read its
#: own branch protection, so the names are pinned here instead.
REQUIRED_CONTEXTS = {"tests.yml": "tests", "ledger-guard.yml": "append_only"}


def test_the_required_status_check_contexts_still_exist() -> None:
    """Each required context is still a job, and still the only job in its file.

    "Only" is load-bearing and not decoration: `check_no_job_can_be_skipped_
    into_a_pass` in tests/test_workflows.py refuses `needs:` on every job, and
    the reason that blunt rule costs nothing is that there is one job per file
    to weigh it against. A second job appearing here is the edit that makes the
    blunt rule expensive, and it should be a conversation rather than a
    surprise.
    """
    for filename, context in REQUIRED_CONTEXTS.items():
        document = yaml.safe_load(
            (WORKFLOWS / filename).read_text(encoding="utf-8")
        )
        jobs = document.get("jobs")
        assert isinstance(jobs, dict) and list(jobs) == [context], (
            f"{filename} declares jobs {list(jobs) if jobs else jobs!r}; the "
            f"required status check is named {context!r}. A renamed job is a "
            "required check that never reports."
        )
