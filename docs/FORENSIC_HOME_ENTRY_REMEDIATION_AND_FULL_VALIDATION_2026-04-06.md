# Forensic Home-Entry Remediation And Full Validation

## Scope

This pass fixed the remaining `Homicide` season drift on **Lourdes Gonzalez** and then reran the broader forensic validation matrix.

The fix was required to stay:

1. general rather than case-specific
2. backed by the local forensic corpus
3. safe against the existing journalist-abduction and disaster replay packs

## Root Cause

The Lourdes case was drifting because three broad shortcuts were interacting badly:

1. `domestic_partner_known_spouse_homicide` treated `7th ruler in 6th` as acceptable spouse testimony.
2. `domestic_partner_axis_contact` allowed a hard-afflicted 4th ruler to stand in for a concrete domestic/home link.
3. `abduction_deceptive_public_or_assignment_seizure_signature` allowed `mute_signs_on_angles` to stand in for Mercury-based deception.

That combination let a stranger-at-home case slide into:

- `Domestic`
- `Abduction`
- `Public`

instead of holding a clearer violence-plus-deception read.

## Source Basis

The remediation was grounded in the local corpus, not in the Lourdes case alone.

Primary source files used:

- `extracted_text_docs/text_forensics/Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve… (Caroline J. Luley) (Z-Library).txt`
- `extracted_text_docs/text_forensics/Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt`
- `extracted_text_docs/text_forensics/Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt`

Relevant source-backed principles:

1. `4th house` = home, residence, current location, family/home axis.
2. `7th house` = attacker, abductor, stranger, or the other person.
3. `6th house` = servants, repairmen, domestic workers, work/service intermediaries, misfortune.
4. A bare `6th` testimony should not be collapsed into spouse/partner logic.
5. Mercury-linked deception is stronger support for assignment/public seizure than generic mute-sign symbolism.

## Implemented Fixes

### 1. Tightened spouse/partner logic

File:

- [backend/forensic/knowledge/directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)

Changes:

- `domestic_partner_known_spouse_homicide`
  - removed `houses.seventh_ruler_house: [6, 8, 12]`
  - now only accepts `7th ruler` in `8` or `12`, or direct Mercury/Saturn or Moon/Venus partner stress
- `domestic_partner_axis_contact`
  - removed `houses.fourth_ruler_hard_afflicted: true` from the domestic-link branch

Why:

- `7th ruler in 6th` is source-backed as work/service/servant/repairman territory, not spouse by itself.
- a hard-hit 4th ruler alone is too broad to justify partner language in stranger-at-home charts.

### 2. Tightened deceptive public-assignment seizure logic

File:

- [backend/forensic/knowledge/directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)

Changes:

- `abduction_deceptive_public_or_assignment_seizure_signature`
  - removed `houses.mute_signs_on_angles: true` from the deception branch

Why:

- the rule rationale is Mercury-based deception under public/professional or assignment exposure
- mute-sign noise alone was too broad and was falsely promoting non-assignment stranger-home charts into `Abduction`

### 3. Added a general home-entry / service-pretext violence rule

File:

- [backend/forensic/knowledge/directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)

New rule:

- `violence_home_entry_service_pretext_pattern`

Rule intent:

- home axis tied to attacker/stranger axis
- explicit 6th/7th service-entry or service-intermediary structure
- separate violence or death pressure

Why:

- this is the general missing pattern for stranger-at-home violence or deceptive-entry cases
- it fits the source meanings of `4th`, `6th`, and `7th` without hardcoding any single replay case

### 4. Narrowed the new rule after regression testing

During the full replay rerun, the first version of the new rule falsely tagged the Haiti earthquake as violence.

Cause:

- the rule initially allowed `6th ruler in 8th` to stand in for the service/pretext link by itself

Fix:

- removed `houses.sixth_ruler_house: 8` from the middle service-entry branch
- kept it only as supporting violence/death pressure

Why:

- `6th ruler -> 8th` can describe misfortune, service-linked damage, or crisis, but it is not enough by itself to prove stranger-entry or service-pretext violence

## Engine Output Vs. Real Events After Fix

### Lourdes Gonzalez

Anchor kept:

- `1989-06-14 19:00`
- `East 97th Street, Manhattan, New York, USA`

Real event summary:

- stranger home invasion
- adult female homicide victim
- children in another room

Current engine categories:

- `Deception: 3`
- `Degree Signatures: 1`
- `Violence: 1`

Leading findings:

- `violence_home_entry_service_pretext_pattern`
- `venus_saturn_hard`
- `node_with_neptune_or_mercury`
- `mute_signs_on_angles`

Assessment:

- materially better aligned
- no longer forced into spouse/partner language at the strongest evening anchor
- still directional, because the timing source is lower-confidence than the court-backed replay anchors in the stronger packs

### Haiti Earthquake regression check

Anchor:

- `2010-01-12 16:58`
- `Haiti`

Current engine categories after the guard:

- `Associates: 1`
- `Deception: 3`
- `Disaster: 1`
- `Headwinds: 1`

Important result:

- the false `Violence` signal from `violence_home_entry_service_pretext_pattern` is gone
- the disaster replay is back to directional alignment

## Tests Added / Updated

Updated tests:

- [tests/test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)
- [tests/test_forensic_drift_guards.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_drift_guards.py)
- [tests/fixtures/forensic_external_homicide_season3_cases.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_homicide_season3_cases.json)
- [docs/HOMICIDE_SEASON3_CASE_LIST_AND_PROBES_2026-04-06.md](C:/Users/sabaa/Downloads/codexhorary/docs/HOMICIDE_SEASON3_CASE_LIST_AND_PROBES_2026-04-06.md)

New assertions added:

1. positive synthetic coverage for `violence_home_entry_service_pretext_pattern`
2. negative guard ensuring home-entry/service-pretext charts do not fire partner rules
3. negative guard ensuring deceptive public-assignment seizure does not fire from mute-sign noise alone
4. negative guard ensuring disaster charts with `4th -> 7th` and `6th -> 8th` do not trip the home-entry violence rule

## Full Validation Rerun

### Broad forensic replay / slice / journalist matrix

Executed:

```powershell
$files = Get-ChildItem tests -Filter 'test_forensic*.py' | ForEach-Object { $_.FullName }
python -m pytest -q $files
```

Result:

- `120 passed`
- `52 subtests passed`
- `1 warning`

Coverage included:

- forensic replay slices
- journalist abduction benchmark
- journalist holdout probes
- abduction map benchmark / holdouts
- season homicide probes
- Joey documentary probe
- route contract and rule packs

### Adapter / geocoding support checks

Executed:

```powershell
python -m pytest -q tests/test_astroclock_adapter_fixes.py backend/test_astro_clock_dashboard_geocoding.py
```

Result:

- `7 passed`
- `1 warning`

### Frontend forensic UI tests

Executed:

```powershell
npm run test:ui -- src/tests/forensicAbductionMap.test.mjs src/tests/forensicReplayAxes.test.mjs src/tests/astroclockApi.test.mjs
```

Result:

- `3 files passed`
- `23 tests passed`

## Current Status

1. Lourdes is no longer the unresolved season failure.
2. The season pack now has:
   - Joey Comunale: partial strongest-anchor alignment
   - Irene Silverman: aligned
   - Sylvie Cachay: aligned
   - Lourdes Gonzalez: aligned at strongest evening anchor
3. The original resolved journalist benchmark remains green.
4. The journalist holdout set remains green.
5. The disaster slices remain green after the guard on the new home-entry rule.

## Remaining Known Warning

- external `pytz` deprecation warning only
- no current forensic assertion failures remain in the rerun matrix
