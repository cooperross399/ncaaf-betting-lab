"""Repository hygiene: no credential may reach a tracked file.

These tests run against the files git actually tracks, so they fail the build
if a secret is ever committed — including by a future change that means well.
They deliberately do not read `.env`: the point is to prove nothing *else*
contains a credential, and reading the real key here would be the very leak
being guarded against.

Ported from the EPL lab. Do not weaken it — and do not read the port as a
warranty. Six holes in this copy have each let a real credential be committed
with the suite still green. The first three: an exemption earned in
`data/outputs/` was spendable anywhere in the tree, a 32-hex run in a
*filename* was scanned by nothing, and a credential name this module did not
know could be assigned in Markdown. Fixing those three left three more, which
is the pattern worth naming — every one of them was a rule that had been
*narrowed* rather than repaired:

* the key-shape matcher was upgraded for paths and left alone for bodies, so
  one underscore of adjacent context (`<key>_odds.json` inside a string) hid a
  key from the body scan;
* the filename scan was placed behind the filter that drops binaries from the
  *body* scan, so a tracked `docs/<32-hex>.png` was read by nothing;
* the assignment scan required `=` to touch the name, so
  `os.environ["NAME"] = "<key>"` — the canonical Python spelling — was not a
  finding in a `.py`, a `.md` or a `.yml`.

A fourth round found seven more, and two of them had no punctuation to
grep for at all:

* the two spacing classes and the value capture disagreed about what a blank
  is — `[ \\t]*` is ASCII, `\\S` is Unicode-aware, and one U+00A0 fell in the
  gap between them, so `export NAME=<U+00A0><key>` opened no match anywhere;
* a tracked symlink's target was read by nothing: `path.is_file()` is False
  for a dangling link so the body scan dropped it, and the name scan saw only
  the link's own name;
* `_CLOSERS` enumerated six punctuation characters, so `**NAME**: <key>` and
  `<code>NAME</code>: <key>` — Markdown and HTML emphasis — sat between the
  name and the operator and stopped the match;
* the operator was the single character `=`, so `:=`, `?=` and `+=` were not
  assignments;
* `API_KEY_PARAM` could not match a value containing `-`, which is the shape
  of the example key this very module uses;
* only the first token after the operator was read, and an empty first token
  abandoned the whole line — so `NAME = "" "<key>"` and a three-column table
  row both passed;
* and `_collect_event_ids` harvested exemptions from `data/outputs/`, which
  is inside `EXEMPT_SCOPE`, so a file could create the exemption it spends.

Every hole here is pinned by a test that fails against the module as it was
before the fix. That is a weaker claim than "fails if you revert one line",
and it is the true one: several of these rules overlap, so reverting just one
of them can leave the test passing. The U+00A0 case is the worked example —
`test_a_unicode_blank_does_not_open_a_gap_between_the_classes` names which
reversion re-opens it and which does not, because it was run both ways.

The rewordings that still get past this module are listed in
`test_the_gaps_this_guard_still_has_are_the_ones_written_down` rather than
left to be rediscovered. That ledger is the honest half of this file: where a
gap could not be closed cheaply it is written down there rather than papered
over in a docstring here. When you change a rule in here, attack the new rule
with three spellings of the same leak before believing it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import pytest

from ncaaf_betting_lab.config import PROJECT_ROOT
from ncaaf_betting_lab.providers.env_file import ENV_FILENAME, PROVIDER_ENV_ALLOWLIST


#: Obvious placeholders that must never be mistaken for a real credential.
#:
#: This is the whole allowance documentation gets. There used to be a second,
#: much wider one — any `.md`, `.rst` or `.txt` value that was not 32 hex
#: characters was skipped outright. That skip was a *second, independent*
#: route by which a live provider key could sit in a tracked Markdown file:
#: it waved through every value shape but one, so even a credential name this
#: module already knew could be assigned a real key in prose and pass. It is
#: not how the `NCAAF_ODDS_API_KEY` leak actually passed — that one passed
#: because the assignment scan was keyed to `PROVIDER_ENV_ALLOWLIST` and did
#: not know the name at all, so no suffix rule was ever consulted. Both routes
#: are closed and each is pinned separately; do not read either fix as having
#: shut the other. A real key is rarely 32 hex characters; most providers
#: issue something else entirely. Prose that wants
#: to show the form of the command writes a placeholder from this set or a
#: reference (`$VAR`, `<your-key>`, `${{ secrets.X }}`), both of which stay
#: allowed everywhere.
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
#:
#: The fence is a pair of lookarounds and not `\b`, and there is now exactly
#: one matcher rather than a body one and a path one. `\b` will not open
#: beside `_`, because `_` is a word character — and the provider cache names
#: its files `<event id>_odds.json`, the convention an attacker would copy. A
#: previous round upgraded only the *path* scan to these lookarounds and left
#: `\b[0-9a-f]{32}\b` scanning bodies, so one underscore of adjacent context
#: (`CACHE = f"<key>_odds.json"`, `KEY_<key> = 1`) hid a real credential in a
#: tracked file with the suite green. Two spellings of the same shape is how
#: that happens; keeping one is the fix.
#:
#: The lookarounds are what the word boundaries were reaching for: they still
#: refuse to fire inside a longer hex run, so a SHA-256 — in a name or in a
#: body — is not a finding. `test_the_key_shape_matcher_is_not_stopped_by_a_
#: word_character` pins both halves, over a path and over a body.
#:
#: `A-F` as well as `a-f` because the provider issues lowercase and an
#: uppercased copy of a key is the same key. While the class was lowercase
#: only, `KEY = "<the key, uppercased>"` was invisible — found by attacking
#: this matcher rather than by reading it. Admitting the uppercase half adds
#: no offender to the tracked corpus, and 32 characters drawn only from
#: `[0-9a-fA-F]` is not a word of English in any case.
HEX_KEY = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")

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
#: The evidence has to be the response *body*, never the filename. An earlier
#: version unioned filename stems into the exemption set as a "second,
#: independent record", and that did let a key through: committing an
#: otherwise empty `data/processed/<key>_odds.json` next to a hardcoded key
#: exempted that key everywhere, without touching this guard at all. A body is
#: written by the provider; a filename is chosen by whoever adds the file.
#:
#: A filename is now checked twice over, because the stem-versus-body rule
#: alone turned out to check nothing: `_collect_event_ids` only reads stems
#: under `data/raw/`, which `.gitignore` makes untrackable, so on the real
#: repository it compares two empty sets forever. The load-bearing check is
#: that `_hex_key_offenders` scans the path itself, so an uncorroborated stem
#: is a finding directly, wherever the file sits.
_EVENT_ID_KEYS = ("id", "event_id")

#: Where a recorded event id may be *spent*.
#:
#: Collecting the exemption by value fixed which literals are allowed and left
#: open where they are allowed, and the answer was "the whole tree". Since
#: `.gitignore` makes `data/raw/` untrackable, the entire live exemption
#: surface on a tracked-file scan is `data/outputs/` — reports this repository
#: writes, not the provider — so one hand-committed JSON there whose body
#: carried `{"id": "<a key>"}` turned that same key green in `scripts/`.
#: Nothing outside the provider cache and the reports rendered from it has an
#: innocent reason to carry a provider event id, so nothing outside them gets
#: to spend one. The reproduction is run as a test:
#: `test_a_recorded_event_id_is_not_spendable_outside_the_data_directories`.
#:
#: This is a **spend** rule and only a spend rule. It used to be both, and that
#: made the exemption self-nominating: `_collect_event_ids` harvested ids from
#: any `.json` under this scope, `data/outputs/` is tracked and is inside it,
#: so a hand-committed `data/outputs/x.json` whose body was `{"id": "<a key>"}`
#: created the very exemption it then spent — and turned that key green for its
#: siblings too. A report this repository *writes* may spend an exemption; only
#: the provider's own cache under `data/raw/` may create one, which is the gate
#: `_collect_event_ids` now applies. Pinned by
#: `test_a_report_this_repository_writes_cannot_nominate_an_exemption`.
EXEMPT_SCOPE = ("data/raw/", "data/outputs/")

#: A 32-hex digest — a truncated hash, a manifest checksum — is not an event
#: id but is legitimately hex. It is exempted the same way: by recorded value,
#: each literal carrying a comment naming the file it was read from so the
#: exemption can be re-checked against that file. Empty because no tracked
#: file needs one yet.
#:
#: Note that it is spent under the same `EXEMPT_SCOPE` rule as an event id, so
#: a digest recorded outside those two directories has no exemption route at
#: all today. That is deliberate and it is not free: if one is ever needed in,
#: say, `docs/receipts/`, widen this deliberately rather than reaching for the
#: by-name skip described below, which is what was there before.
#:
#: What this replaces skipped any file whose name contained "checksum" or
#: "receipt". That exempted every 32-hex run in such a file, a real key
#: included, and it aimed the blind spot squarely at acceptance receipts — the
#: artifacts whose whole job is to record provenance.
RECORDED_DIGESTS: frozenset[str] = frozenset()

#: The GitHub secret holding this lab's provider credential. The **name**
#: belongs in the repository — it is a contract string, recorded in CLAUDE.md's
#: contract table and pinned by `ODDS_API_SECRET` in
#: `tests/test_contract_strings.py`. The **value** never does.
#:
#: It has to be named here because it is not in `PROVIDER_ENV_ALLOWLIST`: the
#: provider code still reads `FOOTBALL_ODDS_API_KEY`, inherited from the port,
#: and mapping the secret onto it is a job for a gameday workflow that does not
#: exist yet. Keying the assignment scan to the allowlist alone therefore left
#: this module unable to recognise the very name on the credential Cooper
#: actually holds — a name it would have gone on not recognising right up to
#: the first run that used it.
GITHUB_SECRET_NAME = "NCAAF_ODDS_API_KEY"

#: Every credential-ish variable name a tracked file may mention but never
#: assign. `test_no_credential_name_in_the_repository_is_unknown_to_this_guard`
#: fails the build if a name appears in the tree that is missing from here.
CREDENTIAL_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys((*PROVIDER_ENV_ALLOWLIST, GITHUB_SECRET_NAME))
)

#: The shape of a credential variable name, used to find names this guard has
#: not been taught. Matching the token itself, not a punctuation mark of it.
#:
#: The suffix alternation is not decoration. `_API_KEY` alone recognised
#: exactly one spelling, so a credential named `..._APIKEY` or `..._API_TOKEN`
#: was invisible to both the drift guard below and the assignment scan — a
#: future rename would have silently un-armed two tests at once. Widening it
#: adds no name to the tracked corpus beyond the two already known, so it
#: costs nothing today and closes a rename-shaped hole tomorrow.
CREDENTIAL_NAME_SHAPE = re.compile(
    r"\b[A-Z][A-Z0-9_]*_(?:API_KEY|APIKEY|API_TOKEN)\b"
)


def _collect_event_ids(
    paths: Iterable[Path], root: Path
) -> tuple[set[str], set[str]]:
    """Split recorded event ids by how strong the evidence for them is.

    `content_ids` come out of a response body or a table cell — the provider
    put them there, so they are a record. `name_ids` come off a filename,
    which anyone can choose, so they are a claim. Only `content_ids` is ever
    allowed to exempt a hex run; `name_ids` exists to be checked against it.
    """
    content_ids: set[str] = set()
    name_ids: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _EVENT_ID_KEYS and isinstance(value, str):
                    if HEX_KEY.fullmatch(value):
                        content_ids.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in paths:
        relative = path.relative_to(root).as_posix()
        if relative.startswith("data/raw/"):
            # Only the cached-response directory names files after the event
            # they hold. Harvesting stems repo-wide let any file anywhere
            # nominate an exemption.
            stem = path.name.split("_")[0]
            if HEX_KEY.fullmatch(stem):
                name_ids.add(stem)
        if not relative.startswith("data/raw/"):
            # Creating an exemption is the provider cache's privilege alone.
            # `EXEMPT_SCOPE` says where one may be *spent*; using it here too
            # let `data/outputs/` — tracked, and written by this repository —
            # nominate the literal it wanted exempted.
            #
            # State the cost plainly: `.gitignore` makes `data/raw/`
            # untrackable, so on this repository today nothing can nominate
            # anything and the live exemption set is empty. That is the
            # fail-closed direction — every 32-hex run in a tracked file is a
            # finding — and the day a report legitimately needs to carry an
            # event id, the fix is to record the literal in
            # `RECORDED_DIGESTS` with the file it came from, not to widen
            # this back to `EXEMPT_SCOPE`.
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
                        content_ids.add(cells[index].strip())
    return content_ids, name_ids


def _exempt_hex_values() -> set[str]:
    """Every 32-hex literal this repository has a recorded reason to allow.

    Which literals, not where they may appear: `_hex_key_offenders` decides
    that, and only lets them be spent under `EXEMPT_SCOPE`.
    """
    content_ids, _ = _collect_event_ids(_tracked_files(), PROJECT_ROOT)
    return content_ids | set(RECORDED_DIGESTS)

#: `apiKey=` FOLLOWED BY A VALUE is a leak. The bare token is not: it appears
#: legitimately in the redaction regex that strips credentials and in tests
#: asserting the token is absent. Flagging the bare token would force those
#: defences to be written obscurely, or exempted — both worse than matching
#: precisely. Eight characters is well below any real key length.
#:
#: The spelling is a family, not a literal. `apiKey` is what The Odds API
#: names the parameter today; `apikey`, `api_key` and `api-key` are what the
#: next provider will name it, and a matcher that knows one casing is a
#: matcher that goes quiet on a rename. Admitting the family adds no offender
#: to the tracked corpus. What is still matched is the *capability* — a
#: parameter that hands a key to a URL — followed by something long enough to
#: be one, so the bare token in a redaction regex stays clean.
#:
#: The value class is `[A-Za-z0-9][A-Za-z0-9_-]{7,}` and not `[A-Za-z0-9]{8,}`,
#: because the narrower one could not match the example key this module uses
#: everywhere: `apiKey=sk-live-4f19c0d27ba6e83d` was a NOMATCH, probed and
#: confirmed, while `apiKey=0123456789abcdef` matched — and the all-alphanumeric
#: shape was the only one the test exercised. A matcher that fires on its own
#: worked example and not on the leak it is named after is a matcher that reads
#: as armed. The first character stays alphanumeric so `apiKey=[redacted]` and
#: `apiKey=)` — the redaction regex and the assertions that mention the token —
#: are still non-matches; each is asserted below.
API_KEY_PARAM = re.compile(
    r"api[_-]?key=[A-Za-z0-9][A-Za-z0-9_-]{7,}", re.IGNORECASE
)

#: Punctuation that may sit between a credential name and the operator that
#: gives it a value: the closing half of a quote, a subscript or a code span.
#: `os.environ["NAME"] = "..."`, `` `NAME` = ... ``, `{"NAME": "..."}`.
#:
#: Space and tab are in the class, not just after it. `os.environ[ "NAME" ] =`
#: defeated the first draft of this fix — the closers ran out at the space
#: before `]` — which is the whole reason the rewording test exists. Newline
#: is deliberately still excluded, so `NAME` on one line and `=` on the next
#: is not an assignment; that is what keeps `.env.example` green.
#:
#: It used to enumerate six characters, and an enumeration is a spelling. An
#: emphasis marker is not one of the six, so `**NAME**: <key>`, `*NAME*: <key>`
#: and `_NAME_: <key>` — Markdown, which is most of this repository's prose —
#: all opened no match, and neither did the HTML `<code>NAME</code>: <key>`.
#: So the rule is now a shape: an HTML tag, or any character that is neither
#: alphanumeric, nor a newline, nor one of the operators this module reads
#: back. Bounded at eight so it cannot run away across a line.
#:
#: `_` is admitted deliberately even though it is a word character, because
#: `_NAME_` is the Markdown emphasis spelling. It costs nothing: a longer
#: identifier like `NAME_FILE:` still does not match, since the closers stop
#: dead at the alphanumeric that follows the underscore.
#:
#: The tag alternative carries attributes because `<code>` and
#: `<span class="x">` are one capability and two spellings; the attribute run
#: is bounded and must still close on `>`, so it cannot walk off the tag.
_CLOSERS = r"(?:</?[A-Za-z][A-Za-z0-9]*[^<>\n]{0,64}>|[^0-9A-Za-z\n=:,|]){0,8}"

#: A horizontal blank, agreeing with `\S` about what a blank is.
#:
#: This is the highest-severity thing this round found, and it had no
#: punctuation to grep for. The spacing was `[ \t]*` — ASCII only — and the
#: value was captured with `(?=(\S+))`, which is Unicode-aware. A U+00A0 after
#: the operator therefore fell in the gap *between* the two: the spacing class
#: would not consume it and `\S` would not start on it, so the match never
#:
#: The name is written as `<the secret's name>` rather than spelled out
#: because tests/test_contract_strings.py reads the three characters after
#: that literal and fails on an `=`. Prose demonstrating an assignment is
#: indistinguishable from the assignment itself to a scanner, which is the
#: guard behaving correctly — so the example is written around it.
#: opened at all and `export <the secret's name>=<U+00A0>sk-live-…` in a tracked
#: `.md` gave a fully green suite. `[^\S\r\n]*` is every character `\S`
#: refuses, minus the line breaks — so the two classes now partition the input
#: between them and there is no gap to fall into. Newline stays excluded for
#: the reason below: it is what keeps `.env.example`'s bare `NAME=` green.
#:
#: U+200B is *not* whitespace in Unicode, so `\S` does start on it and it is
#: read as part of the value rather than as spacing; `_unwrap` deletes it by
#: category. See `test_a_unicode_blank_does_not_open_a_gap_between_the_classes`.
#:
#: Say what this class is worth now, rather than letting it read as the sole
#: barrier. Measured by reverting one rule at a time: with the rest of the line
#: captured through `_REST_OF_LINE` and split on `str.split()` — which is
#: Unicode-aware — a blank *after* the operator is absorbed whatever this class
#: says, and a blank *before* it is absorbed by `_CLOSERS`, which now admits
#: any non-alphanumeric. So reverting this class alone no longer re-opens the
#: hole; reverting the value capture to `(?=(\S+))` does, with this class or
#: without it. This is redundancy, and it is kept as redundancy: it costs
#: nothing, and it is the rule that stays correct if either of the other two is
#: ever narrowed back.
_BLANK = r"[^\S\r\n]*"

#: How much of the line after the operator is handed to the value tests.
#:
#: A zero-width lookahead, for the reason `ASSIGNMENT` gives, and bounded, for
#: a reason that only shows up under measurement: with `(?=(.*))` each match
#: copies and splits the entire remainder of the line, so one line carrying the
#: credential name two thousand times ran in seconds rather than milliseconds.
#: `.` still refuses to cross a newline, so the line boundary is unchanged.
_REST_OF_LINE = r"(?=(.{0,512}))"

#: The names, alternated once, for every scanner that keys on one.
_NAMES = "|".join(re.escape(name) for name in CREDENTIAL_NAMES)

#: `NAME=value` where NAME is a credential variable and value is not a
#: placeholder — i.e. a real assignment, not documentation.
#:
#: The spacing is `_BLANK` rather than `\s*` deliberately. `\s` crosses a
#: newline, so `NAME=` on one line and any word on the next read as an
#: assignment — which is exactly what `.env.example` looks like, and it made
#: the guard fail on a file whose values are all empty. It is not `[ \t]*`
#: either; see `_BLANK` for the U+00A0 that fell between that class and `\S`.
#:
#: The operator is a family, `[:?+]?=`, and not the single character `=`.
#: `NAME := <key>` (Make, and Go's short declaration), `NAME ?= <key>` (Make's
#: conditional) and `NAME += <key>` are assignments a machine reads back, and
#: all three were missed by both families — `=` did not touch the name and the
#: leading `:`/`?`/`+` was not a closer either. One new intentional catch comes
#: with it: shell's `${NAME:=literal}`, which assigns the literal into the
#: environment if the variable is unset, is now a finding. That is the right
#: answer — it is an assignment of a literal — and it is stated here because it
#: is a behaviour change, not a side effect. `${NAME:-literal}` is unchanged
#: and is still reached by `SEPARATED`.
#:
#: `_CLOSERS` is why this now catches the canonical Python spelling. Requiring
#: `=` to touch the name meant `os.environ["NCAAF_ODDS_API_KEY"] = "sk-live-…"`
#: was not a finding at all — a closing quote and bracket sit between — and a
#: live key written that way passed a fully green suite, in a `.py` and in a
#: `.md`. The sibling check in `tests/test_contract_strings.py` missed it for
#: the same reason from the other side: it inspects the three characters after
#: the name, which there are `"] `, and finds no `=`.
#:
#: The value is captured through a lookahead so the match itself ends at the
#: operator. Consuming the value would swallow a nested occurrence: in
#: `NAME: ${NAME:-<key>}` the outer match would eat the inner one, and the
#: outer value begins with `$` so it is dismissed as a reference — the leak
#: would sit inside a span already scanned and dismissed.
#: `re.IGNORECASE` because a credential written under a lowercased spelling of
#: the name is the same credential. Nothing in the tracked corpus changes when
#: the case is relaxed, and the *value* is the thing being protected — the
#: name is only the handle this scanner grabs it by.
#:
#: The rest of the line is captured, not the first token. `(?=(\S+))`
#: read exactly one token and `if not value: continue` then abandoned the line
#: when that token unwrapped to nothing — so `os.environ["NAME"] = "" "<key>"`,
#: a real Python assignment, was dismissed on its empty first token, and a
#: three-column Markdown table row hid the key in its third cell.
#: `_REST_OF_LINE` keeps the match zero-width at the operator (the reason for
#: the lookahead is unchanged) and hands every token on the rest of it to
#: `_assignment_offenders`, which advances past an empty one instead of giving
#: up. `.` does not cross a newline, so the line boundary still holds.
#:
#: `_REST_OF_LINE` is bounded, and the bound is load-bearing rather than
#: cosmetic. Unbounded, every match copies and splits the whole remainder, so
#: a single line carrying the credential name many times costs O(n²): timed on
#: one line holding two thousand `NAME: <value>` pairs, it ran in seconds
#: rather than in milliseconds, and a minified or generated file could
#: plausibly contain such a line. A guard slow enough to look hung is a guard
#: someone switches off. The cost of the bound is written into the known-gaps
#: ledger, not hidden here.
#:
#: The fence is `(?<![A-Za-z0-9])` and not `\b`. `\b` will not open between
#: `_` and a letter, so the emphasis spelling `_NAME_` was unreachable however
#: wide `_CLOSERS` got.
ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9])("
    + _NAMES
    + r")"
    + _CLOSERS
    + _BLANK
    + r"[:?+]?="
    + _BLANK
    + _REST_OF_LINE,
    re.IGNORECASE,
)

#: The same idea for the separators `=` cannot cover: YAML's `NAME: value`,
#: the comma of `setdefault("NAME", value)` / `{"NAME": value}`, and the pipe
#: of a Markdown table row — this repository documents its credential in a
#: table, so `| NAME | <value> |` is a leak surface it actually has.
#:
#: These could not simply be folded into `ASSIGNMENT` as `[:=,|]`, because
#: each of them also separates a name from ordinary prose —
#: "`NCAAF_ODDS_API_KEY`: the name of the GitHub secret", a list of two names
#: side by side, and that very table row, whose cell begins "The name of the
#: GitHub secret". So the separator is widened *and* the value must
#: independently look like a value. `=` needs no such test on its **first**
#: token and does not get one: nothing writes `NAME=` in prose, and demanding a
#: value shape there would narrow a scan that already works. Every token after
#: the first faces this test under either separator, which is what stops the
#: sentence following `export NAME=<placeholder>` from being reported.
#:
#: Same three repairs as `ASSIGNMENT`: the Unicode-aware blank class, the
#: `(?<![A-Za-z0-9])` fence, and the whole rest of the line rather than its
#: first token. The last one matters most here, because the shape it missed is
#: the shape this repository actually writes — `| `NAME` | live | <key> |`, a
#: table row with the value in its third cell, sailed past a guard that read
#: only `live`. Every token on the rest of the line now faces the value test.
SEPARATED = re.compile(
    r"(?<![A-Za-z0-9])("
    + _NAMES
    + r")"
    + _CLOSERS
    + _BLANK
    + r"[:,|]"
    + _BLANK
    + _REST_OF_LINE,
    re.IGNORECASE,
)

#: Does this token look like a credential *value* rather than a word of prose?
#:
#: A secret is one unbroken run of name-safe characters, long, containing at
#: least one digit, and is not itself an identifier in shouting case. Each
#: clause pays for itself against real prose in this repository: the length
#: rejects "the", "required", "see"; the character class rejects a path or a
#: filename ("docs/runbook-2024.md" carries `/` and `.`); the digit rejects
#: "not-configured" and "documentation"; the shouting-case clause rejects a
#: bare list of credential *names*, which is what `CREDENTIAL_NAMES =
#: frozenset({"NCAAF_ODDS_API_KEY", "FOOTBALL_ODDS_API_KEY"})` in
#: `tests/test_workflows.py` looks like to a comma scanner.
#:
#: Two gaps this leaves, stated rather than hidden. They bite the `:`/`,`/`|`
#: family on every token, and the `=` family on every token *after the first*
#: — that is the honest width of it. The `=` family's first token runs no
#: value test at all and so has neither gap; its later tokens are read with
#: this test, because without it the sentence after `export NAME=<placeholder>`
#: would be a finding. Do not read the older, wider claim that "the `=` family
#: has no value test" anywhere: it stopped being true when both patterns began
#: reading the whole rest of the line.
#:
#: * A value of letters only (`NAME: purelettersecret`) is not a finding here.
#:   Dropping the digit clause flags ordinary English words instead, and a
#:   provider key with no digit in it is a shape no provider issues.
#: * A value carrying `.` or `/` (`NAME: ab12.cd34.ef56`) is not a finding
#:   here. Admitting those characters flags every documentation path.
#:
#: Both are pinned by `test_the_value_test_gaps_are_the_ones_documented`, so
#: they fail loudly the day someone narrows or widens this by accident.
CREDENTIAL_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{11,}")

#: An identifier in shouting case is a *name*, never a value.
SHOUTING_CASE = re.compile(r"[A-Z0-9_]+")

#: Unicode categories that occupy no space and belong to no credential.
#:
#: `_BLANK` handles the invisible characters Unicode calls whitespace; these
#: are the ones it does not — U+200B, U+00AD, U+FEFF and the rest of the
#: format and control marks. `\S` starts on every one of them, so they ride
#: *into* the captured token instead of being consumed as spacing, and one on
#: the front of a value was enough to make it fail `CREDENTIAL_VALUE` under
#: `:`/`,`/`|`. `_unwrap` deletes them.
#:
#: It is a category test and not a list of codepoints on purpose: a list is a
#: spelling, and the first spelling anyone tried that was not on it — U+00AD —
#: got through. `Cf` and `Cc` are what "formatting mark with no width" and
#: "control character" mean, so the rule denies the capability instead.
INVISIBLE_CATEGORIES = frozenset({"Cf", "Cc"})


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


#: Suffixes whose *bodies* there is no point decoding. This is a statement
#: about bodies only. A file with one of these suffixes still has a name, and
#: a name needs no decoding — see `_hex_offenders_for_corpus`.
BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip"}
)


def _link_target(path: Path) -> str:
    """What a tracked symlink actually carries, which is neither name nor body.

    `git` stores a symlink as a blob whose contents are the target string, so
    `ln -s sk-live-… docs/provider_key` commits the credential in plaintext and
    every scan here used to miss it. The body scan dropped the path on
    `path.is_file()`, which is False for a dangling link; the name scan read
    `docs/provider_key` and found nothing in it. The target needs no decoding —
    it is a string in the index, exactly like a path — so it is scanned wherever
    a name is.

    Returns `""` for anything that is not a symlink, and for a link that cannot
    be read, so callers can concatenate it unconditionally.
    """
    try:
        if not path.is_symlink():
            return ""
        return os.readlink(path)
    except OSError:
        return ""


def _is_this_file(path: Path) -> bool:
    """`path` is this module, resolving symlinks — and never raises.

    `Path.resolve()` raises `RuntimeError` on a symlink loop, and admitting
    symlinks to this corpus put a loop in front of it: a committed
    `ln -s loop loop` turned the whole guard into a crash rather than a
    finding. A path that cannot be resolved is *not* this file, so it stays in
    the corpus and gets scanned. Absence of an answer is never an exemption.
    """
    try:
        return path.resolve() == SELF
    except (OSError, RuntimeError):
        return False


def _body_scannable(paths: Iterable[Path]) -> list[Path]:
    """The subset of `paths` whose contents are worth reading as text.

    A symlink is kept even when it dangles. Its body reads as empty — `_read`
    returns `""` on the `OSError` — but keeping it is what carries the path
    into `_assignment_offenders`, which scans the link target as well as the
    body. Dropping it on `is_file()` is what hid `ln -s "NAME=<key>" note`.
    """
    keep: list[Path] = []
    for path in paths:
        if not path.is_file() and not path.is_symlink():
            continue
        if _is_this_file(path):
            continue
        if path.suffix in BINARY_SUFFIXES:
            continue
        keep.append(path)
    return keep


def _text_files() -> list[Path]:
    return _body_scannable(_tracked_files())


def _read(path: Path) -> str:
    """The file as text, plus a NUL-stripped reading when there are NULs.

    A UTF-16 file decodes under `errors="ignore"` into `K\\x00E\\x00Y…`, and
    every matcher in this module wants an unbroken run — so a key written into
    a UTF-16 `.txt` was invisible to all of them. Found by writing the file and
    scanning it, not by reasoning about codecs. Removing the NULs recovers the
    ASCII, and appending rather than replacing means the ordinary reading is
    still scanned exactly as before. No tracked text file contains a NUL, so
    the second reading costs nothing today and closes an encoding-shaped hole.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if "\x00" in text:
        return text + "\n" + text.replace("\x00", "")
    return text


def _hex_key_offenders(
    paths: Iterable[Path],
    allowed: set[str],
    root: Path,
    *,
    names: bool = True,
    bodies: bool = True,
) -> list[str]:
    """Every 32-hex run in `paths` — name or body — that is not accounted for.

    Taking the corpus as an argument is what lets the regression tests below
    run this exact code over a synthetic file instead of asserting about it
    from a distance. Only six characters of a finding are reported: enough to
    locate it, not enough to publish it.

    Three rules that were each learned from a leak:

    * The path is scanned as well as the body. A key written into a filename
      used to be read by nothing at all, since the only code that looked at
      names was scoped to the untrackable `data/raw/`.
    * A symlink's target is scanned as a third string beside the two, under
      the `names` flag because it needs no decoding either. `ln -s <32-hex>
      docs/provider_key` committed the key in the index and was read by
      neither of the other two scans — see `_link_target`.
    * Both scans use the same `HEX_KEY`. They used to use different matchers
      and the body one could not see a key with an `_` beside it.
    * `allowed` is spendable only under `EXEMPT_SCOPE`, for a name exactly as
      for a body. An event id recorded in a report does not excuse the same
      hex run in `scripts/`.

    `names` and `bodies` exist because the two scans want different corpora,
    not different rules: a body has to be decodable text, a filename does not.
    `test_no_tracked_file_contains_an_odds_api_key_shape` is the caller that
    splits them, and `test_a_hex_run_in_the_name_of_a_binary_is_a_finding`
    pins why. Both default to on so no caller can drop a scan by omission.
    """
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        permitted = allowed if relative.startswith(EXEMPT_SCOPE) else set()
        found: list[str] = []
        if names:
            found += [match.group(0) for match in HEX_KEY.finditer(relative)]
            found += [
                match.group(0)
                for match in HEX_KEY.finditer(_link_target(path))
            ]
        if bodies:
            found += [match.group(0) for match in HEX_KEY.finditer(_read(path))]
        for value in found:
            if value in permitted:
                continue
            offenders.append(f"{relative}: {value[:6]}...")
    return offenders


def _unwrap(raw: str) -> str:
    """Strip the punctuation that surrounds a value in source and prose.

    Quotes, then trailing commas/semicolons and the closing halves of a call,
    dict or list, then quotes again — `"sk-live-x"})` and `"sk-live-x")` and
    `sk-live-x,` all come out as the value. The leading `-` of a shell default
    goes too, so `${NAME:-<key>}` is read as the assignment it is; a `-` on
    the front of a real credential is not a shape any provider issues, and
    keeping it would leave `${NAME:-<key>}` un-scanned.

    A string-literal prefix goes first, because `f"{SECRET}"` is quoting, not
    value: without this the `f` survives the quote strip, the `{` that marks
    an interpolation is no longer the first character, and an ordinary
    f-string interpolation of a secret reads as a hardcoded credential. That
    was a false positive this round's widening introduced and this line
    removes — the module's comment had claimed `{SECRET}` was handled, and it
    was only handled for spellings with no prefix.

    Invisible characters go first of all. U+200B, U+00AD and the rest of the
    `Cf`/`Cc` categories are the half of the invisible-blank attack `_BLANK`
    cannot reach: Unicode does not call them whitespace, so `\\S` starts on
    them and they arrive inside the token rather than beside it. For the `=`
    family that is already a finding, but under `:`/`,`/`|` one of them glued
    to the front of a real key made `CREDENTIAL_VALUE` refuse it. Nothing
    invisible is part of any credential a provider issues, so they are removed
    by category — see `INVISIBLE_CATEGORIES` for why not by codepoint list.
    """
    visible = "".join(
        character
        for character in raw
        if unicodedata.category(character) not in INVISIBLE_CATEGORIES
    )
    without_prefix = re.sub(r"^[fFrRbBuU]{1,2}(?=[\"'])", "", visible)
    return without_prefix.strip("'\"`").strip(",;)}]").strip("'\"`").lstrip("-")


def _is_a_reference(value: str) -> bool:
    """`$VAR`, `<placeholder>`, `${{ secrets.X }}`, an f-string `{SECRET}`.

    All of these name a value rather than being one. `$` is unconditional: a
    `$`-prefixed token is a shell or CI expansion whatever follows it.

    The bracket forms are *not* unconditional, and they used to be. Anything
    beginning `<` or `{` was waved through, so `NAME: <sk-live-…>` — the leak
    wearing the placeholder's clothes — was not a finding. Written and run,
    not reasoned about. Now the brackets are stripped and what is inside has
    to fail the value test, which `<your-key>`, `<paste yours>` and `{SECRET}`
    all do and a real credential does not.

    The cost is a placeholder that is itself value-shaped —
    `<your-api-key-2024>` would be a finding. That is the trade taken
    deliberately: a false positive is a build someone looks at, and the
    alternative is a bypass anybody who reads this file can use.
    """
    if value[0] == "$":
        return True
    if value[0] in "<{":
        return not _looks_like_a_credential_value(_unbracket(value))
    return False


def _unbracket(value: str) -> str:
    """`<sk-live-…>` and `{sk-live-…}` down to the value they wrap.

    Used on both sides of the reference question, and that symmetry is the
    point: the first draft of the bracket fix stripped them in
    `_is_a_reference` only, so `NAME: <sk-live-…>` stopped being a reference
    and then failed the value test on the `<` it still carried — through the
    guard by a different door. Found by re-running the same attack after the
    fix, which is the only reason it is not still open.
    """
    return value.strip("<>{} ")


def _looks_like_a_credential_value(value: str) -> bool:
    """The value test the `:` and `,` separators need and `=` does not.

    See `CREDENTIAL_VALUE` for each clause and for the two gaps it leaves.
    """
    if not CREDENTIAL_VALUE.fullmatch(value):
        return False
    if SHOUTING_CASE.fullmatch(value):
        return False
    return any(character.isdigit() for character in value)


def _hex_offenders_for_corpus(
    tracked: Iterable[Path], allowed: set[str], root: Path
) -> list[str]:
    """The whole hex scan for a corpus: names over all of it, bodies over the
    part that has one worth reading.

    This split is the fix for a scan that a `.png` suffix could walk past
    entirely. It is a function rather than two lines inside the repository
    test so that `test_a_hex_run_in_the_name_of_a_binary_is_a_finding` can run
    the real thing over a synthetic corpus containing a real binary, instead
    of asserting about `_text_files()` from a distance.
    """
    paths = list(tracked)
    offenders = _hex_key_offenders(paths, allowed, root, bodies=False)
    offenders += _hex_key_offenders(
        _body_scannable(paths), allowed, root, names=False
    )
    return offenders


def _assignment_offenders(paths: Iterable[Path], root: Path) -> list[str]:
    """Every `CREDENTIAL_NAME <given> <real value>` in `paths`, by file and name.

    Corpus-as-argument for the same reason as `_hex_key_offenders`: the
    regression test for a key committed in Markdown runs this code rather than
    describing it. The value itself is never reported.

    Two families, because they need different evidence. `=` is an assignment
    wherever it appears, so any value that is neither a placeholder nor a
    reference is a finding. `:` and `,` also occur in prose, so a match there
    is a finding only if the value independently looks like a credential.

    Both patterns capture the **rest of the line**, and every whitespace-
    separated token on it is evaluated. Reading only the first token, and
    abandoning the whole line when it unwrapped to nothing, is what let
    `os.environ["NAME"] = "" "<key>"` — a functioning Python assignment — and
    the third cell of a Markdown table row both pass. An empty token now
    *advances*; it never ends the line. For the `=` family the first non-empty
    token keeps the old rule (no value test, because nothing writes `NAME=` in
    prose) and every later token has to look like a credential value before it
    is reported, which is what keeps the sentence after `export NAME=<x>` from
    becoming a finding.

    The symlink target is appended to the text, for the reason in
    `_link_target`: `ln -s 'NAME=<key>' docs/note` writes the assignment into
    the git index and into no file body at all.
    """
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        text = _read(path)
        target = _link_target(path)
        if target:
            text = f"{text}\n{target}"
        for pattern, value_must_look_real in ((ASSIGNMENT, False), (SEPARATED, True)):
            for match in pattern.finditer(text):
                tokens = [
                    unwrapped
                    for unwrapped in (
                        _unwrap(token) for token in match.group(2).split()
                    )
                    if unwrapped
                ]
                for index, value in enumerate(tokens):
                    must_look_real = value_must_look_real or index > 0
                    if value in PLACEHOLDERS:
                        continue
                    if _is_a_reference(value):
                        continue
                    if must_look_real and not _looks_like_a_credential_value(
                        _unbracket(value)
                    ):
                        continue
                    finding = f"{relative}: {match.group(1)}"
                    if finding not in offenders:
                        offenders.append(finding)
                    break
    return offenders


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
    """`<a credential name>=<something real>` must not appear in a tracked file.

    Every tracked text file, every name in `CREDENTIAL_NAMES`, every suffix.
    Markdown is not a safer place to write a key than Python is.
    """
    offenders = _assignment_offenders(_text_files(), PROJECT_ROOT)

    assert offenders == [], f"credential assignment in tracked files: {offenders}"


def test_no_credential_name_in_the_repository_is_unknown_to_this_guard() -> None:
    """A credential name this module has not been taught is a name it cannot
    catch being assigned.

    That is not hypothetical — it is how a real key assigned to
    `NCAAF_ODDS_API_KEY` survived in a tracked Markdown file: the scan was
    keyed to
    `PROVIDER_ENV_ALLOWLIST`, which holds the *inherited* `FOOTBALL_...` name
    and not the one on Cooper's actual GitHub secret. Rather than trusting
    the list, go and find every credential-shaped name in the tree and demand
    the list covers it.
    """
    found: set[str] = set()
    for path in _text_files():
        found.update(CREDENTIAL_NAME_SHAPE.findall(_read(path)))

    # An empty scan would pass this vacuously, and absence is never a pass.
    assert found, "no credential name found in any tracked file — scan is broken"
    assert found <= set(CREDENTIAL_NAMES), (
        "credential names this guard cannot recognise being assigned: "
        f"{sorted(found - set(CREDENTIAL_NAMES))}"
    )


def test_a_credential_committed_in_markdown_is_a_finding(tmp_path: Path) -> None:
    """Reproduction: a key in a `.md` file used to give a fully green suite.

    Two independent reasons it did, and this pins both. The name
    `NCAAF_ODDS_API_KEY` was unknown to the assignment scan, and documentation
    suffixes were skipped outright unless the value happened to be 32 hex
    characters — so even a name the scan *did* know could be assigned a live
    key in prose and pass. `sk-live-...` is neither hex nor 32 characters, and
    it is what a leaked key really looks like.
    """
    name = GITHUB_SECRET_NAME
    inherited = "FOOTBALL_ODDS_API_KEY"
    docs = tmp_path / "docs"
    docs.mkdir()
    leaked = docs / "runbook.md"
    leaked.write_text(
        f"Export the credential before the fetch:\n\n"
        f"    export {name}=" + "sk-live-4f19c0d27ba6e83d\n"
        f"    export {inherited}=" + "sk-live-4f19c0d27ba6e83d\n",
        encoding="utf-8",
    )

    assert _assignment_offenders([leaked], tmp_path) == [
        f"docs/runbook.md: {name}",
        f"docs/runbook.md: {inherited}",
    ]

    # ...and prose that shows the shape of the command still passes, because
    # placeholders and references are what documentation is supposed to use.
    fine = docs / "setup.md"
    fine.write_text(
        f"Run `export {name}=your-api-key`, or in CI set\n"
        f"`{name}=" + "${{ secrets." + name + " }}`, or locally\n"
        f"`{name}=$ODDS_KEY` / `{name}=<paste yours>`.\n",
        encoding="utf-8",
    )

    assert _assignment_offenders([fine], tmp_path) == []


def test_a_recorded_event_id_is_not_spendable_outside_the_data_directories(
    tmp_path: Path,
) -> None:
    """Reproduction: an exemption earned in the data directories used to be
    spent anywhere in the tree.

    The by-value rule fixed *which* literals are allowed and said nothing
    about *where*, so an id the provider genuinely recorded turned the same hex
    run green in `scripts/`, with the guard untouched. Note the exemption is
    genuinely earned: the collector does put the value in `content_ids`.
    Earning it is no longer enough.

    The nominating file sits in `data/raw/` because that is now the only
    directory permitted to *create* an exemption —
    `test_a_report_this_repository_writes_cannot_nominate_an_exemption` is why.
    `EXEMPT_SCOPE` is unchanged and is still both directories, which is what
    the `data/outputs/` report below demonstrates: it spends the exemption it
    did not earn, and that is allowed.
    """
    key = "0123456789abcdef0123456789abcdef"
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    cached = raw / f"{key}_odds.json"
    cached.write_text(
        json.dumps({"events": [{"id": key, "retained": None}]}), encoding="utf-8"
    )
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    report = outputs / "retention_probe.md"
    report.write_text(f"retention for {key}: unprobed\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    hardcoded = scripts / "fetch_odds.py"
    hardcoded.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")

    corpus = [cached, report, hardcoded]
    content_ids, _ = _collect_event_ids(corpus, tmp_path)

    assert content_ids == {key}
    assert _hex_key_offenders(corpus, content_ids, tmp_path) == [
        f"scripts/fetch_odds.py: {key[:6]}..."
    ]


def test_a_report_this_repository_writes_cannot_nominate_an_exemption(
    tmp_path: Path,
) -> None:
    """Reproduction: the event-id exemption was self-nominating.

    `_collect_event_ids` harvested `id`/`event_id` out of any `.json` under
    `EXEMPT_SCOPE`, and `EXEMPT_SCOPE` contains `data/outputs/` — which is
    tracked, and is written by this repository rather than by the provider. A
    file therefore sat inside its own spend scope and created the exemption it
    then spent. Measured on exactly the corpus below before the fix: zero
    offenders, for the nominating file *and* for its sibling, so a key could be
    laundered green by committing one small JSON beside it.

    A report this repository writes may **spend** an exemption; only the
    provider's own cache under `data/raw/` may **create** one.
    """
    key = "0123456789abcdef0123456789abcdef"
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    self_nominating = outputs / "retention_probe.json"
    self_nominating.write_text(json.dumps({"id": key}), encoding="utf-8")
    sibling = outputs / "notes.md"
    sibling.write_text(f"the value is {key}\n", encoding="utf-8")

    corpus = [self_nominating, sibling]
    content_ids, name_ids = _collect_event_ids(corpus, tmp_path)

    assert (content_ids, name_ids) == (set(), set())
    assert _hex_key_offenders(corpus, content_ids, tmp_path) == [
        f"data/outputs/retention_probe.json: {key[:6]}...",
        f"data/outputs/notes.md: {key[:6]}...",
    ]

    # ...and the CSV half of the harvest is gated the same way, so a bought
    # -price table written into the reports directory cannot nominate either.
    table = outputs / "bought_prices.csv"
    table.write_text(f"event_id,price\n{key},-110\n", encoding="utf-8")

    assert _collect_event_ids([table], tmp_path) == (set(), set())


def test_a_hex_run_in_a_filename_is_a_finding_wherever_the_name_sits(
    tmp_path: Path,
) -> None:
    """Reproduction: a 32-hex key in a *filename* was scanned by nothing.

    `_hex_key_offenders` matched only against the body, and the sole code that
    read names — `_collect_event_ids` — is scoped to `data/raw/`, which
    `.gitignore` makes untrackable, so on the real repository it reads no name
    at all. Committing `docs/<key>.md` with an innocent body leaked the key in
    its own filename, past a green suite.

    The second file uses the cache's `<id>_odds.json` convention, which is the
    one an attacker would copy and the one a naive path scan misses.
    """
    key = "0123456789abcdef0123456789abcdef"
    docs = tmp_path / "docs"
    docs.mkdir()
    plain = docs / f"{key}.md"
    plain.write_text(
        "Notes on the fetch. Nothing sensitive in here.\n", encoding="utf-8"
    )
    cache_shaped = docs / f"{key}_odds.json"
    cache_shaped.write_text(json.dumps({"ok": True}), encoding="utf-8")

    assert _hex_key_offenders([plain, cache_shaped], set(), tmp_path) == [
        f"docs/{key}.md: {key[:6]}...",
        f"docs/{key}_odds.json: {key[:6]}...",
    ]

    # ...and it composes with the by-value rule rather than fighting it: a
    # genuine cached response, named after the event its body records, stays
    # green because the stem is a recorded value spent inside `EXEMPT_SCOPE`.
    recorded = "a1b2c3d4" * 4
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    cached = raw / f"{recorded}_odds.json"
    cached.write_text(
        json.dumps({"id": recorded, "bookmakers": []}), encoding="utf-8"
    )

    content_ids, _ = _collect_event_ids([cached], tmp_path)

    assert content_ids == {recorded}
    assert _hex_key_offenders([cached], content_ids, tmp_path) == []


def test_the_key_shape_matcher_is_not_stopped_by_a_word_character() -> None:
    """One matcher, and it sees the cache naming convention in either scan.

    `_` is a word character, so a `\\b`-fenced matcher cannot see the stem in
    `<id>_odds.json` — the exact shape the provider cache uses, and the one an
    attacker would copy. There were two matchers here, and only the path one
    was fenced with lookarounds; a key with an underscore beside it in a
    *body* was therefore invisible. The strings below are deliberately not all
    paths: the same matcher has to fire on the same shape wherever it is read.
    """
    key = "0123456789abcdef0123456789abcdef"
    fences = ("_", "-", ".", "/", "x", "")

    for fence in fences:
        assert HEX_KEY.search(f"{fence}{key}{fence}"), fence
    assert HEX_KEY.search(f"data/raw/{key}_odds.json")
    assert HEX_KEY.search(f"docs/{key}.md")
    # ...and a body, which is the half that was missing.
    assert HEX_KEY.search(f'CACHE = f"{key}_odds.json"')
    assert HEX_KEY.search(f"KEY_{key} = 1")
    # ...while a longer hex run is still not a 32-hex key, name or body.
    assert not HEX_KEY.search("docs/" + "a" * 64 + ".txt")
    assert not HEX_KEY.search("docs/" + "a" * 40 + ".txt")
    assert not HEX_KEY.search("sha256 = " + "a" * 64)


def test_no_tracked_file_contains_an_odds_api_key_shape() -> None:
    """A bare 32-hex string is the shape of the provider key.

    Two corpora and three strings, one rule. Every tracked file is scanned by
    **name** — every one, including the binaries — every tracked file that is a
    symlink is scanned by **target**, and every tracked *text* file is scanned
    by **body**. Dropping a `.png` from a body scan is right, because there is
    nothing to decode; dropping it from a name scan is not, because a filename
    needs no decoding, and while it was dropped from both a tracked
    `docs/<32-hex>.png` was read by nothing.

    The target is the third case, and this docstring did not used to name it:
    a symlink's blob *is* the target string, so `ln -s <32-hex> docs/x`
    committed the key with `path.is_file()` False and the name scan reading a
    filename with nothing in it. It is scanned under the name flag because,
    like a name, it needs no decoding.

    No file is exempt from the name scan for what it is called, and none is
    exempt from the body scan for what it is called either — only for what it
    *is*, and only from the scan that cannot apply to it. Where a file sits
    matters in exactly one direction, identically for both scans: a file under
    `EXEMPT_SCOPE` may spend a recorded event id, a file anywhere else may
    not. A SHA-256 needs no exemption at all — `HEX_KEY`'s lookarounds refuse
    to match inside 64 hex characters, pinned by
    `test_the_key_shape_check_still_catches_a_real_leak`.

    `_text_files()` is deliberately *not* widened to keep binaries: it is also
    the corpus for the assignment and `apiKey=` body scans, which do need
    decodable text.
    """
    offenders = _hex_offenders_for_corpus(
        _tracked_files(), _exempt_hex_values(), PROJECT_ROOT
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


@pytest.mark.parametrize("name", CREDENTIAL_NAMES)
def test_credential_names_are_referenced_but_never_valued(name: str) -> None:
    """The variable name may appear anywhere; only a real value is forbidden."""
    assert isinstance(name, str) and name


def test_the_production_credential_name_is_the_one_the_workflow_uses() -> None:
    """The secret name is a contract with GitHub Actions; it must not drift."""
    assert "FOOTBALL_ODDS_API_KEY" in PROVIDER_ENV_ALLOWLIST
    assert GITHUB_SECRET_NAME in CREDENTIAL_NAMES


def test_data_outputs_reports_are_not_tracked_with_secrets() -> None:
    """Report artifacts under data/outputs must be clean if tracked at all.

    This used to run its own copy of the hex scan with the `\\b` matcher, so
    it carried the same underscore blind spot the body scan did. It now calls
    `_hex_key_offenders`, which means there is one matcher and one spend rule
    to keep correct rather than two, and it scans names as well as bodies —
    a report artifact is as capable of carrying a key in its filename as any
    other file.
    """
    known = _exempt_hex_values()
    reports = [
        path
        for path in _text_files()
        if path.relative_to(PROJECT_ROOT).as_posix().startswith("data/outputs/")
    ]
    named = [
        path
        for path in _tracked_files()
        if path.relative_to(PROJECT_ROOT).as_posix().startswith("data/outputs/")
    ]
    offenders = _hex_key_offenders(named, known, PROJECT_ROOT, bodies=False)
    offenders += _hex_key_offenders(reports, known, PROJECT_ROOT, names=False)
    offenders += [
        f"{path.relative_to(PROJECT_ROOT).as_posix()}: apiKey="
        for path in reports
        if API_KEY_PARAM.search(_read(path))
    ]

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


def test_the_event_id_exemption_is_by_value_and_not_by_directory(
    tmp_path: Path,
) -> None:
    """A hex run that is not a recorded event id is still a finding, even in
    the directory where provider data lives.

    The easy fix for the event-id collision was to exempt `data/raw/`. That
    would carve a hole in this guard exactly where provider data lands, and
    the hole would be invisible. This asserts the narrower rule actually
    holds — over a corpus built here rather than one waited for.

    Waiting is what it used to do: it skipped when nothing had been fetched,
    on the stated promise that the skip would disappear with the first fetch.
    It could not have. `_collect_event_ids` reads `git ls-files`, and
    `.gitignore` makes `data/raw/` untrackable on purpose, so no fetch would
    ever put a file in front of it. The skip was permanent and this assertion
    had never run once.
    """
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    recorded = "a1b2c3d4" * 4
    invented = "deadbeef" * 4
    cached = raw / f"{recorded}_odds.json"
    cached.write_text(
        json.dumps({"id": recorded, "bookmakers": []}), encoding="utf-8"
    )
    # Same directory, same shape, no record of it anywhere in a body. A
    # directory-wide exemption would swallow this; a by-value one must not.
    neighbour = raw / "settings.json"
    neighbour.write_text(json.dumps({"note": invented}), encoding="utf-8")

    content_ids, name_ids = _collect_event_ids([cached, neighbour], tmp_path)

    assert content_ids == {recorded}
    assert name_ids == {recorded}
    assert HEX_KEY.fullmatch(invented)
    assert _hex_key_offenders([cached, neighbour], content_ids, tmp_path) == [
        f"data/raw/settings.json: {invented[:6]}..."
    ]


def test_a_hex_run_that_exists_only_in_a_filename_is_still_a_finding(
    tmp_path: Path,
) -> None:
    """A filename is a claim about what a file holds, not evidence of it.

    Unioning filename stems into the exemption set meant a file named after a
    key and containing nothing exempted that key repo-wide — a leak added by
    committing a file, not by editing this guard. So a stem is only ever
    checked against the bodies, and one that no body corroborates is a
    finding.
    """
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    key = "0123456789abcdef0123456789abcdef"
    empty = raw / f"{key}_odds.json"
    empty.write_text(json.dumps({"ok": True}), encoding="utf-8")

    content_ids, name_ids = _collect_event_ids([empty], tmp_path)

    assert key not in content_ids
    assert name_ids - content_ids == {key}
    # An uncorroborated stem is not merely un-exempt, it is reported — the
    # path is scanned like the body, so this needs no separate bookkeeping.
    assert _hex_key_offenders([empty], content_ids, tmp_path) == [
        f"data/raw/{key}_odds.json: {key[:6]}..."
    ]
    # ...and a file outside the cache directory cannot nominate a stem at all,
    # so it cannot exempt a key that is hardcoded somewhere else.
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    elsewhere = processed / f"{key}_odds.json"
    elsewhere.write_text(json.dumps({"ok": True}), encoding="utf-8")
    leak = tmp_path / "leak.py"
    leak.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")

    content_ids, name_ids = _collect_event_ids([elsewhere, leak], tmp_path)

    assert (content_ids, name_ids) == (set(), set())
    assert _hex_key_offenders([elsewhere, leak], content_ids, tmp_path) == [
        f"data/processed/{key}_odds.json: {key[:6]}...",
        f"leak.py: {key[:6]}...",
    ]


def test_every_cached_response_filename_is_corroborated(tmp_path: Path) -> None:
    """A cached response is named after the event it holds, so its stem and
    its body must agree. When they do not, either the file was renamed or the
    stem is not an event id at all — and the second case is how a key would
    arrive.

    Applied to the real repository, and to a corpus built here first, because
    the repository half is empty and structurally will stay so: `_collect_
    event_ids` reads `git ls-files`, and `.gitignore` makes `data/raw/`
    untrackable (`git check-ignore -v data/raw/x.json` names the rule), so
    both sets come back empty and the repository assertion on its own would be
    an absence rather than a pass. It is kept because it costs nothing and
    would fire the day a cached response is force-added; the synthetic half is
    what proves the rule is alive.

    This is also no longer the only thing standing between a hex filename and
    the build — see
    `test_a_hex_run_in_a_filename_is_a_finding_wherever_the_name_sits`.
    """
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    invented = "beefcafe" * 4
    named_but_unrecorded = raw / f"{invented}_odds.json"
    named_but_unrecorded.write_text(json.dumps({"ok": True}), encoding="utf-8")

    content_ids, name_ids = _collect_event_ids([named_but_unrecorded], tmp_path)

    assert name_ids - content_ids == {invented}

    content_ids, name_ids = _collect_event_ids(_tracked_files(), PROJECT_ROOT)
    uncorroborated = sorted(stem[:6] + "..." for stem in name_ids - content_ids)

    assert uncorroborated == [], (
        f"cached-response filenames no body records: {uncorroborated}"
    )


def test_a_file_is_never_exempt_from_the_hex_scan_for_what_it_is_called(
    tmp_path: Path,
) -> None:
    """Receipts and checksum files are scanned like everything else.

    The guard used to `continue` past any file whose name contained "receipt"
    or "checksum". Identical bytes therefore passed as
    `week3_acceptance_receipt.md` and failed as `week3_acceptance.md`, and
    acceptance receipts are a first-class artifact here — the blind spot sat
    on the files most likely to carry provenance.
    """
    key = "0123456789abcdef0123456789abcdef"
    receipts = tmp_path / "docs" / "receipts"
    receipts.mkdir(parents=True)
    for name in ("week3_acceptance_receipt.md", "manifest_checksum.txt"):
        (receipts / name).write_text(
            f"human acceptance recorded against {key}\n", encoding="utf-8"
        )

    found = _hex_key_offenders(sorted(receipts.iterdir()), set(), tmp_path)

    assert found == [
        f"docs/receipts/manifest_checksum.txt: {key[:6]}...",
        f"docs/receipts/week3_acceptance_receipt.md: {key[:6]}...",
    ]


def test_a_sha256_does_not_need_a_by_name_exemption(tmp_path: Path) -> None:
    """The reason the "checksum" skip could go: `HEX_KEY` never wanted it.

    Its `\\b` boundaries refuse to match inside a 64-character run, so a real
    digest was never a finding and the skip bought nothing — while costing
    every other hex run in the file.
    """
    digest = tmp_path / "SHA256SUMS"
    digest.write_text("a" * 64 + "  data/outputs/report.md\n", encoding="utf-8")

    assert _hex_key_offenders([digest], set(), tmp_path) == []


def test_the_key_shape_check_still_fires_on_something_that_is_not_an_event_id() -> None:
    known = _exempt_hex_values()
    leaked = "0123456789abcdef0123456789abcdef"

    assert leaked not in known
    assert HEX_KEY.search(f"{GITHUB_SECRET_NAME}={leaked}")


def test_a_hex_key_beside_an_underscore_in_a_body_is_a_finding(
    tmp_path: Path,
) -> None:
    """Reproduction: one underscore of context hid a 32-hex key in a body.

    The path scan was fenced with lookarounds and the body scan was left on
    `\\b[0-9a-f]{32}\\b`. `_` is a word character, so the boundary never opened
    beside it — and the cache-naming form `<key>_odds.json`, which this
    module's own comment calls the one an attacker would copy, is exactly that
    shape. Each body below carried a real credential past a green suite.

    Written as several spellings on purpose: a fix that catches only the first
    is a narrower guard, not a repaired one.
    """
    key = "0123456789abcdef0123456789abcdef"
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    spellings = {
        # the cache-naming form, quoted in source
        "cache.py": f'CACHE = f"{key}_odds.json"\n',
        # the name on the left of an assignment
        "named.py": f"KEY_{key} = 1\n",
        # underscore on both sides, no whitespace anywhere
        "fenced.py": f"_{key}_\n",
        # a URL path segment, which is neither `_` nor a word boundary case
        "url.md": f"https://api.example/v4/{key}/odds\n",
        # inside a longer identifier, which `\\b` also refuses
        "ident.py": f"ODDS{key}ZONE = 2\n",
        # uppercased, which is the same credential
        "upper.py": f'KEY = "{key.upper()}"\n',
    }
    for name, body in spellings.items():
        (scripts / name).write_text(body, encoding="utf-8")

    offenders = _hex_key_offenders(
        [scripts / name for name in sorted(spellings)], set(), tmp_path
    )

    assert offenders == [
        f"scripts/{name}: {key[:6]}..." for name in sorted(spellings)
    ]

    # ...and the matcher still declines a longer hex run in a body, so a
    # digest table is not turned into a wall of findings.
    digests = tmp_path / "SHA256SUMS"
    digests.write_text(
        "\n".join(
            f"{letter * 64}  report-{index}.md"
            for index, letter in enumerate("abcdef")
        ),
        encoding="utf-8",
    )

    assert _hex_key_offenders([digests], set(), tmp_path) == []


def test_a_hex_run_in_the_name_of_a_binary_is_a_finding(tmp_path: Path) -> None:
    """Reproduction: the name scan sat behind a *content* filter.

    `_text_files()` drops a `.png` before anything reads it, which is right
    for a body and wrong for a name — a filename needs no decoding. A tracked
    `docs/<32-hex>.png` was therefore scanned by nothing at all and the suite
    stayed green.

    This runs `_hex_offenders_for_corpus`, the real split, over a corpus that
    contains real undecodable bytes, so the assertion is about what the code
    does and not about what the filter list says.
    """
    key = "0123456789abcdef0123456789abcdef"
    docs = tmp_path / "docs"
    docs.mkdir()
    binaries = [f"{key}.png", f"{key}.pdf", f"{key}_chart.zip", f"cover-{key}.jpg"]
    for name in binaries:
        # Bytes that are not valid UTF-8, so nothing here can be read as text.
        (docs / name).write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00\x01")
    text = docs / "notes.md"
    text.write_text("Nothing sensitive in here.\n", encoding="utf-8")

    corpus = [docs / name for name in binaries] + [text]

    assert _body_scannable(corpus) == [text]
    assert _hex_offenders_for_corpus(corpus, set(), tmp_path) == [
        f"docs/{name}: {key[:6]}..." for name in binaries
    ]

    # ...and the spend rule is the same for a name as for a body: a recorded
    # event id is still spendable under `EXEMPT_SCOPE` and nowhere else.
    recorded = "a1b2c3d4" * 4
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    chart = outputs / f"{recorded}.png"
    chart.write_bytes(b"\x89PNG\r\n\x1a\n")
    elsewhere = docs / f"{recorded}.pdf"
    elsewhere.write_bytes(b"%PDF-1.4\n")

    assert _hex_offenders_for_corpus([chart, elsewhere], {recorded}, tmp_path) == [
        f"docs/{recorded}.pdf: {recorded[:6]}..."
    ]


def test_the_canonical_python_assignment_is_a_finding(tmp_path: Path) -> None:
    """Reproduction: `os.environ["NAME"] = "<key>"` was caught by nothing.

    `ASSIGNMENT` required `=` to touch the name, and in the canonical spelling
    a closing quote and bracket sit between. The sibling guard in
    `tests/test_contract_strings.py` inspects the three characters after the
    name, which there are `"] `, and finds no `=` either. The three files
    below are the three spellings that were confirmed green while carrying the
    same value verbatim.
    """
    name = GITHUB_SECRET_NAME
    inherited = "FOOTBALL_ODDS_API_KEY"
    value = "sk-live-4f19c0d27ba6e83d"
    leaks = {
        "src/fetch.py": f'import os\nos.environ["{name}"] = "{value}"\n',
        "docs/runbook.md": f'Then run `os.environ["{name}"] = "{value}"`.\n',
        "ci/gameday.yml": f"env:\n  {inherited}: {value}\n",
    }
    written: list[Path] = []
    for relative, body in leaks.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        written.append(path)

    assert _assignment_offenders(written, tmp_path) == [
        f"src/fetch.py: {name}",
        f"docs/runbook.md: {name}",
        f"ci/gameday.yml: {inherited}",
    ]


def test_the_assignment_scan_survives_a_rewording(tmp_path: Path) -> None:
    """The attacks I tried against my own fix, and the prose it must not eat.

    Every spelling here writes the same live-looking value under a credential
    name. A guard that catches the first and misses the rest is the narrowing
    this module has been through twice already, so the rewordings are asserted
    rather than trusted.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    hexish = "aB3xQ9zLmN2pR7tV"
    rewordings = {
        "a.py": f'os.environ["{name}"] = "{value}"',
        "b.py": f"os.environ['{name}']='{value}'",
        "c.py": f'os.environ.setdefault("{name}", "{value}")',
        "d.py": f'CONFIG = {{"{name}": "{value}"}}',
        "e.py": f'settings["env"]["{name}"] = "{hexish}"',
        "f.yml": f"  {name}: {value}",
        "g.yml": f'  {name}: "{value}"',
        "h.md": f"- `{name}` = {value}",
        "i.sh": f': "${{{name}:-{value}}}"',
        "j.json": f'{{"{name}": "{hexish}"}}',
        "k.py": f'os.environ[ "{name}" ] = "{value}"',
        "l.toml": f'{name} = "{value}"',
    }
    for filename, body in rewordings.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    caught = _assignment_offenders(
        [tmp_path / filename for filename in sorted(rewordings)], tmp_path
    )

    assert caught == [f"{filename}: {name}" for filename in sorted(rewordings)]

    # ...and the prose that has to keep passing, which is why the `:` and `,`
    # separators carry a value test rather than a wider regex.
    prose = {
        "table.md": f"| `{name}` | The name of the GitHub secret |",
        "gloss.md": f"`{name}`: the name of the GitHub secret",
        "list.py": (
            f'CREDENTIAL_NAMES = frozenset({{"{name}", "FOOTBALL_ODDS_API_KEY"}})'
        ),
        "guard.sh": f'if [ -n "${{{name}:-}}" ]; then echo missing; fi',
        "ci.yml": f"  {name}: ${{{{ secrets.{name} }}}}",
        "empty.yml": f'  {name}: ""',
        "state.md": f"{name}: not-configured",
        "where.md": f"{name}: see docs/runbook-2024.md",
        "ref.md": f"{name}: $ODDS_KEY",
        "both.md": f"{name}, FOOTBALL_ODDS_API_KEY",
        "shape.md": f"Run `export {name}=your-api-key` first.",
        "example.env": f"{name}=",
    }
    for filename, body in prose.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(prose)], tmp_path
    ) == []


def test_the_value_test_gaps_are_the_ones_documented() -> None:
    """The `:` and `,` value test is not airtight; these are its exact edges.

    Naming them in an assertion is the difference between a known limit and a
    surprise. Both are confined to the separated family — the `=` family runs
    no value test, so it catches all four of these — and both are the price of
    letting ordinary prose through. If someone tightens the value test, this
    test fails and the comment above `CREDENTIAL_VALUE` gets corrected with
    it.
    """
    assert not _looks_like_a_credential_value("purelettersecret")
    assert not _looks_like_a_credential_value("ab12.cd34.ef56")
    assert not _looks_like_a_credential_value("sk/live/4f19c0d2")
    # ...but the `=` family runs no value test on its FIRST token, so the same
    # values are findings the moment an `=` is what gives them to the name.
    assert ASSIGNMENT.search(f"{GITHUB_SECRET_NAME}=purelettersecret")
    assert ASSIGNMENT.search(f"{GITHUB_SECRET_NAME}=ab12.cd34.ef56")
    # ...and a value that is short, shouting, or digitless is not a value.
    assert not _looks_like_a_credential_value("the")
    assert not _looks_like_a_credential_value("FOOTBALL_ODDS_API_KEY")
    assert not _looks_like_a_credential_value("not-configured")
    # ...while the shapes a provider actually issues are.
    assert _looks_like_a_credential_value("sk-live-4f19c0d27ba6e83d")
    assert _looks_like_a_credential_value("0123456789abcdef0123456789abcdef")
    assert _looks_like_a_credential_value("aB3xQ9zLmN2pR7tV")


def test_the_credential_name_shape_knows_more_than_one_spelling() -> None:
    """A credential renamed `..._APIKEY` must not un-arm two scans at once.

    `CREDENTIAL_NAME_SHAPE` feeds the drift guard *and* decides which names
    the assignment scan is built from. While it recognised only `_API_KEY`, a
    future credential named any other way was invisible to both — and the
    failure mode is silence, not a red build.
    """
    for spelling in ("NCAAF_ODDS_APIKEY", "NCAAF_ODDS_API_TOKEN", "X_API_KEY"):
        assert CREDENTIAL_NAME_SHAPE.findall(f"export {spelling}=x") == [spelling]
    # ...and it still does not claim ordinary shouting-case constants.
    assert CREDENTIAL_NAME_SHAPE.findall("PROJECT_ROOT = Path(__file__)") == []
    assert CREDENTIAL_NAME_SHAPE.findall("API_KEY_PARAM = re.compile(...)") == []


def test_a_unicode_blank_does_not_open_a_gap_between_the_classes(
    tmp_path: Path,
) -> None:
    """Reproduction: one invisible character defeated both families at once.

    The spacing class was `[ \\t]*` — ASCII — and the value was captured with
    `(?=(\\S+))`, which is Unicode-aware. A U+00A0 between the operator and the
    key fell in the gap *between* the two: the spacing would not consume it and
    `\\S` would not begin on it, so no match opened anywhere and
    `export <the secret's name>=<U+00A0>sk-live-…` in a tracked `.md` gave a
    fully green suite. Nothing about the line looks unusual on screen, which is
    why it is asserted over three spellings and on both sides of the operator
    rather than trusted once.

    U+200B is here for the opposite reason. Unicode does not call it
    whitespace, so `\\S` starts on it and it rides *into* the token; `_unwrap`
    deletes it by category, which is what makes it a finding under `:` as well
    as under `=`.

    Be exact about what this test pins, because it is not one rule. Reverting
    `_BLANK` to `[ \\t]*` on its own leaves this passing — `_CLOSERS` eats the
    blank before the operator and `str.split()` eats it after. What re-opens it
    is reverting the value capture to `(?=(\\S+))`, with or without the ASCII
    spacing class; both reversions were run and the outcome of each recorded
    here rather than assumed. So this is a test of the *behaviour*, and three
    separate rules have to stay right for it to pass.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    blanks = {
        "nbsp": "\u00a0",
        "zero_width": "\u200b",
        "ideographic": "\u3000",
    }
    written: list[Path] = []
    for label, blank in blanks.items():
        for family, line in (
            ("after_equals", f"export {name}={blank}{value}"),
            ("around_equals", f"export {name}{blank}={blank}{value}"),
            ("after_colon", f"{name}:{blank}{value}"),
        ):
            path = tmp_path / f"{label}_{family}.md"
            path.write_text(line + "\n", encoding="utf-8")
            written.append(path)

    assert _assignment_offenders(written, tmp_path) == [
        f"{path.name}: {name}" for path in written
    ]

    # ...and a newline is still not a blank. That exclusion is the whole reason
    # the class is not `\s*`, and it is what keeps a bare `NAME=` green.
    example = tmp_path / "example.env"
    example.write_text(f"{name}=\n{value}\n", encoding="utf-8")

    assert _assignment_offenders([example], tmp_path) == []


def test_a_tracked_symlink_carries_its_target_into_the_scans(
    tmp_path: Path,
) -> None:
    """Reproduction: a symlink's blob was read by no scanner in this module.

    `git` stores a symlink as a blob whose contents are the target string, so
    `ln -s sk-live-… docs/provider_key` commits the credential in plaintext.
    `_body_scannable` dropped the path on `path.is_file()` — False for a
    dangling link — and the name scan read `docs/provider_key`, a name with
    nothing in it. Both links below are named after nothing on purpose: the
    only place the credential appears is the target.
    """
    key = "0123456789abcdef0123456789abcdef"
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    docs = tmp_path / "docs"
    docs.mkdir()
    hex_link = docs / "provider_key"
    hex_link.symlink_to(key)
    assignment_link = docs / "note"
    assignment_link.symlink_to(f"{name}={value}")

    # The condition that used to drop it, asserted rather than described.
    assert not hex_link.is_file()
    assert _hex_offenders_for_corpus([hex_link], set(), tmp_path) == [
        f"docs/provider_key: {key[:6]}..."
    ]

    # The link survives the body filter, which is what carries it into the
    # assignment scan — its body reads as empty and its target does not.
    assert _body_scannable([assignment_link]) == [assignment_link]
    assert _read(assignment_link) == ""
    assert _assignment_offenders([assignment_link], tmp_path) == [
        f"docs/note: {name}"
    ]

    # ...and the spend rule reaches a target exactly as it reaches a name: a
    # recorded event id is still only spendable under `EXEMPT_SCOPE`.
    recorded = "a1b2c3d4" * 4
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    inside = outputs / "chart"
    inside.symlink_to(recorded)
    outside = docs / "chart"
    outside.symlink_to(recorded)

    assert _hex_offenders_for_corpus(
        [inside, outside], {recorded}, tmp_path
    ) == [f"docs/chart: {recorded[:6]}..."]

    # ...and a symlink loop is a finding-free file, not a crash. Admitting
    # symlinks to the body corpus put one in front of `Path.resolve()`, which
    # raises `RuntimeError` on a loop, so a committed `ln -s loop loop` turned
    # the whole guard into a traceback. Found by writing the loop and running
    # the scan, not by reading `pathlib`. A path that will not resolve is not
    # this file, so it stays in the corpus and is scanned.
    loop = docs / "loop"
    loop.symlink_to("loop")

    assert _body_scannable([loop]) == [loop]
    assert _hex_offenders_for_corpus([loop], set(), tmp_path) == []
    assert _assignment_offenders([loop], tmp_path) == []


def test_markup_between_the_name_and_the_operator_is_a_finding(
    tmp_path: Path,
) -> None:
    """`_CLOSERS` enumerated six characters, and an enumeration is a spelling.

    Most of this repository's prose is Markdown and most of its emphasis
    markers were none of the six, so `**NAME**: <key>` and its siblings sat
    between the name and the operator and stopped the match dead. The HTML
    spelling did the same. Every line below was written, run, and observed to
    pass a green suite before `_CLOSERS` became a shape rather than a list.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    markup = {
        "bold_colon.md": f"**{name}**: {value}",
        "bold_equals.md": f"**{name}** = {value}",
        "italic.md": f"*{name}*: {value}",
        "code_tag.md": f"<code>{name}</code>: {value}",
        "underscore.md": f"_{name}_: {value}",
        "strong_tag.md": f"<strong>{name}</strong> = {value}",
        "table_bold.md": f"| **{name}** | {value} |",
    }
    for filename, body in markup.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(markup)], tmp_path
    ) == [f"{filename}: {name}" for filename in sorted(markup)]

    # ...and admitting `_` to the closers does not turn a longer identifier
    # into an assignment of the shorter one: the closers stop dead at the
    # alphanumeric that follows.
    sibling = tmp_path / "sibling.yml"
    sibling.write_text(f"{name}_FILE: {value}\n", encoding="utf-8")

    assert _assignment_offenders([sibling], tmp_path) == []


def test_the_compound_assignment_operators_are_findings(tmp_path: Path) -> None:
    """`:=`, `?=` and `+=` are assignments a machine reads back.

    All three were missed by both families: the `=` did not touch the name, and
    the character in front of it was not a closer either, so nothing bridged
    the gap. The operator is a family now for the same reason the parameter
    name and the credential name are — a matcher that knows one spelling goes
    quiet, and goes quiet silently, the day something is written another way.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    operators = {
        "colon_equals.mk": f"{name} := {value}",
        "plus_equals.mk": f"{name} += {value}",
        "query_equals.mk": f"{name} ?= {value}",
        "tight.mk": f"{name}:={value}",
    }
    for filename, body in operators.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(operators)], tmp_path
    ) == [f"{filename}: {name}" for filename in sorted(operators)]

    # The intentional catch that comes with the family: shell's default-assign
    # writes a literal into the environment, so it is an assignment and is now
    # reported. `:-` does not assign and is unchanged — `SEPARATED` reaches it.
    assign_default = tmp_path / "default.sh"
    assign_default.write_text(f': "${{{name}:={value}}}"\n', encoding="utf-8")

    assert _assignment_offenders([assign_default], tmp_path) == [
        f"default.sh: {name}"
    ]
    assert ASSIGNMENT.search(f'"${{{name}:={value}}}"')
    assert not ASSIGNMENT.search(f'"${{{name}:-}}"')


def test_a_value_past_the_first_token_on_the_line_is_a_finding(
    tmp_path: Path,
) -> None:
    """Reproduction: both patterns read one token and then gave up on the line.

    `(?=(\\S+))` captured exactly the first whitespace-separated token, and
    `if not value: continue` abandoned the whole line whenever that token
    unwrapped to nothing. So a functioning Python assignment whose first token
    is an empty string literal passed, and so did a three-column Markdown table
    row — the shape this repository's own contract table uses — because the
    guard read the second cell and never reached the third.

    An empty token now advances; it never ends the line.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    past_the_first = {
        "after_a_placeholder.md": f"{name}: <your-key> {value}",
        "after_a_reference.sh": f"{name}=$UNUSED {value}",
        "empty_first.py": f'os.environ["{name}"] = "" "{value}"',
        "four_columns.md": f"| `{name}` | live | rotated weekly | {value} |",
        "three_columns.md": f"| `{name}` | live | {value} |",
    }
    for filename, body in past_the_first.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(past_the_first)], tmp_path
    ) == [f"{filename}: {name}" for filename in sorted(past_the_first)]

    # ...and the prose that has to survive reading a whole line rather than its
    # first token. An English sentence after a placeholder is still not a
    # value, and this repository's real contract row is three cells of prose.
    prose = {
        "gloss.md": f"{name}: the name of the secret, not its value",
        "row.md": (
            f"| `{name}` | The name of the GitHub secret holding the provider "
            "credential | Two labs on one credential cannot be told apart |"
        ),
        "shape.md": f"Run `export {name}=your-api-key` before the fetch.",
    }
    for filename, body in prose.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(prose)], tmp_path
    ) == []


def test_the_gaps_this_guard_still_has_are_the_ones_written_down(
    tmp_path: Path,
) -> None:
    """The rewordings that still get past this module, asserted not remembered.

    Each line below is an attack that was written, run, and observed to pass.
    They are recorded rather than quietly left open, because the failure this
    module keeps repeating is a guard that looks closed: the previous two
    rounds each replaced a blacklist with a narrower rule and reported the
    rule, not its edges.

    **This asserts nothing is allowed.** Every gate above still demands an
    empty offender list. This is a ledger of coverage, and the correct
    response to any line is to close it and delete the line — a failure here
    means someone closed a gap, which is good news and an invitation to
    rewrite this docstring.

    * Hex glued to another hex character. `<key>00`, or `<key>CACHE` whose `C`
      is a hex letter, is a run longer than 32 and the matcher deliberately
      refuses to fire inside one — that refusal is what keeps a SHA-256 quiet.
      Widening the fence to `A-F` traded a little of this away for uppercase
      coverage, which is the better half of the trade but not a free one.
    * A key split across a concatenation. Nothing here parses source.
    * A value on the line after its name. The spacing classes stop at a
      newline on purpose: `\\s` would read `.env.example`'s empty `NAME=` plus
      the next line's first word as an assignment, which failed the build on a
      file with no values in it at all.
    * A name assembled at runtime from pieces.
    * A separator this module does not know. `=`, `:`, `,` and `|` are the
      four that a machine reads back — assignment, YAML, dict-or-call, and
      the Markdown table this repository documents its credential in. A tab
      or a prose arrow is not among them; prose separators are unbounded and
      chasing them is how a guard gets narrow.
    * A value under `:`/`,`/`|` that is shorter than twelve characters, all
      letters, or carries a `.` or a `/`. Those are the value test's edges and
      `test_the_value_test_gaps_are_the_ones_documented` states each one. The
      `=` family runs no value test **on its first token** and so has none of
      these gaps there — but every later token on the line is read with the
      same test, so `NAME=$UNUSED sk.live.4f19c0d2` is missed for exactly the
      reason `NAME: sk.live.4f19c0d2` is. The alternative was to report the
      English sentence after `export NAME=<placeholder>`.
    * A literal nested inside a shell or CI expansion. `_is_a_reference`
      dismisses a `$`-prefixed token unconditionally — deliberately, because
      `$` means expansion whatever follows — so `${NAME:=${OTHER:-<key>}}`
      hides the key one level down where no inner match opens on it, since
      `OTHER` is not a credential name. Reaching it means parsing shell.
    * A value more than five hundred characters along the line from the name
      that gives it. `_REST_OF_LINE` is bounded there so the scan cannot go
      quadratic on a generated one-line file; the bound is stated in that
      comment with the measurement that forced it.
    * More than eight characters of markup between the name and the operator.
      `_CLOSERS` is bounded at eight repetitions, so `NAME]]]]]]]]]]: <key>`
      opens no match. Unbounded closers would let the scan walk across
      arbitrary punctuation to reach an operator that belongs to something
      else, which is a wider hole than this one.
    * Markup between the name and the operator that carries alphanumerics and
      is not an HTML tag. A Markdown link, `[NAME](#anchor): <key>`, is the
      live example; so is an HTML entity, `NAME&nbsp;= <key>`. The entity case
      is a *decoding* this module does not do, like the base64 line below.
    * An invisible character Unicode files as a letter rather than as a space
      or a format mark — U+3164 HANGUL FILLER is the one that was found —
      glued to the front of a value under `:`/`,`/`|`. `_BLANK` does not
      consume it because it is not whitespace and `INVISIBLE_CATEGORIES` does
      not strip it because its category is `Lo`, so it fails
      `CREDENTIAL_VALUE` and the value is dismissed. The `=` family catches
      it, having no value test on the first token; both halves are run below.
    * A symlink wearing a binary suffix. Its **name** and its **target** are
      both hex-scanned, because that scan needs no decoding — but
      `BINARY_SUFFIXES` drops it from `_text_files()`, which is the corpus for
      the assignment and `apiKey=` scans, so `ln -s "NAME=<key>" cover.png`
      leaks past those two. This is the same suffix-rule trade as `notes.pdf`
      below and it is widened the same way or not at all.
    * A body that is not text at all — a base64 or otherwise encoded key.
      Nothing here decodes. The UTF-16 case *is* covered, because that one is
      a decoding this module was getting wrong rather than an encoding it
      would have to undo.
    * A text body wearing a binary suffix. `notes.pdf` full of ASCII is not
      body-scanned, because `BINARY_SUFFIXES` is a suffix rule and not a
      sniff. Its *name* is still scanned, and widening the body corpus is not
      the fix: that same corpus feeds the assignment and `apiKey=` scans,
      which need decodable text.
    * This file's own body, which is excluded so the guard does not flag its
      own needles — `test_the_guard_excludes_itself_from_its_own_scan`. A
      credential pasted into this module is caught by nothing here. Its name
      is scanned like every other tracked path.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    key = "0123456789abcdef0123456789abcdef"
    gaps = {
        "padded.py": f'KEY = "{key}00"',
        "glued.py": f"ODDS{key}CACHE = 2",
        "split.py": f'KEY = "{key[:16]}" "{key[16:]}"',
        "block.yml": f"{name}: >\n  {value}",
        "next_line.env": f"{name}=\n{value}",
        "built.py": f'os.environ["NCAAF_ODDS_" "API_KEY"] = "{value}"',
        "arrow.md": f"{name} -> {value}",
        "column.tsv": f"{name}\t{value}",
        "short.yml": f"{name}: abc123def45",
        "encoded.py": 'KEY = "MDEyMzQ1Njc4OWFiY2RlZg=="',
        "closers.md": f"{name}]]]]]]]]]]: {value}",
        "link.md": f"[{name}](#the-secret): {value}",
        "entity.md": f"{name}&nbsp;= {value}",
        "filler.md": f"{name}:\u3164{value}",
        "past_colon.md": f"{name}: <your-key> sk.live.4f19c0d27ba6e83d",
        "past_equals.sh": f"{name}=$UNUSED sk.live.4f19c0d27ba6e83d",
        "far.md": f"{name}: " + "prose " * 120 + value,
        "nested.sh": ': "${' + name + ':=${OTHER:-' + value + '}}"',
    }
    for filename, body in gaps.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")
    paths = [tmp_path / filename for filename in sorted(gaps)]

    assert _hex_key_offenders(paths, set(), tmp_path) == []
    assert _assignment_offenders(paths, tmp_path) == []

    # The suffix rule is a rule about bodies, so a text file wearing a binary
    # suffix keeps its body — and only its body — out of the scan.
    disguised = tmp_path / "notes.pdf"
    disguised.write_text(f'KEY = "{key}"\n{name} = "{value}"\n', encoding="utf-8")

    assert _body_scannable([disguised]) == []
    assert _hex_offenders_for_corpus([disguised], set(), tmp_path) == []
    # ...and the name half of the same file is scanned, which is the half the
    # binary carve-out used to swallow too.
    named = tmp_path / f"{key}.pdf"
    named.write_bytes(b"%PDF-1.4\n")

    assert _hex_offenders_for_corpus([named], set(), tmp_path) == [
        f"{key}.pdf: {key[:6]}..."
    ]

    # A symlink wearing a binary suffix is the same trade seen from the other
    # side: the suffix rule keeps it out of the body corpus, so the assignment
    # scan never sees the target — while the hex scan, which needs no
    # decoding, reads both the name and the target.
    cover = tmp_path / "cover.png"
    cover.symlink_to(f"{name}={value}")
    hex_cover = tmp_path / "art.png"
    hex_cover.symlink_to(key)

    assert _body_scannable([cover]) == []
    assert _assignment_offenders(_body_scannable([cover]), tmp_path) == []
    assert _hex_offenders_for_corpus([hex_cover], set(), tmp_path) == [
        f"art.png: {key[:6]}..."
    ]

    # ...and the halves of those gaps that are NOT open, so that narrowing one
    # of them back fails here rather than passing quietly. An invisible letter
    # and a value past the first token are both findings under `=`.
    caught = {
        "filler_equals.md": f"{name}=\u3164{value}",
        "past_equals_real.sh": f"{name}=$UNUSED {value}",
        "eight_closers.md": f"{name}]]]]]]]]: {value}",
    }
    for filename, body in caught.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(caught)], tmp_path
    ) == [f"{filename}: {name}" for filename in sorted(caught)]


def test_the_rewordings_that_were_closed_stay_closed(tmp_path: Path) -> None:
    """The other half of the attack run: what was open and now is not.

    Each of these passed the guard when it was written and fails it now. They
    live in a test rather than in a commit message because the next narrowing
    will be someone's honest simplification of one of these rules.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    key = "0123456789abcdef0123456789abcdef"

    # An uppercased copy of a key is the same key — in a body and in a name.
    upper = tmp_path / "docs"
    upper.mkdir()
    (upper / f"{key.upper()}.md").write_text("notes\n", encoding="utf-8")
    (upper / "mixed.py").write_text(
        f'KEY = "{key[:16].upper()}{key[16:]}"\n', encoding="utf-8"
    )

    assert _hex_offenders_for_corpus(sorted(upper.iterdir()), set(), tmp_path) == [
        f"docs/{key.upper()}.md: {key[:6].upper()}...",
        f"docs/mixed.py: {key[:6].upper()}...",
    ]

    # A Markdown table cell, which is how this repository writes about its own
    # credential, and a lowercased spelling of the name.
    table = tmp_path / "contract.md"
    table.write_text(f"| `{name}` | {value} |\n", encoding="utf-8")
    lowered = tmp_path / "shim.py"
    lowered.write_text(f'os.environ["{name.lower()}"] = "{value}"\n', encoding="utf-8")

    assert _assignment_offenders([table, lowered], tmp_path) == [
        f"contract.md: {name}",
        f"shim.py: {name.lower()}",
    ]

    # ...and the real table row this repository actually has still passes.
    real = tmp_path / "CONTRACT.md"
    real.write_text(
        f"| `{name}` | The name of the GitHub secret holding the provider "
        "credential | Two labs on one credential cannot be told apart |\n",
        encoding="utf-8",
    )

    assert _assignment_offenders([real], tmp_path) == []


def test_a_credential_in_a_utf16_body_is_a_finding(tmp_path: Path) -> None:
    """A UTF-16 file decodes into `K\\x00E\\x00Y…` and hid everything.

    `errors="ignore"` on a UTF-8 decode leaves the NULs in place, so every
    matcher here — which all want an unbroken run — saw nothing. Written as
    real UTF-16 bytes rather than as a string with NULs typed into it, so the
    test would still fail if `_read` were changed to decode differently.
    """
    key = "0123456789abcdef0123456789abcdef"
    name = GITHUB_SECRET_NAME
    little = tmp_path / "notes.txt"
    little.write_bytes(f'KEY = "{key}"\n'.encode("utf-16-le"))
    big = tmp_path / "config.txt"
    big.write_bytes(f'{name} = "sk-live-4f19c0d27ba6e83d"\n'.encode("utf-16-be"))

    assert "\x00" in little.read_text(encoding="utf-8", errors="ignore")
    assert _hex_key_offenders([little], set(), tmp_path) == [
        f"notes.txt: {key[:6]}..."
    ]
    assert _assignment_offenders([big], tmp_path) == [f"config.txt: {name}"]


def test_the_api_key_parameter_matcher_knows_the_spelling_family(
    tmp_path: Path,
) -> None:
    """`apiKey=` is one provider's casing, not the shape of the capability.

    The thing being matched is a URL parameter that carries a key. A matcher
    that knows a single casing goes quiet the day a provider spells it
    `api_key`, and goes quiet silently.

    This used to reword only the *parameter name*, and the single value it
    tried was all-alphanumeric — which is how the matcher came to be unable to
    fire on the one value this module uses as its own worked example. Probed:
    `apiKey=sk-live-4f19c0d27ba6e83d` was a NOMATCH under
    `api[_-]?key=[A-Za-z0-9]{8,}`, because `-` is not in the class, while
    `apiKey=0123456789abcdef` matched. The value is a family now too, and the
    four spellings below cross every casing.
    """
    values = (
        "aZ90bYx8cW7v",
        "sk-live-4f19c0d27ba6e83d",
        "sk_live_4f19c0d27ba6e83d",
        "0123456789abcdef",
    )
    for spelling in ("apiKey=", "apikey=", "API_KEY=", "api-key=", "ApiKey="):
        for value in values:
            url = f"https://x/v4/odds?{spelling}{value}&regions=us"
            assert API_KEY_PARAM.search(url), (spelling, value)
    # ...and the defences that mention the token, in any casing, stay clean.
    assert not API_KEY_PARAM.search('re.compile(r"(apiKey=)[^&s]+")')
    assert not API_KEY_PARAM.search('assert "api_key=" not in text')
    assert not API_KEY_PARAM.search("apiKey=[redacted]")


def test_a_value_wearing_a_placeholder_bracket_is_still_a_finding(
    tmp_path: Path,
) -> None:
    """`NAME: <sk-live-…>` — the leak dressed as documentation.

    Anything starting `<` or `{` used to be waved through as a reference, so
    an attacker had only to put the key in the brackets the docs use. Now the
    brackets come off and what is inside has to fail the value test.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    dressed = {
        "a.yml": f"{name}: <{value}>",
        "b.py": f'os.environ["{name}"] = "<{value}>"',
        "c.py": f'os.environ["{name}"] = "{{{value}}}"',
    }
    for filename, body in dressed.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(dressed)], tmp_path
    ) == [f"{filename}: {name}" for filename in sorted(dressed)]

    # ...and the placeholders and interpolations documentation actually uses
    # still pass, f-string prefix included — that prefix was a false positive
    # this widening introduced, and `_unwrap` removing it is what fixed it.
    fine = {
        "d.md": f"{name}=<your-key>",
        "e.md": f"{name}=<paste yours>",
        "f.py": f'os.environ["{name}"] = f"{{SECRET}}"',
        "g.py": f'os.environ["{name}"] = rb"{{SECRET}}"',
        "h.yml": f"{name}: ${{{{ secrets.{name} }}}}",
    }
    for filename, body in fine.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(fine)], tmp_path
    ) == []
