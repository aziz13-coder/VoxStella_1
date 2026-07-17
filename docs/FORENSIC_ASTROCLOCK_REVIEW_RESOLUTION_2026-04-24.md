# Forensic AstroClock Review Resolution - 2026-04-24

## Scope

This pass resolves the three review findings against the AstroClock forensic workflow:

- `child_house_under_stress` promoted adult disaster/abduction charts into `child_victim`.
- Family/household rules leaked into public armed abduction holdouts.
- Survivability pushed documented survived shootings into `Lower / fatal_pressure_dominant`.

The fix stays in source files only:

- `backend/forensic/knowledge/directional_context_rules.yaml`
- `frontend/backend/forensic/knowledge/directional_context_rules.yaml`
- `backend/forensic/survivability.py`
- `frontend/backend/forensic/survivability.py`

## Source Basis

Local sources:

- `docs/FORENSIC_REPLAY_DRIFT_RESTORATION_2026-04-23.md` defines the rule-calibration principle used here: child, family, water, violence, abduction, public, and disaster axes are separate directional labels and require corroboration.
- `docs/FORENSIC_SURVIVABILITY_CALIBRATION_2026-04-23.md` defines survivability as a mechanism-aware score with separate recovery support.
- `tests/fixtures/forensic_case_replay_slice_5.json` freezes TWA Flight 800 as `accident_or_disaster` with `child_victim` and `family_involvement` as contradictions.
- `tests/fixtures/forensic_external_journalist_abduction_candidates.json` freezes Alan Johnston as a public-road abduction released alive, with child/family/domestic/accident as contradictions.
- `tests/fixtures/forensic_external_journalist_abduction_holdout_cases.json` freezes Phil Sands as an armed street abduction released alive, with family/child/domestic/accident as contradictions.
- `tests/fixtures/forensic_survivability_stratified_cases.json` freezes Reagan, Giffords, and John Paul II as survived public shootings while keeping Lindbergh, Phil Hartman, and Marvin Gaye as fatal controls.

External sources:

- CDC child abuse guidance defines child abuse/neglect as harm or threatened harm to a child under 18 by a parent, caregiver, or custodial-role person, supporting a real child-context guard rather than generic 5th-house promotion: https://www.cdc.gov/child-abuse-neglect/about/index.html
- FBI expanded homicide data separates family, other-known, stranger, and unknown offender relationships, supporting separate family and known-person axes: https://ucr.fbi.gov/crime-in-the-u.s/2017/crime-in-the-u.s.-2017/topic-pages/expanded-homicide
- CDC WISQARS separates injury outcome, intent, and mechanism, supporting the change that generic water testimony is not automatically drowning fatality proof: https://wisqars.cdc.gov/help/injury-reports/
- CDC WISQARS nonfatal mechanism definitions list drowning/submersion and firearm gunshot as specific mechanisms, supporting mechanism-specific survivability pressure: https://wisqars-viz.cdc.gov/about/nonfatal-injury-data/
- CDC firearm guidance explicitly separates homicide from nonfatal assault injury for interpersonal firearm violence, supporting survived-shooting controls: https://www.cdc.gov/firearm-violence/about/index.html
- FBI UCR offense definitions distinguish aggravated assault with weapons likely to cause death/great bodily harm from homicide, supporting violent-but-nonfatal classifications: https://ucr.fbi.gov/crime-in-the-u.s/2011/crime-in-the-u.s.-2011/offense-definitions
- NTSB determines TWA Flight 800's probable cause as center wing fuel tank explosion, supporting the disaster axis rather than child/family axes: https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR0003.pdf
- Reagan Library records the March 30, 1981 shooting and Reagan's return to the White House after twelve days, supporting the survived public shooting benchmark: https://www.reaganlibrary.gov/permanent-exhibits/assassination-attempt

## Resolution

Child axis:

- `child_house_under_stress` now requires explicit child case context or compound child/family structure before 5th-house stress can emit `Children`.
- Mars/Saturn or angular malefic pressure no longer turns adult public/disaster charts into child cases by itself.
- Older child-fatal controls still pass through strong child-family structures such as Sun-dominated 5th-house clusters, 4th/5th links, 1st/5th/7th clustering, or perpetrator/home links.

Family axis:

- `family_home_axis_under_pressure` now requires an anchored home/family axis, not Moon-in-8th plus angular malefics alone.
- `family_home_axis_under_pressure` and `family_household_relationship_cluster` now back off when the testimony is a public-place/route seizure pattern without separate household evidence.
- This keeps public armed abductions on the abduction/public axes.

Survivability:

- Generic `Water or drowning signatures are foregrounded` no longer contributes `drowning testimony` to fatal pressure.
- Water fatal pressure is reserved for explicit water-death or water-recovery findings.
- Known-person social violence no longer becomes a fatal mechanism when a disaster/public-event classifier is active without death-edge corroboration.
- Strong recovery support can now block a forced fatal band even when the net score is low, matching the existing rescue/recovery model.

## Engine vs Reality

Post-fix live route output:

| Case | Real outcome | Engine output |
| --- | --- | --- |
| `twa_flight_800` | aviation disaster | `aligned`; `Disaster` present; no `Children` or `Family` |
| `alan_johnston_gaza_abduction` | public street abduction, released alive | `aligned`; `Abduction` present; no child/family contradiction |
| `phil_sands_baghdad_abduction_holdout` | armed street abduction, released alive | `aligned`; `Abduction`/`Public` present; no `Family` or `Children` |
| `reagan_assassination_attempt_survived` | survived targeted public shooting | `Moderate / mixed_nonfatal` |
| `gabrielle_giffords_shooting_survived` | survived public shooting / active-shooter event | `Moderate / mixed_nonfatal` |
| `john_paul_ii_assassination_attempt_survived` | survived targeted public shooting | `Moderate / risk_loaded_survival` |
| `lindbergh_kidnapping_fatal` | abduction ending in death | `Lower / fatal_pressure_dominant` |
| `phil_hartman_known_person_homicide` | fatal domestic homicide | `Lower / fatal_pressure_dominant` |
| `marvin_gaye_known_person_homicide` | fatal family homicide | `Lower / fatal_pressure_dominant` |

## Validation

Focused failing-set rerun:

```powershell
python -m pytest tests\test_forensic_case_replay_slice_5.py tests\test_forensic_journalist_abduction_benchmark.py tests\test_forensic_journalist_abduction_holdout_probes.py tests\test_forensic_survivability_stratified_benchmark.py -q
```

Result: `16 passed, 1 warning, 18 subtests passed`.

Full forensic backend matrix:

```powershell
$files = Get-ChildItem -Path tests -Filter 'test_forensic*.py' | ForEach-Object { $_.FullName }; python -m pytest $files -q
```

Result: `139 passed, 1 warning, 111 subtests passed`.

The warning is the existing `pytz` deprecation warning.
