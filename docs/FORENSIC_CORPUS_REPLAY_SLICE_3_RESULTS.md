# Forensic Corpus Replay Slice 3 Results

## Scope

Third real replay pass through the actual `/api/astro-clock/forensic` route using the five fresh source-backed cases in [FORENSIC_CORPUS_REPLAY_SLICE_3.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_3.md).

Machine-readable output:

- [forensic_case_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3_results.json)

## Route-Level Result

- `5/5` cases returned `200`
- `5/5` returned `success: true`

So the current forensic route can process the third replay slice end to end.

## Directional Comparison Result

- `5` aligned
- `0` partially aligned
- `0` misaligned

## What Slice 3 Was Meant To Test

Slice 1 and slice 2 already established that the route and grounded homicide-direction rules were functional on the earlier family, domestic, and public murder sets.

Slice 3 was the first deliberate pressure test against:

- spouse-linked homicide not already present in slice 1 or 2
- parental / celebrity homicide with weaker 8th-house emphasis
- child-victim homicide with disputed public narrative
- aviation disaster
- maritime disaster

The key question was whether the route could generalize beyond homicide-only framing without collapsing disasters into family, child, domestic, or abduction false positives.

## Initial Failure Pattern And Smallest Responsible Fix

The first replay pass exposed a coherent rule-layer problem rather than an Astro Clock request-context problem:

- `ronnie_lee_bakley` was under-signaled for partner-linked homicide
- `marvin_gaye` was under-signaled for family/public homicide
- `air_france_447` and `costa_concordia` were picking up broad family/child/domestic/abduction language because those rules were too permissive
- `costa_concordia` also exposed misleading `domestic` wording in a deception rule title

The smallest responsible fix was to stay in the forensic knowledge layer:

- tighten over-broad direction rules
- add missing partner-homicide, parental/public-homicide, and disaster rules
- remove misleading `domestic` wording from the staged-location deception title

The detailed rule changes are documented in:

- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md)

No shared Astro Clock request plumbing or chart projection changes were needed for this slice.

## Aligned Cases

- `ronnie_lee_bakley`
  - matched:
    - `domestic_partner_involvement`
    - `violence_homicide`

- `marvin_gaye`
  - matched:
    - `family_involvement`
    - `violence_homicide`
    - `authority_or_public_case`

- `alice_crimmins`
  - matched:
    - `family_involvement`
    - `child_victim`
    - `violence_homicide`

- `air_france_447`
  - matched:
    - `accident_or_disaster`
    - `water_disappearance_or_drowning`

- `costa_concordia`
  - matched:
    - `accident_or_disaster`
    - `water_disappearance_or_drowning`

## What Slice 3 Now Shows

The current grounded direction layer now generalizes across both homicide and disaster cases without requiring a shared Astro Clock context fix.

It now handles:

- partner-linked homicide
- parental / celebrity homicide
- child-victim family homicide
- air-disaster direction
- maritime-disaster direction

## Residual Noise Worth Watching

`air_france_447` still emits a lower-priority associate finding:

- `Friend or close associate axis is active`

That did not contradict the slice labels and was therefore not promoted into another fix in this pass. It is a good candidate for slice-4 monitoring if more travel/disaster cases show the same noise.

## Root-Level Interpretation

Slice 3 still does not point to an Astro Clock request-context or shared chart-projection problem.

The route works and the improvement again came from the forensic knowledge layer itself:

- grounded direction rules in [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- deception wording cleanup in [deception_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/deception_rules.yaml)

## Files Added Or Updated For Slice 3

- [forensic_case_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3.json)
- [forensic_case_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3_results.json)
- [run_forensic_case_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_3.py)
- [test_forensic_case_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_3.py)
- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md)

## Verification

- `python -m pytest tests\test_forensic_direction_rules.py tests\test_forensic_case_replay_slice_3.py -q`
- `python scripts\run_forensic_case_replay_slice_3.py`
- `python -m pytest tests\test_forensic_case_corpus.py tests\test_forensic_case_replay_slice_1.py tests\test_forensic_case_replay_slice_2.py tests\test_forensic_case_replay_slice_3.py tests\test_forensic_direction_rules.py tests\test_forensic_features.py tests\test_forensic_route_contract.py tests\test_astroclock_adapter_fixes.py tests\test_astroclock_chart_bundle_helpers.py tests\test_astroclock_internal_chart_passthrough.py -q`
