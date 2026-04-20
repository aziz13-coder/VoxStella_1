# Weather Runtime Gate

Status date: 2026-04-12

## Purpose

This document defines when the weather branch can leave benchmark-only status and move into runtime implementation.

The goal is to prevent the repo from adding a weather engine simply because a benchmark branch exists.

## Current State

Weather is:

- `benchmark-first active`
- `seed runtime implemented`
- `promotion beyond seed runtime still gated`

The weather branch now has:

- a local multi-source doctrine base
- seeded doctrine-alignment cases
- seeded historical family packs
- validation and reporting tooling

This is enough for a research-gated seed runtime.

It is not yet enough for graduation beyond seed status.

## Runtime Gate

All of the following must be true before the weather runtime can leave seed status and be treated as a promoted runtime surface.

### 1. Source gate

At least two operational source families must remain usable as text for weather logic.

Minimum acceptable base:

- Riske
- Bonatti

Supporting sources such as Watters and Green / Raphael / Carter help, but they do not replace the operational-source requirement.

### 2. Benchmark breadth gate

The benchmark branch must have:

- at least `12` source-alignment cases
- at least `30` historical rows
- at least `6` distinct weather families
- at least `2` historical rows per active family
- `0` citation failures

This gate is now essentially satisfied for branch seeding, but not by itself for runtime.

### 3. Family stability gate

At least four families must show stable doctrine and historical shape over multiple reviews.

Current likely candidates:

- floods
- hurricanes
- thunderstorms / tornadoes
- drought
- snow / freezing precipitation
- temperature extremes
- wind

`generalized_seasonal_temperature` is useful for framework gating, but it should not be treated as a runtime family unless it becomes more explicit and less mixed with precipitation narratives.

### Selected first runtime-candidate set

The current selected first runtime-candidate set is:

1. floods
2. hurricanes
3. thunderstorms / tornadoes
4. wind

Reason:

- they are the cleanest operational families in the current corpus
- they preserve distinct locality logic
- they have clearer event-shape boundaries than `generalized_seasonal_temperature`
- they are less likely to collapse into broad background-climate language than temperature families

### 4. Method-shape gate

The future runtime implementation must be able to separate:

- seasonal framework
- short-term trigger
- locality / map logic
- family-specific interpretation

If the implementation collapses these into one flat weather score, it fails the gate.

### 5. Benchmark-to-runtime mapping gate

Before runtime code begins, the repo must define a one-to-one map from benchmark family to candidate runtime family.

Example acceptable mapping:

- benchmark `floods` -> runtime `flood_risk`
- benchmark `hurricanes` -> runtime `hurricane_pressure`
- benchmark `thunderstorms_tornadoes` -> runtime `severe_convective_pressure`
- benchmark `drought` -> runtime `drought_pressure`

Example unacceptable mapping:

- all benchmark families -> one generic `weather`

### 6. Honesty gate

The first runtime weather implementation must remain:

- research-gated
- family-specific
- calibration-explicit
- non-deterministic

It must not claim earthquake coverage, climate-change modeling, or universal meteorological precision.

## What Still Blocks Runtime Promotion

These blockers remain:

- no prospective or held-out predictive benchmark proving date reliability
- no scan policy for weather locality grids
- no fuller locality-map runtime
- no evidence yet that the seed runtime is stable enough to leave research-gated status

The repo now has a predictive hindcast benchmark suite, but that suite is explicitly not enough to claim prospective prediction.

The hardened hindcast suite also now distinguishes:

- broad alignment
- exact timing
- near timing
- control-window superiority

At the moment that stricter benchmark still fails the promotion case for reliable timing.

## Next Safe Step

The next safe step is not to broaden the runtime immediately.

It is:

1. exercise the seed runtime against benchmark-backed review cases
2. define promotion criteria beyond the current benchmark-shape checks
3. decide whether weather scan/locality work is justified before broader family expansion
