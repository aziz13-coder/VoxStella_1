# Mundane Implementation Plan

## Main Goal

Implement a source-governed mundane astrology layer as a sibling feature family to astrocartography, then expose it through AstroClock with a research-gated toggle.

This is not a generic scoring extension of the current astrocartography engine.

It is a new runtime family that reuses the delivery architecture while keeping separate doctrine, schemas, and domain logic.

## Mundane Capabilities

The mundane layer is intended to do these things:

- resolve a mundane chart context from chart type, polity or event, and location context
- analyze public rather than personal topics
- combine framework, trigger, and activation layers in one response
- expose domain-lens outputs instead of one generic score
- attach doctrine notes, source tags, and research-gating flags to results
- support national-chart and event-chart workflows without collapsing them into one generic location model

The first runtime capability set should cover:

- chart types:
  - `aries_ingress`
  - `lunation`
  - `eclipse`
  - `war_event`
  - `national_chart`
- context types:
  - `capital_chart`
  - `national_chart`
  - `event_chart`
  - `regional_chart`
- domain lenses:
  - `war_conflict`
  - `government_stability`
  - `diplomacy_foreign_affairs`
  - `public_health`

The mundane layer is not intended, in its first implementation, to do these things:

- replace astrocartography
- generate a single universal mundane score
- treat weak doctrines as production-ready predictions
- include weather, earthquakes, or fixed-star catastrophe logic in runtime output

## Preconditions Already Met

The following are now in place:

- raw and normalized source corpus
- doctrine reference docs and merged summaries
- source-alignment dataset
- historical benchmark packs
- dataset validator and runner

This means the project has crossed the research threshold needed to start implementation work.

## Next Step

Build the mundane runtime family and backend API skeleton before touching the frontend toggle.

Reason:

- the frontend toggle has no value without a stable backend contract
- the current astrocartography models cannot be repurposed directly
- the first implementation risk is schema and domain-shape drift, not presentation

## Implementation Sequence

### Phase 1: Runtime asset family

Create:

- `backend/knowledge/mundane/mundane_chart_types.runtime.json`
- `backend/knowledge/mundane/mundane_domain_models.runtime.json`
- `backend/knowledge/mundane/mundane_country_registry.runtime.json`
- `backend/knowledge/mundane/mundane_reference_runtime.json`

Purpose:

- freeze the first runtime-facing schema
- separate chart types, domain lenses, and polity registry
- keep source-backed doctrine available to the service layer

### Phase 2: Backend service skeleton

Add a sibling service pattern to astrocartography:

- `backend/mundane_assets.py`
- `backend/mundane_service.py`
- `backend/mundane_models.py`

First responsibilities:

- load runtime assets
- resolve chart context
- validate domain and chart-type requests
- return cited doctrine notes and research-gating flags

No scoring model generation yet.

### Phase 3: API surface

Expose the first research-mode endpoints:

- `/api/astro-clock/mundane/chart-types`
- `/api/astro-clock/mundane/context/resolve`
- `/api/astro-clock/mundane/analyze`

The initial `analyze` response should include:

- resolved chart context
- active domain lens
- framework layer
- trigger layer
- activation layer
- doctrine/source tags
- research status flags

### Phase 4: Frontend toggle and modal shell

Only after the API shape is stable:

- keep the existing advanced modal entrypoint in `frontend/src/features/astroclock/AstroClock.jsx`
- add an analysis-mode toggle inside `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- render a dedicated mundane workspace inside that modal rather than a second top-level modal
- call the new mundane endpoints through `frontend/src/features/astroclock/api.mjs`

The first UI should select:

1. chart type
2. polity or event
3. location context
4. domain lens

See:

- `docs/MUNDANE_ASTROCARTOGRAPHY_TOGGLE_INTEGRATION_2026-04-11.md`
- `docs/MUNDANE_MODEL_EXPANSION_PLAN_2026-04-11.md`
- `docs/MUNDANE_PHASE2_SPLIT_PLAN_2026-04-11.md`
- `docs/MUNDANE_PHASE3_TRIGGER_PLAN_2026-04-11.md`
- `docs/MUNDANE_PHASE4_CONTEXT_PLAN_2026-04-11.md`
- `docs/MUNDANE_PHASE5_DOMAIN_PLAN_2026-04-11.md`
- `docs/MUNDANE_PHASE5_COMPLETION_PLAN_2026-04-11.md`
- `docs/FRONTEND_BUNDLE_WARNING_2026-04-11.md`
- `docs/MUNDANE_SCAN_ENGINE_PLAN_2026-04-11.md`
- `docs/MUNDANE_WAR_SCAN_IMPROVEMENT_PLAN_2026-04-11.md`
- `docs/MUNDANE_SCAN_SERIES_GRAPH_PLAN_2026-04-11.md`
- `docs/MUNDANE_SCAN_SERIES_BENCHMARK_PLAN_2026-04-11.md`
- `docs/MUNDANE_CUSTOM_CHART_INPUT_2026-04-11.md`

Current roadmap status:

- Phase 1 complete
- Phase 2 complete
- Phase 3 complete
- Phase 4 complete
- Phase 5 complete: `alliance_stress`, `trade_and_commerce`, and `epidemic_wave_pressure` live as benchmark-backed research-gated slices
- Post-Phase-5 hardening complete
- Phase 6 defined, implementation deferred
- Weather/earthquake research-only intake active

It should not display one generic “mundane score”.

## First Implementation Scope

Keep the first runtime scope narrow:

- chart types:
  - `aries_ingress`
  - `lunation`
  - `eclipse`
  - `war_event`
  - `national_chart`
- domain lenses:
  - `war_conflict`
  - `government_stability`
  - `diplomacy_foreign_affairs`
  - `public_health`

Leave these out of the first runtime cut:

- weather
- earthquakes
- fixed-star catastrophe logic

## Acceptance Gate For Starting UI Work

Do not begin the user-facing toggle until all of these exist:

1. runtime asset files
2. backend service skeleton
3. API contract with stable request and response shape
4. at least one backend test for context resolution and analyze payload shape

## Immediate Build Target

The immediate build target is:

1. scaffold `backend/knowledge/mundane/*`
2. scaffold `backend/mundane_assets.py`
3. scaffold `backend/mundane_service.py`
4. expose the first three `/api/astro-clock/mundane/*` endpoints

That is the next step for the project.

## Post-Phase-5 Hardening

The active hardening note is:

- `docs/MUNDANE_POST_PHASE5_HARDENING_PLAN_2026-04-12.md`
- `docs/MUNDANE_POST_PHASE5_HARDENING_COMPLETION_PLAN_2026-04-12.md`

## Phase 6

The active Phase 6 note is:

- `docs/MUNDANE_PHASE6_PLAN_2026-04-12.md`
- `docs/MUNDANE_PHASE6_DEFERRAL_AND_WEATHER_RESEARCH_PLAN_2026-04-12.md`

## Weather / Earthquake Research Intake

The current source-inventory note is:

- `docs/WEATHER_EARTHQUAKE_SOURCE_INVENTORY_2026-04-12.md`
