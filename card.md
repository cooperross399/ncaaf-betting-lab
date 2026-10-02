# NCAAF card — 2026-10-02

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (3 game(s) staged)

Liberty Flames @ Delaware Blue Hens, Penn State Nittany Lions @ Northwestern Wildcats, Pittsburgh Panthers @ Virginia Tech Hokies

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| Pittsburgh Panthers @ Virginia Tech Hokies | `alternate_spread` | home | -16.5 | +581 | draftkings | 18.6% | +3.9% |
| Pittsburgh Panthers @ Virginia Tech Hokies | `alternate_spread` | home | -14.5 | +499 | draftkings | 20.5% | +3.8% |
| Pittsburgh Panthers @ Virginia Tech Hokies | `alternate_spread` | away | -11.5 | +547 | draftkings | 19.2% | +3.7% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

## The accounting identity

`priced 4,108 = no_opinion 1,024 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 3,084 — reconciles.`

- 836 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 48 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 48 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 48 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 44 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured

## Forward evidence

3,084 opinion(s) frozen for 2026-10-02; 0 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.
