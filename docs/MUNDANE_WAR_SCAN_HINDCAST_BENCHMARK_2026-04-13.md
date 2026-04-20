# Mundane War Scan Hindcast Benchmark

## Purpose

This suite tests the current mundane scan runtime against a small set of known war events and campaign windows.

It is intentionally narrower than the main mundane benchmark corpus:

- chart type: `war_event`
- domains:
  - `war_outbreak`
  - `campaign_escalation`
- output under test:
  - scan place-series localization
  - scan time-window concentration
  - control-window discrimination

It does **not** claim validated prospective war prediction.

## What It Measures

Each hindcast case runs a real scan and evaluates:

1. whether the expected target place survives into `series.places`
2. the target place rank inside the aggregated place-series output
3. whether the target window carries one of the stronger scores inside the matched place series
4. how far the selected peak sits from the target window
5. whether the target window beats matched non-event control windows

## Why This Exists

The existing mundane scan benchmarks answer operational questions:

- does the expected place survive into returned cells
- does the series payload have the expected shape

They do not answer the harder question:

- when we scan around a real war event, does the runtime recover the relevant theater and concentrate pressure in the event window better than nearby control windows

This suite fills that gap.

## Scope Limits

This benchmark is still a hindcast, not a true blind forecast test.

The current suite is limited to `war_event` because:

- local doctrine is strongest there for opening hostilities
- runtime policy already treats `war_outbreak` as chart-type-specific
- framework charts like `aries_ingress`, `lunation`, and `eclipse` are doctrinally narrower and should not be scored as if they were event-anchor outbreak scans

## Dataset Shape

Each JSONL row in `backend/benchmarks/mundane/war_scan_hindcast_cases.jsonl` includes:

- `enabled`
- `case_id`
- `label`
- `request`
- `target_window`
- `control_windows`
- `target_place_tokens_any`
- optional `target_country_codes_any`
- `scoring_expectations`
- `benchmark_refs`

### `request`

The request must be directly compatible with `build_scan_request(...)`.

### `target_window`

The expected event or campaign concentration window inside the scan window.

### `control_windows`

Matched non-event windows inside the same scan run. These are used to test whether the target window really stands out, instead of looking good only because the whole series is elevated.

### `scoring_expectations`

Current thresholds are intentionally modest:

- `max_target_place_rank`
- `min_target_percentile`
- `max_peak_distance_hours`

These thresholds should stay honest to the actual runtime behavior. They are not supposed to force a green benchmark through loose acceptance.

## Expected Interpretation

The critical answer from this suite should be read as:

- scan localization / timing concentration around known war events

not as:

- proof of standalone prospective war prediction

If this suite performs badly, the right conclusion is that the war scan runtime is still weak at theater localization and event-window concentration.

If it performs moderately, the right conclusion is still only that the runtime shows some hindcast signal.

## Next Steps After This Suite

If the suite shows real signal:

- widen case count
- add more matched control windows
- test `campaign_escalation` more broadly

If the suite shows weak signal:

- inspect place-atlas coverage
- inspect war-event locality semantics
- inspect raw-cell versus place-series ranking behavior
- inspect chart-type / domain leakage
