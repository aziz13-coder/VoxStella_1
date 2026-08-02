# The Idaho Murders: College Nightmare — Forensic Benchmark

Date audited: 2026-08-02

Case ID: `netflix_idaho_murders_college_nightmare_2026`

Evaluation role: development regression, not a holdout

## Scope

This benchmark compares the Vox Stella Forensic engine with a predeclared set
of source-backed facts from the Idaho student murders. It is a symbolic engine
regression test. It is not evidence, a crime reconstruction, or prospective
validation of forensic astrology.

The documentary title and release are established by
[Netflix Tudum](https://www.netflix.com/tudum/articles/the-idaho-murders-college-nightmare-release-date-trailer-news).
The factual targets come from official court and law-enforcement records, not
from the documentary's narrative framing.

## Ground truth used

- Event: four fatal stabbing homicides at 1122 King Road in Moscow, Idaho, on
  November 13, 2022.
- Official time basis: investigators placed the homicides between 4:00 and
  4:25 a.m. The benchmark uses 4:12:30 a.m. only as the interval midpoint and
  tests both endpoints. It does not claim an exact time of death for any victim.
- Outcome: all four members of the direct-victim group died.
- Victim ages: 20, 20, 21, and 21.
- Adjudication: guilty dispositions on one burglary count and four first-degree
  murder counts, followed by sentencing on July 23, 2025.
- Residence context: two roommates survived. One reported seeing a masked
  intruder inside the house. The cited order does not say either roommate
  witnessed a killing, so a witness axis is not scored.

Primary records:

- [Official homicide-window filing](https://coi.isc.idaho.gov/docs/CR01-24-31665/2025/031725-States-Response-Defendants-MiL-12-RE-Make-Model-Suspect-Vehicle.pdf)
- [Court order concerning the surviving roommates' messages and 911 call](https://coi.isc.idaho.gov/docs/CR01-24-31665/2025/042425%2BOrder%2Bon%2BStates%2BMotions%2Bin%2BLimine%2BRE%2BText%2BMessages%2Band%2B911%2BCall.pdf)
- [Plea agreement](https://coi.isc.idaho.gov/docs/CR01-24-31665/2025/070225%2BPlea%2BAgreement.pdf)
- [Current official case summary](https://coi.isc.idaho.gov/docs/CR01-24-31665/Summary/Current-Case-Summary.pdf)
- [Moscow Police homicide facts and investigative timeline](https://www.ci.moscow.id.us/CivicSend/ViewMessage/message/188862)
- [Moscow Police victim identification and ages](https://www.ci.moscow.id.us/CivicSend/ViewMessage/Message/186660)
- [Post-sentencing law-enforcement statement](https://www.ci.moscow.id.us/CivicSend/ViewMessage/Message/265798)

## Comparison policy

Six outputs are hard-scored:

1. `violence_homicide` must be present.
2. `accident_or_disaster` must be absent.
3. `water_disappearance_or_drowning` must be absent.
4. `abduction_missing_person` must be absent.
5. `child_victim` must be absent.
6. Survivability must align with the fatal outcome direction.

The earlier seven-check version counted absent family and partner axes as hard
successes. That was too strong: the benchmark records do not establish those
relationships, but absence of evidence is not a verified negative. Family,
partner, friend/acquaintance, witness, motive, deception/cover-up, and the
engine's broad relationship label are therefore observations only.

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
- relationship: `stranger_public` (unscored)
- survivability: `Lower / fatal_pressure_dominant`
- survivability score: `-2.92`

| Comparison | Known fact target | Engine output | Result |
|---|---|---|---|
| Event family | Four-victim stabbing homicide | `violence_homicide` | Pass |
| Accident/disaster | Documented intentional homicide | Absent | Pass |
| Water/drowning | Victims found in the residence; homicide by stabbing | Absent | Pass |
| Abduction/missing person | Four victims found inside the residence | Absent | Pass |
| Child victim | Victims were ages 20–21 | Absent | Pass |
| Direct-victim outcome | 0 of 4 survived | `Lower / fatal_pressure_dominant` | Pass |
| Relationship | No relationship class established by the benchmark records | `stranger_public` | Not scored |
| Witness | No eyewitness to a killing established | No `accomplice_or_witness` axis | Not scored |
| Deception/cover-up | Not established by the facts used here | `deception_coverup` | Unverified extra; not scored |

## Result

The engine passes all six evidence-supported hard checks and produces the same
classification across the full official 25-minute interval. It identifies the
core homicide event and fatal outcome without producing any declared
contradiction axis.

The output is not a complete factual match. `deception_coverup` is an
additional symbolic output that the benchmark facts do not verify and receives
no credit. The broad `stranger_public` label is also unscored because it cannot
establish motive, random targeting, or the absence of every prior contact.

Because this case has already been inspected during engine development, the
6/6 result is an in-sample regression result. It does not measure real-world
predictive validity. The benchmark can detect future code regressions, but it
cannot demonstrate that an astrological chart identifies a crime or offender.

## Reproduction

Human-readable fact comparison:

```powershell
backend\.release-venv\Scripts\python.exe `
  backend\forensic_idaho_benchmark_runner.py
```

Machine-readable result:

```powershell
backend\.release-venv\Scripts\python.exe `
  backend\forensic_idaho_benchmark_runner.py --json
```

Regression tests:

```powershell
backend\.release-venv\Scripts\python.exe -m pytest -q `
  tests\test_forensic_idaho_college_nightmare_benchmark.py
```
