# NCAAF card — 2026-10-23

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (5 game(s) staged)

Air Force Falcons @ Wyoming Cowboys, Army Black Knights @ Tulsa Golden Hurricane, Duke Blue Devils @ Virginia Cavaliers, NC State Wolfpack @ Stanford Cardinal, UMass Minutemen @ UConn Huskies

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

**One side per game.** 3 selection(s) also cleared the bars on the other side of 1 game(s) (Duke Blue Devils @ Virginia Cavaliers) and were dropped. The side kept is the one whose best price sits furthest from the model, which is not a forecast of who wins: the model's centre is the market's own line.

**Edge floor.** 7 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 6,945 = no_opinion 1,630 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 5,315 — reconciles.`

- 1310 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 80 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 80 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 80 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 80 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

5,315 opinion(s) frozen for 2026-10-23; 152,982 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,252 games through 2026-10-23 12:43 UTC; home field +4.3 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-10-18. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Air Force @ Wyoming | -5.5 | -2.2 | +3.3 | same (Tyler Hughes) | **changed last game** (Evan Medders) |
| Army @ Tulsa | +1.5 | +1.0 | -0.5 | same (Baylor Hayes) | **changed last game** (Caden Veltkamp) |
| Duke @ Virginia | +2.5 | +1.6 | -0.9 | same (Beau Pribula) | same (Walker Eget) |
| Massachusetts @ UConn | +14.5 | +8.1 | -6.4 | same (Kalieb Osborne) | **changed last game** (Logan Inagawa) |
| NC State @ Stanford | -7.0 | +0.6 | +7.6 | same (Davis Warren) | same (CJ Bailey) |
