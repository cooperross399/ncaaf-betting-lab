"""This lab may not reach into the NFL lab, and nothing else was checking.

`leagues.py` says the two labs share no code, and calls that a deliberate and
costly choice. It was a promise in a docstring.

The venv was copied from the NFL lab to save a few minutes of setup, which
installed `football_betting_lab` into it as an editable package pointing at the
sibling repository. Every college module could have imported it and it would
simply have worked — no error, no warning, the two labs quietly coupled through
a path nobody would think to look at. Cooper spotted it; no test did.

Two things are asserted here, because either alone is insufficient:

* no module in this repository imports the sibling, and
* the sibling is not importable from this environment at all.

The first catches a line someone writes. The second catches the environment
making it possible in the first place, which is what actually happened.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Packages belonging to sibling labs. Sharing machinery with them is done by
#: PORTING code into this repository, deliberately and visibly, never by an
#: import that couples two projects through an environment.
SIBLING_PACKAGES = ("football_betting_lab", "nhl_betting_lab", "epl_betting_lab",
                    "cbb_betting_lab")


def _python_files() -> list[Path]:
    keep: list[Path] = []
    for root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests"):
        if root.is_dir():
            keep.extend(
                p for p in root.rglob("*.py")
                if ".venv" not in p.parts and p.name != Path(__file__).name
            )
    return keep


def test_no_module_imports_a_sibling_lab() -> None:
    offenders: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                root = name.split(".")[0]
                if root in SIBLING_PACKAGES:
                    offenders.append(f"{path.name}:{node.lineno}: imports {name}")
    assert not offenders, (
        "This lab imports a sibling lab. Machinery is shared by PORTING it "
        "here, visibly, never by coupling two repositories:\n  "
        + "\n  ".join(offenders)
    )


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
