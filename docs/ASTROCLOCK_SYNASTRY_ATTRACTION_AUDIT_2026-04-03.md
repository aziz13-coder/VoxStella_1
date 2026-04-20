# AstroClock Synastry Attraction Audit

Date: 2026-04-03

## Purpose

Resolve the repeated replay-slice signal that attraction was under-modeled in volatile real couples, without turning attraction into a generic inflation layer.

The audit focuses on two source-backed questions:

1. when supportive polarity and direct chemistry repeat the same message, does attraction still display too low?
2. when high-friction couples remain obviously magnetic, does the engine preserve that magnetism without mistaking it for ease?

## Source Basis

The attraction audit stays inside the existing synastry source stack:

1. Davison
   - `Pages 5, 59, and 74 - Sun/Moon and Venus/Mars combinations`
2. Arroyo
   - `Chapter 8 - Mars and Venus`

These sources support two distinct attraction patterns:

1. supportive polarity:
   - luminary complementarity plus Venus-Mars testimony
2. stressed magnetism:
   - attraction that stays strong under conflict rather than disappearing into friction alone

## Implemented Adjustments

The audit added two governed category adjustments in [synastry_rule_catalog.json](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_rule_catalog.json):

1. `attraction_supportive_polarity_floor`
   - raises attraction only when `sun_moon_soft` or `sun_moon_polar` and `venus_mars_attraction` repeat the same message
   - source: Davison
2. `attraction_stress_cluster_floor`
   - raises attraction only when `sun_moon_stress` and `venus_mars_square` or `mars_mars_hard` appear under already-high friction
   - source: Arroyo

Supporting score changes were also kept narrow:

1. `venus_mars_attraction`
   - attraction weight increased modestly
2. `venus_mars_square`
   - attraction weight increased modestly
3. `sun_moon_stress`
   - now contributes a small attraction signal rather than only conflict

## Replay Effect

The attraction audit changed replay slice 2 from:

1. `3 / 3 partially_aligned`

to:

1. `Frida Kahlo / Diego Rivera`
   - `partially_aligned`
   - live miss remains `burden` and `attraction`
2. `Sid Vicious / Nancy Spungen`
   - `aligned`
   - `attraction_stress_cluster_floor` now fires
3. `Elizabeth Taylor / Richard Burton`
   - `aligned`
   - `attraction_supportive_polarity_floor` now fires

Interpretation:

1. the audit fixed the repeated volatile-couple attraction miss
2. it did so through doctrine-shaped patterns, not a blanket attraction boost
3. the remaining replay miss now concentrates on `Frida / Diego`, where the problem is not the same pattern

## Slice 3 Follow-Through

The next replay slice was added specifically to see whether the attraction-family work generalized beyond `Sid / Nancy` and `Elizabeth / Burton`.

Current slice-3 result:

1. `Frank Sinatra / Ava Gardner`
   - `aligned`
   - attraction, friction, and burden all land in range
   - neither attraction floor is needed
2. `Jean-Paul Sartre / Simone de Beauvoir`
   - `aligned`
   - attraction was never the live miss here; attachment is now in range after the governed binding cluster adjustment
   - neither attraction floor is needed

Interpretation:

1. the attraction-family logic now generalizes to another better-timed glamour-and-volatility marriage without depending on a floor trigger
2. the attraction-family logic is no longer the live weakness in unconventional lifelong bonds either
3. the remaining replay miss stays with `Frida / Diego`, where attraction and burden appear to be jointly underpowered in a different pattern

## Selectivity Checks

The attraction changes were checked on three surfaces:

1. historical replay slice 2
   - `Sid / Nancy` gets only the stress attraction floor
   - `Elizabeth / Burton` gets only the supportive attraction floor
   - `Frida / Diego` gets neither
2. seeded corpus
   - `attraction_supportive_polarity_floor` fires on `1 / 24` seeded pairs
   - `attraction_stress_cluster_floor` fires on `0 / 24` seeded pairs
3. synthetic doctrine archetypes
   - supportive polarity plus chemistry: floor fires
   - magnetic stress cluster: floor fires

This matters because the stress attraction floor did not generalize through random seeded incidence alone. It needed explicit doctrine-shaped counterexamples to prove it was more than a local replay patch.

## Current Conclusion

The attraction-family audit is successful but not complete.

What is now stronger:

1. volatile chemistry is no longer being flattened into friction only
2. polarity-plus-chemistry patterns are no longer displaying as merely moderate attraction
3. the fixes stay selective instead of spreading across unrelated cases

What still needs pressure:

1. `Frida / Diego` remains a replay miss
2. attraction and burden still need to be watched together in growth-heavy, creative, or asymmetrical bonds
3. the next doctrinal pressure is not another attraction-family patch, but whether the `Frida / Diego` pattern repeats elsewhere as a burden-plus-attraction under-read
