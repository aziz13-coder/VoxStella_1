# Forensic Corpus Replay Slice 2 Results

## Scope

Second real replay pass through the actual `/api/astro-clock/forensic` route using the eight source-backed cases in [FORENSIC_CORPUS_REPLAY_SLICE_2.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_2.md).

Machine-readable output:

- [forensic_case_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2_results.json)

## Route-Level Result

- `8/8` cases returned `200`
- `8/8` returned `success: true`

So the current forensic route can process the second replay slice end to end.

## Directional Comparison Result

- `8` aligned
- `0` partially aligned
- `0` misaligned

## What Slice 2 Was Meant To Test

Slice 1 already showed that the first grounded directional-rule pass worked on a small core set.

Slice 2 was the first real generalization check. It deliberately moved into:

- filicide
- parricide
- familicide
- close-associate homicide
- celebrity / public homicide

The question was not whether the route worked. It was whether the same grounded direction families still pointed the feature in the right direction without another round of tuning.

## Aligned Cases

- `andrea_yates`
  - matched:
    - `family_involvement`
    - `child_victim`
    - `violence_homicide`

- `darlie_routier`
  - matched:
    - `family_involvement`
    - `child_victim`
    - `violence_homicide`

- `lizzie_borden`
  - matched:
    - `family_involvement`
    - `violence_homicide`

- `menendez_brothers`
  - matched:
    - `family_involvement`
    - `violence_homicide`
    - `accomplice_or_witness`

- `john_list`
  - matched:
    - `family_involvement`
    - `violence_homicide`
    - `deception_coverup`

- `amityville_defeo`
  - matched:
    - `family_involvement`
    - `violence_homicide`

- `bob_crane`
  - matched:
    - `friend_or_close_associate`
    - `violence_homicide`

- `gianni_versace`
  - matched:
    - `violence_homicide`
    - `authority_or_public_case`

## What Slice 2 Shows

The first grounded rule pass was not overfit to slice 1, and the follow-up rule pass on slice 2 stayed grounded at the feature/house-pattern layer.

It now generalizes well on:

- family / child / domestic-homicide direction
- broad homicide / violence direction
- deception / concealment in family-killing cases
- accomplice / witness participation
- friend / close-associate direction
- public / celebrity / authority emphasis

## Root-Level Interpretation

This replay pass still does not point to an Astro Clock request-context problem.

The route works and the feature remains directionally useful. The improvements in this pass came from the forensic rule/feature layer itself:

- richer shared feature synthesis in [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py)
- grounded directional rules in [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)

That means shared Astro Clock request plumbing still does not look like the limiting factor for this slice.

## Files Added For Slice 2

- [forensic_case_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2.json)
- [forensic_case_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2_results.json)
- [run_forensic_case_replay_slice_2.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_2.py)
- [test_forensic_case_replay_slice_2.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_2.py)
- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-23.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-23.md)

## Verification

- `python -m unittest tests.test_forensic_case_replay_slice_2 -v`
- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary:/mnt/c/Users/sabaa/Downloads/codexhorary/backend backend/venv/bin/python - <<'"'"'PY'"'"'\nimport runpy\nrunpy.run_path(\"scripts/run_forensic_case_replay_slice_1.py\", run_name=\"__main__\")\nrunpy.run_path(\"scripts/run_forensic_case_replay_slice_2.py\", run_name=\"__main__\")\nPY'`

## Next Safe Step

Move to a fresh replay slice before changing the rule layer again.

Slice 2 is now aligned, so the next useful pressure test is whether the current grounded direction families generalize to new forensic cases instead of being tuned further against the same eight.
