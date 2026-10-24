# NCAAF card — 2026-10-24

**10 market(s) are allowlisted**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`, `team_total`, `total_points`, `total_points_h1`. The approval records an owner's decision, not a measurement.

Shapes fitted on 3,864 finished FBS-vs-FBS games, 2021-2025: 9 of 10 spread buckets and 6 of 6 total buckets carry enough games. Below the floor, so fixtures there get no opinion: spread -60 to -24 (56 games).

## Slate (44 game(s) staged)

Akron Zips @ Kent State Golden Flashes, BYU Cougars @ UCF Knights, Baylor Bears @ Kansas Jayhawks, Boise State Broncos @ Washington State Cougars, Boston College Eagles @ Georgia Tech Yellow Jackets, Bowling Green Falcons @ Buffalo Bulls, California Golden Bears @ SMU Mustangs, Colorado Buffaloes @ Oklahoma State Cowboys, Eastern Michigan Eagles @ Ohio Bobcats, Georgia State Panthers @ Arkansas State Red Wolves, Hawaii Rainbow Warriors @ Northern Illinois Huskies, Houston Cougars @ Utah Utes, Indiana Hoosiers @ Michigan Wolverines, Iowa Hawkeyes @ Minnesota Golden Gophers, Iowa State Cyclones @ Arizona Wildcats, Kansas State Wildcats @ Arizona State Sun Devils, LSU Tigers @ Auburn Tigers, Louisiana Ragin Cajuns @ Southern Mississippi Golden Eagles, Miami (OH) RedHawks @ Central Michigan Chippewas, Michigan State Spartans @ UCLA Bruins, North Dakota State Bison @ New Mexico Lobos, North Texas Mean Green @ Navy Midshipmen, Oklahoma Sooners @ Mississippi State Bulldogs, Old Dominion Monarchs @ Louisiana Tech Bulldogs, Ole Miss Rebels @ Texas Longhorns, Oregon Ducks @ Illinois Fighting Illini, Pittsburgh Panthers @ Miami Hurricanes, Rice Owls @ Florida Atlantic Owls, Rutgers Scarlet Knights @ Northwestern Wildcats, Sacramento State Hornets @ Ball State Cardinals, San Diego State Aztecs @ Colorado State Rams, San Jose State Spartans @ Nevada Wolf Pack, Syracuse Orange @ North Carolina Tar Heels, Tennessee Volunteers @ South Carolina Gamecocks, Texas A&M Aggies @ Alabama Crimson Tide, Texas Tech Red Raiders @ Cincinnati Bearcats, UL Monroe Warhawks @ Troy Trojans, USC Trojans @ Wisconsin Badgers, UTSA Roadrunners @ Tulane Green Wave, Utah State Aggies @ Texas State Bobcats, Vanderbilt Commodores @ Kentucky Wildcats, Virginia Tech Hokies @ Clemson Tigers, West Virginia Mountaineers @ TCU Horned Frogs, Western Michigan Broncos @ Toledo Rockets

## Selections

**None.** Markets are allowlisted, but nothing cleared every bar today. That is a genuine judgement about markets that were priced and modelled.

**Edge floor.** 42 selection(s) on the kept side cleared 3.5% but not 6%, and were not selected: the card selects only edges strictly above 6%.

## The accounting identity

`priced 59,194 = no_opinion 13,910 + unrated_opponent 0 + kickoff_tbd 0 + unresolved 0 + unparseable 0 + opinions 45,284 — reconciles.`

- 11284 x `alternate_team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 668 x `team_total`: a team total needs the joint distribution of margin and total, which this lab has not measured
- 654 x `spread_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 654 x `total_points_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)
- 650 x `moneyline_h1`: first-half markets have no model, and no in-season half-time score source exists to settle them (`docs/build_order.md`, 1.2)

## Forward evidence

45,284 opinion(s) frozen for 2026-10-24; 152,982 row(s) in the settled ledger. Frozen before kickoff, settled after, never repriced.

## Form and quarterbacks — context, not an opinion

Refitted this run from every finished FBS-vs-FBS game, recent games weighing most. **These numbers do not move any probability above**: measured on 2022-2025 they added nothing to the closing or opening line (`data/outputs/nightly_form.md`), so they are a description of how teams are playing, not an edge.

Form rating fitted on 4,252 games through 2026-10-24 12:42 UTC; home field +4.3 points.
Quarterback reads come from cfbfastR's play-level file, which runs through 2026-10-18. **No free source names the coming game's starter**, and no league-wide college injury feed exists; a change flag means a different quarterback took most of the dropbacks last time out.

| Game | Market home margin | Form home margin | Form − market | Home QB | Away QB |
|:---|---:|---:|---:|:---|:---|
| Akron @ Kent State | +3.0 | +7.5 | +4.5 | same (Dru Deshields) | same (Brayden Roggow) |
| BYU @ UCF | -7.5 | -1.8 | +5.7 | same (Keyone Jenkins) | same (Bear Bachmeier) |
| Baylor @ Kansas | -1.0 | +0.1 | +1.1 | same (Isaiah Marshall) | same (D.J. Lagway) |
| Boise State @ Washington State | -14.5 | -8.1 | +6.4 | **changed last game** (Owen Eshelman) | same (Maddux Madsen) |
| Boston College @ Georgia Tech | +6.5 | +3.7 | -2.8 | same (Alberto Mendoza) | same (Mason McKenzie) |
| Bowling Green @ Buffalo | +3.0 | +7.3 | +4.3 | same (Jason Wright) | same (Jay Kastantin) |
| California @ SMU | +18.5 | +12.2 | -6.3 | same (Kevin Jennings) | **changed last game** (Jackson Brousseau) |
| Colorado @ Oklahoma State | +13.5 | +11.3 | -2.2 | same (Drew Mestemaker) | same (Isaac Wilson) |
| Eastern Michigan @ Ohio | +10.0 | +11.9 | +1.9 | **changed last game** (Nick Poulos) | same (Noah Kim) |
| Georgia State @ Arkansas State | -2.5 | +1.5 | +4.0 | same (Trey Owens) | same (Cameran Brown) |
| Hawai'i @ Northern Illinois | -3.5 | +1.6 | +5.1 | same (Taron Dickens) | same (Micah Alejado) |
| Houston @ Utah | +6.8 | +5.4 | -1.4 | same (Devon Dampier) | same (Conner Weigman) |
| Indiana @ Michigan | -7.5 | -5.4 | +2.1 | same (Bryce Underwood) | same (Josh Hoover) |
| Iowa @ Minnesota | -7.5 | -2.6 | +4.9 | same (Drake Lindsey) | **changed last game** (Jeremy Hecklinski) |
| Iowa State @ Arizona | +11.0 | +10.9 | -0.1 | same (Noah Fifita) | same (Jaylen Raynor) |
| Kansas State @ Arizona State | -1.5 | -1.6 | -0.1 | **changed last game** (Mikey Keene) | same (Avery Johnson) |
| LSU @ Auburn | -7.0 | -2.3 | +4.7 | same (Byrum Brown) | same (Sam Leavitt) |
| Louisiana @ Southern Miss | -10.0 | -7.6 | +2.4 | same (Landy Lyddy) | same (D'Wayne' Winfield) |
| Miami (OH) @ Central Michigan | -3.5 | +3.1 | +6.6 | same (Angel H Flores) | **changed last game** (Caleb Heavner) |
| Michigan State @ UCLA | +15.0 | +13.4 | -1.6 | **changed last game** (Ty Dieffenbach) | same (Alessio Milivojevic) |
| North Dakota State @ New Mexico | +4.5 | +3.5 | -1.0 | same (Toa Faavae) | same (Nathan Hayes) |
| North Texas @ Navy | -3.0 | +1.4 | +4.4 | same (Jackson Gutierrez) | same (Tayven Jackson) |
| Oklahoma @ Mississippi State | -2.0 | +3.5 | +5.5 | **changed last game** (Parker Puckett) | same (John Mateer) |
| Old Dominion @ Louisiana Tech | +13.5 | +10.3 | -3.2 | same (Blake Baker) | **changed last game** (Ryan Huff) |
| Ole Miss @ Texas | +3.0 | +0.4 | -2.6 | same (Arch Manning) | same (Trinidad Chambliss) |
| Oregon @ Illinois | -10.0 | -1.8 | +8.2 | same (Katin Houser) | **changed last game** (Brock Thomas) |
| Pittsburgh @ Miami | +20.0 | +14.0 | -6.0 | same (Darian Mensah) | no read |
| Rice @ Florida Atlantic | +8.0 | +10.1 | +2.1 | same (Caden Veltkamp) | same (Jacurri Brown) |
| Rutgers @ Northwestern | +15.5 | +15.9 | +0.4 | same (Aidan Chiles) | same (Dylan Lonergan) |
| Sacramento State @ Ball State | +14.5 | +11.1 | -3.4 | same (Keldric Luster) | same (Jackson Sharman) |
| San Diego State @ Colorado State | -1.0 | +0.4 | +1.4 | same (Ksaan Farrar) | same (Jayden Denegal) |
| San José State @ Nevada | +6.5 | +7.4 | +0.9 | **changed last game** (AJ Bianco) | **changed last game** (Daniel Rolovich) |
| Syracuse @ North Carolina | +9.0 | +8.8 | -0.2 | same (Billy Edwards) | **changed last game** (Malachi Nelson) |
| Tennessee @ South Carolina | +2.5 | -1.4 | -3.9 | same (Lanorris Sellers) | **changed last game** (George MacIntyre) |
| Texas A&M @ Alabama | +13.5 | +11.5 | -2.0 | same (Keelon Russell) | same (Marcel Reed) |
| Texas Tech @ Cincinnati | -11.5 | -6.8 | +4.7 | same (JC French) | same (Will Hammond) |
| UL Monroe @ Troy | +12.0 | +12.3 | +0.3 | same (Will Crowder) | same (Aidan Armenta) |
| USC @ Wisconsin | -3.0 | +2.8 | +5.8 | same (Colton Joseph) | same (Jayden Maiava) |
| UTSA @ Tulane | -3.0 | +4.2 | +7.2 | **changed last game** (Trace Johnson) | same (Owen McCown) |
| Utah State @ Texas State | +13.5 | +8.5 | -5.0 | same (Brad Jackson) | same (Grady Brosterhous) |
| Vanderbilt @ Kentucky | +10.5 | +12.7 | +2.2 | same (Kenny Minchey) | same (Jared Curtis) |
| Virginia Tech @ Clemson | +2.5 | +3.1 | +0.6 | same (Tait Reynolds) | same (Ethan Grunkemeyer) |
| West Virginia @ TCU | +10.5 | +10.9 | +0.4 | same (Jaden Craig) | same (Michael Hawkins Jr.) |
| Western Michigan @ Toledo | +2.5 | +4.0 | +1.5 | same (John Alan Richter) | same (Broc Lowry) |
