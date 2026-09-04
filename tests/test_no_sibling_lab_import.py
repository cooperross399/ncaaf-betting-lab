"""This lab may not reach into the NFL lab, and nothing else was checking.

`leagues.py` says the two labs share no code, and calls that a deliberate and
costly choice. It was a promise in a docstring.

The venv was copied from the NFL lab to save a few minutes of setup, which
installed `football_betting_lab` into it as an editable package pointing at the
sibling repository. Every college module could have imported it and it would
simply have worked — no error, no warning, the two labs quietly coupled through
a path nobody would think to look at. Cooper spotted it; no test did.

Two things are asserted here, because either alone is insufficient:

* no module in this repository writes an `import` or `from ... import` of a
  sibling package, or a dynamic `import_module` call this scan cannot read, and
* the sibling is not importable from this environment at all.

The first catches a line someone writes. The second catches the environment
making it possible in the first place, which is what actually happened.

The first claim is exactly as wide as `_scan`, and no wider. `_scan` reads
four things:

* `ast.Import` and `ast.ImportFrom` — the import statement someone writes;
* `import_module(...)` with a plain string argument, rejected when that string
  names a sibling package;
* `import_module(...)` with **any other argument**, rejected on the spot;
* the name `import_module` **referenced without being called**, or bound to
  another name by `from importlib import import_module as ...`, rejected on the
  spot as well.

The last two are capability rules rather than name rules, and they are there
because `importlib.import_module("football" + "_betting_lab")` cannot be
resolved by an AST walk and does not need to be. A repository that never has
cause to compute an import target at run time can refuse the computation
instead of trying to follow it — so the concatenation, the f-string and the
bare variable are all rejected without any of them being evaluated, and so is
`f = importlib.import_module` before the call site is even reached. That last
one is why the reference rule exists rather than a call rule alone: chasing the
function through a rebinding would mean writing a resolver, and a resolver that
handles two of the four ways to move a reference around reads as one that
handles all of them.

The cost of that strictness is stated rather than assumed. `_scan` matches the
name wherever it appears, so a method of your own called `import_module` is
refused too, and `from importlib import import_module as im` is refused even if
`im` is only ever handed literals. No reference to `import_module` of any kind
appears anywhere under `SCAN_ROOTS`, which
`test_the_dynamic_import_rule_costs_the_shipped_tree_nothing` measures on every
run — so today the rule costs this tree nothing, and the day it does, that test
fails first and says which module.

The scan reads `SCAN_ROOTS` only — `src/`, `scripts/`, `tests/`. A `.py` file
elsewhere in the repository, or under a `.venv` inside one of those trees, is
not read. Nothing else is exempt: this module is scanned by the guard it
defines.

Neither claim is worth anything unless the scan can prove it read something, so
the file scan refuses to return an empty list and refuses to step over a module
it cannot parse. Both refusals are exercised below: a guard whose failure has
never been seen is a guard nobody has checked.

What still gets through is not written here. It is asserted, spelling by
spelling, in `test_the_spellings_this_scan_still_cannot_see`, so that closing
one of those holes fails a test and forces the ledger to be rewritten rather
than letting a stale paragraph read as coverage.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: This module, by resolved path. It used to exempt itself from its own scan
#: on the grounds that it names the sibling packages — but it names them as
#: strings, and `_scan` reads import statements, so the exemption bought
#: nothing and cost the one thing an exemption always costs: it was keyed on
#: the BASENAME, so any file in `src/`, `scripts/` or `tests/` that happened
#: to be called this was handed to nobody, whatever it imported. There is now
#: no exemption at all; this module is scanned like every other, which
#: `test_the_guard_reads_itself_like_any_other_module` asserts and
#: `test_a_decoy_sharing_this_modules_filename_is_still_scanned` proves is not
#: a filename match.
THIS_MODULE = Path(__file__).resolve()

#: Packages belonging to sibling labs. Sharing machinery with them is done by
#: PORTING code into this repository, deliberately and visibly, never by an
#: import that couples two projects through an environment.
SIBLING_PACKAGES = ("football_betting_lab", "nhl_betting_lab", "epl_betting_lab",
                    "cbb_betting_lab")


#: The trees the import scan is responsible for reading.
SCAN_ROOTS = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests")


#: The dynamic-import call this repository has no use for, matched as
#: `importlib.import_module(...)` and as a bare `import_module(...)` brought in
#: by `from importlib import import_module`. Matching the attribute rather than
#: the receiver is deliberate: aliasing the module (`import importlib as il`)
#: changes the receiver and not the attribute.
DYNAMIC_IMPORT_CALL = "import_module"


def _python_files(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    """Every module the scan reads, and never an empty list.

    The old `if root.is_dir()` stepped over a missing root in silence, and
    `rglob` on one that has been renamed yields nothing just as quietly. Either
    way the scan iterated over nothing and reported no offenders, which is
    indistinguishable in a test report from a clean repository.

    Each root is counted on its own, because two live roots would otherwise
    cover for a third that had vanished.

    One thing is left out, stated so the caller does not read more coverage
    into the list than it has: any path with a `.venv` component, so a copied
    environment sitting inside a scanned tree is not mistaken for this
    repository's own code. Nothing else is excluded — not even this module,
    which is scanned like any other.
    """
    found: list[Path] = []
    for root in roots:
        here = [
            p for p in root.rglob("*.py")
            if ".venv" not in p.parts
        ]
        if not here:
            raise AssertionError(
                f"{root} contributed no Python files to the sibling-import "
                "scan. A moved or renamed tree has to be a red build; a guard "
                "that reads nothing passes everything."
            )
        found.extend(here)
    return found


def _is_dynamic_import(node: ast.AST) -> bool:
    """Whether this node names `import_module`, however it was reached.

    Matched on the attribute or the bare name, never on the receiver, because
    the receiver is the easy half to change: `import importlib as il` moves
    `importlib` and leaves `il.import_module` spelled the same.
    """
    if isinstance(node, ast.Attribute):
        return node.attr == DYNAMIC_IMPORT_CALL
    if isinstance(node, ast.Name):
        return node.id == DYNAMIC_IMPORT_CALL
    return False


def _scan(paths: list[Path]) -> tuple[list[str], list[str]]:
    """Sibling imports found, and the files this scan could not read.

    The second list is not a footnote, and the reason is this guard's own
    integrity rather than anything about what other tools do. A module
    `ast.parse` chokes on is a module this guard did not examine, and silence
    about it is indistinguishable in a test report from a file that was
    examined and found clean. Returning the unreadable files rather than
    swallowing them is what lets the caller turn a hole in the coverage into a
    failure that names the file.

    `ast.Import` and `ast.ImportFrom` are the import statement someone writes.
    `import_module(...)` is the dynamic one, and it is judged by what it is
    *given*: a plain string is read like an import statement and rejected when
    it names a sibling; anything else — a concatenation, an f-string, a
    variable, a keyword argument, no argument at all — is rejected because the
    target cannot be read, and a repository with no legitimate dynamic import
    has nothing to lose by refusing it.

    The name itself is read as well. `import_module` mentioned anywhere other
    than as the thing being called, and `import_module` renamed on the way in
    by `from importlib import import_module as ...`, are both rejected: a
    reference this scan hands off is a call it will never see, and refusing the
    reference is cheaper and more honest than following it.

    What is still invisible here is asserted in
    `test_the_spellings_this_scan_still_cannot_see`, and the reason those are
    not covered by the same trick is written there rather than implied.
    """
    offenders: list[str] = []
    unreadable: list[str] = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            unreadable.append(f"{path}: {exc}")
            continue
        called = {
            id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_dynamic_import(node.func):
                target = node.args[0] if node.args else None
                if isinstance(target, ast.Constant) and isinstance(target.value, str):
                    if target.value.split(".")[0] in SIBLING_PACKAGES:
                        offenders.append(
                            f"{path.name}:{node.lineno}: "
                            f"import_module imports {target.value}"
                        )
                else:
                    offenders.append(
                        f"{path.name}:{node.lineno}: import_module is given a "
                        "target this scan cannot read. Import the module by "
                        "name, in an import statement, where the guard can see "
                        "what it is."
                    )
                continue
            if _is_dynamic_import(node) and id(node) not in called:
                offenders.append(
                    f"{path.name}:{node.lineno}: import_module is referenced "
                    "without being called, so this scan cannot follow where it "
                    "is called from or what it is given there."
                )
                continue
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == DYNAMIC_IMPORT_CALL and alias.asname:
                        offenders.append(
                            f"{path.name}:{node.lineno}: import_module is bound "
                            f"to the name {alias.asname}. This scan follows the "
                            "name and not the binding, so a renamed one is a "
                            "dynamic import it would never see."
                        )
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                root = name.split(".")[0]
                if root in SIBLING_PACKAGES:
                    offenders.append(f"{path.name}:{node.lineno}: imports {name}")
    return offenders, unreadable


def test_no_module_imports_a_sibling_lab() -> None:
    scanned = _python_files()
    offenders, unreadable = _scan(scanned)
    assert not unreadable, (
        "The sibling-import scan could not parse these modules, so it did not "
        "check them. An unreadable module is a hole in this guard, not a file "
        f"to step over ({len(scanned)} modules read):\n  " + "\n  ".join(unreadable)
    )
    assert not offenders, (
        "This lab imports a sibling lab. Machinery is shared by PORTING it "
        f"here, visibly, never by coupling two repositories ({len(scanned)} "
        "modules read):\n  " + "\n  ".join(offenders)
    )


def test_a_module_the_scan_cannot_parse_is_a_failure_and_not_a_skip(
    tmp_path: Path,
) -> None:
    """`continue` on SyntaxError handed the file to nobody.

    The fixture below imports a sibling lab in plain text and the scan still
    cannot see it, because it never parses. That is precisely why silence was
    a lie: the one file most likely to be mid-edit was the one file exempt
    from the guard.
    """
    broken = tmp_path / "broken_module.py"
    broken.write_text("from football_betting_lab import (\n", encoding="utf-8")

    offenders, unreadable = _scan([broken])

    assert offenders == []
    assert len(unreadable) == 1
    assert "broken_module.py" in unreadable[0]


def test_a_root_that_contributes_no_files_fails_rather_than_scanning_nothing(
    tmp_path: Path,
) -> None:
    """Zero findings and zero coverage have to stop reading the same.

    All three shapes are covered: an empty root, a missing root, and a dead
    root travelling alongside a live one.
    """
    with pytest.raises(AssertionError, match="contributed no Python files"):
        _python_files(roots=(tmp_path,))

    with pytest.raises(AssertionError, match="contributed no Python files"):
        _python_files(roots=(tmp_path / "never_existed",))

    with pytest.raises(AssertionError, match="contributed no Python files"):
        _python_files(roots=(PROJECT_ROOT / "tests", tmp_path))

    assert _python_files(roots=(PROJECT_ROOT / "src",))
    assert _python_files(roots=(PROJECT_ROOT / "scripts",))
    assert _python_files(roots=(PROJECT_ROOT / "tests",))


@pytest.mark.parametrize("package", SIBLING_PACKAGES)
def test_no_sibling_lab_is_even_importable(package: str) -> None:
    """The environment half, and the one that actually bit.

    A copied venv installed the NFL lab as an editable package pointing at the
    sibling repository. No line of code had to be written for the two labs to
    be coupled — the import would simply have worked.
    """
    assert importlib.util.find_spec(package) is None, (
        f"{package} is importable from this environment. A copied venv or a "
        "stray editable install couples the two labs through a path nobody "
        "reads. Uninstall it: `.venv/bin/python -m pip uninstall "
        f"{package.replace('_', '-')}`."
    )


def test_a_decoy_sharing_this_modules_filename_is_still_scanned(
    tmp_path: Path,
) -> None:
    """The exclusion is this file, not this filename.

    `_python_files` used to drop every path whose `name` matched this
    module's, so a module anywhere in `src/`, `scripts/` or `tests/` that
    happened to be called the same thing was handed to nobody — the one
    exemption in the guard was claimable by copying a filename. The decoy
    below imports a sibling in plain, parseable text and has to be reported.
    """
    decoy = tmp_path / "nested" / THIS_MODULE.name
    decoy.parent.mkdir(parents=True)
    decoy.write_text("import football_betting_lab\n", encoding="utf-8")
    innocent = tmp_path / "innocent.py"
    innocent.write_text("x = 1\n", encoding="utf-8")

    # The other exclusion, exercised in the same breath: a copied environment
    # inside a scanned tree is skipped, which is why the module docstring says
    # so rather than leaving the reader to assume the scan reads everything.
    vendored = tmp_path / ".venv" / "lib" / "vendored.py"
    vendored.parent.mkdir(parents=True)
    vendored.write_text("import nhl_betting_lab\n", encoding="utf-8")

    scanned = _python_files(roots=(tmp_path,))
    assert decoy in scanned
    assert vendored not in scanned

    offenders, unreadable = _scan(scanned)
    assert unreadable == []
    assert len(offenders) == 1
    assert "football_betting_lab" in offenders[0]


def test_the_guard_reads_itself_like_any_other_module() -> None:
    """No exemption, so nothing can be claimed by copying a filename.

    The scan covers `tests/`, this module lives there, and it is read. The
    exemption it used to hold was justified by the sibling names it holds as
    strings — but `_scan` reads import statements and call nodes, not strings,
    so the justification was false and the exemption only ever removed
    coverage.
    """
    tests_dir = PROJECT_ROOT / "tests"
    on_disk = {
        path for path in tests_dir.rglob("*.py") if ".venv" not in path.parts
    }
    assert THIS_MODULE in on_disk, "this module should be under tests/"
    assert set(_python_files(roots=(tests_dir,))) == on_disk, (
        "the scan skipped a module under tests/. There is no exemption list "
        "here, and the moment there is one it is the hole."
    )

    offenders, unreadable = _scan([THIS_MODULE])
    assert unreadable == []
    assert offenders == [], (
        "this module imports a sibling lab, or calls import_module. Naming the "
        "packages as strings is how the guard works; importing one, or "
        "computing an import target, is the thing it forbids."
    )


def test_scan_reads_the_import_statement_and_the_dynamic_one(
    tmp_path: Path,
) -> None:
    """Every spelling `_scan` is responsible for, run as a module.

    The first group is the import statement. The second is `import_module`
    judged by its argument: a literal naming a sibling, and — the case that
    matters — a target the scan cannot resolve. A concatenation is not resolved
    here and is not meant to be; it is refused, which is a rule about a
    capability rather than about a spelling, and therefore not beatable by
    respelling the concatenation.
    """
    caught = {
        "plain": "import football_betting_lab\n",
        "from-import-as": "from nhl_betting_lab.markets import x as y\n",
        "submodule": "import football_betting_lab.markets.pricing\n",
        "inside a function": "def f():\n    import epl_betting_lab\n",
        "inside try/except": (
            "try:\n    import cbb_betting_lab\nexcept ImportError:\n    pass\n"
        ),
        "import_module, literal sibling": (
            "import importlib\n"
            "m = importlib.import_module('football_betting_lab')\n"
        ),
        "import_module, literal sibling submodule": (
            "import importlib\n"
            "m = importlib.import_module('nhl_betting_lab.markets')\n"
        ),
        "import_module, concatenated": (
            "import importlib\n"
            "m = importlib.import_module('football' + '_betting_lab')\n"
        ),
        "import_module, f-string": (
            "import importlib\n"
            "m = importlib.import_module(f'{sport}_betting_lab')\n"
        ),
        "import_module, join": (
            "import importlib\n"
            "m = importlib.import_module('_'.join(['football', 'betting', 'lab']))\n"
        ),
        "import_module, variable": (
            "import importlib\nm = importlib.import_module(name)\n"
        ),
        "import_module, keyword argument": (
            "import importlib\nm = importlib.import_module(name=pkg)\n"
        ),
        "import_module through an alias of importlib": (
            "import importlib as il\nm = il.import_module(pkg + '_lab')\n"
        ),
        "import_module imported bare": (
            "from importlib import import_module\nm = import_module(pkg)\n"
        ),
        "import_module inside a function": (
            "import importlib\n"
            "def f():\n    return importlib.import_module(build_name())\n"
        ),
        "import_module renamed on the way in": (
            "from importlib import import_module as im\n"
            "m = im('football' + '_betting_lab')\n"
        ),
        "import_module bound to a variable, then called": (
            "import importlib\nf = importlib.import_module\n"
            "m = f('football' + '_betting_lab')\n"
        ),
        "import_module stashed in a container": (
            "import importlib\nD = {'f': importlib.import_module}\n"
            "m = D['f']('football' + '_betting_lab')\n"
        ),
        "import_module passed as an argument": (
            "import importlib\nrun(importlib.import_module, pkg)\n"
        ),
        "import_module used as a decorator": (
            "import importlib\n@importlib.import_module\ndef f():\n    pass\n"
        ),
        # The cost of matching the name rather than the receiver, asserted so
        # that it is a known price rather than a surprise. A method of your own
        # called `import_module` is refused too. That is acceptable here only
        # because the price is measured:
        # `test_the_dynamic_import_rule_costs_the_shipped_tree_nothing` shows
        # the name appears nowhere under SCAN_ROOTS.
        "a method of your own called import_module (the cost of this rule)": (
            "class Loader:\n"
            "    def import_module(self, name):\n        return name\n"
            "Loader().import_module(pkg)\n"
        ),
    }
    for label, source in caught.items():
        module = tmp_path / "caught.py"
        module.write_text(source, encoding="utf-8")
        offenders, unreadable = _scan([module])
        assert unreadable == [], label
        assert offenders, f"{label} reaches a sibling package and was not reported"

    allowed = {
        "import_module, literal that is not a sibling": (
            "import importlib\nm = importlib.import_module('json')\n"
        ),
        "import_module, literal naming this package": (
            "import importlib\n"
            "m = importlib.import_module('ncaaf_betting_lab.leagues')\n"
        ),
        "a method that merely shares the name of a package": (
            "import football\nfootball.load()\n"
        ),
        "from importlib import import_module, used with a literal": (
            "from importlib import import_module\nm = import_module('json')\n"
        ),
    }
    for label, source in allowed.items():
        module = tmp_path / "allowed.py"
        module.write_text(source, encoding="utf-8")
        offenders, unreadable = _scan([module])
        assert unreadable == [], label
        assert offenders == [], (
            f"{label} is reported, which would fail correct code. The rule is "
            "about targets that cannot be read and packages that are siblings, "
            "not about the word import_module."
        )


def test_the_dynamic_import_rule_costs_the_shipped_tree_nothing() -> None:
    """The rule is only honest if the real tree pays nothing for it.

    Refusing an unresolvable `import_module` target — and refusing a reference
    to `import_module` that goes somewhere this scan cannot follow — is worth
    having because this repository has no cause to do either. That is a claim
    about the tree, so it is measured against the tree on every run rather than
    asserted once: the name does not appear as an attribute, a bare name or a
    renamed import anywhere under `SCAN_ROOTS`. It is measured at the width of
    the rule rather than at the width of the call, because the rule is what
    would fail somebody's build.

    If a legitimate use appears, this fails first and names the module, instead
    of the rule surfacing as a mystery failure somewhere unrelated. That is the
    point of measuring it here: a strict rule whose cost is unmeasured is a
    rule that gets waived the first time it bites.
    """
    scanned = _python_files()
    references: list[str] = []
    for path in scanned:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if _is_dynamic_import(node):
                references.append(f"{path.name}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                references.extend(
                    f"{path.name}:{node.lineno}"
                    for alias in node.names
                    if alias.name == DYNAMIC_IMPORT_CALL
                )
    assert scanned, "nothing was read, so this measured nothing"
    assert not references, (
        f"{len(references)} reference(s) to import_module across "
        f"{len(scanned)} modules under SCAN_ROOTS: {references}. The rule that "
        "refuses what it cannot read was adopted because this tree never "
        "needed a dynamic import. If it now does, that is a design decision to "
        "take deliberately, not a rule to quietly relax."
    )


def test_the_spellings_this_scan_still_cannot_see(tmp_path: Path) -> None:
    """The known-gaps ledger: what reaches a sibling and is not reported.

    Asserted rather than described, so that closing one of these fails this
    test and forces the ledger to be rewritten. Each entry carries the reason
    it is still open, because a gap without a reason reads as an oversight and
    an oversight gets closed badly.

    All of these are covered by the second assertion instead —
    `test_no_sibling_lab_is_even_importable`. A dynamic lookup can only resolve
    against a package the environment can find, and that test forbids it. The
    residue neither assertion sees is code that puts the sibling on `sys.path`
    itself and then looks it up dynamically.
    """
    missed = {
        # `__import__` with a computed name is the same hole as `import_module`
        # with one, and the same refusal would close it. It is NOT applied,
        # deliberately: this repository's own test machinery executes
        # `__import__(<computed name>)` inside a probe driver to warm modules
        # before a recorded run. That driver lives in a string today, so an AST
        # rule would not fire on it — but it is correct code that a future
        # round could reasonably move into a module, and a guard that would red
        # the build the moment it did is a guard that gets waived. The cost of
        # refusing `import_module` is measured and zero; the cost of refusing
        # `__import__` is not, and an unmeasured cost is not a gate to ship.
        "__import__, literal": "m = __import__('football_betting_lab')\n",
        "__import__, computed": "m = __import__('football' + '_betting_lab')\n",
        # A module already imported by something else is fetched from the
        # module table without any import node or call to `import_module` at
        # all. There is no target here to refuse; the name is a dictionary key.
        "sys.modules": "import sys\nm = sys.modules['football_betting_lab']\n",
        # Loader lookups reach the package through the import system without
        # importing it. Refusing every function that takes a module name would
        # be a spelling rule, and spelling rules are what the last three rounds
        # kept losing to.
        "pkgutil loader": "import pkgutil\nl = pkgutil.get_loader('cbb_betting_lab')\n",
        "importlib.util.find_spec": (
            "import importlib.util\n"
            "s = importlib.util.find_spec('epl_betting_lab')\n"
        ),
        # `import_module` reached through a string rather than through the
        # name. The reference rule reads identifiers; these reach the same
        # function by spelling it in a string constant, and refusing every
        # string that happens to spell a function name is exactly the kind of
        # spelling rule the last three rounds kept losing to. What would close
        # it is a resolver, and a resolver is what the reference rule exists to
        # avoid pretending to be.
        "getattr on importlib": (
            "import importlib\n"
            "m = getattr(importlib, 'import_module')('football_betting_lab')\n"
        ),
        "importlib.__dict__ lookup": (
            "import importlib\n"
            "m = importlib.__dict__['import_module']('nhl_betting_lab')\n"
        ),
        # Source assembled and handed to the interpreter. Nothing in a static
        # walk reaches inside a string that becomes code at run time.
        "exec of an import statement": (
            "exec('import football_betting_lab')\n"
        ),
    }
    for label, source in missed.items():
        module = tmp_path / "missed.py"
        module.write_text(source, encoding="utf-8")
        offenders, unreadable = _scan([module])
        assert unreadable == [], label
        assert offenders == [], (
            f"{label} is now reported by _scan, which is an improvement. Move "
            "it into the caught group in "
            "`test_scan_reads_the_import_statement_and_the_dynamic_one` and "
            "take it out of this ledger, which currently tells the reader this "
            "spelling is invisible here."
        )
        # Folded the way the interpreter would fold it, so that a spelling
        # which assembles the name still has to be pointed at a sibling to
        # earn its place in this ledger.
        assembled = source.translate(str.maketrans("", "", "'\" +"))
        assert any(package in assembled for package in SIBLING_PACKAGES), (
            f"{label} no longer reaches a sibling package, so it stopped being "
            "a gap in this guard and stopped belonging in this ledger"
        )

    for package in SIBLING_PACKAGES:
        assert importlib.util.find_spec(package) is None, (
            f"{package} is importable, and every spelling in this ledger "
            f"({len(missed)} of them) resolves the moment it is. The "
            "environment being clean is the only thing standing between them "
            "and a coupled build."
        )
