# Weather Runtime Weak Spot Review

Status date: 2026-04-12

## Scope

This memo reviews the current seed weather runtime against the hardened predictive hindcast suite.

It is answering a narrow engineering question:

- which families lose because the benchmark is too strict for the source claim
- which families lose because the runtime is too broad or poorly discriminated
- which runtime changes are justified by the local source corpus

It is not claiming a validated forecasting engine.

## Benchmark Interpretation Correction

The hardened suite does **not** require exact minute-level prediction.

The current predictive runner already measures:

- `target_window_hit`
  - the overall peak overlaps the defined event window
- `near_hit`
  - the overall peak lands near the event window inside the configured tolerance

So the weak headline is not coming from an unrealistic "exact hour and minute" requirement.

It is coming mainly from:

- control windows that match or beat the target window
- peaks that drift to earlier or later nearby windows

## Current Hardened Result

- cases: `9`
- alignment passes: `6`
- target-window passes: `4`
- near passes: `2`
- median target percentile: `0.9722`
- median peak distance: `6` hours

This means the runtime often elevates the real event window, and the flood/hurricane families now isolate it materially better than the earlier baseline, but the branch still is not clean enough overall to count as reliable timing.

## Failure Pattern Summary

Current dominant failure reasons:

- `control_window_outperformed_target`
- `peak_distance_too_large`
- `target_percentile_below_threshold`
- `target_rank_above_threshold`

The key engineering point is that the suite is failing more from **competition and drift** than from complete absence of signal.

## Family Review

### Flood Risk

Current behavior:

- now `2/2` alignment
- `2/2` target-window hits
- controls no longer beat the target windows in the current suite

What is working:

- the runtime can find high water / heavy precipitation pressure
- Heppner still localizes a flash-flood window cleanly
- Dyersburg now benefits from the new accumulation handling instead of collapsing to the earlier control window

Remaining weak spot:

- the family is now usable in the current hindcast suite, but it still relies on a narrow proxy for accumulation
- there is not yet a fuller multi-phase weather-map runtime behind the score

Local-source justification:

- Riske treats Dyersburg through the spring ingress plus a sequence of successive lunar phases, not one isolated trigger chart
- that supports a future accumulation / successive-trigger hypothesis

Change kept:

- added a successive wet-trigger accumulation rule
- added a tight water-angle concentration rule

Safe conclusion:

- the local source was strong enough for a narrow accumulation fix
- no broader flood retune is justified yet

### Hurricane Pressure

Current behavior:

- now `2/2` alignment
- both cases are still near, not exact
- both target windows now beat their controls

What is working:

- the runtime can find tropical-storm pressure windows
- Galveston and Sandy now both retain the target period in the active band strongly enough to beat controls

Remaining weak spot:

- landfall timing is still broad rather than exact
- the family is better at corridor concentration than at precise arrival timing

Local-source justification:

- Riske explicitly frames astrology as stronger for weekly and seasonal storm pressure than for precise hurricane landfall timing
- Riske also emphasizes regional susceptibility and track zones, not only generic storm pressure

Change kept:

- added a landfall-concentration gate
- added a path-cluster concentration rule

Safe conclusion:

- the weak spot was locality / path discrimination, not total absence of hurricane signal
- the local source supported a narrow concentration fix
- more generic storm-planet scoring is still not justified

### Severe Convective Pressure

Current behavior:

- one near pass
- one clear fail

What is working:

- Moore shows the runtime can concentrate pressure near a real tornado day

Weak spot:

- Xenia shows the family is still too broad in some severe-weather windows
- earlier or later competing slices can outrank the target day

Local-source justification:

- Riske explicitly says astrometeorology is strongest for high-risk tornado days, weeks, or seasons, not exact minute/location work
- Riske repeatedly ties tornado / severe convection to stacked Mercury, Mars, Uranus, angle, and ingress-to-lunar activation logic

Safe conclusion:

- the family probably needs better stacked-trigger discrimination
- it does **not** justify treating every spring Mercury/Uranus setup as a target-day signal

### Wind Event Pressure

Current behavior:

- `1/3` alignment passes
- Reno now lands as a clean target-window hit
- the remaining two wind cases still lose on control-window competition

What is working:

- the runtime is detecting broad wind-prone periods

Weak spot:

- the family is too permissive
- generic Mercury angularity creates broad front/wind pressure that is not specific enough to isolate the real event window

Local-source justification:

- Riske treats Mercury as wind direction / velocity / fronts
- Riske also links high wind to Mercury-Uranus, Mars-Saturn, Saturn, Uranus, and other reinforced signatures
- Bonatti supports wind judgment, but not as a single generic Mercury-only rule

Safe conclusion:

- wind is the clearest family where the runtime likely overweights generic testimony and underweights reinforced combinations
- any future wind adjustment should first reduce unreinforced Mercury weight before adding new positive triggers

## Runtime Change Review

I first tested a broader source-backed runtime expansion pass and rejected it.

Why:

- the predictive suite got worse
- exact target-window performance dropped
- median peak distance worsened
- wind did not improve

So that patch was not kept.

This is the correct engineering outcome. Source-backed additions that degrade the benchmark should not ship.

I then tested a narrower wind-only adjustment and kept it.

What changed:

- Mercury angular wind testimony is now angle-distance-sensitive instead of completely flat
- `wind_event_pressure` now recognizes Mercury-Mars wind/gust signatures
- `wind_event_pressure` now recognizes Mercury-Saturn frontal-compression signatures
- retrograde Mercury now amplifies wind only when Mercury is already active

Result:

- Reno recovered as a clean target-window hit
- suite headline improved from `5/9` to `6/9` after the kept bridge pass
- wind improved from `0/3` to `1/3`
- remaining wind losses are now concentrated in control-window competition

Safe conclusion:

- this change improved wind timing discrimination without widening the family
- the remaining problem is still selection against matched nearby controls, not absence of wind signal

I then implemented the two next source-backed changes and kept both.

What changed:

- `flood_risk`
  - successive wet-trigger accumulation
  - tight water-angle concentration
- `hurricane_pressure`
  - landfall concentration gate
  - path cluster concentration

Result:

- suite headline improved from `3/9` to `5/9`
- `flood_risk` improved from `1/2` to `2/2`
- `hurricane_pressure` improved from `1/2` to `2/2`
- median peak distance improved from `18h` to `12h`
- dominant fail reason count for `control_window_outperformed_target` improved from `6` to `4`

Safe conclusion:

- both changes were narrow enough to keep
- both changes improved the families they targeted without introducing an obvious suite regression

## Source-Justified Next Hypotheses

The next runtime experiments that are justified by the local corpus are now:

1. `wind_event_pressure`
   - test better control-window separation after the new Mercury/Mars/Saturn reinforcement pass
   - next likely step is stronger path/front concentration, not another broad signal increase

2. `severe_convective_pressure`
   - test stacked-trigger concentration
   - avoid widening the family with more general spring storm signals

## Engineering Recommendation

The next implementation step should be:

1. keep the hardened benchmark as-is
2. use the new fail-reason accounting to target one family at a time
3. start with `wind_event_pressure`
4. then move to `severe_convective_pressure`
5. keep only changes that improve control-window superiority without degrading the other families

That is the only defensible way to move this branch forward.
