# Forensic Replay Drift Restoration - 2026-04-23

## Scope

This pass analyzed and resolved outcome-vs-engine drift in older forensic replay slices after the survivability and Netflix benchmark calibrations.

The issue was not a survivability regression. Explicit survivability expectations were already stable. The drift was in the directional rule layer: some older local family, child, and water/violence outcomes no longer matched live engine output after prior rule tightening.

## Drift Before Fix

The live outcome-vs-engine audit found seven older local replay cases that had drifted from their stored aligned baseline:

| Fixture | Case | Before | Missing axis |
| --- | --- | --- | --- |
| `forensic_case_replay_slice_1.json` | `natalie_wood` | partial | `violence_homicide` |
| `forensic_case_replay_slice_1.json` | `jonbenet_ramsey` | partial | `child_victim` |
| `forensic_case_replay_slice_1.json` | `susan_smith` | partial | `family_involvement`, `child_victim`, `violence_homicide` |
| `forensic_case_replay_slice_2.json` | `andrea_yates` | partial | `family_involvement`, `child_victim` |
| `forensic_case_replay_slice_2.json` | `darlie_routier` | partial | `family_involvement`, `child_victim` |
| `forensic_case_replay_slice_2.json` | `lizzie_borden` | partial | `family_involvement` |
| `forensic_case_replay_slice_2.json` | `amityville_defeo` | misaligned | `family_involvement`, `violence_homicide` |

The root cause was over-correction from earlier false-positive prevention. The engine had become too reluctant to read family/child homicide clusters unless they matched the newer narrow forms. That protected public and abduction benchmarks, but it also erased legitimate older slice patterns where family and child testimony is carried by 4th/5th ruler links, 5th/11th pressure, or a home/opponent homicide axis.

## Source Basis

Local forensic corpus:

- `docs/FORENSIC_CORPUS_EVALUATION_PLAN.md` defines benchmark evaluation as broad directional axes, not exact narrative reproduction.
- `docs/FORENSIC_GENERIC_DRIFT_FIX_2026-04-03.md` requires compound testimony for family and child labels and warns against single-symbol family drift.
- `docs/FORENSIC_NETFLIX_BENCHMARK_CALIBRATION_2026-04-23.md` keeps child, family, public, water, and abduction as separate axes and explicitly warns that the 5th house must not become a child label by itself.
- `extracted_text_docs/text_forensics/Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt` treats family homicide, filicide, parricide, familicide, and murder by friend as distinct case families. Its worked examples use compound 4th/5th/7th/10th, Sun/Moon/Jupiter, and death-pressure testimony rather than a single home or child marker.
- The local text file in `extracted_text_docs/text_forensics/` whose name begins `Forensic Astrology for Everyone` separates the 4th as home/location/family, the 5th as children but also recreation/pleasure/parties, the 7th as murderer/abductor/accomplice, and the 10th as public/authority context. That supports requiring multi-axis corroboration.

External taxonomy sources:

- FBI UCR supplementary homicide data records victim/offender relationship and circumstances, and separates family, other-known, stranger, and unknown offender relationships:
  https://ucr.fbi.gov/crime-in-the-u.s/2017/crime-in-the-u.s.-2017/topic-pages/expanded-homicide
- FBI UCR domestic/family-violence reporting treats murder and other violent crimes as reportable where the victim-to-offender relationship meets domestic/family definitions:
  https://www.fbi.gov/news/press-releases/fbi-releases-domestic-violence-special-report
- BJS family violence guidance treats domestic/family violence as broader than an isolated incident and recognizes children as victims or witnesses in the justice process:
  https://bjs.ojp.gov/feature/family-violence/overview
- CDC child abuse/neglect definitions require a child under 18 plus harm, potential harm, or threat of harm by a parent, caregiver, or custodial-role person:
  https://www.cdc.gov/child-abuse-neglect/about/index.html
- CDC WISQARS separates injury intent from mechanism, and defines mechanisms such as drowning/submersion separately from violence-related intent:
  https://wisqars.cdc.gov/help/injury-reports/
  https://wisqars-viz.cdc.gov/about/nonfatal-injury-data/

These sources support the calibration principle: family, child, violence, water, and abduction should be general mechanism/context axes, but a label should require the same kind of relationship or mechanism evidence that the axis claims.

## Code Changes

Added shared family-child feature extraction in both backend source twins:

- `houses.fourth_and_fifth_same_ruler`
- `houses.fourth_and_fifth_rulers_same_house`

Added/restored general rules in both source twins:

- `child_parental_harm_cluster`
- `family_child_homicide_axis_cluster`
- `family_home_opponent_homicide_axis`
- `violence_water_death_under_malefic_pressure`

Then tightened the restored rules after full-suite controls exposed temporary false positives:

- shared 4th/5th rulers no longer create family labels by themselves
- 6th-house shared ruler patterns require actual 5th-house density, first-ruler-in-5th testimony, or Mars pressure on the 5th/11th axis
- 5th-ruler-in-8th/12th child patterns require child context, first/seventh linkage, 5th density, or 4th-ruler affliction
- Mars in the 5th/11th requires child context or a stronger first/fifth/seventh or fifth/seventh cluster
- home/opponent family homicide now requires life/death ruler pressure, preventing child home-intrusion abduction from being mislabeled as family homicide

No case-id exceptions were added.

## Outcome After Fix

Live replay outcome audit:

- local replay slices 1-6 plus external replay slices 1-3: `28 / 28` aligned
- no partial or misaligned replay cases remained

The seven original drifted local cases are now aligned again:

| Case | After |
| --- | --- |
| `natalie_wood` | aligned |
| `jonbenet_ramsey` | aligned |
| `susan_smith` | aligned |
| `andrea_yates` | aligned |
| `darlie_routier` | aligned |
| `lizzie_borden` | aligned |
| `amityville_defeo` | aligned |

Regression controls that stayed protected:

- `mlk_assassination`: public/violence aligned, no family contradiction
- `shinzo_abe_assassination`: public/violence aligned, no family contradiction
- `centanni_wiig_gaza_abduction`: abduction aligned, no family/child contradiction
- `elizabeth_smart_abduction`: child/abduction aligned, no family contradiction
- `shannan_gilbert_lisk_911_anchor`: missing-person/water/violence aligned, no child contradiction

## Tests

Focused restored-slice tests:

```powershell
python -m pytest tests\test_forensic_case_replay_slice_1.py tests\test_forensic_case_replay_slice_2.py -q
```

Result: `8 passed, 14 subtests passed`.

Historical replay batches:

```powershell
python -m pytest tests\test_forensic_case_replay_slice_1.py tests\test_forensic_case_replay_slice_2.py tests\test_forensic_case_replay_slice_3.py tests\test_forensic_case_replay_slice_4.py tests\test_forensic_case_replay_slice_5.py tests\test_forensic_case_replay_slice_6.py tests\test_forensic_external_replay_slice_1.py tests\test_forensic_external_replay_slice_2.py tests\test_forensic_external_replay_slice_3.py -q
```

Result: `33 passed, 24 subtests passed`.

Full forensic backend matrix:

```powershell
$files = Get-ChildItem -Path tests -Filter 'test_forensic*.py' | ForEach-Object { $_.FullName }; python -m pytest $files -q
```

Result: `135 passed, 111 subtests passed`.

Frontend AstroClock/forensic helper batch:

```powershell
npm --prefix frontend run test:ui -- src/tests/astroclockApi.test.mjs src/tests/forensicReplayAxes.test.mjs src/tests/forensicRelationshipLink.test.mjs src/tests/forensicSurvivalSignal.test.mjs src/tests/astroClockModeFlow.test.jsx src/tests/astroClockAspectData.test.mjs
```

Result: `6 passed`, `66 tests passed`. The snap preload timeout stack trace is emitted by an expected passing test.
