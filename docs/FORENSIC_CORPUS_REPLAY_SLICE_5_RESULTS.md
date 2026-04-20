# Forensic Corpus Replay Slice 5 Results

## Scope

Fifth real replay pass through the actual `/api/astro-clock/forensic` route using the two deferred disaster cases defined in [FORENSIC_CORPUS_REPLAY_SLICE_5.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_5.md).

Machine-readable output:

- [forensic_case_replay_slice_5_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_5_results.json)

## Route-Level Result

- `2/2` cases returned `200`
- `2/2` returned `success: true`

## Directional Comparison Result

- `2` aligned
- `0` partially aligned
- `0` misaligned

## Initial Failure Pattern And Smallest Responsible Fix

The initial holdback was not an Astro Clock request-context issue.

The live route already had the correct charts, but the direction layer lacked two narrow disaster reads:

- a take-off / aviation-disaster pattern for `twa_flight_800`
- a structural catastrophe / earth-disaster pattern for `haiti_earthquake`

The smallest responsible fix stayed in the forensic knowledge layer:

- add one narrow air-disaster launch rule
- add one narrow structural catastrophe rule

No shared Astro Clock request plumbing, chart projection, or feature-extraction contract changes were needed.

The detailed rule note is in:

- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_5.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_5.md)

## Aligned Cases

- `twa_flight_800`
  - matched:
    - `accident_or_disaster`
  - route signal:
    - `Air-disaster launch pattern is active`

- `haiti_earthquake`
  - matched:
    - `accident_or_disaster`
  - route signal:
    - `Structural catastrophe pattern is active`

## Residual Noise Worth Watching

`haiti_earthquake` still emits:

- `Friend or close associate axis is active`

That is the same kind of low-priority disaster noise already seen earlier in `air_france_447`. It does not contradict the slice labels, so it was documented rather than promoted into another rule change in this pass.

## What Slice 5 Now Shows

The current grounded direction layer can now classify the two remaining source-backed disaster holdbacks without changing shared Astro Clock plumbing.

It now explicitly handles:

- an aviation-disaster launch chart with a source-matched Aquarian take-off signature
- a large-scale structural / earth-disaster chart with Capricorn saturation and cazimi stress

## Remaining Holdback

`charles_whitman` remains deferred.

The local source support for the mother-killing chart is real, but the live route still does not produce a stable enough public-violence / family-homicide direction to justify a source change in this pass.

## Verification

- `python -m pytest tests\\test_forensic_direction_rules.py tests\\test_forensic_case_replay_slice_5.py -q`
- `python scripts\\run_forensic_case_replay_slice_5.py`
- `python -m pytest tests\\test_forensic_case_corpus.py tests\\test_forensic_case_replay_slice_1.py tests\\test_forensic_case_replay_slice_2.py tests\\test_forensic_case_replay_slice_3.py tests\\test_forensic_case_replay_slice_4.py tests\\test_forensic_case_replay_slice_5.py tests\\test_forensic_direction_rules.py tests\\test_forensic_features.py tests\\test_forensic_route_contract.py tests\\test_astroclock_adapter_fixes.py tests\\test_astroclock_chart_bundle_helpers.py tests\\test_astroclock_internal_chart_passthrough.py -q`
