# Weather Runtime Graduation Decision

Status date: 2026-04-13

## Decision

No benchmark-only weather family graduates into runtime in this pass.

The live runtime remains:

1. `flood_risk`
2. `hurricane_pressure`
3. `severe_convective_pressure`
4. `wind_event_pressure`

## Families Reviewed But Deferred

Deferred:

1. `snow / freezing precipitation`
2. `temperature extremes`
3. `drought`

## Why Deferred

The benchmark branch is broader than the live runtime, but that alone is not enough.

Graduation stays blocked because:

1. the current four families still needed narrowing work
2. severe convective still has a live control-window separation problem
3. wind still has one unresolved failure after the current pass
4. adding more runtime families now would widen maintenance before the current seed engine is stable enough

## Current Standard

A benchmark family should not graduate into runtime unless all are true:

1. doctrine is operational enough for analysis output
2. scan behavior is coherent enough to expose place/time windows without heavy caveats
3. predictive or family-shape benchmark behavior is strong enough to justify maintenance
4. the family does not just duplicate a live runtime family

## Revisit Order

The next graduation review should happen only after:

1. severe convective is revisited against its remaining control-window failure
2. the remaining wind failure is inspected and either improved or formally accepted as a limit

Only then should:

1. `snow / freezing precipitation`
2. `temperature extremes`
3. `drought`

be reconsidered for runtime promotion.
