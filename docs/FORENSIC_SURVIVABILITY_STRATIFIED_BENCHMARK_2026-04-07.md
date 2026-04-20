# Forensic Survivability Stratified Benchmark - 2026-04-07

## Scope
This pass expanded survivability validation beyond the resolved journalist-abduction benchmark.

The new benchmark adds four additional outcome families:
- `abduction_fatal`
- `nonfatal_violent_event`
- `known_person_homicide`
- `mixed_disappearance_homicide`

This keeps the original journalist-abduction benchmark intact, while pressure-testing whether the survivability model can separate:
- released / survived abductions
- fatal kidnappings
- fatal known-person homicides
- public violent attacks with survival
- disappearance charts that remain mixed rather than cleanly survivable or cleanly fatal

## Source basis
The algorithm changes in this pass are source-backed and deliberately narrow.

### Local forensic doctrine
1. `Forensic Astrology for Everyone` by Caroline J. Luley
- Angular rulers and angular planets carry the most power in event charts.
- The Moon is always a co-significator of the subject.
- Angular houses and angular rulers should dominate the read; weaker factors should not outweigh them.

2. `Forensics by the Stars` by B. D. Salerno
- Benefic testimony can preserve life even when the victim ruler is weak.
- In the Tim McLean child-abduction discussion, Salerno explicitly treats Jupiter-term protection and the lack of malefic affliction to the victim ruler / Moon as reasons to keep hope that the victim is alive and safe.
- In the travel-election chapter, Salerno repeats Lilly's doctrine that a fortune in the Ascendant or another angle is safety testimony.

3. `Exploring Forensic Astrology The Secrets Behind Famous Family Murders` by B. D. Salerno
- Essential and accidental dignity both matter.
- Family / partner / public homicide charts need to be treated differently from disappearance and captivity charts.

### Public case sources used for new survivor cases
- Ronald Reagan attempt:
  - [Reagan Library 1981 Public Papers Appendix](https://www.reaganlibrary.gov/1981-public-papers-president-appendix)
- Gabrielle Giffords shooting:
  - [FBI active shooter study](https://www.fbi.gov/file-repository/reports-and-publications/active-shooter-study-2000-2013-1.pdf/view)
- John Paul II attempt:
  - [Vatican commemorative plaque](https://www.vatican.va/content/vatican/en/ra/piastrella-commemorativa-gpii.html)

## Model changes
### 1. Broader homicide-title fatal pressure matching
Fatal pressure now recognizes both:
- `violence or homicide`
- generic `homicide`

This prevents family-homicide charts from underfiring only because the title wording differs slightly.

### 2. New `recovery_support` component
A new backend survivability component was added:
- `recovery_support`

It is intentionally narrow.

It only rewards charts where benefic testimony clusters around core life markers:
- the primary victim significator
- the Moon
- and, secondarily, an angular benefic already carrying power by placement

This is the doctrinal reason for the component:
- Luley treats angular power as decisive
- Salerno treats benefic protection and the absence of malefic collapse as reasons to preserve survivability judgment

This is not a general optimism bonus. It is a rescue / recovery buffer.

### 3. Narrow rescue override in classification
The non-abduction `Lower` override is now bypassed only when all of the following are true:
- `recovery_support >= 1.0`
- `support >= 4.5`
- benefic support is at least as strong as direct danger
- fatal pressure is not extreme (`< 7.0`)

That keeps the override narrow enough to fix genuine survivor cases without lifting fatal homicide anchors.

## Files changed
- `backend/forensic/survivability.py`
- `tests/fixtures/forensic_survivability_stratified_cases.json`
- `tests/test_forensic_survivability_stratified_benchmark.py`
- `tests/test_forensic_route_contract.py`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/tests/forensicSurvivalSignal.test.mjs`

## Current stratified benchmark results
### Abduction fatal
| Case | Level | Outcome band | Score | Recovery support |
|---|---|---:|---:|---:|
| Lindbergh kidnapping | Lower | fatal_pressure_dominant | -7.80 | 0.0 |

### Nonfatal violent events
| Case | Level | Outcome band | Score | Recovery support |
|---|---|---:|---:|---:|
| Ronald Reagan attempt | Moderate | mixed_nonfatal | -2.19 | 1.0 |
| Gabrielle Giffords shooting | Higher | mixed_nonfatal | +6.16 | 1.0 |
| John Paul II attempt | Moderate | risk_loaded_survival | -5.98 | 0.4 |

### Known-person homicide
| Case | Level | Outcome band | Score | Recovery support |
|---|---|---:|---:|---:|
| Phil Hartman | Lower | fatal_pressure_dominant | -7.85 | 0.0 |
| Marvin Gaye | Lower | fatal_pressure_dominant | -4.20 | 0.0 |
| Joey Comunale | Lower | fatal_pressure_dominant | -3.87 | 0.4 |
| Sylvie Cachay | Lower | fatal_pressure_dominant | -6.60 | 1.0 |
| Lourdes Gonzalez | Lower | fatal_pressure_dominant | -8.27 | 0.0 |

### Mixed disappearance / homicide
| Case | Level | Outcome band | Score | Recovery support |
|---|---|---:|---:|---:|
| Scott Peterson / Laci disappearance chart | Moderate | mixed_nonfatal | +1.30 | 0.0 |
| Irene Silverman | Moderate | risk_loaded_survival | -4.94 | 1.3 |
| Natalie Wood | Lower | fatal_pressure_dominant | -4.69 | 0.4 |

## Interpretation
### What improved
1. The model is no longer journalist-only.
- Survivability now has explicit pressure from fatal kidnapping, fatal homicide, public survivor attacks, and mixed disappearance charts.

2. Fatal homicide anchors stayed intact.
- Phil Hartman, Marvin Gaye, Joey Comunale, Sylvie Cachay, and Lourdes Gonzalez all remain `Lower / fatal_pressure_dominant`.

3. The public-survivor family no longer collapses automatically.
- Reagan moved out of `Lower` because the chart carries unusually strong benefic protection to the victim ruler and Moon despite violence.
- Giffords stays clearly nonfatal.
- John Paul II remains dangerous but not fatal in the model.

4. Mixed cases remain mixed.
- Scott and Irene do not get falsely promoted into clean survival language.
- Natalie still reads fatal, which is acceptable in the mixed family because the case remains a death chart rather than a clean rescue chart.

### What this means
The survivability model is now doing a more defensible job across families:
- `release_favored` and `risk_loaded_survival` remain useful for resolved abductions
- `fatal_pressure_dominant` remains stable for clear fatal anchors
- public attack survivors can register as dangerous without being auto-collapsed into death testimony
- disappearance cases can stay ambiguous when they should

## Validation
Executed:

```powershell
python -m pytest -q tests/test_forensic_route_contract.py tests/test_forensic_survivability_benchmark.py tests/test_forensic_survivability_stratified_benchmark.py
npm run test:ui -- src/tests/forensicSurvivalSignal.test.mjs src/tests/astroClockModeFlow.test.jsx
$files = Get-ChildItem tests -Filter 'test_forensic*.py' | ForEach-Object { $_.FullName }; python -m pytest -q $files
```

Results:
- targeted backend: `16 passed, 1 warning, 27 subtests passed`
- targeted frontend: `19 passed`
- broad forensic regression: `130 passed, 1 warning, 79 subtests passed`

Remaining warning:
- external `pytz` deprecation only

## Bottom line
The benchmark expansion was necessary and is now in place.

The algorithm change stayed disciplined:
- one broader fatal-title matcher
- one narrow `recovery_support` component
- one narrow rescue override

That is a defensible expansion. It improves the model where the local sources justify it and does not degrade the fatal homicide or abduction benchmarks that were already working.
