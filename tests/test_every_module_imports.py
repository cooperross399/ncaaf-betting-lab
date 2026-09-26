"""Every module under `src/` and `scripts/` is actually imported, and watched.

## The hole this closes, measured rather than supposed

Two modules in this repository raised `ModuleNotFoundError` on import and the
suite passed over both of them with zero skips:

* `selection.py` imported `ncaaf_betting_lab.season`, which did not exist;
* `reports/clv.py` imported `ncaaf_betting_lab.forward_evidence`, which did not
  exist — and behind it `reports.props_backtest`, which did not either, and
  which nothing would have seen until the first one was fixed.

Nothing was red because nothing imported either module, and the two things in
this repository that read every file under `src/` both stop at the parse.
`python -m compileall` in `tests.yml` byte-compiles a module **without
executing its import statements**, and
`tests/test_league_registry_is_the_only_place.py` walks the same files with
`ast.parse`. A file that parses and cannot be imported is invisible to both.

That is not a hypothetical cost. `selection.py` holds `selection_key()`, the
one join-key builder its own docstring says both sides of every join must call,
written to stop the NHL lab's join-vocabulary bug family from reaching a sixth
member — and `CLAUDE.md` listed it under "Exists" for as long as it could not
be imported.

So the floor this file sets is deliberately the lowest one there is: the module
loads. It says nothing about what the module then does, and it is a floor
rather than a substitute — most of these modules still have no test of their
behaviour, and this one passing says only that the file loads.

## Both roots, because half a hole is not closed

`scripts/` is covered as well as `src/`. Every script here guards its work
behind `if __name__ == "__main__"` — checked, and re-checked on every run by
the import below, since a script that stopped doing so would start doing its
work inside this test and be noticed immediately. They are exactly as invisible
as `selection.py` was: nothing imports `run_opener_h1_line_move`, so a broken
import in it would surface the next time somebody ran it by hand, which is the
run where the answer was wanted.

`src/` modules are named package-relative and `scripts/` modules are named as
bare top-level modules, which is what they are: `scripts/` holds no
`__init__.py` and is a directory on the path rather than a package.

## Why a child interpreter, and not an import in this process

Two reasons, and the first one is a rule.

`tests/test_no_sibling_lab_import.py` refuses any reference to
`importlib.import_module` anywhere under `src/`, `scripts/` or `tests/`,
because a dynamic import is one its sibling-lab scan cannot follow:
`import_module(name)` where `name` is computed is exactly how
`football_betting_lab` would re-enter this repository without the scan seeing
it. That rule's own prose says the day it costs this tree something, the cost
is to be taken deliberately rather than waived — and the honest reading is that
this guard does not need it. What it needs is an `import` statement, which is
what the child runs: the probe script is generated with one literal
`import <module>` line per module, each in its own `try`. Those are ordinary
static imports, the same statement the reproduction case used, and the sibling
scan keeps every bit of its reach.

Second, isolation is the better test regardless. Importing forty-odd modules
into the suite's own process would leave all of them in `sys.modules` for every
test that runs afterwards, which is a side effect a guard should not have.

## Why the modules are discovered and not listed

A hard-coded list is a list somebody forgets to extend, and the module most
likely to be missing from it is the one added last — which is the one most
likely to be broken.

**The walk is itself asserted, because a walk that finds nothing passes
silently.** This is the same failure the byte-compile step in `tests.yml` was
already hardened against: `compileall` prints "Can't list 'src'" and exits 0
when its path argument names nothing, so a rename turns the step into a green
report about no files at all. A `parametrize` over an empty list is the same
shape — pytest reports it as a skip, which the junit gate catches in CI and
which a bare `python -m pytest -q` exits 0 over. So the discovery is checked
directly: both roots have to be there, the walk has to clear a floor, and it
has to reach every level of the package and the scripts beside it.

**And the probe is asserted too**, by running it against a synthetic tree
holding a module that cannot import and requiring it to say so. A guard whose
failure has never been seen is a guard nobody has checked, and a probe that
reported success unconditionally would look exactly like this one on a clean
tree.

## Why this is not in `tests/test_the_guards_exist.py`

That file asks whether the machinery that enforces the rules — the root
conftest, the junit gate, the shadow rules, the ledger guard's base resolution
— is still there and still does what its prose says. This asks a question about
the source tree instead, and it fails per module rather than per guard. It is
in `scripts/check_test_results.py`'s `REQUIRED_MODULES` for the same reason
that file is: deleting it must be a red build rather than a smaller green one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
SCRIPTS = PROJECT_ROOT / "scripts"
PACKAGE = "ncaaf_betting_lab"

#: A floor on the walk, not a count of the tree. An absolute would decay the
#: moment a module is added or retired — the same decay `CLAUDE.md` refuses for
#: the suite total — and the job here is only to catch a walk that collapsed to
#: nothing or to a handful. Set well below the real number on purpose.
MINIMUM_MODULES = 20

#: Modules whose absence from the walk means the walk is wrong rather than the
#: tree. Each is a level the discovery has to reach: the package root, a
#: top-level module, one inside each subpackage, and one script. A walk that
#: returned only the top level would clear the floor above and miss every
#: report.
MUST_BE_FOUND = (
    PACKAGE,
    f"{PACKAGE}.selection",
    f"{PACKAGE}.season",
    f"{PACKAGE}.leagues",
    f"{PACKAGE}.data.cfbfastr",
    f"{PACKAGE}.models.margin",
    f"{PACKAGE}.providers.env_file",
    f"{PACKAGE}.reports.settlement_agreement",
    "check_test_results",
)

#: How long the probe gets. A module that hangs on import — a network call at
#: module scope, say — is a failure of exactly the kind this guard is for, and
#: a probe with no timeout would hang the whole suite instead of reporting it.
PROBE_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class Module:
    """One module the probe will import, and where it came from."""

    #: The name an `import` statement uses. Dotted under `src/`, bare under
    #: `scripts/`, because that is how each is actually reached.
    name: str
    path: Path


def discover(root: Path) -> list[Module]:
    """Every importable module under `root`, sorted by name.

    `__init__.py` becomes its package rather than a module called `__init__`,
    which is not importable under that name and would make this guard red on a
    tree that is fine.
    """
    if not root.is_dir():
        return []
    found: dict[str, Module] = {}
    for path in sorted(root.rglob("*.py")):
        parts = list(path.relative_to(root).parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].removesuffix(".py")
        if parts:
            found.setdefault(".".join(parts), Module(".".join(parts), path))
    return [found[name] for name in sorted(found)]


def discover_all() -> list[Module]:
    """Both roots, `src/` first. Names cannot collide across the two: `src/`
    holds one package and everything in it is dotted beneath that package."""
    return discover(SRC) + discover(SCRIPTS)


def probe_source(modules: list[str], roots: list[Path]) -> str:
    """A script that imports each module with a real `import` statement.

    Generated rather than written because the list is discovered, and built out
    of literal `import` lines rather than a dynamic call because
    `tests/test_no_sibling_lab_import.py` refuses the dynamic one across this
    whole tree — for a reason that applies to any resolver, this one included.

    **The roots go onto `sys.path` here rather than into `PYTHONPATH`, and the
    ordering is the point.** `scripts/` is a directory of top-level modules, so
    a file named `json.py` in it would sit ahead of the standard library on a
    `PYTHONPATH` and the probe would import that instead of the one it needs.
    That is the family `tests/test_the_guards_exist.py` refuses at the
    repository root, one directory further in. Loading what the probe needs
    BEFORE extending the path takes that question away.

    **It replaces it with a quieter one, which is why `_preloaded` exists.**
    Measured on this tree rather than reasoned about: with the ordering above
    and a `scripts/json.py` that raises on import, the probe reported it as
    importing fine — because `import json` found the standard library's copy
    already in `sys.modules` and never touched the file. A guard that vouches
    for a file it did not read is worse than one that skips it, so a discovered
    name whose top-level package was already loaded is reported as its own
    kind of failure rather than as a pass.

    `BaseException` and not `Exception`: a module calling `sys.exit()` at
    import scope raises `SystemExit`, which is not an `Exception` and would
    otherwise take the probe down and be reported as a crash rather than as the
    one broken module it is.
    """
    for name in modules:
        if not all(part.isidentifier() for part in name.split(".")):
            raise ValueError(
                f"{name!r} is not a dotted identifier, so no import statement "
                "can name it. A file in one of the scanned roots is named "
                "something Python cannot import."
            )
    lines = [
        "import json",
        "import sys",
        "",
        "# Snapshot BEFORE the roots go on the path, so it names what this",
        "# probe loaded rather than what it then imported on purpose.",
        "_preloaded = frozenset(sys.modules)",
        "",
        f"sys.path[:0] = {[str(root) for root in roots]!r}",
        "",
        "results = {}",
        "",
    ]
    for name in modules:
        top = name.split(".")[0]
        lines += [
            f"if {top!r} in _preloaded:",
            f"    results[{name!r}] = (",
            f"        'ShadowsALoadedModule: {top} was already imported before '",
            "        'the scanned roots went on the path, so importing it here "
            "returns '",
            "        'that module and says nothing about this file. The file "
            "shadows '",
            "        'the standard library for anything run with these roots "
            "on the '",
            "        'path, which is the defect, not the report.'",
            "    )",
            "else:",
            "    try:",
            f"        import {name}",
            f"        results[{name!r}] = None",
            "    except BaseException as exc:  # reporting, not handling",
            f"        results[{name!r}] = f'{{type(exc).__name__}}: {{exc}}'",
            "",
        ]
    lines += ["json.dump(results, sys.stdout)", ""]
    return "\n".join(lines)


def run_probe(modules: list[str], *, roots: list[Path], tmp_path: Path) -> dict:
    """`{module: None}` when it imported, `{module: "Error: text"}` when it did
    not.

    The child gets `PYTHONSAFEPATH` to match what `tests.yml` hands the suite,
    so a module that imports only because the checkout root happens to be on
    `sys.path` is not reported as fine. Any inherited `PYTHONPATH` is cleared
    for the same reason: the roots this probe is asked about are the only ones
    it may resolve against, and a value in the environment would silently widen
    that.
    """
    script = tmp_path / "probe_imports.py"
    script.write_text(probe_source(modules, roots), encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONSAFEPATH"] = "1"
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
        timeout=PROBE_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise AssertionError(
            "The import probe did not finish. That is not a clean tree — a "
            "module took the interpreter down at import scope, which no "
            "per-module report can describe.\n"
            f"exit {completed.returncode}\n"
            f"stdout: {completed.stdout[-2000:]}\n"
            f"stderr: {completed.stderr[-2000:]}"
        )
    return json.loads(completed.stdout)


MODULES = discover_all()
MODULE_NAMES = [module.name for module in MODULES]
MODULES_BY_NAME = {module.name: module for module in MODULES}


@pytest.fixture(scope="module")
def import_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """One child run for the whole module, so this guard costs one startup."""
    return run_probe(
        MODULE_NAMES,
        roots=[SRC, SCRIPTS],
        tmp_path=tmp_path_factory.mktemp("import-probe"),
    )


def test_the_walk_found_both_roots() -> None:
    """The gate on the gate. A walk over nothing is not a clean tree.

    Asserted rather than trusted because the failure is silent: a root renamed
    and the parametrised test below gets a shorter list — or an empty one,
    which pytest reports as a skip rather than a failure, and which
    `python -m pytest -q` exits 0 over.

    Each root is counted on its own. Two roots checked only in total would let
    one of them vanish behind the other's count, which is the shape
    `tests/test_no_sibling_lab_import.py` already learned to refuse.
    """
    for root in (SRC, SCRIPTS):
        assert root.is_dir(), (
            f"{root} is not a directory, so the import guard below is "
            "parametrised over less than it claims. Either the tree moved or "
            "the checkout is wrong; neither is a pass."
        )
        assert discover(root), f"{root} contributed no modules to the walk."
    assert len(MODULES) >= MINIMUM_MODULES, (
        f"The walk found {len(MODULES)} module(s), below the floor of "
        f"{MINIMUM_MODULES}. A walk that collapses finds nothing broken."
    )
    unimportable_names = [
        name
        for name in MODULE_NAMES
        if not all(part.isidentifier() for part in name.split("."))
    ]
    assert not unimportable_names, (
        f"{unimportable_names} cannot be named by an import statement. A file "
        "in a scanned root is named something Python cannot import, so no "
        "guard here or anywhere else is covering it."
    )


@pytest.mark.parametrize("module", MUST_BE_FOUND)
def test_the_walk_reaches_every_level(module: str) -> None:
    """A count alone would pass on a walk that never left the top level."""
    assert module in MODULES_BY_NAME, (
        f"{module} is not in the walk's output, so the discovery is not seeing "
        f"the whole tree: it found {len(MODULES)} module(s)."
    )


def test_the_probe_reports_a_module_that_cannot_import(tmp_path: Path) -> None:
    """The negative control, without which every assertion below proves only
    that this repository happens to be clean today.

    Both directions are exercised on one synthetic tree: a module importing
    something that was never written is reported with its error, and a module
    beside it that is fine is reported as fine. A probe that returned `None`
    unconditionally would look identical to this one on the real tree.
    """
    root = tmp_path / "src"
    (root / "synthetic").mkdir(parents=True)
    (root / "synthetic" / "__init__.py").write_text("", encoding="utf-8")
    (root / "synthetic" / "fine.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "synthetic" / "broken.py").write_text(
        "from synthetic.never_written import thing\n", encoding="utf-8"
    )

    report = run_probe(
        ["synthetic", "synthetic.fine", "synthetic.broken"],
        roots=[root],
        tmp_path=tmp_path,
    )

    assert report["synthetic"] is None
    assert report["synthetic.fine"] is None
    assert report["synthetic.broken"] is not None, (
        "The probe reported a module that raises ModuleNotFoundError on import "
        "as fine. Every other assertion in this file rests on it not doing "
        "that."
    )
    assert "ModuleNotFoundError" in report["synthetic.broken"]
    assert "never_written" in report["synthetic.broken"], (
        "The probe reported the failure without the name that caused it. A "
        "guard that says a module is broken and not why is one somebody "
        "deletes rather than fixes."
    )


def test_the_probe_refuses_to_vouch_for_a_file_that_shadows_the_stdlib(
    tmp_path: Path,
) -> None:
    """The case that was measured passing before `_preloaded` existed.

    A top-level `json.py` in a scanned root is never imported by the probe,
    because the probe imported the standard library's `json` first and
    `sys.modules` answers the second request. Reported as a pass, it is a guard
    vouching for a file it did not read — and the file is a real defect besides,
    since anything run with that root on its path gets it instead of the
    standard library.
    """
    root = tmp_path / "scripts"
    root.mkdir()
    (root / "json.py").write_text(
        "raise RuntimeError('this file shadows the standard library')\n",
        encoding="utf-8",
    )

    report = run_probe(["json"], roots=[root], tmp_path=tmp_path)

    assert report["json"] is not None, (
        "The probe reported a file that shadows the standard library as "
        "importing fine. It never read the file; sys.modules answered."
    )
    assert "ShadowsALoadedModule" in report["json"]


@pytest.mark.parametrize("module", MODULE_NAMES or ["<the walk found nothing>"])
def test_every_module_imports(module: str, import_report: dict) -> None:
    """The floor: the module loads.

    Says nothing about what the module then does, and is not offered as
    coverage. What it catches is the class of defect that reached `main` here
    twice — an import naming a module that was never ported — and the class the
    EPL lab carried for over a month, a module broken where no test looked.
    """
    assert MODULE_NAMES, (
        "The walk found no modules, so this test was parametrised with a "
        "placeholder to stay red. See test_the_walk_found_both_roots."
    )
    failure = import_report.get(module, "the probe returned no verdict for it")
    source = MODULES_BY_NAME[module].path.relative_to(PROJECT_ROOT)
    assert failure is None, (
        f"{source} does not import as {module}: {failure}\n"
        "It parses, so `compileall` and the ast walkers are green over it. "
        "If a dependency is missing, write it or remove the module that wants "
        "it — deleting the import line leaves that module's callers broken."
    )
