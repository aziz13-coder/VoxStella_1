# Mundane Phase 6 Plan

Status date: 2026-04-12

Current state: defined, deferred

See:

- `docs/MUNDANE_PHASE6_DEFERRAL_AND_WEATHER_RESEARCH_PLAN_2026-04-12.md`

## Goal

Move from isolated domain families to cross-domain synthesis.

This remains the intended Phase 6 direction, but implementation is currently deferred while the weather/earthquake research intake is assessed as a stronger benchmark-first branch candidate.

Phase 6 should not add another thin standalone family. The baseline is now stable enough to combine mature lenses into composite scenario outputs that explain how multiple public-event pressures interact in one chart, one polity context, or one scan window.

## Stabilized Baseline

Phase 6 starts only because the post-Phase-5 hardening gate is now satisfied:

- `alliance_stress`: `supported`
- `trade_and_commerce`: `broad`
- `epidemic_wave_pressure`: `broad`
- scan benchmarks: green
- scan-series benchmarks: green
- trigger benchmarks: green
- national-chart proving benchmarks: green
- citation failures: `0`

This means the baseline is strong enough for synthesis without building on thin or single-case families.

## Phase 6 Direction

Build composite scenario bundles that can combine multiple benchmark-backed mundane domains into one interpreted output.

The first Phase 6 bundles should be:

1. `external_pressure_complex`
2. `domestic_strain_complex`
3. `epidemic_state_stress_complex`

## First Composite Bundles

### 1. External pressure complex

Combine:

- `alliance_stress`
- `trade_and_commerce`
- `diplomacy_foreign_affairs`
- `war_outbreak`
- `campaign_escalation`

Use when the question is:

- external coercion
- treaty strain
- embargo pressure
- foreign-policy deterioration
- widening conflict exposure

This bundle should distinguish:

- allied fracture
- trade restriction or blockade
- broad diplomatic deterioration
- open war entry
- sustained campaign heat

### 2. Domestic strain complex

Combine:

- `regime_stability`
- `leadership_transition`
- `civil_unrest`
- `finance_economy`

Use when the question is:

- internal regime strain
- party fracture
- cabinet or leadership vulnerability
- public agitation
- treasury and budget pressure

This bundle should distinguish:

- office-holder transition stress
- institutional or parliamentary blockage
- crowd, labor, or union unrest
- treasury, debt, and budget strain

### 3. Epidemic-state-stress complex

Combine:

- `public_health`
- `epidemic_wave_pressure`
- `regime_stability`

Use when the question is:

- whether a health surge is only a medical burden
- or whether it is also becoming a state-function and institutional-pressure problem

This bundle should distinguish:

- broad public-health burden
- wave timing, recurrence, or subsiding pressure
- regime or governing-center strain caused by health-system overload

## Deliverables

### Runtime

Add a composite synthesis layer, not a second unrelated engine.

Candidate files:

- `backend/mundane_composite_rules.py`
- `backend/mundane_composite_models.py`
- `backend/mundane_composite_benchmark_runner.py`

Responsibilities:

- take multiple domain assessments from one resolved context
- produce composite conclusions without overwriting the underlying domain outputs
- preserve calibration and research flags per contributing domain
- explain which domains are driving the composite outcome

### API

Expose composite analysis as an additional research-mode surface, not a replacement for single-domain analysis.

Candidate endpoints:

- `/api/astro-clock/mundane/composite/catalog`
- `/api/astro-clock/mundane/composite/analyze`

### Frontend

Add composite output as a mode inside the existing mundane workspace rather than a separate shell.

The UI should show:

- contributing domains
- contributing scores and levels
- composite summary
- supporting signals and triggers
- calibration warnings for each contributing domain

## Benchmark Plan

Phase 6 needs its own benchmark family.

Add:

- `backend/benchmarks/mundane/composite_scenario_cases.jsonl`

The first benchmark rows should cover:

- alliance strain plus embargo pressure without open war
- regime instability plus civil unrest without leadership death
- epidemic wave plus regime pressure without needing war or economic collapse

Each composite row should require:

- expected leading composite family
- required contributing domains
- forbidden overreach domains
- source-backed rationale

## Guardrails

Phase 6 must keep these boundaries:

1. No universal mundane score
2. No hidden composite override that erases domain-level results
3. No composite promotion of thin or source-blocked families
4. No predictive certainty language
5. Composite outputs must preserve research flags from the underlying domains

## Sequence

1. Define composite output schema
2. Build composite synthesis layer on top of existing domain assessments
3. Seed composite benchmark pack
4. Validate composite outputs against the benchmark pack
5. Add composite mode to the existing mundane workspace

## Non-Goals

Phase 6 should not:

- add weather or earthquake runtime families
- add fixed-star catastrophe logic
- replace the existing single-domain analysis paths
- collapse scan graphs into one composite number

## Acceptance Gate

Phase 6 is complete when:

1. at least one composite bundle is live
2. composite outputs are benchmark-backed
3. composite outputs preserve domain-level calibration
4. scanner and graph outputs can show composite overlays without losing domain detail
