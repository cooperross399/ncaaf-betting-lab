# NCAAF card — 2026-10-20

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (3 game(s) staged)

Middle Tennessee Blue Raiders @ Florida International Panthers, Missouri State Bears @ Delaware Blue Hens, South Alabama Jaguars @ Marshall Thundering Herd

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| South Alabama Jaguars @ Marshall Thundering Herd | `alternate_spread` | away | -10.5 | +320 | betrivers | 32.2% | +8.4% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

**Edge floor.** 4 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

**One pick per question.** 7 selection(s) cleared every bar but were other rungs of a question the card already answers, and were not selected: each game's margin, total and team totals carry only their largest edge.

## The accounting identity

`priced 4,200 = no_opinion 958 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 3,242 — reconciles.`

- 778 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 48 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 48 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 48 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 36 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured

## Forward evidence

3,242 opinion(s) frozen for 2026-10-20; 152,982 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,252 games through 2026-10-20 12:43 UTC; home field +4.2 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-10-18. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Middle Tennessee @ Florida International | +10.0 | +10.0 | -0.0 | same (J.J. Kohl) | same (Roman Gagliano) |
| Missouri State @ Delaware | +2.5 | +5.5 | +3.0 | **changed last game** (Tyler Bell) | **changed last game** (Henry Belin IV) |
| South Alabama @ Marshall | -3.0 | -0.5 | +2.5 | same (Zion Turner) | same (Jared Hollins) |
