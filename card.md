# NCAAF card — 2026-11-14

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (55 game(s) staged)

Alabama Crimson Tide @ Vanderbilt Commodores, Appalachian State Mountaineers @ Marshall Thundering Herd, Arizona State Sun Devils @ UCF Knights, Arkansas State Red Wolves @ Coastal Carolina Chanticleers, Auburn Tigers @ Mississippi State Bulldogs, Baylor Bears @ BYU Cougars, Boston College Eagles @ Notre Dame Fighting Irish, California Golden Bears @ Virginia Cavaliers, Cincinnati Bearcats @ Iowa State Cyclones, Colorado State Rams @ Washington State Cougars, Duke Blue Devils @ Miami Hurricanes, East Carolina Pirates @ Charlotte 49ers, Florida Atlantic Owls @ Tulsa Golden Hurricane, Florida Gators @ Kentucky Wildcats, Florida International Panthers @ Delaware Blue Hens, Fresno State Bulldogs @ Texas State Bobcats, Georgia Southern Eagles @ Georgia State Panthers, Georgia Tech Yellow Jackets @ Clemson Tigers, Jacksonville State Gamecocks @ Western Kentucky Hilltoppers, James Madison Dukes @ UConn Huskies, Kansas Jayhawks @ West Virginia Mountaineers, Kansas State Wildcats @ TCU Horned Frogs, Kennesaw State Owls @ Sam Houston State Bearkats, Louisville Cardinals @ North Carolina Tar Heels, Michigan Wolverines @ Oregon Ducks, Middle Tennessee Blue Raiders @ Liberty Flames, Minnesota Golden Gophers @ Penn State Nittany Lions, Missouri Tigers @ Georgia Bulldogs, Nebraska Cornhuskers @ Rutgers Scarlet Knights, Nevada Wolf Pack @ Northern Illinois Huskies, New Mexico State Aggies @ Missouri State Bears, North Dakota State Bison @ Hawaii Rainbow Warriors, North Texas Mean Green @ UTSA Roadrunners, Northwestern Wildcats @ Ohio State Buckeyes, Oregon State Beavers @ Boise State Broncos, Purdue Boilermakers @ Iowa Hawkeyes, San Jose State Spartans @ Air Force Falcons, South Carolina Gamecocks @ Arkansas Razorbacks, Southern Mississippi Golden Eagles @ Louisiana Tech Bulldogs, Stanford Cardinal @ Virginia Tech Hokies, Syracuse Orange @ NC State Wolfpack, Tennessee Volunteers @ Texas A&M Aggies, Texas Longhorns @ LSU Tigers, Texas Tech Red Raiders @ Oklahoma State Cowboys, Troy Trojans @ South Alabama Jaguars, Tulane Green Wave @ Rice Owls, UAB Blazers @ Temple Owls, UNLV Rebels @ New Mexico Lobos, USC Trojans @ Indiana Hoosiers, Utah State Aggies @ San Diego State Aztecs, Utah Utes @ Arizona Wildcats, Wake Forest Demon Deacons @ SMU Mustangs, Washington Huskies @ Michigan State Spartans, Wisconsin Badgers @ Maryland Terrapins, Wyoming Cowboys @ UTEP Miners

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

**Bet down to** is the worst price at which a pick still clears the card's 6% edge bar, never worse than -160. Below it, the pick is no longer a selection.

| Game | Market | Selection | Line | Price | Book | Model | Edge | Bet down to |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|------------:|
| Kansas Jayhawks @ West Virginia Mountaineers | `alternate_spread` | away | -5.5 | +275 | betrivers | 32.8% | +6.1% | +274 |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

**Edge floor.** 40 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 67,812 = no_opinion 17,201 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 50,611 — reconciles.`

- 13867 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 864 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 834 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 834 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 802 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

50,611 opinion(s) frozen for 2026-11-14; 328,059 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,426 games through 2026-11-14 15:38 UTC; home field +3.3 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-11-08. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Alabama @ Vanderbilt | -14.0 | -11.0 | +3.0 | same (Jared Curtis) | same (Keelon Russell) |
| App State @ Marshall | -1.5 | +3.6 | +5.1 | same (Zion Turner) | same (Malachi Singleton) |
| Arizona State @ UCF | +3.5 | +4.5 | +1.0 | **changed last game** (Alonza Barnett) | **changed last game** (Jake Fette) |
| Arkansas State @ Coastal Carolina | +1.5 | +3.3 | +1.8 | same (Deuce Bailey) | same (Trey Owens) |
| Auburn @ Mississippi State | -2.5 | +1.6 | +4.1 | **changed last game** (AJ Swann) | same (Byrum Brown) |
| Baylor @ BYU | +8.5 | +1.8 | -6.7 | same (Bear Bachmeier) | same (D.J. Lagway) |
| Boston College @ Notre Dame | +29.0 | +17.3 | -11.7 | same (C.J. Carr) | same (Mason McKenzie) |
| California @ Virginia | +11.5 | +9.5 | -2.0 | same (Beau Pribula) | same (Jaron-Keawe Sagapolutele) |
| Cincinnati @ Iowa State | +3.0 | +3.9 | +0.9 | same (Jaylen Raynor) | same (JC French) |
| Colorado State @ Washington State | +9.5 | +5.6 | -3.9 | **changed last game** (Owen Eshelman) | same (Hauss Hejny) |
| Duke @ Miami | +14.0 | +7.6 | -6.4 | same (Darian Mensah) | same (Walker Eget) |
| East Carolina @ Charlotte | -11.0 | -4.9 | +6.1 | **changed last game** (Conner Harrell) | **changed last game** (Emory Williams) |
| Florida @ Kentucky | +3.0 | +6.4 | +3.4 | same (Kenny Minchey) | **changed last game** (Tramell Jones Jr.) |
| Florida Atlantic @ Tulsa | +6.5 | +5.4 | -1.1 | same (Baylor Hayes) | same (Caden Veltkamp) |
| Florida International @ Delaware | +4.0 | +4.7 | +0.7 | same (Nick Minicucci) | same (J.J. Kohl) |
| Fresno State @ Texas State | +9.5 | +5.7 | -3.8 | same (Brad Jackson) | same (Jayden Mandal) |
| Georgia Southern @ Georgia State | -6.0 | -0.5 | +5.5 | **changed last game** (Ayden Pereira) | same (Max Johnson) |
| Georgia Tech @ Clemson | +15.5 | +13.4 | -2.1 | same (Tait Reynolds) | same (Alberto Mendoza) |
| Jacksonville State @ Western Kentucky | -7.5 | -5.6 | +1.9 | same (Brock Glenn) | same (Caden Creel) |
| James Madison @ UConn | -4.5 | -5.3 | -0.8 | same (Kalieb Osborne) | **changed last game** (JC Evans) |
| Kansas @ West Virginia | +2.5 | +4.2 | +1.7 | same (Michael Hawkins Jr.) | same (Isaiah Marshall) |
| Kansas State @ TCU | +13.5 | +9.4 | -4.1 | same (Jaden Craig) | **changed last game** (Dillon Duff) |
| Kennesaw State @ Sam Houston | -7.5 | -4.7 | +2.8 | same (Landyn Locke) | **changed last game** (Landon Varnes) |
| Louisville @ North Carolina | -3.5 | -0.8 | +2.7 | same (Billy Edwards) | same (Lincoln Kienholz) |
| Michigan @ Oregon | +10.0 | +9.4 | -0.6 | same (Dylan Raiola) | **changed last game** (Tommy Carr) |
| Middle Tennessee @ Liberty | +21.0 | +17.7 | -3.3 | same (Deshawn Purdie) | same (Roman Gagliano) |
| Minnesota @ Penn State | +12.5 | +8.5 | -4.0 | same (Rocco Becht) | same (Drake Lindsey) |
| Missouri @ Georgia | +16.5 | +11.9 | -4.6 | same (Gunner Stockton) | same (Austin Simmons) |
| Nebraska @ Rutgers | -15.0 | -7.1 | +7.9 | same (AJ Surace) | same (Anthony Colandrea) |
| Nevada @ Northern Illinois | -6.0 | -3.7 | +2.3 | same (Taron Dickens) | same (AJ Bianco) |
| New Mexico State @ Missouri State | +1.5 | +4.7 | +3.2 | **changed last game** (Henry Belin IV) | **changed last game** (Trey Hedden) |
| North Dakota State @ Hawai'i | -7.0 | -5.8 | +1.2 | same (Micah Alejado) | same (Nathan Hayes) |
| North Texas @ UTSA | -2.5 | -2.3 | +0.2 | same (Owen McCown) | same (Tayven Jackson) |
| Northwestern @ Ohio State | +14.0 | +5.1 | -8.9 | **changed last game** (Luke Fahey) | **changed last game** (Nicco Marchiol) |
| Oregon State @ Boise State | +16.5 | +11.9 | -4.6 | **changed last game** (Max Cutforth) | same (Braden Atkinson) |
| Purdue @ Iowa | +17.5 | +12.8 | -4.7 | same (Hank Brown) | same (Ryan Browne) |
| San José State @ Air Force | +14.0 | +7.8 | -6.2 | **changed last game** (Evan Medders) | **changed last game** (Daniel Rolovich) |
| South Carolina @ Arkansas | -7.5 | -4.4 | +3.1 | same (KJ Jackson) | same (Lanorris Sellers) |
| Southern Miss @ Louisiana Tech | +17.5 | +16.5 | -1.0 | same (Blake Baker) | **changed last game** (John White) |
| Stanford @ Virginia Tech | +16.8 | +9.1 | -7.6 | same (Ethan Grunkemeyer) | same (Davis Warren) |
| Syracuse @ NC State | -2.5 | +0.8 | +3.3 | same (CJ Bailey) | same (Steven Angeli) |
| Tennessee @ Texas A&M | -1.0 | -3.7 | -2.7 | same (Marcel Reed) | same (George MacIntyre) |
| Texas @ LSU | +4.8 | +2.5 | -2.2 | same (Sam Leavitt) | same (Arch Manning) |
| Texas Tech @ Oklahoma State | +3.5 | +4.3 | +0.8 | same (Drew Mestemaker) | **changed last game** (Thomas Castellanos) |
| Troy @ South Alabama | +3.0 | +6.0 | +3.0 | **changed last game** (Bishop Davenport) | **changed last game** (Tucker Kilcrease) |
| Tulane @ Rice | +3.0 | +0.8 | -2.2 | **changed last game** (Gael Ochoa) | **changed last game** (Trace Johnson) |
| UAB @ Temple | +2.5 | +2.1 | -0.4 | **changed last game** (Jaxon Smolik) | same (Ryder Burton) |
| UNLV @ New Mexico | +17.5 | +12.0 | -5.5 | same (Toa Faavae) | same (Jackson Arnold) |
| USC @ Indiana | +9.5 | +6.9 | -2.6 | same (Josh Hoover) | same (Jayden Maiava) |
| Utah @ Arizona | -1.0 | +0.7 | +1.7 | same (Noah Fifita) | same (Devon Dampier) |
| Utah State @ San Diego State | -2.8 | -1.1 | +1.6 | **changed last game** (Stone Saunders) | **changed last game** (McCae Hillstead) |
| Wake Forest @ SMU | +1.5 | -0.5 | -2.0 | same (Kevin Jennings) | **changed last game** (Steele Pizzella) |
| Washington @ Michigan State | -2.5 | +0.7 | +3.2 | same (Alessio Milivojevic) | same (Demond Williams Jr.) |
| Wisconsin @ Maryland | -8.5 | -4.7 | +3.8 | same (Malik Washington) | **changed last game** (Ryan Hopkins) |
| Wyoming @ UTEP | -7.0 | -7.9 | -0.9 | **changed last game** (Raymond Moore III) | same (Tyler Hughes) |
