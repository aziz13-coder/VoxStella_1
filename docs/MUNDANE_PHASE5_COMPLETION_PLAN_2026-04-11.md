# Mundane Phase 5 Completion Plan

## Goal

Close Phase 5 honestly by widening the three new runtime families until none of them remain a one-case curiosity.

Phase 5 families:

- `alliance_stress`
- `trade_and_commerce`
- `epidemic_wave_pressure`

## Remaining Steps

1. `alliance_stress`
   - add one second explicit historical ally-network case
   - keep the doctrine side local and use an external historical anchor only for the event record if needed
   - target: remove `single_case_benchmark`

2. `trade_and_commerce`
   - add shipping-blockage coverage beyond Tientsin
   - add embargo or longer commercial-disruption coverage beyond post-1947 Britain
   - target: move from `moderate` toward `supported`

3. `epidemic_wave_pressure`
   - add one non-1918/1919 influenza wave case
   - keep the family narrow: surge, recurrence, and subsidence windows only
   - target: move from `moderate` toward `supported`

4. Update roadmap and status docs after the benchmark profiles change.

5. Re-run all benchmark suites and close Phase 5 only if the full mundane stack remains green.

## Closure Gate

Phase 5 is complete only if all of the following remain true:

- all three families stay `research_gated`
- `alliance_stress` is no longer single-case seeded
- `trade_and_commerce` and `epidemic_wave_pressure` have wider benchmark shape than their initial seeded slices
- full benchmark validation stays green with `0` citation failures

## Completion Status

Status: complete

The completion slice used:

- a second ally-network strain case from the 1973-1974 oil embargo and Atlantic Alliance tension
- two additional trade/commercial cases:
  - Suez Canal closure and shipping interruption, 1956-1957
  - oil-embargo commercial disruption, 1973-1974
- one non-influenza epidemic-wave case:
  - India COVID-19 second-wave surge, 2021

Resulting intended maturity:

- `alliance_stress`: `moderate`
- `trade_and_commerce`: `supported`
- `epidemic_wave_pressure`: `supported`

## Verified Outcome

After implementation and benchmark validation:

- `alliance_stress`
  - `2` unique cases
  - `3` source titles
  - `moderate`
- `trade_and_commerce`
  - `4` unique cases
  - `4` source titles
  - `supported`
- `epidemic_wave_pressure`
  - `4` unique cases
  - `4` source titles
  - `supported`

Validation state:

- mundane benchmarks: pass
- scanner benchmarks: pass
- scanner-series benchmarks: pass
- trigger benchmarks: pass
- national-chart proving benchmarks: pass
