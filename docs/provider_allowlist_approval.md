# How a market becomes trusted

Nothing in this repository trusts a provider or a market by default. The policy
file `data/manual/staging_provider_policy.json` decides which provider and which
markets the card may use, **per league**, and every failure mode in
`src/ncaaf_betting_lab/staging_provider_policy.py` resolves to *not allowed*:
a missing file, an unreadable one, a malformed one, an entry for a different
league, a market absent from `required_markets`, an allowlist entry with no
reviewer or no receipt id, or a receipt named but not present on disk.

This document was ported from the NHL lab on 2026-09-25. Three modules cited it
by path before it existed — `staging_provider_policy.py` in
`write_starter_policy`, and `reports/allowlist_evidence.py` in its module
docstring and in `render()`. A citation pointing at nothing is a defect, and
this file is the fix. It is **adapted rather than copied**: where the NHL lab
has machinery this lab has not built, that is said here rather than implied.

## Why the entries are keyed by league

The key is `{provider}:{league}` — `the_odds_api:ncaaf` — built by
`League.policy_key()`. Approving a market in the NFL approves it in no other
league, and a policy file therefore **cannot express "allowed everywhere" even
by accident**. ~134 FBS teams with forty-point talent gaps and 32 near-parity
NFL clubs do not share a distribution. One receipt, one league.

## The sequence

1. **Shadow runs.** A live fetch writes to `data/staging/`, which the card
   cannot read. This proves the adapter parses the provider's real responses
   and produces the rows it claims to.
   *State in this lab: has never run. No provider fetch has ever been made —
   nothing has been asked of The Odds API, no price has been bought, no event
   id is cached, and `data/staging/` is untracked and absent.*
2. **Coverage discovery.** Per bookmaker, per market, including alternate
   ladders. A market is **not** "unavailable" until this says so. (`total_2_5`
   in the EPL lab was excluded for a season on a coverage check that only
   looked at the featured `totals` key; the line was sitting in
   `alternate_totals` the whole time.)
   *State in this lab: has never run. Every market's `retained` field in
   `markets.py` is `None` — unprobed. `False` would be a finding and `True`
   would be a guess, and neither has been earned.*
3. **Measurement against real prices.** Historical prices are bought per event
   where the provider retains them. Where it does not, that is recorded **by
   name** as unmeasurable, and a calibration number is **not** offered as a
   substitute.
   *State in this lab: no market has been measured against a bought price. What
   exists is measurement against the free cfbfastR archive
   (`data/raw/ncaaf/betting/cfb_line_odds.csv.gz`), which is a different and
   narrower thing: it carries moneyline prices, and it carries no spread odds
   at all (100% NaN for `market_type='spread'`, 2021-25).*
4. **Evidence bundle.** Shadow report, coverage report and measurement reports
   assembled into one reviewable artifact that states what the evidence
   supports market by market. Its honest default — the one every market in this
   repository currently gets — is **not supported**. A market with only a
   calibration number is never supported by it, however large the sample.
   *State in this lab: the renderer exists at
   `src/ncaaf_betting_lab/reports/allowlist_evidence.py`; **no script drives
   it**. The NHL lab's `scripts/run_allowlist_evidence.py` was not ported, so
   there is no `data/outputs/allowlist_evidence_bundle.md` and no bundle to
   quote. A session that needs one has to build it from inputs that do not
   exist yet — see steps 1 to 3.*
5. **PR gate.** `tests/test_policy_pr_gate.py::test_the_shipped_policy_passes_the_gate`
   runs `reports/policy_pr_gate.py` against the repository's own policy,
   receipts and evidence, inside the suite branch protection requires. Every
   entry whose status is `allowed` must cite a receipt that is complete — see
   below — and whose evidence checksums still match the files on disk, or the
   pull request cannot merge. It is a registered guard, so deleting or
   deselecting it is a red build.
6. **Human acceptance receipt.** Cooper reviews the evidence and signs. Only
   this step allowlists anything. The card opens the receipt on every run: a
   market is allowed only if the policy lists it **and** the receipt's own
   `approved_markets` does. An id naming a file that is not there, a receipt
   for another league, or a policy listing a market the receipt does not
   approve all allow nothing.

## The receipt

`data/manual/human_acceptance_receipts/{receipt_id}.json`, cited by
`evidence_receipt_id` in the policy entry:

```json
{
  "receipt_id": "the same id as the filename",
  "policy_key": "the_odds_api:ncaaf",
  "reviewer_name": "who signed",
  "reviewer_statement": "what was read, and why it is enough",
  "reviewed_at": "2026-09-01T12:00:00-04:00",
  "approved_markets": ["moneyline"],
  "evidence": [
    {"path": "data/outputs/ncaaf_allowlist_evidence.md", "sha256": "..."}
  ]
}
```

| checked | by the card, every run | by the PR gate |
| --- | --- | --- |
| file exists, is JSON, id is a safe filename | yes | yes |
| `receipt_id` matches the filename | yes | yes |
| `policy_key` is this league | yes | yes |
| `reviewer_name` present and the same name the entry carries | yes | yes |
| the entry's provider is in `allowed_provider_names` | yes | yes |
| not a symlink; resolves inside the receipts directory | yes | yes |
| market is in `approved_markets` | yes | yes, for every listed market |
| an entry that says `allowed` is complete (reviewer, receipt id, markets) | | yes |
| `reviewer_statement`, timezone-aware `reviewed_at` | | yes |
| every evidence file inside the repository, outside `data/manual/`, present, checksum matching | | yes |

The card reads each receipt once per loaded policy, so every row of a run is
judged against the same bytes.

**What neither can do is verify that a human wrote the receipt.** The checker
and the file live in the same repository, and whoever can edit one can edit
the other. Cooper's review of the pull request, enforced by branch protection,
is what carries that weight. The gate makes the record complete and current;
it does not make it authentic.

## The one receipt Claude wrote

The receipt on `main` today is the case that paragraph describes.
`the_odds_api-ncaaf-20260928-signed-by-claude-for-cooperross399.json` was
written by Claude, on Cooper's written instruction of 2026-09-28, and merged by
Cooper as #4. It allowlists all ten markets. It passes the gate because every
field the gate checks is present and current; it is honest because its own
`signed_by`, `authorisation` and `reviewer_statement` fields say who wrote it,
quote the instruction, and record that Cooper did not review the evidence
first and that no market had been measured against a bought price.

It is not evidence, and it does not alter the list below: the next receipt
still waits for Cooper's own instruction naming it. `CLAUDE.md` carries the
same record under *The one receipt Claude wrote*.

## What Claude may never do

- Write or edit a human acceptance receipt. Not as a draft, not as a template,
  not "so it is ready to sign".
- Fill in `reviewer_name`, `approved_at` or `evidence_receipt_id` on an
  allowlist entry, or add a name to `allowed_provider_names`. Those fields are
  the receipt's counterpart inside the policy file, and writing them is signing
  on Cooper's behalf however the surrounding JSON is labelled.
- Set a market's `retained` field to `True`. `None` means unprobed and stays
  `None` until a real probe runs.
- Weaken, skip, disable or work around a gate, a test or a CI check.
- Present shadow evidence, a proposal, or a prepared file as though it had
  allowlisted something.

Claude prepares every one of the six steps and then stops. Step 6 is Cooper's.

## What Claude may do, and what "prepared" means

Claude may assemble the evidence bundle and may **prepare** a change to the
policy file and open a pull request carrying it. A prepared entry names the
markets under `required_markets` and records what is and is not known about
each under `known_limitations`. It leaves `allowlist_status` at something other
than `allowed` and leaves the reviewer and receipt fields empty, so that
`AllowlistEntry.is_allowed` is false on every count and `market_allowed()`
returns `False` for every market in it.

That distinction is the whole point: a prepared entry is a **request for a
decision**, and it must be structurally incapable of being mistaken for the
decision. An entry that carried a reviewer name and a receipt id would be one
absent file away from live, with an attestation nobody made.

## What approval does not buy

An allowlisted market still passes every other gate on every run: staging
validation, completeness, freshness, the coverage precondition and the kickoff
guard. Allowlisting says *this market's prices may be used*. It does not say
*skip the checks*, and it does not say an edge exists — clearing the evidence
bars means the measurements do not rule the market out, and nothing in a bundle
predicts a return.

**Allowlisting is also not sufficient for a pick.** In this lab it is not close
to sufficient: there is no card, no fetch, and no selection pipeline, so a
market can be allowlisted and still be structurally unable to produce a
selection. Where that is true it is recorded per market in `known_limitations`,
because "allowlisted" and "able to produce a pick" being confused is how a
reader concludes the lab is running when it is not.

## The record stays on the record

If Cooper approves a market against the measurement's own recommendation, both
the evidence and the decision are recorded, and any answer to "what do the
card's picks rest on" says so plainly. That happened in the EPL lab and the
record is the reason the answer there is still honest.

The NHL lab carries the other half of that lesson. Its 2026-08-27 approval of
all eleven markets was **withdrawn** on 2026-08-29 when the evidence moved
underneath it: the receipt had been signed against a backtest reporting +1.4%
over 4,830 bets with an interval including zero, and buying the full two-season
population replaced that sample with 73,918 bets and changed the sign to -1.6%,
interval [-2.3%, -0.8%]. Claude withdrew it and could not re-enable it.
**Withdrawal is the only direction Claude may move this file on its own, because
it can only ever reduce what the card is allowed to do.**
