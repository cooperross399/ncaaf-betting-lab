# NCAAF card — 2026-11-18

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (2 game(s) staged)

Akron Zips @ UMass Minutemen, Central Michigan Chippewas @ Buffalo Bulls

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

**Edge floor.** 4 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 2,956 = no_opinion 654 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 2,302 — reconciles.`

- 526 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 32 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 32 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 32 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 32 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

2,302 opinion(s) frozen for 2026-11-18; 391,134 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,493 games through 2026-11-18 15:16 UTC; home field +3.2 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-15. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Akron @ Massachusetts | +3.5 | +9.0 | +5.5 | **changed last game** (Logan Inagawa) | **changed last game** (Cibastian Broughton) |
| Central Michigan @ Buffalo | +2.5 | +4.5 | +2.0 | same (Jason Wright) | same (Jadyn Glasser) |
