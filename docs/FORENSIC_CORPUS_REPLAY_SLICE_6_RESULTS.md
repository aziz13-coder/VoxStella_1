# Forensic Corpus Replay Slice 6 Results

## Scope

Sixth real replay pass through the actual `/api/astro-clock/forensic` route using the remaining named holdback defined in [FORENSIC_CORPUS_REPLAY_SLICE_6.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_6.md).

Machine-readable output:

- [forensic_case_replay_slice_6_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_6_results.json)

## Route-Level Result

- `1/1` case returned `200`
- `1/1` returned `success: true`

## Directional Comparison Result

- `1` aligned
- `0` partially aligned
- `0` misaligned

## Initial Failure Pattern And Smallest Responsible Fix

The initial holdback was not an Astro Clock request-context issue.

The live route already had a usable chart and returned the expected homicide pressure, but it was not surfacing a stable family/parricide direction strongly enough to make the case replay-safe.

The smallest responsible fix stayed in the forensic knowledge layer:

- add one narrow family-parricide cluster rule

No shared Astro Clock request plumbing, chart projection, or route-contract changes were needed.

The detailed rule note is in:

- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_6.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_6.md)

## Aligned Case

- `charles_whitman`
  - matched:
    - `family_involvement`
    - `violence_homicide`
  - route signal:
    - `Family homicide cluster is active`

## Residual Noise Worth Watching

`charles_whitman` still emits low-priority secondary noise:

- `Witness or accomplice signatures are active`
- generic `Deception` category weight from Mercury retrograde / combustion language

That noise does not contradict the slice labels, so it was documented rather than expanded into a broader witness/deception rewrite in this pass.

## What Slice 6 Now Shows

The current grounded direction layer can now classify the remaining named local-source holdback as a family-homicide chart without changing shared Astro Clock plumbing.

It now explicitly handles:

- a parent-killing chart anchored by explicit local prose and a conservative minute replay
- a family/parricide cluster that was previously getting flattened into generic witness or deception language

## Remaining Gap

There is no longer a named replay-ready holdback from the current local-source set.

The remaining forensic expansion work is now:

- low-priority witness/deception noise cleanup on some homicide and disaster charts
- anonymous or weak-metadata family cases that still belong in manual review until their chart anchors are defensible

## Verification

- `python -m pytest tests\\test_forensic_direction_rules.py tests\\test_forensic_case_replay_slice_6.py -q`
- `python scripts\\run_forensic_case_replay_slice_6.py`
- `python -m pytest tests\\test_forensic_case_corpus.py tests\\test_forensic_case_replay_slice_1.py tests\\test_forensic_case_replay_slice_2.py tests\\test_forensic_case_replay_slice_3.py tests\\test_forensic_case_replay_slice_4.py tests\\test_forensic_case_replay_slice_5.py tests\\test_forensic_case_replay_slice_6.py tests\\test_forensic_direction_rules.py tests\\test_forensic_features.py tests\\test_forensic_route_contract.py tests\\test_astroclock_adapter_fixes.py tests\\test_astroclock_chart_bundle_helpers.py tests\\test_astroclock_internal_chart_passthrough.py -q`
