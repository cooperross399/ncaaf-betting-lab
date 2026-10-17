# NCAAF card — 2026-10-17

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (52 game(s) staged)

Akron Zips @ Miami (OH) RedHawks, Alabama Crimson Tide @ Tennessee Volunteers, Arizona State Sun Devils @ Texas Tech Red Raiders, Arkansas Razorbacks @ Vanderbilt Commodores, Arkansas State Red Wolves @ Southern Mississippi Golden Eagles, Auburn Tigers @ Georgia Bulldogs, Ball State Cardinals @ Bowling Green Falcons, Charleston Southern Buccaneers @ Clemson Tigers, Charlotte 49ers @ Temple Owls, Cincinnati Bearcats @ West Virginia Mountaineers, Citadel Bulldogs @ Texas A&M Aggies, Elon Phoenix @ Stanford Cardinal, Florida Atlantic Owls @ Army Black Knights, Florida Gators @ Texas Longhorns, Florida State Seminoles @ Miami Hurricanes, Fresno State Bulldogs @ San Diego State Aztecs, Georgia State Panthers @ James Madison Dukes, Georgia Tech Yellow Jackets @ Virginia Tech Hokies, Kansas Jayhawks @ Kansas State Wildcats, Kent State Golden Flashes @ South Florida Bulls, Kentucky Wildcats @ Oklahoma Sooners, Louisiana Tech Bulldogs @ UL Monroe Warhawks, Louisville Cardinals @ Syracuse Orange, Mississippi State Bulldogs @ LSU Tigers, Missouri Tigers @ Ole Miss Rebels, Navy Midshipmen @ UTSA Roadrunners, Nebraska Cornhuskers @ Oregon Ducks, Nevada Wolf Pack @ North Dakota State Bison, New Mexico Lobos @ Hawaii Rainbow Warriors, North Carolina Tar Heels @ Duke Blue Devils, Northern Illinois Huskies @ Wyoming Cowboys, Northwestern Wildcats @ Michigan State Spartans, Notre Dame Fighting Irish @ BYU Cougars, Ohio Bobcats @ Sacramento State Hornets, Ohio State Buckeyes @ Indiana Hoosiers, Oklahoma State Cowboys @ Houston Cougars, Penn State Nittany Lions @ Michigan Wolverines, Pittsburgh Panthers @ Boston College Eagles, Rutgers Scarlet Knights @ Maryland Terrapins, San Jose State Spartans @ UTEP Miners, TCU Horned Frogs @ Baylor Bears, Toledo Rockets @ Eastern Michigan Eagles, Troy Trojans @ Louisiana Ragin Cajuns, Tulsa Golden Hurricane @ Rice Owls, UMass Minutemen @ Buffalo Bulls, UNLV Rebels @ Air Force Falcons, Utah Utes @ Colorado Buffaloes, Virginia Cavaliers @ SMU Mustangs, Wake Forest Demon Deacons @ California Golden Bears, Washington State Cougars @ Oregon State Beavers, Western Michigan Broncos @ Central Michigan Chippewas, Wisconsin Badgers @ UCLA Bruins

## Selections

**Every selection below has no demonstrated edge.** Each cleared the card's bars, which is not a prediction. The markets are allowlisted by an owner's decision rather than by a measurement: no priced test of this model against college prices exists, and every result this lab has measured is a null.

| Game | Market | Selection | Line | Price | Book | Model | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|------:|-----:|
| Fresno State Bulldogs @ San Diego State Aztecs | `alternate_spread` | away | -16 | +255 | betrivers | 35.0% | +6.8% |
| Louisville Cardinals @ Syracuse Orange | `alternate_spread` | home | +10 | +160 | betrivers | 44.9% | +6.4% |
| Louisiana Tech Bulldogs @ UL Monroe Warhawks | `alternate_spread` | home | +10 | +165 | betrivers | 44.2% | +6.4% |

The spread, the total and any ladder rung on one game are one afternoon seen several ways. They are never staked as independent, and their edges are never summed.

**One side per game.** 2 selection(s) also cleared the bars on the other side of 1 game(s) (Wisconsin Badgers @ UCLA Bruins) and were dropped. The side kept is the one whose best price sits furthest from the model, which is not a forecast of who wins: the model's centre is the market's own line.

**Edge floor.** 88 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

**One pick per question.** 1 selection(s) cleared every bar but were other rungs of a question the card already answers, and were not selected: each game's margin, total and team totals carry only their largest edge.

## Games this lab holds no opinion on (3)

Refused by the fixture screen. Not a pass on the game: this lab has no opinion it is entitled to hold on it.

- Charleston Southern Buccaneers @ Clemson Tigers — Charleston Southern Buccaneers is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- Citadel Bulldogs @ Texas A&M Aggies — Citadel Bulldogs matched no known team; a fixture holding an unmatched name is never priced
- Elon Phoenix @ Stanford Cardinal — Elon Phoenix is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only

## The accounting identity

`priced 53,494 = no_opinion 15,591 + unrated_opponent 54 + kickoff_tbd 0 + unresolved 24 + unparseable 0 + opinions 37,825 — reconciles.`

- 12591 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 768 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 746 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 746 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 740 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 28 x Charleston Southern Buccaneers is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- 26 x Elon Phoenix is not an FBS team this season, and the shapes were measured on FBS-vs-FBS games only
- 24 x Citadel Bulldogs matched no known team; a fixture holding an unmatched name is never priced

## Forward evidence

37,825 opinion(s) frozen for 2026-10-17; 108,500 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,193 games through 2026-10-17 12:42 UTC; home field +4.4 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-10-11. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Akron @ Miami (OH) | +9.5 | +11.8 | +2.3 | **changed last game** (Caleb Heavner) | same (Brayden Roggow) |
| Alabama @ Tennessee | -7.5 | -2.0 | +5.5 | **changed last game** (George MacIntyre) | same (Keelon Russell) |
| Arizona State @ Texas Tech | +15.5 | +16.8 | +1.3 | same (Will Hammond) | same (Cutter Boley) |
| Arkansas @ Vanderbilt | +6.0 | +4.9 | -1.1 | same (Jared Curtis) | same (KJ Jackson) |
| Arkansas State @ Southern Miss | -6.5 | +0.9 | +7.4 | same (Landy Lyddy) | same (Trey Owens) |
| Auburn @ Georgia | +19.5 | +15.6 | -3.9 | same (Gunner Stockton) | same (Byrum Brown) |
| Ball State @ Bowling Green | +6.5 | +11.0 | +4.5 | same (Jay Kastantin) | same (Keldric Luster) |
| Charlotte @ Temple | +19.5 | +12.6 | -6.9 | same (Ajani Sheppard) | **changed last game** (Conner Harrell) |
| Cincinnati @ West Virginia | +1.5 | +2.6 | +1.1 | same (Michael Hawkins Jr.) | same (JC French) |
| Florida @ Texas | +11.0 | +10.0 | -1.0 | same (Arch Manning) | same (Aaron Philo) |
| Florida Atlantic @ Army | +2.0 | +3.6 | +1.6 | same (Cale Hellums) | same (Caden Veltkamp) |
| Florida State @ Miami | +20.5 | +16.1 | -4.4 | same (Darian Mensah) | same (Ashton Daniels) |
| Fresno State @ San Diego State | -7.5 | -4.3 | +3.2 | same (Jayden Denegal) | same (Jayden Mandal) |
| Georgia State @ James Madison | +9.5 | +10.0 | +0.5 | same (Camden Coleman) | same (Cameran Brown) |
| Georgia Tech @ Virginia Tech | +8.5 | +8.5 | +0.0 | same (Ethan Grunkemeyer) | same (Alberto Mendoza) |
| Kansas @ Kansas State | +3.5 | +5.0 | +1.5 | same (Avery Johnson) | same (Isaiah Marshall) |
| Kent State @ South Florida | +20.5 | +12.7 | -7.8 | no read | same (Dru Deshields) |
| Kentucky @ Oklahoma | +6.5 | +4.2 | -2.3 | same (John Mateer) | same (Kenny Minchey) |
| Louisiana Tech @ UL Monroe | -15.5 | -1.6 | +13.9 | same (Aidan Armenta) | same (Blake Baker) |
| Louisville @ Syracuse | -14.8 | -0.9 | +13.8 | **changed last game** (Malachi Nelson) | same (Lincoln Kienholz) |
| Massachusetts @ Buffalo | +7.0 | +7.1 | +0.1 | same (Jason Wright) | **changed last game** (Aedan McCarthy) |
| Mississippi State @ LSU | +17.5 | +8.8 | -8.7 | same (Sam Leavitt) | same (Kamario Taylor) |
| Missouri @ Ole Miss | +5.0 | +2.8 | -2.2 | same (Trinidad Chambliss) | same (Austin Simmons) |
| Navy @ UTSA | +6.5 | +5.1 | -1.4 | same (Owen McCown) | same (Jackson Gutierrez) |
| Nebraska @ Oregon | +7.0 | +2.5 | -4.5 | **changed last game** (Dylan Raiola) | same (Anthony Colandrea) |
| Nevada @ North Dakota State | +14.2 | +10.0 | -4.3 | same (Nathan Hayes) | same (Carter Jones) |
| New Mexico @ Hawai'i | -14.5 | -8.3 | +6.2 | same (Micah Alejado) | same (Toa Faavae) |
| North Carolina @ Duke | +3.0 | +7.1 | +4.1 | same (Walker Eget) | same (Billy Edwards) |
| Northern Illinois @ Wyoming | +7.5 | +8.6 | +1.1 | same (Tyler Hughes) | same (Taron Dickens) |
| Northwestern @ Michigan State | -7.0 | -5.8 | +1.2 | same (Alessio Milivojevic) | same (Aidan Chiles) |
| Notre Dame @ BYU | -10.5 | -1.6 | +8.9 | same (Bear Bachmeier) | same (C.J. Carr) |
| Ohio @ Sacramento State | -15.5 | -8.1 | +7.4 | same (Jackson Sharman) | **changed last game** (Nick Poulos) |
| Ohio State @ Indiana | -3.0 | +5.5 | +8.5 | same (Josh Hoover) | same (Julian Sayin) |
| Oklahoma State @ Houston | +4.5 | +10.0 | +5.5 | same (Conner Weigman) | same (Drew Mestemaker) |
| Penn State @ Michigan | +6.5 | +2.6 | -3.9 | same (Bryce Underwood) | same (Rocco Becht) |
| Pittsburgh @ Boston College | -6.5 | -1.7 | +4.8 | same (Mason McKenzie) | no read |
| Rutgers @ Maryland | +5.5 | +5.9 | +0.4 | same (Malik Washington) | same (Dylan Lonergan) |
| San José State @ UTEP | -7.0 | -3.3 | +3.7 | **changed last game** (Raymond Moore III) | same (Luke Weaver) |
| TCU @ Baylor | +5.5 | +8.3 | +2.8 | same (D.J. Lagway) | same (Jaden Craig) |
| Toledo @ Eastern Michigan | -7.0 | +1.8 | +8.8 | same (Noah Kim) | same (John Alan Richter) |
| Troy @ Louisiana | +3.0 | +4.8 | +1.8 | same (D'Wayne' Winfield) | same (Will Crowder) |
| Tulsa @ Rice | -4.5 | +1.4 | +5.9 | same (Jacurri Brown) | same (Baylor Hayes) |
| UNLV @ Air Force | +0.8 | +4.8 | +4.0 | **changed last game** (Taron Dickens) | same (Jackson Arnold) |
| Utah @ Colorado | -14.5 | -9.6 | +4.9 | **changed last game** (Isaac Wilson) | same (Devon Dampier) |
| Virginia @ SMU | +10.0 | +6.6 | -3.4 | same (Kevin Jennings) | same (Beau Pribula) |
| Wake Forest @ California | -10.0 | -5.4 | +4.6 | **changed last game** (Jackson Brousseau) | same (Giovanni Lopez) |
| Washington State @ Oregon State | +18.5 | +15.1 | -3.4 | same (Braden Atkinson) | same (Caden Pinnick) |
| Western Michigan @ Central Michigan | -7.0 | -0.3 | +6.7 | same (Angel H Flores) | same (Broc Lowry) |
| Wisconsin @ UCLA | +2.5 | +7.1 | +4.6 | same (Nico Iamaleava) | same (Colton Joseph) |
