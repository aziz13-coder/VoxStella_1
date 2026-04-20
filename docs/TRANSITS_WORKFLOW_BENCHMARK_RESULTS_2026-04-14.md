# Transits Workflow Benchmark Results
Date: 2026-04-14

## Scope

This memo records the first runtime baseline for:

- exact vs window consistency
- predictor stability across step sizes
- documented Morin hindcast cases

## Result Summary

### Exact vs Window Consistency

- cases: `2`
- passes: `2/2`
- pass rate: `100%`

Observed baseline:

- the matching scan row preserved the exact-analysis top transit family overlap
- prediction-family overlap was also strong in both seed cases

This is a workflow consistency result, not a predictive result.

### Predictor Stability

- cases: `2`
- passes: `2/2`
- pass rate: `100%`

Observed baseline:

- the expected family remained present at the same rank across `180m` and `60m` scans
- dominant timestamps did not drift in the seed cases

This is a stability result, not a truth-validation result.

### Documented Hindcasts

- cases: `2`
- passes: `2/2`
- pass rate: `100%`

Case detail:

- `Doctorate 1613`
  - pass
  - expected `honors/public_recognition` family found at rank `1`
  - dominant timestamp was `39h` away from the target window
- `Near-drowning 1615`
  - pass
  - expected `danger/accident_major` family found at rank `1`
  - dominant timestamp landed inside the target window

## Interpretation

The new transits workflow harness supports three defensible claims:

1. exact analysis and window scan are materially consistent in the seed cases
2. predictor output is stable across the tested step sizes in the seed cases
3. documented hindcast ranking now matches both seeded Morin examples

That still does not justify a broad predictive claim. It means the current row-ranking and predictor-window logic are no longer contradicting the two seeded Morin examples.

## Next Useful Move

The next benchmark improvement should not be more tuning on these same two examples.

It should be:

1. expand documented hindcast cases beyond Morin’s two canonical examples
2. add a stricter timestamp-distance tolerance tier
3. keep the crisis-ranking and dominant-window behavior pinned while the hindcast set grows
