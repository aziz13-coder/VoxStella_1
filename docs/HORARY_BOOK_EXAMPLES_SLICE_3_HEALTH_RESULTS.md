# Horary Book Examples Slice 3 Results

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Replay fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`

## Scope

This third replay slice extends the book corpus into the next planned family:

- Health
- Death-edge survival questions

Implemented case ids:

- `will_dad_die_soon_if_so_when`
- `will_mums_tumor_stop_growing`
- `will_i_die_soon`
- `is_it_multiple_sclerosis`
- `will_my_dog_get_better_will_it_survive`
- `will_grandfather_survive_this_time`

## Output Summary

Third-slice totals at the harness stage:

- replay cases added: `6`
- source-aligned: `2`
- explicit disagreements: `4`

Cumulative book replay totals:

- total replay cases: `24`
- source-aligned: `19`
- explicit disagreements: `5`

Current explicit disagreement ids in the harness-stage full replay corpus:

- `will_we_rent_the_house`
- `will_mums_tumor_stop_growing`
- `is_it_multiple_sclerosis`
- `will_my_dog_get_better_will_it_survive`
- `will_grandfather_survive_this_time`

## Aligned Cases In This Slice

### `will_dad_die_soon_if_so_when`

- Book result: `NO`
- Current engine: `NO`
- Route: death, derived from the father (`4th`) and the father's death (`11th`)

This is a strong alignment anchor because the engine already uses the father's turned death house rather than collapsing the question into a generic 1st/8th chart.

### `will_i_die_soon`

- Book result: `NO`
- Current engine: `NO`
- Route: death, `L1/L8`

This is another useful anchor because it shows the engine can already keep a straight death-timing question on the proper 1st/8th route and deny the event without forcing a speculative yes/no flip.

## Disagreement Classes Isolated

### 1. Mother-health turned-house and body-localization routing

Case:

- `will_mums_tumor_stop_growing`

Current engine:

- category: `general`
- houses: `1/7`
- verdict: `NO`

Book direction:

- category: health
- route: turned-house mother chart
- result: stabilizes / does not worsen dangerously

Root issue isolated:

- the engine does not yet have a mother-health progression branch that keeps both the mother and her illness on the correct turned houses

### 2. Medical diagnosis routed as generic occurrence

Case:

- `is_it_multiple_sclerosis`

Current engine:

- category: `general`
- houses: `1/7`
- verdict: `NO`

Book direction:

- category: health
- family: present-state diagnosis
- result: `NO`, but by diagnosis logic rather than generic occurrence failure

Root issue isolated:

- the engine reaches the right verdict but by the wrong route, so it still needs a diagnosis-specific doctrine path

### 3. Pet recovery and survival doctrine

Case:

- `will_my_dog_get_better_will_it_survive`

Current engine:

- category: `pet`
- houses: `1/6`
- verdict: `NO`

Book direction:

- category: pet
- route: `1/6`
- result: `YES`, with limited recovery and short-term improvement

Root issue isolated:

- the engine keeps the pet route but still falls back to strict no-perfection denial instead of a recovery/survival balance

### 4. Maternal-grandfather death derivation

Case:

- `will_grandfather_survive_this_time`

Current engine:

- category: `parent`
- houses: `1/4`
- verdict: `NO`

Book direction:

- category: death
- route: maternal-grandfather derivation leading into a survival/death judgment
- result: `YES`

Root issue isolated:

- the engine is stopping at a plain parent route instead of deriving the relative fully and then judging the death question from there

## Result

The third slice harness isolated the health / death-edge disagreement classes and fed directly into the later phase 5/6 pass.

What is now pinned safely:

- the current engine observations for all six health/death cases
- which cases are already aligned
- which cases disagree only on route
- which cases disagree on both route and verdict

What is intentionally not done yet in this harness note:

- no health or death logic had been changed from this slice alone
- no chart-specific patch has been introduced

## Safety Boundary For The Next Fix Pass

Any phase 5/6 fix coming from this slice must still be checked against shared consumers:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs`

The next planned expansion after the health/death fix pass remains:

- Lost & Found
- Contests / public-event questions
