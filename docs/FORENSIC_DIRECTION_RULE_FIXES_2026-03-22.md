# Forensic Direction Rule Fixes 2026-03-22

## Scope

This pass implemented the first grounded directional-rule expansion for the forensic feature and re-ran the first replay slice through the real `/api/astro-clock/forensic` route.

The goal was not to patch individual famous cases. It was to improve the reusable directional layer so the feature can express:

- violence / homicide
- domestic / partner involvement
- family involvement
- child-victim emphasis
- water / drowning direction
- abduction / missing-person direction

## Rule-Layer Changes

### Feature extraction

[features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py) now exposes additional reusable context, including:

- water-sign and water-house synthesis
- angular malefic counts
- richer ruler context for the 4th, 5th, 7th, and 10th
- first/7th ruler interaction
- Moon house/sign/water/malefic-pressure flags
- Neptune hidden-house / water context
- house occupancy counts and cusp-sign synthesis

These are shared structural signals, not case-specific overrides.

### Knowledge rules

[directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml) now provides grounded directional findings for:

- `Violence`
- `Domestic`
- `Family`
- `Children`
- `Water`
- `Abduction`

These rules are based on combinations of reusable conditions such as:

- life/death ruler overlap
- hidden/end houses
- Moon under hard malefic pressure
- activated 1st/7th axis
- pressured 4th/5th houses
- water emphasis and Neptune

## Evaluation-Harness Fix

[forensic_case_corpus_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/forensic_case_corpus_utils.py) now treats contradictory-axis detection more strictly than ordinary matching:

- primary-axis matching still uses titles, categories, and rationales
- contradictory-axis detection now uses only explicit titles and categories

This prevents false contradictions caused by negated rationale text such as "more than a simple accident."

## Test Coverage Added

- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)
  - synthetic rule-level coverage for violence/abduction/child overlap
  - domestic/family partner-axis pressure
  - water disappearance signatures

- [test_forensic_case_corpus.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_corpus.py)
  - added regression coverage for negated contradiction wording

The replay inspector was also improved in [inspect_forensic_case_replay.py](C:/Users/sabaa/Downloads/codexhorary/scripts/inspect_forensic_case_replay.py) so case-by-case feature probes can show finding ids and selected feature paths.

## Replay Result

The first replay slice is now fully aligned:

- `6/6` returned `200`
- `6/6` aligned
- `0` partially aligned
- `0` misaligned

Current machine-readable result:

- [forensic_case_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_1_results.json)

Result summary:

- [FORENSIC_CORPUS_REPLAY_SLICE_1_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_1_RESULTS.md)

## Verification

- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary backend/venv/bin/python scripts/run_forensic_case_replay_slice_1.py >/dev/null'`
- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary backend/venv/bin/python -m unittest tests.test_forensic_case_corpus tests.test_forensic_case_replay_slice_1 tests.test_forensic_direction_rules tests.test_forensic_route_contract tests.test_forensic_features -v'`

## Next Safe Step

Do not keep tuning slice 1. Move to replay slice 2 and test whether these same grounded rules generalize to fresh cases.
