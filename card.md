# NCAAF card — 2026-10-08

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (4 game(s) staged)

Missouri State Bears @ Western Kentucky Hilltoppers, Sam Houston State Bearkats @ Liberty Flames, South Alabama Jaguars @ Arkansas State Red Wolves, South Florida Bulls @ UTSA Roadrunners

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | home | -13.5 | +544 | draftkings | 21.1% | +5.6% |
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | away | -11.5 | +528 | draftkings | 20.5% | +4.5% |
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | away | -12.5 | +593 | draftkings | 18.9% | +4.5% |
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | away | -10.5 | +465 | draftkings | 22.2% | +4.5% |
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | home | -12.5 | +487 | draftkings | 21.4% | +4.4% |
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | away | -9.5 | +380 | draftkings | 24.8% | +3.9% |
| Missouri State Bears @ Western Kentucky Hilltoppers | `alternate_spread` | away | -8.5 | +352 | draftkings | 25.7% | +3.6% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

## The accounting identity

`priced 5,612 = no_opinion 1,252 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 4,360 — reconciles.`

- 1038 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 56 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 56 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 54 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 48 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured

## Forward evidence

4,360 opinion(s) frozen for 2026-10-08; 57,463 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.
