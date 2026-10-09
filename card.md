# NCAAF card — 2026-10-09

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (5 game(s) staged)

Florida State Seminoles @ Louisville Cardinals, Iowa Hawkeyes @ Washington Huskies, Iowa State Cyclones @ BYU Cougars, Washington State Cougars @ Utah State Aggies, Wyoming Cowboys @ San Jose State Spartans

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | away | -9.5 | +500 | draftkings | 23.4% | +6.7% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | away | -8.5 | +457 | draftkings | 24.3% | +6.3% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | away | -7.5 | +411 | draftkings | 25.4% | +5.9% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | away | -6.5 | +305 | draftkings | 30.2% | +5.5% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | home | -14.5 | +556 | draftkings | 20.5% | +5.3% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | away | -5.5 | +261 | draftkings | 32.8% | +5.1% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | away | -4.5 | +235 | draftkings | 34.2% | +4.4% |
| Iowa Hawkeyes @ Washington Huskies | `alternate_spread` | home | -13.5 | +450 | draftkings | 22.5% | +4.3% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

## The accounting identity

`priced 6,425 = no_opinion 1,592 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 4,833 — reconciles.`

- 1284 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 80 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 76 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 76 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 76 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

4,833 opinion(s) frozen for 2026-10-09; 57,463 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.
