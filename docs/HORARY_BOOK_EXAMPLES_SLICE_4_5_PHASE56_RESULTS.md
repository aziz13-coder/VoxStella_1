# Horary Book Examples Slice 4/5 Phase 5/6 Results

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Replay fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`

Focused rule tests:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_lost_contest_rules.py`

## Scope

This pass implemented the grounded doctrine fixes for the remaining rule-level disagreement classes from:

- Lost & Found
- Contests / public-event questions

The goal was not to flip isolated chart answers. The goal was to correct the underlying routing and judgment logic so the same rules can apply to other charts of the same kind.

## Grounded Rule Changes

### 1. Lost-object questions now stay lost-object questions

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\lost_object_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

What changed:

- genuine recovery/location questions are now protected from being swallowed by generic money or education keywords
- documents and cards are still judged as lost objects, with Mercury as a natural witness, instead of being diverted into travel or exam logic
- a missing document is no longer denied simply because there is no event-style perfection
- Moon void of course is no longer an absolute lost-object denial by itself

Why this is rule-level rather than chart-level:

- traditional lost-object questions are about recovery, concealment, and place-description
- Moon VOC can delay or weaken recovery, but it is not by itself a universal proof that the item is permanently lost
- the condition of the object significator still matters: combustion or very severe affliction can justify denial, but moderate obscurity like under-beams should not automatically overturn recoverability

### 2. Public-office contests now use office/incumbent logic

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\competition_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

What changed:

- explicit public-office contests now route through `1/10` instead of generic `1/7`
- the office-holder or the office itself is treated as the stronger pole in the 10th
- no-perfection office contests can now resolve through an office/incumbent balance test instead of falling back to generic opponent logic

Why this is rule-level rather than chart-level:

- the question is not merely “will X beat another person”
- it is “will X take the office,” which requires the office and its present holder to be treated differently from an ordinary opponent

### 3. Champion-versus-challenger charts now preserve title-holder asymmetry

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\competition_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

What changed:

- reigning champions/title holders now route as `10th`
- challengers now route as `4th`
- the reigning holder receives an incumbent/title advantage in the no-perfection balance

Why this is rule-level rather than chart-level:

- a title-defense question is not symmetric
- the reigning holder is not just “another person”; he stands in the position of the king or established possessor of the title

## Output Summary

Before this pass:

- cumulative replay cases: `30`
- source-aligned: `22`
- explicit disagreements: `8`

After this pass:

- cumulative replay cases: `30`
- source-aligned: `27`
- explicit disagreements: `3`

Resolved in this pass:

- `where_is_my_atm_card`
- `where_is_my_scarf`
- `wheres_my_passport`
- `will_romney_win_the_us_presidency`
- `will_the_champion_retain_his_belt`

Still deferred:

- `will_we_rent_the_house`
- `will_grandfather_survive_this_time`
- `will_barrett_win`

## Why The Remaining Three Stay Deferred

### `will_we_rent_the_house`

This is no longer a simple routing failure. It looks like a deeper chained-state property question involving ownership transfer or post-sale status. That needs a reusable doctrine model, not another narrow tweak.

### `will_grandfather_survive_this_time`

The remaining issue is not ordinary death routing. It is a kinship-derivation ambiguity. The title alone does not reliably encode the maternal branch, so a safe fix requires a broader turned-kinship rule rather than guessing from one example.

### `will_barrett_win`

The remaining issue is contextual identification. The bare title does not explicitly say “governor,” “office,” or “election,” so the analyzer cannot safely infer a public-office contest from text alone without risking false positives in other contest questions.

## What This Protects

These fixes were made in shared rule layers and therefore protect:

- the backend replay corpus
- frontend verdict parity
- shared horary routing and significator selection
- Astro Clock consumers that depend on the same question-analysis and chart utilities

## Verification Targets

Backend:

- `tests\test_horary_book_examples_replay.py`
- `tests\test_horary_book_lost_contest_rules.py`

Frontend:

- `frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `frontend\src\tests\astroclockApi.test.mjs`
