# Mundane Phase 5 Domain Plan

## Goal

Start Phase 5 by adding new domain families only where the corpus already supports a real, source-backed, benchmarked runtime slice.

The first Phase 5 family is:

- `alliance_stress`

This is the cleanest starting point because the existing corpus already contains:

- Green's eleventh-house logic for friendly nations
- Watters' retrograde-Mars doctrine for broken treaties and reversals
- an explicit historical ally-collapse case through France in 1940

## Phase 5 Order

1. `alliance_stress`
2. `trade_and_commerce`
3. `epidemic_wave_pressure`

Do not start weather, earthquakes, or fixed-star catastrophe runtime families here.

## Alliance Stress Scope

`alliance_stress` should cover:

- friendly-nation support failure
- coalition backing rupture
- ally-network coldness or unreliability
- treaty-channel instability when it specifically degrades allied support

It should not replace:

- `diplomacy_foreign_affairs` for broad treaty and negotiation questions
- `war_outbreak` for hostilities
- `regime_stability` for domestic institutional strain

## Acceptance Gate

The first Alliance Stress slice is honest only if all three remain true:

1. doctrine remains tied to local sources
2. benchmark calibration stays seeded rather than overstated
3. runtime flags explicitly preserve `research_gated` and `source_concentrated`

## First Slice

The first implementation slice includes:

- runtime domain catalog entry
- doctrine note ids in the reference runtime
- a dedicated historical slice:
  - `backend/benchmarks/mundane/alliance_stress_cases.jsonl`
- one mirrored case in the master historical pack
- at least one dedicated evaluator path in `backend/mundane_domain_rules.py`
- benchmark-profile and API catalog coverage tests

## Trade and Commerce Scope

`trade_and_commerce` should cover:

- foreign trade disputes
- treaty-port and shipping blockage
- commercial restrictions or paralysis
- parliamentary or policy blockage that directly burdens commerce

It should not replace:

- `finance_economy` for broad treasury, debt, and banking strain
- `diplomacy_foreign_affairs` for general treaty and negotiation logic

## Next After Trade and Commerce

If the first two Phase 5 families stay green after their seeded slices, the next Phase 5 family should be:

- `epidemic_wave_pressure`

That family is next only if it can be kept honest as a narrower public-health subfamily rather than a duplicate of the broader epidemic domain.

## Current Phase 5 Status

- `alliance_stress`
  - live
  - doctrine-expanded
  - benchmark-backed at moderate depth
- `trade_and_commerce`
  - live
  - doctrine-expanded
  - benchmark-backed at supported depth
- `epidemic_wave_pressure`
  - live
  - benchmark-backed at supported depth
  - broadened beyond the 1918-1919 influenza family

## Completion Slice

The Phase 5 completion slice adds:

- a second explicit historical `alliance_stress` case:
  - Atlantic Alliance strain during the 1973-1974 oil embargo
- two additional `trade_and_commerce` cases:
  - Suez Canal closure and shipping interruption, 1956-1957
  - oil-embargo commercial disruption, 1973-1974
- one non-influenza `epidemic_wave_pressure` case:
  - India COVID-19 second-wave surge, 2021

See:

- `docs/MUNDANE_PHASE5_COMPLETION_PLAN_2026-04-11.md`

## Phase 5 Status

Status: complete

Phase 5 is now closed as runtime-live, benchmark-backed, and still research-gated.
