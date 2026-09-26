"""A path this repository names in prose or in output has to be a path it has.

## What this catches, and why it is not a spelling rule

Three files under `src/` named a path that does not exist here, each inherited
from `../football-betting-lab` when the module was ported:

* `reports/feed_freshness.py` **rendered** the instruction "Fetch with
  `scripts/fetch_football_data.py --seasons <season>`" into a report. The
  script here is `scripts/fetch_ncaaf_data.py`. The reader gets that sentence at
  07:00 on a game day with a stale feed, and the command does not exist.
* `reports/forecast_skill.py` raised `FileNotFoundError` telling the reader to
  run `scripts/run_settlement_agreement.py`, which is the NFL lab's script.
* `reports/allowlist_evidence.py` and `staging_provider_policy.py` both cited
  `docs/provider_allowlist_approval.md` — the six-step procedure the second of
  them writes into the shipped policy template, for **the one action
  `CLAUDE.md` says is never Claude's to take**. The document had not been
  ported, so the template pointed the human at nothing.

None of those is a syntax error, none is an import error, and none is a wrong
number that reading carefully would catch. They are references whose referent
is missing, which is a question a machine can answer exactly.

**This is deliberately not a rule about what the prose says.** This repository
has repeatedly recorded that a guard matching spellings gets defeated by a
rewording — `tests/test_no_sibling_lab_import.py` says so about two of its own
earlier versions. A rule about NFL-shaped *numbers* in ported prose would be
exactly that kind, and it is not attempted here: the `272 games` and `+16%`
figures fixed alongside this guard were found by reading, and the next one will
be too.

What makes this rule different is that it does not ask what a string means. It
extracts the paths a string names and asks the filesystem. Rewording the
sentence around the path changes nothing, and renaming the path is the thing it
is checking.

## Its reach, stated at the width it really has

* **String constants and docstrings only**, under `src/` and `scripts/`. A path
  assembled at runtime from an f-string or a `Path(...) / name` join is not a
  constant and is not seen.
* **`data/` is excluded on purpose.** `data/manual/staging_provider_policy.json`
  is *deliberately* absent — `CLAUDE.md` calls that its correct shipping state —
  and `data/outputs/` names files that only exist after a run. A guard that
  failed on those would be demanding the lab fabricate evidence it has not
  gathered, which is the opposite of the rule it serves.
* Only suffixes this repository actually commits are matched. A bare directory
  name is not checked, because `data/staging/` legitimately does not exist yet.
* **It will almost never see a path inside the package**, and that is another
  guard's doing rather than an oversight. `src/ncaaf_betting_lab/...` contains
  the league key, and `tests/test_league_registry_is_the_only_place.py` fails
  the build on a league literal in any string under `src/` or `scripts/` —
  measured while writing this file, by putting one in an error message and
  watching that guard reject it. So intra-package paths are already banned
  there and this rule has nothing left to check about them. Under `docs/` they
  are allowed and are checked normally.

So it is a floor. It proves that the paths named as literals resolve, and
nothing about whether the prose around them is true.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The trees whose strings are read. `tests/` is out for the reason
#: `tests/test_league_registry_is_the_only_place.py` keeps it out of its own
#: scan: a guard that scans itself trips on the examples it needs in order to
#: prove it works — the docstring above names three paths that are now correct
#: and one, `scripts/fetch_football_data.py`, that must never exist here.
SCAN_ROOTS = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts")

#: Directories a referenced path may live under. `data/` is absent on purpose;
#: see the module docstring.
REFERENCEABLE = ("src", "scripts", "docs", "tests", ".github")

#: Suffixes worth checking. A path with no suffix is usually a directory, and
#: several of this lab's directories are legitimately unbuilt.
SUFFIXES = ("py", "md", "json", "yml", "yaml", "toml", "cfg", "txt")

PATH_PATTERN = re.compile(
    r"\b((?:" + "|".join(re.escape(d) for d in REFERENCEABLE) + r")"
    r"/[\w./-]+\.(?:" + "|".join(SUFFIXES) + r"))\b"
)


def python_files() -> list[Path]:
    """Every module the scan reads, and never an empty list.

    Each root is counted on its own. A renamed root yields nothing from
    `rglob` just as quietly as a missing one, and a scan that iterated over
    nothing would report no offenders — indistinguishable in a test report
    from a clean repository.
    """
    found: list[Path] = []
    for root in SCAN_ROOTS:
        assert root.is_dir(), f"{root} is not a directory, so this scan read nothing."
        here = sorted(root.rglob("*.py"))
        assert here, f"{root} contributed no files to the scan."
        found.extend(here)
    return found


def referenced_paths(source: str) -> set[str]:
    """Every repository path named by a string constant or docstring.

    Docstrings are `ast.Constant` nodes too, so walking constants covers both;
    they are not collected separately, which would double-count them.
    """
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.update(PATH_PATTERN.findall(node.value))
    return found


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_every_path_a_module_names_exists(path: Path) -> None:
    """A file that names a path this repository does not have is wrong about
    this repository, whoever reads it next."""
    missing = sorted(
        reference
        for reference in referenced_paths(path.read_text(encoding="utf-8"))
        if not (PROJECT_ROOT / reference).exists()
    )
    assert not missing, (
        f"{path.relative_to(PROJECT_ROOT)} names {missing}, which "
        f"{'do' if len(missing) > 1 else 'does'} not exist here. Ported "
        "machinery carries the sibling lab's paths, and a rendered instruction "
        "naming a script this repository does not have is read at 07:00 on a "
        "game day. Either port the thing or correct the reference."
    )


def test_the_pattern_finds_a_path_and_ignores_what_is_not_one() -> None:
    """The rule's own reach, measured rather than described.

    Without this, the test above passes on a pattern that matches nothing,
    which is the failure this repository has written down more than once.
    """
    assert referenced_paths("'see scripts/fetch_ncaaf_data.py now'") == {
        "scripts/fetch_ncaaf_data.py"
    }
    assert referenced_paths('"""docs/build_order.md and src/x/y.py"""') == {
        "docs/build_order.md",
        "src/x/y.py",
    }
    # Not paths: a bare directory, a module in dotted form, a sibling lab's
    # package name, and a URL path that is not this repository's.
    assert referenced_paths("'data/staging/ and ncaaf_betting_lab.selection'") == set()
    assert referenced_paths("'football_betting_lab/season.py'") == set()
    # `data/` is excluded deliberately; the policy file is meant to be absent.
    assert referenced_paths("'data/manual/staging_provider_policy.json'") == set()


def test_the_rule_would_fail_on_the_reference_it_was_written_for() -> None:
    """The synthetic bad input. A rule that has never been seen to fail is a
    rule nobody has checked — and this one is checked against the exact string
    that shipped, so a future port of the same shape cannot slip through."""
    shipped = '"Fetch with `scripts/fetch_football_data.py --seasons <season>`."'
    found = referenced_paths(shipped)
    assert found == {"scripts/fetch_football_data.py"}
    assert not (PROJECT_ROOT / "scripts/fetch_football_data.py").exists(), (
        "scripts/fetch_football_data.py is the NFL lab's fetcher. If it now "
        "exists here, this guard's worked example is no longer an example and "
        "the test needs a different one."
    )
