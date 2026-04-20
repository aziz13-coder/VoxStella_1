# Weather Predictive Hindcast Results

Run date: 2026-04-12

## Result

Hardened predictive hindcast suite result:

- cases: `9`
- alignment passes: `6`
- alignment pass rate: `66.7%`
- exact passes: `4`
- exact pass rate: `44.4%`
- near passes: `2`
- near pass rate: `22.2%`
- target-window hit rate: `44.4%`
- median target percentile: `0.9722`
- median peak distance: `6.0` hours

## Critical Answer

Current seed weather models do **not** show reliable event-timing prediction in this hindcast suite.

What the hardened suite now shows:

- the target event window is often relatively strong inside the scan
- timing concentration improved materially after the flood, hurricane, and kept wind-timing revisions
  - here "exact" means the overall peak lands inside the target event window, not exact minute-level prediction
- matched nearby control windows still compete with or beat the target window too often, especially in wind and one severe-convective case

## Failure Reasons

Current dominant fail reasons in the hardened suite:

- `control_window_outperformed_target`: `3`
- `target_percentile_below_threshold`: `1`
- `target_rank_above_threshold`: `1`

This means the branch is currently losing more from broad competition and timing drift than from a complete absence of target-window signal.

## Interpretation

The stricter suite lowered the apparent success rate for a good reason:

- the first hindcast pass rate could look encouraging
- but it mixed broad alignment with actual timing
- and it did not require the target window to beat matched nearby non-event windows

Under the hardened benchmark, the current seed runtime still behaves more like a pressure-highlighting system than a validated date-prediction system, but the flood and hurricane families are no longer the main blockers.

## Family Snapshot

- `flood_risk`: now `2/2` alignment with `2` target-window hits
- `hurricane_pressure`: now `2/2` alignment with `2` near passes and both target windows beating controls
- `severe_convective_pressure`: one near pass, one clear fail
- `wind_event_pressure`: now `1/3` alignment with the Reno target window recovered as a clean hit, but two control-window losses still remain

## Latest Runtime Experiments

The current kept runtime changes are:

- Mercury wind testimony is now less flat and more angle-distance-sensitive
- wind-family reinforcements now include Mercury-Mars and Mercury-Saturn aspect logic
- retrograde Mercury now only amplifies wind pressure when Mercury is already active
- forecast-to-support-chart Mercury bridge timing is now explicitly scored in the wind family
- flood now has a successive-trigger accumulation rule plus a tighter water-angle concentration rule
- hurricane now has a landfall-concentration gate plus a path-cluster concentration rule

Result:

- headline alignment improved from `3/9` to `6/9`
- flood improved from `1/2` to `2/2`
- hurricane improved from `1/2` to `2/2`
- wind improved from `0/3` to `1/3`
- wind-family failures are still concentrated in control-window competition

See also:

- [WEATHER_RUNTIME_WEAK_SPOT_REVIEW_2026-04-12.md](./WEATHER_RUNTIME_WEAK_SPOT_REVIEW_2026-04-12.md)

## What This Means

The models are not behaving like exact event-date predictors.

They are behaving like this:

- sometimes the real event window now becomes the actual top window
- sometimes the top peak still drifts into a nearby window
- and control windows still show that some of the apparent signal is broader atmospheric pressure, not event-specific timing

## Next Research Move

The next step is not more benchmark inflation.

It is model research:

1. inspect why control windows still beat target windows in `wind_event_pressure`
2. inspect why `severe_convective_pressure` still loses on Xenia-style competition
3. trace those weak spots back to the runtime family rules and the source doctrine
4. only then widen the benchmark again
