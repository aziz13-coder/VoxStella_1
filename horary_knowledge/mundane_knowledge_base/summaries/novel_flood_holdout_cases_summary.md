# Novel Flood Holdout Cases Summary

Status date: 2026-04-19

This summary records the first flood holdout cases added to the predictive hindcast weather benchmark.

The purpose is not to expand the doctrine corpus. The purpose is to test whether the existing flood runtime can concentrate pressure around real historical flood events that were not part of the source-backed seed set.

## Included Holdouts

### Eastern Kentucky Flooding, Hindman, July 2022

- Origin: `novel_holdout`
- Runtime family: `flood_risk`
- Benchmark family: `floods`
- Verification basis:
  - NWS Jackson event archive for the July 26-30, 2022 flood
  - NWS service assessment for the July 2022 southeastern Kentucky flood disaster
- Selected scan framing:
  - benchmark window `2022-07-25T00:00:00` to `2022-07-31T18:00:00`
  - target window `2022-07-28T00:00:00` to `2022-07-29T18:00:00`

### Great Vermont Flood, Montpelier, July 2023

- Origin: `novel_holdout`
- Runtime family: `flood_risk`
- Benchmark family: `floods`
- Verification basis:
  - NWS July 2023 northeast flash flood and river flooding service assessment
  - NWS Burlington flood safety archive referencing the Great Vermont Flood of July 2023
- Selected scan framing:
  - benchmark window `2023-07-08T00:00:00` to `2023-07-14T18:00:00`
  - target window `2023-07-10T00:00:00` to `2023-07-11T18:00:00`

## Benchmark Use

- These cases should remain in the predictive hindcast dataset, not the doctrine or historical source-backed datasets.
- They should be reported separately from `source_backed` cases so the benchmark can distinguish in-corpus fit from out-of-source generalization.
