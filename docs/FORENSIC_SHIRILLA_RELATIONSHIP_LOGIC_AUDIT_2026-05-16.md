# Forensic Shirilla Relationship Logic Audit - 2026-05-16

## Scope

This audit checks the forensic relationship logic against the Mackenzie F. Shirilla case involving the deaths of Dominic "Dom" Russo and Davion Flanagan, the case covered by Netflix's 2026 documentary `The Crash`.

The change is intentionally general. It does not key on Netflix, Shirilla, Strongsville, Russo, Flanagan, or the case id.

## Source-backed case facts

- Incident anchor: July 31, 2022, approximately 5:30 a.m. local time, Strongsville, Ohio. The Cuyahoga County Prosecutor places the crash at approximately 5:30 a.m.; appellate reporting of the record supports a narrow 5:30-5:36 a.m. window.
- Location: Progress Drive and Alameda Drive / PLIDCO building area, Strongsville, Cuyahoga County, Ohio.
- People: Mackenzie Shirilla was 17 at the crash. Dominic Russo was 20 and was Shirilla's boyfriend. Davion Flanagan was 19 and is described in sources as a friend/passenger, with wording varying between Russo's friend, their friend, and two best friends.
- Outcome: Russo and Flanagan died; Shirilla survived. Shirilla was convicted after a bench trial and sentenced to life with first parole eligibility after 15 years. The direct appeal was affirmed.
- Relationship context: court records support a volatile relationship, prior breakups, arguments, and threats. This is prosecution/court-supported context, not a free-standing psychological certainty.

Primary sources:

- Cuyahoga County Prosecutor sentencing release: https://www.ccprosecutor.us/strongsville-woman-sentenced-life-in-prison-crash-killed-two/
- Ohio Court of Appeals, `State v. Shirilla`, 2024-Ohio-4674: https://law.justia.com/cases/ohio/eighth-district-court-of-appeals/2024/113167.html
- AP sentencing report: https://apnews.com/article/ohio-fatal-crash-murder-sentence-88c1c8ab2a292a72fe3f66b6da81b825
- Netflix Tudum `The Crash` article: https://www.netflix.com/tudum/articles/the-crash-release-date-news

## Baseline engine behavior

Input used:

- `datetime`: `2022-07-31T05:30:00`
- `timezone`: `America/New_York`
- `location`: `Progress Drive and Alameda Drive, Strongsville, OH, USA`
- `latitude`: `41.3167`
- `longitude`: `-81.8248`
- `house_system_code`: `R`
- `case_type`: `general`

Baseline strengths:

- The backend normalized the time correctly to `2022-07-31T09:30:00+00:00`.
- The engine identified the route/vehicle crash axis.
- Survivability was directionally aligned: `Lower / fatal_pressure_dominant`.

Baseline relationship gap:

- The live payload produced no relationship category.
- The frontend relationship diagnostic derived `Stranger/Random`, score `0`.
- That underfit the sourced facts: the real case was not random. Russo was the defendant's boyfriend/cohabiting partner; Flanagan was a friend/passenger.

## Logic review

The user's example was sound as a question but not as a direct score by itself:

- Moon in Virgo means the Moon is disposed by Mercury.
- A bare Moon-in-Virgo placement should not automatically imply relationship involvement.
- In this chart, the stronger general testimony is that the Moon's dispositor, Mercury, is tightly opposed to Saturn, the 7th ruler. Saturn is also in the 8th-house/death context.
- Because the same chart also has route/vehicle pressure, this supports a known-person or close-associate bridge. It still does not prove "boyfriend" versus "friend" from astrology alone.

## Calibration decision

Added general Moon-dispositor bridge handling:

- Backend feature extraction now records Moon dispositor, its house, whether it shares the Moon's house, and whether it is hard-linked to the 7th ruler.
- Backend YAML rules now emit `known_person_route_harm_moon_dispositor_bridge` when:
  - the Moon's dispositor is tightly hard-linked to the 7th ruler,
  - the 7th ruler is in death/hidden houses,
  - separate route/vehicle pressure is present.
- Frontend relationship scoring now gives a modest relationship-score reason for this bridge.

Result for the Shirilla chart after calibration:

- Categories: `Associates: 1`, `Disaster: 1`, `Deception: 3`, `Public: 3`.
- Added finding: `Moon dispositor links route harm to a known-person or close associate axis`.
- Frontend relationship summary: `Friend/associate link`, `Low` confidence.
- Score reason: `Moon dispositor hard-linked to perpetrator ruler`.

This is intentionally conservative. It corrects `Stranger/Random` without overclaiming intimate partner involvement.

## Limitations

- The model still cannot distinguish Russo as boyfriend from Flanagan as friend/passenger using chart logic alone.
- The current `case_type` options are coarse and victim-centered; `general` remains the correct input here because the deceased victims were male adults.
- Public/authority findings remain noisy for this chart because 10th-house and solar testimony is high. That is separate from the relationship calibration.
- The benchmark fixture under `tests/fixtures/forensic_netflix_true_crime_2025_2026_cases.json` remains frozen; the added associate signal does not alter the existing primary-axis comparison.

## Verification

- `python -m pytest backend/test_forensic_relationship_dispositor_bridge.py tests/test_forensic_netflix_true_crime_benchmarks.py tests/test_forensic_route_contract.py`
- `npx vitest run --config vitest.config.mjs src/tests/forensicRelationshipLink.test.mjs src/tests/astroClockModeFlow.test.jsx`
