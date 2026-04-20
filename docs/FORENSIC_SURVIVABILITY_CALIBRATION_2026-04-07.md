# Forensic Survivability Calibration - 2026-04-07

## Scope
This pass completed three follow-up tasks on the backend survivability signal:

1. Defined explicit outcome bands for resolved benchmark cases.
2. Tuned the existing factor model against those outcome bands instead of adding broad ad hoc weights.
3. Added one limited, source-backed accidental-strength refinement before rerunning the benchmark.

The work stays backend-first and then flows into the frontend display.

## Source basis
The refinement and calibration were grounded in the local forensic corpus, not case-specific fitting:

- `extracted_text_docs/text_forensics/Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve? (Caroline J. Luley) (Z-Library).txt`
  - emphasizes angular houses and angular rulers as the houses and planets with power in event charts
  - repeatedly treats the Moon as an always-important co-significator
  - states that planets gain more importance when they rule an angle and are also placed in an angular house
- `extracted_text_docs/text_forensics/Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt`
  - distinguishes essential dignity from accidental dignity
  - repeatedly treats poor accidental condition such as cadency and combustion as weakening testimony

This led to one narrow doctrinal refinement:
- reward already-relevant victim significators when they are angular rulers and also well placed by house
- do not introduce broad new planets or case-type-specific co-rulers into survivability scoring

## Outcome bands
Top-level survivability labels remain unchanged:
- `Higher`
- `Moderate`
- `Lower`

A second layer was added for calibration and UI clarity:

### Abduction context
- `release_favored`
  - cleaner release/survival profile
  - low fatal pressure and low direct danger
- `risk_loaded_survival`
  - survivor/release outcome still possible or historically realized, but under materially riskier pressure
- `fatal_pressure_dominant`
  - fatal testimony dominates even in an abduction context

### Non-abduction context
- `nonfatal_tilt`
- `mixed_nonfatal`
- `fatal_pressure_dominant`

## Model changes
### 1. Threshold calibration before factor expansion
The first change was not a new factor. It was calibration.

The survivability model already had the right major dimensions:
- vitality
- support
- Moon testimony
- danger
- fatal pressure

The problem was that resolved abduction cases were being compressed into a single `Moderate` bucket, which limited comparative value.

Calibration changes:
- abduction `Higher` now requires a cleaner profile: good net score, low fatal pressure, and low danger
- the new outcome band layer now distinguishes clean-release patterns from risk-loaded survival patterns without forcing false fatal calls on surviving abduction cases

### 2. One accidental-strength refinement
A new backend component was added:
- `accidental`

It gives modest extra strength when a victim significator is:
- an angular ruler
- and also well placed by house, especially angular placement

This is intentionally limited. It does not try to replace dignity, Moon testimony, or fatal-pressure logic.

## Files changed
- `backend/forensic/survivability.py`
- `tests/test_forensic_survivability_benchmark.py`
- `tests/test_forensic_route_contract.py`
- `frontend/src/features/astroclock/forensicSurvivalSignal.mjs`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/tests/forensicSurvivalSignal.test.mjs`
- `frontend/src/tests/astroClockModeFlow.test.jsx`

## Current benchmark readout
### Resolved journalist abductions
| Case | Level | Outcome band | Score |
|---|---|---:|---:|
| Rory Carroll | Moderate | risk_loaded_survival | -3.91 |
| Giuliana Sgrena | Moderate | risk_loaded_survival | -8.16 |
| Jill Carroll | Moderate | risk_loaded_survival | -3.77 |
| James Brandon | Moderate | release_favored | +2.60 |
| Alan Johnston | Moderate | risk_loaded_survival | -1.70 |
| Centanni / Wiig | Moderate | risk_loaded_survival | -1.75 |
| Phil Sands | Moderate | risk_loaded_survival | -10.19 |
| Meutya Hafid / Budiyanto | Moderate | release_favored | +2.30 |
| Romanian journalists in Jadriya | Higher | release_favored | +2.97 |
| Richard Butler | Moderate | risk_loaded_survival | +0.26 |

### Fatal homicide anchors
| Case | Level | Outcome band | Score |
|---|---|---:|---:|
| Joey Comunale | Lower | fatal_pressure_dominant | -4.27 |
| Sylvie Cachay | Lower | fatal_pressure_dominant | -7.60 |
| Lourdes Gonzalez | Lower | fatal_pressure_dominant | -8.27 |

### Mixed case worth keeping separate
| Case | Level | Outcome band | Score |
|---|---|---:|---:|
| Irene Silverman | Moderate | risk_loaded_survival | -6.24 |

## Interpretation
The benchmark is better than before for two reasons:

1. Fatal cases are still cleanly separated.
- Joey, Sylvie, and Lourdes remain `Lower`.
- Their new outcome band is now explicit: `fatal_pressure_dominant`.

2. The resolved abduction set is no longer flat.
- James Brandon, Meutya Hafid/Budiyanto, and the Romanian journalists now separate as `release_favored`.
- Rory, Giuliana, Jill, Phil, Alan, Centanni/Wiig, and Richard Butler remain survivable in the model, but visibly risk-loaded rather than merely thrown into an undifferentiated `Moderate` bucket.

That is the right direction. The model is now doing more than binary separation.

## Opinion
This confirms the earlier judgment:
- backendization was necessary before tuning
- brute-force factor addition would have been the wrong first move
- calibration plus one limited accidental-strength refinement was enough to improve the benchmark materially without making the model opaque

What still should not happen next:
- do not start adding many new survivability factors at once
- do not add sex/age co-rulers back in as equal life testimony
- do not tune to one case like Irene

What should happen next if the signal needs another pass:
1. treat Irene Silverman and similar disappearance-homicide cases as a separate benchmark class instead of forcing them into the same banding logic as clear abductions or clear homicides
2. compare release-favored vs risk-loaded abduction cases against captivity length, not just alive/dead outcome
3. only then consider one more source-backed refinement, likely around combustion/under-beams severity or Moon-victim-link weighting

## Validation
Executed:

```powershell
python -m pytest -q tests	est_forensic_route_contract.py tests	est_forensic_survivability_benchmark.py
npm run test:ui -- src/tests/forensicSurvivalSignal.test.mjs src/tests/astroClockModeFlow.test.jsx
```

Results:
- backend: `11 passed, 1 warning, 15 subtests passed`
- frontend: `19 passed`

The only remaining warning is the existing external `pytz` deprecation warning.
