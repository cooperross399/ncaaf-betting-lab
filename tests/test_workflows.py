"""The workflows' self-declared invariants, checked instead of commented.

Until this file existed, nothing in this repository read
`.github/workflows/*.yml`. Every promise those files make about themselves —
no credential in the test job, no path filter, read-only permissions, no
swallowed failure, the whole suite every time — was enforced by a comment, and
a comment survives the edit that contradicts it. Both files were caught doing
exactly that: ledger-guard.yml carried "Unfiltered on purpose" two lines above
a `branches: [main]` push filter, and tests.yml carried a credential assertion
that inspected an environment the credential could never have been in.

So the rules live here, against the parse rather than the prose. Every check is
written to fail closed: a workflow that cannot be found, cannot be parsed, or
declares nothing at all is a failure, not a quiet pass. That is why
`test_the_workflow_directory_is_not_empty` exists — a linter with nothing to
lint reports green, which is the same fail-open shape as the gates it is here
to protect.

The rules are deliberately blunt. Every one of them has a legitimate-looking
exception somebody will eventually want; the exceptions are how gates rot.

DO NOT MATCH TEXT. EXECUTE THE THING AND OBSERVE WHAT IT DOES.
--------------------------------------------------------------
This file has now been defeated in three rounds, and the first two fixes were
the same mistake twice. Round one shipped blacklists of exact spellings. Round
two replaced each blacklist with a NARROWER POSITIVE RULE and every one of
those was defeated by a rewording, because a positive rule written as a regex
is still a rule about punctuation:

* the swallow rule began `if not OR_LIST.search(line) ... : continue`, so
  `if ! cmd; then echo; fi` — which contains no `||` at all — was never even
  looked at, and neither was `set +o pipefail`, and neither was a `trap` that
  exits zero. Every one of those was verified under `bash -e` to exit 0 where
  the house idiom exits 1: a full pass over the step that makes green mean
  "the suite passed";
* the same rule exempted any line matching CONDITION, which matched the WHOLE
  line, so moving a `|| true` onto a line that also carried `; then` exempted
  it wholesale;
* NONZERO_EXIT was searched over the whole joined line, so one `exit 1`
  belonging to a different command — or sitting inside a quoted string that
  never executes — satisfied the rule for every or-list on that line;
* `check_every_piped_run_block_sets_pipefail` read only `lines[0]`, so a block
  could open with `set -euo pipefail` and turn it off again two lines down;
* SECRET_REFERENCE knew the two spellings that dereference a NAMED secret, so
  `${{ toJSON(secrets) }}` — which needs neither a dot nor a bracket and
  interpolates EVERY secret in the repository — was a full pass, strictly worse
  than the attack that was caught. So was `secrets: inherit`;
* `check_the_suite_is_never_narrowed` inspected only arguments beginning with
  `-`, so `--ignore=tests/test_power.py` was rejected while the positional
  `tests/test_power.py` passed, and a selection naming only the modules the
  junit manifest requires would have satisfied that gate too.

So the swallow rule no longer reads the block. It RUNS it.
`swallow_findings` writes each run block to a sandbox, prepends a shell stub
for every command word it contains, executes it under `bash -e`, and reads the
exit code. Nothing real runs: PATH points at an empty directory, every command
word is replaced by a shell function, and any command that reaches the shell
without a stub is reported by `run_block_under_stubs` as unmodelled — which is
a failure of the check, because a gate that could not model the thing has not
cleared it. `test_nothing_real_runs_under_the_stub_harness` is the proof.

That one executed rule subsumes OR_LIST, NONZERO_EXIT, CONDITION and
DISABLES_ERREXIT: it rejects `|| true`, `|| :`, `|| { echo; exit 0; }`,
`if ! cmd; then echo; fi`, `if cmd; then ok; else warn; fi`, `while ! cmd; do`,
`set +e`, `trap 'exit 0' ERR` and a swallow behind a shell function, while
accepting the real workflows' `cmd || { echo '::error::...'; exit 1; }`. The
textual rules are kept as a cheap second net, and they earn their place: the
executed rule cannot see past a `$(...)`, a pipeline element, or a subshell,
and `unguarded_or_branches` catches `( cmd ) || true` where execution does not.
Where the two disagree, both are still run, and either one rejecting is a
rejection.

The known holes are written down rather than hoped about, in
`test_the_disclosed_holes_in_the_swallow_rule_are_real` and
`test_the_disclosed_holes_in_the_narrowing_rule_are_real`. Both assert the hole
is exactly as open as the sentence says, so closing one turns the file red and
the sentence gets rewritten rather than outliving the fix. A hole nobody wrote
down is a hole the next round rediscovers by being defeated through it.

Three of the rules below were changed by being attacked after they were
written rather than by being reasoned about: the secrets rule gained the
expression form after `${{ secrets }}` — no dot, no bracket, no paren — walked
past it; the pipefail rule gained an anchor and quote-blanking after a first
line of `echo 'set -o pipefail'` satisfied it over a block that set nothing;
and the narrowing rule gained `--override-ini`/`-o` and a token rule for
PYTEST_ADDOPTS written from the shell, after both got a full pass.

ROUND FOUR: THE RULES WERE ALL ABOUT ONE STEP AT A TIME
-------------------------------------------------------
Every rule above reads one step, or one line, or one mapping. None of them read
the JOIN between two steps, and none of them asserted that a step exists at all.
So the whole evidence chain was unpinned at both ends and in the middle:

* nothing compared the `--junit-xml=` value pytest is given with the path the
  gate step is handed, so the gate could be pointed at a tracked fixture — and
  a hand-written junit of a few passing testcases really does make the gate exit
  0, with no suite having run;
* nothing forbade a step BETWEEN them writing that path. `cp fixtures/green.xml
  "$RUNNER_TEMP/junit.xml"` is a legal step with no secret, no swallow, no
  narrowing flag and no pipeline in it: a full pass on every rule this file had;
* nothing asserted a suite step or a gate step is PRESENT. Deleting the gate
  step outright was a full pass, because every rule here is a loop and a loop
  over a step that is gone inspects nothing;
* nothing stopped the whole job being replaced by `uses:` on a reusable
  workflow, which moves every run block out of this file's reach at once.

`check_the_gate_reads_the_evidence_this_run_wrote` and
`check_the_suite_and_the_gate_are_both_present` close those, and the corpus-level
half — both ends vanishing together — is counted by `missing_subjects`.

The same round found `swallow_findings` grading a shell the workflow does not
use: nothing read `shell:` at any level, so `shell: bash {0}` (bash WITHOUT the
`-e`), `shell: pwsh`, and a `defaults.run.shell` at job or workflow level were
all full passes over an executed rule that assumes `bash -e`.

And two swallows that contain no swallow punctuation: process substitution
(`tee out < <(gate)` — a pipeline with no pipe character, invisible to PIPELINE
and to the pid probe alike) and a backgrounded gate (`gate & wait`, measured
exit 0 under `bash -e` where the bare gate exits 1). The background fix follows
this file's rule about mechanism over spelling: the stub for a failing command
now writes a SECOND log with no pid test in it, so the executed rule sees the
failure wherever it happened, while the pid test stays as the discriminator that
keeps `echo "$(head -n 1 f)"` exempt.

Two of this round's fixes ARE textual construct bans — `PROCESS_SUBSTITUTION`
and `ASYNC_LAUNCHER` — and they are labelled as such rather than dressed up as
something stronger. Process substitution is banned outright because no shell
option propagates its status, so there is nothing to demand beside it; the
launcher ban is an enumeration and the disclosure test says which launchers it
does not name. Where a gap could not be closed cheaply and honestly it is
written into a disclosure test instead of into a docstring's promise:
`test_the_disclosed_holes_in_the_evidence_chain_are_real` is the new one.

ROUND FOUR: A GREEN REQUIRED CHECK IS NOT EVIDENCE THAT ANYTHING RAN.
---------------------------------------------------------------------
Four more full passes, every one of them measured against this file at 4454b20
rather than imagined, and all four are the same question answered badly: this
file asked whether the workflow SAYS the right things, and none of it asked
whether the job runs, whether the suite runs, or whether the gate runs.

* `needs:` IS `if: false` REWORDED. `check_no_condition_disables_the_chain`
  reads `if:` and nothing else, so a `prep` job carrying `if: false` and a
  one-line `needs: prep` on the tests job passed every rule in this file —
  measured at 4454b20,
  and it is the half of this that WAS measured. The other half is cited and not
  measured, because nothing inside a repository can observe its own branch
  protection: GitHub's troubleshooting guidance for required status checks
  states that a CONDITIONALLY skipped check reports Success, where a
  path-filtered one stays pending forever. Taken together the required check is
  green with no suite behind it.
  `check_no_job_can_be_skipped_into_a_pass` refuses `needs`, `strategy` and
  `if` on every job in both files.
* THE SUITE LINE WAS A BLOCKLIST. Every rule about the pytest invocation
  enumerated flags that NARROW the run. `--version`, `-h` and `--help` narrow
  nothing — they replace the run: each exits 0, collects nothing and writes no
  junit at all (measured, pytest 9.1.1, with `--junit-xml` on the same line).
  Point the junit inside the checkout, commit a file of passing testcases at
  that path, and the gate grades the committed file while `git status
  --porcelain` stays empty. `check_the_suite_line_carries_only_whitelisted_
  arguments` is a WHITELIST — `-q`, `-rs`, one junit path under `$RUNNER_TEMP`,
  nothing else — and `check_the_suite_runs_as_a_whole_command` pins the words in
  FRONT of `pytest`, which no rule read until a `:` and a `PYTEST_PLUGINS=`
  assignment were each put into the real tests.yml at 5072f97 and left every
  test in this module passing.
* THE GATE WAS PINNED BY SUBSTRING. A run line had only to CONTAIN
  `check_test_results.py` and the junit path, so `: python
  scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"` — the no-op builtin
  in command position — was a full pass on every rule while the gate never
  executed. It is now pinned as a whole command, AND the stub harness records
  the arguments of every top-level invocation so
  `test_the_gate_step_is_executed_and_not_merely_written` can observe the
  interpreter being entered with the script rather than read a line about it.
* `python -m` PREFERS THE CHECKOUT. A tracked `pytest.py` at the root is the
  module `-m` finds: measured, `raise SystemExit(0)` in one made
  `python -m pytest -q` exit 0 with nothing collected, and the same tree under
  `PYTHONSAFEPATH=1` ran the whole suite. The suite step now declares that
  variable and `check_the_suite_step_takes_the_checkout_off_the_path` requires
  it; the tracked half of the family is refused by name in
  `tests/test_the_guards_exist.py`.

THE SELF-REGRESSION SUITE
-------------------------
Every rule used to be parametrised over the two real workflows only, which
proves those two files do not trip the rules and proves nothing whatsoever
about whether the rules can fire. A linter nobody has watched fail is a linter
that might not work. So each rule is a `check_*` function, and the bottom half
of this file runs those functions over deliberately-broken workflows written to
`tmp_path` and asserts they REJECT. `GOOD_WORKFLOW` is the control: it passes
every check, and every bad case is that same text with one anchored
substitution, so a rejection can only have come from the substitution.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = PROJECT_ROOT / ".github" / "workflows"

#: The GitHub secret's name and the variable the provider code actually reads.
#: Neither may be bound into an `env:` anywhere in CI. tests.yml's suite must
#: pass without either, and that is what proves no test needs a live provider.
CREDENTIAL_NAMES = frozenset({"NCAAF_ODDS_API_KEY", "FOOTBALL_ODDS_API_KEY"})

#: The `secrets` CONTEXT being reached into, in any spelling GitHub accepts.
#: This has now been narrowed twice by being written as one punctuation mark:
#: first the bare substring "secrets.", which the documented and equivalent
#: `${{ secrets['NAME'] }}` walked straight past; then `secrets` followed by a
#: dot or a bracket, which `${{ toJSON(secrets) }}` walked past in turn — and
#: that one is strictly worse than the attack that was caught, because it
#: interpolates EVERY secret in the repository into one env var and thence into
#: any log. GitHub's contexts are also case-insensitive, and this pattern was
#: not.
#:
#: So the character class is now every punctuation mark that can follow the
#: context word when the context is being USED — dot, bracket, closing paren —
#: and the match is case-insensitive. Prose stays legal because prose writes the
#: word and then a space, a backtick or a letter;
#: `test_the_secret_accessor_pattern_ignores_prose` pins that direction and
#: `test_the_whole_secrets_context_cannot_be_interpolated` pins the other.
#:
#: Checked against the raw text rather than the parse on purpose: it catches a
#: reference inside a comment too, and a commented-out credential is one
#: uncomment away from a live one. `secrets:` as a YAML KEY is a different
#: thing in a different place and has a rule of its own —
#: `check_no_workflow_declares_a_secrets_key`.
SECRET_REFERENCE = re.compile(r"(?i)\bsecrets\s*[.\[)]")

#: The other half of the same guarantee, and the one that does not depend on
#: punctuation at all: the context word appearing ANYWHERE inside a `${{ }}`
#: expression. `${{ secrets }}` on its own is followed by neither a dot nor a
#: bracket nor a paren, and it renders the whole object; so does
#: `${{ format('{0}', secrets) }}`. Prose is untouched because prose is not
#: inside an expression, which is what makes this the accessor rule rather than
#: a rule about the word.
GITHUB_EXPRESSION = re.compile(r"(?s)\$\{\{.*?\}\}")
SECRETS_WORD = re.compile(r"(?i)\bsecrets\b")

#: A shell or-list, and not the `|||` that cannot occur or the single `|` of a
#: pipeline.
OR_LIST = re.compile(r"\|\|(?!\|)")

#: `exit` with a status that fails the step. `exit 0` and `exit 00` are both
#: absent from this by construction. Searched per or-list BRANCH by
#: `unguarded_or_branches`, never over a whole line: an `exit 1` belonging to
#: some other command on the same line is not this branch's exit.
NONZERO_EXIT = re.compile(r"\bexit\s+[1-9]")

#: A SEGMENT whose `||` is joining two TESTS rather than guarding a command —
#: `if [ -n "$A" ] || [ -n "$B" ]; then`. The or-list there decides a branch; it
#: does not swallow anything, and the branch itself carries the `exit 1`.
#:
#: Anchored at the start of a segment, not searched over a line. The line-wide
#: version of this pattern was an exemption you could claim by writing
#: `; then` anywhere on the line, which is how a `|| true` got a full pass. The
#: shapes it exempts are still executed by `swallow_findings`, so the exemption
#: buys nothing: `if cmd || true; then ...; fi` is rejected by running it.
CONDITION = re.compile(r"^\s*(?:if|elif|while|until)\b")

#: `set +e`, and every synonym for it that turns off the shell option protecting
#: the step. Two spellings got past the previous alternation: it matched the
#: LETTER `e` and the option name `errexit`, but not the option name `pipefail`
#: — so `set +e` was rejected while `set +o pipefail`, which is the same defeat
#: for the pipeline case, was allowed. A flag banned in one spelling and allowed
#: in another is not banned.
DISABLES_ERREXIT = re.compile(
    r"\bset\b[^;&|]*\+(?:[a-z]*e[a-z]*\b|o\s+(?:errexit|pipefail)\b)"
)

#: `set -o pipefail` being turned ON, and the same thing being turned back OFF.
#: The pipefail rule used to read `lines[0]` and stop, so a block could open
#: with `set -euo pipefail`, satisfy the rule, and write `set +o pipefail` two
#: lines down over the pipeline that mattered. ENABLES_PIPEFAIL also refuses to
#: accept `set +o pipefail` as an opening line, which the old `"pipefail" in
#: first` substring test would have.
#:
#: ENABLES_PIPEFAIL is anchored to the START of the line, not searched in it:
#: unanchored, a first line reading `echo 'set -o pipefail'` satisfied the rule
#: over a block that never set the option. Both patterns are applied to the
#: line with its quoted spans blanked, for the same reason in reverse — a
#: workflow that prints an explanation of the rule must not trip it.
ENABLES_PIPEFAIL = re.compile(r"^\s*set\b[^;&|]*-[a-zA-Z]*o\s+pipefail\b")
DISABLES_PIPEFAIL = re.compile(r"\bset\b[^;&|]*\+o?\s*pipefail\b")

#: A single `|` and not the `||` of a shell or-list. GitHub's default shell is
#: `bash -e {0}` — errexit but NOT pipefail — so `failing | tee` reports tee's
#: zero and the step goes green.
PIPELINE = re.compile(r"(?<!\|)\|(?!\|)")

#: Process substitution: `<(cmd)` and `>(cmd)`. A pipeline with no pipe
#: character in it, so PIPELINE cannot see it — and the command inside runs in a
#: subshell whose status the stub preamble's pid probe cannot attribute to the
#: top level either, so the executed rule cannot see it either. It was a full
#: pass on both nets at once.
#:
#: Rejected OUTRIGHT rather than conditioned on a shell option, because there is
#: no option that propagates it: `set -o pipefail` covers pipelines and does not
#: cover this, and errexit never sees a subshell's failure. That is a ban on the
#: capability, not on the spelling — `<`, `>`, any command inside, any
#: surrounding redirection. The cost is that a legitimate `diff <(a) <(b)` is
#: rejected too, and that conservatism is recorded in
#: `test_the_disclosed_holes_in_the_swallow_rule_are_real` rather than argued
#: away.
PROCESS_SUBSTITUTION = re.compile(r"[<>]\(")

#: A background operator: a single `&` that is not the `&&` of an and-list, not
#: the `&` of `>&` / `2>&1`, and not the `&` of `&>`.
#:
#: `gate &` is a swallow with no swallow operator anywhere in it. errexit does
#: not apply to an asynchronous command, and `wait` with no argument returns 0
#: whatever the job did, so `gate & wait` reports success over a failed gate.
#: Measured under `bash -e` with a failing stub: the backgrounded form exits 0
#: where the bare gate exits 1. The round-two failure mode was rejecting the
#: spelling that ADDS an operator while allowing the one that removes it, so the
#: executed rule grew a matching arm (`swallow_findings` reads a second failure
#: log with no pid test) and this pattern is the second belt beside it.
BACKGROUND = re.compile(r"(?<![&>])&(?![&>])")

#: The same capability reached without the operator. `setsid gate` forks and
#: returns 0 the moment the child is detached, so errexit has nothing to see;
#: `coproc gate` runs the gate in a subshell whose status the block never
#: consults. Found by attacking `BACKGROUND` after it was written, which is how
#: every rule in this file that survived a round was found.
#:
#: This one IS a rule about spellings, and it is labelled as one rather than
#: dressed up: `&` is banned by mechanism (the executed rule reads a second
#: failure log and does not care how the fork happened), and these two are the
#: named launchers on top. A launcher this file does not name — `systemd-run`,
#: `at`, a wrapper script that forks — still gets through, and
#: `test_the_disclosed_holes_in_the_swallow_rule_are_real` says so.
ASYNC_LAUNCHER = re.compile(r"\b(?:setsid|coproc)\b")

#: A physical line that bash will continue onto the next one. The backslash is
#: the one that hid arguments from this file for a whole round; the operators
#: are here because `foo ||` / `foo &&` / `foo |` at end of line continue too,
#: and a rule that scanned the fragments separately would see neither the
#: command nor its guard.
CONTINUATION = re.compile(r"(?:\\|\|\||&&|\|)$")

#: pytest flags that stop the run early or narrow it. The junit file is the
#: evidence that the gate ran over everything, and a partial run cannot account
#: for the tests it never reached.
#:
#: `--exitfirst` and `--ignore-glob` are in this set because a flag banned in
#: its short spelling and allowed in its long one is not banned: `-x` was
#: rejected here while `--exitfirst`, pytest's own documented alias for it,
#: passed, and `--ignore` was rejected while `--ignore-glob` passed.
#:
#: `--override-ini`, `--config-file` and `--confcutdir` are in this set for a
#: different reason from the rest, and it is the same reason for all three:
#: none of them selects anything, they RECONFIGURE pytest — and one of the
#: things that configuration decides is `testpaths`, which is exactly a
#: selection when the command line carries no positional. `--config-file=ci.ini`
#: hands pytest a different ini file wholesale, so it is `--override-ini` with
#: no key to name; `--confcutdir` moves the boundary pytest stops looking for
#: conftest.py above, and a conftest that is no longer loaded is a collection
#: hook that no longer runs.
#:
#: This was measured rather than reasoned about: pointing `-c` at a second ini
#: file narrowed what a real pytest run in this repository collected, and the
#: junit file that run wrote agreed with itself — the evidence file records the
#: tests that ran, never the ones the configuration removed, so no downstream
#: gate can notice. `-o` and `-c` are the short spellings and are banned in
#: NARROWING_PYTEST_SHORT_FLAGS, because a flag banned in one spelling and
#: allowed in another is not banned.
#:
#: `--runxfail` is here for a third reason, and it is the one CLAUDE.md names
#: as sorted into no category by any rule: it does not narrow the run at all, it
#: DISARMS the gate. Measured in a sandbox holding a single strict-xfail test,
#: one run each way: without it pytest exits non-zero and the junit records the
#: xpass as a failure, which is what `scripts/check_test_results.py` catches;
#: with it the marker goes inert, pytest exits 0 and the junit records an
#: ordinary passing testcase with no child element — indistinguishable from a
#: real pass to any reader of that file. The suite is not smaller and the
#: evidence is not missing; the evidence is wrong, which is worse. A flag that
#: makes the junit unable to account for the suite belongs in this set whether
#: it shrinks the run or launders it.
#:
#: `--rootdir` is deliberately NOT here, and it was measured rather than
#: assumed: pointed at a subdirectory of a sandbox whose ini sets `testpaths`,
#: it collected the same tests as the run without it. It changes where pytest
#: thinks the root is, not what pytest collects, so banning it would be a rule
#: rejecting a correct command line — which is how rules get deleted.
NARROWING_PYTEST_LONG_FLAGS = frozenset(
    {
        "--maxfail",
        "--ignore",
        "--ignore-glob",
        "--deselect",
        "--exitfirst",
        "--override-ini",
        "--config-file",
        "--confcutdir",
        "--runxfail",
    }
)

#: The same class of alias, found by reading `pytest --help` (pytest 9.1.1) for
#: every option that ends the run early or picks a subset, rather than by
#: recalling the ones somebody had been bitten by:
#:   `--collect-only, --co`        collects the suite and executes none of it
#:   `--last-failed, --lf`         runs only what failed last time
#:   `--stepwise, --sw`            stops at the first failure
#:   `--stepwise-skip, --sw-skip`  implicitly enables --stepwise
#:   `--stepwise-reset, --sw-reset`  restarts the stepwise workflow, and so
#:                                 enables it: the run still stops early
#: The enumeration above is the set below, and both are the parametrisation of
#: `test_a_narrowing_pytest_flag_is_rejected`; a flag named in one and missing
#: from another is the shape that let `--exitfirst` through.
#: `--failed-first`/`--ff` is deliberately NOT here: it reorders the run and
#: still runs everything.
NARROWING_PYTEST_ALIAS_FLAGS = frozenset(
    {
        "--collect-only",
        "--co",
        "--last-failed",
        "--lf",
        "--stepwise",
        "--sw",
        "--stepwise-skip",
        "--sw-skip",
        "--stepwise-reset",
        "--sw-reset",
    }
)

#: `-x`, `-k`, `-m`, `-o` and `-c` matched as letters inside a short-option
#: cluster, so `-xq` is caught too — and so is `-qcci.ini`, where the config
#: file is clustered behind an accepted flag and the argument is glued to the
#: letter. The sweep of `pytest --help` that produced the alias set above found
#: NO long spelling for `-k` or `-m` — they are declared short-only — so for
#: those two the cluster check is the whole rule; `-o` is the short spelling of
#: `--override-ini` and `-c` of `--config-file`, both of which are in the long
#: set.
NARROWING_PYTEST_SHORT_FLAGS = frozenset("xkmoc")

#: pytest reads this as if the flags had been typed, so every rule that reads
#: the command line sees a clean invocation over a narrowed run. It is checked
#: three ways, because there are three places it can be set and only one of them
#: is an `env:` mapping: as a key at any level, as a token in any run block —
#: `export PYTEST_ADDOPTS=-x` — and as a token written into `$GITHUB_ENV`, which
#: sets it for every LATER step and appears in no mapping at all. This is a
#: token rule rather than a spelling rule: PYTEST_ADDOPTS is the exact name
#: pytest reads and it has no synonym, so the name IS the thing.
PYTEST_ADDOPTS = "PYTEST_ADDOPTS"
PYTEST_ADDOPTS_TOKEN = re.compile(r"(?i)\bPYTEST_ADDOPTS\b")

#: The gate script's file name. The evidence chain is: pytest writes a junit
#: file, and this script reads THAT file and exits non-zero on a skip, an xfail,
#: a missing guard module or an empty run. Every rule above reads one end of
#: that chain or the other and NOTHING pinned them together, so all of these
#: were full passes on every rule in CHECKS at once:
#:
#:   * a step between the two that overwrites the junit path with a tracked
#:     fixture (`cp fixtures/green.xml "$RUNNER_TEMP/junit.xml"`);
#:   * the gate pointed at a path pytest never wrote;
#:   * the gate step deleted outright;
#:   * the whole job replaced by `uses:` on a reusable workflow, which moves
#:     every run block out of this file's view.
#:
#: A hand-written junit with a handful of passing testcases and nothing else in
#: it really does make the gate exit 0, so none of these needs the suite to have
#: run at all.
GATE_SCRIPT = "check_test_results.py"

#: Both spellings pytest accepts for the junit path, and the separated form of
#: each (`--junit-xml FILE`) is read as well as the `=` form. A flag read in one
#: spelling and not another is a flag that can be written the other way.
JUNIT_FLAGS = frozenset({"--junit-xml", "--junitxml"})

#: `${NAME}` and `$NAME` are the same variable to bash, so the evidence rule
#: compares paths with the braces removed. The negative lookahead is the whole
#: point of doing it with a pattern rather than a `strip`: `${RUNNER_TEMP}x` and
#: `$RUNNER_TEMPx` name DIFFERENT variables, and collapsing them would let two
#: unrelated paths compare equal.
BRACED_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}(?![A-Za-z0-9_])")

#: Tokens that end one command and begin another. `shlex.split` hands these back
#: as ordinary words, so the argument scan stops at the first one rather than
#: reading the next command's words as this command's arguments.
SHELL_OPERATOR_TOKENS = frozenset(
    {"|", "||", "&&", "&", ";", ";;", ">", ">>", "<", "<<", "2>", "&>", "(", ")"}
)

#: Characters that end the command whose arguments are being read. The argument
#: scan stops at the first one outside quotes, so `gate.py "$X"; } &` reports
#: `$X` and not `$X;` — a path that would then compare unequal to the one pytest
#: wrote and produce a rejection for the wrong reason.
COMMAND_TERMINATORS = frozenset(";|&<>(){}\n")

#: Values GitHub accepts for `shell:` that leave the block running under the
#: shell every executed rule in this file grades it under. Everything else is
#: rejected, and the test is STRUCTURAL rather than textual: a value carrying
#: whitespace is a custom command line, whatever it spells. `bash {0}` is the
#: one that matters most — it is the documented way to write "bash, my own
#: arguments" and it drops the `-e` that GitHub's own default supplies, so every
#: `swallow_findings` verdict in this file would be about a shell the workflow
#: does not use.
SAFE_SHELLS = frozenset({"bash", "sh"})


def workflow_files_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


WORKFLOW_FILES = workflow_files_in(WORKFLOWS_DIR)

#: Parametrised by file so a red tick names the workflow that broke the rule.
#: With no workflows the parameter set is empty and every one of these collects
#: nothing — which `test_the_workflow_directory_is_not_empty` is what catches.
every_workflow = pytest.mark.parametrize(
    "path", WORKFLOW_FILES, ids=[path.name for path in WORKFLOW_FILES]
)


def load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(document: Any) -> Any:
    """The `on:` block, whichever of its two keys it landed under.

    Bare `on` is a YAML 1.1 boolean, so `yaml.safe_load` files it under the key
    `True`; tests.yml quotes it and lands under `"on"`. GitHub reads the two
    identically, so a check that knew only one of them would silently pass
    every workflow written the other way.
    """
    if isinstance(document, dict):
        if "on" in document:
            return document["on"]
        if True in document:
            return document[True]
    return None


def mappings(node: Any) -> Iterator[dict]:
    """Every mapping in the document, at any depth.

    The rules below are about placement as much as content — a `permissions:`
    or an `env:` is just as dangerous on a job or a step as at the top — so
    they are checked everywhere rather than at the levels somebody remembered.
    """
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from mappings(value)
    elif isinstance(node, list):
        for item in node:
            yield from mappings(item)


def steps_using(document: Any, action: str) -> Iterator[dict]:
    for mapping in mappings(document):
        uses = mapping.get("uses")
        if isinstance(uses, str) and uses.split("@", 1)[0] == action:
            yield mapping


def run_blocks(document: Any) -> Iterator[tuple[str, str]]:
    for mapping in mappings(document):
        command = mapping.get("run")
        if isinstance(command, str):
            yield str(mapping.get("name", "<unnamed step>")), command


def commands(block: str) -> list[str]:
    """The LOGICAL lines of a run block that bash will actually execute.

    Comment lines are dropped. They carry pipes, the word pytest and the very
    constructs these rules ban, because the comments explain the rules —
    matching them would make the prose that documents a gate the thing that
    trips it.

    Continuations are joined, and that is the load-bearing part. This returned
    physical lines until an audit pointed out that `pytest \\` on one line and
    `-k slow` on the next hid the `-k` from every rule in this file — while
    ledger-guard.yml writes its own commands in exactly that shape, so the
    idiom is the house style rather than an exotic input. A line ending in a
    backslash, `||`, `&&` or `|` continues onto the next one; the backslash is
    dropped because bash drops it, and the operators are kept because they are
    part of the command.
    """
    joined: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if joined and CONTINUATION.search(joined[-1]):
            previous = joined[-1]
            if previous.endswith("\\"):
                previous = previous[:-1].rstrip()
            joined[-1] = f"{previous} {line}"
        else:
            joined.append(line)
    # A backslash with nothing after it (end of block, or only comments after)
    # is what bash drops on the floor, so drop it here too rather than leaving
    # it dangling on the end of a line every downstream regex has to read.
    return [
        line[:-1].rstrip() if line.endswith("\\") else line for line in joined
    ]


# --------------------------------------------------------------------------
# The stub harness: the swallow rule stops reading shell and starts running it.
#
# Everything below writes a run block into a sandbox directory, replaces every
# command it invokes with a shell function of known exit status, and executes
# it under `bash -e` — which is exactly the shell GitHub runs a `run:` block
# with (`bash -e {0}`). The verdict is the process exit code, not a regex.
# --------------------------------------------------------------------------

#: The shell the harness runs blocks under, and the one it uses to read back a
#: subshell's real pid. Absent, every executed rule FAILS rather than passing
#: quietly: absence is never a pass.
HARNESS_SHELL = shutil.which("bash")

#: Words bash treats as syntax. Defining a function named `for` is a syntax
#: error, so these are never stubbed — and none of them is a command whose exit
#: status the harness needs to control.
SHELL_KEYWORDS = frozenset(
    {
        "if", "then", "else", "elif", "fi", "for", "while", "until", "do",
        "done", "case", "esac", "in", "function", "select", "time", "coproc",
        "!", "{", "}", "[[", "]]",
    }
)

#: Builtins the harness deliberately leaves alone. A function shadows a builtin
#: in bash, so stubbing `true`, `:` or `test` would make `cmd || true` LOOK
#: like a failure path and the swallow would pass. Keeping the builtins real is
#: what makes `|| true` and `|| printf ''` come out as exit 0.
SHELL_BUILTINS = frozenset(
    {
        "set", "unset", "exit", "return", "echo", "printf", "test", "[", "]",
        ":", "true", "false", "cd", "pwd", "read", "eval", "exec", "export",
        "local", "shift", "trap", "source", ".", "wait", "break", "continue",
        "declare", "typeset", "let", "mapfile", "readarray", "alias",
        "unalias", "bind", "builtin", "caller", "command", "compgen",
        "complete", "dirs", "disown", "enable", "fc", "fg", "bg", "getopts",
        "hash", "help", "history", "jobs", "kill", "logout", "popd", "pushd",
        "readonly", "suspend", "times", "type", "ulimit", "umask", "shopt",
    }
)

#: A command word the harness can safely define a bash function for. `/bin/true`
#: is in scope on purpose — bash accepts a function name containing slashes, and
#: an absolute path is the one command word an empty PATH would NOT stop from
#: running for real.
STUB_SAFE_NAME = re.compile(r"^[A-Za-z_./][A-Za-z0-9_./+-]*$")

#: `NAME=value` in command position is a prefix assignment, not a command, and
#: the word after it is still the command.
PREFIX_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")

#: bash's own report that a command word reached the shell with no stub behind
#: it. With PATH pointed at an empty directory this is the only way an unstubbed
#: simple command can end up, and the harness treats it as "this block was not
#: modelled" rather than as a result.
COMMAND_NOT_FOUND = re.compile(r"[:\s]([^:\s]+): command not found")

#: Variables the runner provides. Bound to real paths inside the sandbox so a
#: block that writes to `$GITHUB_STEP_SUMMARY` behaves the way it does in CI
#: rather than dying on a redirection and being accepted for the wrong reason.
RUNNER_FILE_VARIABLES = (
    "GITHUB_STEP_SUMMARY",
    "GITHUB_OUTPUT",
    "GITHUB_ENV",
    "GITHUB_PATH",
)

#: `${VAR}` / `$VAR` with no default, and the same with one. A block under
#: `set -u` dies on an unbound variable, and a block that died before reaching
#: its swallow would be accepted having proved nothing — so referenced
#: variables are bound. Ones written `${VAR:-}` are LEFT unbound, because empty
#: is what they are in CI and binding them would take a different branch: bind
#: `${NCAAF_ODDS_API_KEY:-}` and tests.yml's suite step exits at its own
#: credential assertion without ever reaching the command under test.
VARIABLE_WITH_DEFAULT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\s*:?[-=+?]")
VARIABLE_BRACED = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")
VARIABLE_BARE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _uncommented(block: str) -> str:
    return "\n".join(
        line for line in block.splitlines() if not line.strip().startswith("#")
    )


def _shell_regions(text: str) -> list[str]:
    """The text with `$(...)` and backtick spans lifted out, plus those spans.

    A command inside a substitution is still a command that runs, so it is
    still a command the harness has to stub — `test -z "$(git status)"` is one
    of the shapes the real workflows use, and an unstubbed `git` there would be
    a command the sandbox did not model. Single quotes are opaque; double
    quotes are not, because a substitution inside them still executes.
    """
    outer: list[str] = []
    inner: list[str] = []
    index, size = 0, len(text)
    while index < size:
        character = text[index]
        if character == "'":
            close = text.find("'", index + 1)
            close = size if close < 0 else close
            outer.append(text[index : close + 1])
            index = close + 1
            continue
        if character == "\\":
            outer.append(text[index : index + 2])
            index += 2
            continue
        if text.startswith("$(", index):
            depth, cursor = 1, index + 2
            while cursor < size and depth:
                if text[cursor] == "'":
                    close = text.find("'", cursor + 1)
                    cursor = (size if close < 0 else close) + 1
                    continue
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == "(":
                    depth += 1
                elif text[cursor] == ")":
                    depth -= 1
                cursor += 1
            inner.append(text[index + 2 : max(cursor - 1, index + 2)])
            outer.append(" ")
            index = cursor
            continue
        if character == "`":
            close = text.find("`", index + 1)
            close = size if close < 0 else close
            inner.append(text[index + 1 : close])
            outer.append(" ")
            index = close + 1
            continue
        outer.append(character)
        index += 1
    regions = ["".join(outer)]
    for span in inner:
        regions.extend(_shell_regions(span))
    return regions


def _scan_command_words(region: str, found: list[str]) -> None:
    current: list[str] = []
    quote: str | None = None
    at_command, skip_next = True, False
    index, size = 0, len(region)

    def flush() -> None:
        nonlocal current, at_command, skip_next
        token = "".join(current)
        current = []
        if not token:
            return
        if skip_next:
            skip_next = False
            return
        if not at_command:
            return
        if token in SHELL_KEYWORDS or PREFIX_ASSIGNMENT.match(token):
            return
        at_command = False
        if token in SHELL_BUILTINS or re.fullmatch(r"[0-9]+", token):
            return
        if "$" in token or "*" in token or "?" in token:
            return
        if token not in found:
            found.append(token)

    while index < size:
        character = region[index]
        if quote is not None:
            if character == quote:
                quote = None
            elif quote == '"' and character == "\\":
                index += 1
            current.append(character)
            index += 1
            continue
        if character in "'\"":
            quote = character
            current.append(character)
            index += 1
            continue
        if character == "\\":
            index += 2
            continue
        if character in "<>":
            # A redirection target is not a command, and `>/dev/null` used to be
            # collected as one.
            flush()
            skip_next = True
            index += 1
            continue
        if character == "\n" or character in ";|&(){}`":
            flush()
            at_command, skip_next = True, False
            index += 1
            continue
        if character.isspace():
            flush()
            index += 1
            continue
        current.append(character)
        index += 1
    flush()


def command_words(block: str) -> list[str]:
    """Every word this block would invoke as a command, in order of appearance.

    Over-collection is safe and under-collection is not, so the scanner errs
    towards more: a word collected that never runs becomes an unused shell
    function, while a word missed becomes a command the sandbox cannot control.
    `run_block_under_stubs` closes that gap from the other side by reporting
    anything that reached the shell without a stub.
    """
    found: list[str] = []
    for region in _shell_regions(_uncommented(block)):
        _scan_command_words(region, found)
    return found


def referenced_variables(block: str) -> list[str]:
    named = set(VARIABLE_BRACED.findall(block)) | set(VARIABLE_BARE.findall(block))
    return sorted(named - set(VARIABLE_WITH_DEFAULT.findall(block)))


def _quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def stub_preamble(
    words: list[str],
    failing: set[str] | None,
    failure_log: Path,
    any_failure_log: Path,
    unmodelled_log: Path,
    marker: Path,
    invocation_log: Path | None = None,
) -> str:
    """The shell that turns each command word into a function of known status.

    Each stub is written out in full rather than delegating to a shared helper,
    and that is not a style choice: with a helper in the middle the stub runs
    one function frame deeper, and bash does not inherit an ERR trap into a
    nested frame without `set -E`. Written flat, `trap 'exit 0' ERR` — a
    swallow with no `||` anywhere in it — is caught. Written nested, it was not.
    Measured both ways before this shape was chosen.

    A stub records itself in `failure_log` only when it failed AND it ran in the
    top-level shell. The pid comparison is how it tells: `$$` is the script's
    pid everywhere, while re-execing a shell reports its own parent, which is
    the shell that actually forked it. A command inside `$(...)` or a pipeline
    element runs in a subshell whose failure errexit never sees, and counting
    those would reject `echo "$(head -n 1 f)"` — a real step's summary line —
    as a swallowed failure.

    It records itself in `any_failure_log` whenever it failed, pid test or not.
    That second log is what sees a BACKGROUNDED failure: `gate &` runs the stub
    in a forked subshell, so the pid test excludes it from `failure_log` exactly
    as it excludes a substitution — and `gate & wait` was therefore a full pass
    on the executed rule, measured exit 0 under `bash -e` where the bare gate
    exits 1. `swallow_findings` uses the two logs together: the pid test stays
    the discriminator that keeps `echo "$(head -n 1 f)"` exempt, and the second
    log only becomes a finding when the block also carries a background
    operator.

    Every stub also prints a marker, so a command substitution has output. A
    silent stub makes `test -z "$(cmd)"` true, which is the opposite of what a
    failing command does and would turn a real failure path into a green line.

    `invocation_log` records the ARGUMENTS of every top-level call, which is
    what `check_the_gate_is_executed_and_not_merely_written` reads. The word
    alone is not enough for that rule: `: python scripts/check_test_results.py
    "$RUNNER_TEMP/junit.xml"` contains the gate's word, its script and its path,
    passes every rule that reads the line as text, and runs nothing — `:` is a
    builtin the harness deliberately leaves real, so it consumes the whole
    command and the gate's own stub is never entered. Only a log of what was
    actually invoked, with what, can tell the two lines apart.
    """
    assert HARNESS_SHELL, "no bash on PATH: the executed swallow rule cannot run"
    lines = [
        # bash >= 4 hands an unfound command here; older bash reports it on
        # stderr instead and COMMAND_NOT_FOUND reads that. Both feed the same
        # "not modelled" verdict.
        "command_not_found_handle() { printf '%s\\n' \"$1\" >> "
        + _quote(str(unmodelled_log))
        + "; return 127; }",
        # PATH is the empty directory the harness pointed it at, and a block
        # must not be able to point it back at a real one. Without this,
        # `PATH=/usr/bin; something` would run something.
        "readonly PATH",
    ]
    for word in words:
        status = 1 if (failing is None or word in failing) else 0
        body = ["%s() {" % word]
        if invocation_log is not None:
            # Recorded with the same pid test the failure log uses, so a call
            # made inside `$(...)`, a pipeline element or a background job is
            # not counted as the top-level invocation the gate rule demands.
            body.append(
                '  __INVOKE_PID="$( exec %s -c \'echo $PPID\' )"'
                % _quote(HARNESS_SHELL)
            )
            body.append(
                '  if [ "$__INVOKE_PID" = "$$" ]; then printf \'%s %s\\n\' '
                + _quote(word)
                + ' "$*" >> '
                + _quote(str(invocation_log))
                + "; fi"
            )
        if status:
            # No pid test on this one, deliberately: a failure in a forked
            # subshell is invisible to the log below and a backgrounded gate is
            # exactly that.
            body.append(
                "  printf '%s\\n' "
                + _quote(word)
                + " >> "
                + _quote(str(any_failure_log))
            )
            body.append(
                '  __SWALLOW_PID="$( exec %s -c \'echo $PPID\' )"'
                % _quote(HARNESS_SHELL)
            )
            body.append(
                '  if [ "$__SWALLOW_PID" = "$$" ]; then printf \'%s\\n\' '
                + _quote(word)
                + " >> "
                + _quote(str(failure_log))
                + "; fi"
            )
        body.append("  printf 'stub:%s\\n' " + _quote(word))
        body.append("  return %d" % status)
        body.append("}")
        lines.append("\n".join(body))
    # The last thing the preamble does, so a preamble that died half way through
    # cannot be mistaken for a block that failed honestly.
    lines.append(": > %s" % _quote(str(marker)))
    return "\n".join(lines) + "\n"


class BlockRun(NamedTuple):
    exit_code: int
    top_level_failures: list[str]
    unmodelled: list[str]
    stderr: str
    #: Every stub that failed, wherever it ran — subshell, pipeline element,
    #: command substitution or background job. `top_level_failures` is the
    #: subset errexit could have seen; this is the superset that includes the
    #: ones it could not.
    any_failures: list[str]
    #: `word arg arg ...` for every stub entered in the TOP-LEVEL shell, in
    #: order. Empty for a block whose commands all ran inside a substitution, a
    #: pipeline or a builtin that swallowed them.
    invocations: list[str] = []


def run_block_under_stubs(
    block: str, failing: set[str] | None, sandbox: Path
) -> BlockRun:
    """Execute one run block with every command replaced by a stub.

    `failing` is the set of command words whose stub returns 1; `None` means
    all of them. Nothing real executes: PATH is an empty directory inside the
    sandbox, the working directory is the sandbox, and the environment is built
    from scratch.

    A `:` is appended after the block. Without it a block that ends in a failing
    command exits non-zero whatever it did with the failure, so `set +e` and
    every other "keep going" shape would read as clean. With it, the rule the
    exit code answers is the right one: once a top-level command has failed,
    this block must not reach its end.
    """
    assert HARNESS_SHELL, "no bash on PATH: the executed swallow rule cannot run"
    sandbox = Path(sandbox)
    failure_log = sandbox / "top_level_failures.txt"
    any_failure_log = sandbox / "any_failures.txt"
    unmodelled_log = sandbox / "unmodelled_commands.txt"
    invocation_log = sandbox / "invocations.txt"
    marker = sandbox / "preamble_completed"
    failure_log.write_text("", encoding="utf-8")
    any_failure_log.write_text("", encoding="utf-8")
    unmodelled_log.write_text("", encoding="utf-8")
    invocation_log.write_text("", encoding="utf-8")
    if marker.exists():
        marker.unlink()
    empty_path_dir = sandbox / "empty-path"
    empty_path_dir.mkdir(exist_ok=True)

    words = command_words(block)
    unstubbable = [word for word in words if not STUB_SAFE_NAME.match(word)]
    preamble = stub_preamble(
        [word for word in words if STUB_SAFE_NAME.match(word)],
        failing,
        failure_log,
        any_failure_log,
        unmodelled_log,
        marker,
        invocation_log,
    )
    parsed = subprocess.run(
        [HARNESS_SHELL, "-n"], input=preamble, capture_output=True, text=True
    )
    if parsed.returncode != 0:
        raise RuntimeError(
            "the stub preamble does not parse, so no verdict from it means "
            f"anything: {parsed.stderr}"
        )

    script = sandbox / "run_block.sh"
    script.write_text(preamble + block + "\n:\n", encoding="utf-8")
    environment = {
        # An empty directory rather than an empty string: with PATH unset bash
        # reports "No such file or directory", which is also what a failed
        # redirection says, and the two must not be confused.
        "PATH": str(empty_path_dir),
        "LC_ALL": "C",
        "HOME": str(sandbox),
        "GITHUB_WORKSPACE": str(sandbox),
        "RUNNER_TEMP": str(sandbox),
    }
    for name in RUNNER_FILE_VARIABLES:
        target = sandbox / name.lower()
        target.touch()
        environment[name] = str(target)
    for name in referenced_variables(block):
        environment.setdefault(name, "__harness__")

    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)],
        cwd=sandbox,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not marker.exists():
        raise RuntimeError(
            "the stub preamble did not run to completion, so the exit code "
            f"below is not a verdict on the block: {completed.stderr}"
        )
    unmodelled = sorted(
        set(unstubbable)
        | set(unmodelled_log.read_text(encoding="utf-8").split())
        | set(COMMAND_NOT_FOUND.findall(completed.stderr))
    )
    return BlockRun(
        completed.returncode,
        failure_log.read_text(encoding="utf-8").split(),
        unmodelled,
        completed.stderr,
        any_failure_log.read_text(encoding="utf-8").split(),
        invocation_log.read_text(encoding="utf-8").splitlines(),
    )


def swallow_findings(block: str) -> list[str]:
    """Run the block under every single-failure configuration; report swallows.

    The configurations are: every command fails, and then each command failing
    alone. The second half is not redundant — with everything failing, a block
    stops at its first gate and a swallow further down is never reached, and
    `cmd_a; cmd_b || true` would pass. Failing `cmd_b` alone reaches it.

    Failing one command alone is also the only configuration that can see
    `cmd || /bin/true`: with everything failing, `/bin/true` fails too and the
    or-list looks like a failure path.

    A block carrying a background operator is judged on the SECOND failure log
    as well. `gate &` forks, so the pid test that keeps `echo "$(cmd)"` exempt
    also excluded the backgrounded gate, and the block exited 0 with an empty
    `top_level_failures` — a swallow the executed rule could not see. The pid
    test stays where it is and does the discriminating; the background operator
    is what says this exit code is not to be trusted.
    """
    findings: list[str] = []
    words = command_words(block)
    backgrounded = [
        line
        for line in commands(block)
        if BACKGROUND.search(without_quoted_spans(line))
        or ASYNC_LAUNCHER.search(without_quoted_spans(line))
    ]
    with tempfile.TemporaryDirectory() as directory:
        sandbox = Path(directory)
        for failing in [None] + [{word} for word in words]:
            result = run_block_under_stubs(block, failing, sandbox)
            label = "every command failing" if failing is None else (
                "only %s failing" % ", ".join(sorted(failing))
            )
            if result.unmodelled:
                findings.append(
                    f"with {label}, {result.unmodelled} reached the shell with "
                    "no stub behind it, so this block was never modelled. A "
                    "gate that could not run the thing has not cleared it."
                )
                continue
            if result.exit_code == 0 and result.top_level_failures:
                findings.append(
                    f"with {label}, {sorted(set(result.top_level_failures))} "
                    "failed and the block still exited 0. In CI that is a green "
                    "step over a failed command."
                )
                continue
            if result.exit_code == 0 and backgrounded and result.any_failures:
                findings.append(
                    f"with {label}, {sorted(set(result.any_failures))} failed "
                    f"and the block still exited 0 while running {backgrounded} "
                    "in the background. errexit does not apply to an "
                    "asynchronous command and `wait` with no argument returns "
                    "0, so the step is green over a failed command with no "
                    "swallow operator anywhere in it."
                )
    return findings


def without_quoted_spans(line: str) -> str:
    """The line with every quoted span replaced by spaces of the same width.

    Two rules read this. The or-list rule reads it because
    `echo "gate failed; will exit 1 later"` used to satisfy NONZERO_EXIT with an
    `exit 1` that is a string; the shell-option rules read it because
    `echo 'set -o pipefail'` used to satisfy the pipefail rule over a block that
    never set the option, and because a workflow printing an explanation of the
    `set +e` rule must not be the thing that trips it.
    """
    text: list[str] = []
    index, size = 0, len(line)
    while index < size:
        character = line[index]
        if character == "\\":
            text.append(" ")
            index += 2
            continue
        if character in "'\"":
            cursor = index + 1
            while cursor < size:
                if character == '"' and line[cursor] == "\\":
                    cursor += 2
                    continue
                if line[cursor] == character:
                    break
                cursor += 1
            text.append(" " * (min(cursor, size - 1) - index + 1))
            index = cursor + 1
            continue
        text.append(character)
        index += 1
    return "".join(text)


def _top_level_pieces(line: str) -> list[list[str]]:
    """Segments split on top-level `;` and `&&`, each split on top-level `||`.

    Brace and paren groups keep their depth, so
    `cmd || { echo '...'; exit 1; }` stays ONE segment with the exit inside its
    branch rather than being cut in three by the semicolons.
    """
    blanked = without_quoted_spans(line)
    segments: list[list[str]] = []
    chunks: list[str] = []
    current: list[str] = []
    depth = 0
    index, size = 0, len(blanked)
    while index < size:
        character = blanked[index]
        if character in "({":
            depth += 1
        elif character in ")}":
            depth = max(0, depth - 1)
        if depth == 0 and blanked.startswith("||", index):
            chunks.append("".join(current))
            current = []
            index += 2
            continue
        if depth == 0 and blanked.startswith("&&", index):
            chunks.append("".join(current))
            segments.append(chunks)
            chunks, current = [], []
            index += 2
            continue
        if depth == 0 and character == ";":
            chunks.append("".join(current))
            segments.append(chunks)
            chunks, current = [], []
            index += 1
            continue
        current.append(character)
        index += 1
    chunks.append("".join(current))
    segments.append(chunks)
    return segments


def unguarded_or_branches(line: str) -> list[str]:
    """The `||` branches on this line that do NOT end in a non-zero exit.

    Evaluated per or-list rather than per line. Searching NONZERO_EXIT over the
    whole joined line meant any `exit 1` token anywhere satisfied the rule for
    every or-list on it — including one belonging to a different command, and
    including one inside a quoted string that never executes. Both were verified
    to give a full pass over `<gate> || true`.
    """
    branches: list[str] = []
    for chunks in _top_level_pieces(line):
        if len(chunks) < 2:
            continue
        if CONDITION.search(chunks[0]):
            # `if [ -n "$A" ] || [ -n "$B" ]; then` joins two tests; the branch
            # that carries the exit is the body, not the or-list. The shape is
            # executed by `swallow_findings` anyway, so this exemption is not a
            # way through: `if cmd || true; then ...; fi` is rejected by running
            # it.
            continue
        for position in range(1, len(chunks)):
            branch = "||".join(chunks[position:])
            if not NONZERO_EXIT.search(branch):
                branches.append(branch.strip())
    return branches


def pytest_arguments(line: str) -> list[str]:
    found = re.search(r"\bpytest\b", line)
    if found is None:
        return []
    tail = line[found.end() :]
    try:
        return shlex.split(tail)
    except ValueError:
        # Unbalanced quoting: fall back to whitespace splitting rather than
        # erroring out, so an odd line is still inspected instead of skipped.
        return tail.split()


def pytest_lines(document: Any) -> Iterator[tuple[str, str]]:
    for name, block in run_blocks(document):
        for line in commands(block):
            if re.search(r"\bpytest\b", line):
                yield name, line


def same_path(text: str) -> str:
    """One path token, in the spelling two paths are compared in.

    The only normalisation is `${NAME}` to `$NAME`, because bash resolves those
    two to the same file and rejecting a workflow for changing brace style would
    be a rule enforced by deleting it. Nothing else is normalised: `./j.xml` and
    `j.xml` are left different, which is the fail-closed direction — the rule
    then demands the two ends of the chain be written the same way, rather than
    guessing that two different strings are one file.
    """
    return BRACED_VARIABLE.sub(r"$\1", text.strip())


def arguments_after(line: str, marker: str) -> list[str]:
    """The words following `marker` on this line, up to the next command.

    The tail is cut at the first command terminator OUTSIDE quotes before it is
    split, which is what makes `gate.py "$X"; } &` report `$X` rather than
    `$X;`. Without the cut, a gate written as the last statement of a brace
    group compared unequal to the path pytest wrote and the rule rejected a
    correct workflow — which is how a rule gets deleted rather than fixed.
    `shlex.split` also hands back `||` and `>` as ordinary words, so the token
    check stays as a second cut for anything the character scan let through.
    """
    position = line.find(marker)
    if position < 0:
        return []
    tail = line[position + len(marker) :]
    cut: list[str] = []
    quote: str | None = None
    for character in tail:
        if quote is not None:
            if character == quote:
                quote = None
            cut.append(character)
            continue
        if character in "'\"":
            quote = character
            cut.append(character)
            continue
        if character in COMMAND_TERMINATORS:
            break
        cut.append(character)
    try:
        tokens = shlex.split("".join(cut))
    except ValueError:
        tokens = "".join(cut).split()
    arguments: list[str] = []
    for token in tokens:
        if token in SHELL_OPERATOR_TOKENS:
            break
        arguments.append(token)
    return arguments


def junit_paths_on(line: str) -> list[str]:
    """Every `--junit-xml` value this pytest invocation declares.

    A junit flag with no value after it yields the empty string rather than
    nothing, so "pytest was told to write a junit and was not told where"
    reaches the comparison as a path that cannot equal the gate's, instead of
    vanishing and leaving the sets accidentally equal.
    """
    arguments = pytest_arguments(line)
    found: list[str] = []
    index = 0
    while index < len(arguments):
        head, _, tail = arguments[index].partition("=")
        if head in JUNIT_FLAGS:
            if tail:
                found.append(same_path(tail))
            elif index + 1 < len(arguments) and not arguments[
                index + 1
            ].startswith("-"):
                found.append(same_path(arguments[index + 1]))
                index += 1
            else:
                found.append("")
        index += 1
    return found


def gate_lines(document: Any) -> Iterator[tuple[str, str]]:
    for name, block in run_blocks(document):
        for line in commands(block):
            if GATE_SCRIPT in line:
                yield name, line


def gate_path_on(line: str) -> str:
    """The file this gate invocation reads, or `""` if it names none.

    The empty string is a value, not an absence: a gate invoked with no path at
    all is a gate reading whatever its default is, which is not the file this
    run wrote, and it must not compare equal to one.
    """
    for argument in arguments_after(line, GATE_SCRIPT):
        if not argument.startswith("-"):
            return same_path(argument)
    return ""


def junit_paths_written(document: Any) -> set[str]:
    return {path for _, line in pytest_lines(document) for path in junit_paths_on(line)}


def junit_paths_gated(document: Any) -> set[str]:
    return {gate_path_on(line) for _, line in gate_lines(document)}


def missing_subjects(paths: list[Path]) -> list[str]:
    """Which of the things the loop-shaped rules iterate over are absent.

    Returned rather than asserted so the same counting can be pointed at a
    synthetic workflow and shown to report the absence, instead of being
    trusted to.

    `gate` is counted here and not only in `check_the_suite_and_the_gate_are_
    both_present`, because that check is a PAIRING rule — it fires when one end
    of the evidence chain is present without the other, and a corpus with
    neither end anywhere satisfies it by having nothing to pair. The last gate
    disappearing from the whole directory is what this count turns red.
    """
    found = {
        "pytest": 0,
        "gate": 0,
        "checkout": 0,
        "python-version": 0,
        "upload": 0,
    }
    for path in paths:
        document = load(path)
        found["pytest"] += sum(1 for _ in pytest_lines(document))
        found["gate"] += sum(1 for _ in gate_lines(document))
        found["checkout"] += sum(1 for _ in steps_using(document, "actions/checkout"))
        found["upload"] += sum(
            1 for _ in steps_using(document, "actions/upload-artifact")
        )
        found["python-version"] += sum(
            1 for mapping in mappings(document) if "python-version" in mapping
        )
    return sorted(subject for subject, count in found.items() if count == 0)


# --------------------------------------------------------------------------
# The rules. Each is a function so it can be aimed at a synthetic workflow as
# well as at the real ones; the `test_*` wrappers below are what parametrise
# over `.github/workflows/`.
# --------------------------------------------------------------------------


def check_parses_and_declares_a_trigger(path: Path) -> None:
    document = load(path)
    assert isinstance(document, dict), f"{path.name} did not parse to a mapping"
    assert triggers(document), (
        f"{path.name} declares no `on:` trigger. A workflow that never runs "
        "reports nothing, and nothing is indistinguishable from green."
    )


def check_no_trigger_is_path_filtered(path: Path) -> None:
    trigger = triggers(load(path))
    if not isinstance(trigger, dict):
        return
    for event, config in trigger.items():
        if not isinstance(config, dict):
            continue
        for key in ("paths", "paths-ignore"):
            assert key not in config, (
                f"{path.name}: `{event}` carries a `{key}:` filter. A "
                "path-filtered required check stays pending instead of "
                "passing, and the gate is never reached."
            )


def check_permissions_are_declared_and_read_only(path: Path) -> None:
    document = load(path)
    assert isinstance(document, dict) and "permissions" in document, (
        f"{path.name} declares no top-level `permissions:`. The omitted block "
        "inherits the repository default, which may be write."
    )
    for mapping in mappings(document):
        granted = mapping.get("permissions")
        if granted is None:
            continue
        rendered = (
            " ".join(f"{scope}:{level}" for scope, level in granted.items())
            if isinstance(granted, dict)
            else str(granted)
        )
        assert "write" not in rendered, (
            f"{path.name} grants write permission ({rendered}). These "
            "workflows read; nothing here commits, pushes, or repairs."
        )


def check_no_step_or_job_continues_on_error(path: Path) -> None:
    for mapping in mappings(load(path)):
        assert "continue-on-error" not in mapping, (
            f"{path.name}: `continue-on-error` on "
            f"{mapping.get('name', 'a job')}. A step that reports success "
            "after failing is worse than no step."
        )


def check_no_workflow_references_a_secret(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    accesses = [
        text[found.start() : found.end() + 40]
        for found in SECRET_REFERENCE.finditer(text)
    ]
    accesses += [
        expression.group(0)
        for expression in GITHUB_EXPRESSION.finditer(text)
        if SECRETS_WORD.search(expression.group(0))
    ]
    assert not accesses, (
        f"{path.name} references a secret ({accesses!r}). "
        "The test job's whole claim is that the suite passes without one, and "
        "the ledger guard needs none to read a diff. A test that needs a "
        "credential is the bug."
    )


def check_no_workflow_declares_a_secrets_key(path: Path) -> None:
    """`secrets:` as a YAML KEY, which no expression pattern can see.

    `secrets: inherit` on a `uses:` job hands the called workflow every secret
    in the repository and contains no `${{ }}`, no dot, no bracket and no
    paren — so SECRET_REFERENCE, which is a rule about an EXPRESSION, is the
    wrong instrument for it entirely. This is a rule about structure, so it
    reads the parse: at any level, `secrets` must not be a key.
    """
    for mapping in mappings(load(path)):
        declared = [
            key for key in mapping if str(key).strip().lower() == "secrets"
        ]
        assert not declared, (
            f"{path.name}: a `secrets:` key on "
            f"{mapping.get('name', 'a job or the workflow')} "
            f"({ {key: mapping[key] for key in declared} }). `secrets: inherit` "
            "hands over every secret in the repository, and an explicit block "
            "hands over the ones it names. Neither workflow needs any."
        )


def check_no_env_mapping_binds_a_provider_credential(path: Path) -> None:
    for mapping in mappings(load(path)):
        environment = mapping.get("env")
        if not isinstance(environment, dict):
            continue
        bound = CREDENTIAL_NAMES.intersection(map(str, environment))
        assert not bound, (
            f"{path.name}: `env:` binds {sorted(bound)} on "
            f"{mapping.get('name', 'a job or the workflow')}. Remove it — "
            "never relax the assertion that catches it."
        )


def check_python_version_is_pinned_to_an_exact_minor(path: Path) -> None:
    for mapping in mappings(load(path)):
        version = mapping.get("python-version")
        if version is None:
            continue
        assert isinstance(version, str), (
            f"{path.name}: python-version {version!r} is not a string. "
            "Unquoted 3.10 parses as the float 3.1 and installs Python 3.1."
        )
        assert re.fullmatch(r"\d+\.\d+", version), (
            f"{path.name}: python-version {version!r} is not an exact X.Y pin."
        )


def check_checkout_never_persists_credentials(path: Path) -> None:
    for step in steps_using(load(path), "actions/checkout"):
        options = step.get("with") or {}
        assert options.get("persist-credentials") is False, (
            f"{path.name}: checkout does not set `persist-credentials: false`."
        )


def check_every_piped_run_block_sets_pipefail(path: Path) -> None:
    """Pipefail on at the top, and never turned off again below it.

    Reading `lines[0]` and stopping was the hole: a block could open with
    `set -euo pipefail`, satisfy this rule, and write `set +o pipefail` on the
    line above the pipeline that mattered. The opening line must also ENABLE the
    option rather than merely mention it — `"pipefail" in first` was true of
    `set +o pipefail`.
    """
    for name, block in run_blocks(load(path)):
        lines = [without_quoted_spans(line) for line in commands(block)]
        if not any(PIPELINE.search(line) for line in lines):
            continue
        first = lines[0]
        assert ENABLES_PIPEFAIL.search(first), (
            f"{path.name}: step {name!r} pipes but does not open with "
            f"`set -o pipefail`; its first command is {first!r}. The pipeline's "
            "status would be its last command's, not its failure's."
        )
        # Every line, the first one included: `set -euo pipefail; set +o
        # pipefail` satisfies the opening assertion and undoes it on the same
        # physical line.
        for line in lines:
            assert not DISABLES_PIPEFAIL.search(line), (
                f"{path.name}: step {name!r} opens with pipefail and turns it "
                f"back off: {line!r}. After that a failing command in a "
                "pipeline reports the status of whatever came after it."
            )


def check_no_run_block_swallows_a_failure(path: Path) -> None:
    """Run every run block with its commands failing, and demand it notices.

    The gate is `swallow_findings`, which executes the block. The two textual
    rules in front of it are a cheap second net, kept because execution has
    blind spots of its own — a failure inside `$(...)`, inside a pipeline
    element, or inside a `( )` subshell is invisible to errexit and therefore
    invisible to the exit code, and `unguarded_or_branches` catches
    `( cmd ) || true` where running it does not.

    Neither net is the whole rule and both are run. What is NOT here any more is
    the shape that let three defeats through: a guard clause that decided
    whether to look at a line by searching it for `||`.
    """
    for name, block in run_blocks(load(path)):
        for line in commands(block):
            assert not DISABLES_ERREXIT.search(without_quoted_spans(line)), (
                f"{path.name}: step {name!r} turns off the option that makes a "
                f"failing command fail the step: {line!r}."
            )
            assert not PROCESS_SUBSTITUTION.search(without_quoted_spans(line)), (
                f"{path.name}: step {name!r} uses process substitution: "
                f"{line!r}. The command inside `<(...)` runs in a subshell "
                "whose status NOTHING propagates — not errexit, not pipefail — "
                "so `tee out < <(gate)` reports tee's zero over a failed gate. "
                "It is a pipeline with no pipe character in it, which is why "
                "neither the pipefail rule nor the executed rule can see it."
            )
            assert not BACKGROUND.search(without_quoted_spans(line)), (
                f"{path.name}: step {name!r} runs a command in the background: "
                f"{line!r}. errexit does not apply to an asynchronous command "
                "and `wait` with no argument returns 0, so a backgrounded gate "
                "is a swallowed failure that contains no `||`, no `if`, and no "
                "`set +e`. The executed rule rejects it too, from the second "
                "failure log; this net is the belt beside that brace."
            )
            assert not ASYNC_LAUNCHER.search(without_quoted_spans(line)), (
                f"{path.name}: step {name!r} detaches a command without a "
                f"background operator: {line!r}. `setsid` returns 0 as soon as "
                "the child is forked and `coproc` runs it in a subshell, so "
                "the step's exit status is about the launcher and not about "
                "the command. The harness cannot model these — the launcher is "
                "the word it stubs — so this net is the whole rule for them."
            )
            unguarded = unguarded_or_branches(line)
            assert not unguarded, (
                f"{path.name}: step {name!r} swallows a failure: {line!r}. The "
                f"branch(es) {unguarded} run when the command on the left "
                "fails and do not end in a non-zero exit, so the step reports "
                "success after it failed."
            )
        findings = swallow_findings(block)
        assert not findings, (
            f"{path.name}: step {name!r} was executed under stubs and "
            + "; ".join(findings)
        )


def check_the_suite_is_never_narrowed(path: Path) -> None:
    """Every argument after `pytest` is a flag, and none of them narrows the
    run or launders the evidence.

    The positional half is new and it is the bigger hole: this used to inspect
    only arguments beginning with `-`, so `--ignore=tests/test_power.py` was
    rejected while `tests/test_power.py` — the same selection, one punctuation
    mark cheaper — was not looked at at all. A positional selection naming only
    the modules the junit manifest requires would satisfy that gate too, and CI
    would run a fraction of the suite and report green. The real invocation has
    zero positionals.

    PYTEST_ADDOPTS is the same narrowing with no command line at all, so it is
    checked as a NAME at every level the way the credential rule is.
    """
    document = load(path)
    banned = NARROWING_PYTEST_LONG_FLAGS | NARROWING_PYTEST_ALIAS_FLAGS
    for mapping in mappings(document):
        environment = mapping.get("env")
        if not isinstance(environment, dict):
            continue
        bound = [
            key for key in environment if str(key).strip().upper() == PYTEST_ADDOPTS
        ]
        assert not bound, (
            f"{path.name}: `env:` binds {PYTEST_ADDOPTS} on "
            f"{mapping.get('name', 'a job or the workflow')}. pytest reads it "
            "as if the flags had been typed, so every rule that reads the "
            "command line sees a clean invocation over a narrowed run."
        )
    for name, block in run_blocks(document):
        for line in commands(block):
            assert not PYTEST_ADDOPTS_TOKEN.search(line), (
                f"{path.name}: step {name!r} sets {PYTEST_ADDOPTS} from the "
                f"shell: {line!r}. `export PYTEST_ADDOPTS=-x` narrows this "
                "step's own run, and writing it into $GITHUB_ENV narrows every "
                "later step — in neither case does it appear in any `env:` "
                "mapping or on any command line."
            )
    for name, line in pytest_lines(document):
        for argument in pytest_arguments(line):
            assert argument.startswith("-"), (
                f"{path.name}: step {name!r} passes the positional "
                f"{argument!r} to pytest. A path, a node id or a directory "
                "selects a subset exactly as --ignore does, and the junit file "
                "cannot account for the tests it never collected."
            )
            if argument.startswith("--"):
                flag = argument.split("=", 1)[0]
                assert flag not in banned, (
                    f"{path.name}: step {name!r} narrows the suite with {flag}"
                )
            elif argument != "-":
                cluster = set(argument[1:].split("=", 1)[0])
                narrowing = cluster & NARROWING_PYTEST_SHORT_FLAGS
                assert not narrowing, (
                    f"{path.name}: step {name!r} narrows the suite with "
                    f"{argument} (-{''.join(sorted(narrowing))})"
                )


def check_every_upload_fails_when_there_is_nothing_to_upload(path: Path) -> None:
    for step in steps_using(load(path), "actions/upload-artifact"):
        options = step.get("with") or {}
        assert options.get("if-no-files-found") == "error", (
            f"{path.name}: upload {step.get('name')!r} does not set "
            "`if-no-files-found: error`. An empty artifact would let "
            "'nothing was compared' pass for a completed check."
        )


def check_the_suite_and_the_gate_are_both_present(path: Path) -> None:
    """Both ends of the evidence chain, or neither, and never a delegated job.

    Three separate holes, all of which were full passes on every other rule:

    * the gate step deleted outright. Every rule in CHECKS is a loop over
      something, so with the gate gone they all pass by having nothing to
      inspect, and a suite that exits 0 on a skipped test is the whole green
      tick;
    * the suite step deleted, leaving a gate reading a stale or absent file;
    * `uses:` at JOB level. A reusable workflow moves every step out of
      `.github/workflows/*.yml` in this repository — there is no run block left
      to read, no pytest line, no gate — and this file reports green over a job
      whose contents it has never seen. `check_no_workflow_declares_a_secrets_
      key` already rejects one that also passes secrets; this rejects the
      delegation itself.

    The first two are asserted as a PAIRING and not as a presence, deliberately.
    A per-file "must contain pytest" would fail ledger-guard.yml, which
    legitimately runs no suite, and a rule that rejects a correct workflow is a
    rule somebody deletes. What must never happen is one end of the chain
    outliving the other, which is what this rejects; the corpus-level half —
    both ends disappearing from the whole directory at once — is counted by
    `missing_subjects` and asserted by `test_no_rule_in_this_file_is_vacuous`.
    """
    document = load(path)
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if isinstance(jobs, dict):
        for job_name, job in jobs.items():
            if isinstance(job, dict) and "uses" in job:
                raise AssertionError(
                    f"{path.name}: job {job_name!r} delegates to the reusable "
                    f"workflow {job['uses']!r} instead of declaring its steps. "
                    "Every rule in this file reads run blocks, and a called "
                    "workflow has none here to read — so the whole job would be "
                    "outside the reach of every check, and a green tick would "
                    "mean nothing had objected rather than that anything ran."
                )
    suite = [name for name, _ in pytest_lines(document)]
    gate = [name for name, _ in gate_lines(document)]
    assert bool(suite) == bool(gate), (
        f"{path.name}: the suite runs in {suite} and the gate runs in {gate}. "
        f"One end of the evidence chain is missing. `pytest` alone exits 0 on a "
        f"skipped test, on an xfail and on a run that collected nothing, so "
        f"without {GATE_SCRIPT} green means 'the suite did not object'; and a "
        f"{GATE_SCRIPT} with no suite in front of it grades whatever file was "
        "left lying around."
    )


def check_the_gate_reads_the_evidence_this_run_wrote(path: Path) -> None:
    """The junit path pytest writes IS the path the gate is handed, and nothing
    in between writes it.

    Three unpinned joints, each a full pass on every other rule in this file:

    * pytest's `--junit-xml=` value and the gate's argument were never compared,
      so the gate could be pointed at a tracked fixture — a hand-written junit
      with a handful of passing testcases and nothing else in it really does
      make the gate exit 0, with no suite run at all;
    * nothing stopped a step BETWEEN the two from overwriting the path.
      `cp fixtures/green.xml "$RUNNER_TEMP/junit.xml"` is a legal step with no
      swallow, no secret, no narrowing flag and no pipeline in it;
    * pytest could be run with no junit flag at all while the gate read a file
      from an earlier run of the job.

    So the comparison is between SETS and it demands equality, not overlap or
    containment: every junit written is gated on, and every file gated on was
    written by a pytest invocation in this same workflow.

    The write ban is deliberately blunter than the enumeration that prompted it,
    and it is blunt in two directions:

    * any run-block line naming the junit path that is neither the producer nor
      the gate is a rejection. Not `>`, `>>`, `cp`, `mv`, `tee` — ANY use. A
      list of writer commands is a rule about spellings, and `install`,
      `busybox cp`, `sed -i` and `python -c "open(...).write(...)"` are all
      writers nobody would have listed. The cost is a read-only
      `ls -l "$RUNNER_TEMP/junit.xml"`, which is exactly the kind of
      legitimate-looking exception this file's header calls out;
    * on the producer's or the gate's OWN line, the path must appear no more
      times than it is legitimately used. `cp fixture X && gate.py X` contains
      the gate, so the first arm exempts it; counting the occurrences does not.
      That arm names no command either — a second mention of the evidence file
      on the line that produces or grades it is the finding, whatever wrote it.
    """
    document = load(path)
    written = junit_paths_written(document)
    gated = junit_paths_gated(document)
    if not written and not gated:
        # Neither end of the chain is here. That is either a workflow with no
        # suite in it — ledger-guard.yml is one — or both ends deleted at once,
        # and the second is what `check_the_suite_and_the_gate_are_both_present`
        # and `missing_subjects` are for. Silence here, a rule of its own there.
        return
    assert written, (
        f"{path.name}: {GATE_SCRIPT} is invoked on {sorted(gated)} and no "
        "pytest invocation in this workflow writes a junit file at all. The "
        "gate would be reading a file from somewhere else — a fixture, an "
        "earlier job, or nothing."
    )
    assert gated, (
        f"{path.name}: pytest writes {sorted(written)} and nothing invokes "
        f"{GATE_SCRIPT}. The evidence is produced and never read, and pytest's "
        "own exit code is 0 over a skipped test."
    )
    assert written == gated, (
        f"{path.name}: pytest writes junit to {sorted(written)} and the gate "
        f"reads {sorted(gated)}. The gate must grade the evidence THIS run "
        "wrote; pointed anywhere else it grades a file this workflow did not "
        "produce, and a hand-written junit of passing testcases exits 0."
    )
    for name, block in run_blocks(document):
        for line in commands(block):
            normalised = BRACED_VARIABLE.sub(r"$\1", line)
            for junit in sorted(written):
                if not junit or junit not in normalised:
                    continue
                produced = junit_paths_on(line).count(junit)
                gated_here = int(GATE_SCRIPT in line and gate_path_on(line) == junit)
                assert produced or gated_here, (
                    f"{path.name}: step {name!r} names the junit path "
                    f"{junit!r} without being the pytest run that writes it or "
                    f"the {GATE_SCRIPT} that reads it: {line!r}. A step between "
                    "the two can replace the evidence with a file of its own "
                    "choosing, and every other rule here passes over it."
                )
                assert normalised.count(junit) <= produced + gated_here, (
                    f"{path.name}: step {name!r} names the junit path "
                    f"{junit!r} more often than it produces or gates it: "
                    f"{line!r}. The extra mention is a second use of the "
                    "evidence file on the line that is supposed to write it or "
                    "read it — a redirection, a copy, an in-place edit — and "
                    "the evidence must not be assembled by the step that "
                    "grades it."
                )


def check_no_workflow_overrides_the_shell(path: Path) -> None:
    """Every run block runs under the shell the executed rules grade it under.

    `run_block_under_stubs` executes each block under `bash -e`, which is what
    GitHub's default `shell:` gives on Linux. NOTHING in CHECKS read `shell:` at
    any level, and five spellings walked past every rule in this file at once —
    a step-level `shell: bash {0}`, `shell: /bin/bash {0}`, `shell: pwsh`, and a
    `defaults.run.shell` at job level or at workflow level, which applies to
    every step without appearing on any of them.

    `bash {0}` is the one that matters most and it is the least conspicuous:
    it is bash, it looks like the default, and it drops the `-e`. After it, a
    failing command in the middle of a block does not fail the step at all, and
    every `swallow_findings` verdict in this file is a verdict about a shell the
    workflow does not use.

    The test is structural rather than textual. It does not look for the string
    `{0}` — it demands the value be the bare keyword `bash` or `sh`, so any
    value carrying an argument, a path, a different interpreter or whitespace of
    any kind is rejected whatever it spells. `mappings()` walks the whole
    document, so a `shell:` on a step, inside `defaults.run` on a job, and
    inside `defaults.run` at the top are all the same finding in the same loop.
    """
    for mapping in mappings(load(path)):
        if "shell" not in mapping:
            continue
        declared = mapping["shell"]
        # Not `.strip()`: the claim this rule makes is that any value carrying
        # whitespace is a custom command line, and stripping would make the
        # claim false for `"bash "` — which YAML preserves only when it is
        # explicitly quoted, so a plain `shell: bash` is unaffected.
        assert isinstance(declared, str) and declared in SAFE_SHELLS, (
            f"{path.name}: `shell: {declared!r}` on "
            f"{mapping.get('name', 'a step, a job default or the workflow')}. "
            f"Only {sorted(SAFE_SHELLS)} are accepted, as bare keywords. A "
            "value with an argument in it is a custom command line — `bash {0}`"
            " drops the errexit that GitHub's own default supplies, and after "
            "that every executed rule in this file is grading a shell this "
            "workflow does not run."
        )


#: Every rule above, by the name it is known by. The synthetic control below
#: runs the whole list, so a rule added without a bad case of its own is still
#: at least asserted to accept a well-formed workflow.
#: The only `if:` a step in the evidence chain may carry. `always()` WIDENS
#: when a step runs — it makes the step fire even after an earlier failure,
#: which is why the real gate uses it. Every other expression NARROWS, and a
#: narrowed gate is a gate that does not run.
PERMITTED_CHAIN_CONDITION = "always()"


def _is_a_chain_step(step: object) -> bool:
    """A step that runs the suite or the gate — the two ends of the evidence."""
    if not isinstance(step, dict):
        return False
    run = step.get("run")
    if not isinstance(run, str):
        return False
    return "pytest" in run or "check_test_results.py" in run


def _condition(node: dict) -> str | None:
    """The `if:` as written, unwrapped from `${{ }}` and normalised.

    YAML parses `if: false` to the BOOLEAN False, not the string, so this
    stringifies before comparing — a rule that only ever compared strings would
    pass the single cheapest way to switch a gate off.
    """
    if "if" not in node:
        return None
    raw = str(node["if"]).strip()
    if raw.startswith("${{") and raw.endswith("}}"):
        raw = raw[3:-2].strip()
    return raw


def check_no_condition_disables_the_chain(path: Path) -> None:
    """A step that is present but never runs is the same as a step that is gone.

    `check_the_suite_and_the_gate_are_both_present` asserts the TEXT of both
    ends exists. It reads no `if:`, so every one of these was a full pass on
    all rules while switching the gate off completely:

        if: false
        if: ${{ false }}
        if: github.event_name == 'schedule'     # on a workflow with no schedule
        if: ${{ !cancelled() && false }}

    and the same expression on the JOB, which disables every step inside it at
    once. The failure is worse than a deleted gate, because the step is still
    there to read: a reviewer looking for the gate finds it.

    `always()` is permitted and nothing else is. That asymmetry is the whole
    rule — `always()` is the one condition that makes a step run MORE often
    than the default, and the real workflows use it so the gate still fires on
    a run where an earlier step already failed. Any other expression can
    evaluate false, and a gate that can evaluate false is not a gate.
    """
    document = load(path)
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict):
        return
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        steps = steps if isinstance(steps, list) else []
        chain = [step for step in steps if _is_a_chain_step(step)]
        if not chain:
            continue
        job_condition = _condition(job)
        assert job_condition is None, (
            f"{path.name}: job {job_name!r} carries `if: {job_condition}` and "
            "contains the suite or the gate. A job-level condition switches "
            "every step inside it off at once."
        )
        for step in chain:
            condition = _condition(step)
            if condition is None:
                continue
            assert condition == PERMITTED_CHAIN_CONDITION, (
                f"{path.name}: a step running the suite or the gate carries "
                f"`if: {condition}`. Only `{PERMITTED_CHAIN_CONDITION}` is "
                "permitted — it widens when the step runs; anything else can "
                "evaluate false, and a gate that can evaluate false is not a "
                "gate."
            )


#: The two prefixes that name the runner's own temporary directory, in the
#: shell spelling and the expression spelling. Evidence written anywhere else is
#: evidence written into the checkout, and a file in the checkout can be
#: TRACKED — which is the whole attack: `--junit-xml=tests/junit.xml` beside a
#: `pytest --version` that exits 0 and writes nothing leaves a committed junit
#: of passing testcases sitting at the gated path, and the gate grades it, and
#: `git status --porcelain` is empty because nothing was written.
RUNNER_TEMP_PREFIXES = ("$RUNNER_TEMP/", "${{ runner.temp }}/")

#: Every argument the suite line may carry. A WHITELIST, because the blocklist
#: this replaces was defeated by three arguments that are not narrowing flags at
#: all: `--version`, `-h` and `--help` each exit 0, run no test and write no
#: junit (measured, pytest 9.1.1), so the suite step goes green having done
#: nothing. None of them appears in any set of flags that shorten a run,
#: because they do not shorten a run — they replace it.
#:
#: `-q` is the quiet report, `-rs` prints the reason for every skip next to the
#: gate that fails on it. The junit flag is handled separately below because it
#: carries a value. Anything else is a deliberate edit to this set with a
#: reason beside it.
SUITE_FLAG_WHITELIST = frozenset({"-q", "-rs"})

#: The gate and the suite, pinned as whole commands rather than as substrings.
#: `run:` had only to CONTAIN the gate's script name and the path, so
#: `: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"` — the
#: no-op builtin in front — satisfied every rule in this file while the gate
#: never executed (measured: exit 0 under `bash -e`).
#:
#: The suite line had the same shape and one more hole in it. Both were found
#: at 5072f97 by making the edit to the REAL tests.yml and running this whole
#: module against it — not a rule at a time, the file:
#: `: python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"` and
#: `echo python -m pytest …` were full passes, and so was
#: `PYTEST_PLUGINS=disarm python -m pytest -q -rs --junit-xml=…`, because the
#: argument whitelist reads what follows the word `pytest` and nothing had ever
#: read what precedes it. An assignment in front of a command is that command's
#: environment, and `PYTEST_PLUGINS` is a plugin list pytest imports at startup.
PYTHON_INTERPRETERS = frozenset({"python", "python3"})
GATE_SCRIPT_PATH = "scripts/check_test_results.py"
SUITE_MODULE = "pytest"

#: The variable that takes the checkout's own directory back off `sys.path`.
#: `python -m pytest` puts the working directory ahead of site-packages, so a
#: tracked `pytest.py` at the repository root IS the suite: measured on this
#: repository, a two-line `pytest.py` made `python -m pytest -q` exit 0 having
#: collected nothing, and the same tree with PYTHONSAFEPATH=1 ran the whole
#: suite. The tracked half of that family is refused by
#: tests/test_the_guards_exist.py; this is the half that also covers an
#: untracked file the runner picked up some other way.
SAFE_PATH_VARIABLE = "PYTHONSAFEPATH"


def tracked_paths() -> frozenset[str]:
    """Every path git is watching, read from git rather than from the disk.

    `check=True`: outside a work tree this raises, and an error is a failure.
    A rule that answered "no tracked files" when it could not ask would accept
    exactly the workflow it exists to reject.
    """
    done = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(entry for entry in done.stdout.split("\0") if entry)


def check_no_job_can_be_skipped_into_a_pass(path: Path) -> None:
    """`needs:` is `if: false` reworded, and GitHub reports it as Success.

    `check_no_condition_disables_the_chain` reads `if:`. It reads nothing else,
    and one line defeats it:

        jobs:
          prep:
            if: false
            ...
          tests:
            needs: prep

    The required job is skipped because its dependency was skipped, and
    What was measured here, at 4454b20: the whole linter passed
    with `needs: prep` on the tests job and a `prep` job carrying `if: false`.
    What is CITED rather than measured, because no test inside a repository can
    observe its own branch protection: GitHub's troubleshooting guidance for
    required status checks states that a conditionally skipped check reports
    Success, where a path-filtered one stays pending forever. If that ever
    stopped being true this rule would merely be strict; while it is true, a
    required check that never ran turns the PR green.

    `strategy:` is the same shape with a different word. A matrix with an empty
    `include` produces zero jobs, and a required context that produced no job
    is a required context nobody waited for.

    The rule is blunt in both directions and deliberately so: NO job in either
    workflow may carry `needs`, `strategy` or `if`. Both files hold exactly one
    job today and both of those jobs are required contexts, so there is no
    legitimate use to weigh against it. A future multi-job workflow is a
    deliberate edit here with an argument attached — which is the point, because
    the cheap version of that edit is the attack.
    """
    document = load(path)
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict):
        return
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for key, why in (
            ("needs", "a dependency that is skipped or fails skips this job "
                      "too, and GitHub reports a conditionally-skipped "
                      "required check as Success"),
            ("strategy", "a matrix that expands to nothing produces no job, "
                         "and a required context with no job behind it is a "
                         "check nobody waited for"),
            ("if", "a job-level condition switches every step inside it off at "
                   "once, and a skipped required check reports Success"),
        ):
            assert key not in job, (
                f"{path.name}: job {job_name!r} carries `{key}:` "
                f"({job[key]!r}). {why}. Every job in this repository's "
                "workflows is a required status check; a required check that "
                "did not run must be red, never green."
            )


def check_the_suite_line_carries_only_whitelisted_arguments(path: Path) -> None:
    """A whitelist of what pytest may be told, and where the evidence may go.

    `check_the_suite_is_never_narrowed` is a blocklist: it rejects the flags
    somebody has been bitten by and accepts every flag nobody has thought of.
    Three of the ones nobody had thought of do not narrow the run — they
    replace it. `python -m pytest --version -q -rs --junit-xml=<path>` exits 0,
    runs no test and writes no junit file at all (measured, pytest 9.1.1; `-h`
    and `--help` behave the same way). Point the junit at a path inside the
    checkout, commit a file of passing testcases there, and the gate grades the
    committed file, the clean-tree check stays empty because nothing was
    written, and every other rule in this file passes. Measured at 4454b20: the
    whole linter passed with that suite line in tests.yml.

    WHAT THIS RULE ACTUALLY ACCEPTS, stated at its real width, because the
    sentence that used to stand here — "every argument must be `-q`, `-rs` or
    the junit flag" — described a different and larger rule than the one below.
    It reads every logical line of every `run:` block in this file's workflow
    that contains the word `pytest`, takes the words AFTER the first such word,
    and permits exactly:

      * the tokens in `SUITE_FLAG_WHITELIST` — today `-q` and `-rs`, matched
        whole, so `-qq` and `-q=1` are not the same token and are rejected;
      * exactly one `--junit-xml`/`--junitxml`, in the `=` form or with its
        value as the next word, whose value begins with `$RUNNER_TEMP/` or
        `${{ runner.temp }}/`, holds no `..` segment, and names no tracked file.

    Everything else on that line is rejected, including the separators of a
    second command: `pytest … ; echo done` reports `;`, `echo` and `done` as
    arguments (run, not assumed), so a second invocation behind the first is
    rejected the same way a stray flag is.

    Three things it does NOT decide, each run rather than reasoned about:

      * the words BEFORE `pytest`. Until `check_the_suite_runs_as_a_whole_
        command` was written beside it, `: python -m pytest …` and
        `PYTEST_PLUGINS=disarm python -m pytest …` in the real tests.yml left
        every test in this module passing (measured at 5072f97). That is the
        sibling rule's subject, not this one's;
      * flags that never appear on a command line. `addopts` in pyproject.toml
        and `PYTEST_ADDOPTS` in the environment reach pytest as if typed; the
        root conftest refuses BOTH wholesale — any value at all, not an
        enumerated set — and `check_the_suite_is_never_narrowed` refuses the
        variable by name here (measured at 5072f97: `PYTEST_ADDOPTS=--runxfail`
        and `addopts = "--runxfail"` each exit 1 under `python -m pytest -q`);
      * what a loaded plugin does once pytest is running. That is gap 5 in
        `tests/test_the_guards_exist.py::test_known_gaps_that_still_get_through`.

    The tracked-path clause below is a second cut and its reach is narrow by
    construction: a path under `$RUNNER_TEMP` is not in the checkout, so today
    it can only fire on a path that names a tracked file underneath it. It is
    here for the edit that widens the prefix rule later — the prefix is the
    clause somebody will want an exception to, and this is what remains when
    they get one.
    """
    document = load(path)
    for name, line in pytest_lines(document):
        arguments = pytest_arguments(line)
        index = 0
        junit_seen = 0
        while index < len(arguments):
            argument = arguments[index]
            head, separator, tail = argument.partition("=")
            if head in JUNIT_FLAGS:
                junit_seen += 1
                if not separator and index + 1 < len(arguments):
                    tail = arguments[index + 1]
                    index += 1
                value = same_path(tail)
                assert any(
                    value.startswith(prefix)
                    for prefix in (same_path(p) for p in RUNNER_TEMP_PREFIXES)
                ), (
                    f"{path.name}: step {name!r} writes the junit evidence to "
                    f"{value!r}, which is not under the runner's temporary "
                    f"directory ({list(RUNNER_TEMP_PREFIXES)}). Evidence "
                    "written inside the checkout can be a file that was "
                    "committed, and a committed junit of passing testcases "
                    "satisfies the gate and leaves the tree clean."
                )
                assert ".." not in value.split("/"), (
                    f"{path.name}: step {name!r} writes the junit evidence to "
                    f"{value!r}. A `..` climbs back out of the runner's "
                    "temporary directory, so the prefix above stops meaning "
                    "what it says — `$RUNNER_TEMP/../../workspace/junit.xml` "
                    "satisfies a prefix test and lands in the checkout."
                )
                bare = value
                for prefix in (same_path(p) for p in RUNNER_TEMP_PREFIXES):
                    if bare.startswith(prefix):
                        bare = bare[len(prefix):]
                assert value not in tracked_paths() and bare not in tracked_paths(), (
                    f"{path.name}: step {name!r} points the junit evidence at "
                    f"{value!r}, which names a TRACKED file. The gate would be "
                    "grading a file that arrived in the checkout rather than "
                    "one this run produced."
                )
                index += 1
                continue
            assert argument in SUITE_FLAG_WHITELIST, (
                f"{path.name}: step {name!r} passes {argument!r} to pytest. "
                f"The suite line may carry {sorted(SUITE_FLAG_WHITELIST)} and "
                "a junit path, and nothing else. This is a whitelist because "
                "the blocklist it replaced accepted `--version`, `-h` and "
                "`--help` — none of which narrows a run, and each of which "
                "makes pytest exit 0 having run nothing and written no "
                "evidence."
            )
            index += 1
        assert junit_seen == 1, (
            f"{path.name}: step {name!r} names the junit flag {junit_seen} "
            "time(s). The suite must write exactly one evidence file, and the "
            "gate must grade that one."
        )
    # `$RUNNER_TEMP` is the prefix the clause above rests on, and a variable is
    # only a guarantee while nothing reassigns it. A step that writes
    # `RUNNER_TEMP=$GITHUB_WORKSPACE` into `$GITHUB_ENV` moves the evidence
    # into the checkout for every LATER step, with the pytest line and the gate
    # line both still reading exactly as they do now.
    #
    # This is a SPELLING rule and it is worth saying so where it is written:
    # what it refuses is the literal token `RUNNER_TEMP` followed by `=` on a
    # command line. A name assembled at run time is the same assignment and
    # this does not see it — measured at 5072f97, `V=RUNNER` on one line and
    # `echo "${V}_TEMP=$GITHUB_WORKSPACE" >> "$GITHUB_ENV"` on the next passed
    # every rule in CHECKS. That route is gap 9 in
    # `tests/test_the_guards_exist.py::test_known_gaps_that_still_get_through`
    # rather than a hole implied shut here.
    for name, block in run_blocks(document):
        for line in commands(block):
            assert not re.search(r"\bRUNNER_TEMP\s*=", line), (
                f"{path.name}: step {name!r} assigns RUNNER_TEMP: {line!r}. "
                "The junit path is pinned to that variable, so reassigning it "
                "moves the evidence somewhere a committed file can be waiting."
            )


def check_the_gate_runs_as_a_whole_command(path: Path) -> None:
    """The gate line is a command, not a line that mentions a command.

    Every rule that pinned the gate asked whether the run block CONTAINS
    `check_test_results.py` and the junit path. `:` in front of it satisfies
    both — `: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"` is
    the no-op builtin with three arguments, it exits 0 (measured under
    `bash -e`), and at 4454b20 the entire linter passed with it in tests.yml
    while the gate never executed. `echo`, `#` on the same logical line after a
    continuation, and `true` all do the same thing.

    So the line is pinned as a WHOLE command: exactly an interpreter, exactly
    the script, exactly one path. `check_the_suite_runs_as_a_whole_command` is
    the same pin on the other end of the chain, written later and for the same
    reason. The executed half — that a stub for that interpreter is actually
    entered, at the top level, with the script as its first argument — is
    `test_the_gate_step_is_executed_and_not_merely_written`, because a rule
    about text cannot tell `python x.py` from `: python x.py` and running it
    can.
    """
    document = load(path)
    for name, line in gate_lines(document):
        try:
            words = shlex.split(line)
        except ValueError:
            words = line.split()
        assert len(words) == 3, (
            f"{path.name}: step {name!r} runs the gate as {line!r}. The gate "
            "line must be exactly `<python> scripts/check_test_results.py "
            "<junit path>` — three words, nothing before them and nothing "
            "after. A line that merely CONTAINS the script satisfies every "
            "textual rule while running nothing: `: python "
            "scripts/check_test_results.py <path>` exits 0."
        )
        interpreter, script, _ = words
        assert interpreter in PYTHON_INTERPRETERS, (
            f"{path.name}: step {name!r} starts the gate line with "
            f"{interpreter!r}, not one of {sorted(PYTHON_INTERPRETERS)}. "
            "Whatever is in command position is what runs, and the gate is "
            "only a gate when it is the thing that runs."
        )
        assert script == GATE_SCRIPT_PATH, (
            f"{path.name}: step {name!r} hands {interpreter!r} the argument "
            f"{script!r}. The gate is {GATE_SCRIPT_PATH}, given as the first "
            "argument, so that the interpreter runs it rather than mentioning "
            "it."
        )


def check_the_suite_runs_as_a_whole_command(path: Path) -> None:
    """The suite line is a command too, not a line that mentions pytest.

    The argument whitelist reads the words after `pytest`. Nothing read the
    words in front of it, and three shapes walked through that gap. Each was
    measured at 5072f97 by putting it into the real tests.yml and running this
    entire module: every test in the file passed, all three times.

      * `: python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"` — the
        no-op builtin, exactly the shape that was found in front of the gate;
      * `echo python -m pytest …`, which prints the command and runs nothing;
      * `PYTEST_PLUGINS=disarm python -m pytest …`. An assignment in front of a
        command is that command's environment, and `PYTEST_PLUGINS` is a list
        of modules pytest imports as plugins at startup. No flag appears on the
        line, so no rule that reads flags has anything to object to.

    So the words before `pytest` are pinned the way the gate's are: exactly an
    interpreter and `-m`. `env FOO=bar python -m pytest …` is rejected by that
    too, which is the point — an environment assembled in front of the suite is
    an input to the suite, and it belongs in an `env:` mapping where
    `check_no_env_mapping_binds_a_provider_credential` and
    `check_the_suite_is_never_narrowed` can both read it.

    The executed half is `test_the_suite_step_is_executed_and_not_merely_
    written`, for the reason the gate has one: a rule about text cannot tell
    `python -m pytest` from `: python -m pytest`, and running the block can.
    """
    document = load(path)
    for name, line in pytest_lines(document):
        try:
            words = shlex.split(line)
        except ValueError:
            words = line.split()
        if SUITE_MODULE not in words:
            # The word is on the line but not as a word of its own — a junit
            # path with `pytest` in its name, say. `pytest_arguments` reads the
            # same line and the whitelist grades whatever it finds there.
            continue
        head = words[: words.index(SUITE_MODULE)]
        assert len(head) == 2 and head[0] in PYTHON_INTERPRETERS and head[1] == "-m", (
            f"{path.name}: step {name!r} runs the suite as {line!r}. The words "
            f"in front of `{SUITE_MODULE}` must be exactly "
            f"`<{'|'.join(sorted(PYTHON_INTERPRETERS))}> -m` — found {head!r}. "
            "A builtin in command position runs nothing while the line still "
            "reads correctly, and an assignment in front of the command is an "
            "environment nobody declared: `PYTEST_PLUGINS=x python -m pytest` "
            "loads a plugin with no flag on the line for any rule to see."
        )


def check_the_suite_step_takes_the_checkout_off_the_path(path: Path) -> None:
    """The suite step declares PYTHONSAFEPATH, because `-m` prefers the cwd.

    `python -m pytest` puts the working directory at the front of `sys.path`,
    ahead of site-packages. A tracked `pytest.py` at the repository root is
    therefore the module `-m` finds. Measured on this repository: a `pytest.py`
    holding `raise SystemExit(0)` made `python -m pytest -q` exit 0 having
    collected nothing, and the identical tree run with `PYTHONSAFEPATH=1` ran
    the whole suite. `coverage.py`, and a `sitecustomize.py` on any declared
    PYTHONPATH entry, are the same family.

    The tracked half is refused by name in
    `tests/test_the_guards_exist.py::test_no_tracked_file_can_shadow_the_suite`.
    This is the other half: it does not care how the file got there.
    """
    document = load(path)
    for mapping in mappings(document):
        run = mapping.get("run")
        if not isinstance(run, str) or not re.search(r"\bpytest\b", run):
            continue
        if not any(re.search(r"\bpytest\b", line) for line in commands(run)):
            # The word occurs only in a comment; not the suite step.
            continue
        environment = mapping.get("env")
        declared = environment.get(SAFE_PATH_VARIABLE) if isinstance(
            environment, dict
        ) else None
        assert str(declared) == "1", (
            f"{path.name}: the step {mapping.get('name')!r} runs pytest "
            f"without `{SAFE_PATH_VARIABLE}: '1'` in its `env:` (found "
            f"{declared!r}). `python -m` searches the working directory "
            "first, so a `pytest.py` or `coverage.py` in the checkout is the "
            "module that runs."
        )


CHECKS: dict[str, Callable[[Path], None]] = {
    "parses_and_declares_a_trigger": check_parses_and_declares_a_trigger,
    "no_trigger_is_path_filtered": check_no_trigger_is_path_filtered,
    "permissions_are_declared_and_read_only": (
        check_permissions_are_declared_and_read_only
    ),
    "no_step_or_job_continues_on_error": check_no_step_or_job_continues_on_error,
    "no_workflow_references_a_secret": check_no_workflow_references_a_secret,
    "no_workflow_declares_a_secrets_key": check_no_workflow_declares_a_secrets_key,
    "no_env_mapping_binds_a_provider_credential": (
        check_no_env_mapping_binds_a_provider_credential
    ),
    "python_version_is_pinned_to_an_exact_minor": (
        check_python_version_is_pinned_to_an_exact_minor
    ),
    "checkout_never_persists_credentials": check_checkout_never_persists_credentials,
    "every_piped_run_block_sets_pipefail": check_every_piped_run_block_sets_pipefail,
    "no_run_block_swallows_a_failure": check_no_run_block_swallows_a_failure,
    "the_suite_is_never_narrowed": check_the_suite_is_never_narrowed,
    "every_upload_fails_when_there_is_nothing_to_upload": (
        check_every_upload_fails_when_there_is_nothing_to_upload
    ),
    "the_suite_and_the_gate_are_both_present": (
        check_the_suite_and_the_gate_are_both_present
    ),
    "the_gate_reads_the_evidence_this_run_wrote": (
        check_the_gate_reads_the_evidence_this_run_wrote
    ),
    "no_workflow_overrides_the_shell": check_no_workflow_overrides_the_shell,
    "no_condition_disables_the_chain": check_no_condition_disables_the_chain,
    "no_job_can_be_skipped_into_a_pass": check_no_job_can_be_skipped_into_a_pass,
    "the_suite_line_carries_only_whitelisted_arguments": (
        check_the_suite_line_carries_only_whitelisted_arguments
    ),
    "the_gate_runs_as_a_whole_command": check_the_gate_runs_as_a_whole_command,
    "the_suite_runs_as_a_whole_command": check_the_suite_runs_as_a_whole_command,
    "the_suite_step_takes_the_checkout_off_the_path": (
        check_the_suite_step_takes_the_checkout_off_the_path
    ),
}


# --------------------------------------------------------------------------
# The rules, applied to the real .github/workflows/*.yml.
# --------------------------------------------------------------------------


def test_the_workflow_directory_is_not_empty() -> None:
    """A linter that lints nothing passes, which is the fail-open case again.

    Every other test in this file is parametrised over the file list. If
    .github/workflows/ is renamed, emptied, or moved, that list is empty, every
    parametrised rule below collects zero cases, and the file reports green
    over a repository with no CI at all. This is the assertion that makes that
    a red build.
    """
    assert WORKFLOWS_DIR.is_dir(), f"{WORKFLOWS_DIR} does not exist"
    assert WORKFLOW_FILES, (
        f"No workflow files under {WORKFLOWS_DIR}. Every rule in this module "
        "is parametrised over them, so an empty directory would pass every "
        "check by having nothing to check."
    )


def test_the_executed_swallow_rule_has_a_shell_to_run_in() -> None:
    """No bash, no verdict — and no verdict must not read as a clean one.

    `swallow_findings` is the gate now. If `shutil.which("bash")` ever comes
    back empty the whole executed half of this file would either error or, worse,
    be quietly softened into a skip by someone in a hurry. Named here so the
    absence is a red tick of its own rather than a surprise inside another rule.
    """
    assert HARNESS_SHELL, (
        "bash is not on PATH, so run blocks cannot be executed and the swallow "
        "rule cannot report anything. That is a broken gate, NOT evidence that "
        "no failure is swallowed."
    )


@every_workflow
def test_every_workflow_parses_and_declares_a_trigger(path: Path) -> None:
    """A workflow with no `on:` never runs, and never running looks identical
    to passing: no red tick appears anywhere to say the gate is gone."""
    check_parses_and_declares_a_trigger(path)


@every_workflow
def test_no_trigger_is_path_filtered(path: Path) -> None:
    """A path-filtered workflow configured as a required status check never
    reports at all — it sits pending forever rather than passing. And the
    change that breaks a guard rarely touches the guard's own file."""
    check_no_trigger_is_path_filtered(path)


@every_workflow
def test_permissions_are_declared_and_read_only(path: Path) -> None:
    """An omitted `permissions:` block inherits the repository default, so
    silence is a route to write access. Named explicitly, and read-only: a
    guard that can push is a guard that can rewrite the evidence it guards."""
    check_permissions_are_declared_and_read_only(path)


@every_workflow
def test_no_step_or_job_continues_on_error(path: Path) -> None:
    """`continue-on-error` is the YAML spelling of a gate that passes when it
    should fail, which the lab rules put below having no gate at all."""
    check_no_step_or_job_continues_on_error(path)


@every_workflow
def test_no_workflow_references_a_secret(path: Path) -> None:
    """Neither of these workflows needs a credential, and a credential in
    scope is a credential that can leak — into a log, a fork PR, or an action
    nobody audited. Every spelling of the accessor counts — dot, bracket,
    paren, any casing — and so does one inside a comment."""
    check_no_workflow_references_a_secret(path)


@every_workflow
def test_no_workflow_declares_a_secrets_key(path: Path) -> None:
    """`secrets: inherit` is not an expression, so no expression rule can see
    it — and it hands over more than any named reference does."""
    check_no_workflow_declares_a_secrets_key(path)


@every_workflow
def test_no_env_mapping_binds_a_provider_credential(path: Path) -> None:
    """Checked at every level, because an `env:` on a step is the placement
    that broke the credential assertion in tests.yml: a step-level binding is
    invisible to every other step, so a check standing beside it sees an empty
    environment and reports all clear."""
    check_no_env_mapping_binds_a_provider_credential(path)


@every_workflow
def test_python_version_is_pinned_to_an_exact_minor(path: Path) -> None:
    """pyproject declares `requires-python = ">=3.12"`, an open upper bound
    that has never been exercised. '3.x' or 'latest' would move the lab onto an
    untested interpreter and attribute a moved measurement to nothing.

    The string check is not pedantry: unquoted `python-version: 3.10` is a YAML
    float, and 3.10 as a float is 3.1.
    """
    check_python_version_is_pinned_to_an_exact_minor(path)


@every_workflow
def test_checkout_never_persists_credentials(path: Path) -> None:
    """Left at its default, checkout leaves a token in .git/config for every
    later step. No step in either workflow authenticates to git, so the token
    is pure blast radius — and the ledger guard must not be able to push."""
    check_checkout_never_persists_credentials(path)


@every_workflow
def test_every_piped_run_block_sets_pipefail(path: Path) -> None:
    """GitHub's default shell is `bash -e {0}`: errexit, but NOT pipefail. A
    pipeline reports the exit status of its LAST command, so `failing-thing |
    tee file` is a green step over a failed command. Set at the top, and not
    unset anywhere below it."""
    check_every_piped_run_block_sets_pipefail(path)


@every_workflow
def test_no_run_block_swallows_a_failure(path: Path) -> None:
    """Every run block is EXECUTED with its commands stubbed to fail, and must
    not exit 0. The shape that survives is `cmd || { echo '::error::...'; exit
    1; }`: the branch ends in a non-zero exit, so the run stops there and the
    exit code says so. Which failure paths the workflows actually use is not
    claimed here — that is what running them answers."""
    check_no_run_block_swallows_a_failure(path)


@every_workflow
def test_the_suite_is_never_narrowed(path: Path) -> None:
    """The junit file must account for every test, and a run that stops early
    or selects a subset cannot. Arguments are read only after the word
    `pytest`, so the `-m` of `python -m pytest` is not mistaken for pytest's
    own marker flag — and they are read from the JOINED logical line, so a
    backslash continuation cannot carry one past the rule. A positional is a
    selection too, and so is PYTEST_ADDOPTS."""
    check_the_suite_is_never_narrowed(path)


@every_workflow
def test_every_upload_fails_when_there_is_nothing_to_upload(path: Path) -> None:
    """The artifact IS the evidence that the gate ran, so a missing file must
    be an error. `if-no-files-found: warn` is the default, and it is what let
    the CBB lab's 1.3M-credit purchase upload nothing and stay green."""
    check_every_upload_fails_when_there_is_nothing_to_upload(path)


@every_workflow
def test_the_suite_and_the_gate_are_both_present(path: Path) -> None:
    """A workflow that runs the suite and never grades it is a green tick over
    `pytest` exiting 0 on a skipped test; one that grades without running is
    grading a file it did not produce. And a job delegated to a reusable
    workflow takes every step out of this file's reach at once."""
    check_the_suite_and_the_gate_are_both_present(path)


@every_workflow
def test_the_gate_reads_the_evidence_this_run_wrote(path: Path) -> None:
    """The chain was unpinned at both ends: nothing compared pytest's
    `--junit-xml=` to the path the gate is handed, and nothing stopped a step
    in between overwriting it. A hand-written junit of passing testcases makes
    the gate exit 0 with no suite run at all."""
    check_the_gate_reads_the_evidence_this_run_wrote(path)


@every_workflow
def test_no_workflow_overrides_the_shell(path: Path) -> None:
    """Every executed rule here runs blocks under `bash -e`. `shell: bash {0}`
    — at step level or in a `defaults.run` nobody reads — is bash without the
    `-e`, and after it every verdict in this file is about a shell the workflow
    does not use."""
    check_no_workflow_overrides_the_shell(path)


@every_workflow
def test_no_condition_disables_the_chain(path: Path) -> None:
    """A gate that is present but never runs is a gate that is gone, and it is
    worse than a deleted one because a reviewer looking for it finds it.

    `check_the_suite_and_the_gate_are_both_present` reads the step's TEXT.
    Nothing in this file read `if:` at all until this rule, so `if: false` on
    the gate step — or on the job around it — was a full pass on every other
    rule while switching the whole evidence chain off.
    """
    check_no_condition_disables_the_chain(path)


@every_workflow
def test_no_job_can_be_skipped_into_a_pass(path: Path) -> None:
    """A `needs:` on a required job is `if: false` with a different word, and
    GitHub reports a conditionally-skipped required check as Success."""
    check_no_job_can_be_skipped_into_a_pass(path)


@every_workflow
def test_the_suite_line_carries_only_whitelisted_arguments(path: Path) -> None:
    """`--version`, `-h` and `--help` narrow nothing and run nothing. A
    blocklist of narrowing flags has no opinion about any of them."""
    check_the_suite_line_carries_only_whitelisted_arguments(path)


@every_workflow
def test_the_gate_runs_as_a_whole_command(path: Path) -> None:
    """A rule that asks whether the line CONTAINS the gate is satisfied by
    `: python scripts/check_test_results.py <path>`, which runs nothing."""
    check_the_gate_runs_as_a_whole_command(path)


@every_workflow
def test_the_suite_runs_as_a_whole_command(path: Path) -> None:
    """The argument whitelist reads what follows `pytest`; this reads what
    precedes it. `: python -m pytest …` and `PYTEST_PLUGINS=x python -m pytest
    …` were full passes on every other rule."""
    check_the_suite_runs_as_a_whole_command(path)


@every_workflow
def test_the_suite_step_takes_the_checkout_off_the_path(path: Path) -> None:
    """`python -m` searches the working directory first, so a tracked
    `pytest.py` in the checkout is the suite that runs."""
    check_the_suite_step_takes_the_checkout_off_the_path(path)


def test_no_rule_in_this_file_is_vacuous() -> None:
    """Absence must not be how a rule passes.

    Most of the rules here are loops over things a workflow contains: pytest
    invocations, gate invocations, checkouts, Python setups, artifact uploads.
    Every one of them passes trivially when the thing is not there — delete the
    suite step and "the suite is never narrowed" goes green over a repository
    that runs no suite. That is the excluded-market shape the lab rules name: an
    absence reported as a clean call.

    `gate` is counted for the same reason and it closes the corpus-level half of
    the evidence chain: `check_the_suite_and_the_gate_are_both_present` is a
    pairing rule, so deleting the suite step AND the gate step together
    satisfies it, and only this count notices that the last one is gone.

    The counts are asserted across ALL workflows rather than per file, because
    a future workflow that legitimately uploads nothing must not be a failure.
    What must be a failure is the last one disappearing.
    """
    missing = missing_subjects(WORKFLOW_FILES)
    assert not missing, (
        f"Nothing under {WORKFLOWS_DIR} contains: {missing}. The rules above "
        "iterate over these, so with none present they report green having "
        "inspected nothing."
    )


def test_every_real_run_block_is_actually_executed_by_the_swallow_rule() -> None:
    """The executed rule's own anti-vacuity check.

    `swallow_findings` returning nothing means "no configuration swallowed"
    only if a configuration ran at all. A run block that produced no command
    words, or a `run_blocks` that stopped yielding, would return the same empty
    list from having done nothing — the fail-open shape this whole file exists
    to close. So the real workflows are asserted to contain run blocks, and
    those blocks are asserted to contain commands the harness stubs.
    """
    blocks = [
        (path.name, name, block)
        for path in WORKFLOW_FILES
        for name, block in run_blocks(load(path))
    ]
    assert blocks, (
        f"No `run:` block anywhere under {WORKFLOWS_DIR}. The swallow rule "
        "iterates over them, so with none present it reports green having "
        "executed nothing."
    )
    stubbed = {
        (filename, name): command_words(block) for filename, name, block in blocks
    }
    assert any(stubbed.values()), (
        f"No run block yields a single command word: {stubbed}. Every block "
        "would then be executed with nothing to fail, and the rule would pass "
        "over shell it never modelled."
    )


def test_the_real_pytest_invocation_survives_the_line_joining() -> None:
    """The joining introduced for the continuation hole must not lose the very
    line the narrowing rule exists to read.

    This is the regression for the fix itself: if `commands()` ever joins the
    suite invocation onto something else, or drops it, the narrowing rule would
    still report green — over a run it never saw. Asserted across all workflows
    for the reason `test_no_rule_in_this_file_is_vacuous` gives.
    """
    invocations = [
        (path.name, name, line)
        for path in WORKFLOW_FILES
        for name, line in pytest_lines(load(path))
    ]
    assert invocations, (
        "No `pytest` invocation survives `commands()` in any workflow. Either "
        "CI stopped running the suite or the line joining ate the line that "
        "runs it; both make the narrowing rule vacuous."
    )
    for filename, step, line in invocations:
        assert pytest_arguments(line), (
            f"{filename}: step {step!r} invokes pytest with no arguments at "
            f"all after joining ({line!r}), which is what a mis-joined line "
            "looks like from here."
        )


def test_the_secret_accessor_pattern_ignores_prose() -> None:
    """The accessor pattern must stay narrow enough to leave prose legal.

    A workflow that cannot name the rule it obeys stops documenting it, and an
    undocumented rule is the state this whole file exists to leave behind. What
    the real files actually say is not asserted here and no sentence in this
    module claims it: a claim about another file's contents decays exactly like
    a line number, and this docstring used to carry one — "Both real files name
    tests/test_no_secrets_committed.py" — that was wrong about
    ledger-guard.yml. The real files are checked against the pattern directly,
    by `check_no_workflow_references_a_secret` over
    `.github/workflows/*.yml`; what is pinned HERE is the pattern's own
    behaviour on prose shapes.

    The rejecting direction is covered by `test_a_bracket_syntax_secret_is_rejected`
    and `test_the_whole_secrets_context_cannot_be_interpolated`.
    """
    for prose in (
        "tests/test_no_secrets_committed.py",
        "takes the entire secrets guard down",
        "It accesses the `secrets` context nowhere",
        "fails the build if the `secrets` context is ACCESSED anywhere",
        "no secret is reachable from here",
        "rejects the substring `secrets` followed by a dot",
    ):
        assert SECRET_REFERENCE.search(prose) is None, (
            f"The secret accessor pattern matches prose: {prose!r}"
        )


# --------------------------------------------------------------------------
# The self-regression suite: proof that the rules above can actually FAIL.
#
# Everything before this point is parametrised over two files that pass. That
# demonstrates the workflows are clean; it demonstrates nothing about the
# linter. Below, each rule is pointed at a workflow built to break it.
# --------------------------------------------------------------------------

#: The control. This passes every check in `CHECKS`, and every bad workflow
#: below is this text with ONE anchored substitution — so a rejection can only
#: have come from that substitution, and no bad case can pass by accident on
#: some unrelated defect.
GOOD_WORKFLOW = """\
name: Synthetic
"on": [push, pull_request]

permissions:
  contents: read

jobs:
  suite:
    runs-on: ubuntu-latest
    steps:
      - name: Check out the repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1
          persist-credentials: false
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run the suite
        env:
          PYTHONSAFEPATH: '1'
        run: |
          set -euo pipefail
          python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"
      - name: Gate on the results
        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"
      - name: Upload the test evidence
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: ${{ runner.temp }}/junit.xml
          if-no-files-found: error
"""

#: The anchors the mutations below cut against, named once so a change to
#: GOOD_WORKFLOW that orphans one is a loud failure rather than a silent
#: no-op mutation.
TRIGGER_LINE = '"on": [push, pull_request]'
PERMISSIONS_BLOCK = "permissions:\n  contents: read\n"
PYTHON_VERSION_LINE = "python-version: '3.12'"
PERSIST_LINE = "          persist-credentials: false\n"
SUITE_LINE = 'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"'
GATE_STEP = (
    "      - name: Gate on the results\n"
    '        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\n'
)
GATE_COMMAND = 'python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"'
UPLOAD_POLICY = "if-no-files-found: error"


def mutate(anchor: str, replacement: str) -> str:
    """GOOD_WORKFLOW with exactly one substitution, or a loud failure.

    The `assert` is the point: a mutation whose anchor has drifted out of
    GOOD_WORKFLOW would otherwise produce the good text unchanged, and a
    "prove it rejects" test that silently started feeding the linter a clean
    workflow is a self-regression suite that regressed.
    """
    assert anchor in GOOD_WORKFLOW, f"anchor no longer in GOOD_WORKFLOW: {anchor!r}"
    return GOOD_WORKFLOW.replace(anchor, replacement, 1)


def gate_block(*lines: str) -> str:
    """The gate step rewritten as a block scalar carrying `lines`.

    A block scalar and not a flow one: `|| :` ends in a colon, and YAML reads
    `run: cmd || :` as a nested mapping rather than a command.
    """
    body = "".join(f"          {line}\n" for line in lines)
    return mutate(f"        run: {GATE_COMMAND}\n", "        run: |\n" + body)


def workflow(tmp_path: Path, text: str, name: str = "synthetic.yml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def assert_rejects(check: Callable[[Path], None], path: Path) -> None:
    with pytest.raises(AssertionError):
        check(path)


@pytest.mark.parametrize("rule", sorted(CHECKS), ids=sorted(CHECKS))
def test_the_control_workflow_passes_every_rule(tmp_path: Path, rule: str) -> None:
    """The baseline every bad case is measured against.

    Without this, "the linter rejected the bad workflow" would be worth nothing
    — the rejection could be coming from a typo in the YAML rather than from
    the defect under test.
    """
    CHECKS[rule](workflow(tmp_path, GOOD_WORKFLOW))


def test_every_rule_has_a_case_that_proves_it_fires() -> None:
    """The self-regression suite's own anti-vacuity check.

    A rule added to CHECKS with no bad case is a rule nobody has watched fail.
    The names here are the test functions below; each one is asserted to exist
    in this module so a rename cannot quietly retire a proof.
    """
    proofs = {
        "parses_and_declares_a_trigger": "test_a_workflow_with_no_trigger_is_rejected",
        "no_trigger_is_path_filtered": "test_a_paths_filter_is_rejected",
        "permissions_are_declared_and_read_only": (
            "test_write_permissions_are_rejected"
        ),
        "no_step_or_job_continues_on_error": "test_continue_on_error_is_rejected",
        "no_workflow_references_a_secret": "test_a_bracket_syntax_secret_is_rejected",
        "no_workflow_declares_a_secrets_key": "test_secrets_inherit_is_rejected",
        "no_env_mapping_binds_a_provider_credential": (
            "test_an_env_bound_credential_is_rejected"
        ),
        "python_version_is_pinned_to_an_exact_minor": (
            "test_an_unpinned_python_version_is_rejected"
        ),
        "checkout_never_persists_credentials": (
            "test_a_credential_persisting_checkout_is_rejected"
        ),
        "every_piped_run_block_sets_pipefail": (
            "test_a_pipeline_without_pipefail_is_rejected"
        ),
        "no_run_block_swallows_a_failure": "test_a_swallowed_failure_is_rejected",
        "the_suite_is_never_narrowed": "test_a_narrowing_pytest_flag_is_rejected",
        "every_upload_fails_when_there_is_nothing_to_upload": (
            "test_a_warning_upload_policy_is_rejected"
        ),
        "the_suite_and_the_gate_are_both_present": (
            "test_a_missing_end_of_the_evidence_chain_is_rejected"
        ),
        "the_gate_reads_the_evidence_this_run_wrote": (
            "test_a_planted_junit_file_is_rejected"
        ),
        "no_workflow_overrides_the_shell": "test_a_custom_shell_is_rejected",
        "no_condition_disables_the_chain": (
            "test_a_condition_that_can_be_false_on_the_gate_is_rejected"
        ),
        "no_job_can_be_skipped_into_a_pass": (
            "test_a_needs_on_the_required_job_is_rejected"
        ),
        "the_suite_line_carries_only_whitelisted_arguments": (
            "test_an_argument_outside_the_suite_whitelist_is_rejected"
        ),
        "the_gate_runs_as_a_whole_command": (
            "test_a_gate_line_that_only_mentions_the_gate_is_rejected"
        ),
        "the_suite_runs_as_a_whole_command": (
            "test_a_suite_line_that_only_mentions_pytest_is_rejected"
        ),
        "the_suite_step_takes_the_checkout_off_the_path": (
            "test_a_suite_step_without_pythonsafepath_is_rejected"
        ),
    }
    unproven = sorted(set(CHECKS) - set(proofs))
    assert not unproven, (
        f"Rules with no synthetic case proving they fire: {unproven}. A rule "
        "nobody has seen reject anything is a rule that might not work."
    )
    missing = sorted(name for name in proofs.values() if name not in globals())
    assert not missing, f"Named proofs that do not exist in this module: {missing}"


def test_a_workflow_with_no_trigger_is_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_parses_and_declares_a_trigger,
        workflow(tmp_path, mutate(TRIGGER_LINE + "\n", "")),
    )


def test_a_workflow_that_is_not_a_mapping_is_rejected(tmp_path: Path) -> None:
    """`yaml.safe_load` of a list, a bare string or an empty file returns
    something with no `.get`, and the old code would have raised
    AttributeError somewhere downstream instead of naming the problem."""
    for text in ("- not: a workflow\n", "just a string\n", ""):
        assert_rejects(
            check_parses_and_declares_a_trigger, workflow(tmp_path, text)
        )


def test_a_paths_filter_is_rejected(tmp_path: Path) -> None:
    filtered = '"on":\n  push:\n    paths:\n      - \'src/**\'\n'
    assert_rejects(
        check_no_trigger_is_path_filtered,
        workflow(tmp_path, mutate(TRIGGER_LINE + "\n", filtered)),
    )


def test_a_paths_filter_under_bare_on_is_rejected(tmp_path: Path) -> None:
    """Bare `on:` lands under the YAML 1.1 boolean key `True`. A rule that knew
    only the quoted spelling would pass every workflow written the other way,
    which is the same defeat-by-rewording this file was audited for."""
    filtered = "on:\n  push:\n    paths-ignore:\n      - 'docs/**'\n"
    path = workflow(tmp_path, mutate(TRIGGER_LINE + "\n", filtered))
    assert True in load(path), "the bare `on:` key did not land under True"
    assert_rejects(check_no_trigger_is_path_filtered, path)


def test_write_permissions_are_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_permissions_are_declared_and_read_only,
        workflow(tmp_path, mutate("  contents: read", "  contents: write")),
    )


def test_job_level_write_permissions_are_rejected(tmp_path: Path) -> None:
    """Placement is half the rule: a `permissions:` on the job overrides the
    read-only one at the top, so a check that only read the top-level block
    would report clean over a job that can push."""
    assert_rejects(
        check_permissions_are_declared_and_read_only,
        workflow(
            tmp_path,
            mutate(
                "  suite:\n    runs-on: ubuntu-latest\n",
                "  suite:\n    runs-on: ubuntu-latest\n"
                "    permissions:\n      contents: write\n",
            ),
        ),
    )


def test_a_missing_permissions_block_is_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_permissions_are_declared_and_read_only,
        workflow(tmp_path, mutate(PERMISSIONS_BLOCK, "")),
    )


def test_continue_on_error_is_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_no_step_or_job_continues_on_error,
        workflow(
            tmp_path,
            mutate(
                "      - name: Gate on the results\n",
                "      - name: Gate on the results\n        continue-on-error: true\n",
            ),
        ),
    )


def test_a_bracket_syntax_secret_is_rejected(tmp_path: Path) -> None:
    """DEFEAT 3, reproduced and closed.

    `${{ secrets['NAME'] }}` is documented GitHub Actions syntax, equivalent to
    the dot form, and contains no dot. Against the old substring rule this file
    gave a full pass; changing only the bracket to a dot failed. Both spellings
    are rejected now, and both are asserted here so a future narrowing of the
    pattern to one of them is a red build.
    """
    for accessor in (
        "${{ secrets['SOME_TOKEN'] }}",
        "${{ secrets.SOME_TOKEN }}",
        "${{ secrets ['SOME_TOKEN'] }}",
    ):
        assert_rejects(
            check_no_workflow_references_a_secret,
            workflow(
                tmp_path,
                mutate(
                    "      - name: Gate on the results\n",
                    "      - name: Gate on the results\n"
                    "        env:\n"
                    f"          TOKEN: {accessor}\n",
                ),
            ),
        )


def test_the_whole_secrets_context_cannot_be_interpolated(tmp_path: Path) -> None:
    """The attack that was strictly worse than the one being caught.

    `${{ toJSON(secrets) }}` needs neither a dot nor a bracket. It interpolates
    EVERY secret in the repository into one environment variable and thence into
    any log that prints the environment, and against the dot-or-bracket rule it
    was a full pass while `${{ secrets.NAME }}` — which leaks exactly one — was
    rejected. The casing variants are here because GitHub's contexts are
    case-insensitive and the pattern was not.
    """
    for accessor in (
        "${{ toJSON(secrets) }}",
        "${{ toJson( secrets ) }}",
        "${{ toJSON(SECRETS) }}",
        "${{ Secrets.SOME_TOKEN }}",
        "${{ SECRETS['SOME_TOKEN'] }}",
        # No dot, no bracket, no paren at all: the context rendered whole. The
        # punctuation rule could not see these, which is why the expression rule
        # exists beside it.
        "${{ secrets }}",
        "${{ secrets  }}",
        "${{ format('{0}', secrets) }}",
        "${{ fromJSON(toJSON(secrets))['A'] }}",
    ):
        assert_rejects(
            check_no_workflow_references_a_secret,
            workflow(
                tmp_path,
                mutate(
                    "      - name: Gate on the results\n",
                    "      - name: Gate on the results\n"
                    "        env:\n"
                    f"          EVERYTHING: {accessor}\n",
                ),
            ),
        )


def test_secrets_inherit_is_rejected(tmp_path: Path) -> None:
    """A YAML key, not an expression, so no expression rule can reach it.

    `secrets: inherit` on a `uses:` job hands the called workflow every secret
    the repository holds. There is no `${{ }}` in it at all, which is why this
    is a structural rule over the parse rather than another pattern.
    """
    called = (
        "  called:\n"
        "    uses: ./.github/workflows/other.yml\n"
        "    secrets: inherit\n"
    )
    assert_rejects(
        check_no_workflow_declares_a_secrets_key,
        workflow(tmp_path, mutate("jobs:\n", "jobs:\n" + called)),
    )


def test_an_explicit_secrets_block_on_a_called_workflow_is_rejected(
    tmp_path: Path,
) -> None:
    """The named form of the same handover. `inherit` is one spelling of it and
    a mapping of names is another, so the rule is about the KEY."""
    called = (
        "  called:\n"
        "    uses: ./.github/workflows/other.yml\n"
        "    secrets:\n"
        "      TOKEN: a-value\n"
    )
    assert_rejects(
        check_no_workflow_declares_a_secrets_key,
        workflow(tmp_path, mutate("jobs:\n", "jobs:\n" + called)),
    )


def test_a_commented_out_secret_is_rejected(tmp_path: Path) -> None:
    """Checked against the raw text, not the parse: a commented-out credential
    is one uncomment away from a live one."""
    assert_rejects(
        check_no_workflow_references_a_secret,
        workflow(
            tmp_path,
            mutate(
                "      - name: Gate on the results\n",
                "      # TODO: TOKEN: ${{ secrets.SOME_TOKEN }}\n"
                "      - name: Gate on the results\n",
            ),
        ),
    )


@pytest.mark.parametrize("credential", sorted(CREDENTIAL_NAMES))
def test_an_env_bound_credential_is_rejected(tmp_path: Path, credential: str) -> None:
    """Bound on a STEP, which is the placement that defeated the assertion in
    tests.yml: invisible to every other step, so a check standing beside it
    sees an empty environment and reports all clear."""
    assert_rejects(
        check_no_env_mapping_binds_a_provider_credential,
        workflow(
            tmp_path,
            mutate(
                "      - name: Gate on the results\n",
                "      - name: Gate on the results\n"
                "        env:\n"
                f"          {credential}: ''\n",
            ),
        ),
    )


@pytest.mark.parametrize(
    "version", ["3.10", "'3.x'", "'latest'", "'3'", "'3.12.1'", "3"]
)
def test_an_unpinned_python_version_is_rejected(tmp_path: Path, version: str) -> None:
    """Unquoted `3.10` is the YAML float 3.1 — a real 3.1 install request — and
    '3.x' / 'latest' hand the lab whatever interpreter shipped that week."""
    assert_rejects(
        check_python_version_is_pinned_to_an_exact_minor,
        workflow(tmp_path, mutate(PYTHON_VERSION_LINE, f"python-version: {version}")),
    )


def test_a_credential_persisting_checkout_is_rejected(tmp_path: Path) -> None:
    """Omitted is the dangerous case, because the default is `true`."""
    assert_rejects(
        check_checkout_never_persists_credentials,
        workflow(tmp_path, mutate(PERSIST_LINE, "")),
    )
    assert_rejects(
        check_checkout_never_persists_credentials,
        workflow(
            tmp_path, mutate(PERSIST_LINE, "          persist-credentials: true\n")
        ),
    )


def test_a_pipeline_without_pipefail_is_rejected(tmp_path: Path) -> None:
    """`bash -e` is not `bash -eo pipefail`: the pipeline reports its LAST
    command's status, so the failing thing on the left is discarded."""
    piped = (
        "        run: |\n"
        '          python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" '
        '| tee "$RUNNER_TEMP/gate.txt"\n'
    )
    assert_rejects(
        check_every_piped_run_block_sets_pipefail,
        workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", piped)),
    )


def test_turning_pipefail_back_off_is_rejected(tmp_path: Path) -> None:
    """The block opens with `set -euo pipefail`, satisfies the old rule's only
    assertion, and turns the option off again on the line above the pipeline.

    The old check read `lines[0]` and stopped, so this was a full pass. It is
    the pipeline case of `set +e`, and it was allowed while `set +e` itself was
    rejected — a flag banned in one spelling and allowed in another.
    """
    path = workflow(
        tmp_path,
        gate_block(
            "set -euo pipefail",
            "set +o pipefail",
            f'{GATE_COMMAND} | tee "$RUNNER_TEMP/gate.txt"',
        ),
    )
    first = commands([block for _, block in run_blocks(load(path))][-1])[0]
    assert ENABLES_PIPEFAIL.search(first), (
        f"the mutation no longer opens with pipefail ({first!r}), so it does "
        "not reproduce the defect it is named for"
    )
    assert_rejects(check_every_piped_run_block_sets_pipefail, path)


def test_opening_a_piped_block_by_disabling_pipefail_is_rejected(
    tmp_path: Path,
) -> None:
    """`"pipefail" in first` was the old opening test, and `set +o pipefail`
    contains the word. Mentioning the option is not enabling it."""
    assert_rejects(
        check_every_piped_run_block_sets_pipefail,
        workflow(
            tmp_path,
            gate_block(
                "set +o pipefail", f'{GATE_COMMAND} | tee "$RUNNER_TEMP/gate.txt"'
            ),
        ),
    )


def test_turning_pipefail_off_on_the_opening_line_is_rejected(
    tmp_path: Path,
) -> None:
    """The undo written onto the same physical line as the enable.

    Checking `lines[1:]` for the disable left this open: the first line both
    satisfies the opening assertion and cancels it, and there is no second line
    to inspect.
    """
    assert_rejects(
        check_every_piped_run_block_sets_pipefail,
        workflow(
            tmp_path,
            gate_block(
                "set -euo pipefail; set +o pipefail",
                f'{GATE_COMMAND} | tee "$RUNNER_TEMP/gate.txt"',
            ),
        ),
    )


def test_a_printed_pipefail_does_not_count_as_an_enabled_one(
    tmp_path: Path,
) -> None:
    """The option rules read the line with its quoted spans blanked.

    Unanchored and unblanked, a first line of `echo 'set -o pipefail'`
    satisfied the pipefail rule over a block that never set the option — the
    prose about a rule standing in for the rule, which is the failure mode this
    whole file was written against.
    """
    assert_rejects(
        check_every_piped_run_block_sets_pipefail,
        workflow(
            tmp_path,
            gate_block(
                "echo 'set -o pipefail'",
                f'{GATE_COMMAND} | tee "$RUNNER_TEMP/gate.txt"',
            ),
        ),
    )


def test_a_printed_set_plus_e_is_not_a_disabled_errexit(tmp_path: Path) -> None:
    """The accepting direction of the same blanking.

    A workflow that echoes an explanation of the `set +e` rule must not be
    rejected by it; a rule that forbids its own documentation gets deleted along
    with the documentation.
    """
    path = workflow(
        tmp_path,
        gate_block(
            "set -euo pipefail",
            "echo 'this step never writes set +e or set +o pipefail'",
            f"{GATE_COMMAND} || {{ echo '::error::the gate failed'; exit 1; }}",
        ),
    )
    check_no_run_block_swallows_a_failure(path)


def test_a_pipeline_hidden_behind_a_continuation_is_rejected(tmp_path: Path) -> None:
    """The pipe on its own physical line. Before `commands()` joined logical
    lines this still worked by luck — the fragment `| tee ...` carries the pipe
    — but the joined line is what the rule now reads, so it is pinned."""
    piped = (
        "        run: |\n"
        '          python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" \\\n'
        '            | tee "$RUNNER_TEMP/gate.txt"\n'
    )
    path = workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", piped))
    joined = [line for _, block in run_blocks(load(path)) for line in commands(block)]
    assert any("| tee" in line and "check_test_results" in line for line in joined), (
        f"the continuation was not joined: {joined!r}"
    )
    assert_rejects(check_every_piped_run_block_sets_pipefail, path)


# --------------------------------------------------------------------------
# The swallow rule, executed.
# --------------------------------------------------------------------------

#: Every swallow this file knows about, by the shape of the swallow rather than
#: by the punctuation of it. The last group is what round three was defeated
#: through: not one of those five contains a `||`, so the guard clause that
#: decided whether to look at a line by searching it for `||` never examined a
#: single one of them.
SWALLOWS = {
    "or-true": [f"{GATE_COMMAND} || true"],
    "or-colon": [f"{GATE_COMMAND} || :"],
    "or-echo": [f"{GATE_COMMAND} || echo 'no junit'"],
    "or-exit-0": [f"{GATE_COMMAND} || exit 0"],
    "or-brace-exit-0": [
        f"{GATE_COMMAND} || {{ echo 'no junit; nothing to gate on'; exit 0; }}"
    ],
    "or-exit-00": [f"{GATE_COMMAND} || exit 00"],
    "or-bin-true": [f"{GATE_COMMAND} || /bin/true"],
    "or-printf": [f"{GATE_COMMAND} || printf ''"],
    "or-test": [f"{GATE_COMMAND} || test 1 -eq 1"],
    "or-brace-true": [f"{GATE_COMMAND} || {{ true; }}"],
    "or-double": [f"{GATE_COMMAND} && true || true"],
    # The or-list belongs to a DIFFERENT command, and its `exit 1` used to
    # satisfy the rule for the gate's or-list on the same line.
    "exit-belongs-to-another-or-list": [
        f"test -f x || {{ echo 'no file'; exit 1; }}; {GATE_COMMAND} || true"
    ],
    # An `exit 1` inside a string that is printed and never executed.
    "exit-inside-a-quoted-message": [
        f'{GATE_COMMAND} || echo "::error::gate failed; will exit 1 later"'
    ],
    # A `; then` anywhere on the line used to exempt the whole line.
    "swallow-beside-a-then": [f"if true; then echo hi; fi; {GATE_COMMAND} || true"],
    # ATTACK (j) AND ITS FAMILY: no `||` anywhere.
    "if-not-then": [f"if ! {GATE_COMMAND}; then echo '::warning::no junit'; fi"],
    "if-then-else": [f"if {GATE_COMMAND}; then echo ok; else echo 'no junit'; fi"],
    "while-not": [f"while ! {GATE_COMMAND}; do break; done"],
    "bang-prefix": [f"! {GATE_COMMAND}"],
    "set-plus-e": ["set +e", GATE_COMMAND],
    "trap-err-exit-0": ["trap 'exit 0' ERR", GATE_COMMAND],
    "shell-function": [f"gate() {{ {GATE_COMMAND}; }}", "gate || true"],
    "status-captured-then-reported": [
        f"{GATE_COMMAND} && rc=0 || rc=$?",
        'echo "the gate said $rc"',
    ],
    # A PIPELINE WITH NO PIPE CHARACTER. PIPELINE is `(?<!\\|)\\|(?!\\|)`, so
    # none of these three contains anything it can match, and the failing
    # command runs in a subshell the stub preamble's pid probe cannot attribute
    # to the top level either — a full pass on the pipefail rule, the or-list
    # rule and the executed rule simultaneously. No shell option propagates the
    # status out of `<(...)`, which is why the fix rejects the construct rather
    # than demanding an option beside it.
    "process-substitution-tee": [
        "set -euo pipefail",
        f'tee "$RUNNER_TEMP/gate.txt" < <({GATE_COMMAND})',
    ],
    "process-substitution-cat": ["set -euo pipefail", f"cat < <({GATE_COMMAND})"],
    "process-substitution-wc": ["set -euo pipefail", f"wc -l < <({GATE_COMMAND})"],
    # A SWALLOW WITH NO OPERATOR. `&` is not an or-list, not a conditional and
    # not a `set +e`; errexit simply does not apply to an asynchronous command,
    # and `wait` with no argument returns 0 whatever the job did. Measured under
    # `bash -e` with a failing stub: both of these exit 0 where the bare gate
    # exits 1. Only the spelling that ADDS an operator (`gate & || true`) was
    # rejected before, which is rejection by punctuation rather than mechanism.
    "background-then-wait": [f"{GATE_COMMAND} &", "wait"],
    "background-then-carry-on": [f"{GATE_COMMAND} &", "echo 'gate launched'"],
    "background-brace-group": [f"{{ {GATE_COMMAND}; }} &", "wait"],
    "background-subshell": [f"( {GATE_COMMAND} ) &", "wait"],
    # The same capability with no operator on the line at all, found by
    # attacking `BACKGROUND` after it was written. `setsid` returns 0 as soon
    # as it has forked; `coproc` runs the gate in a subshell nothing consults.
    "detached-setsid": [f"setsid {GATE_COMMAND}"],
    "detached-coproc": [f"coproc {GATE_COMMAND}", "wait"],
}


@pytest.mark.parametrize("case", sorted(SWALLOWS), ids=sorted(SWALLOWS))
def test_a_swallowed_failure_is_rejected(tmp_path: Path, case: str) -> None:
    assert_rejects(
        check_no_run_block_swallows_a_failure,
        workflow(tmp_path, gate_block(*SWALLOWS[case])),
    )


def test_the_executed_rule_catches_what_no_or_list_pattern_can_see(
    tmp_path: Path,
) -> None:
    """ATTACK (j), reproduced and closed, and the measurement kept as a test.

    The rule this replaces started `if not OR_LIST.search(line) ... : continue`.
    None of the blocks below contains a `||`, so none of them was ever
    examined, and each one was verified under `bash -e` to exit 0 where the
    house idiom exits 1. Asserted twice over: the textual nets are shown to be
    SILENT on each one — which is what makes them evidence about the executed
    rule rather than about themselves — and then the executed rule is shown to
    reject.
    """
    invisible_to_a_pattern = [
        [f"if ! {GATE_COMMAND}; then echo '::warning::no junit'; fi"],
        [f"if {GATE_COMMAND}; then echo ok; else echo 'no junit'; fi"],
        [f"while ! {GATE_COMMAND}; do break; done"],
        ["trap 'exit 0' ERR", GATE_COMMAND],
        [f"gate() {{ {GATE_COMMAND}; }}", "gate || :"],
    ]
    for lines in invisible_to_a_pattern:
        block = "\n".join(lines) + "\n"
        for line in commands(block):
            if "gate ||" in line:
                continue  # the function case: its second line IS an or-list
            assert not OR_LIST.search(line), (
                f"{line!r} contains an or-list, so it is not evidence that the "
                "executed rule sees further than an or-list pattern"
            )
            assert not unguarded_or_branches(line), (
                f"the textual net already rejects {line!r}"
            )
        assert swallow_findings(block), (
            f"executing {block!r} under stubs did not reveal the swallow"
        )
        assert_rejects(
            check_no_run_block_swallows_a_failure, workflow(tmp_path, gate_block(*lines))
        )


def test_the_rewritten_swallows_defeated_the_blacklist_this_replaced(
    tmp_path: Path,
) -> None:
    """The measurement behind the fix, kept as a test rather than a claim.

    These are the five exact spellings the round-one check grepped for. The
    rewrites below match none of them and are rejected anyway, which is what
    "strictly stronger on this input" means here. If someone ever swaps the
    executed rule back for a list of spellings, this goes red.
    """
    superseded_blacklist = (
        re.compile(r"\|\|\s*true\b"),
        re.compile(r"\|\|\s*:(?:\s|;|$)"),
        re.compile(r"\|\|\s*echo\b"),
        re.compile(r"\|\|\s*exit\s+0\b"),
        re.compile(r"\bset\s+\+e"),
    )
    for rewrite in (
        f"{GATE_COMMAND} || {{ echo 'no junit; nothing to gate on'; exit 0; }}",
        f"{GATE_COMMAND} || exit 00",
        f"if ! {GATE_COMMAND}; then echo '::warning::no junit'; fi",
    ):
        assert not any(pattern.search(rewrite) for pattern in superseded_blacklist), (
            f"{rewrite!r} was already caught by the old blacklist; it is not "
            "evidence that the rule that replaced it is stronger."
        )
        assert_rejects(
            check_no_run_block_swallows_a_failure,
            workflow(tmp_path, gate_block(rewrite)),
        )


@pytest.mark.parametrize(
    "disable",
    ["set +e", "set +eu", "set +o errexit", "set +o pipefail"],
    ids=["+e", "+eu", "+o-errexit", "+o-pipefail"],
)
def test_disabling_errexit_is_rejected(tmp_path: Path, disable: str) -> None:
    """After any of these a failing command no longer fails the step.

    `set +o pipefail` is in this list because the alternation it used to face
    matched the LETTER `e` and the option name `errexit` and stopped there, so
    the pipeline spelling of the same defeat was allowed while `set +e` was
    rejected.
    """
    assert DISABLES_ERREXIT.search(disable), (
        f"{disable!r} is not matched by DISABLES_ERREXIT, so this case proves "
        "nothing about the pattern it is named for"
    )
    assert_rejects(
        check_no_run_block_swallows_a_failure,
        workflow(tmp_path, gate_block(disable, GATE_COMMAND)),
    )


@pytest.mark.parametrize(
    "enabling", ["set -euo pipefail", "set -o pipefail", "set -eo pipefail"]
)
def test_enabling_pipefail_is_not_read_as_disabling_it(enabling: str) -> None:
    """The other direction of the option patterns, which is how a rule gets
    deleted: reject the correct spelling and the cheapest fix is to remove the
    rule that rejected it."""
    assert not DISABLES_ERREXIT.search(enabling)
    assert not DISABLES_PIPEFAIL.search(enabling)
    assert ENABLES_PIPEFAIL.search(enabling)


def test_a_conditional_or_list_is_not_a_swallowed_failure(tmp_path: Path) -> None:
    """The rule must accept the shape both real workflows use, or it would be
    enforced by deleting the credential assertion it is meant to protect.

    `if [ -n "$A" ] || [ -n "$B" ]; then ... exit 1; fi` joins two tests; the
    `||` guards nothing. So does the legitimate failure path
    `cmd || { echo '::error::...'; exit 1; }`.
    """
    path = workflow(
        tmp_path,
        gate_block(
            "set -euo pipefail",
            'if [ -n "${A:-}" ] || [ -n "${B:-}" ]; then',
            "  echo '::error::a credential is in scope'",
            "  exit 1",
            "fi",
            f"{GATE_COMMAND} || {{ echo '::error::the gate failed'; exit 1; }}",
        ),
    )
    check_no_run_block_swallows_a_failure(path)


def test_the_legitimate_failure_path_is_accepted_by_both_nets(
    tmp_path: Path,
) -> None:
    """Acceptance asserted at the level of each net, not only of the whole rule.

    A rule that rejected everything would be enforced by deleting the step, so
    the accepting direction needs its own proof — and it needs to be specific,
    because "the check did not raise" would also be true of a check that had
    quietly stopped inspecting anything.
    """
    legitimate = f"{GATE_COMMAND} || {{ echo '::error::the gate failed'; exit 1; }}"
    assert unguarded_or_branches(legitimate) == []
    assert not DISABLES_ERREXIT.search(legitimate)
    assert swallow_findings(f"set -euo pipefail\n{legitimate}\n") == []
    check_no_run_block_swallows_a_failure(
        workflow(tmp_path, gate_block("set -euo pipefail", legitimate))
    )


def test_an_exit_elsewhere_on_the_line_does_not_excuse_an_or_list() -> None:
    """The per-or-list evaluation, asserted on the helper rather than through a
    whole workflow, so a regression names the thing that regressed.

    Both of these gave a full pass while NONZERO_EXIT was searched over the
    joined line: the first has an `exit 1` belonging to a different command,
    the second has one inside a string that is printed rather than run.
    """
    borrowed = f"test -f x || {{ echo 'no file'; exit 1; }}; {GATE_COMMAND} || true"
    assert unguarded_or_branches(borrowed) == ["true"]
    quoted = f'{GATE_COMMAND} || echo "::error::gate failed; will exit 1 later"'
    assert unguarded_or_branches(quoted) == ["echo"]
    # And the legitimate shape survives being cut into segments: the `;` inside
    # the brace group must not split the branch away from its exit.
    guarded = f"{GATE_COMMAND} || {{ echo '::error::gate failed'; exit 1; }}"
    assert unguarded_or_branches(guarded) == []


def test_a_then_on_the_line_no_longer_exempts_it() -> None:
    """The exemption is claimed per SEGMENT now, not per line.

    CONDITION was searched over the whole joined line, so a line that carried
    `; then` anywhere on it — or merely began with `if` — was exempt in full,
    and moving a `|| true` onto such a line was a complete defeat of the rule.
    Reproduced below with the pattern as it was written then.
    """
    superseded_condition = re.compile(r"^(if|elif|while|until)\b|;\s*then\b")
    line = f"if true; then echo hi; fi; {GATE_COMMAND} || true"
    assert superseded_condition.search(line), (
        "this line no longer reproduces the whole-line exemption it is named for"
    )
    assert unguarded_or_branches(line) == ["true"]
    # The shape the exemption exists for still claims it, because the segment
    # that carries the or-list is the one that starts with `if`.
    condition = 'if [ -n "${A:-}" ] || [ -n "${B:-}" ]; then'
    assert unguarded_or_branches(condition) == []


def test_a_legitimate_failure_path_split_across_a_continuation_is_accepted(
    tmp_path: Path,
) -> None:
    """Joining cuts both ways, and this is the direction that would have made
    the swallow rule unusable.

    `cmd ||` on one line and `{ echo '::error::...'; exit 1; }` on the next is
    one command. Read as physical lines the first fragment is an or-list with
    no exit anywhere in it, so the rule would reject a correct failure path and
    the cheapest way out would be to delete the rule. The same shape ending in
    `exit 0` is still caught, which is what makes this an acceptance rather
    than a hole.
    """
    def split_on(tail: str) -> str:
        return (
            "        run: |\n"
            "          set -euo pipefail\n"
            f"          {GATE_COMMAND} ||\n"
            f"            {tail}\n"
        )

    good = workflow(
        tmp_path,
        mutate(
            f"        run: {GATE_COMMAND}\n",
            split_on("{ echo '::error::the gate failed'; exit 1; }"),
        ),
    )
    joined = [line for _, block in run_blocks(load(good)) for line in commands(block)]
    assert any("||" in line and "exit 1" in line for line in joined), (
        f"the operator continuation was not joined: {joined!r}"
    )
    check_no_run_block_swallows_a_failure(good)

    assert_rejects(
        check_no_run_block_swallows_a_failure,
        workflow(
            tmp_path,
            mutate(
                f"        run: {GATE_COMMAND}\n",
                split_on("{ echo 'never mind'; exit 0; }"),
            ),
            "swallowed.yml",
        ),
    )


def test_process_substitution_is_a_pipeline_no_pipe_pattern_can_see(
    tmp_path: Path,
) -> None:
    """The measurement behind the outright ban, kept as the test.

    `PIPELINE` is `(?<!\\|)\\|(?!\\|)`, so it matches nothing in any of these —
    there is no pipe character in a `<(...)`. The or-list nets see nothing
    either. And the EXECUTED rule is blind too, which is the part that makes
    this a hole rather than a duplicate: the failing command runs in the forked
    subshell that produces the substitution, so the pid probe never attributes
    it to the top level, and in the configuration where only the inner command
    fails the block exits 0 with an empty top-level log.

    That blindness is asserted here, not assumed. It is also why the rule bans
    the construct instead of demanding a shell option beside it: there is no
    option that propagates a process substitution's status — `pipefail` covers
    pipelines and this is not one.
    """
    for line in (
        f'tee "$RUNNER_TEMP/gate.txt" < <({GATE_COMMAND})',
        f"cat < <({GATE_COMMAND})",
        f"wc -l < <({GATE_COMMAND})",
    ):
        blanked = without_quoted_spans(line)
        assert not PIPELINE.search(blanked), (
            f"{line!r} contains a pipe character, so the pipefail rule would "
            "cover it and this is not the hole it is named for"
        )
        assert not OR_LIST.search(blanked)
        assert not unguarded_or_branches(line)
        assert not DISABLES_ERREXIT.search(blanked)
        block = f"set -euo pipefail\n{line}\n"
        assert swallow_findings(block) == [], (
            f"the executed rule now sees into a process substitution ({line!r}); "
            "rewrite this test and the disclosure that goes with it"
        )
        assert PROCESS_SUBSTITUTION.search(blanked), (
            f"the construct pattern does not match {line!r}"
        )
        assert_rejects(
            check_no_run_block_swallows_a_failure,
            workflow(tmp_path, gate_block("set -euo pipefail", line)),
        )


def test_a_backgrounded_gate_is_caught_by_running_it(tmp_path: Path) -> None:
    """FIX 4's executed half, measured rather than asserted from the pattern.

    `gate &` carries no or-list, no conditional, no `set +e` and no redirection.
    Only the spelling that ADDS an operator was ever rejected, which is
    rejection by punctuation rather than by mechanism — the round-two failure
    mode exactly. So the discriminator stays where it was (the pid probe, which
    is what keeps `echo "$(head -n 1 f)"` exempt) and the executed rule grew a
    second failure log with no pid test behind it.

    Asserted in the order the argument runs: the textual nets that existed
    before are silent; the block really does exit 0 with an empty top-level log;
    the second log is not empty; and the rule rejects.
    """
    block = f"set -euo pipefail\n{GATE_COMMAND} &\nwait\n"
    for line in commands(block):
        blanked = without_quoted_spans(line)
        assert not OR_LIST.search(blanked)
        assert not unguarded_or_branches(line)
        assert not DISABLES_ERREXIT.search(blanked)
        assert not PIPELINE.search(blanked)

    result = run_block_under_stubs(block, None, tmp_path)
    assert result.exit_code == 0, (
        f"a backgrounded failing gate no longer exits 0 ({result!r}), so this "
        "case does not reproduce the defect it is named for"
    )
    assert result.top_level_failures == [], (
        "the pid probe now attributes a background job to the top level; if "
        f"that is deliberate, the second log is redundant ({result!r})"
    )
    assert result.any_failures, (
        f"the second failure log did not record the background failure: {result!r}"
    )
    assert swallow_findings(block), "the executed rule did not report the swallow"
    assert_rejects(
        check_no_run_block_swallows_a_failure,
        workflow(tmp_path, gate_block("set -euo pipefail", f"{GATE_COMMAND} &", "wait")),
    )


def test_the_background_pattern_is_not_an_and_list_or_a_redirection() -> None:
    """The accepting direction of `BACKGROUND`, which is the whole reason it is
    a lookaround and not a bare `&`.

    `a && b`, `2>&1` and `cmd &>log` all contain the character. A rule that
    matched it would reject the house idiom `cmd || { ...; }` written with
    `&&`, and would reject every step that redirects stderr — and a rule that
    rejects correct shell is a rule somebody deletes rather than fixes.
    """
    for legitimate in (
        f"{GATE_COMMAND} && echo ok",
        "git cat-file -e HEAD 2>&1",
        "probe &>/dev/null",
        "cmd >&2",
        "a && b && c",
    ):
        assert not BACKGROUND.search(without_quoted_spans(legitimate)), legitimate
    for backgrounded in (f"{GATE_COMMAND} &", "gate & wait", "gate & echo hi"):
        assert BACKGROUND.search(without_quoted_spans(backgrounded)), backgrounded

    # The launcher half reads the blanked line for the same reason every other
    # option rule does: a step that PRINTS an explanation of this rule must not
    # be the thing that trips it.
    assert not ASYNC_LAUNCHER.search(
        without_quoted_spans("echo 'never launch the gate with setsid or coproc'")
    )
    for launched in ("setsid gate", "coproc gate", "setsid  gate --flag"):
        assert ASYNC_LAUNCHER.search(without_quoted_spans(launched)), launched


# --------------------------------------------------------------------------
# The stub harness itself, which is the thing the swallow rule now trusts.
# A harness nobody has watched work is a harness that might be reporting
# "clean" from having executed nothing.
# --------------------------------------------------------------------------


def test_nothing_real_runs_under_the_stub_harness(tmp_path: Path) -> None:
    """The safety claim, executed rather than asserted in a comment.

    Every command word becomes a shell function, PATH points at an empty
    directory inside the sandbox, and the working directory is the sandbox. A
    block whose whole purpose is to write a file must therefore leave no file.
    """
    block = (
        "python -c \"open('pwned', 'w').write('x')\"\n"
        "touch also-pwned\n"
        "/bin/sh -c 'touch third'\n"
    )
    result = run_block_under_stubs(block, None, tmp_path)
    assert result.unmodelled == [], (
        f"a command reached the shell without a stub: {result.unmodelled} "
        f"({result.stderr!r})"
    )
    for name in ("pwned", "also-pwned", "third"):
        assert not (tmp_path / name).exists(), f"{name} was really created"

    # And a block cannot point PATH back at a real directory to get around it.
    escaped = run_block_under_stubs(
        'PATH=/usr/bin:/bin\ntouch escaped\n', None, tmp_path
    )
    assert escaped.exit_code != 0, escaped
    assert not (tmp_path / "escaped").exists(), "PATH was rebuilt and touch ran"


def test_the_stub_harness_reports_a_command_it_could_not_model(
    tmp_path: Path,
) -> None:
    """The fail-closed half. A command assembled at run time is invisible to
    the word scanner, so it reaches bash with no stub — and the harness must
    say so instead of returning a verdict about a block it never modelled.

    This is also the honest disclosure of a real hole: indirection through a
    variable defeats the word scanner. What it does NOT do is defeat the check,
    because "not modelled" is reported as a finding.
    """
    result = run_block_under_stubs(
        'GATE="python scripts/check_test_results.py"\neval "$GATE" || true\n',
        None,
        tmp_path,
    )
    assert result.unmodelled, (
        "an unstubbed command ran and the harness did not notice: "
        f"{result!r}"
    )


def test_the_stub_harness_leaves_the_builtins_alone(tmp_path: Path) -> None:
    """A function shadows a builtin in bash, so a stubbed `true` would make
    `cmd || true` look like a failure path and the swallow would pass.

    Asserted twice: the scanner never collects a builtin or a keyword, and a
    block made only of builtins runs to a clean exit under the harness.
    """
    block = (
        "set -euo pipefail\n"
        "for word in a b; do\n"
        '  if [ -n "$word" ] || true; then\n'
        "    printf '%s\\n' \"$word\"\n"
        "  fi\n"
        "done\n"
    )
    collected = set(command_words(block))
    assert not collected & (SHELL_BUILTINS | SHELL_KEYWORDS), (
        f"the scanner collected a builtin or keyword: {sorted(collected)}"
    )
    result = run_block_under_stubs(block, None, tmp_path)
    assert result.exit_code == 0 and result.unmodelled == [], result


def test_the_stub_harness_distinguishes_a_top_level_failure(tmp_path: Path) -> None:
    """The pid comparison that keeps `echo "$(cmd)"` from being a finding.

    A command inside a substitution runs in a subshell whose failure errexit
    never sees, so counting it would reject a summary line that is not a
    swallow. A command at the top level is the one whose failure the step's
    exit status is supposed to carry.
    """
    top_level = run_block_under_stubs("git status\n", None, tmp_path)
    assert top_level.top_level_failures == ["git"], top_level
    assert top_level.exit_code != 0

    substituted = run_block_under_stubs('echo "$(git status)"\n', None, tmp_path)
    assert substituted.top_level_failures == [], substituted
    assert substituted.exit_code == 0


def test_the_stub_harness_honours_the_requested_failure_set(tmp_path: Path) -> None:
    """`failing=None` fails everything; a set fails only what it names.

    The per-command configurations are the half that reaches a swallow standing
    behind an earlier gate, and the only half that can see `|| /bin/true`. If
    the status argument stopped being honoured they would all silently become
    the same run.
    """
    block = "alpha\nbeta || true\n"
    everything = run_block_under_stubs(block, None, tmp_path)
    assert everything.exit_code != 0, everything

    only_beta = run_block_under_stubs(block, {"beta"}, tmp_path)
    assert only_beta.exit_code == 0 and only_beta.top_level_failures == ["beta"], (
        only_beta
    )
    assert swallow_findings(block), "the per-command pass did not reach the swallow"


def test_a_swallow_behind_an_earlier_gate_still_fires(tmp_path: Path) -> None:
    """With every command failing, the block stops at its first gate and the
    swallow below is never executed. Failing one command at a time is what
    reaches it, and this is the case that proves those runs are not decoration.
    """
    block = f"set -euo pipefail\npytest -q\n{GATE_COMMAND} || true\n"
    assert run_block_under_stubs(block, None, tmp_path).exit_code != 0, (
        "with everything failing the block did not stop at its first gate, so "
        "this case does not reproduce the situation it is named for"
    )
    assert swallow_findings(block), (
        "the swallow behind the first gate was never reached"
    )


def test_the_harness_reads_command_words_out_of_the_shapes_the_workflows_use(
    tmp_path: Path,
) -> None:
    """The word scanner, asserted as behaviour rather than assumed.

    Everything the harness controls depends on this list. A word missed is a
    command the sandbox cannot fail on demand, which is a rule that quietly
    stops testing anything. Comments are excluded because they carry the very
    words the rules ban; redirection targets are excluded because `>/dev/null`
    is not a command; substitutions are included because a command inside one
    still runs.
    """
    assert command_words("git status\n") == ["git"]
    assert command_words('test -z "$(git status --porcelain)"\n') == ["git"]
    assert command_words("cmd >/dev/null\n") == ["cmd"]
    assert command_words("# git status\nls\n") == ["ls"]
    assert command_words("PYTHONPATH=src python script.py\n") == ["python"]
    assert command_words("a && b || c\n") == ["a", "b", "c"]
    assert command_words("if ! gate; then echo x; fi\n") == ["gate"]
    assert command_words("cmd || /bin/true\n") == ["cmd", "/bin/true"]
    assert command_words("for d in x; do probe; done\n") == ["d", "probe"]


def test_commands_joins_the_shapes_bash_joins() -> None:
    """The joining itself, asserted as behaviour rather than assumed.

    Every textual rule downstream reads what this returns, so a regression here
    is a silent hole in all of them at once.
    """
    assert commands("a \\\nb") == ["a b"]
    assert commands("a \\\n  b \\\n  c") == ["a b c"]
    assert commands("a ||\nb") == ["a || b"]
    assert commands("a &&\nb") == ["a && b"]
    assert commands("a |\nb") == ["a | b"]
    assert commands("a\nb") == ["a", "b"]
    assert commands("# a comment\nreal") == ["real"]
    assert commands("real \\\n# still a comment line\n") == ["real"]


def test_the_disclosed_holes_in_the_swallow_rule_are_real() -> None:
    """What still gets through, written down instead of hoped about.

    An honest disclosure beats a guard that looks closed, and a hole nobody
    wrote down is a hole the next round is defeated through. Each entry below
    is asserted to be exactly as open as it is described, so the day one of them
    closes this test goes red and the sentence gets rewritten rather than
    quietly outliving the fix.

    1. `( cmd ) || true` — the failure happens in a subshell, errexit never
       sees it, and the executed rule reports nothing. The TEXTUAL net catches
       it, which is why both nets are run.
    2. `cmd | tee log` with no pipefail — the failure is a pipeline element, in
       a subshell again. `check_every_piped_run_block_sets_pipefail` is the
       rule that covers it, not this one. Its residue is
       `set -euo pipefail; ! cmd | cat`, where pipefail IS set and the `!` then
       consumes the status the pipeline correctly reported: nothing here
       catches that one.
    3. `bash -c 'cmd || true'` — the inner shell is a stub, so the inner text
       is never executed or read. Nothing here catches it.
    4. Indirection through a variable — the command word is assembled at run
       time. The word scanner cannot see it, but the harness REPORTS it as
       unmodelled, so the check still fails; it fails for "I could not model
       this", not for "this swallows".
    5. The failure configurations are keyed on the command WORD, not on the
       occurrence, so two invocations of the same word in one block cannot be
       failed independently: `python a` followed by `python b || true` stops at
       the first `python` in every configuration and the swallow below it is
       never reached. The textual net catches that particular one; a swallow
       with no or-list standing behind an earlier call of the same command
       would not be caught by anything here.
    6. Process substitution — `tee out < <(gate)` — is invisible to the
       executed rule for reason 1: the inner command runs in the forked subshell
       that feeds the substitution, so the pid probe never attributes its
       failure to the top level. Nothing propagates its status either; `set -o
       pipefail` covers pipelines and this is not one. It is caught ONLY by
       `PROCESS_SUBSTITUTION`, a textual ban on the construct — so this hole is
       closed by punctuation, and a spelling of process substitution that is not
       `<(` or `>(` would reopen it. There is no such spelling in bash as of
       this writing, which is the whole reason a construct ban is defensible
       here where a spelling ban was not defensible for `|| true`.
    7. Detaching a command WITHOUT the `&` operator, by a launcher this file
       does not name. `swallow_findings` only consults the second failure log
       when a line carries `BACKGROUND` or `ASYNC_LAUNCHER`, because the pid
       probe has to stay the discriminator that keeps `echo "$(head -n 1 f)"`
       exempt — so something on the line has to say the exit code is not to be
       trusted. `setsid` and `coproc` are named, and that half IS a spelling
       rule: the harness cannot model either, because the LAUNCHER is the
       command word it stubs and the gate behind it is an argument that never
       runs. `systemd-run`, `at`, `batch` and any wrapper script that forks are
       not named and get through both nets. This is hole 3 (`bash -c '...'`) in
       a second costume. The `&` spelling is closed by mechanism; the launcher
       family is closed only as far as it is enumerated, which is exactly the
       shape three previous rounds were defeated through, and it is written
       here rather than claimed shut.

    And two conservatisms in the other direction, recorded because a rule that
    rejects a correct workflow is how a rule gets deleted:

    * the textual net reads the TEXT of an or-list branch, so `cmd || die` —
      where `die` is a function defined earlier in the same block that ends in
      `exit 1` — is rejected even though executing it shows the step failing
      properly. Both nets are run and either one rejecting is a rejection, which
      is the fail-closed choice; the idiom the real workflows use is the inline
      brace group, which both nets accept;
    * `PROCESS_SUBSTITUTION` and `BACKGROUND` are bans on a capability, so a
      legitimate `diff <(a) <(b)` and a legitimate parallel step are rejected
      along with the swallows. Neither workflow uses either, and the header of
      this file says what the alternative is: every rule here has a
      legitimate-looking exception somebody will eventually want, and the
      exceptions are how gates rot.
    """
    subshell = f"( {GATE_COMMAND} ) || true"
    assert swallow_findings(subshell + "\n") == [], (
        "the executed rule now sees into a subshell; rewrite this disclosure"
    )
    assert unguarded_or_branches(subshell) == ["true"]

    unpipefailed = f"{GATE_COMMAND} | tee log"
    assert swallow_findings(unpipefailed + "\n") == [], (
        "the executed rule now sees into a pipeline element; rewrite this "
        "disclosure"
    )
    assert PIPELINE.search(unpipefailed), (
        "the pipefail rule is what covers this shape and it would not match"
    )
    negated = f"set -euo pipefail\n! {GATE_COMMAND} | cat\n"
    assert swallow_findings(negated) == [], (
        "the executed rule now sees a negated pipeline; rewrite this disclosure"
    )
    assert ENABLES_PIPEFAIL.search(commands(negated)[0]), (
        "this case no longer sets pipefail, so the pipefail rule would catch "
        "it and it is not the residue it is described as"
    )

    nested_shell = f"bash -c '{GATE_COMMAND} || true'"
    assert swallow_findings(nested_shell + "\n") == [], (
        "the executed rule now sees inside a nested shell; rewrite this "
        "disclosure"
    )
    assert unguarded_or_branches(nested_shell) == [], (
        "the textual net now sees inside a nested shell; rewrite this "
        "disclosure"
    )

    indirect = 'GATE="python gate.py || true"\neval "$GATE"\n'
    assert unguarded_or_branches(commands(indirect)[0]) == [], (
        "the textual net now reads inside the assignment; rewrite this "
        "disclosure"
    )
    findings = swallow_findings(indirect)
    assert findings and "never modelled" in findings[0], (
        f"indirection is no longer reported as unmodelled: {findings}"
    )

    same_word_twice = "set -euo pipefail\npython a.py\npython b.py || true\n"
    assert swallow_findings(same_word_twice) == [], (
        "the configurations are per occurrence now; rewrite this disclosure"
    )
    assert unguarded_or_branches(commands(same_word_twice)[-1]) == ["true"], (
        "the textual net is what covers the same-word case and it no longer does"
    )

    substituted = f'tee out < <({GATE_COMMAND})'
    assert swallow_findings(f"set -euo pipefail\n{substituted}\n") == [], (
        "the executed rule now sees into a process substitution; rewrite this "
        "disclosure"
    )
    assert unguarded_or_branches(substituted) == [], (
        "the or-list net now sees a process substitution; rewrite this "
        "disclosure"
    )
    assert PROCESS_SUBSTITUTION.search(without_quoted_spans(substituted)), (
        "the construct ban is the only thing covering this shape and it no "
        "longer matches"
    )

    for detached in ("systemd-run --wait gate\n", "at now -f gate.sh\n"):
        assert not BACKGROUND.search(without_quoted_spans(detached)), (
            f"{detached!r} now carries a background operator, so it is not the "
            "no-operator case the disclosure describes"
        )
        assert not ASYNC_LAUNCHER.search(without_quoted_spans(detached)), (
            f"{detached!r} is now a named launcher; rewrite this disclosure"
        )
        assert swallow_findings(detached) == [], (
            f"{detached!r} is now reported; rewrite this disclosure"
        )
    # And the named half, which IS closed, so the sentence above stays honest
    # about which launchers are covered.
    named = "setsid gate\n"
    assert command_words(named) == ["setsid"], (
        "the scanner now looks past the launcher; if it models the command "
        "behind it, the executed rule covers this and the spelling rule is "
        "redundant"
    )
    assert swallow_findings(named) == [], (
        "the executed rule now reports a detached launcher, which would make "
        "ASYNC_LAUNCHER a second net rather than the whole rule"
    )
    assert ASYNC_LAUNCHER.search(without_quoted_spans(named))

    via_a_function = f"die() {{ echo '::error::x'; exit 1; }}\n{GATE_COMMAND} || die\n"
    assert swallow_findings(via_a_function) == [], (
        "executing this shows the step failing properly, which is what makes "
        "the textual net's rejection of it a conservatism rather than a bug"
    )
    assert unguarded_or_branches(commands(via_a_function)[-1]) == ["die"], (
        "the textual net no longer rejects the function form; rewrite this "
        "disclosure"
    )


# --------------------------------------------------------------------------
# The evidence chain: the junit pytest writes IS the junit the gate reads.
# --------------------------------------------------------------------------

#: A workflow with no steps at all, because the whole job is somebody else's
#: file. Not a mutation of GOOD_WORKFLOW, because it is not a defect you can
#: reach by substituting one line — it is the shape where there is nothing left
#: for a run-block rule to read.
DELEGATED_WORKFLOW = """\
name: Delegated
"on": [push, pull_request]

permissions:
  contents: read

jobs:
  everything:
    uses: ./.github/workflows/reusable-tests.yml
"""


@pytest.mark.parametrize(
    "planted",
    [
        'cp fixtures/green.xml "$RUNNER_TEMP/junit.xml"',
        'mv fixtures/green.xml "$RUNNER_TEMP/junit.xml"',
        'tee "$RUNNER_TEMP/junit.xml" < fixtures/green.xml',
        'cat fixtures/green.xml > "$RUNNER_TEMP/junit.xml"',
        'printf \'<testsuite tests="7"/>\' >> "$RUNNER_TEMP/junit.xml"',
        'install -m 644 fixtures/green.xml "$RUNNER_TEMP/junit.xml"',
        'cp fixtures/green.xml "${RUNNER_TEMP}/junit.xml"',
    ],
    ids=["cp", "mv", "tee", "redirect", "append", "install", "braced"],
)
def test_a_planted_junit_file_is_rejected(tmp_path: Path, planted: str) -> None:
    """A step between the suite and the gate that replaces the evidence.

    Every one of these was a full pass on every rule that existed before this
    one: no secret, no swallow, no narrowing flag, no pipeline, no
    continue-on-error, permissions read-only. The gate then grades a file the
    suite did not write, and a hand-written junit of passing testcases exits 0.

    The last case is the same attack with the variable braced. `${RUNNER_TEMP}`
    and `$RUNNER_TEMP` are one file to bash, and a rule that compared the raw
    strings would have seen a path it did not recognise and said nothing.
    """
    assert_rejects(
        check_the_gate_reads_the_evidence_this_run_wrote,
        workflow(
            tmp_path,
            mutate(
                GATE_STEP,
                "      - name: Refresh the evidence\n"
                f"        run: {planted}\n" + GATE_STEP,
            ),
        ),
    )


@pytest.mark.parametrize(
    "gate",
    [
        "python scripts/check_test_results.py tests/fixtures/green.xml",
        'python scripts/check_test_results.py "$RUNNER_TEMP/other.xml"',
        "python scripts/check_test_results.py",
    ],
    ids=["tracked-fixture", "another-path", "no-argument"],
)
def test_a_gate_pointed_away_from_this_run_is_rejected(
    tmp_path: Path, gate: str
) -> None:
    """The gate reading anything but the file this run produced.

    The first is the one that needs no suite at all: a tracked junit with a
    handful of passing testcases in it, committed once, and the gate exits 0
    for ever. The third is the same thing with no path typed — whatever the
    script's default turns out to be is not the evidence this run wrote.
    """
    assert_rejects(
        check_the_gate_reads_the_evidence_this_run_wrote,
        workflow(tmp_path, mutate(GATE_COMMAND, gate)),
    )


@pytest.mark.parametrize(
    "suite",
    [
        "python -m pytest -q -rs",
        'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/other.xml"',
    ],
    ids=["no-junit-flag", "different-path"],
)
def test_a_suite_that_does_not_write_the_gated_file_is_rejected(
    tmp_path: Path, suite: str
) -> None:
    """The producer end of the same joint.

    With no `--junit-xml` at all the gate reads whatever is left at that path
    from an earlier step, an earlier job, or the image; pointed at a second
    path, the suite writes evidence nothing grades and the gate grades evidence
    nothing wrote.
    """
    assert_rejects(
        check_the_gate_reads_the_evidence_this_run_wrote,
        workflow(tmp_path, mutate(SUITE_LINE, suite)),
    )


def test_the_evidence_rule_accepts_the_other_spelling_of_the_same_path(
    tmp_path: Path,
) -> None:
    """The accepting direction, which is how this rule avoids being deleted.

    `${RUNNER_TEMP}/junit.xml` and `$RUNNER_TEMP/junit.xml` are the same file,
    and a workflow that changes brace style must not go red. Both ends written
    the braced way is accepted; only ONE end changed is a different path and is
    covered by the rejection cases above.
    """
    braced = mutate(
        SUITE_LINE,
        'python -m pytest -q -rs --junit-xml="${RUNNER_TEMP}/junit.xml"',
    ).replace(GATE_COMMAND, GATE_COMMAND.replace("$RUNNER_TEMP", "${RUNNER_TEMP}"))
    path = workflow(tmp_path, braced, "braced.yml")
    assert junit_paths_written(load(path)) == {"$RUNNER_TEMP/junit.xml"}, (
        "the brace normalisation stopped working, so this case no longer "
        "exercises what it is named for"
    )
    check_the_gate_reads_the_evidence_this_run_wrote(path)


@pytest.mark.parametrize(
    "written",
    [
        ["python scripts/check_test_results.py \\", '  "$RUNNER_TEMP/junit.xml"'],
        ['python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml";'],
        ['{ python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"; }'],
        [
            'if [ -n "${CI:-}" ]; then :; fi',
            'python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        ],
    ],
    ids=["continuation", "trailing-semicolon", "brace-group", "beside-a-condition"],
)
def test_the_gate_is_recognised_however_the_line_is_punctuated(
    tmp_path: Path, written: list[str]
) -> None:
    """The accepting direction of the argument scan, which is the half that
    would get this rule deleted.

    `shlex.split` hands back `$X;` and `$X"` as ordinary words, so a gate
    written as the last statement of a brace group, or with a trailing
    semicolon, reported a path that compared unequal to the one pytest wrote —
    a rejection of a correct workflow, and the cheapest fix for one of those is
    always to remove the rule. The tail is cut at the first command terminator
    outside quotes before it is split, and these are the shapes that pins.
    """
    path = workflow(
        tmp_path, gate_block("set -euo pipefail", *written), "punctuated.yml"
    )
    assert junit_paths_gated(load(path)) == {"$RUNNER_TEMP/junit.xml"}, (
        f"the gate's argument was misread from {written!r}"
    )
    check_the_gate_reads_the_evidence_this_run_wrote(path)


def test_the_separated_junit_flag_is_read(tmp_path: Path) -> None:
    """`--junit-xml FILE` and `--junitxml=FILE` are the same instruction.

    A rule that read one spelling would be defeated by typing the other, and
    the gate could then be pointed anywhere while the junit set came back
    empty.
    """
    for suite, expected in (
        (
            'python -m pytest -q -rs --junit-xml "$RUNNER_TEMP/junit.xml"',
            "$RUNNER_TEMP/junit.xml",
        ),
        (
            'python -m pytest -q -rs --junitxml="$RUNNER_TEMP/junit.xml"',
            "$RUNNER_TEMP/junit.xml",
        ),
    ):
        path = workflow(tmp_path, mutate(SUITE_LINE, suite), "spelling.yml")
        assert junit_paths_written(load(path)) == {expected}, suite
        check_the_gate_reads_the_evidence_this_run_wrote(path)
        assert_rejects(
            check_the_gate_reads_the_evidence_this_run_wrote,
            workflow(
                tmp_path,
                mutate(SUITE_LINE, suite).replace(
                    GATE_COMMAND,
                    "python scripts/check_test_results.py tests/fixtures/green.xml",
                ),
                "spelling-bad.yml",
            ),
        )


def test_a_missing_end_of_the_evidence_chain_is_rejected(tmp_path: Path) -> None:
    """The gate step deleted outright, and the suite step deleted outright.

    Deleting the gate was a full pass on every rule that existed before this
    one, and it is the cheapest possible defeat of the whole file: `pytest`
    exits 0 on a skipped test, on an xfail, and on a run that collected
    nothing, so the green tick survives with no gate behind it. Every other
    rule here is a loop, and a loop over a step that is gone inspects nothing.
    """
    assert_rejects(
        check_the_suite_and_the_gate_are_both_present,
        workflow(tmp_path, mutate(GATE_STEP, ""), "no-gate.yml"),
    )
    assert_rejects(
        check_the_suite_and_the_gate_are_both_present,
        workflow(
            tmp_path,
            mutate(SUITE_LINE, "echo 'the suite runs somewhere else now'"),
            "no-suite.yml",
        ),
    )


def test_a_job_delegated_to_a_reusable_workflow_is_rejected(tmp_path: Path) -> None:
    """The whole job moved out of view, and the proof that ONLY the new rule
    sees it.

    A `uses:` job has no `steps:`, so it has no run blocks, no pytest line and
    no gate line in this repository at all. Every other rule in CHECKS is a loop
    over one of those and passes this workflow — which is asserted below rather
    than claimed, because "the new rule rejects it" is worth nothing without
    knowing the old ones did not.
    """
    path = workflow(tmp_path, DELEGATED_WORKFLOW, "delegated.yml")
    silent = sorted(
        rule
        for rule in CHECKS
        if rule != "the_suite_and_the_gate_are_both_present"
        and _accepts(CHECKS[rule], path)
    )
    assert silent == sorted(set(CHECKS) - {"the_suite_and_the_gate_are_both_present"}), (
        f"another rule now rejects a delegated job as well ({silent}); rewrite "
        "this case, because it no longer demonstrates what it is named for"
    )
    assert_rejects(check_the_suite_and_the_gate_are_both_present, path)

    # And the same delegation bolted onto the good workflow as a second job,
    # where the suite job is still present and passing.
    assert_rejects(
        check_the_suite_and_the_gate_are_both_present,
        workflow(
            tmp_path,
            mutate(
                "jobs:\n",
                "jobs:\n  delegated:\n"
                "    uses: ./.github/workflows/reusable-tests.yml\n",
            ),
            "second-job.yml",
        ),
    )


def _accepts(check: Callable[[Path], None], path: Path) -> bool:
    try:
        check(path)
    except AssertionError:
        return False
    return True


def test_the_disclosed_holes_in_the_evidence_chain_are_real(tmp_path: Path) -> None:
    """What still separates the gate from the run, written down instead of
    hoped about.

    The three rules added this round pin the chain from the pytest command line
    to the gate's argument. They do NOT pin everything, and the docstrings above
    are written to claim only what is asserted here. Each hole below is asserted
    to be exactly as open as it is described, so closing one turns this red and
    the sentence gets rewritten rather than outliving the fix.

    1. The write ban is a rule about the PATH AS WRITTEN. A step that reaches
       the junit file through a variable this file cannot resolve — an `env:`
       binding, a `$GITHUB_ENV` write, a `$(...)` — names a string that does not
       contain the junit path, so the planted write is invisible. The
       assignment itself IS caught when it happens in a run block, because that
       line names the path and is neither producer nor gate; it is the mapping
       spellings that get through.
    2. A step-level `uses:` on a local composite action can run the suite, the
       gate, or both, entirely out of view. The JOB-level `uses:` is rejected;
       this one cannot be, because `actions/checkout`, `actions/setup-python`
       and `actions/upload-artifact` are how both real workflows are written.
       With both steps hidden inside one action there is no pytest line and no
       gate line, the pairing rule is satisfied by having nothing to pair, and
       only `missing_subjects` across the whole directory notices — and only
       when it is the last one.
    3. WHICH `check_test_results.py` runs is not pinned. The rule matches the
       file name anywhere on the line, so a copy of the script vendored
       somewhere else, or the tracked one edited to exit 0, satisfies it. This
       file reads `.github/workflows/`; what the gate script does when it reads
       a junit belongs to the tests that cover that script.
    4. `check_no_workflow_overrides_the_shell` forbids an explicit override. It
       does NOT pin the runner's implicit default, and GitHub's default shell is
       `bash -e {0}` on Linux and macOS but `pwsh` on Windows — so moving a job
       to a Windows runner changes the shell every executed rule in this file
       grades blocks under, with no `shell:` key appearing anywhere.
    5. `check_no_workflow_overrides_the_shell` reads the key `shell` ANYWHERE in
       the document, so a mapping that uses that word for something else — a
       `strategy.matrix` dimension named `shell`, or a `with:` input named
       `shell` on a composite action — is judged as if it were a shell
       declaration. That is a conservatism and not a hole: it rejects, it does
       not admit. It is recorded because a rule that rejects a legitimate
       workflow is the kind somebody deletes rather than narrows, and the
       narrowing to make (matching only step-level and `defaults.run` keys)
       would reintroduce the placement blindness that made this rule necessary.
    6. A SECOND pytest invocation writing the SAME junit path is accepted. The
       rule pins the path, not which run's result survives at it, so a second
       run overwrites the evidence the gate then grades. That second run has to
       pass `check_the_suite_is_never_narrowed` like the first, which means the
       narrowing this buys is exactly the narrowing that rule already discloses:
       `cd` and `working-directory:`, neither of which is a flag.
    """
    hidden_path = mutate(
        GATE_STEP,
        "      - name: Refresh the evidence\n"
        "        env:\n"
        "          J: ${{ runner.temp }}/junit.xml\n"
        '        run: cp fixtures/green.xml "$J"\n' + GATE_STEP,
    )
    check_the_gate_reads_the_evidence_this_run_wrote(
        workflow(tmp_path, hidden_path, "indirect-write.yml")
    )
    written_out = mutate(
        GATE_STEP,
        "      - name: Refresh the evidence\n"
        '        run: J="$RUNNER_TEMP/junit.xml"; cp fixtures/green.xml "$J"\n'
        + GATE_STEP,
    )
    assert_rejects(
        check_the_gate_reads_the_evidence_this_run_wrote,
        workflow(tmp_path, written_out, "visible-write.yml"),
    )

    composite = mutate(
        "      - name: Run the suite\n"
        "        env:\n"
        "          PYTHONSAFEPATH: '1'\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        f"          {SUITE_LINE}\n" + GATE_STEP,
        "      - name: Run the suite and gate it\n"
        "        uses: ./.github/actions/suite\n",
    )
    hidden = workflow(tmp_path, composite, "composite.yml")
    check_the_suite_and_the_gate_are_both_present(hidden)
    check_the_gate_reads_the_evidence_this_run_wrote(hidden)
    assert missing_subjects([hidden]) == ["gate", "pytest"], (
        "the corpus count is the only thing left covering a composite action "
        "and it no longer reports the absence"
    )

    vendored = mutate(
        GATE_COMMAND,
        'python vendor/check_test_results.py "$RUNNER_TEMP/junit.xml"',
    )
    check_the_gate_reads_the_evidence_this_run_wrote(
        workflow(tmp_path, vendored, "vendored.yml")
    )

    windows = mutate("    runs-on: ubuntu-latest\n", "    runs-on: windows-latest\n")
    check_no_workflow_overrides_the_shell(workflow(tmp_path, windows, "windows.yml"))

    unrelated_key = mutate(
        "  suite:\n    runs-on: ubuntu-latest\n",
        "  suite:\n    runs-on: ubuntu-latest\n"
        "    strategy:\n      matrix:\n        shell: [pwsh]\n",
    )
    assert_rejects(
        check_no_workflow_overrides_the_shell,
        workflow(tmp_path, unrelated_key, "matrix-shell.yml"),
    )

    twice = mutate(
        GATE_STEP,
        "      - name: And again\n"
        '        run: python -m pytest -q --junit-xml="$RUNNER_TEMP/junit.xml"\n'
        + GATE_STEP,
    )
    second_run = workflow(tmp_path, twice, "twice.yml")
    check_the_gate_reads_the_evidence_this_run_wrote(second_run)
    check_the_suite_is_never_narrowed(second_run)
    assert len(list(pytest_lines(load(second_run)))) == 2, (
        "the second invocation was not parsed as one, so this case does not "
        "exercise what it is named for"
    )


# --------------------------------------------------------------------------
# The shell the executed rules grade the workflow under.
# --------------------------------------------------------------------------

#: The three places a `shell:` can be set, by the text that puts it there. The
#: two `defaults.run` placements are the ones that apply to every step in the
#: job or the file while appearing on none of them, which is the same
#: invisible-placement shape as the step-level credential binding that defeated
#: tests.yml's own assertion.
SHELL_PLACEMENTS: dict[str, Callable[[str], str]] = {
    "step": lambda value: mutate(
        "      - name: Gate on the results\n",
        f"      - name: Gate on the results\n        shell: {value}\n",
    ),
    "job-defaults": lambda value: mutate(
        "  suite:\n    runs-on: ubuntu-latest\n",
        "  suite:\n    runs-on: ubuntu-latest\n"
        f"    defaults:\n      run:\n        shell: {value}\n",
    ),
    "workflow-defaults": lambda value: mutate(
        PERMISSIONS_BLOCK,
        PERMISSIONS_BLOCK + f"\ndefaults:\n  run:\n    shell: {value}\n",
    ),
}


@pytest.mark.parametrize("placement", sorted(SHELL_PLACEMENTS))
@pytest.mark.parametrize(
    "value",
    [
        "bash {0}",
        "/bin/bash {0}",
        "bash --noprofile {0}",
        "bash -c {0}",
        "pwsh",
        "python",
        "sh {0}",
        "'bash  {0}'",
        '"bash "',
        "Bash",
        "[bash]",
    ],
)
def test_a_custom_shell_is_rejected(
    tmp_path: Path, placement: str, value: str
) -> None:
    """Every executed rule in this file runs blocks under `bash -e`, and
    nothing read `shell:` at any level.

    `bash {0}` is the quiet one: it is still bash, it still looks like the
    default, and it drops the `-e`. After it a failing command in the middle of
    a block does not fail the step, so every `swallow_findings` verdict here is
    about a shell the workflow does not use. `pwsh` and `python` are not bash at
    all, and the two `defaults.run` placements apply to steps that carry no
    `shell:` of their own.

    Rejection is by SHAPE and not by the string `{0}`: any value that is not
    EXACTLY the keyword `bash` or `sh` is a custom command line — a doubled
    space, a trailing space that only survives because the YAML quoted it, a
    capital letter GitHub's keyword table does not carry, and a list where a
    string belongs.
    """
    assert_rejects(
        check_no_workflow_overrides_the_shell,
        workflow(tmp_path, SHELL_PLACEMENTS[placement](value), "shell.yml"),
    )


@pytest.mark.parametrize("placement", sorted(SHELL_PLACEMENTS))
@pytest.mark.parametrize("value", ["bash", "sh"])
def test_the_bare_shell_keywords_are_accepted(
    tmp_path: Path, placement: str, value: str
) -> None:
    """The accepting direction. `shell: bash` is GitHub's own keyword form and
    it runs `bash --noprofile --norc -eo pipefail {0}` — strictly stronger than
    the harness's `bash -e`, so a block that survives the harness survives it.
    A rule that rejected the keyword would be enforced by deleting the rule."""
    check_no_workflow_overrides_the_shell(
        workflow(tmp_path, SHELL_PLACEMENTS[placement](value), "shell-ok.yml")
    )


def test_the_shell_rule_reads_every_placement_it_claims_to(tmp_path: Path) -> None:
    """The mutations are asserted to land where they say they land.

    A `defaults:` block written at the wrong indentation parses into some other
    mapping, and the rejection would then be coming from a placement the test
    is not named for — the self-regression suite regressing quietly, which is
    what `mutate`'s own assert exists to stop one level up.
    """
    for placement, place in sorted(SHELL_PLACEMENTS.items()):
        document = load(workflow(tmp_path, place("pwsh"), "placed.yml"))
        if placement == "workflow-defaults":
            assert document["defaults"]["run"]["shell"] == "pwsh"
        elif placement == "job-defaults":
            assert document["jobs"]["suite"]["defaults"]["run"]["shell"] == "pwsh"
        else:
            steps = document["jobs"]["suite"]["steps"]
            gates = [step for step in steps if step.get("name") == "Gate on the results"]
            assert len(gates) == 1 and gates[0]["shell"] == "pwsh"


# --------------------------------------------------------------------------
# The narrowing rule.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flag",
    [
        "-x",
        "-xq",
        "-k",
        "-m",
        "-qk",
        "--exitfirst",
        "--maxfail=1",
        "--ignore=tests/test_power.py",
        "--ignore-glob=tests/test_*.py",
        "--deselect=tests/test_power.py::test_one",
        "--collect-only",
        "--co",
        "--last-failed",
        "--lf",
        "--stepwise",
        "--sw",
        "--stepwise-skip",
        "--sw-skip",
        "--stepwise-reset",
        "--sw-reset",
        "--override-ini=testpaths=tests/test_power.py",
        "-o",
        "-qo",
        # The config-file family: the same mechanism as --override-ini with no
        # key to name. All four spellings, because the short one takes its
        # argument glued to the letter and clusters behind an accepted flag.
        "--config-file=ci.ini",
        "-cci.ini",
        "-qcci.ini",
        "--confcutdir=tests",
        # Not a narrowing at all: a disarming. It leaves the junit claiming a
        # pass where the strict-xfail marker had written a failure.
        "--runxfail",
    ],
)
def test_a_narrowing_pytest_flag_is_rejected(tmp_path: Path, flag: str) -> None:
    """DEFEAT 4, reproduced and closed.

    `-x` was banned and `--exitfirst` was not; `--ignore` was banned and
    `--ignore-glob` was not. The aliases here were taken from `pytest --help`
    (pytest 9.1.1) rather than from memory, which is how `--co`, `--lf`, `--sw`
    and the `--sw-reset` pair turned up.

    The config-file family arrived the same way `--override-ini` did: by
    attacking the rule after it was written. `-c FILE` and `--config-file=FILE`
    hand pytest a different ini wholesale — testpaths, addopts and all — and
    `--confcutdir` stops conftest.py being loaded above a directory. Neither was
    in either flag set, though the comment above `--override-ini` already said
    that a flag which reconfigures rather than selects is still a selection.
    """
    assert_rejects(
        check_the_suite_is_never_narrowed,
        workflow(
            tmp_path,
            mutate(
                SUITE_LINE,
                'python -m pytest -q -rs %s --junit-xml="$RUNNER_TEMP/junit.xml"'
                % flag,
            ),
        ),
    )


def test_every_named_narrowing_alias_is_in_the_set_that_is_proved_to_fire() -> None:
    """The enumeration in the comment above NARROWING_PYTEST_ALIAS_FLAGS, the
    set itself and the parametrisation above it must agree.

    They did not: `--stepwise-reset` and `--sw-reset` were in none of the three
    while the comment claimed the set came from reading `pytest --help` for
    every option that ends the run early or picks a subset. A comment that
    describes a sweep it did not survive is the same failure mode as a rule
    that describes a check it does not perform.
    """
    proved = set(
        test_a_narrowing_pytest_flag_is_rejected.pytestmark[0].args[1]
    )
    unproved = sorted(
        flag
        for flag in NARROWING_PYTEST_ALIAS_FLAGS | NARROWING_PYTEST_LONG_FLAGS
        if not any(argument.split("=", 1)[0] == flag for argument in proved)
    )
    assert not unproved, (
        f"Flags banned with no case proving the ban fires: {unproved}"
    )


@pytest.mark.parametrize(
    "flag", ["-q", "-rs", "-vv", "--tb=short", "--durations=10", "--failed-first"]
)
def test_a_non_narrowing_pytest_flag_is_accepted(tmp_path: Path, flag: str) -> None:
    """The other half of the rule. A narrowing check that rejected everything
    would be enforced by deleting the pytest step, and then
    `test_no_rule_in_this_file_is_vacuous` would be the only thing left."""
    check_the_suite_is_never_narrowed(
        workflow(
            tmp_path,
            mutate(
                SUITE_LINE,
                'python -m pytest -q -rs %s --junit-xml="$RUNNER_TEMP/junit.xml"'
                % flag,
            ),
        )
    )


@pytest.mark.parametrize(
    "positional",
    [
        "tests/test_power.py",
        "tests",
        "tests/test_power.py::test_one",
        "tests/test_no_secrets_committed.py tests/test_contract_strings.py",
        "./tests/",
    ],
)
def test_a_positional_selection_is_rejected(tmp_path: Path, positional: str) -> None:
    """The bigger half of DEFEAT 5, reproduced and closed.

    `--ignore=tests/test_power.py` was rejected while the positional
    `tests/test_power.py` — the same selection, one punctuation mark cheaper —
    was never looked at, because the loop inspected only arguments beginning
    with `-`. The fourth case is the one that would have satisfied the junit
    manifest gate as well: name the required guard modules and nothing else, and
    CI runs a fraction of the suite and reports green over it.
    """
    assert_rejects(
        check_the_suite_is_never_narrowed,
        workflow(
            tmp_path,
            mutate(
                SUITE_LINE,
                'python -m pytest -q -rs %s --junit-xml="$RUNNER_TEMP/junit.xml"'
                % positional,
            ),
        ),
    )


def test_pytest_addopts_in_an_env_mapping_is_rejected(tmp_path: Path) -> None:
    """The narrowing with no command line at all.

    pytest reads PYTEST_ADDOPTS as if the flags had been typed, so every rule
    that reads the invocation sees a clean one over a narrowed run. Checked at
    every level for the reason the credential rule is: a step-level `env:` is
    invisible to a check standing beside it.
    """
    for placement, text in (
        (
            "step",
            mutate(
                "          PYTHONSAFEPATH: '1'\n",
                "          PYTHONSAFEPATH: '1'\n"
                "          PYTEST_ADDOPTS: '-x --ignore=tests/test_power.py'\n",
            ),
        ),
        (
            "workflow",
            mutate(
                PERMISSIONS_BLOCK,
                PERMISSIONS_BLOCK + "\nenv:\n  PYTEST_ADDOPTS: '--collect-only'\n",
            ),
        ),
    ):
        assert_rejects(
            check_the_suite_is_never_narrowed,
            workflow(tmp_path, text, f"addopts-{placement}.yml"),
        )


@pytest.mark.parametrize(
    "line",
    [
        'echo "PYTEST_ADDOPTS=-x" >> "$GITHUB_ENV"',
        "export PYTEST_ADDOPTS=--collect-only",
        "PYTEST_ADDOPTS='-k gate' python -m pytest -q",
    ],
    ids=["github-env", "export", "prefix"],
)
def test_pytest_addopts_set_from_the_shell_is_rejected(
    tmp_path: Path, line: str
) -> None:
    """The placement that is in no mapping and on no pytest command line.

    Found by attacking the `env:` rule after writing it. A step that writes
    `PYTEST_ADDOPTS=-x` into `$GITHUB_ENV` narrows every LATER step, and the
    step that runs the suite then shows a clean invocation with no `env:`
    anywhere near it — which is the same invisible-placement trick as the
    step-level credential binding that defeated tests.yml's own assertion.
    """
    assert_rejects(
        check_the_suite_is_never_narrowed,
        workflow(
            tmp_path,
            mutate(
                f"        run: {GATE_COMMAND}\n",
                f"        run: |\n          {line}\n",
            ),
        ),
    )


def test_the_disclosed_holes_in_the_narrowing_rule_are_real(tmp_path: Path) -> None:
    """What still narrows the suite without tripping this rule.

    Written down for the same reason the swallow rule's disclosure is: the
    round that gets defeated is the round that believed the guard was closed.
    Each one is asserted to be exactly as open as it is described, so closing
    it turns this red and the sentence gets rewritten instead of outliving the
    fix.

    1. Changing WHERE pytest collects from, rather than what it collects:
       `cd tests/unit && python -m pytest` and the YAML `working-directory:`
       both hand pytest a smaller tree with a command line this rule reads as
       clean. Two spellings of one mechanism, and neither is a flag.
    2. Building the PYTEST_ADDOPTS name out of pieces — `PYTEST_ADD""OPTS=-x`,
       or a printf that assembles it — which the token rule cannot see. It is
       the same indirection hole the stub harness has, and unlike that one
       nothing here reports it.
    """
    moved = mutate(
        SUITE_LINE,
        'cd tests/unit && python -m pytest -q --junit-xml="$RUNNER_TEMP/j.xml"',
    )
    check_the_suite_is_never_narrowed(workflow(tmp_path, moved, "moved.yml"))

    directory = mutate(
        "      - name: Run the suite\n",
        "      - name: Run the suite\n        working-directory: tests/unit\n",
    )
    check_the_suite_is_never_narrowed(workflow(tmp_path, directory, "wd.yml"))

    for assembled in ('export PYTEST_ADD""OPTS=-x', "export PYTEST_${X}ADDOPTS=-x"):
        assert not PYTEST_ADDOPTS_TOKEN.search(assembled), (
            f"{assembled!r} is matched by the token rule now; rewrite this "
            "disclosure"
        )


def test_a_narrowing_flag_behind_a_backslash_continuation_is_rejected(
    tmp_path: Path,
) -> None:
    """DEFEAT 1, reproduced and closed.

    `commands()` returned physical lines and `pytest_lines()` yielded only the
    physical line carrying the word `pytest`, so everything after a backslash
    was invisible to this rule. It is not an exotic input: ledger-guard.yml
    writes its own `check_ledger_append_only` invocation in exactly this shape.
    """
    continued = (
        "python -m pytest -q -rs \\\n"
        '            -k "not slow" \\\n'
        '            --junit-xml="$RUNNER_TEMP/junit.xml"'
    )
    path = workflow(tmp_path, mutate(SUITE_LINE, continued))
    lines = [line for _, line in pytest_lines(load(path))]
    assert lines and "-k" in pytest_arguments(lines[0]), (
        f"the continuation was not joined before scanning: {lines!r}"
    )
    assert_rejects(check_the_suite_is_never_narrowed, path)


def test_a_second_pytest_invocation_on_a_continued_line_is_rejected(
    tmp_path: Path,
) -> None:
    """`&&` at end of line continues too, and the two invocations become one
    logical line.

    `pytest_arguments` reads the tail after the FIRST `pytest`, so the second
    command's flags land in that tail and must still be caught. This is the
    case that would break if the tail were ever trimmed at the next command
    separator as a tidy-up.
    """
    continued = (
        'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml" &&\n'
        "            python -m pytest --collect-only"
    )
    path = workflow(tmp_path, mutate(SUITE_LINE, continued))
    lines = [line for _, line in pytest_lines(load(path))]
    assert len(lines) == 1 and "--collect-only" in lines[0], (
        f"the `&&` continuation was not joined into one line: {lines!r}"
    )
    assert_rejects(check_the_suite_is_never_narrowed, path)


def test_a_warning_upload_policy_is_rejected(tmp_path: Path) -> None:
    """`warn` is the default, and it is what let the CBB lab's 1.3M-credit
    purchase upload nothing and stay green."""
    for policy in ("warn", "ignore"):
        assert_rejects(
            check_every_upload_fails_when_there_is_nothing_to_upload,
            workflow(tmp_path, mutate(UPLOAD_POLICY, f"if-no-files-found: {policy}")),
        )
    assert_rejects(
        check_every_upload_fails_when_there_is_nothing_to_upload,
        workflow(tmp_path, mutate("          " + UPLOAD_POLICY + "\n", "")),
    )


def test_an_empty_or_missing_directory_yields_no_workflow_files(
    tmp_path: Path,
) -> None:
    """`test_the_workflow_directory_is_not_empty` is only a gate if the thing
    it reads actually reports emptiness. Both fail-open shapes are here: the
    directory emptied, and the directory gone."""
    empty = tmp_path / "empty"
    empty.mkdir()
    assert workflow_files_in(empty) == []
    assert workflow_files_in(tmp_path / "absent") == []
    (empty / "notes.md").write_text("not a workflow\n", encoding="utf-8")
    assert workflow_files_in(empty) == []
    kept = empty / "a.yml"
    kept.write_text(GOOD_WORKFLOW, encoding="utf-8")
    assert workflow_files_in(empty) == [kept]


def test_a_workflow_with_none_of_the_subjects_reports_them_missing(
    tmp_path: Path,
) -> None:
    """The anti-vacuity rule, proved to fire.

    A workflow with no pytest run, no gate, no checkout, no Python setup and no
    upload makes five of the rules above pass by having nothing to iterate over.
    This is what turns that into a red build.

    `gate` matters most of the five here, because it is the one that is ALSO
    invisible to the pairing rule: delete the suite step and the gate step
    together and `check_the_suite_and_the_gate_are_both_present` is satisfied —
    neither end outlives the other — while the repository has no merge gate at
    all. Only the count notices.
    """
    absent = ["checkout", "gate", "pytest", "python-version", "upload"]
    hollow = (
        'name: Hollow\n"on": [push]\npermissions:\n  contents: read\n'
        "jobs:\n  nothing:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - name: Do nothing\n        run: 'true'\n"
    )
    path = workflow(tmp_path, hollow)
    assert missing_subjects([path]) == absent
    assert missing_subjects([]) == absent
    assert missing_subjects([workflow(tmp_path, GOOD_WORKFLOW, "good.yml")]) == []

    # And the pairing rule really is silent on the same file, which is what
    # makes the count a second rule rather than a duplicate of the first.
    check_the_suite_and_the_gate_are_both_present(path)


GATE_WITH_CONDITION = (
    "      - name: Gate on the results\n"
    "        if: {condition}\n"
    '        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\n'
)

SUITE_STEP_TEXT = (
    "      - name: Run the suite\n"
    "        env:\n"
    "          PYTHONSAFEPATH: '1'\n"
    "        run: |\n"
    "          set -euo pipefail\n"
    '          python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"\n'
)


@pytest.mark.parametrize(
    "condition",
    [
        "false",
        "${{ false }}",
        "github.event_name == 'schedule'",
        "${{ !cancelled() && false }}",
        "success() && false",
    ],
)
def test_a_condition_that_can_be_false_on_the_gate_is_rejected(
    tmp_path: Path, condition: str
) -> None:
    """Every spelling of switching the gate off while leaving it on the page.

    `if: false` is the cheap one; the rest are the ones that read as ordinary
    CI hygiene. All five were full passes on every other rule in this file,
    because nothing else here reads `if:` at all.
    """
    assert_rejects(
        check_no_condition_disables_the_chain,
        workflow(
            tmp_path,
            mutate(GATE_STEP, GATE_WITH_CONDITION.format(condition=condition)),
        ),
    )


def test_a_condition_on_the_suite_step_is_rejected(tmp_path: Path) -> None:
    """The other end of the chain. A suite that does not run leaves the gate
    reading a stale or absent junit — a different failure behind the same tick.
    """
    guarded = SUITE_STEP_TEXT.replace(
        "      - name: Run the suite\n",
        "      - name: Run the suite\n        if: github.ref == 'refs/heads/never'\n",
        1,
    )
    assert_rejects(
        check_no_condition_disables_the_chain,
        workflow(tmp_path, mutate(SUITE_STEP_TEXT, guarded)),
    )


def test_a_job_level_condition_over_the_chain_is_rejected(tmp_path: Path) -> None:
    """One `if:` on the job switches every step inside it off at once, and the
    steps themselves stay clean for a reader to find."""
    assert_rejects(
        check_no_condition_disables_the_chain,
        workflow(
            tmp_path,
            mutate(
                "  suite:\n    runs-on: ubuntu-latest\n",
                "  suite:\n    if: false\n    runs-on: ubuntu-latest\n",
            ),
        ),
    )


def test_always_is_the_one_condition_the_chain_may_carry(tmp_path: Path) -> None:
    """The real gate carries `if: always()` so it still fires when an earlier
    step failed. A rule banning every `if:` would reject the correct workflow,
    and a rule that rejects correct work is a rule somebody deletes."""
    check_no_condition_disables_the_chain(
        workflow(
            tmp_path,
            mutate(GATE_STEP, GATE_WITH_CONDITION.format(condition="always()")),
        )
    )


# --------------------------------------------------------------------------
# `needs:`, the whitelisted suite line, the pinned gate, and the safe path.
#
# Four rules, one round, all found the same way: by asking what a green tick
# on a REQUIRED check is actually evidence of. It is evidence that the check
# reported success. Whether anything ran is a separate question, and these are
# the four answers that were "nothing did".
# --------------------------------------------------------------------------


PREP_JOB = (
    "jobs:\n"
    "  prep:\n"
    "    if: false\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: echo prep\n"
    "\n"
    "  suite:\n"
)


def test_a_needs_on_the_required_job_is_rejected(tmp_path: Path) -> None:
    """The one-line defeat of the whole file, measured before it was closed.

    At 4454b20, tests.yml with a `prep` job carrying `if: false` and
    `needs: prep` on the tests job passed every rule in this module. GitHub
    skips the dependent job and reports the skipped required check as Success,
    so the PR is mergeable with no suite behind it. `check_no_condition_
    disables_the_chain` cannot see it: the `if:` is on a job that runs no part
    of the evidence chain, and the chain's own job carries no condition at all.
    """
    assert_rejects(
        check_no_job_can_be_skipped_into_a_pass,
        workflow(
            tmp_path,
            mutate("  suite:\n", PREP_JOB).replace(
                "    runs-on: ubuntu-latest\n    steps:\n"
                "      - name: Check out the repository",
                "    needs: prep\n    runs-on: ubuntu-latest\n    steps:\n"
                "      - name: Check out the repository",
                1,
            ),
            "needs.yml",
        ),
    )


def test_a_matrix_on_the_required_job_is_rejected(tmp_path: Path) -> None:
    """`strategy:` is `needs:` with a different word: a matrix that expands to
    nothing produces no job, and a required context with no job behind it is a
    check nobody ever waited for."""
    assert_rejects(
        check_no_job_can_be_skipped_into_a_pass,
        workflow(
            tmp_path,
            mutate(
                "  suite:\n    runs-on: ubuntu-latest\n",
                "  suite:\n    strategy:\n      matrix:\n        include: []\n"
                "    runs-on: ubuntu-latest\n",
            ),
            "matrix.yml",
        ),
    )


def test_a_condition_on_any_job_is_rejected(tmp_path: Path) -> None:
    """A second job carrying `if:` is harmless on its own — it becomes the
    attack the moment something `needs:` it, and the two edits arrive
    separately. `check_no_condition_disables_the_chain` looks only at jobs that
    hold the chain, so a conditional neighbour was invisible to it."""
    assert_rejects(
        check_no_job_can_be_skipped_into_a_pass,
        workflow(tmp_path, mutate("  suite:\n", PREP_JOB), "neighbour.yml"),
    )


@pytest.mark.parametrize(
    "argument",
    ["--version", "-h", "--help", "--co", "-x", "--tb=short", "tests/test_power.py"],
    ids=["version", "dash-h", "help", "collect-only", "exitfirst", "tb", "positional"],
)
def test_an_argument_outside_the_suite_whitelist_is_rejected(
    tmp_path: Path, argument: str
) -> None:
    """The three at the front are the reason this rule is a whitelist.

    `--version`, `-h` and `--help` are in no set of narrowing flags anywhere in
    this file, because they do not narrow: each makes pytest exit 0 having run
    nothing and written no junit at all (measured, pytest 9.1.1, with
    `--junit-xml` present on the same command line). The rest are here to show
    the whitelist also subsumes what the blocklist already caught.
    """
    assert_rejects(
        check_the_suite_line_carries_only_whitelisted_arguments,
        workflow(
            tmp_path,
            mutate(SUITE_LINE, f"python -m pytest {argument} -q -rs "
                               '--junit-xml="$RUNNER_TEMP/junit.xml"'),
            "argument.yml",
        ),
    )


@pytest.mark.parametrize(
    "junit",
    ["junit.xml", "tests/junit.xml", "$GITHUB_WORKSPACE/junit.xml", "/tmp/junit.xml"],
    ids=["bare", "in-the-tree", "workspace", "absolute"],
)
def test_a_junit_path_outside_the_runner_temp_is_rejected(
    tmp_path: Path, junit: str
) -> None:
    """Evidence written into the checkout can be evidence that was committed.

    `tests/junit.xml` is the one that mattered: a tracked file of passing
    testcases at that path, beside a suite line that exits 0 without writing
    anything, satisfies the gate AND leaves `git status --porcelain` empty.
    """
    assert_rejects(
        check_the_suite_line_carries_only_whitelisted_arguments,
        workflow(
            tmp_path,
            mutate(SUITE_LINE, f'python -m pytest -q -rs --junit-xml="{junit}"')
            .replace(GATE_COMMAND,
                     f'python scripts/check_test_results.py "{junit}"', 1),
            "elsewhere.yml",
        ),
    )


def test_a_junit_path_naming_a_tracked_file_is_rejected(tmp_path: Path) -> None:
    """The second cut, exercised where it can actually fire.

    Under `$RUNNER_TEMP` nothing is tracked, so this clause is unreachable
    today through the prefix rule above it — which is exactly why it has a case
    of its own. It is what remains if somebody later widens the prefix rule,
    and a clause nobody has watched fire is a clause that might not work.
    """
    tracked = sorted(tracked_paths())[0]
    assert_rejects(
        check_the_suite_line_carries_only_whitelisted_arguments,
        workflow(
            tmp_path,
            mutate(
                SUITE_LINE,
                f'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/{tracked}"',
            ).replace(
                GATE_COMMAND,
                f'python scripts/check_test_results.py "$RUNNER_TEMP/{tracked}"',
                1,
            ),
            "tracked-evidence.yml",
        ),
    )


def test_the_suite_line_this_repository_uses_is_accepted(tmp_path: Path) -> None:
    """The accepting direction, without which a whitelist is just a ban.

    Both junit spellings and both brace styles, because a rule that rejected a
    correct line is a rule that gets deleted rather than fixed.
    """
    for suite in (
        'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"',
        'python -m pytest -q -rs --junitxml="${RUNNER_TEMP}/junit.xml"',
        'python -m pytest -rs -q --junit-xml "$RUNNER_TEMP/junit.xml"',
    ):
        check_the_suite_line_carries_only_whitelisted_arguments(
            workflow(tmp_path, mutate(SUITE_LINE, suite), "accepted.yml")
        )


@pytest.mark.parametrize(
    "suite",
    [
        ': python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"',
        'echo python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"',
        'true python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"',
        'PYTEST_PLUGINS=disarm python -m pytest -q -rs '
        '--junit-xml="$RUNNER_TEMP/junit.xml"',
        'env PYTEST_PLUGINS=disarm python -m pytest -q -rs '
        '--junit-xml="$RUNNER_TEMP/junit.xml"',
        'python -m coverage run -m pytest -q -rs '
        '--junit-xml="$RUNNER_TEMP/junit.xml"',
    ],
    ids=["colon", "echo", "true", "assignment", "env", "wrapped"],
)
def test_a_suite_line_that_only_mentions_pytest_is_rejected(
    tmp_path: Path, suite: str
) -> None:
    """The words in front of `pytest`, which no rule read until this one.

    The first three were measured at 5072f97, in the real tests.yml, leaving
    every test in this module passing: they run nothing while the line still
    reads correctly. The two assignment shapes hand pytest a plugin list with
    no flag on the line for any other rule to see, and the `PYTEST_PLUGINS=`
    spelling was measured the same way. The last one is the accepted-looking
    shape that is rejected on purpose: `coverage run -m pytest` is a different
    program in command position with its own view of what to collect, and if it
    is ever wanted it is an edit to this rule with a reason beside it.
    """
    assert_rejects(
        check_the_suite_runs_as_a_whole_command,
        workflow(tmp_path, mutate(SUITE_LINE, suite), "mentioned.yml"),
    )


def test_the_suite_line_this_repository_uses_reads_as_a_whole_command(
    tmp_path: Path,
) -> None:
    """The accepting direction, and `python3` as well as `python` because both
    are named in `PYTHON_INTERPRETERS` and a set with an untried member is an
    enumeration nobody has checked."""
    for suite in (SUITE_LINE, SUITE_LINE.replace("python ", "python3 ", 1)):
        check_the_suite_runs_as_a_whole_command(
            workflow(tmp_path, mutate(SUITE_LINE, suite), "whole-command.yml")
        )


@pytest.mark.parametrize(
    "line",
    [
        ': python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'echo python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'true python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'python -c "pass" scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
    ],
    ids=["colon", "echo", "true", "dash-c"],
)
def test_a_gate_line_that_only_mentions_the_gate_is_rejected(
    tmp_path: Path, line: str
) -> None:
    """A no-op in command position, and every textual rule is satisfied.

    Measured at 4454b20: tests.yml with `: python scripts/check_test_results.py
    "$RUNNER_TEMP/junit.xml"` passed every rule in this module, and `bash -e`
    exits 0 on that line. The path still matches what pytest wrote, the script
    name is still there, the step still carries no condition — and nothing runs.
    """
    assert_rejects(
        check_the_gate_runs_as_a_whole_command,
        workflow(tmp_path, gate_block("set -euo pipefail", line), "mention.yml"),
    )


def test_a_suite_step_without_pythonsafepath_is_rejected(tmp_path: Path) -> None:
    """`python -m` prefers the checkout, so the checkout can be the suite.

    Measured on this repository: a root `pytest.py` holding `raise
    SystemExit(0)` made `python -m pytest -q` exit 0 with nothing collected,
    and the same tree with `PYTHONSAFEPATH=1` ran the whole suite.
    """
    assert_rejects(
        check_the_suite_step_takes_the_checkout_off_the_path,
        workflow(
            tmp_path,
            mutate("        env:\n          PYTHONSAFEPATH: '1'\n", ""),
            "unsafe-path.yml",
        ),
    )
    assert_rejects(
        check_the_suite_step_takes_the_checkout_off_the_path,
        workflow(
            tmp_path,
            mutate("          PYTHONSAFEPATH: '1'\n", "          PYTHONSAFEPATH: '0'\n"),
            "safe-path-off.yml",
        ),
    )


def _suite_step_blocks() -> list[tuple[str, str, str]]:
    """(workflow, step name, run block) for every step that runs the suite."""
    found: list[tuple[str, str, str]] = []
    for path in WORKFLOW_FILES:
        for name, block in run_blocks(load(path)):
            if any(re.search(r"\bpytest\b", line) for line in commands(block)):
                found.append((path.name, name, block))
    return found


def test_the_suite_step_is_executed_and_not_merely_written(tmp_path: Path) -> None:
    """OBSERVED: an interpreter is entered, at the top level, with `-m pytest`.

    `check_the_suite_runs_as_a_whole_command` says the line READS as a command.
    This says it RAN: the block goes through the stub harness with nothing set
    to fail, and the invocation log must show `python -m pytest`. `:`, `echo`
    and `true` are builtins the harness leaves real, so a line that hides the
    suite behind one of them records no invocation at all — the difference a
    rule about text cannot see, and the reason the gate has this test too.
    """
    steps = _suite_step_blocks()
    assert steps, (
        "No step in .github/workflows runs the suite, so this test observed "
        "nothing. An absence is not a pass."
    )
    for workflow_name, step_name, block in steps:
        result = run_block_under_stubs(block, set(), tmp_path)
        assert not result.unmodelled, (
            f"{workflow_name}: step {step_name!r} used commands the harness "
            f"could not model ({result.unmodelled}), so its verdict is not "
            "about the suite."
        )
        invoked = [
            entry for entry in result.invocations
            if entry.split()[0] in PYTHON_INTERPRETERS
            and entry.split()[1:3] == ["-m", SUITE_MODULE]
        ]
        assert invoked, (
            f"{workflow_name}: step {step_name!r} completed without entering "
            f"{sorted(PYTHON_INTERPRETERS)} with `-m {SUITE_MODULE}`. Top-level "
            f"invocations recorded: {result.invocations}. The suite is written "
            "in this step and this step does not run it."
        )


@pytest.mark.parametrize(
    "line",
    [
        ': python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"',
        'echo python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"',
    ],
    ids=["colon", "echo"],
)
def test_the_executed_suite_rule_sees_a_suite_that_did_not_run(
    tmp_path: Path, line: str
) -> None:
    """The synthetic bad input for the observation above. A log that is never
    empty proves nothing by being non-empty."""
    result = run_block_under_stubs(line, set(), tmp_path)
    invoked = [
        entry for entry in result.invocations
        if entry.split()[0] in PYTHON_INTERPRETERS
        and entry.split()[1:3] == ["-m", SUITE_MODULE]
    ]
    assert not invoked, (
        f"The harness recorded {result.invocations} for {line!r}. That line "
        "runs a builtin with the suite as an argument; if the suite shows up "
        "as invoked, the invocation log cannot tell a run suite from a "
        "mentioned one."
    )


def _gate_step_blocks() -> list[tuple[str, str, str]]:
    """(workflow, step name, run block) for every step that invokes the gate."""
    found: list[tuple[str, str, str]] = []
    for path in WORKFLOW_FILES:
        for name, block in run_blocks(load(path)):
            if any(GATE_SCRIPT in line for line in commands(block)):
                found.append((path.name, name, block))
    return found


def test_the_gate_step_is_executed_and_not_merely_written(tmp_path: Path) -> None:
    """OBSERVED: the interpreter is entered, at the top level, with the script.

    The textual pin above says the line reads as a whole command. This says the
    command RAN: the block goes through the stub harness with nothing set to
    fail, and the invocation log must show `python` entered in the top-level
    shell with `scripts/check_test_results.py` as its first argument. `:`,
    `echo` and `true` are builtins the harness deliberately leaves real, so a
    line that hides the gate behind one of them records no invocation at all —
    which is the difference a rule about text cannot see.
    """
    steps = _gate_step_blocks()
    assert steps, (
        "No step in .github/workflows invokes the gate, so this test observed "
        "nothing. An absence is not a pass."
    )
    for workflow_name, step_name, block in steps:
        result = run_block_under_stubs(block, set(), tmp_path)
        assert not result.unmodelled, (
            f"{workflow_name}: step {step_name!r} used commands the harness "
            f"could not model ({result.unmodelled}), so its verdict is not "
            "about the gate."
        )
        invoked = [
            entry for entry in result.invocations
            if entry.split()[0] in PYTHON_INTERPRETERS
            and entry.split()[1:2] == [GATE_SCRIPT_PATH]
        ]
        assert invoked, (
            f"{workflow_name}: step {step_name!r} completed without entering "
            f"{sorted(PYTHON_INTERPRETERS)} with {GATE_SCRIPT_PATH} as its first "
            f"argument. Top-level invocations recorded: {result.invocations}. "
            "The gate is written in this step and this step does not run it."
        )


@pytest.mark.parametrize(
    "line",
    [
        ': python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'echo python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
    ],
    ids=["colon", "echo"],
)
def test_the_executed_gate_rule_sees_a_gate_that_did_not_run(
    tmp_path: Path, line: str
) -> None:
    """The synthetic bad input for the observation above.

    Without this, "the invocation log contained the gate" would be worth
    nothing: a log that is never empty proves nothing by being non-empty.
    """
    result = run_block_under_stubs(line, set(), tmp_path)
    invoked = [
        entry for entry in result.invocations
        if entry.split()[0] in PYTHON_INTERPRETERS
        and entry.split()[1:2] == [GATE_SCRIPT_PATH]
    ]
    assert not invoked, (
        f"The harness recorded {result.invocations} for {line!r}. That line "
        "runs a builtin with the gate as an argument; if the gate shows up as "
        "invoked, the invocation log cannot tell a run gate from a mentioned "
        "one and the rule above is decorative."
    )


@pytest.mark.parametrize(
    "junit",
    ["$RUNNER_TEMP/../junit.xml", "${{ runner.temp }}/../workspace/junit.xml"],
    ids=["one-level", "into-the-workspace"],
)
def test_a_junit_path_that_climbs_out_of_the_runner_temp_is_rejected(
    tmp_path: Path, junit: str
) -> None:
    """The prefix rule is a claim about WHERE the file lands, and `..` breaks
    the claim while satisfying the test. Found by attacking the prefix clause
    after writing it, which is the only way that clause was ever going to be
    checked."""
    assert_rejects(
        check_the_suite_line_carries_only_whitelisted_arguments,
        workflow(
            tmp_path,
            mutate(SUITE_LINE, f'python -m pytest -q -rs --junit-xml="{junit}"')
            .replace(GATE_COMMAND,
                     f'python scripts/check_test_results.py "{junit}"', 1),
            "climbing.yml",
        ),
    )


def test_a_step_that_reassigns_runner_temp_is_rejected(tmp_path: Path) -> None:
    """The other way to defeat a prefix rule: leave the prefix alone and change
    what it points at. `RUNNER_TEMP=$GITHUB_WORKSPACE` written into `$GITHUB_ENV`
    applies to every later step, and both the pytest line and the gate line go
    on reading exactly as they do today."""
    assert_rejects(
        check_the_suite_line_carries_only_whitelisted_arguments,
        workflow(
            tmp_path,
            mutate(
                "      - name: Run the suite\n",
                "      - name: Move the evidence\n"
                '        run: echo "RUNNER_TEMP=$GITHUB_WORKSPACE" >> "$GITHUB_ENV"\n'
                "      - name: Run the suite\n",
            ),
            "moved-temp.yml",
        ),
    )
