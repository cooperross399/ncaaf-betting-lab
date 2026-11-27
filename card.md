# NCAAF card — 2026-11-27

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (13 game(s) staged)

Air Force Falcons @ New Mexico Lobos, Appalachian State Mountaineers @ South Alabama Jaguars, Buffalo Bulls @ Akron Zips, Florida Gators @ Florida State Seminoles, Minnesota Golden Gophers @ Wisconsin Badgers, Mississippi State Bulldogs @ Ole Miss Rebels, Nebraska Cornhuskers @ Iowa Hawkeyes, North Dakota State Bison @ San Jose State Spartans, Temple Owls @ Memphis Tigers, Texas Longhorns @ Texas A&M Aggies, Toledo Rockets @ Ohio Bobcats, Tulsa Golden Hurricane @ UTSA Roadrunners, West Virginia Mountaineers @ Utah Utes

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

**Edge floor.** 12 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 18,518 = no_opinion 4,094 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 14,424 — reconciles.`

- 3302 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 204 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 198 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 198 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 192 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

14,424 opinion(s) frozen for 2026-11-27; 460,845 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,559 games through 2026-11-27 15:15 UTC; home field +3.1 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-22. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Air Force @ New Mexico | +7.0 | +5.3 | -1.7 | **changed last game** (Luke Moga) | **changed last game** (Raymond Moore III) |
| App State @ South Alabama | +3.0 | +5.8 | +2.8 | **changed last game** (Bishop Davenport) | same (Malachi Singleton) |
| Buffalo @ Akron | -7.5 | -10.6 | -3.1 | **changed last game** (Cibastian Broughton) | same (Jason Wright) |
| Florida @ Florida State | -6.5 | +1.9 | +8.4 | same (Ashton Daniels) | same (Aaron Philo) |
| Minnesota @ Wisconsin | +9.5 | +11.1 | +1.6 | same (Colton Joseph) | same (Drake Lindsey) |
| Mississippi State @ Ole Miss | +17.5 | +14.2 | -3.3 | same (Trinidad Chambliss) | **changed last game** (Parker Puckett) |
| Nebraska @ Iowa | +3.5 | +6.4 | +2.9 | same (Hank Brown) | same (Anthony Colandrea) |
| North Dakota State @ San José State | -8.0 | -5.1 | +2.9 | same (Luke Weaver) | same (Nathan Hayes) |
| Temple @ Memphis | +19.5 | +15.5 | -4.0 | same (Marcus Stokes) | **changed last game** (Jaxon Smolik) |
| Texas @ Texas A&M | -11.2 | -8.1 | +3.2 | **changed last game** (Brady Hart) | same (Arch Manning) |
| Toledo @ Ohio | -3.0 | -1.3 | +1.7 | same (Nick Poulos) | same (John Alan Richter) |
| Tulsa @ UTSA | -1.0 | +0.5 | +1.5 | same (Owen McCown) | same (Baylor Hayes) |
| West Virginia @ Utah | +26.0 | +16.6 | -9.4 | same (Devon Dampier) | same (Michael Hawkins Jr.) |
