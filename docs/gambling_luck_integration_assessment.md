# Gambling Luck Astrocartography Curation

## Scope

This note documents the implemented change that adapts the legacy gambling logic described in `C:\Users\sabaa\Downloads\Gambling_Reverse_Engineering.md` into a **natal-relocation astrocartography scorer** for PathFinder.

The goal here is not to reproduce the original election engine minute-for-minute. The goal is to make `gambling_luck` rank places using the same core logic family:

- gambler / querent -> Ascendant and Ascendant ruler
- gambling matter / quesited -> 5th house and 5th ruler
- flow and traction -> Moon condition
- drag and blockage -> retrograde, Moon void, hard ruler conflict, malefic pressure

## What Changed

### 1. `gambling_luck` is no longer a money-placeholder profile

Changed file:

- [backend/knowledge/astrocartography/place_goal_models.runtime.json](</C:/Users/sabaa/Downloads/codexhorary/backend/knowledge/astrocartography/place_goal_models.runtime.json:3711>)

Current model state:

- `evaluation_strategy` is now `gambling_natal_curated`
- `transit_strategy` is now `ignore`
- model metadata now describes a natal-relocation gambling scorer rather than a benchmark-aligned money inheritance
- the documented score components now reflect curated gambling metrics instead of the old money-family `visibility` placeholder set

### 2. Relocation feature extraction now reads the chart state the gambling model actually needs

Changed file:

- [backend/astrocartography_goal_engine.py](</C:/Users/sabaa/Downloads/codexhorary/backend/astrocartography_goal_engine.py:123>)

The extractor now uses relocation chart fields that were already present in the app payload but previously ignored:

- `house_rulers`
- `aspects`
- `considerations.moon_void`
- `moon_next_aspect`
- planet `retrograde`
- planet `dignity_score`
- planet `solar_condition`

New relocation metrics added:

- `asc_ruler_strength`
- `gambling_ruler_strength`
- `asc_gambling_harmony`
- `asc_gambling_tension`
- `moon_gambling_support`
- `moon_liability`
- `retrograde_liability`
- `money_support`

The extractor also now returns lightweight gambling details:

- `asc_ruler`
- `gambling_ruler`
- `moon_void`

### 3. A dedicated heuristic scorer now powers the goal

Changed file:

- [backend/astrocartography_goal_engine.py](</C:/Users/sabaa/Downloads/codexhorary/backend/astrocartography_goal_engine.py:696>)

The new `evaluate_gambling_natal_curated_heuristic(...)` does three things:

1. Scores natal angular lines and crossings with a gambling-specific bias.
2. Scores relocation metrics built from Asc-ruler, 5th-ruler, and Moon logic.
3. Penalizes liabilities that matter for gambling specifically instead of treating the goal like generic money.

## Rule Mapping Used

The legacy reverse-engineering note says the original product heavily rewards harmony between:

- the querent ruler
- the quesited ruler
- the Moon
- the Ascendant

and heavily penalizes:

- Moon void-of-course
- retrogradation and weakness
- obstructive ruler conflict
- malefic pressure

For astrocartography, that was mapped as follows.

### Querent axis

- `1st house ruler` = native / gambler
- score from relocated house placement, angularity, dignity, combustion, and retrograde state

### Gambling axis

- `5th house ruler` = main gambling significator
- score from relocated house placement, dignity, combustion, and retrograde state

### Querent vs gambling relationship

- support if Asc ruler and 5th ruler are the same planet
- support for trine, sextile, conjunction
- penalty for square, opposition
- small bonus if the rulers occupy each other's relevant houses

### Moon logic

- support if Moon is in 1st, 2nd, 5th, or 11th
- support if Moon's next aspect helps the Asc ruler, 5th ruler, Venus, or Jupiter
- penalty for Moon VOC
- penalty for hostile Moon next aspects
- penalty for Moon in 8th or 12th

### Secondary bankroll layer

- `2nd`, `8th`, and `11th` house rulers are treated as secondary support only
- this keeps the model tied to gambling rather than collapsing back into a generic money score

## Files Changed

- [backend/astrocartography_goal_engine.py](</C:/Users/sabaa/Downloads/codexhorary/backend/astrocartography_goal_engine.py:1>)
- [backend/knowledge/astrocartography/place_goal_models.runtime.json](</C:/Users/sabaa/Downloads/codexhorary/backend/knowledge/astrocartography/place_goal_models.runtime.json:3711>)
- [backend/test_astrocartography_goal_engine.py](</C:/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_goal_engine.py:1>)

## Tests Added And Updated

Changed file:

- [backend/test_astrocartography_goal_engine.py](</C:/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_goal_engine.py:1>)

Coverage now includes:

- curated gambling metrics appearing in relocation extraction
- Moon VOC and retrograde liabilities
- `gambling_luck` asserting curated metric contributions instead of `visibility`/`benefic_balance`
- favorable gambling relocations outranking broken Moon-and-ruler cases

## What This Still Does Not Do

This remains an astrocartography place model, not the original timing engine.

Still not implemented here:

- minute-by-minute election logic
- exact daily calendar scoring
- intercepted Ascendant logic
- full dynamic applying/separating timing windows across changing charts

If those are needed later, that should be a separate election-engine task.

## Result

The repo now has a defensible astrocartography-specific answer to the gambling logic request:

- `gambling_luck` is distinct from `money`
- it uses curated natal-relocation ruler logic
- it applies to place ranking in PathFinder, not election timing
