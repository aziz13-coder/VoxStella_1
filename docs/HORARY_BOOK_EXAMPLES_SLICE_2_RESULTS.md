# Horary Book Examples Slice 2 Results

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Replay fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`

## Scope

This second replay slice extends the book corpus beyond the first `Money & Jobs` and `Housing` batch.

Families added here:

- Relationship
- Pregnancy & Children

Implemented case ids:

- `will_the_relationship_last`
- `any_chance_of_a_romance_with_x`
- `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her`
- `will_i_find_a_new_relationship_and_when`
- `will_i_conceive`
- `will_they_put_the_baby_up_for_adoption`
- `am_i_pregnant`
- `any_chance_of_having_my_own_child`

## Output Summary

Second-slice totals after the rule-fix pass:

- replay cases added: `8`
- source-aligned: `8`
- explicit disagreements: `0`

Cumulative book replay totals:

- total replay cases: `18`
- source-aligned: `17`
- explicit disagreements: `1`

The only remaining book disagreement in the whole replay corpus is still:

- `will_we_rent_the_house`

## Root Fixes Implemented For This Slice

### 1. Relationship durability doctrine

Added a dedicated durability branch so questions like `Will the Relationship Last?` are no longer forced through bare occurrence/no-perfection logic.

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\relationship_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

This now judges continuity by:

- condition of the quesited
- Moon strength and sign stability
- limited reception support
- whether the next lunar testimony shows strain

### 2. Relationship timing vs lost-object keyword capture

The analyzer no longer misroutes `Will I find a new relationship and when?` to `lost_object` just because of the generic verb `find`.

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`

### 3. Pregnancy diagnosis doctrine

`Am I Pregnant?` is now treated as a present-state diagnosis, not a future-occurrence chart.

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\pregnancy_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

The core doctrinal correction is:

- an applying L1/L5 aspect in a diagnosis chart can mean the bond lies ahead, therefore `NO` for current pregnancy
- a separating connection would support `YES`

### 4. Pregnancy conception sufficiency

`Will I Conceive?` no longer falls straight through to strict no-perfection denial when the Moon is immediately moving to the child significator in fertile signs.

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\pregnancy_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

### 5. Someone-else's-child adoption routing

`Will They Put the Baby Up for Adoption?` is now routed as a children/adoption question through the parents and their child, not as a pregnancy chart.

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\children_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

## Aligned Cases In This Slice

### `any_chance_of_a_romance_with_x`

- Book result: `YES`, but harmful and short-lived
- Current engine: `YES`
- Route: relationship, `L1/L7`

This is a useful anchor because it shows the engine can still allow a relationship chart to perfect while carrying penalties and warnings.

### `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her`

- Book result: `NO`
- Current engine: `NO`
- Route: relationship, `L1/L7`

The engine and the book agree that the relationship is not favorable, though the book reaches that answer by richer feeling-state analysis than the engine currently exposes.

### `any_chance_of_having_my_own_child`

- Book result: `NO` to the biological-child part of the question
- Current engine: `NO`
- Route: children / `L1/L5`

This is an important pregnancy-family anchor because the current engine now keeps first-person fertility language on `L1/L5` instead of falsely turning it into a third-person child question. That restores the real frustration pattern: the Moon as child-significator is preempted by Saturn before union with Mars.

## Result

The second slice no longer has any explicit disagreement cases.

The five disagreement classes identified in the harness-only pass are now resolved by rule-level changes:

1. relationship durability vs relationship occurrence
2. relationship timing routing vs lost-object keyword capture
3. pregnancy sufficiency vs strict no-perfection denial
4. present-state pregnancy diagnosis
5. someone-else's-child / adoption turned-house routing

## Safety Boundary For The Next Fix Pass

Any change made from this slice must still be checked against shared consumers:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs`

This slice now includes both the replay harness and the corresponding rule-level fixes.
