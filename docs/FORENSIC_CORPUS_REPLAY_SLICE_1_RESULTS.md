# Forensic Corpus Replay Slice 1 Results

## Scope

First real replay pass through the actual `/api/astro-clock/forensic` route using the six source-backed cases in [FORENSIC_CORPUS_REPLAY_SLICE_1.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_1.md).

Machine-readable output:

- [forensic_case_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_1_results.json)

## Route-Level Result

- `6/6` cases returned `200`
- `6/6` returned `success: true`

So the current forensic route can process the first replay slice end to end.

## Directional Comparison Result

- `6` aligned
- `0` partially aligned
- `0` misaligned

## What Changed Since The First Replay Baseline

- The route itself was already operational.
- The main gap was the knowledge layer and feature vocabulary, not Astro Clock request plumbing.
- The next safe step added grounded directional context for:
  - violence / homicide
  - domestic / partner involvement
  - family involvement
  - child-victim emphasis
  - water / drowning direction
  - abduction / missing-person patterns
- The feature extractor was expanded so those rules could rely on reusable structural signals instead of case-specific phrasing.
- The replay comparison helper was also tightened so negated language inside rationales does not create a false contradiction.

## Aligned Cases

- `lindbergh_kidnapping`
  - matched:
    - `abduction_missing_person`
    - `child_victim`
    - `violence_homicide`

- `phil_hartman`
  - matched:
    - `violence_homicide`
    - `domestic_partner_involvement`

- `natalie_wood`
  - matched:
    - `water_disappearance_or_drowning`
    - `violence_homicide`

- `scott_peterson`
  - matched:
    - `deception_coverup`
    - `domestic_partner_involvement`
    - `violence_homicide`

- `jonbenet_ramsey`
  - matched:
    - `child_victim`
    - `family_involvement`
    - `violence_homicide`

- `susan_smith`
  - matched:
    - `family_involvement`
    - `child_victim`
    - `deception_coverup`
    - `violence_homicide`

## What The First Replay Pass Shows

The current forensic feature is now directionally viable on the first replay slice.

It is now better at:

- deception / concealment
- family and domestic relationship direction
- child-victim emphasis
- homicide / violence direction
- water / drowning direction
- abduction direction

## Root-Level Interpretation

This replay pass still does not point to a request-context bug.

The route works, returns findings, and processes all six cases. The improved outcome came from:

- broader feature extraction for victim/partner/family/child/water context
- grounded directional rules in the forensic knowledge layer
- a tighter replay comparison harness that avoids false contradiction from negated rationale text

The feature still remains a directional overlay, not a final forensic verdict engine, so future work should keep evaluating emphasis and narrative drift rather than assuming the current six-case slice is sufficient.

## Files Changed For This Improvement Pass

- [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py)
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- [forensic_case_corpus_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/forensic_case_corpus_utils.py)
- [inspect_forensic_case_replay.py](C:/Users/sabaa/Downloads/codexhorary/scripts/inspect_forensic_case_replay.py)
- [test_forensic_case_corpus.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_corpus.py)
- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)

## Verification

- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary backend/venv/bin/python scripts/run_forensic_case_replay_slice_1.py >/dev/null'`
- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary backend/venv/bin/python -m unittest tests.test_forensic_case_corpus tests.test_forensic_case_replay_slice_1 tests.test_forensic_direction_rules tests.test_forensic_route_contract tests.test_forensic_features -v'`

## Next Safe Step

Move to replay slice 2 before changing the rule layer again. The first slice is now aligned, so the next useful pressure test is whether these same grounded directions generalize to a fresh set of cases instead of overfitting the current six.
