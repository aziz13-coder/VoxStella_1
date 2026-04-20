# Horary Book Examples Slice 3 Phase 5/6 Results

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Harness note:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_3_HEALTH_RESULTS.md`

Rule tests:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_health_rules.py`

## Scope

This phase 5/6 pass implemented rule-level fixes for the health / death-edge replay slice.

Target disagreement classes from the harness pass:

- mother-health turned-house / illness-progression routing
- medical diagnosis routed as generic occurrence
- pet recovery / survival doctrine
- maternal-grandfather death derivation

## Root Fixes Implemented

### 1. Health-specific routing and doctrine classification

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\health_doctrine.py`

What changed:

- medical wording like `tumor`, `multiple sclerosis`, `diagnosis`, and `inflammation` now routes to `Category.HEALTH`
- third-person health questions now derive the subject and illness houses correctly
- diagnosis and progression questions are separated into dedicated health families

### 2. Mother-health progression branch

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\health_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

What changed:

- `Will Mum's Tumor Stop Growing?` no longer falls through to a generic `1/7` occurrence chart
- the engine now judges it as a turned-house mother-health progression question
- the current replay resolves to `YES`, aligned with the book's stabilization judgment

### 3. Medical diagnosis branch

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\health_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

What changed:

- `Is It Multiple Sclerosis?` is now treated as a present-state diagnosis chart
- the engine keeps the `NO` verdict, but now reaches it by health-diagnosis logic and `1/6` routing rather than generic `1/7` occurrence logic

### 4. Pet recovery and survival branch

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\pet_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

What changed:

- pet recovery wording like `get better` and `survive` now forces the chart into the recovery/survival family
- the engine now evaluates pet safety and Moon testimony as a balance, instead of demanding direct perfection for survival questions
- a bug in the hard-aspect check between `L6` and `L8` was also corrected to compare real aspect enums rather than strings

### 5. Grandfather survival boundary improved but not fully closed

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`

What changed:

- `Will Grandfather Survive This Time?` now routes as a death-edge chart instead of an ordinary parent chart
- the replay now reaches the correct `YES` verdict and the correct `death` category

What remains:

- the engine still derives the grandfather via `4/11`
- the book chapter explicitly uses maternal-grandfather context to return to radical `1/8`
- that extra relational context is not present in the bare chart title alone, so the route mismatch is still tracked explicitly instead of being forced

## Output Summary

Slice 3 after the rule-fix pass:

- replay cases in slice: `6`
- source-aligned: `5`
- explicit disagreements: `1`

Cumulative replay totals after the health pass:

- total replay cases: `24`
- source-aligned: `22`
- explicit disagreements: `2`

Remaining disagreement ids:

- `will_we_rent_the_house`
- `will_grandfather_survive_this_time`

## Safety Check

The fixes were verified against:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_health_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs`

No Astro Clock-specific logic was changed in this pass, but the shared frontend parity path was still rerun because the replay corpus and displayed backend verdicts are part of the same regression boundary.
