# Horary Book Examples Slice 5 Results

Follow-up:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_4_5_PHASE56_RESULTS.md`

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Replay fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`

## Scope

This slice extends the replay corpus into the next planned family:

- Contests / public-event questions

Implemented case ids:

- `will_barrett_win`
- `will_romney_win_the_us_presidency`
- `will_the_champion_retain_his_belt`

## Output Summary

Slice-5 totals at the harness stage:

- replay cases added: `3`
- source-aligned: `0`
- explicit disagreements: `3`

## Disagreement Classes Isolated

### 1. Public-office contests collapse to generic 1/7 charts

Cases:

- `will_barrett_win`
- `will_romney_win_the_us_presidency`

Current engine:

- category: `general`
- houses: `1/7`
- verdict: historically correct `NO`, but by the wrong route

Why this matters:

- the book treats elections with incumbents as office/king contests, not generic other-person charts
- so even when the engine lands on the historical result, it is not using the correct public-office structure

### 2. Champion vs challenger asymmetry is missing

Case:

- `will_the_champion_retain_his_belt`

Current engine:

- category: `general`
- houses: `1/7`
- verdict: `NO`

Book direction:

- reigning champion: `10th`
- challenger: `4th`
- result: `YES`

Why this matters:

- the champion/title-holder asymmetry is a reusable contest rule, not a one-chart exception
- without it, the engine misreads title-defense charts and can reverse the verdict

## Result

This slice is now ready for a contest/public-event doctrine pass.

The next fix pass should target:

- incumbent-versus-challenger routing for elections and office contests
- champion/king versus challenger routing for title-defense questions
- post-event result handling where the vote or contest is already complete and the chart asks who has won
