# Forensic Deception Rule Coverage - 2026-04-03

## Scope
- Added explicit tests for the deception-focused forensic rule set.
- Goal: move deception logic out of indirect replay-only coverage and into direct rule-ID assertions.

## Test File Added
- `tests/test_forensic_deception_rules.py`

## Explicit Rule Coverage Added
- `mercury_neptune_aspect`
- `mercury_retrograde`
- `mercury_combust`
- `mercury_combust_applying`
- `mercury_in_12th`
- `mercury_in_mute_sign`
- `neptune_personal_planets`
- `neptune_in_7th_or_12th`
- `neptune_angular_strong`
- `mars_neptune_opposition`
- `mars_neptune_square`
- `venus_saturn_hard`
- `venus_detriment_with_saturn`
- `twelfth_house_emphasis_deception`
- `seventh_ruler_in_12th`
- `sun_or_moon_in_12th`
- `mute_signs_on_angles`
- `mute_signs_on_3rd_or_9th`
- `north_node_in_8th`
- `saturn_neptune_coverup`
- `node_with_neptune_or_mercury`
- `north_node_in_4th`
- `truth_jupiter_mercury_easy`

## Validation Commands
- `python -m pytest -q tests/test_forensic_deception_rules.py`
- `python -m pytest -q tests/test_forensic*.py`

## Result
- Deception-focused rule test file:
  - `8 passed`
- Full forensic suite at the time of this expansion:
  - later superseded by broader coverage expansion; see `FORENSIC_RULE_COVERAGE_EXPANSION_2026-04-03.md`

## What This Improves
- Directly verifies the live rule IDs loaded from `backend/forensic/knowledge/deception_rules.yaml`
- Confirms rule firing through the actual `extract_features -> evaluate` path
- Reduces risk of silent regression in deception keyword/rule behavior

## Remaining Gaps
- Broader rule-list and scoring gaps were addressed in the follow-up expansion documented in `FORENSIC_RULE_COVERAGE_EXPANSION_2026-04-03.md`.
