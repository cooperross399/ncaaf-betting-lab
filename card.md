# NCAAF card — 2026-10-31

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (47 game(s) staged)

Appalachian State Mountaineers @ Georgia Southern Eagles, Arizona State Sun Devils @ BYU Cougars, Arizona Wildcats @ Texas Tech Red Raiders, Army Black Knights @ Memphis Tigers, Auburn Tigers @ Ole Miss Rebels, Boston College Eagles @ Duke Blue Devils, Bowling Green Falcons @ Western Michigan Broncos, California Golden Bears @ NC State Wolfpack, Clemson Tigers @ Florida State Seminoles, Coastal Carolina Chanticleers @ Georgia State Panthers, Colorado State Rams @ Utah State Aggies, Florida Gators @ Georgia Bulldogs, Florida International Panthers @ Liberty Flames, Georgia Tech Yellow Jackets @ Pittsburgh Panthers, Illinois Fighting Illini @ Maryland Terrapins, Kansas Jayhawks @ TCU Horned Frogs, Kansas State Wildcats @ Colorado Buffaloes, Louisiana Tech Bulldogs @ South Alabama Jaguars, Marshall Thundering Herd @ Old Dominion Monarchs, Miami Hurricanes @ North Carolina Tar Heels, Michigan Wolverines @ Rutgers Scarlet Knights, Minnesota Golden Gophers @ Indiana Hoosiers, Mississippi State Bulldogs @ Texas Longhorns, Missouri Tigers @ Arkansas Razorbacks, Nevada Wolf Pack @ UCLA Bruins, New Mexico Lobos @ San Jose State Spartans, Northern Illinois Huskies @ UNLV Rebels, Northwestern Wildcats @ Oregon Ducks, Notre Dame Fighting Irish @ Navy Midshipmen, Ohio State Buckeyes @ USC Trojans, Oklahoma State Cowboys @ Iowa State Cyclones, Oregon State Beavers @ Fresno State Bulldogs, Purdue Boilermakers @ Penn State Nittany Lions, SMU Mustangs @ Syracuse Orange, South Carolina Gamecocks @ Oklahoma Sooners, Southern Mississippi Golden Eagles @ UL Monroe Warhawks, Stanford Cardinal @ Louisville Cardinals, Temple Owls @ East Carolina Pirates, Texas State Bobcats @ Boise State Broncos, UAB Blazers @ South Florida Bulls, UConn Huskies @ Air Force Falcons, UTEP Miners @ North Dakota State Bison, Utah Utes @ Cincinnati Bearcats, Virginia Cavaliers @ Wake Forest Demon Deacons, Washington Huskies @ Nebraska Cornhuskers, Washington State Cougars @ San Diego State Aztecs, Wisconsin Badgers @ Iowa Hawkeyes

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| UTEP Miners @ North Dakota State Bison | `alternate_spread` | away | +10.5 | +420 | fanduel | 26.8% | +7.5% |
| Michigan Wolverines @ Rutgers Scarlet Knights | `alternate_spread` | home | +9.5 | +190 | fanduel | 41.9% | +7.4% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

**Edge floor.** 46 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

**One pick per question.** 8 selection(s) cleared every bar but were other rungs of a question the card already answers, and were not selected: each game's margin, total and team totals carry only their largest edge.

## The accounting identity

`priced 62,402 = no_opinion 15,144 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 47,258 — reconciles.`

- 11798 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 744 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 714 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 712 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 694 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 482 x no margin shape: 'no margin shape for spread bucket (-60.0, -24.0)'

## Forward evidence

47,258 opinion(s) frozen for 2026-10-31; 210,829 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,308 games through 2026-10-31 12:43 UTC; home field +4.4 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-10-25. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| App State @ Georgia Southern | +6.0 | +5.8 | -0.2 | **changed last game** (Turner Helton) | no read |
| Arizona @ Texas Tech | +3.5 | +2.4 | -1.1 | same (Will Hammond) | same (Noah Fifita) |
| Arizona State @ BYU | +16.5 | +12.9 | -3.6 | same (Bear Bachmeier) | **changed last game** (Mikey Keene) |
| Army @ Memphis | +6.0 | +4.1 | -1.9 | same (Marcus Stokes) | same (Cale Hellums) |
| Auburn @ Ole Miss | +11.5 | +11.4 | -0.1 | no read | same (Byrum Brown) |
| Boston College @ Duke | +7.0 | +5.7 | -1.3 | same (Walker Eget) | same (Mason McKenzie) |
| Bowling Green @ Western Michigan | +14.0 | +10.3 | -3.7 | same (Broc Lowry) | same (Jay Kastantin) |
| California @ NC State | +9.5 | +8.2 | -1.3 | no read | same (Jaron-Keawe Sagapolutele) |
| Clemson @ Florida State | +6.0 | +7.6 | +1.6 | same (Ashton Daniels) | no read |
| Coastal Carolina @ Georgia State | +3.5 | +7.0 | +3.5 | **changed last game** (Ayden Pereira) | same (Deuce Bailey) |
| Colorado State @ Utah State | +7.5 | +8.9 | +1.4 | same (Grady Brosterhous) | **changed last game** (Hauss Hejny) |
| Florida @ Georgia | +12.0 | +7.1 | -4.9 | same (Gunner Stockton) | **changed last game** (Tramell Jones Jr.) |
| Florida International @ Liberty | +14.0 | +13.6 | -0.4 | same (Deshawn Purdie) | same (J.J. Kohl) |
| Georgia Tech @ Pittsburgh | +7.5 | +10.5 | +3.0 | **changed last game** (Holden Geriner) | same (Alberto Mendoza) |
| Illinois @ Maryland | -2.5 | -2.1 | +0.4 | same (Malik Washington) | **changed last game** (Michael Clayton II) |
| Kansas @ TCU | +6.0 | +7.2 | +1.2 | same (Jaden Craig) | same (Isaiah Marshall) |
| Kansas State @ Colorado | +3.0 | -0.9 | -3.9 | same (Isaac Wilson) | **changed last game** (Jacob Knuth) |
| Louisiana Tech @ South Alabama | -6.0 | +0.9 | +6.9 | no read | same (Blake Baker) |
| Marshall @ Old Dominion | -2.5 | +1.5 | +4.0 | **changed last game** (Jaxon Potter) | same (Zion Turner) |
| Miami @ North Carolina | -14.0 | -7.5 | +6.5 | same (Billy Edwards) | same (Darian Mensah) |
| Michigan @ Rutgers | -16.0 | -2.2 | +13.8 | **changed last game** (AJ Surace) | **changed last game** (Tommy Carr) |
| Minnesota @ Indiana | +20.5 | +17.1 | -3.4 | same (Josh Hoover) | same (Drake Lindsey) |
| Mississippi State @ Texas | +20.5 | +10.7 | -9.8 | same (Arch Manning) | **changed last game** (Parker Puckett) |
| Missouri @ Arkansas | -10.0 | -1.3 | +8.7 | same (KJ Jackson) | same (Austin Simmons) |
| Nevada @ UCLA | +22.5 | +9.7 | -12.8 | **changed last game** (Ty Dieffenbach) | **changed last game** (Luke Duncan) |
| New Mexico @ San José State | -14.5 | -4.8 | +9.7 | **changed last game** (Robert McDaniel) | no read |
| Northern Illinois @ UNLV | +21.5 | +18.1 | -3.4 | no read | same (Taron Dickens) |
| Northwestern @ Oregon | +3.5 | -0.3 | -3.8 | same (Dylan Raiola) | same (Aidan Chiles) |
| Notre Dame @ Navy | -30.5 | -11.0 | +19.5 | same (Jackson Gutierrez) | same (C.J. Carr) |
| Ohio State @ USC | -6.5 | -3.7 | +2.8 | same (Jayden Maiava) | same (Julian Sayin) |
| Oklahoma State @ Iowa State | -9.5 | -2.0 | +7.5 | **changed last game** (Connor Moberly) | same (Drew Mestemaker) |
| Oregon State @ Fresno State | -6.0 | +1.2 | +7.2 | same (Jayden Mandal) | same (Braden Atkinson) |
| Purdue @ Penn State | +10.5 | +8.1 | -2.4 | same (Rocco Becht) | same (Ryan Browne) |
| SMU @ Syracuse | -9.5 | -1.6 | +7.9 | same (Steven Angeli) | same (Kevin Jennings) |
| South Carolina @ Oklahoma | +3.5 | +4.3 | +0.8 | same (John Mateer) | same (Lanorris Sellers) |
| Southern Miss @ UL Monroe | -3.5 | +3.3 | +6.8 | same (Aidan Armenta) | same (Landy Lyddy) |
| Stanford @ Louisville | +23.0 | +15.1 | -7.9 | no read | same (Davis Warren) |
| Temple @ East Carolina | +4.5 | +7.4 | +2.9 | no read | same (Ajani Sheppard) |
| Texas State @ Boise State | +10.5 | +11.6 | +1.1 | same (Maddux Madsen) | same (Brad Jackson) |
| UAB @ South Florida | +7.5 | +10.7 | +3.2 | no read | same (Ryder Burton) |
| UConn @ Air Force | -1.0 | +3.9 | +4.9 | **changed last game** (Howard Fisher IV) | same (Kalieb Osborne) |
| UTEP @ North Dakota State | +24.0 | +22.1 | -1.9 | same (Nathan Hayes) | **changed last game** (Raymond Moore III) |
| Utah @ Cincinnati | -7.2 | -2.2 | +5.0 | same (JC French) | same (Devon Dampier) |
| Virginia @ Wake Forest | +13.0 | +13.2 | +0.2 | same (Giovanni Lopez) | same (Beau Pribula) |
| Washington @ Nebraska | +7.5 | +10.2 | +2.7 | same (Anthony Colandrea) | **changed last game** (Elijah Brown) |
| Washington State @ San Diego State | +2.5 | +5.9 | +3.4 | **changed last game** (Stone Saunders) | **changed last game** (Owen Eshelman) |
| Wisconsin @ Iowa | +2.5 | +2.2 | -0.3 | same (Hank Brown) | same (Colton Joseph) |
