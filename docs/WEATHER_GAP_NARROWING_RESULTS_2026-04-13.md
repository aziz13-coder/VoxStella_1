# Weather Gap Narrowing Results

Status date: 2026-04-13

## Scope

This memo records the implemented outcome of:

- `docs/WEATHER_GAP_NARROWING_PLAN_2026-04-13.md`

The work was applied to both:

1. analysis mode
2. scan mode

## What Changed In Runtime

### Phase A: Locality and path narrowing

Implemented in the live runtime:

1. locality strength is now explicit rather than implied
2. locality notes now carry:
   - forecast angular concentration
   - tight-hit count
   - reinforcing-layer count
   - family-specific path concentration
3. `flood_risk` now adds a narrower waterfield locality cluster when wet testimony concentrates on forecast-chart angles
4. `hurricane_pressure` now carries stronger path/landfall concentration into scan metadata instead of only raw score

### Phase B: Weak-family discrimination

Implemented in the live runtime:

1. family scoring now uses weighted duplicate-signal reinforcement instead of flat duplicate stacking
2. `severe_convective_pressure` now distinguishes:
   - stacked convective trigger structure
   - fresh quarter-phase trigger window
   - aging late-window convective drift
3. `wind_event_pressure` now distinguishes:
   - stacked frontal structure
   - broad Mercury-only background without enough reinforcement

### Phase C: Scan semantics

Implemented in the scan runtime:

1. place-series now expose:
   - `event_focus_index`
   - `peak_sharpness`
   - `peak_locality_strength`
   - `peak_path_concentration`
   - `peak_window_width_steps`
   - `peak_occurrence_count`
2. recurring equal peaks now widen the returned peak window across the full recurring span
3. place ranking is now event-focus weighted instead of only score/timing weighted

### Phase D: Bounded eclipse decision

Implemented as a runtime decision, not live scoring:

1. weather chart resolution now exposes `eclipse_overlay.status = deferred`
2. runtime research flags now include `eclipse_runtime_deferred`
3. eclipse timing is explicit in the runtime as a deferred decision instead of silent absence

### Phase E: Runtime family graduation

Implemented as a decision artifact:

1. no benchmark-only family graduates into runtime in this pass
2. runtime catalog now states that new families remain deferred

## Benchmark Rerun

Command:

```text
python backend\run_weather_predictive_benchmarks.py --json
```

Result:

1. `9` cases
2. `7` alignment passes
3. `2` alignment failures
4. alignment pass rate `77.8%`
5. `4` target-window hits
6. target-window hit rate `44.4%`
7. `3` near passes
8. near-pass rate `33.3%`
9. median target percentile `0.9722`
10. median peak distance `6.0h`

## Family-Level Readout

### Flood

Current result:

1. `2/2` alignment passes
2. `2/2` target-window hits

Interpretation:

- flood remains the strongest live family
- the locality/path narrowing did not degrade the family

### Hurricane

Current result:

1. `2/2` alignment passes
2. `0/2` exact target-window hits
3. `2/2` near passes

Interpretation:

- hurricane remains strong on concentration, but still broad on exact timing

### Severe convective

Current result:

1. `1/2` alignment passes
2. `1/2` target-window hits
3. `1` remaining failure

Interpretation:

- the family is narrower than before, but Xenia-style control-window competition still remains a live weak spot

### Wind

Current result:

1. `2/3` alignment passes
2. `1/3` target-window hits
3. `1/3` near passes

Interpretation:

- wind improved materially from the earlier `0/3` state
- the remaining failure is still about broad competition and late peak drift rather than total absence of signal

## Failure Profile

Current failure reasons:

1. `control_window_outperformed_target = 2`
2. `peak_distance_too_large = 1`
3. `target_percentile_below_threshold = 1`
4. `target_rank_above_threshold = 1`

Interpretation:

- the remaining problems are now narrower
- the dominant weakness is still competition from nearby windows, not a total lack of target pressure

## Decision

The current runtime is better localized and better discriminated than the previous baseline.

That said:

1. this is still not strong enough to claim reliable prospective weather prediction
2. the remaining work should stay focused on:
   - severe-convective control-window separation
   - the last wind failure
3. no new runtime family should be added before those two weak spots are revisited
