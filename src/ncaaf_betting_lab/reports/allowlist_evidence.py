"""Everything a human needs to decide whether a market may be bet.

## What this is, and what it is not

It is **step four of six** in `docs/provider_allowlist_approval.md`. It
assembles every measurement into one reviewable artifact, states what each one
supports, and stops. It allowlists nothing. Claude prepares it; Cooper signs
or does not.

Its honest default is **not supported**. A market earns a different verdict by
clearing every bar below, and a market with only a calibration number never
earns one however large the sample.

## The bars, and why each is here

Each was added because something failed it, and the failures are named so a
reader can check the reasoning rather than take it:

``harness``
    The null baseline must lose. If betting everything makes money, nothing
    computed on top of it means anything.
``settlement``
    The realised rate must match the devigged price. `tackles_assists`
    returns +11.7% across three seasons and is a seven-point settlement gap;
    a constant offset replicates perfectly and survives every other check.
    A market this screen never *examined* fails the bar too — an approval
    cleared by never having been measured is the same artefact in a
    different shape.
``consensus``
    The return must survive at the median quote. A number that exists only as
    the maximum of thirteen quotes needs an account at whichever book was
    softest that day.
``books``
    It must be positive at most books, not one. One book's mistake is a fact
    about that book, and books that price like that get sharper or limited.
``replication``
    It must hold on seasons it was not selected on — necessary, and by itself
    not sufficient, which is the lesson `tackles_assists` cost.
``sample``
    Above the minimum declared in advance, or the verdict is "not enough
    evidence" rather than a number.

## What it deliberately does not do

It does not weigh closing-line value. Profit and ROI are the objective
(Cooper, 2026-08-29); CLV is a diagnostic that raises questions and answers
none, and a market is never refused for lacking it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


NOT_SUPPORTED = "not supported"
SUPPORTED = "supported for review"


@dataclass
class Bar:
    """One requirement, and whether a market cleared it."""

    name: str
    passed: bool
    detail: str


@dataclass
class MarketEvidence:
    market: str
    bets: int
    bars: list[Bar] = field(default_factory=list)

    @property
    def failed(self) -> list[Bar]:
        return [bar for bar in self.bars if not bar.passed]

    @property
    def verdict(self) -> str:
        return NOT_SUPPORTED if self.failed else SUPPORTED

    def summary(self) -> str:
        if not self.failed:
            return (
                "clears every bar — **this is a recommendation to review, not "
                "an approval**"
            )
        return "fails: " + "; ".join(bar.name for bar in self.failed)


@dataclass
class EvidenceBundle:
    league: str
    markets: list[MarketEvidence] = field(default_factory=list)
    inputs: dict[str, str] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)

    @property
    def supported(self) -> list[MarketEvidence]:
        return [m for m in self.markets if not m.failed]


def render(bundle: EvidenceBundle) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Allowlist evidence — {bundle.league.upper()}")
    add("")
    add(
        "**This allowlists nothing.** It is step four of the six in "
        "`docs/provider_allowlist_approval.md`. Claude prepares it and stops; "
        "step six is Cooper reading it and signing a receipt, or not."
    )
    add("")
    add(
        "The default verdict is **not supported**. A market earns anything "
        "else only by clearing every bar, and each bar exists because "
        "something failed it."
    )
    add("")
    add("## What this rests on")
    add("")
    add("| Input | State |")
    add("|:------|:------|")
    for name, state in bundle.inputs.items():
        add(f"| {name} | {state} |")
    add("")
    add("## Market by market")
    add("")
    add("| Market | Bets | Verdict | Detail |")
    add("|:-------|-----:|:--------|:-------|")
    for market in sorted(bundle.markets, key=lambda m: (bool(m.failed), -m.bets)):
        add(
            f"| `{market.market}` | {market.bets:,} | "
            f"**{market.verdict}** | {market.summary()} |"
        )
    add("")
    for market in bundle.markets:
        add(f"### `{market.market}`")
        add("")
        add("| Bar | Result |")
        add("|:----|:-------|")
        for bar in market.bars:
            mark = "pass" if bar.passed else "**FAIL**"
            add(f"| {bar.name} | {mark} — {bar.detail} |")
        add("")

    add("## What a signature would and would not buy")
    add("")
    add(
        f"**{len(bundle.supported)} of {len(bundle.markets)} markets clear "
        "every bar.** Clearing them means the measurements do not rule the "
        "market out; it does not mean an edge is established. Nothing here "
        "predicts a return."
    )
    add("")
    add(
        "An allowlisted market still passes every gate on every run: staging "
        "validation, completeness, freshness, the kickoff guard, the "
        "quarterback-change quarantine and the availability gate. Approval "
        "says *these prices may be used*. It does not say *skip the checks*."
    )
    if bundle.caveats:
        add("")
        add("## What would change these numbers")
        add("")
        for caveat in bundle.caveats:
            add(f"- {caveat}")
    return "\n".join(lines) + "\n"
