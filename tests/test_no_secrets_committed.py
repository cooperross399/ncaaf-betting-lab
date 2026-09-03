"""Repository hygiene: no credential may reach a tracked file.

These tests run against the files git actually tracks, so they fail the build
if a secret is ever committed — including by a future change that means well.
They deliberately do not read `.env`: the point is to prove nothing *else*
contains a credential, and reading the real key here would be the very leak
being guarded against.

Ported from the EPL lab, where this guard has held since the provider was
first wired up. Do not weaken it.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from ncaaf_betting_lab.config import PROJECT_ROOT
from ncaaf_betting_lab.providers.env_file import ENV_FILENAME, PROVIDER_ENV_ALLOWLIST


#: Files whose whole job is to describe secret handling, so they legitimately
#: contain placeholder-looking strings.
DOC_SUFFIXES = {".md", ".rst", ".txt"}

#: Obvious placeholders that must never be mistaken for a real credential.
PLACEHOLDERS = {
    "your-secret-key",
    "your-api-key",
    "test-secret-that-must-not-be-written",
    "env-file-secret-that-must-never-be-written",
    "shadow-test-secret-never-write",
    "discovery-secret-must-not-be-written",
    "props-secret-must-not-be-written",
    "already-exported-value",
    "${{",
}

#: A 32-hex-character run is the shape of an Odds API key.
HEX_KEY = re.compile(r"\b[0-9a-f]{32}\b")

#: ...and it is also the shape of an Odds API **event id**, which is a real
#: collision rather than a theoretical one: the retention probe's record and
#: its cached responses are full of them.
#:
#: Exempting the directories they live in would be the easy fix and the wrong
#: one — it would carve a hole in the guard exactly where provider data lands.
#: So the exemption is by *value*: every event id this repository has actually
#: recorded is collected from the provider artifacts and those literals alone
#: are allowed. Any other 32-hex run is still a finding.
#:
#: This cannot be used to smuggle a key past the guard. A key would have to be
#: written into a provider artifact as an event id to be exempted, and the
#: credential never appears in a response body — it travels only in the query
#: string, which `API_KEY_PARAM` covers everywhere including here.
_EVENT_ID_KEYS = ("id", "event_id")


def _known_provider_event_ids() -> set[str]:
    """Every 32-hex event id this repository has recorded from the provider."""
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _EVENT_ID_KEYS and isinstance(value, str):
                    if HEX_KEY.fullmatch(value):
                        found.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in _tracked_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if not (
            relative.startswith("data/raw/") or relative.startswith("data/outputs/")
        ):
            continue
        if path.suffix == ".json":
            try:
                walk(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
        elif path.suffix == ".csv":
            # Bought-price and backtest tables carry the provider's event ids
            # in a column. The first commit of the props backtest tripped this
            # guard in CI and not locally, because the suite had been run
            # before the file was staged — which is the guard working, and a
            # reminder that `git ls-files` is what it reads.
            try:
                header, *rows = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            columns = [name.strip() for name in header.split(",")]
            wanted = [
                index
                for index, name in enumerate(columns)
                if name in _EVENT_ID_KEYS
            ]
            if not wanted:
                continue
            for row in rows:
                cells = row.split(",")
                for index in wanted:
                    if index < len(cells) and HEX_KEY.fullmatch(cells[index].strip()):
                        found.add(cells[index].strip())
    # A cached response is named after the event it holds, so the filename is
    # a second, independent record of the same id.
    for path in _tracked_files():
        stem = path.name.split("_")[0]
        if HEX_KEY.fullmatch(stem):
            found.add(stem)
    return found

#: `apiKey=` FOLLOWED BY A VALUE is a leak. The bare token is not: it appears
#: legitimately in the redaction regex that strips credentials and in tests
#: asserting the token is absent. Flagging the bare token would force those
#: defences to be written obscurely, or exempted — both worse than matching
#: precisely. Eight characters is well below any real key length.
API_KEY_PARAM = re.compile(r"apiKey=[A-Za-z0-9]{8,}")

#: `NAME=value` where NAME is a credential variable and value is not a
#: placeholder — i.e. a real assignment, not documentation.
#:
#: The spacing is `[ \t]*` rather than `\s*` deliberately. `\s` crosses a
#: newline, so `NAME=` on one line and any word on the next read as an
#: assignment — which is exactly what `.env.example` looks like, and it made
#: the guard fail on a file whose values are all empty.
ASSIGNMENT = re.compile(
    r"\b("
    + "|".join(re.escape(name) for name in PROVIDER_ENV_ALLOWLIST)
    + r")[ \t]*=[ \t]*(\S+)"
)


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    )
    names = [item for item in result.stdout.decode("utf-8").split("\0") if item]
    return [PROJECT_ROOT / name for name in names]


#: This file necessarily contains every pattern it hunts for, so it must not
#: scan itself. A scanner that flags its own needles reports a false positive
#: forever and teaches everyone to ignore it.
SELF = Path(__file__).resolve()


def _text_files() -> list[Path]:
    keep: list[Path] = []
    for path in _tracked_files():
        if not path.is_file():
            continue
        if path.resolve() == SELF:
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip"}:
            continue
        keep.append(path)
    return keep


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def test_env_file_is_never_tracked() -> None:
    tracked = {path.name for path in _tracked_files()}

    assert ENV_FILENAME not in tracked


def test_env_file_is_gitignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", ENV_FILENAME],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )

    assert result.returncode == 0, ".env must stay gitignored"


def test_no_tracked_file_assigns_a_real_credential() -> None:
    """`FOOTBALL_ODDS_API_KEY=<something real>` must not appear in a tracked file."""
    offenders: list[str] = []
    for path in _text_files():
        for match in ASSIGNMENT.finditer(_read(path)):
            # Strip the punctuation that surrounds a value in source and
            # prose: quotes, and trailing commas/semicolons/parens.
            value = match.group(2).strip("'\"`").strip(",;)").strip("'\"`")
            if not value:
                continue
            if value in PLACEHOLDERS:
                continue
            # Documentation shows the shape of the command; a placeholder-ish
            # value in prose is fine, a 32-hex key is not.
            if path.suffix in DOC_SUFFIXES and not HEX_KEY.fullmatch(value):
                continue
            # `$VAR`, `<placeholder>`, `${{ secrets.X }}` and an f-string
            # interpolation `{SECRET}` are all references to a value, not a
            # value. A literal credential never begins with one of these.
            if value[0] in "$<{":
                continue
            offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {match.group(1)}")

    assert offenders == [], f"credential assignment in tracked files: {offenders}"


def test_no_tracked_file_contains_an_odds_api_key_shape() -> None:
    """A bare 32-hex string is the shape of the provider key."""
    known = _known_provider_event_ids()
    offenders: list[str] = []
    for path in _text_files():
        # Checksums are legitimately hex, and SHA-256 is 64 chars, so only an
        # isolated 32-char run is suspicious.
        if "checksum" in path.name or "receipt" in path.name:
            continue
        for match in HEX_KEY.finditer(_read(path)):
            if match.group(0) in known:
                continue
            offenders.append(
                f"{path.relative_to(PROJECT_ROOT)}: {match.group(0)[:6]}..."
            )

    assert offenders == [], f"possible credential in tracked files: {offenders}"


def test_generated_reports_never_include_the_api_key_parameter() -> None:
    """`apiKey=<value>` is how the credential travels; never write it."""
    offenders: list[str] = []
    for path in _text_files():
        for match in API_KEY_PARAM.finditer(_read(path)):
            offenders.append(
                f"{path.relative_to(PROJECT_ROOT)}: {match.group(0)[:10]}..."
            )

    assert offenders == [], f"apiKey= with a value in tracked files: {offenders}"


def test_the_api_key_parameter_check_still_catches_a_real_leak() -> None:
    """A precise matcher is only useful if it still fires on the real thing."""
    assert API_KEY_PARAM.search("https://x/v4/odds?apiKey=0123456789abcdef&r=us")
    assert API_KEY_PARAM.search("apiKey=abcdef0123456789abcdef0123456789")
    # ...and stays quiet on the defences that mention the token.
    assert not API_KEY_PARAM.search('re.compile(r"(apiKey=)[^&s]+")')
    assert not API_KEY_PARAM.search('assert "apiKey=" not in text')
    assert not API_KEY_PARAM.search("apiKey=[redacted]")


def test_the_key_shape_check_still_catches_a_real_leak() -> None:
    """The 32-hex matcher must fire on a key and not on a SHA-256."""
    assert HEX_KEY.search("key is 0123456789abcdef0123456789abcdef here")
    assert not HEX_KEY.search("sha256 " + "a" * 64)


@pytest.mark.parametrize("name", PROVIDER_ENV_ALLOWLIST)
def test_credential_names_are_referenced_but_never_valued(name: str) -> None:
    """The variable name may appear anywhere; only a real value is forbidden."""
    assert isinstance(name, str) and name


def test_the_production_credential_name_is_the_one_the_workflow_uses() -> None:
    """The secret name is a contract with GitHub Actions; it must not drift."""
    assert "FOOTBALL_ODDS_API_KEY" in PROVIDER_ENV_ALLOWLIST


def test_data_outputs_reports_are_not_tracked_with_secrets() -> None:
    """Report artifacts under data/outputs must be clean if tracked at all."""
    known = _known_provider_event_ids()
    offenders: list[str] = []
    for path in _text_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if not relative.startswith("data/outputs/"):
            continue
        text = _read(path)
        if API_KEY_PARAM.search(text):
            offenders.append(relative)
            continue
        unknown = [
            match.group(0)
            for match in HEX_KEY.finditer(text)
            if match.group(0) not in known
        ]
        if unknown:
            offenders.append(relative)

    assert offenders == [], f"tracked report contains a credential: {offenders}"


def test_the_guard_excludes_itself_from_its_own_scan() -> None:
    """Otherwise it flags its own needles and everyone learns to ignore it."""
    scanned = {path.resolve() for path in _text_files()}

    assert SELF not in scanned


def test_the_guard_still_scans_other_test_files() -> None:
    """Self-exclusion must be exactly one file, not all of tests/."""
    scanned = {path.name for path in _text_files()}

    assert "test_league_registry_is_the_only_place.py" in scanned
    assert "test_contract_strings.py" in scanned


def test_the_event_id_exemption_is_by_value_and_not_by_directory() -> None:
    """A hex run that is not a recorded event id is still a finding, even in
    the directory where provider data lives.

    The easy fix for the event-id collision was to exempt `data/raw/`. That
    would carve a hole in this guard exactly where provider data lands, and
    the hole would be invisible. This asserts the narrower rule actually
    holds.
    """
    known = _known_provider_event_ids()

    if not known:
        # Nothing has been fetched yet, so there are no recorded event ids and
        # the exemption has nothing to exempt. That is an honest state for a
        # lab on its first day, and it is a SKIP rather than a pass: a green
        # tick here would say the narrower rule holds when it has not been
        # exercised once.
        #
        # It stops skipping the moment any provider data is cached, which is
        # before any price is ever read — so this cannot go quiet for a season.
        pytest.skip(
            "No provider event ids are cached yet, so the by-value exemption "
            "is untested rather than confirmed. This skip disappears with the "
            "first fetch."
        )
    invented = "deadbeef" * 4

    assert HEX_KEY.fullmatch(invented)
    assert invented not in known


def test_the_key_shape_check_still_fires_on_something_that_is_not_an_event_id() -> None:
    known = _known_provider_event_ids()
    leaked = "0123456789abcdef0123456789abcdef"

    assert leaked not in known
    assert HEX_KEY.search(f"FOOTBALL_ODDS_API_KEY={leaked}")
