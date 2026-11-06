# NCAAF card — 2026-11-06

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (5 game(s) staged)

Nebraska Cornhuskers @ Illinois Fighting Illini, New Mexico Lobos @ Nevada Wolf Pack, South Florida Bulls @ East Carolina Pirates, TCU Horned Frogs @ Arizona Wildcats, Virginia Tech Hokies @ SMU Mustangs

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

**One side per game.** 1 selection(s) also cleared the bars on the other side of 1 game(s) (New Mexico Lobos @ Nevada Wolf Pack) and were dropped. The side kept is the one whose best price sits furthest from the model, which is not a forecast of who wins: the model's centre is the market's own line.

**Edge floor.** 3 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 6,680 = no_opinion 1,562 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 5,118 — reconciles.`

- 1254 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 80 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 76 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 76 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 76 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

5,118 opinion(s) frozen for 2026-11-06; 267,724 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,364 games through 2026-11-06 16:38 UTC; home field +4.3 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-01. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Nebraska @ Illinois | -4.0 | +0.8 | +4.8 | same (Katin Houser) | same (Anthony Colandrea) |
| New Mexico @ Nevada | -10.0 | -2.2 | +7.8 | **changed last game** (AJ Bianco) | same (Toa Faavae) |
| South Florida @ East Carolina | +2.5 | -0.8 | -3.3 | same (Mitch Griffis) | no read |
| TCU @ Arizona | +7.0 | +10.9 | +3.9 | same (Noah Fifita) | same (Jaden Craig) |
| Virginia Tech @ SMU | +6.5 | +6.8 | +0.3 | same (Kevin Jennings) | same (Ethan Grunkemeyer) |
