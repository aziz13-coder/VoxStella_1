# Astro Clock Remediation Implementation Plan (2026-04-14)

## Purpose

This document turns the Astro Clock review into a staged implementation plan.
It is anchored to the live source workflow as of 2026-04-14 and is intended to
prevent performance fixes from breaking the existing Electron, backend, and
renderer flow.

This plan supersedes ad hoc assumptions from older audits where the source no
longer matches the documented route shape.

## Current Runtime Workflow

### Desktop startup

1. `frontend/main.js`
   - resolves the packaged or source backend command
   - spawns the local backend
   - waits on `GET /api/health?skip_network=true`
   - creates the Electron window with `contextIsolation: true`,
     `nodeIntegration: false`, and `sandbox: true`
2. `frontend/preload.js`
   - exposes `API_BASE_URL`
   - exposes `IS_PACKAGED`
   - exposes a narrow `electronAPI` bridge
3. Renderer bootstrap
   - Astro Clock renderer code talks to the backend through
     `frontend/src/features/astroclock/api.mjs`

### Astro Clock live loop

1. `AstroClock.jsx` is the main Astro Clock screen.
2. The live loop fetches:
   - `/api/astro-clock/dashboard`
   - `/api/astro-clock/planetary-hours`
3. `/api/astro-clock/stream` is a heartbeat trigger only.
   - The renderer uses it to know when to refresh.
   - The data payload still comes from normal HTTP routes.

### On-demand feature routes

These are not part of the baseline live loop and should stay decoupled:

- `/api/astro-clock/traits/profile`
- `/api/astro-clock/forensic`
- `/api/astro-clock/synastry`
- `/api/astro-clock/transits`
- `/api/astro-clock/context/auto`
- `/api/astro-clock/astrocartography/*`

### Chart data source of truth

Astro Clock still depends on `AstroClockEngine.get_current_data(...)` as the
chart-generation source of truth.

The main backend workflow is:

1. route resolves manual or realtime request context
2. route or helper calls `AstroClockEngine.get_current_data(...)`
3. route builds a projection for the specific feature
4. renderer consumes the route-specific payload

## Current Bottlenecks

### 1. Dashboard cost center

`_build_dashboard_payload()` is still the central fan-out function for:

- moon block and timeline
- aspect summaries
- fixed stars
- Arabic parts
- sect
- cusp aspects
- metrics
- receptions
- optional Morin payloads

This is fine as a compatibility layer, but it is too broad to remain the only
shared internal model.

### 2. Cusp aspects hidden chart rebuild

`compute_cusp_aspects()` currently performs forward sampling by instantiating a
fresh `AstroClockEngine` and computing another chart. That creates hidden cost
inside dashboard and forensic.

### 3. Synastry cold-path rebuild

Synastry still:

1. loads two snaps from the JSON store
2. recomputes two chart bundles
3. serializes that work behind `_engine_lock`

The hot path is fine. The cold path is still expensive and sensitive to
concurrency.

### 4. Logging noise

Per-request INFO logging remains high in:

- `backend/astro_clock_engine.py`
- `backend/cusp_aspects.py`
- `backend/horary_engine/services/geolocation.py`

This makes real performance traces harder to read.

## Guardrails

These constraints apply to every phase below:

- Do not change public route shapes in the first remediation pass.
- Do not change frontend request helper signatures unless the backend contract
  changes intentionally.
- Keep `/api/astro-clock/stream` as a trigger-only heartbeat unless the live
  loop is intentionally redesigned.
- Keep traits on the lightweight path and do not route it back through
  `_build_dashboard_payload()`.
- Preserve synastry input and output contracts while changing only caching or
  recomputation strategy.
- Keep packaged artifacts untouched. Source-only edits live under:
  - `backend/**`
  - `frontend/backend/**`
  - `frontend/src/**`

## Phased Plan

### Phase 1. Instrumentation and workflow freeze

Goal:

- measure route and substep timings without changing route payloads

Work:

- add opt-in Astro Clock timing spans in `backend/astro_clock_api.py`
- cover:
  - `/current`
  - `/dashboard`
  - `/traits/profile`
  - `/synastry`
  - `/forensic` preparation/evaluation slices
  - `_data_for_request_clock_context`
  - `_compute_chart_bundle_for`
  - dashboard cost centers such as cusp aspects and metrics
- keep instrumentation behind environment flags:
  - `VOX_STELLA_ASTRO_PERF=1`
  - `VOX_STELLA_ASTRO_TIMINGS=1`

Status:

- started in this pass

### Phase 2. Dashboard internal split

Goal:

- preserve the dashboard JSON contract while splitting the internal builder into
  reusable sub-projections

Work:

- extract stable helpers for:
  - base chart projection
  - moon data
  - aspect summaries
  - fixed stars / lots / sect
  - cusp aspects
  - metrics / receptions
  - Morin extras

This is the prerequisite for reducing forensic coupling safely.

### Phase 3. Remove the hidden cusp-aspect chart rebuild

Goal:

- stop `compute_cusp_aspects()` from instantiating its own engine

Work:

- make the caller provide optional forward-sampled chart state
- keep the returned cusp-aspect payload stable
- benchmark dashboard and forensic again after the change

### Phase 4. Synastry cold-path hardening

Goal:

- reduce cold-start recomputation without changing the synastry contract

Work:

- add an in-process bundle cache keyed by snap identity and effective chart
  context
- add a lightweight in-memory snap index while keeping JSON persistence
- keep `snap_a_id` and `snap_b_id` as the public API

### Phase 5. Forensic de-coupling

Goal:

- stop forensic from paying for every dashboard tile by default

Work:

- reuse only the specific sub-projections forensic needs
- keep the forensic payload stable while replacing internal dependencies in
  slices

### Phase 6. Logging discipline

Goal:

- reduce hot-path INFO noise without losing failure diagnostics

Work:

- move per-request happy-path logs to DEBUG where practical
- keep failure, fallback, and degraded-path logs visible
- keep one structured timing line when perf tracing is enabled

## Immediate Verification Checklist

After each remediation slice, re-run the targeted workflow checks:

- backend:
  - `python -m pytest backend\\test_astro_clock_api_traits.py -q`
- frontend:
  - `npm --prefix frontend run test:ui -- astroClockModeFlow.test.jsx`
  - `npm --prefix frontend run test:unit`

## Notes on Documentation Hygiene

- `docs/ASTRO_CLOCK_BACKEND_WORKFLOW_AUDIT_REFRESH_2026-04-14.md` is the
  current backend audit baseline.
- `docs/ASTRO_CLOCK_BACKEND_WORKFLOW_AUDIT_2026-04-14.md` reflects an older
  traits-path understanding and should be treated as superseded unless updated.
- `docs/FRONTEND_BACKEND_WORKFLOW_AUDIT_2026-03-05.md` contains at least one
  stale health/readiness finding and should not be used as the current startup
  authority without revalidation.
