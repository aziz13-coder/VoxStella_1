# Weather Predictive Hindcast Benchmark

Status date: 2026-04-12

## Purpose

This benchmark is designed to answer a narrower question than "does weather astrology predict weather?"

It asks:

- when a known historical weather event is turned into a place-timeline scan
- does the current seed runtime concentrate pressure near the real event window
- or does it peak elsewhere in the benchmark window

This is a hindcast benchmark, not a prospective forecast benchmark.

## Scope

The first predictive suite is intentionally limited to the four active seed-runtime families:

- `flood_risk`
- `hurricane_pressure`
- `severe_convective_pressure`
- `wind_event_pressure`

Each case is a place-timeline scan at a fixed historical location.

## Why This Is Separate From The Existing Weather Benchmark

The existing weather benchmark branch proves:

- source doctrine exists
- historical cases are curated
- citations resolve
- families are broad enough to justify runtime research

It does not prove that the runtime predicts dates.

The predictive hindcast suite exists specifically to test date alignment.

## Method

Each predictive case defines:

- a runtime family
- a historical location
- a benchmark scan window
- a narrower target event window
- matched non-event control windows
- scoring expectations

The runner executes a weather place-timeline scan across the benchmark window and then measures:

- `target_percentile`
  - how high the strongest event-window score sits relative to the full scanned timeline
- `target_rank`
  - rank of the strongest event-window slice among all slices in the scan
- `peak_distance_hours`
  - distance from the runtime's overall peak window to the historical target window
- `target_window_hit`
  - whether the runtime's overall peak overlaps the real event window
- `target_mean_lift`
  - how much stronger the event-window average is than the out-of-window average
- `target_beats_all_controls`
  - whether the target window peak beats the strongest matched control window
- `failure_reasons`
  - which configured thresholds the case missed, so weak spots can be traced back family-by-family
- `exact_passed`
  - whether the target window both aligns strongly and contains the overall peak
  - this means a target-window hit, not exact minute-level prediction
- `near_passed`
  - whether the target window aligns strongly and the overall peak lands near, but not inside, the target window

## Pass Logic

A case passes only if all configured expectations hold:

- `target_percentile >= min_target_percentile`
- `target_rank <= max_target_rank`
- `peak_distance_hours <= max_peak_distance_hours`
- `target_beats_all_controls = true`

This is deliberately stricter than simply asking whether the event window contains some non-zero score.

## Critical Interpretation Rule

Even a good hindcast result does not prove prospective prediction.

The suite can justify only one of these statements:

- no reliable hindcast timing signal
- weak or moderate hindcast timing signal
- usable hindcast timing signal

It must not be used to claim validated prospective prediction without a separate forward-looking or held-out benchmark design.

The hardened suite also distinguishes:

- broad alignment
- target-window timing
- near timing

The broad alignment rate can still be useful, but it must not be mistaken for precise event prediction.

## Current Constraint

The positive case count is still limited by the local source corpus.

At the moment:

- `flood_risk` has two explicit local hindcast anchors
- `hurricane_pressure` has two
- `severe_convective_pressure` has two
- `wind_event_pressure` has three

So the suite is now structurally stronger, but still source-limited in the number of positive historical anchors it can claim.

## Current Use

Run:

```powershell
python backend/run_weather_predictive_benchmarks.py
```

Or single-case:

```powershell
python backend/run_weather_predictive_benchmarks.py --case-id weather_predictive_hurricane_sandy_2012
```

Prospective scaffold:

```powershell
python backend/run_weather_prospective_benchmarks.py
```
