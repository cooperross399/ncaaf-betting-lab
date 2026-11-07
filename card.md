# NCAAF card — 2026-11-07

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (51 game(s) staged)

Air Force Falcons @ Army Black Knights, Alabama Crimson Tide @ LSU Tigers, Arkansas Razorbacks @ Auburn Tigers, BYU Cougars @ Utah Utes, Boise State Broncos @ Colorado State Rams, Charlotte 49ers @ UAB Blazers, Cincinnati Bearcats @ Houston Cougars, Clemson Tigers @ Syracuse Orange, Colorado Buffaloes @ Arizona State Sun Devils, Delaware Blue Hens @ Kennesaw State Owls, Duke Blue Devils @ NC State Wolfpack, Florida State Seminoles @ Boston College Eagles, Fresno State Bulldogs @ Utah State Aggies, Georgia Bulldogs @ Ole Miss Rebels, Georgia State Panthers @ Appalachian State Mountaineers, Hawaii Rainbow Warriors @ UTEP Miners, Iowa Hawkeyes @ Northwestern Wildcats, Iowa State Cyclones @ Baylor Bears, Kentucky Wildcats @ Tennessee Volunteers, Liberty Flames @ New Mexico State Aggies, Louisiana Tech Bulldogs @ Troy Trojans, Louisville Cardinals @ Georgia Tech Yellow Jackets, Marshall Thundering Herd @ Georgia Southern Eagles, Maryland Terrapins @ Purdue Boilermakers, Merrimack Warriors @ Wake Forest Demon Deacons, Miami Hurricanes @ Notre Dame Fighting Irish, Michigan State Spartans @ Michigan Wolverines, Missouri State Bears @ Florida International Panthers, North Carolina Tar Heels @ UConn Huskies, Northern Illinois Huskies @ San Jose State Spartans, Oklahoma Sooners @ Florida Gators, Oklahoma State Cowboys @ Kansas State Wildcats, Old Dominion Monarchs @ Coastal Carolina Chanticleers, Oregon Ducks @ Ohio State Buckeyes, Penn State Nittany Lions @ Washington Huskies, Rice Owls @ North Texas Mean Green, Rutgers Scarlet Knights @ Wisconsin Badgers, Sam Houston State Bearkats @ Jacksonville State Gamecocks, South Alabama Jaguars @ Louisiana Ragin Cajuns, Temple Owls @ Navy Midshipmen, Texas A&M Aggies @ South Carolina Gamecocks, Texas Longhorns @ Missouri Tigers, Texas State Bobcats @ Oregon State Beavers, Tulsa Golden Hurricane @ Tulane Green Wave, UCF Knights @ Kansas Jayhawks, UCLA Bruins @ Minnesota Golden Gophers, UL Monroe Warhawks @ Arkansas State Red Wolves, Vanderbilt Commodores @ Mississippi State Bulldogs, West Virginia Mountaineers @ Texas Tech Red Raiders, Western Kentucky Hilltoppers @ Middle Tennessee Blue Raiders, Wyoming Cowboys @ UNLV Rebels

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

**Bet down to** is the worst price at which a pick still clears the card's 6% edge bar, never worse than -160. Below it, the pick is no longer a selection.

| Game | Market | Selection | Line | Price | Book | Model | Edge | Bet down to |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|------------:|
| Liberty Flames @ New Mexico State Aggies | `alternate_spread` | home | +9.5 | +176 | fanduel | 42.8% | +6.6% | +172 |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

**Edge floor.** 35 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## Games this lab holds no opinion on (1)

Refused by the fixture screen. Not a pass on the game: this lab has no opinion it is entitled to hold on it.

- Merrimack Warriors @ Wake Forest Demon Deacons — Merrimack Warriors is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only

## The accounting identity

`priced 64,181 = no_opinion 15,844 + unrated_opponent 32 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 48,305 — reconciles.`

- 12750 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 796 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 770 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 770 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 758 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 32 x Merrimack Warriors is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only

## Forward evidence

48,305 opinion(s) frozen for 2026-11-07; 267,724 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,364 games through 2026-11-07 16:08 UTC; home field +4.3 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-01. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Air Force @ Army | +4.0 | +4.0 | -0.0 | same (Cale Hellums) | **changed last game** (Kalieb Osborne) |
| Alabama @ LSU | +6.0 | +6.6 | +0.6 | same (Sam Leavitt) | same (Keelon Russell) |
| Arkansas @ Auburn | +10.5 | +7.7 | -2.8 | same (Byrum Brown) | same (KJ Jackson) |
| BYU @ Utah | +4.5 | +10.0 | +5.5 | same (Devon Dampier) | same (Bear Bachmeier) |
| Boise State @ Colorado State | -17.0 | -10.3 | +6.7 | same (Hauss Hejny) | same (Maddux Madsen) |
| Charlotte @ UAB | +8.5 | +8.9 | +0.4 | same (Ryder Burton) | **changed last game** (Conner Harrell) |
| Cincinnati @ Houston | +10.5 | +11.7 | +1.2 | same (Conner Weigman) | same (JC French) |
| Clemson @ Syracuse | -1.5 | +2.4 | +3.9 | same (Steven Angeli) | same (Tait Reynolds) |
| Colorado @ Arizona State | +3.0 | +6.9 | +3.9 | **changed last game** (Jake Fette) | same (Isaac Wilson) |
| Delaware @ Kennesaw State | -1.0 | +1.5 | +2.5 | same (Rickie Collins) | same (Nick Minicucci) |
| Duke @ NC State | -4.0 | -1.1 | +2.9 | same (CJ Bailey) | same (Walker Eget) |
| Florida State @ Boston College | -5.5 | +2.8 | +8.3 | same (Mason McKenzie) | same (Ashton Daniels) |
| Fresno State @ Utah State | -1.0 | -0.0 | +1.0 | **changed last game** (McCae Hillstead) | same (Jayden Mandal) |
| Georgia @ Ole Miss | -3.5 | +4.5 | +8.0 | same (Trinidad Chambliss) | same (Gunner Stockton) |
| Georgia State @ App State | +6.5 | +4.4 | -2.1 | same (Malachi Singleton) | **changed last game** (Ayden Pereira) |
| Hawai'i @ UTEP | -7.5 | -4.2 | +3.3 | same (EJ Colson) | same (Micah Alejado) |
| Iowa @ Northwestern | -3.0 | +5.4 | +8.4 | same (Aidan Chiles) | same (Hank Brown) |
| Iowa State @ Baylor | +10.0 | +10.7 | +0.7 | same (D.J. Lagway) | same (Jaylen Raynor) |
| Kentucky @ Tennessee | +6.0 | +6.1 | +0.1 | same (George MacIntyre) | same (Kenny Minchey) |
| Liberty @ New Mexico State | -15.5 | -12.8 | +2.7 | same (Adam Damante) | same (Deshawn Purdie) |
| Louisiana Tech @ Troy | -6.0 | -2.2 | +3.8 | **changed last game** (Tucker Kilcrease) | same (Blake Baker) |
| Louisville @ Georgia Tech | -14.5 | -8.7 | +5.8 | same (Alberto Mendoza) | same (Lincoln Kienholz) |
| Marshall @ Georgia Southern | +7.5 | +7.4 | -0.1 | same (Max Johnson) | **changed last game** (Jaxon Potter) |
| Maryland @ Purdue | +5.0 | +9.4 | +4.4 | same (Ryan Browne) | same (Malik Washington) |
| Miami @ Notre Dame | +7.0 | +4.1 | -2.9 | same (C.J. Carr) | same (Darian Mensah) |
| Michigan State @ Michigan | +14.0 | +8.2 | -5.8 | **changed last game** (Tommy Carr) | **changed last game** (Leo Hannan) |
| Missouri State @ Florida International | +4.5 | +7.8 | +3.3 | same (J.J. Kohl) | **changed last game** (Henry Belin IV) |
| North Carolina @ UConn | -7.5 | +4.4 | +11.9 | same (Kalieb Osborne) | same (Billy Edwards) |
| Northern Illinois @ San José State | +12.0 | +12.1 | +0.1 | same (Luke Weaver) | same (Taron Dickens) |
| Oklahoma @ Florida | +4.5 | +5.3 | +0.8 | **changed last game** (Tramell Jones Jr.) | same (John Mateer) |
| Oklahoma State @ Kansas State | -7.0 | -0.6 | +6.4 | **changed last game** (Blake Barnett) | same (Drew Mestemaker) |
| Old Dominion @ Coastal Carolina | +6.5 | +11.3 | +4.8 | same (Deuce Bailey) | **changed last game** (Jaxon Potter) |
| Oregon @ Ohio State | +7.5 | +9.3 | +1.8 | **changed last game** (Luke Fahey) | same (Dylan Raiola) |
| Penn State @ Washington | +2.5 | +3.7 | +1.2 | **changed last game** (Elijah Brown) | same (Rocco Becht) |
| Rice @ North Texas | +16.0 | +14.3 | -1.7 | same (Tayven Jackson) | **changed last game** (Gael Ochoa) |
| Rutgers @ Wisconsin | +19.0 | +13.0 | -6.0 | same (Colton Joseph) | same (AJ Surace) |
| Sam Houston @ Jacksonville State | +16.5 | +15.9 | -0.6 | same (Caden Creel) | **changed last game** (DJ Bailey) |
| South Alabama @ Louisiana | +7.0 | +9.3 | +2.3 | same (D'Wayne' Winfield) | same (Jared Hollins) |
| Temple @ Navy | +7.0 | +7.1 | +0.1 | same (Jackson Gutierrez) | same (Ajani Sheppard) |
| Texas @ Missouri | -2.5 | +3.7 | +6.2 | same (Austin Simmons) | same (Arch Manning) |
| Texas A&M @ South Carolina | +6.5 | +6.3 | -0.2 | same (Lanorris Sellers) | same (Marcel Reed) |
| Texas State @ Oregon State | +5.5 | +5.2 | -0.3 | same (Braden Atkinson) | same (Brad Jackson) |
| Tulsa @ Tulane | -2.5 | +3.9 | +6.4 | **changed last game** (Trace Johnson) | same (Baylor Hayes) |
| UCF @ Kansas | +5.5 | +5.7 | +0.2 | **changed last game** (Cole Ballard) | same (Keyone Jenkins) |
| UCLA @ Minnesota | -3.5 | -4.6 | -1.1 | same (Drake Lindsey) | **changed last game** (Ty Dieffenbach) |
| UL Monroe @ Arkansas State | +14.5 | +12.1 | -2.4 | same (Trey Owens) | same (Aidan Armenta) |
| Vanderbilt @ Mississippi State | +2.5 | +6.2 | +3.7 | **changed last game** (AJ Swann) | same (Jared Curtis) |
| West Virginia @ Texas Tech | +16.0 | +12.8 | -3.2 | **changed last game** (Thomas Castellanos) | same (Michael Hawkins Jr.) |
| Western Kentucky @ Middle Tennessee | -2.5 | +4.7 | +7.2 | same (Roman Gagliano) | same (Brock Glenn) |
| Wyoming @ UNLV | +3.5 | +5.9 | +2.4 | same (Jackson Arnold) | same (Tyler Hughes) |
