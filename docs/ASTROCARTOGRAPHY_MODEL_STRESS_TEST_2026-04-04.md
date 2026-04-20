# Astrocartography Model Stress Test

Date: 2026-04-04

## Goal

This pass stress-tested the PathFinder model logic rather than the UI or request workflow.

The objective was to answer:

- do the current goals behave distinctly under themed scenarios
- do specialist variants collapse into their broad parent models
- are there obvious model overlaps that should be reduced before further expansion

## Implemented

Added a repeatable model stress-test harness:

- [astrocartography_model_stress.py](/Users/sabaa/Downloads/codexhorary/backend/astrocartography_model_stress.py)
- [stress_test_astrocartography_models.py](/Users/sabaa/Downloads/codexhorary/scripts/stress_test_astrocartography_models.py)
- [test_astrocartography_model_stress.py](/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_model_stress.py)

The suite now runs `20` themed scenarios across `17` runtime goals and checks:

- expected winners are surfaced
- extreme model overlap is limited
- broad and specialist variants are not near-duplicates

## Source support

The stress-test scenarios are synthetic, but the model semantics they probe still depend on the same source-backed reference layer:

- [02_planetary_and_angular_reference.md](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md)
- [03_techniques_and_ranges.md](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_knowledge_base/reference/03_techniques_and_ranges.md)

The books helped indirectly by giving the cleaned planetary/angle meaning layer. The raw converted book text was not used directly for the stress harness.

## Findings

### Good

- No expectation failures in the current `20` scenario suite.
- The intended goal family surfaces correctly in every scenario.
- `beliefs` and `sex` remain source-backed after their recent rework and now survive explicit scenario tests.
- The new broad-vs-specialist model system is materially better separated than before.
- The expanded suite now exercises more edge boundaries between adjacent families instead of only checking obvious winner cases.

### What had to be fixed

The first expansion run exposed several problems:

- `secure_salary` was too prestige-heavy and behaved more like a public-career case than a stable-income case
- `craft_execution` was too status-facing and let public-profile logic outrank ordinary disciplined work
- `conflict` still overread some hard-work signatures as hostility because it treated general pressure houses too broadly
- `work` vs `career`
- `career` vs `career_public_profile`
- `education` vs `beliefs`
- `home` vs `home_retreat`

Those were tightened by reworking the source builder and the stress scenarios:

- `work` now emphasizes reliable throughput, craft, Mercury/Saturn structure, and `6th`-house style output more than prestige
- `career` now emphasizes advancement, authority, and institutional lift more than public-profile glare
- `home` now emphasizes livability, continuity, and community more than contemplative retreat
- `home_retreat` now leans more clearly into contemplative sanctuary and inward tone
- `education` now emphasizes structured learning, study mobility, and disciplined skill-building more than meaning/pilgrimage language
- `beliefs` now emphasizes worldview, contemplation, `9th/12th`-house tone, and guarded Neptune usage more than pure academic study
- `conflict` now means exposed rivalry and antagonism rather than generic hard work under pressure

## Current results

Final stress-run top winners:

- `study_expansion` -> `education`
- `warm_partnership` -> `love`
- `public_career` -> `career_public_profile`
- `stable_income` -> `money`
- `home_sanctuary` -> `home`
- `transformative_growth` -> `personal_growth`
- `communications_network` -> `communication`
- `chemistry_heat` -> `sex`
- `conflict_hot` -> `conflict`
- `contemplative_beliefs` -> `beliefs`
- `formal_alliance` -> `partners`
- `social_circle` -> `friends`
- `secure_salary` -> `money_stable_income`
- `craft_execution` -> `work`
- `retreat_contemplation` -> `home_retreat`
- `authority_ladder` -> `career`
- `public_teaching` -> `education`
- `rooted_commitment` -> `love_commitment`
- `volatile_reinvention` -> `personal_growth`

Remaining high-overlap pairs above `0.92` cosine are:

- `work` <-> `career`: `0.943`
- `career` <-> `career_public_profile`: `0.936`
- `money` <-> `money_stable_income`: `0.931`

The important change is that `education <-> beliefs` is no longer in the high-overlap list, and the worst remaining pairs are now all genuinely adjacent families.

## Interpretation

This is the correct shape for the current model layer:

- broad families should still correlate with their specialist variants
- but they should not be functionally identical

The suite now shows:

- acceptable differentiation
- no outright logical collapse
- remaining overlap mostly where semantic families are genuinely adjacent
- broader coverage of relationship, income, public-teaching, retreat, and reinvention cases

## Files changed

- [astrocartography_model_stress.py](/Users/sabaa/Downloads/codexhorary/backend/astrocartography_model_stress.py)
- [test_astrocartography_model_stress.py](/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_model_stress.py)
- [stress_test_astrocartography_models.py](/Users/sabaa/Downloads/codexhorary/scripts/stress_test_astrocartography_models.py)
- [build_astrocartography_goal_models.py](/Users/sabaa/Downloads/codexhorary/scripts/build_astrocartography_goal_models.py)
- [astrocartography_goal_engine.py](/Users/sabaa/Downloads/codexhorary/backend/astrocartography_goal_engine.py)
- [place_goal_models.runtime.json](/Users/sabaa/Downloads/codexhorary/backend/knowledge/astrocartography/place_goal_models.runtime.json)

## Verification

Passed:

- `python scripts/stress_test_astrocartography_models.py`
- `python -m pytest backend/test_astrocartography_model_stress.py backend/test_astrocartography_goal_engine.py`
- `python -m pytest backend/test_astrocartography_model_stress.py backend/test_astrocartography_goal_engine.py backend/test_astrocartography_atlas_engine.py backend/test_astrocartography_service.py`
- `python -m py_compile backend/astrocartography_model_stress.py scripts/stress_test_astrocartography_models.py scripts/build_astrocartography_goal_models.py`

## Next useful step

If we want to push model rigor further, the best next move is not more labels. It is another scenario-and-model pass on the three remaining close families:

- tighten `work` vs `career`
- tighten `career` vs `career_public_profile`
- tighten `money` vs `money_stable_income`
- add more direct comparisons against legacy Almagest outputs when available
