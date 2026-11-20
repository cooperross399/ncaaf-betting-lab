# NCAAF card — 2026-11-20

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (6 game(s) staged)

Bowling Green Falcons @ Toledo Rockets, Clemson Tigers @ Duke Blue Devils, Iowa State Cyclones @ UCF Knights, New Mexico Lobos @ Wyoming Cowboys, Oregon Ducks @ Michigan State Spartans, UTEP Miners @ Air Force Falcons

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

**Edge floor.** 18 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 8,711 = no_opinion 1,846 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 6,865 — reconciles.`

- 1474 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 96 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 94 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 94 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 88 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

6,865 opinion(s) frozen for 2026-11-20; 391,134 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,493 games through 2026-11-20 15:16 UTC; home field +3.2 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-15. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Bowling Green @ Toledo | +16.5 | +9.6 | -6.9 | same (John Alan Richter) | **changed last game** (Austin Novosad) |
| Clemson @ Duke | +12.5 | +11.0 | -1.5 | same (Walker Eget) | **changed last game** (Christopher Vizzina) |
| Iowa State @ UCF | -1.2 | -1.0 | +0.2 | **changed last game** (Alonza Barnett) | same (Jaylen Raynor) |
| New Mexico @ Wyoming | -9.0 | -2.6 | +6.4 | **changed last game** (Landon Sims) | same (Toa Faavae) |
| Oregon @ Michigan State | -17.8 | -5.6 | +12.2 | **changed last game** (Cam Fancher) | same (Dylan Raiola) |
| UTEP @ Air Force | +21.5 | +17.7 | -3.8 | **changed last game** (Luke Weaver) | **changed last game** (Raymond Moore III) |
