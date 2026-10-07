# NCAAF card — 2026-10-07

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (2 game(s) staged)

Jacksonville State Gamecocks @ Kennesaw State Owls, New Mexico State Aggies @ Florida International Panthers

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| Jacksonville State Gamecocks @ Kennesaw State Owls | `alternate_spread` | away | -10.5 | +250 | fanduel | 32.2% | +3.6% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

## The accounting identity

`priced 2,818 = no_opinion 692 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 2,126 — reconciles.`

- 564 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 32 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 32 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 32 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 32 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

2,126 opinion(s) frozen for 2026-10-07; 57,463 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.
