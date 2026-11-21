# NCAAF card — 2026-11-21

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (58 game(s) staged)

Arizona Wildcats @ Kansas State Wildcats, Arkansas Razorbacks @ Texas Longhorns, Arkansas State Red Wolves @ Louisiana Tech Bulldogs, BYU Cougars @ Kansas Jayhawks, Charlotte 49ers @ Tulsa Golden Hurricane, Chattanooga Mocs @ Alabama Crimson Tide, Coastal Carolina Chanticleers @ Louisiana Ragin Cajuns, Colorado Buffaloes @ Cincinnati Bearcats, Colorado State Rams @ Fresno State Bulldogs, Delaware Blue Hens @ New Mexico State Aggies, East Carolina Pirates @ Army Black Knights, Florida International Panthers @ Kennesaw State Owls, Georgia Bulldogs @ South Carolina Gamecocks, Georgia Southern Eagles @ Troy Trojans, Georgia State Panthers @ Marshall Thundering Herd, Hawaii Rainbow Warriors @ Nevada Wolf Pack, Houston Cougars @ West Virginia Mountaineers, Indiana Hoosiers @ Washington Huskies, Iowa Hawkeyes @ Illinois Fighting Illini, Kentucky Wildcats @ Missouri Tigers, LSU Tigers @ Tennessee Volunteers, Maryland Terrapins @ USC Trojans, Memphis Tigers @ Navy Midshipmen, Middle Tennessee Blue Raiders @ Sam Houston State Bearkats, Missouri State Bears @ Jacksonville State Gamecocks, NC State Wolfpack @ Florida State Seminoles, North Carolina Tar Heels @ Virginia Cavaliers, North Texas Mean Green @ Tulane Green Wave, Northern Illinois Huskies @ North Dakota State Bison, Northwestern Wildcats @ Minnesota Golden Gophers, Ohio State Buckeyes @ Nebraska Cornhuskers, Oklahoma State Cowboys @ Arizona State Sun Devils, Old Dominion Monarchs @ UConn Huskies, Pittsburgh Panthers @ Louisville Cardinals, Rutgers Scarlet Knights @ Penn State Nittany Lions, SMU Mustangs @ Notre Dame Fighting Irish, Samford Bulldogs @ Auburn Tigers, San Diego State Aztecs @ Boise State Broncos, South Alabama Jaguars @ Southern Mississippi Golden Eagles, South Florida Bulls @ Florida Atlantic Owls, Stanford Cardinal @ California Golden Bears, Syracuse Orange @ Boston College Eagles, Tennessee Tech Golden Eagles @ Mississippi State Bulldogs, Texas A&M Aggies @ Oklahoma Sooners, Texas Tech Red Raiders @ Baylor Bears, UCLA Bruins @ Michigan Wolverines, UL Monroe Warhawks @ Appalachian State Mountaineers, UNLV Rebels @ San Jose State Spartans, UTSA Roadrunners @ UAB Blazers, Utah State Aggies @ Oregon State Beavers, Utah Utes @ TCU Horned Frogs, Vanderbilt Commodores @ Florida Gators, Virginia Tech Hokies @ Miami Hurricanes, Wake Forest Demon Deacons @ Georgia Tech Yellow Jackets, Washington State Cougars @ Texas State Bobcats, Western Kentucky Hilltoppers @ Liberty Flames, Wisconsin Badgers @ Purdue Boilermakers, Wofford Terriers @ Ole Miss Rebels

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

**Bet down to** is the worst price at which a pick still clears the card's 6% edge bar, never worse than -160. Below it, the pick is no longer a selection.

| Game | Market | Selection | Line | Price | Book | Model | Edge | Bet down to |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|------------:|
| Northern Illinois Huskies @ North Dakota State Bison | `alternate_spread` | away | +12.5 | +420 | fanduel | 26.9% | +7.6% | +380 |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

**Edge floor.** 56 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

**One pick per question.** 6 selection(s) cleared every bar but were other rungs of a question the card already answers, and were not selected: each game's margin, total and team totals carry only their largest edge.

## Games this lab holds no opinion on (4)

Refused by the fixture screen. Not a pass on the game: this lab has no opinion it is entitled to hold on it.

- Chattanooga Mocs @ Alabama Crimson Tide — Chattanooga Mocs is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- Samford Bulldogs @ Auburn Tigers — Samford Bulldogs is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- Tennessee Tech Golden Eagles @ Mississippi State Bulldogs — Tennessee Tech Golden Eagles is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- Wofford Terriers @ Ole Miss Rebels — Wofford Terriers is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only

## The accounting identity

`priced 73,328 = no_opinion 16,992 + unrated_opponent 150 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 56,186 — reconciles.`

- 13742 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 840 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 808 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 808 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 794 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 42 x Tennessee Tech Golden Eagles is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- 38 x Chattanooga Mocs is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- 36 x Samford Bulldogs is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- 34 x Wofford Terriers is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only

## Forward evidence

56,186 opinion(s) frozen for 2026-11-21; 391,134 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,493 games through 2026-11-21 15:14 UTC; home field +3.2 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-15. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Arizona @ Kansas State | -9.5 | -6.8 | +2.7 | **changed last game** (Dillon Duff) | same (Noah Fifita) |
| Arkansas @ Texas | +19.0 | +10.7 | -8.3 | same (Arch Manning) | same (KJ Jackson) |
| Arkansas State @ Louisiana Tech | +14.5 | +13.3 | -1.2 | same (Blake Baker) | same (Trey Owens) |
| BYU @ Kansas | -5.2 | -1.8 | +3.5 | same (Isaiah Marshall) | same (Bear Bachmeier) |
| Charlotte @ Tulsa | +22.5 | +14.6 | -7.9 | same (Baylor Hayes) | same (Conner Harrell) |
| Coastal Carolina @ Louisiana | +10.5 | +8.9 | -1.6 | same (D'Wayne' Winfield) | same (Deuce Bailey) |
| Colorado @ Cincinnati | +3.0 | +3.1 | +0.1 | same (JC French) | same (Isaac Wilson) |
| Colorado State @ Fresno State | +20.0 | +16.1 | -3.9 | same (Jayden Mandal) | same (Hauss Hejny) |
| Delaware @ New Mexico State | -3.0 | -3.6 | -0.6 | same (Trey Hedden) | same (Nick Minicucci) |
| East Carolina @ Army | +6.0 | +5.2 | -0.8 | same (Cale Hellums) | same (Emory Williams) |
| Florida International @ Kennesaw State | +2.5 | +4.2 | +1.7 | **changed last game** (Landon Varnes) | same (J.J. Kohl) |
| Georgia @ South Carolina | -15.0 | -9.6 | +5.4 | **changed last game** (Cutter Woods) | same (Gunner Stockton) |
| Georgia Southern @ Troy | -9.5 | -6.6 | +2.9 | same (Will Crowder) | same (Max Johnson) |
| Georgia State @ Marshall | +3.0 | +1.2 | -1.8 | **changed last game** (Khalil Wilkins) | **changed last game** (Ayden Pereira) |
| Hawai'i @ Nevada | +6.0 | +4.8 | -1.2 | same (AJ Bianco) | same (Micah Alejado) |
| Houston @ West Virginia | -7.0 | -2.9 | +4.1 | same (Michael Hawkins Jr.) | same (Conner Weigman) |
| Indiana @ Washington | -9.2 | -2.1 | +7.1 | same (Demond Williams Jr.) | **changed last game** (Grant Wilson) |
| Iowa @ Illinois | -8.5 | -1.7 | +6.8 | same (Katin Houser) | same (Hank Brown) |
| Kentucky @ Missouri | +4.5 | +4.9 | +0.4 | same (Austin Simmons) | same (Kenny Minchey) |
| LSU @ Tennessee | -1.0 | +6.2 | +7.2 | same (George MacIntyre) | same (Sam Leavitt) |
| Maryland @ USC | +17.5 | +10.3 | -7.2 | same (Jayden Maiava) | **changed last game** (Cardell Williams) |
| Memphis @ Navy | -2.5 | -4.4 | -1.9 | **changed last game** (Jaxon Smolik) | same (Marcus Stokes) |
| Middle Tennessee @ Sam Houston | -6.5 | -6.2 | +0.3 | same (Landyn Locke) | same (Roman Gagliano) |
| Missouri State @ Jacksonville State | +10.5 | +9.6 | -0.9 | same (Caden Creel) | same (Henry Belin IV) |
| NC State @ Florida State | +10.5 | +8.1 | -2.4 | same (Ashton Daniels) | same (CJ Bailey) |
| North Carolina @ Virginia | -1.0 | +0.3 | +1.3 | same (Beau Pribula) | same (Billy Edwards) |
| North Texas @ Tulane | -7.5 | -4.0 | +3.5 | same (Trace Johnson) | same (Tayven Jackson) |
| Northern Illinois @ North Dakota State | +25.5 | +20.8 | -4.7 | same (Nathan Hayes) | same (Taron Dickens) |
| Northwestern @ Minnesota | -2.5 | -5.2 | -2.7 | same (Drake Lindsey) | **changed last game** (Nicco Marchiol) |
| Ohio State @ Nebraska | -3.5 | +1.5 | +5.0 | same (Anthony Colandrea) | **changed last game** (Luke Fahey) |
| Oklahoma State @ Arizona State | -2.5 | -0.5 | +2.0 | **changed last game** (Jake Fette) | same (Drew Mestemaker) |
| Old Dominion @ UConn | +13.5 | +10.4 | -3.1 | same (Kalieb Osborne) | **changed last game** (Jaxon Potter) |
| Pittsburgh @ Louisville | +12.5 | +11.0 | -1.5 | same (Lincoln Kienholz) | **changed last game** (Corey Dailey) |
| Rutgers @ Penn State | +26.5 | +17.3 | -9.2 | same (Rocco Becht) | same (AJ Surace) |
| SMU @ Notre Dame | +20.5 | +13.2 | -7.3 | same (C.J. Carr) | same (Kevin Jennings) |
| San Diego State @ Boise State | +18.5 | +13.5 | -5.0 | same (Maddux Madsen) | **changed last game** (Stone Saunders) |
| South Alabama @ Southern Miss | -5.0 | -3.8 | +1.2 | **changed last game** (John White) | **changed last game** (Bishop Davenport) |
| South Florida @ Florida Atlantic | -1.0 | +0.3 | +1.3 | same (Caden Veltkamp) | no read |
| Stanford @ California | -2.5 | -3.1 | -0.6 | same (Jaron-Keawe Sagapolutele) | same (Davis Warren) |
| Syracuse @ Boston College | -3.0 | +0.3 | +3.3 | same (Mason McKenzie) | same (Steven Angeli) |
| Texas A&M @ Oklahoma | +7.0 | +5.3 | -1.7 | same (John Mateer) | same (Marcel Reed) |
| Texas Tech @ Baylor | -5.0 | -0.8 | +4.2 | same (D.J. Lagway) | **changed last game** (Thomas Castellanos) |
| UCLA @ Michigan | -3.5 | -6.7 | -3.2 | **changed last game** (Tommy Carr) | same (Ty Dieffenbach) |
| UL Monroe @ App State | +14.0 | +8.7 | -5.3 | same (Malachi Singleton) | **changed last game** (Austin Carlisle) |
| UNLV @ San José State | -6.5 | -1.6 | +4.9 | same (Luke Weaver) | same (Jackson Arnold) |
| UTSA @ UAB | -5.0 | +1.0 | +6.0 | same (Ryder Burton) | same (Owen McCown) |
| Utah @ TCU | -8.5 | -3.8 | +4.7 | same (Jaden Craig) | same (Devon Dampier) |
| Utah State @ Oregon State | +7.5 | +6.0 | -1.5 | **changed last game** (Maalik Murphy) | **changed last game** (McCae Hillstead) |
| Vanderbilt @ Florida | +13.5 | +7.3 | -6.2 | same (Aaron Philo) | same (Jared Curtis) |
| Virginia Tech @ Miami | +20.5 | +18.0 | -2.5 | same (Darian Mensah) | same (Ethan Grunkemeyer) |
| Wake Forest @ Georgia Tech | -21.5 | -14.0 | +7.5 | same (Alberto Mendoza) | same (Giovanni Lopez) |
| Washington State @ Texas State | +13.5 | +10.9 | -2.6 | same (Brad Jackson) | **changed last game** (Owen Eshelman) |
| Western Kentucky @ Liberty | +17.5 | +15.3 | -2.2 | same (Deshawn Purdie) | **changed last game** (Rodney Tisdale Jr.) |
| Wisconsin @ Purdue | -4.5 | -2.0 | +2.5 | same (Ryan Browne) | **changed last game** (Ryan Hopkins) |
