# Weather Failure Doctrine Review

Date: 2026-04-13

## Scope

This memo inspects the two remaining predictive hindcast failures after the weather gap-narrowing pass:

1. `weather_predictive_tornado_xenia_1974`
2. `weather_predictive_wind_reno_2002`

The purpose is diagnostic, not promotional. The question is whether the remaining misses come from:

- doctrine the runtime is not yet capturing,
- doctrine the sources only support in a broad pressure-window sense,
- or technical scoring/ranking behavior that is looser than the source method.

No runtime scoring changes are proposed in this memo. This is an inspection pass only.

## Benchmark Baseline

Current suite state after the gap-narrowing pass:

- `9` predictive hindcast cases
- `7/9` alignment passes
- `4/9` target-window hits
- `3/9` near passes
- median target percentile `0.9722`
- median peak distance `6h`

Remaining failures:

- `weather_predictive_tornado_xenia_1974`
- `weather_predictive_wind_reno_2002`

## Case 1: Xenia Tornado, 1974

### Runtime Result

Current hindcast outcome:

- family: `severe_convective_pressure`
- overall peak: `1974-04-04 06:00`
- overall peak score: `82`
- target-window peak: `1974-04-03 06:00`
- target-window peak score: `62`
- target percentile: `0.75`
- target rank: `8`
- max control peak: `79` on `1974-04-05 06:00`
- fail reasons:
  - `target_percentile_below_threshold`
  - `target_rank_above_threshold`
  - `control_window_outperformed_target`

The target day still carries clear pressure. The miss is not lack of signal. The miss is that nearby windows outrank it.

### What The Runtime Is Seeing

The strongest target-day rule stack is:

- seasonal `Mercury-Uranus` convective signature
- lunar-phase `Uranus angular`
- forecast `Uranus angular`
- forecast `Mars angular`
- quarter-phase dynamic trigger
- locality reinforcement across seasonal and lunar layers

The overall peak on `1974-04-04 06:00` adds stronger stacked convective structure and slightly stronger locality concentration than the target day. The `1974-04-05 06:00` control window also remains very strong because the runtime still sees:

- the same seasonal convective framework
- the same lunar-phase trigger family still in force
- forecast `Mars-Uranus`
- strong Uranian locality

In short, the runtime reads a broad outbreak band correctly, but it does not separate the true Xenia day sharply enough from the adjacent days.

### Source Doctrine

Riske is explicit on several points relevant to this case:

- astrometeorology is strongest for identifying a high-risk tornado day, week, or season, not exact minute/location timing
- tornadoes require classic thunderstorm structure plus moisture and strong wind
- Mercury, Mars, or Pluto must be prominent, with at least one other planet amplifying them
- tornadoes rarely occur without Mercury or Mars in hard aspect to Uranus or Neptune
- larger tornadoes especially need a hard Pluto factor

In the Xenia worked example, Riske emphasizes:

- Pluto as a key planet
- Mercury and Jupiter as major contributors to excessive wind
- warm moist flow plus cold-front structure
- the March 30 lunar phase as an activation layer
- April 3 transits as the day-level trigger

### Doctrine Comparison

The runtime is aligned with the source in these ways:

- it does use ingress plus lunar trigger plus event-day chart
- it does recognize Mercury/Uranus and Mars/Uranus style severe-weather structure
- it does reward stacked trigger structure and locality reinforcement

But it is still underrepresenting source doctrine in two important ways:

1. `Pluto is too weak in the live severe-convective family`

Riske treats Pluto as central for the high-wind intensity component of tornadoes, especially major tornadoes. The runtime miss suggests that the model is still letting generic Uranus/Mars convective testimony dominate over the stronger tornado-specific wind-intensity logic.

2. `Moisture and front-collision structure are too flattened`

Riske does not treat severe convection as only a dry convective shock pattern. The Xenia example is explicitly about:

- warm moist inflow
- cold-front delivery
- strong wind amplification

The current runtime still scores the target and control windows mostly through repeated Uranus/Mars angularity and quarter-phase freshness. That is a weaker doctrinal fit than the source method.

### Diagnostic Conclusion

This failure is mostly a `doctrine-shape` problem, not a pure technical bug.

The runtime identifies the outbreak band, but it remains too broad because:

- generic convective testimony still outruns tornado-specific structure
- Pluto-weighted wind intensity is too weak
- moisture plus cold-front convergence is not concentrated enough
- quarter-phase freshness remains strong across nearby windows that the source treats as less decisive than the event-day trigger stack

The right next severe-convective improvement is not "more storm score." It is:

- stronger tornado-specific Pluto / high-wind weighting
- tighter moisture-plus-cold-front concentration
- weaker persistence for generic quarter-phase activation once the actual event-day stack has passed

## Case 2: Reno Wind Event, 2002

### Runtime Result

Current hindcast outcome:

- family: `wind_event_pressure`
- overall peak: `2002-12-11 00:00`
- overall peak score: `58`
- target-window peak: `2002-12-14 06:00`
- target-window peak score: `50`
- target percentile: `0.90`
- target rank: `3`
- max control peak: `50`
- peak distance: `72h`
- fail reasons:
  - `peak_distance_too_large`
  - `control_window_outperformed_target`

This is not a weak-signal failure. It is a timing failure. The target day is strong, but the runtime peaks too early and allows control windows to tie it.

### What The Runtime Is Seeing

The current top window on `2002-12-11` is driven by:

- lunar-phase `Mercury-Uranus`
- lunar-phase Mercury angularity
- forecast Uranus angularity
- forecast stacked frontal structure
- Mercury-Mars reinforcement
- Mercury-Saturn reinforcement

The target day still carries strong pressure, but its top score only ties one control window and loses to the early `12/11` peak. That means the runtime is still too willing to call the opening lunar-phase background the strongest timing signal.

### Source Doctrine

Riske's Reno example is much sharper about timing than the runtime currently is.

The worked example emphasizes:

- retrograde Mercury at the autumn ingress
- Mercury sesquisquare Uranus as a high-wind / gust signature
- Saturn-Uranus plus Jupiter/IC pressure-gradient background
- the December 11 lunar phase showing strong event potential
- but not enough to time the emergency on its own
- the actual December 14 event-day trigger comes when transiting Mercury advances to the lunar-phase Ascendant and squares ingress retrograde Mercury

Riske's logic is direct here:

- the ingress shows the season
- the lunar phase shows the active week
- the event-day transits provide the actual timing bridge

### Doctrine Comparison

The runtime is aligned with the source in these ways:

- it correctly treats Mercury as the main wind planet
- it recognizes Mercury-Uranus, Mercury-Mars, and Mercury-Saturn wind/front patterns
- it rewards repeated locality reinforcement across layers

But the miss shows a sharper doctrinal mismatch than Xenia:

1. `The runtime overweights the weekly background`

Riske explicitly says the December 11 lunar phase shows maximum weather-event potential, but that by itself still does not explain the actual high-wind emergency timing. The runtime currently lets that broad weekly setup win the scan.

2. `The runtime underweights the event-day Mercury bridge`

The source puts the event-day bridge on:

- transiting Mercury advancing to the lunar-phase Ascendant
- transiting Mercury squaring ingress retrograde Mercury

That is a much more specific timing mechanism than the current wind runtime uses. The current model sees the background correctly but does not elevate the December 14 transit bridge enough above December 11-13.

3. `Retrograde/stationing Mercury is still not discriminated sharply enough`

Riske repeatedly treats Mercury at its worst when stationing, and secondarily during retrograde, when it hard-aspects ingress or lunar angles. The current runtime includes retrograde logic, but the Reno miss suggests it still behaves too much like a broad amplifier and not enough like a timing gate.

### Bonatti Comparison

Bonatti is less useful than Riske for this exact event, but the broad wind doctrine is consistent:

- Mercury is the primary wind planet
- Mercury often marks fronts and wind direction/velocity
- wind indications strengthen as the relevant body approaches and perfects the angular line

That supports the same conclusion as Riske: the later, more exact transit-to-angle bridge should outrank the earlier broad background.

### Diagnostic Conclusion

This failure is mainly a `technical-plus-doctrinal timing` problem.

The runtime is not wrong to show pressure in the December 11-14 band. It is wrong to let the opening band peak outrank the event-day bridge that the source actually highlights.

The right next wind improvement is not another broad Mercury/Uranus score increase. It is:

- stronger event-day weighting when Mercury perfects a bridge to ingress/lunar angles
- stronger discrimination for retrograde or stationing Mercury when the aspect is directly angular
- weaker scoring for early broad weekly setup when the exact bridge has not yet formed

## Cross-Case Conclusion

The two failures are different.

### Severe Convective

The Xenia miss is mainly about `family shape`:

- too much broad convective pressure
- not enough tornado-specific wind/moisture/front concentration
- not enough Pluto-weighted intensity

### Wind

The Reno miss is mainly about `timing discrimination`:

- too much weekly background weight
- not enough event-day Mercury bridge weight
- control windows tie too easily because the family still behaves too smoothly through the active band

## Recommended Next Changes

The strongest next source-backed changes would be:

1. `Severe convective`
   - raise tornado-specific Pluto/high-wind logic
   - strengthen moisture-plus-cold-front concentration
   - reduce persistence of generic quarter-phase bonus after the event-day bridge window

2. `Wind`
   - add stronger event-day Mercury-to-angle bridge weighting
   - sharpen retrograde/stationary Mercury when the aspect is angular and exacting
   - discount early weekly background if the later bridge becomes more exact

## Decision

No scoring change should be made from this memo alone.

The doctrinal direction is clear enough to justify the next implementation pass, but the next pass should still be narrow and benchmark-gated:

- improve one family
- rerun the predictive suite
- keep the change only if the family improves without degrading the stronger families

## Implementation Outcome

The next implementation pass was run narrowly against this memo.

### Severe Convective

A broader tornado-specific expansion was tested and rejected.

Why it was rejected:

- Xenia got worse instead of better
- the target-day percentile dropped
- the target-day rank worsened
- nearby control windows stayed stronger

So the severe-convective runtime was left at the earlier kept baseline. The Xenia diagnosis in this memo still stands: the remaining gap is family-shape discrimination, not a missing broad storm score.

### Wind

A narrower wind-timing pass was then tested and kept.

What changed:

- forecast Mercury now gets explicit bridge timing against support-chart Mercury in the seasonal ingress and lunar phase
- retrograde support-chart Mercury can amplify that bridge
- stationing Mercury can amplify that bridge
- aging weekly wind background is discounted when no sharper bridge has formed

Benchmark outcome:

- `weather_predictive_wind_reno_2002` moved from a timing failure to a clean target-window hit
- full-suite alignment improved from `5/9` to `6/9`
- wind improved from `0/3` to `1/3`

This means the wind half of the memo produced a retained runtime change, while the severe-convective half remains an open research problem.
