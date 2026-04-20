# Mundane Phase 6 Deferral And Weather Research Plan

Status date: 2026-04-12

## Status

The mundane baseline is stable enough to support Phase 6 in principle, but Phase 6 implementation is now intentionally deferred.

Current stabilized baseline:

- `alliance_stress`: `supported`
- `trade_and_commerce`: `broad`
- `epidemic_wave_pressure`: `broad`
- scan benchmarks: green
- scan-series benchmarks: green
- trigger benchmarks: green
- national-chart proving benchmarks: green
- citation failures: `0`

The newer domains already have dedicated benchmark packs and live calibration. This is not a benchmark gap.

## Why Phase 6 Is Deferred

Phase 6 is cross-domain synthesis. It is optional product work, not a correctness gate.

The stronger near-term research move is to investigate whether weather and earthquake doctrine can support a new benchmark-first branch before any runtime code is added. That work is source-sensitive and should happen before adding another synthesis surface that the product does not currently need.

## New Plan

### 1. Keep Phase 6 defined but not active

- do not implement composite runtime code yet
- keep the plan document as a future option
- avoid expanding output complexity without a user-facing need

### 2. Open a weather/earthquake research-only intake

The intake should stay research-only until the source base is proven strong enough.

Immediate tasks:

1. extract and convert the locally available sources
2. inventory usable weather and earthquake doctrine separately
3. assess whether each subdomain is strong enough for a benchmark-first branch
4. only after that, decide whether to seed benchmark packs
5. do not add runtime families yet

### 3. Treat weather and earthquakes as separate decisions

They should not be accepted or rejected as one bundle.

- weather may become benchmark-feasible earlier
- earthquakes may remain source-blocked longer

## Current Intake Result

See:

- `docs/WEATHER_EARTHQUAKE_SOURCE_INVENTORY_2026-04-12.md`

Current result:

- Kris Brandt Riske weather source: extracted and converted successfully
- B.V. Raman weather/earthquake source: archive chain present, but the embedded PDF is corrupt with the extraction tools currently available in this environment

That means:

- weather: partial source intake, not yet benchmark-ready, but ready for Riske-only doctrine extraction
- earthquakes: still source-blocked

The active natural-phenomena research path is now split:

- `docs/WEATHER_DOCTRINE_INVENTORY_2026-04-12.md`
- `docs/EARTHQUAKE_DOCTRINE_INVENTORY_2026-04-12.md`
- `docs/WEATHER_RISKE_SOURCE_MEMO_2026-04-12.md`

Reassessment from the current local corpus:

- weather now has a narrow seeded benchmark-first branch
- earthquakes remain doctrine-seeded but benchmark-not-ready

Weather runtime remains blocked by an explicit gate:

- `docs/WEATHER_RUNTIME_GATE_2026-04-12.md`

## Acceptance Gate To Revisit Phase 6

Phase 6 should only move back to active implementation after one of these is true:

1. the product explicitly needs cross-domain synthesis now, or
2. the weather/earthquake intake is concluded and there is no stronger benchmark-first research branch to pursue first

## Acceptance Gate For A Weather/Earthquake Benchmark-First Branch

Do not start benchmark packs for those domains until all three are true:

1. at least two usable source families are accessible as text for the target subdomain
2. the source inventory identifies stable doctrine statements that can be converted into source-alignment cases
3. there is enough historical anchor material to seed a benchmark pack without inventing runtime precision
