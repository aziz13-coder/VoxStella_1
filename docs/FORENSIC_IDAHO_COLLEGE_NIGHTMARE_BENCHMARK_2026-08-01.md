# The Idaho Murders: College Nightmare — Forensic Benchmark

Date: 2026-08-01  
Case ID: `netflix_idaho_murders_college_nightmare_2026`  
Evaluation role: development regression, not a holdout

## Scope

This benchmark compares the Vox Stella Forensic engine with a small set of
source-backed, known facts from the Idaho student murders. It is a symbolic
engine regression test. It is not evidence, a reconstruction of the crime, or
prospective validation of forensic astrology.

The documentary title and release are established by
[Netflix Tudum](https://www.netflix.com/tudum/articles/the-idaho-murders-college-nightmare-release-date-trailer-news).
The factual targets come from official court and law-enforcement records, not
from the documentary's narrative framing.

## Ground truth used

- Event: four fatal stabbing homicides at 1122 King Road in Moscow, Idaho, on
  November 13, 2022.
- Official time basis: the investigative interval was 4:00-4:25 a.m. The
  benchmark uses 4:12:30 a.m. only as the interval midpoint and tests both
  endpoints. It does not claim an exact time of death for any victim.
- Outcome: four direct victims and no survivors among that victim group.
- Adjudication: guilty pleas to one burglary count and four first-degree murder
  counts, followed by sentencing.
- Residence context: two roommates survived. One reported seeing a masked
  person inside the house. The cited order does **not** say that either roommate
  witnessed a killing, so no witness axis is expected or scored.

Primary records:

- [Official homicide-window filing](https://coi.isc.idaho.gov/docs/CR01-24-31665/2025/031725-States-Response-Defendants-MiL-12-RE-Make-Model-Suspect-Vehicle.pdf)
- [Court order concerning the surviving roommates' messages and 911 call](https://coi.isc.idaho.gov/docs/CR01-24-31665/2025/042425%2BOrder%2Bon%2BStates%2BMotions%2Bin%2BLimine%2BRE%2BText%2BMessages%2Band%2B911%2BCall.pdf)
- [Plea agreement](https://coi.isc.idaho.gov/docs/CR01-24-31665/2025/070225%2BPlea%2BAgreement.pdf)
- [Moscow Police homicide outcome release](https://www.ci.moscow.id.us/DocumentCenter/View/24998/12-30-22-Arrest-Made-In-Moscow-Homicides)
- [Post-sentencing law-enforcement statement](https://www.ci.moscow.id.us/CivicSend/ViewMessage/Message/265798)

## Benchmark configuration

- Location: `1122 King Road, Moscow, ID, USA`
- Coordinates: `46.7218499, -117.010732`
- Timezone: `America/Los_Angeles`
- House system: Regiomontanus (`R`), the declared application default
- Case type: `general`
- Secondary factors: disabled
- Sensitivity anchors: `04:00:00`, `04:12:30`, and `04:25:00`

## Engine output versus facts

All three time anchors produced the same output:

- axes: `violence_homicide`, `deception_coverup`
- relationship: `stranger_public`
- survivability: `Lower / fatal_pressure_dominant`
- survivability score: `-2.92`

| Comparison | Known fact target | Engine output | Result |
|---|---|---|---|
| Event family | Fatal stabbing homicide | `violence_homicide` | Pass |
| Accident/disaster | Not the documented event family | Absent | Pass |
| Water/drowning | Not present | Absent | Pass |
| Domestic partner | Not established | Absent | Pass |
| Family involvement | Not established | Absent | Pass |
| Child victim | Four adult victims | Absent | Pass |
| Direct-victim outcome | 0 of 4 survived | `Lower / fatal_pressure_dominant` | Pass |
| Relationship | No intimate/family/friend relationship established in these sources | `stranger_public` | Limited contextual match; not a hard check |
| Witness | No eyewitness to a killing established | No `accomplice_or_witness` axis | Not scored; correct benchmark scope |
| Deception/cover-up | Not established by the adjudicated facts used here | `deception_coverup` | Unverified extra; deliberately unscored |

## Result

The engine passes all seven predeclared hard factual checks and is stable across
the full official 25-minute interval. It identifies the core homicide event and
fatal outcome without producing any of the five explicit contradiction axes.

The result is not perfect: `deception_coverup` is an additional symbolic output
that the benchmark facts do not verify. It must not be counted as a factual hit.
The broad `stranger_public` relationship label is lower-confidence context and
does not establish motive, random targeting, or the absence of every prior
contact.

Because this case is already development data and has been inspected during
rule work, the 7/7 result is an in-sample regression result. It does not measure
real-world predictive validity.

## Reproduction

```powershell
backend\.release-venv\Scripts\python.exe -m pytest -q `
  tests\test_forensic_idaho_college_nightmare_benchmark.py

backend\.release-venv\Scripts\python.exe `
  backend\forensic_statistical_benchmark_runner.py `
  --dataset tests\fixtures\forensic_recent_documentaries_2025_2026_cases.json `
  --case-id netflix_idaho_murders_college_nightmare_2026 `
  --json --no-controls --bootstrap-iterations 0
```
