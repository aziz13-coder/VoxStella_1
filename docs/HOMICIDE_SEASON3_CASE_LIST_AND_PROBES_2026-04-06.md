# Homicide Season 3 Case List And Probes

## Scope

This pass builds a season-level forensic probe set for the Netflix `Homicide` season the user referred to as `S3`.

Official Netflix context:

- Netflix Tudum currently presents these episodes under **Homicide: New York Season 2**
- the Netflix landing page presents **Homicide** as a **3-season** franchise

For the purposes of this repo, this document follows the user's label:

- `Homicide S3`

## Official Episode List

From Netflix Tudum:

1. `Party Monster`
2. `Mother Knows Best`
3. `Soho Horror`
4. `Your Eyes or Your Life`
5. `9/11/2001`

## Exclusion

`9/11/2001` is **not included** in this forensic test set.

Reasons:

1. user instruction: do not include it
2. method fit: it is a mass-casualty terror/disaster event, not a single-case homicide probe

## Included Case Set

The season probe set includes four case-driven episodes:

1. Joey Comunale
2. Irene Silverman
3. Sylvie Cachay
4. Lourdes Gonzalez

Fixture:

- [forensic_external_homicide_season3_cases.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_homicide_season3_cases.json)

Test:

- [test_forensic_homicide_season3_probes.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_homicide_season3_probes.py)

## Case List With Engine Output Vs. Real Events

### 1. Joey Comunale

Episode:

- `Party Monster`

Real event:

- after-hours apartment homicide
- known-person social setting
- later body transport and concealment

Best anchors used:

- `2016-11-13 06:50`
- `2016-11-13 07:00`

Engine output at strongest anchors:

- `Associates: 1`
- `Deception: 3`
- `Public: 1`
- `Violence: 1`

Leading findings:

- `Friend or close associate axis is active`
- `Known-person violence pattern is active in a social or after-hours setting`
- `Sun/Moon in 12th house`

Assessment:

- `partial alignment / strongest-anchor alignment`

Why:

- the best anchors now capture known-person dynamics, violence, and concealment together
- later nearby anchors still soften, so Joey remains a strong exploratory probe rather than a replay-grade benchmark

### 2. Irene Silverman

Episode:

- `Mother Knows Best`

Real event:

- disappearance from townhouse
- later prosecuted as abduction / murder without a recovered body
- strong acquaintance / tenant suspicion

Anchor used:

- `1998-07-05 16:30`

Anchor basis:

- court-supported disappearance window between last sighting at `11:45 a.m.` and confirmed missing status by `4:45 p.m.`
- the frozen chart uses a seizure-window proxy inside that span

Engine output:

- `Abduction: 1`
- `Associates: 1`
- `Deception: 2`
- `Degree Signatures: 1`
- `Houses: 2`
- `Violence: 2`

Leading findings:

- `Life/death overlap points to violence or homicide`
- `Abduction or worksite-seizure pattern is active`
- `Friend or close associate axis is active`

Assessment:

- `aligned`

Why:

- the read is directionally consistent with disappearance, abduction pressure, associate involvement, and presumed homicide
- it is not a pure hidden-custody chart, but it is materially useful

### 3. Sylvie Cachay

Episode:

- `Soho Horror`

Real event:

- intimate-partner homicide in a hotel room
- initial ambiguity around accidental drowning or suicide
- later murder conviction

Anchor used:

- `2010-12-09 02:00`

Anchor basis:

- public reporting places the leak complaint shortly after `2 a.m.`
- Brooks is reported leaving at `2:18 a.m.`
- the frozen chart uses the strongest early hotel-window anchor inside that span

Engine output:

- `Deception: 3`
- `Degree Signatures: 3`
- `Domestic: 2`
- `Houses: 1`
- `Public: 1`
- `Stressors: 1`
- `Violence: 2`

Leading findings:

- `Life/death overlap points to violence or homicide`
- `Hidden victim with angular violence markers`
- `Partner axis is active in a domestic matter`

Assessment:

- `aligned`

Why:

- the strongest anchors capture the partner-violence structure correctly
- some hotel/public scene noise remains, but the core reading is directionally right

### 4. Lourdes Gonzalez

Episode:

- `Your Eyes or Your Life`

Real event:

- stranger home invasion
- adult female homicide victim
- children in another room

Anchor used:

- `1989-06-14 19:00`

Anchor basis:

- lower-confidence evening proxy from public recap material
- unlike Silverman and Cachay, this case does not currently have a strong minute-grade public anchor in our source set

Engine output:

- `Deception: 3`
- `Degree Signatures: 1`
- `Violence: 1`

Leading findings:

- `Stranger-at-home or service-pretext violence pattern is active`
- `Venus-Saturn hard aspects`
- `Node with Neptune/Mercury (karmic ruse/lie scheme)`

Assessment:

- `aligned at strongest evening anchor`

Why:

- the strongest evening anchor now surfaces violence plus deception without forcing the case into spouse or partner language
- that is materially closer to the published stranger home-invasion pattern, even though the public timing window is still lower-confidence than the stronger court-backed cases in this pack

## Season-Level Conclusion

Status by included case:

1. Joey Comunale: `partial alignment at strongest anchors`
2. Irene Silverman: `aligned`
3. Sylvie Cachay: `aligned`
4. Lourdes Gonzalez: `aligned at strongest evening anchor`

Overall:

- the season set is useful
- it is stronger than the initial pass
- all four included case-driven episodes now produce usable or partially usable forensic reads
- Joey remains the softest case in the pack because its strongest alignment is still anchor-sensitive

## Validation

Executed:

```powershell
python -m pytest -q tests/test_forensic_homicide_season3_probes.py tests/test_forensic_homicide_documentary_probe.py
```

This validates:

- all included season probes resolve through `/api/astro-clock/forensic`
- stable anchors keep their required category subsets
- Joey's strongest anchors continue to avoid `Disaster`

## Source Links

- [Netflix Tudum season article](https://www.netflix.com/tudum/articles/homicide-new-york-season-2-release-date-news)
- [ABC7 Joey Comunale timeline](https://abc7ny.com/joey-comunale-james-rackover-lawrence-dilon-socialite/1617730/)
- [CBS Joey Comunale concealment reporting](https://www.cbsnews.com/news/joey-comunale-murder-james-rackover-instagram-facebook-clues/)
- [People v. Kimes court record](https://www.nycourts.gov/reporter/3dseries/2006/2006_09134.htm)
- [CBS 48 Hours on Sylvie Cachay](https://www.cbsnews.com/news/48-hours-was-sylvie-cachays-death-at-soho-house-an-accident-or-murder/)
- [Gothamist on the Cachay timeline](https://gothamist.com/news/boyfriend-questioned-in-fashion-designers-soho-house-death)
- [Yahoo timeline covering Lourdes Gonzalez](https://www.yahoo.com/entertainment/netflix-see-us-tells-story-113000400.html)
- [Cinemaholic recap on Lourdes Gonzalez](https://thecinemaholic.com/lourdes-gonzalez/)
