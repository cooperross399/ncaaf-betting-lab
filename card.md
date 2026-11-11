# NCAAF card — 2026-11-11

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (3 game(s) staged)

Buffalo Bulls @ Ball State Cardinals, Sacramento State Hornets @ Central Michigan Chippewas, UMass Minutemen @ Toledo Rockets

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

## The accounting identity

`priced 4,093 = no_opinion 938 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 3,155 — reconciles.`

- 750 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 48 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 48 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 48 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 44 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

3,155 opinion(s) frozen for 2026-11-11; 328,059 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,426 games through 2026-11-11 16:57 UTC; home field +3.3 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-08. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Buffalo @ Ball State | -1.0 | -2.1 | -1.1 | same (Keldric Luster) | same (Jason Wright) |
| Massachusetts @ Toledo | +14.0 | +10.1 | -3.9 | same (John Alan Richter) | same (William Watson III) |
| Sacramento State @ Central Michigan | +17.0 | +13.3 | -3.7 | same (Jadyn Glasser) | **changed last game** (Brian Salazar) |
