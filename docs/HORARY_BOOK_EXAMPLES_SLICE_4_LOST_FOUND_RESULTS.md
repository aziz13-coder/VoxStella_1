# Horary Book Examples Slice 4 Results

Follow-up:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_4_5_PHASE56_RESULTS.md`

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Replay fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`

## Scope

This slice extends the replay corpus into the next planned family:

- Lost & Found

Implemented case ids:

- `where_is_my_atm_card`
- `where_is_my_scarf`
- `wheres_my_passport`

## Output Summary

Slice-4 totals at the harness stage:

- replay cases added: `3`
- source-aligned: `0`
- explicit disagreements: `3`

The disagreements are intentional at this stage. They isolate the current routing problem cleanly:

- the engine still collapses some lost-object charts into `money`
- one chart is even misrouted into `education`
- the book examples judge by object location and recovery conditions rather than generic perfection/no-perfection logic

## Disagreement Classes Isolated

### 1. Lost object vs generic money routing

Cases:

- `where_is_my_atm_card`
- `where_is_my_scarf`

Current engine:

- category: `money`
- houses: `1/2`

Why this matters:

- the houses are partly usable, but the engine still treats the question as a financial event chart rather than a recovery/location chart
- that means it is not exposing the kind of place-description testimony the book examples rely on

### 2. Lost document vs education/travel routing

Case:

- `wheres_my_passport`

Current engine:

- category: `education`
- houses: `1/10/9`

Why this matters:

- the engine is being pulled into exam/travel-success logic because of passport/abroad language
- the book example is still a lost-document question, with the passport itself as the key significator

## Result

This slice is now ready for a dedicated lost-object doctrine pass.

The next fix pass should target:

- lost-object category protection against money/education keyword pollution
- location/discovery logic instead of simple event likelihood
- theft-vs-misplacement branching where another person or employee is explicitly involved
