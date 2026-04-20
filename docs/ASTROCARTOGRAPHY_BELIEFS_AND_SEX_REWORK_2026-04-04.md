# Astrocartography Beliefs And Sex Rework

Date: 2026-04-04

## Why this pass happened

In the earlier model audit, `beliefs` and `sex` were correctly called out as the least mature PathFinder goals. They were usable, but they leaned more heavily on inferred synthesis than the stronger model families.

This pass tightens those two models so they are more explicitly backed by the repo's astrocartography source layer.

## Source grounding used

Primary source layer:

- [02_planetary_and_angular_reference.md](/Users/sabaa/Downloads/codexhorary/horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md)

Most relevant corpus anchors:

- `Jupiter`: growth, opportunity, meaning, teaching, luck
- `Mercury`: language, trade, learning, writing, networking, teaching
- `Sun`: identity, vitality, purpose, recognition
- `Neptune`: spirituality, imagination, inspiration, but also confusion, glamour, escapism
- `Venus`: love, beauty, harmony, attraction, ease
- `Mars`: action, heat, courage, boldness, conflict risk
- `Pluto`: intensity, power, regeneration, obsession/control risk
- `Moon`: emotion, belonging, care, receptivity
- `Saturn`: discipline and endurance, but also heaviness, isolation, delay

Legacy anchors:

- `BELIEFS.HYP`
- `SEX.HYP`

## What changed

### Beliefs

The `beliefs` model is now narrower and more defensible:

- stronger emphasis on `Jupiter`, `Mercury`, and `Sun`
- `Neptune` kept, but softened and constrained instead of treated as a broad positive
- explicit caution for `Mercury/Neptune` blur and excessive instability
- added metric-based constraints so drift does not rank as spiritual depth

### Sex

The `sex` model is now less naive:

- still centered on `Venus`, `Mars`, and `Pluto`
- keeps `Moon` as a softer receptivity layer
- preserves `Saturn` as cooling/inhibiting caution
- adds stronger instability and pressure controls so chaotic harshness does not simply score as intensity
- uses explicit caps when malefic pressure gets too high

## Files changed

- [build_astrocartography_goal_models.py](/Users/sabaa/Downloads/codexhorary/scripts/build_astrocartography_goal_models.py)
- [place_goal_models.runtime.json](/Users/sabaa/Downloads/codexhorary/backend/knowledge/astrocartography/place_goal_models.runtime.json)
- [test_astrocartography_goal_engine.py](/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_goal_engine.py)

## Important boundary

These models are now better source-backed than before, but they are still Vox Stella models, not exact recovered legacy formulas.
