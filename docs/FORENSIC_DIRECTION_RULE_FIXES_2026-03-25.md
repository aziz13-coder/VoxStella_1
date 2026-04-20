# Forensic Direction Rule Fixes 2026-03-25

## Why This Pass Happened

Fresh replay slice 3 exposed a coherent feature-layer issue:

- broad family / child / domestic / abduction rules were firing on disaster charts
- partner-linked homicide and parental/public homicide needed stronger explicit rule coverage
- one deception title leaked `domestic` wording into a maritime-disaster case

This pass stayed in the forensic knowledge layer and did not change Astro Clock request plumbing or shared chart serialization.

## Rules Tightened

In [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml):

- `violence_moon_under_death_pressure`
  - now requires stronger death-context support before a hard-contact Moon alone becomes homicide language

- `domestic_partner_axis_contact`
  - now requires a clearer home-axis anchor so travel/disaster charts do not read as domestic-partner cases

- `family_home_axis_under_pressure`
  - no longer fires from a bare occupied 4th house plus stress

- `child_house_under_stress`
  - no longer fires from a single 5th-house activation plus generic stress

- `abduction_missing_person_signature`
  - no longer fires from a weak 3rd/4th/12th cue plus generic child pressure

## Rules Added

In [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml):

- `domestic_partner_known_spouse_homicide`
  - catches spouse-linked homicide cases like `ronnie_lee_bakley`

- `family_parental_axis_homicide`
  - catches parental/public homicide cases like `marvin_gaye`

- `public_axis_saturated`
  - restores public / celebrity emphasis where 10th-house saturation is the stable signal

- `travel_accident_or_disaster_pattern`
  - introduces a direct accident/disaster path for travel charts like `air_france_447`

- `waterborne_accident_or_disaster_pattern`
  - introduces a direct maritime-disaster path for charts like `costa_concordia`

## Deception Wording Cleanup

In [deception_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/deception_rules.yaml):

- `north_node_in_4th`
  - title changed from `domestic deception` to `staged-location deception`
  - rationale changed to remove family/domestic wording

This was a vocabulary fix, not a scoring change.

## Mirrors Updated

The same knowledge changes were mirrored into the packaged-app source tree:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/forensic/knowledge/directional_context_rules.yaml)
- [deception_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/forensic/knowledge/deception_rules.yaml)

## Safety Coverage Added

- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)
  - added partner-homicide, parental/public-homicide, travel-disaster, and waterborne-disaster cases
  - added false-positive guards so family/child/domestic/abduction rules do not re-expand into disaster charts

- [test_forensic_case_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_3.py)
  - now runs the live `/api/astro-clock/forensic` route and asserts directional alignment for the full slice-3 corpus
