# Astrocartography Advanced Models Implementation

Date: 2026-04-04

## Scope

This memo documents the model findings from the Astrocartography audit and the source-backed implementation changes made in this slice.

Implemented in this pass:

- restored the goal-model builder in source
- added the missing legacy-family models:
  - `personal_growth`
  - `communication`
  - `conflict`
- added specialist submodels:
  - `love_commitment`
  - `money_stable_income`
  - `career_public_profile`
  - `home_retreat`
- added an advanced `constraint` component to the goal grammar
- extended relocation metrics to support the new families
- regenerated the runtime goal-model asset

## Source Findings

### What helped

The Astrocartography books were useful, but the useful layer was not the raw PDF text dump. The strongest support came from the normalized knowledge-base references:

- [02_planetary_and_angular_reference.md](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md)
- [03_techniques_and_ranges.md](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_knowledge_base/reference/03_techniques_and_ranges.md)
- [05_feature_notes.md](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md)

These references were clean enough to support model semantics:

- `Mercury` for language, trade, learning, writing, messaging
- `Venus` and `Moon` for relationship warmth, harmony, care, belonging
- `Mars` for action, heat, confrontation, irritation
- `Jupiter` for growth, opportunity, teaching, expansion
- `Saturn` for discipline, structure, endurance, heaviness
- `Uranus` for reinvention, disruption, freedom, instability
- `Pluto` for intensity, control, transformation
- `Sun` for identity, visibility, recognition, purpose
- `IC / DSC / MC / ASC` angle-domain meanings
- `300 km / 500 km` reading-radius policy already used elsewhere in the feature

### What did not help directly

The raw converted book text under [astrocartography_books_text](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_books_text) is still too noisy for direct runtime scoring work. It remains useful for research, but not as a direct model-definition layer.

### Legacy source alignment

The legacy Almagest family still matters for product parity. The new models were aligned to the recovered hidden-file families where they existed:

- `PERSONAL.HYP`
- `CHATTER.HYP`
- `ENEMIES.HYP`
- `LOVE.HYP`
- `PARTNERS.HYP`
- `MONEY.HYP`
- `WORK.HYP`
- `CAREER.HYP`
- `HOME.HYP`

These were treated as semantic anchors, not exact recovered formulas.

## Implementation Findings

### 1. The previous grammar was too shallow

Before this pass, goal models could only express:

- `line`
- `crossing`
- `relocation`
- `modifier`

That was enough for broad goals, but not enough for specialist models. For example:

- stable income should be penalized when instability is high
- public-profile career should be capped when visibility is too low
- commitment-oriented love should not rank highly if partnership support is absent

### 2. Constraint logic is the right next layer

The new `constraint` component solves that without turning the engine into a black box.

Supported behaviors:

- additive penalty or bonus: `add`
- multiplier on the current subtotal: `multiplier`
- hard cap on the current subtotal: `cap_score`

Constraint evaluation is metric-driven and explainable. It runs only when a named relocation metric crosses a threshold.

### 3. More models is useful only if the grammar improves too

This pass did not just add labels. It added specialist models with stronger internal logic:

- `love_commitment` is not just `love` with more Venus. It explicitly rewards `stability` and penalizes `uncertainty`.
- `money_stable_income` is not just `money`. It rewards `stability` and punishes `uncertainty` and `malefic_pressure`.
- `career_public_profile` is not just `career`. It depends materially on `visibility`.
- `home_retreat` is not just `home`. It depends on `domesticity`, `home_base`, and low instability.

## New Relocation Metrics

The relocation feature extractor now exposes:

- `personal_growth`
- `communication`
- `conflict_pressure`

These sit alongside the older metrics:

- `visibility`
- `partnership`
- `domesticity`
- `mobility`
- `uncertainty`
- `stability`
- `benefic_balance`
- `malefic_pressure`
- `community`
- `beliefs`
- `chemistry`
- `career_status`
- `home_base`

## New Models

Added broad legacy-family models:

- `personal_growth`
- `communication`
- `conflict`

Added specialist models:

- `love_commitment`
- `money_stable_income`
- `career_public_profile`
- `home_retreat`

Total runtime model count is now `17`.

## Files Changed

- [build_astrocartography_goal_models.py](/Users/sabaa/Downloads/codexhorary/scripts/build_astrocartography_goal_models.py)
- [astrocartography_goal_engine.py](/Users/sabaa/Downloads/codexhorary/backend/astrocartography_goal_engine.py)
- [place_goal_model.schema.json](/Users/sabaa/Downloads/codexhorary/backend/knowledge/astrocartography/place_goal_model.schema.json)
- [place_goal_models.runtime.json](/Users/sabaa/Downloads/codexhorary/backend/knowledge/astrocartography/place_goal_models.runtime.json)
- [test_astrocartography_goal_engine.py](/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_goal_engine.py)

## Verification

Passed:

- `python scripts/build_astrocartography_goal_models.py`
- `python -m py_compile scripts/build_astrocartography_goal_models.py backend/astrocartography_goal_engine.py backend/astrocartography_goal_models.py`
- `python -m pytest backend/test_astrocartography_goal_engine.py`
- `python -m pytest backend/test_astrocartography_atlas_engine.py backend/test_astrocartography_service.py backend/test_astro_clock_api_astrocartography.py`

## Current Boundary

The model layer is stronger now, but one boundary remains honest:

- these are source-backed Vox Stella models
- they are not exact recovered Almagest formulas

That is still the correct product position unless more direct legacy-formula evidence appears.
