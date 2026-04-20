# Forensic Corpus Replay Slice 4 Results

## Scope

Fourth real replay pass through the actual `/api/astro-clock/forensic` route using the three public cases defined in [FORENSIC_CORPUS_REPLAY_SLICE_4.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_4.md).

Machine-readable output:

- [forensic_case_replay_slice_4_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_4_results.json)

## Route-Level Result

- `3/3` cases returned `200`
- `3/3` returned `success: true`

## Directional Comparison Result

- `3` aligned
- `0` partially aligned
- `0` misaligned

## Initial Failure Pattern And Smallest Responsible Fix

The first slice-4 probe exposed one concrete problem:

- `sam_sheppard` was being pulled into `domestic_partner_involvement` by `domestic_partner_near_home_axis` even though the local source explicitly argues that the chart does not support spouse guilt

This was a rule-layer issue, not an Astro Clock context issue. The smallest responsible fix was to tighten the domestic-home rule so it now requires relational stress markers instead of letting home-axis overlap alone imply spouse involvement.

The detailed rule note is in:

- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_4.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_4.md)

No shared Astro Clock request plumbing or chart projection changes were needed.

## Aligned Cases

- `sam_sheppard`
  - matched:
    - `violence_homicide`
    - `friend_or_close_associate`
  - avoided:
    - `domestic_partner_involvement`

- `diane_downs`
  - matched:
    - `family_involvement`
    - `child_victim`
    - `violence_homicide`

- `marilyn_monroe_murder`
  - matched:
    - `violence_homicide`
    - `deception_coverup`

## Deferred Public Cases

Two public cases were evaluated during slice-4 triage but not promoted into executable replay assertions:

- `charles_whitman`
  - the available local metadata remained approximate, and the live route did not produce a stable enough directional fit to justify a source change

- `haiti_earthquake`
  - the current directional-axis model still lacks a non-speculative earthquake/natural-disaster rule set, so this remains a documented holdback rather than a forced assertion

## What Slice 4 Now Shows

The current grounded direction layer can keep working on the remaining public-case pool without over-correcting the spouse axis in cold cases.

It now explicitly handles:

- known-associate homicide without forcing a spouse read
- mother/child homicide with deception pressure
- suspicious public death with homicide plus cover-up emphasis

## Verification

- `python -m pytest tests\\test_forensic_direction_rules.py tests\\test_forensic_case_replay_slice_4.py -q`
- `python scripts\\run_forensic_case_replay_slice_4.py`
- `python -m pytest tests\\test_forensic_case_corpus.py tests\\test_forensic_case_replay_slice_1.py tests\\test_forensic_case_replay_slice_2.py tests\\test_forensic_case_replay_slice_3.py tests\\test_forensic_case_replay_slice_4.py tests\\test_forensic_direction_rules.py tests\\test_forensic_features.py tests\\test_forensic_route_contract.py tests\\test_astroclock_adapter_fixes.py tests\\test_astroclock_chart_bundle_helpers.py tests\\test_astroclock_internal_chart_passthrough.py -q`
