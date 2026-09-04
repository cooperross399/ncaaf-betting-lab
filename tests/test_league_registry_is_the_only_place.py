"""No league literal may appear outside the league registry.

This is the test that makes "adding NCAAF is a registry entry, not a
refactor" true rather than aspirational. Without it the guarantee is a
promise in a docstring, and the moment to discover it was broken is during
the NCAAF build, after the cost has been paid.

What is banned, precisely:

* the provider's sport-key prefix (`americanfootball_`), anywhere the trees
  named in `SCAN_ROOTS` reach — `src/` and `scripts/` — outside `leagues.py`;
* a constant that *is* a league key (`"nfl"`, `"ncaaf"`), or that opens one as
  a path, a filename or a policy-key segment. `names_league_key` is the whole
  rule, and it reads: split on `/` and `\\`, then for each segment —

  1. strip whitespace and bracketing off it and flag it if what is left is the
     key (a string with no separator in it is one segment, which is how a bare
     `"ncaaf"`, `"(ncaaf)"` and `"ncaaf\\n"` are caught);
  2. **skip it only if it carries whitespace**, which is the prose signal;
  3. otherwise split it on every character outside `[a-z0-9_]` and flag a piece
     that is the key, begins `<key>_`, or ends `_<key>`.

  Flagged, therefore: `"ncaaf"`, `"(ncaaf)"`, `"ncaaf\\n"`, `"data/raw/ncaaf"`,
  `"ncaaf/raw"`, `"ncaaf.csv"`, `"out/ncaaf_2024.csv"`, `"2024_ncaaf.csv"`,
  `"nfl-teams.csv"`, `"h2h:ncaaf"` and `"?sport=ncaaf&mkt=h2h"` — and also
  `"data/{ncaaf}/raw"`, `"$ncaaf/raw"`, `"raw/@ncaaf"`, `"glob/ncaaf*/x"`,
  `"data/[ncaaf]/raw"` and every other shape in `ATTACK_SHAPES`.

  Step 2 is the correction. It used to skip any segment that failed a
  character *allowlist*
  (`[a-z0-9._+:?=&|,-]`) rather than any segment carrying whitespace. The
  allowlist was described as a no-whitespace filter and was not one: a
  hard-coded key went invisible the moment its segment stood next to `{ } % $
  # ! ; @ * [ ] ( ) ~`. `ATTACK_SHAPES` is that regression written down as
  inputs, and `test_a_key_hidden_by_a_non_name_character_is_still_found` runs
  every one of them.

  Constants are read as `str` **and as `bytes`** — `Path(b"data/ncaaf/raw"
  .decode())` is a league literal wearing a `b` prefix, and reading only `str`
  made it a full pass.

`tests/` is deliberately outside those roots. A guard cannot scan itself
here: naming what is banned means holding it as a value, and this module does
so in `BANNED_SPORT_KEY_PREFIX`, in the `{"nfl"}` of `BANNED_LEAGUE_KEYS`, in
the `REGISTRY` path, in `ATTACK_SHAPES`, and in the assertions of
`test_the_registry_holds_exactly_the_leagues_that_are_built` — every one of
which `offending_strings` flags when pointed at this file. Scanning `tests/`
would therefore buy an exemption list, and an exemption list is the hole.
Shipped code is what the ban is for.

What is deliberately **not** banned: the letters NFL in prose. A docstring
explaining that NFL margins pile up on 3 and 7 is documentation, not a
dependency, and a test that forbade it would be gamed by rewording rather
than by fixing anything.

The gaps are not in this docstring. They are in
`test_the_shapes_this_guard_still_lets_through`, which asserts that each one
is still open — so closing a gap fails that test and forces the ledger to be
rewritten, and no gap can quietly go stale into a claim of coverage.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from ncaaf_betting_lab.leagues import LEAGUES, league_keys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "src" / "ncaaf_betting_lab" / "leagues.py"

#: Every league key the registry knows, plus `nfl`, which it never will —
#: `test_the_registry_holds_exactly_the_leagues_that_are_built` asserts that
#: `league_keys()` is `("ncaaf",)` and that `nfl` is absent from `LEAGUES`.
#: The hard-coded key is the point: the machinery here was ported from the NFL
#: lab, so an `nfl` literal that came across with it has to trip this guard
#: even though no registry entry will ever name that league.
BANNED_LEAGUE_KEYS = frozenset(set(league_keys()) | {"nfl"})

#: The provider's own vocabulary for these leagues.
BANNED_SPORT_KEY_PREFIX = "americanfootball_"


#: The trees this guard is responsible for reading. Named once so the
#: emptiness check below and the parametrize cannot drift apart.
SCAN_ROOTS = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts")


def python_files(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    """Every module under `roots`, and never an empty list.

    `Path.rglob` on a directory that has been moved or renamed yields nothing
    and raises nothing, so this function used to hand `parametrize` an empty
    list and the whole file went green having read no code at all. Zero
    findings and zero coverage are the same colour in a test report, which is
    the failure this raise exists to separate.

    Each root is counted on its own: src/ vanishing while scripts/ still
    yields modules is exactly as blind, and would survive a check on the
    total.
    """
    found: list[Path] = []
    for root in roots:
        here = [
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts and path != REGISTRY
        ]
        if not here:
            raise AssertionError(
                f"{root} contributed no Python files to the league-literal "
                "scan. A moved or renamed tree has to be a red build; a guard "
                "that reads nothing passes everything."
            )
        found.extend(here)
    return sorted(found)


def docstring_nodes(tree: ast.AST) -> set[int]:
    """Every string constant that is a docstring, by id.

    Docstrings are prose about the code and are exempt. Everything else is a
    value the code actually uses. Bytes are never collected here: `b"..."` in
    the first statement position is not a docstring to the interpreter either,
    so a bytes constant is always a value.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


#: Path separators. A league key is a directory segment under `data/` and the
#: prefix on every output file, so a literal that hard-codes one is nearly
#: always writing a path.
PATH_SEPARATORS = re.compile(r"[\\/]")

#: The prose signal, and the only reason a segment is skipped. A segment that
#: carries whitespace is a sentence rather than a name:
#: `"NCAAF. Margins pile up on 3 and 7"` has text before its first dot that is
#: exactly the key, and reading that as the file `ncaaf.<something>` would fail
#: correct code for explaining itself.
#:
#: What stood here before was a character allowlist
#: (`[a-z0-9._+:?=&|,-]`) whose `fullmatch` decided whether to skip. It was
#: described as a no-whitespace filter and was not one — it skipped every
#: segment built from any character nobody had thought to list, which is how a
#: hard-coded key next to `{ } % $ # ! ; @ * [ ] ( ) ~` became invisible.
SEGMENT_IS_PROSE = re.compile(r"\s")

#: Inside a segment that is not prose, every character a name is *not* built
#: from is a join. This is deliberately the complement of `[a-z0-9_]` rather
#: than a list of the joins anyone happened to enumerate: under a complement, a
#: character nobody thought of splits a name apart, and under a list it hides
#: one. Underscore is excluded from the split on purpose — it is handled by the
#: prefix and suffix tests in `names_league_key`, so `fetch_ncaaf_data.py`,
#: which cfbfastr's "no schedule cached" message names in prose, does not trip
#: the guard.
NAME_JOINS = re.compile(r"[^a-z0-9_]")

#: Whitespace and the bracketing a key gets quoted in, stripped off either end
#: before the whole-string comparison and again per path segment, so
#: `"ncaaf\n"`, `"(ncaaf)"`, `"( ncaaf )"` and `"data/ ncaaf"` are read as the
#: key they are.
#:
#: A regex rather than a `str.strip` argument list, because a list is another
#: allowlist: `\v`, `\f` and a non-breaking space are whitespace to
#: `SEGMENT_IS_PROSE` and were not in the list, so `"data/\vncaaf/raw"` was
#: skipped as prose and stripped by nobody — the same shape of hole this file
#: has now been bitten by twice. `\s` and the bracket class between them cover
#: every character either half of the rule reacts to.
EDGE_NOISE = re.compile(r"^[\s\"'`()\[\]{}<>]+|[\s\"'`()\[\]{}<>]+$")


def strip_edges(text: str) -> str:
    """`text` without the whitespace and bracketing around it."""
    return EDGE_NOISE.sub("", text)


def names_league_key(text: str, key: str) -> bool:
    """Whether `text` uses `key` as a value: a whole path segment, or a piece.

    Case-insensitive. The rule is the numbered list in the module docstring,
    and it is exercised shape by shape in
    `test_names_league_key_flags_the_shapes_this_docstring_claims`.

    There is no separate whole-string comparison. There used to be, and it was
    redundant the moment the segment strip arrived: a string with no separator
    in it splits into one segment that is the whole string, and one that does
    contain a separator cannot strip down to a key. Deleting a mutation nobody
    could observe is not tidying — a line no test can kill is a line no reader
    can trust.

    This is a correction of a narrowing, not a widening. The version it
    replaces used `NAME_SHAPED`, a character allowlist, as a reason to *skip* a
    segment; the allowlist is now gone and only whitespace skips. Every shape
    in `ATTACK_SHAPES` passed that version and is caught by this one, which
    `test_a_key_hidden_by_a_non_name_character_is_still_found` runs, and
    `test_no_earlier_spelling_of_this_rule_flags_what_this_one_misses` checks
    that neither earlier spelling caught anything this one lets through.
    """
    lowered = text.lower()
    for segment in PATH_SEPARATORS.split(lowered):
        if strip_edges(segment) == key:
            return True
        if SEGMENT_IS_PROSE.search(segment):
            continue
        for piece in NAME_JOINS.split(segment):
            if piece == key or piece.startswith(f"{key}_") or piece.endswith(f"_{key}"):
                return True
    return False


def constant_text(node: ast.Constant) -> str | None:
    """The readable text of a constant, or None if it holds no text.

    `str` and `bytes` both, because `Path(b"data/ncaaf/raw".decode())` is a
    league literal and reading only `str` made it a full pass. Bytes are
    decoded permissively: a byte sequence that is not valid UTF-8 still has to
    be read for the ASCII a key is spelled in, and refusing to decode would
    hand the whole constant back as unexamined.
    """
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        return node.value.decode("utf-8", errors="replace")
    return None


def offending_strings(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    exempt = docstring_nodes(tree)
    problems: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        text = constant_text(node)
        if text is None or id(node) in exempt:
            continue
        lowered = text.lower()
        if BANNED_SPORT_KEY_PREFIX in lowered:
            problems.append((node.lineno, text))
            continue
        for key in BANNED_LEAGUE_KEYS:
            if names_league_key(text, key):
                problems.append((node.lineno, text))
                break
    return problems


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.name))
def test_no_module_outside_the_registry_writes_a_league_literal(path: Path) -> None:
    problems = offending_strings(path)
    assert not problems, (
        f"{path.relative_to(PROJECT_ROOT)} writes a league literal that belongs "
        f"in leagues.py: {problems}. Take it from the League — "
        "`league.provider_sport_key`, `league.data_dir_segment`, "
        "`league.output_name(...)`, `league.policy_key()` — so that adding "
        "NCAAF is a registry entry and not a search-and-replace."
    )


def test_a_root_that_contributes_no_files_fails_rather_than_scanning_nothing(
    tmp_path: Path,
) -> None:
    """The parametrize above is a gate only while its file list is non-empty.

    Before this check, pointing the scan at a directory that no longer exists
    produced no parametrized cases and no failure — the guard reported clean
    on a repository it had never opened. All three shapes of that bug are
    covered: an empty root, a missing root, and a dead root travelling
    alongside a live one.
    """
    with pytest.raises(AssertionError, match="contributed no Python files"):
        python_files(roots=(tmp_path,))

    with pytest.raises(AssertionError, match="contributed no Python files"):
        python_files(roots=(tmp_path / "never_existed",))

    with pytest.raises(AssertionError, match="contributed no Python files"):
        python_files(roots=(PROJECT_ROOT / "src", tmp_path))

    assert python_files(roots=(PROJECT_ROOT / "src",))
    assert python_files(roots=(PROJECT_ROOT / "scripts",))


def test_the_registry_holds_exactly_the_leagues_that_are_built() -> None:
    """College football ships here; the NFL lives in its own repository.

    Both facts are asserted, because the second is the one a future session is
    liable to undo — the machinery came from the NFL lab and the temptation to
    add it back as a second entry is real. The two labs share no code and no
    data, so an `nfl` entry here would be a league with no adapter, no market
    registry and no results feed, silently priced as though it had them.
    """
    assert league_keys() == ("ncaaf",)
    assert "nfl" not in LEAGUES

def test_every_league_names_an_adapter_and_a_market_registry() -> None:
    for key, league in LEAGUES.items():
        assert league.key == key
        assert league.provider_sport_key.startswith(BANNED_SPORT_KEY_PREFIX)
        assert league.data_adapter, f"{key} names no data adapter"
        assert league.market_registry, f"{key} names no market registry"
        assert league.daily_credit_cap > 0, f"{key} has no credit cap"


def test_outputs_are_league_prefixed_so_two_leagues_cannot_overwrite_each_other() -> None:
    """An unprefixed output is a file two leagues would both write.

    The second one to run would silently become the record, and the evidence
    for the first would be gone with no error anywhere.
    """
    for league in LEAGUES.values():
        name = league.output_name("forward_evidence", ".md")
        assert name.startswith(f"{league.key}_")
        assert name == f"{league.key}_forward_evidence.md"


def test_allowlisting_a_market_in_one_league_cannot_allowlist_it_in_another() -> None:
    """Policy keys carry the league, so a receipt covers one league only."""
    keys = {league.policy_key() for league in LEAGUES.values()}
    assert len(keys) == len(LEAGUES)
    for league in LEAGUES.values():
        assert league.policy_key().endswith(f":{league.key}")


#: The shapes the module docstring promises are caught. Held as a constant so
#: the shape list and the comparison against earlier spellings of the rule read
#: the same corpus and cannot drift apart.
MUST_FLAG = (
    "ncaaf",
    "NCAAF",
    "data/ncaaf/raw",
    "data/raw/ncaaf",
    "ncaaf/raw",
    "/ncaaf",
    "ncaaf/",
    "./ncaaf",
    "ncaaf.csv",
    "data/raw/ncaaf.csv",
    "data\\raw\\ncaaf",
    "ncaaf_forward_evidence.md",
    "out/ncaaf_2024.csv",
    "2024_ncaaf.csv",
    "raw_ncaaf",
    "ncaaf-raw",
    "(ncaaf)",
    "'ncaaf'",
    "ncaaf\n",
    "ncaaf\t",
    " ncaaf ",
    "h2h:ncaaf",
    "spreads:ncaaf:2026",
    "?sport=ncaaf&mkt=h2h",
    "My Reports/ncaaf",
    "data.ncaaf",
    "reports.ncaaf.summary",
    "ncaaf_betting_lab.data.cfbfastr",
    "https://api.example.com/v4/sports/ncaaf/odds",
)

#: The shapes that are deliberately let through, so that correct code is not
#: failed for explaining itself.
MUST_PASS = (
    # Prose. Banning the letters would be gamed by rewording, and a
    # docstring explaining the league is documentation, not a dependency.
    "the ncaaf season",
    "NCAAF. Margins pile up on 3 and 7",
    "no NCAAF games were returned by the provider",
    # The one real-tree edge: cfbfastr's cache message names this script.
    "fetch_ncaaf_data.py",
    "data/fetch_ncaaf_data/raw",
    "`scripts/fetch_ncaaf_data.py --seasons {season}` before anything reads",
    # Near misses that are not the key.
    "ncaa",
    "ncaaff",
    "xncaaf",
    "football",
    # Template strings that take the key from the League at runtime, which
    # is the whole point of the registry.
    "{league}_summary.md",
    "%s_summary.md",
)

#: A hard-coded league key standing next to a character the old allowlist did
#: not list. Every one of these passed the rule this file shipped with, and
#: every one is a path, a glob, a shell or template interpolation, a URL or a
#: cache key that a module could plausibly write. They are held as data because
#: a regression that is only described gets described away; these get executed.
#:
#: Two families are represented and both matter. The bracketing family
#: (`{ } ( ) [ ]`) is what template and glob syntax puts around a segment; the
#: punctuation family (`% $ # ! ; @ * ~` and leading or trailing whitespace) is
#: what shells, URLs and cache keys put beside one.
ATTACK_SHAPES = (
    "data/{ncaaf}/raw",
    "out/{ncaaf}_2024.csv",
    "raw/ncaaf{}",
    "{ncaaf}/raw",
    "data/${ncaaf}/raw",
    "data/ncaaf%2Fraw",
    "raw/ncaaf%2024",
    "%ncaaf%/out",
    "%(ncaaf)s/raw",
    "$ncaaf/raw",
    "raw/ncaaf$",
    "raw/#ncaaf",
    "raw/ncaaf#2024",
    "reports/ncaaf!/x",
    "raw/ncaaf!",
    "cache/ncaaf;raw",
    "raw/;ncaaf",
    "s3://bucket@ncaaf/raw",
    "ncaaf@2024/raw",
    "raw/@ncaaf",
    "glob/ncaaf*/x",
    "raw/*ncaaf",
    "data/[ncaaf]/raw",
    "raw/ncaaf[0]",
    "data/(ncaaf)/raw",
    "~ncaaf/raw",
    "data/~/ncaaf!",
    "data/ ncaaf",
    "data/ncaaf /raw",
    "out/\tncaaf/x",
    # Whitespace the old bracketing list did not contain, which is how the
    # padding cases above would have come back: `SEGMENT_IS_PROSE` reads these
    # as whitespace and skips the segment, so anything that does not also strip
    # them lets the key through.
    "data/\vncaaf/raw",
    "data/ncaaf\f/raw",
    "data/\u00a0ncaaf/raw",
    "( ncaaf )/raw",
)


def test_names_league_key_flags_the_shapes_this_docstring_claims() -> None:
    """Every shape the module docstring names, run through the matcher.

    A docstring describing a guard is a claim about behaviour, and the way to
    check a claim about behaviour is to feed it the input. Both directions are
    here: the shapes that must be caught, and the shapes that are deliberately
    let through — the second list is the one that keeps correct prose from
    failing the build, and it is why the first can be as wide as it is.
    """
    for text in MUST_FLAG:
        assert names_league_key(text, "ncaaf"), f"{text!r} names a league key"

    for text in MUST_PASS:
        assert not names_league_key(text, "ncaaf"), (
            f"{text!r} is not a league literal and flagging it would fail "
            "correct code. If this shape must be banned, ban it deliberately "
            "and rewrite the module docstring, which promises it passes."
        )

    # `nfl` is banned on the same shapes even though no registry entry names it.
    assert names_league_key("reports/nfl/summary.md", "nfl")
    assert names_league_key("nfl-teams.csv", "nfl")
    assert names_league_key("raw/nfl", "nfl")
    assert not names_league_key("the nfl lab lives in its own repository", "nfl")


def test_a_key_hidden_by_a_non_name_character_is_still_found() -> None:
    """The regression, as inputs rather than as a paragraph.

    The rule this file shipped with skipped any path segment that failed a
    character allowlist. The allowlist did not list `{ } % $ # ! ; @ * [ ] ( )
    ~`, so a hard-coded key standing next to one of those was read as prose and
    passed — a guard that got narrower while its own docstring called the
    change a widening.

    Every shape here is a path, glob, template, URL or cache key a module could
    write, and every one has to be caught. The count is reported from the
    corpus rather than written down, so the sample size in a failure message is
    always the sample size that ran.
    """
    missed = [text for text in ATTACK_SHAPES if not names_league_key(text, "ncaaf")]
    assert not missed, (
        f"{len(missed)} of {len(ATTACK_SHAPES)} attack shapes hide a league "
        f"key from this guard: {missed}. A non-name character next to the key "
        "must split the name apart, never excuse the segment from being read."
    )


def test_no_earlier_spelling_of_this_rule_flags_what_this_one_misses() -> None:
    """Both earlier rules kept as second opinions, on a corpus where they fire.

    `names_league_key` has been rewritten twice. The comparison that used to
    stand here read only `src/` and `scripts/`, where the reference rule
    matches nothing at all — so it compared two rules on an empty set and
    passed while the live rule was losing every shape in `ATTACK_SHAPES`. A
    second opinion that never fires is not a second opinion.

    The fix is the corpus, not the comparison: the shipped tree *plus* every
    shape this module holds, and an assertion that each reference rule actually
    fired on it. `narrow` is the rule from before the first rewrite; `allowlist`
    is the rule from before this one, the one that skipped a segment failing a
    character allowlist. Anything either flags, the live rule must flag too.
    """

    def narrow(text: str, key: str) -> bool:
        lowered = text.lower()
        return (
            lowered == key
            or f"/{key}/" in lowered
            or lowered.startswith(f"{key}_")
        )

    name_shaped = re.compile(r"[a-z0-9._+:?=&|,-]+")
    allowlist_joins = re.compile(r"[.:?=&|,-]")

    def allowlist(text: str, key: str) -> bool:
        lowered = text.lower()
        if strip_edges(lowered) == key:
            return True
        for segment in PATH_SEPARATORS.split(lowered):
            if not name_shaped.fullmatch(segment):
                continue
            for piece in allowlist_joins.split(segment):
                if (
                    piece == key
                    or piece.startswith(f"{key}_")
                    or piece.endswith(f"_{key}")
                ):
                    return True
        return False

    corpus: list[tuple[str, str]] = [
        (source, text)
        for source, group in (
            ("MUST_FLAG", MUST_FLAG),
            ("MUST_PASS", MUST_PASS),
            ("ATTACK_SHAPES", ATTACK_SHAPES),
        )
        for text in group
    ]

    files = python_files()
    assert files, "nothing to compare the two rules on"
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        exempt = docstring_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant):
                continue
            text = constant_text(node)
            if text is None or id(node) in exempt:
                continue
            corpus.append((f"{path.name}:{node.lineno}", text))

    fired = {"narrow": 0, "allowlist": 0}
    for reference, name in ((narrow, "narrow"), (allowlist, "allowlist")):
        for source, text in corpus:
            for key in BANNED_LEAGUE_KEYS:
                if reference(text, key):
                    fired[name] += 1
                    assert names_league_key(text, key), (
                        f"{source}: {text!r} is caught by the {name} rule this "
                        f"one replaced and is not caught now, on a corpus of "
                        f"{len(corpus)} constants. A rewrite dropped a case."
                    )

    for name, count in fired.items():
        assert count > 0, (
            f"the {name} rule matched nothing across {len(corpus)} constants, "
            "so comparing it against the live rule proved nothing. Zero "
            "findings and zero coverage are the same colour."
        )


def test_the_guard_still_flags_the_literals_this_module_holds() -> None:
    """The module docstring's reason for keeping `tests/` out of SCAN_ROOTS.

    It claims things in this file would be flagged if the guard were pointed at
    itself, and uses that to argue an exemption list is the only way `tests/`
    could be scanned. The claim is checked here rather than trusted, because it
    is the load-bearing half of that argument.
    """
    flagged = {text for _, text in offending_strings(Path(__file__).resolve())}
    assert BANNED_SPORT_KEY_PREFIX in flagged
    assert "nfl" in flagged
    assert "ncaaf" in flagged
    assert any("ncaaf_betting_lab" == text for text in flagged), (
        "the REGISTRY path no longer contributes a flagged literal"
    )
    assert set(ATTACK_SHAPES) <= flagged, (
        "the attack shapes this module holds as data are no longer flagged "
        "when the guard is pointed at this file, so the argument for keeping "
        "tests/ out of SCAN_ROOTS has lost its evidence"
    )


def test_a_league_literal_written_as_bytes_is_read_like_any_other(
    tmp_path: Path,
) -> None:
    """`b"..."` was a full pass, and `.decode()` gives it straight back.

    `offending_strings` read `ast.Constant` nodes holding `str` and no others,
    so `Path(b"data/ncaaf/raw".decode())` in a live module under `src/` was a
    league literal the guard walked past. The `b` prefix is not an abstraction
    over the key; it is the key.
    """
    module = tmp_path / "bytes_literal.py"
    module.write_text(
        'from pathlib import Path\nRAW = Path(b"data/ncaaf/raw".decode())\n',
        encoding="utf-8",
    )
    assert offending_strings(module), (
        "a bytes league literal is invisible again. The decode is the whole "
        "point: it hands the key back unchanged."
    )

    for source in (
        'KEY = b"ncaaf"\n',
        'SPORT = b"americanfootball_ncaaf"\n',
        'OUT = b"out/ncaaf_2024.csv"\n',
        'BAD = b"\\xff\\xfe" + b"data/ncaaf/raw"\n',
    ):
        module.write_text(source, encoding="utf-8")
        assert offending_strings(module), f"{source!r} writes a league literal"

    module.write_text('OK = b"data/raw"\nALSO = b"\\xff\\xfe"\n', encoding="utf-8")
    assert offending_strings(module) == [], (
        "bytes that name no league key are being reported, which would fail "
        "correct code that happens to hold a byte string"
    )


def test_the_shapes_this_guard_still_lets_through(tmp_path: Path) -> None:
    """The known-gaps ledger: what gets past this guard, asserted as open.

    Written as executable claims rather than as a paragraph, for two reasons.
    A gap that is only described drifts into a claim of coverage the moment
    someone reads quickly; and a gap that is *asserted* open cannot be closed
    silently — closing one fails this test and forces the ledger to be
    rewritten with it.
    """
    # 1. A key as an interior underscore piece. Deliberate, and decided by the
    #    real tree: cfbfastr's "no schedule cached" message names this script
    #    in prose, and flagging it would fail correct code.
    #    `"_ncaaf_"` is the same gap seen from the other side: underscore on
    #    one side only is caught (`"raw_ncaaf"`, `"ncaaf_2024"`), underscore on
    #    both is not, because the piece is neither prefixed nor suffixed by the
    #    key — it contains it.
    for text in (
        "fetch_ncaaf_data.py",
        "data/fetch_ncaaf_data/raw",
        "data/_ncaaf_/raw",
    ):
        assert not names_league_key(text, "ncaaf")

    # 2. A path segment with whitespace *inside* it, rather than around it.
    #    Padding is stripped and caught (`"data/ ncaaf"` is in ATTACK_SHAPES),
    #    but a segment whose whitespace has anything beyond bracketing outside
    #    it is read as prose and skipped. This is the price of the prose
    #    exemption: the same rule that lets "NCAAF. Margins pile up on 3 and 7"
    #    pass lets these pass, and the whitespace need not be a plain space —
    #    `\v`, `\f` and a non-breaking space are whitespace to
    #    `SEGMENT_IS_PROSE` too. Found by sweeping every printable character
    #    plus five exotic spaces through six positions, so the shape of the
    #    residue is measured rather than guessed.
    for text in (
        "data/ncaaf raw/x",
        "my ncaaf dir/out",
        "out/the ncaaf files",
        "out/( ncaaf ).csv",
        "out/{ ncaaf }.csv",
        "data/x ncaaf y/raw",
        "data/x\vncaaf\vy/raw",
        "data/x\u00a0ncaaf\u00a0y/raw",
    ):
        assert not names_league_key(text, "ncaaf")

    # 3. Anything that is not a constant in this module's own AST. The walk
    #    reads constants; a name assembled at run time is outside its reach.
    invisible = {
        "run-time concatenation": 'KEY = "nca" + "af"\n',
        "spelled by chr()": 'KEY = "".join(chr(c) for c in (110, 99, 97, 97, 102))\n',
        "a bare name, not a string": "ncaaf = 1\n",
        "built by str.format": 'KEY = "nca{}".format("af")\n',
        # Reading bytes closed `b"ncaaf"`; it did not close arithmetic on
        # bytes, which is the same gap in the other alphabet.
        "bytes joined at run time": 'KEY = b"nca" + b"af"\n',
        "bytes built by encoding pieces": 'KEY = "nca".encode() + "af".encode()\n',
    }
    for label, source in invisible.items():
        module = tmp_path / "invisible.py"
        module.write_text(source, encoding="utf-8")
        assert offending_strings(module) == [], (
            f"{label} is now reported, which is the guard getting wider. Move "
            "the case out of this ledger and into the caught group in "
            "`test_the_guard_reads_a_key_that_is_a_constant`."
        )

    # 4. A key living in a file that is not a `.py`. The scan globs modules, so
    #    a YAML, JSON or CSV holding the key is never opened at all.
    not_python = tmp_path / "not_python"
    not_python.mkdir()
    (not_python / "config.yaml").write_text("root: data/ncaaf/raw\n", encoding="utf-8")
    (not_python / "rows.csv").write_text("league\nncaaf\n", encoding="utf-8")
    (not_python / "module.py").write_text("x = 1\n", encoding="utf-8")
    scanned = python_files(roots=(not_python,))
    assert [p.name for p in scanned] == ["module.py"], (
        "the scan now reads something other than .py files; the ledger entry "
        "saying a key in a YAML or CSV is never opened has gone stale"
    )


def test_the_guard_reads_a_key_that_is_a_constant(tmp_path: Path) -> None:
    """The reach the walk does have, as running modules.

    The counterpart to the ledger above. Each source here is written to disk
    and handed to `offending_strings`, so what is checked is the guard's
    behaviour on a module rather than a claim about it.
    """
    caught = {
        "plain literal": 'KEY = "ncaaf"\n',
        "implicit concatenation, folded by the parser": 'KEY = "nca" "af"\n',
        "f-string with the key in its literal part": 'P = f"data/{root}/ncaaf/raw"\n',
        "joined with os.sep at run time": 'import os\nP = "data" + os.sep + "ncaaf"\n',
        "provider sport key": 'S = "americanfootball_ncaaf"\n',
        "policy key": 'K = "h2h:ncaaf"\n',
        "bytes literal": 'KEY = b"ncaaf"\n',
        "bytes decoded into a Path": 'from pathlib import Path\n'
        'P = Path(b"data/ncaaf/raw".decode())\n',
        "brace-wrapped segment": 'P = "data/{ncaaf}/raw"\n',
        "shell interpolation": 'P = "$ncaaf/raw"\n',
        "glob": 'P = "glob/ncaaf*/x"\n',
    }
    for label, source in caught.items():
        module = tmp_path / "caught.py"
        module.write_text(source, encoding="utf-8")
        assert offending_strings(module), f"{label} writes a league literal"
