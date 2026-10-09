# The operating contract

This is the file a session reads before it changes anything here. It records
the rules the lab lives by, the strings its automation hard-codes, and the two
decisions that are never Claude's to make.

`src/ncaaf_betting_lab/leagues.py` cites this file for the reasoning behind the
five-lab separation; that reasoning is below, and it is the expensive half of
this contract.

---

## What this lab is, said without optimism

An **NCAAF betting research lab**. College football, and only college football.
Its product is evidence, not picks, and the honest summary of the evidence so
far is short: **every measured result to date is a null.**

* Steps 2 through 4 returned **no demonstrated edge** on 2021-2025 free priced
  history — book coherence, line movement as a detector, and outlier-versus-
  consensus betting. The single actionable finding is internal and costs money
  rather than making it: this lab's margin model prices a fixture at a
  dispersion of 20.5-21.9 points when the realised figure is **15.3, on n =
  3,864 games** (CI [14.81, 15.77] at the x1.395 correction in force when it
  was measured). The held-out scoring that established the over-dispersion is a
  separate and smaller sample: **n = 797 games** (2025)
  (`data/outputs/ncaaf_steps_2_to_5.md`).
* Step 5 asked whether this lab's own ratings correct the closing price. Over
  **3,124 games** the corrected slope is -0.0196, interval [-0.1369, +0.0978] —
  **no demonstrated edge**, and the interval sits entirely below the 0.143 a
  paying strategy needs, so ratings do not re-enter the architecture. The late-
  season split (**n = 2,183**) has an upper bound of +0.1647 and rules nothing
  out in either direction (`data/outputs/ratings_residual.md`).
* The cumulative ledger stands at **95 distinct hypotheses**, which widens any
  new 95% interval by **x1.77** (`data/outputs/experiment_ledger.json`;
  checked 2026-10-09). It read 92 and x1.76 until the nightly-form study added
  three, and 78 and x1.742 before the opener study added 14. The ledger is the
  record; this sentence is a copy of it. **`experiment_ledger.md` still renders
  92**, on purpose: the allowlist receipt pins its checksum as evidence, so
  re-rendering it fails the policy gate until Cooper decides whether the
  receipt's evidence is refreshed. Read the JSON.
* A **nightly form rating** and a **quarterback-change flag**, learned from
  each night's results and cfbfastR's free play-level file, were registered
  (`docs/preregistered_nightly_form.md`) and measured on 2022-2025 before
  reaching the card: **no demonstrated edge** against the close (n = 3,126) or
  the open (n = 3,117), and the starter flag too (n = 2,322)
  (`data/outputs/nightly_form.md`). The card prints both beside the price as
  context; neither moves a probability.

### What exists today, and what does not

Be precise about this. A session that assumes machinery it cannot find will
describe a run that never happened.

**Exists.** The settlement source (cfbfastR's committed CSV — a file download,
no key, no rate limit) with schedules for 2021-2026 cached under `data/raw/`.
The league registry, the market registry, the fail-closed provider policy
loader, the coverage precondition, the kickoff guard, `selection_key()`, the
margin model, the power and positive-control instruments, the append-only
experiment ledger, and six report modules. **The card path**, added
2026-10-01: team identity by id (`providers/team_names.py`, `fixtures.py`), the
provider adapter (`providers/odds_api.py`), measured margin and total shapes
anchored on the market's consensus line (`models/shapes.py`, `models/total.py`,
`reports/card_pricing.py`), the card (`reports/gameday_card.py`), the forward
ledger (`forward_evidence.py`), and `scripts/run_gameday_card.py` /
`scripts/card_feed.py` to run and publish it. Three workflows: `Tests`,
`Ledger Guard`, and `NCAAF Gameday Refresh` — the one that holds a credential
and writes, under a scoped exemption in `tests/test_workflows.py`
(`GAMEDAY_REPLACEMENTS`) that replaces three rules for that one file with
narrower ones, each proved to fire. **Every module under `src/` and `scripts/` imports** — a weaker
claim than it looks, and one that was false until it was enforced; see below.
**The suite
passes with ZERO skips** on a clean
requirements-only clone — no count is written here, because the count moves
whenever a guard gains a case and a stale absolute is worse than no number.
That property is enforced rather than reported, in two places.
`scripts/check_test_results.py` parses the junit XML and fails the build on any
skip — a collection-phase one included, measured: pytest writes a module-level
`skip` or `importorskip` into the XML as `<testcase classname=""
name="tests.test_x"><skipped message="collection skipped">` — any xfail, any
xpass from a marker that did not write `strict=False`, any failure or error, an
empty run, or a required guard module that is absent or contributed zero tests.
The root `conftest.py` is the other place, and it covers what the XML cannot:
it refuses a run that arrived NARROWED (`addopts`, `PYTEST_ADDOPTS`,
`--deselect`, `-k`, `--ignore`, asked of the live `config` rather than matched
in a command line), and it compares the test functions each required guard
module defines against the ones pytest is still holding. That hole was measured
rather than supposed: `--deselect` on one credential guard, written into
`addopts`, left that guard out of the run with everything else passing and the
junit gate exited 0, because the evidence file records what ran and never what
the configuration removed. Note the
shape of that xpass clause: `xfail_strict = true` in `pyproject.toml` sets the
DEFAULT and only the default. A marker overrides it per test, and the xpass of
a test marked `xfail(strict=False)` reaches the XML as a bare `<testcase/>` no
reader can tell from a pass. Established by running it rather than by reading
the flag: pytest reports the test as xpassed, exits 0, and the gate then exits
0 reporting zero xfails. The claim is written at the hole's real width, because
a gate described as closed is a gate nobody re-checks — and the width is wider
still in two directions that were also run: remove `xfail_strict` or set it
false and EVERY xpass goes invisible rather than just the marked one, and
`--runxfail` on the pytest command line makes the marker inert so no xpass is
recorded at all. The first is why the flag is a dependency; the second is a
flag that disarms a gate rather than narrowing a run. An earlier revision of
this paragraph, and of tests.yml's header, said no rule sorted `--runxfail`
into any banned set. That was false when it was written: it is in
`NARROWING_PYTEST_LONG_FLAGS` in `tests/test_workflows.py`, and it has been
there since that file was written — both arrived in `4454b20`. The sentence
that replaced it overclaimed the other way, so here is the width each rule
really has, run at `5072f97` rather than asserted. ON the pytest command line
the arguments are a whitelist — `-q`, `-rs`, one junit path under
`$RUNNER_TEMP` — so a flag nobody enumerated is rejected for not being on the
list; and the words in front of `pytest` are pinned as a whole command
separately, because until they were, `: python -m pytest …` and
`PYTEST_PLUGINS=disarm python -m pytest …` in the real `tests.yml` left every
test in that file passing. OFF the command line the whitelist decides nothing: `addopts` and
`PYTEST_ADDOPTS` reach pytest as if typed, and what refuses them is the root
`conftest.py` refusing BOTH channels wholesale — any value at all, so
`PYTEST_ADDOPTS=--runxfail` and `addopts = "--runxfail"` each exit 1 before a
test runs. A plugin loaded into the run is neither, and gap 5 in
`tests/test_the_guards_exist.py::test_known_gaps_that_still_get_through` names
the shape of it that is still open.

This paragraph used to promise that two skips would resolve themselves. They did
resolve, but not for the stated reason, and one of the reasons was never true:
`.gitignore` makes `data/raw/` untrackable, so the event-id skip could not have
been cleared by a provider fetch. **No skip resolves itself. A skip is resolved
by someone writing the thing.**

And a green suite was never a claim that the package imports. Two modules under
`src/` raised `ModuleNotFoundError` while the suite passed over both with zero
skips, because **no test imported either one** and the two things that read
every file under `src/` both stop at the parse: `compileall` byte-compiles a
module without executing its imports, and
`tests/test_league_registry_is_the_only_place.py` uses `ast.parse`. Neither can
see a file that parses and will not load. `selection.py` imported a `season`
module that was never ported — so `selection_key()` was listed above as
existing while it could not be imported, which is the shape of overstatement
this section exists to prevent — and `reports/clv.py` imported a
`forward_evidence` module that was never ported either, with
`reports.props_backtest` missing behind it. `season.py` was ported (its
calendar and text half only; `data/cfbfastr.py` already owns schedule loading
here). `clv.py` was **removed**: it was a byte-identical copy of the NFL lab's,
it needed a props backtest this lab has ruled out of scope, and it carried that
lab's measured numbers — 272 games, 55.7% of wagers unmoved — as if they were
this league's, which the pooling rule forbids outright.
`tests/test_every_module_imports.py` is what makes the next one red instead of
invisible; it is in the gate's `REQUIRED_MODULES`, so deleting it is red too.
It walks `scripts/` as well as `src/` — every script guards its work behind
`if __name__ == "__main__"`, so importing one runs nothing, and a script that
stopped doing so would start doing its work inside the suite and be caught at
once. It is a floor and not coverage: it asserts that a module loads and
nothing about what the module then does. The byte-compile step in `tests.yml`
is now largely subsumed by it and is kept anyway, because it runs before the
suite and does not depend on pytest collecting anything.

**Does not exist yet.** **No provider fetch has ever run**: the card path is
code, and the first fetch happens on the first `NCAAF Gameday Refresh` run with
the `NCAAF_ODDS_API_KEY` secret set. Until then no price has been bought and no
event id is cached. **All ten markets are allowlisted**, and have been since
2026-09-28, by a receipt Claude wrote on Cooper's instruction — see *The one
receipt Claude wrote* below. Once the workflow runs, **the card can print
selections**, and each one is an opinion that cleared the card's bars with **no
demonstrated edge**; the card says so above every selection table, in those
words. Only the spread, total, moneyline and their ladders carry an opinion;
team totals and the first-half markets are priced as no-opinion with a stated
reason. **Every market's `retained` field is `None`** — no retention probe has
run for college football. `None` means unprobed: `False` would be a finding and
`True` would be a guess. The `daily_credit_cap` is **1,200**, agreed by Cooper
on 2026-10-01 and derived from the real schedule by
`scripts/estimate_credit_cost.py` (`data/outputs/ncaaf_credit_cost.md`).

Do not write prose that implies otherwise. Every claim this lab will ever make
about college football rests on evidence that does not exist yet.

---

## The hard rules

CI exists to enforce these. They are not style.

- Never print, write, compare, or commit an API key. Secrets are referenced by
  NAME only.
- Never weaken a gate. A gate that passes when it should fail is worse than no
  gate.
- An excluded market is never a pass, an avoid, or a no-value call. Absence is
  never a pass.
- The five labs (NFL, NCAAF, NHL, EPL, CBB) must NEVER import from each other.
- The experiment ledger is append-only. A ledger that shrinks is a correction
  factor that lies.
- State the sample size next to every measured number.
- Never place a bet, never automate one, never sign a human acceptance receipt
  on Cooper's behalf.

---

## The contract table

Every string below is hard-coded in automation that does not raise when it is
wrong. A renamed workflow, branch, issue or secret produces no error: the
scheduled run simply stops arriving, and that looks exactly like the lab going
quiet — the one failure a lab whose product is evidence cannot afford, because
the evidence it stops gathering cannot be gathered later.

`tests/test_contract_strings.py` fails the build if any of these disappears
from this table. **These are deliberately not the NFL lab's strings**; that
repository owns `Football Gameday Refresh` and `FOOTBALL_ODDS_API_KEY`.

| String | What holds it | What a rename breaks |
|:---|:---|:---|
| `NCAAF Gameday Refresh` | The scheduled workflow's `name:` | Its runs stop appearing under the name a required status check and every `gh run list` filter look for |
| `.github/workflows/ncaaf-gameday-refresh.yml` | That workflow's path | `gh workflow run` and `workflow_dispatch` address a workflow by file name; a moved file 404s rather than failing |
| `card-feed` | The branch the frozen card and its evidence are pushed to | The feed keeps committing, to a branch nobody reads. Shared with a sibling lab, one league's frozen opinions overwrite the other's |
| `NCAAF Betting Lab — Claude Operating Home` | The issue every run posts its status into, matched literally by `gh issue list --jq` | **The em dash is load-bearing.** A hyphen matches nothing, the run posts nowhere, and a degraded run goes unseen |
| `Selections changed` | The marker a run writes when today's card differs from the last one | The notice still posts and every reader's filter stops matching it, so a change reads as a quiet day |
| `NCAAF_ODDS_API_KEY` | The name of the GitHub secret holding the provider credential | Two labs on one credential cannot be told apart in the provider's usage accounting, and a quota exhausted by one starves the other's fetch — which reads in the reports as a market nobody quoted |

Two notes on that last row. The **name** belongs in this repository; the
**value** never does. `tests/test_contract_strings.py` asserts *that specific
distinction*, and the honest thing to record about it is its reach: it walks
the repository's **`*.py` files only** and fails if a value appears to be
assigned beside the name. So a value pasted into a YAML workflow, a Markdown
note, a JSON fixture or an untracked scratch file is **outside that test's
scope**. Covering those is a different guarantee — a scan of what git TRACKS
whatever the extension, plus a check for the shape of a key rather than for a
name — and `tests/test_no_secrets_committed.py` is where that one lives. Note
what is asserted and what is not: the two GUARANTEES are what this contract
pins. Which module holds which, and what either file does or does not know
about, is a claim about another file's contents that decays exactly like a line
number, so check the overlap rather than assuming it from a sentence written
here. Absence of a finding from a narrow guard is not evidence of a clean
repository.

And the secret's name is not the variable name the provider code reads: `providers/env_file.py` still allowlists
`FOOTBALL_ODDS_API_KEY`, inherited from the port. The gameday workflow has to
map one to the other explicitly, and the test job asserts **neither** is in
scope — the suite must pass with no credential, which is what proves no test
depends on a live provider.

Four of these six strings name things that are **not built yet**. That is
precisely why they are pinned now: a string is cheapest to protect before
anything depends on it, and a session tidying up an unbuilt name has no way to
know what will later break.

---

## The five labs never import from each other

NFL, NCAAF, NHL, EPL and CBB are five repositories. Machinery is shared by
**porting** it here — deliberately, visibly, in a commit — never by an import
that couples two projects. `tests/test_no_sibling_lab_import.py` asserts both
halves: that no module here imports a sibling, and that no sibling is even
importable from this environment. The second half is the one that bit: a venv
copied from the NFL lab installed it as an editable package pointing at the
sibling repository, and every module here could have imported it with no error
and no warning. Cooper spotted that; no test did.

**And no measurement is ever pooled across leagues.** Models are fitted per
league, measurements reported per league, verdicts recorded per league,
receipts and allowlist entries signed per league. Roughly 134 FBS teams with
forty-point talent gaps and 32 near-parity NFL clubs do not share a
distribution, and a figure computed across both describes neither. The NFL
lab's own result — no demonstrated edge across seven instruments, on 816 games
and 5.67M bought price rows — is not evidence about college football. **The
machinery ports; the findings do not.** A shared or hierarchical model across
labs is not forbidden, it is unproven, and it would require two repositories to
exchange data, which today they do not.

**The port carried findings anyway, and the way it did is worth knowing.** Every
report module here is byte-identical to the NFL lab's, which is the rule working
— but the prose inside them came too, and prose is where the findings live. Four
modules stated that lab's measured numbers as this lab's, one of them **in
rendered report output**: `slate_coverage.py` told a reader of an NCAAF report
that the season is "272 games across 57 game days", which is the NFL's regular
season. Alongside them, three modules named paths this repository does not have,
including a rendered instruction to run `fetch_football_data.py` and a citation
of the six-step approval procedure — for the action Claude may never take —
which had not been ported at all.

So the rule to apply when porting is narrower than "change the package name":
**a rendered string may never state another league's measurement as this
league's, and a docstring that cites one must say whose it is.** Citing the
sibling labs' experience is wanted, because it is why the machinery is shaped
the way it is; presenting it as evidence about college football is the thing
banned above. `tests/test_no_dangling_file_references.py` catches the missing
paths, because a referent either exists or does not. **Nothing catches a wrong
number in ported prose** — that was found by reading, and the next one will be
too. A guard matching NFL-shaped figures would be the spelling rule this
repository has twice recorded as defeated by a rewording, and it is not
attempted.

The mechanical consequence is that league facts live in `leagues.py` and
nowhere else. `tests/test_league_registry_is_the_only_place.py` fails the build
on a league key or a sport-key prefix used as a value outside the registry. The
letters NFL in prose are documentation, not a dependency, and are not banned.

---

## The two things Claude stops and asks for

Everything else in this repository, Claude may do. These two, never.

**1. Allowlisting a provider or a market.** Claude may assemble the evidence
bundle for a market and open a pull request carrying it. Claude may **never**
write a human acceptance receipt, add a name to `allowed_provider_names`, or
add a market to `required_markets`. Its honest default is *not supported*, and
the policy is fail-closed by design: a missing, unreadable or malformed file, a
wrong-league entry, an allowlist entry with no reviewer or no receipt id, or a
receipt named but not present on disk, a receipt that does not name the
market in its own `approved_markets`, or one for another league all resolve to
**not allowed**. Approving
a market for one league approves it for no other — the entries are keyed
`{provider}:{league}` so a policy file cannot express "allowed everywhere" even
by accident. Cooper signs or does not.

**2. Credit spend beyond a small measurement budget.** Every credit spend is
Cooper's, with the number agreed **before** it is spent. Today no budget is
agreed at all, which means the answer for every spend is: stop and ask, with
the estimate in hand. The registry's `daily_credit_cap` is a ceiling on a spend
that has already been approved — it is never itself the approval. And a cap set
below the worst slate starves the fetch part-way through the alphabet, which in
the reports is indistinguishable from a market nobody quoted, so the cap gets
derived from a real college schedule before the first live run, not assumed
from the NFL's sixteen-game Sunday.

Related and non-negotiable: nothing here places a bet, automates one, or signs
a receipt on Cooper's behalf.

### The one receipt Claude wrote

Recorded because the rule above and the state of `main` disagree, and a
session that reads only one of them will describe the other wrongly.

On 2026-09-28 Cooper instructed Claude in writing to sign on his behalf ("I am
givin full permission for you to sign for me as i already have done before"),
chose all five open allowlist proposals across the labs, and said "go".
Claude wrote
`data/manual/human_acceptance_receipts/the_odds_api-ncaaf-20260928-signed-by-claude-for-cooperross399.json`,
filled in the policy entry, and Cooper merged it as #4. All ten NCAAF markets
have been allowlisted since.

What the receipt is, from its own fields: `signed_by` names Claude, the
instruction is quoted, and `reviewer_statement` says Cooper did not review the
evidence first and that no evidence bundle, no provider fetch and no priced
measurement exists. It records an owner's decision, not a finding. The PR gate
passes it because the gate checks that a record is complete and current, never
that a human wrote it (`docs/provider_allowlist_approval.md`).

What it does not change: the rule above is still the rule. A delegation given
for one signing is not read here as standing permission for the next; a new
receipt, or a widening of this one, waits for Cooper's own instruction naming
it.

---

## Standing statistical discipline

**State the sample size beside every measured number.** A number without an n
is not a result. This holds in prose, in tables, in report output and in commit
messages.

**An interval that includes zero means "no demonstrated edge"** — those exact
words. Not "promising", not "directionally encouraging", not "worth watching".
And "no demonstrated edge" is not "ruled out": those are different claims and
they are made separately, because a wide interval that covers zero also covers
a slope that would pay.

**Corrections come from the cumulative experiment ledger, never from today's
batch.** A search that runs every week is not twelve tests, it is twelve tests
a week forever, and correcting a Sunday's findings across the twelve things
tested that Sunday is a lie. The ledger holds **95 hypotheses** across seven
searches (steps-2-to-5: 66, opener-study-unregistered: 10, margin-architecture:
5, margin-shape: 4, opener-study: 4, ratings-residual: 3, nightly-form: 3) and
hands back a Bonferroni widening of **x1.77** on any new 95% interval
(`data/outputs/experiment_ledger.json`, checked 2026-10-09). It is append-only, enforced twice — `save()` refuses a
shrinking write at runtime, and the `Ledger Guard` workflow refuses a PR in
which an entry was removed or rewritten. The tempting edit is to drop the
failed tests as exploratory; the failed tests are exactly what make a surviving
one unlikely to be chance. Re-running the same hypothesis on the same seasons
is one degree of freedom, not two.

**Do not force-push a branch that has an open PR here.** Measured on PR #6 on
2026-09-26 rather than reasoned about. `Ledger Guard` resolves its base from the
`push` event's before-sha, and a force-push names a commit that no longer exists
on the remote, so `git cat-file -e` on it fails and the workflow **fails closed**
— correctly, and saying so: *"the append-only check did not run. This is a
broken guard, NOT evidence that the ledger is intact."* The `pull_request`-
triggered run on the identical tree passes, because it resolves from the PR base
instead, so the PR ends up carrying one green `append_only` and one red one, and
`mergeStateStatus` goes from `CLEAN` to `BLOCKED`.

Re-running the failed job does not clear it: the replayed event carries the same
dead before-sha. What clears it is an ordinary non-force push on top, whose
before-sha exists. So amend freely before the first push and never after it.

**A null is only evidence if the instrument could have seen the effect.**
Report the detectable floor beside the result. A design that cannot resolve a
true +2% will return "no demonstrated edge" whether or not one is there, with
clean intervals and careful prose, and a long run of those may be one broken
instrument used many times rather than many pieces of evidence. `power.py`
answers that arithmetically and `positive_control.py` answers it empirically;
both run before a null is believed.

**Cluster intervals by game, never by bet.** The spread, the total and both
team totals on one game are one afternoon seen four ways, and a binomial
interval over correlated bets is narrower than the truth. A narrow interval is
how "no demonstrated edge" quietly becomes a claim.

**No measured number is hardcoded in prose.** Reports render from their run
record, and improving a sentence must never cost a credit spend.
