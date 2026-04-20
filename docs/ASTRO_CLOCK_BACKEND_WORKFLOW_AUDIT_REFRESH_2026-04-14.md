# Astro Clock Backend Workflow Audit Refresh (2026-04-14)

## Scope

This refresh re-audits the live Astro Clock backend after the `traits/profile`
route was detached from `_build_dashboard_payload()`.

Routes re-checked:

- `/api/astro-clock/current`
- `/api/astro-clock/dashboard`
- `/api/astro-clock/traits/profile`
- `/api/astro-clock/synastry`
- `/api/astro-clock/forensic`

The goal is not just raw timing. It is current workflow shape, plumbing
duplication, logic coupling, and likely failure/slowness points.

## Measurement setup

- Source runtime (`ALLOW_DEV_LICENSE_BYPASS=1`, development mode)
- Flask `test_client()`
- Manual clock context pinned to:
  - `2026-04-14T12:00:00+03:00`
  - `Jerusalem, Israel`
  - `Asia/Jerusalem`
  - house system `R`
- Synastry snaps created in-process for:
  - Los Angeles, `1997-08-10T17:25:00-07:00`
  - Manhattan, `1995-12-27T21:16:00-05:00`

## Current timings

Measured route timings from the live test client:

- `/api/astro-clock/current`
  - avg `8.0 ms`
  - hot floor `5.6 ms`
  - first hit `16.0 ms`
- `/api/astro-clock/dashboard?include_modern=1&morin=1`
  - avg `552.3 ms`
- `/api/astro-clock/traits/profile`
  - avg `280.2 ms`
  - hot floor `269.6 ms`
- `/api/astro-clock/forensic`
  - avg `600.8 ms`
- `/api/astro-clock/synastry`
  - first hit `301.0 ms`
  - hot avg `29.2 ms`

Interpretation:

- `current` is operationally healthy.
- `traits/profile` is much better than the old dashboard-layered path, but it is
  still not cheap because it still generates a live chart and recomputes
  metrics/house influence each call.
- `dashboard` and `forensic` remain the heaviest Astro Clock paths.
- `synastry` is not persistently slow; it still has a real cold-start cost and a
  very small hot-path cost.

## Route workflow and current issues

### 1. `/api/astro-clock/current`

Current workflow:

1. resolve active clock context
2. call `AstroClockEngine.get_current_data()`
3. serialize chart result with `_serialize_real_time()`

Current state:

- Fast enough.
- Main risk is not algorithmic latency.
- Main issue is noisy INFO logging on every request:
  - Astro Clock engine lifecycle logging
  - horary judge logging
  - geolocation/time parsing logging

Assessment:

- No urgent performance change needed.
- Logging discipline still needs work.

### 2. `/api/astro-clock/dashboard`

Current workflow:

1. resolve active clock context
2. generate current chart
3. run `_build_dashboard_payload()`
4. inside `_build_dashboard_payload()`:
   - normalize planets
   - derive Moon block
   - derive Moon VoC timeline
   - sort aspects / tightest aspect
   - compute fixed star hits
   - compute Arabic parts
   - derive solar conditions
   - compute sect
   - compute cusp aspects
   - compute dispositors
   - compute metrics
   - optionally compute Morin payloads
   - extract receptions

Current issues:

- `_build_dashboard_payload()` is still a large orchestration hub with many
  optional branches.
- `compute_cusp_aspects()` is a major hidden cost center:
  - it instantiates a fresh `AstroClockEngine`
  - it computes a future chart sample
  - it does this to classify applying/separating phase for cusp hits
- `cusp_aspects` also logs detailed analysis summaries at `INFO`.
- The route still pays for several analyses even when the frontend may only need
  a subset of tiles.

Assessment:

- `dashboard` remains the main shared heavy route.
- The most concrete backend cost inside it is the forward-sampled
  `compute_cusp_aspects()` path.

### 3. `/api/astro-clock/traits/profile`

Current workflow after refactor:

1. resolve active clock context
2. build compact real-time projection
3. extract chart data directly
4. compute trait metrics directly
5. compute house influences directly
6. derive planet-area scores
7. evaluate with cached singleton `TraitEngine`
8. build lightweight trait chart snapshot

What changed relative to the old route:

- No `_build_dashboard_payload()`
- No dashboard-only extras
- No per-request `TraitEngine()` instantiation

Current issues:

- It still generates a live chart each request through the Astro Clock engine.
- It still recomputes `compute_metrics()` and `compute_house_influences()` every
  time.
- It still inherits the global INFO logging noise from chart generation.

Assessment:

- The dominant old redundancy is fixed.
- Remaining latency is mostly genuine route work:
  - live chart generation
  - metrics
  - house influence derivation

### 4. `/api/astro-clock/synastry`

Current workflow:

1. resolve `snap_a_id`
2. resolve `snap_b_id`
3. load both snaps from the JSON snap store
4. rebuild a chart bundle for each snap via `_compute_chart_bundle_for()`
5. detect optional point capability
6. enrich chart data with modern planets / Chiron when available
7. run `build_synastry_report()`

Current issues:

- Cold request still pays full rebuild for both charts.
- `_compute_chart_bundle_for()` serializes engine access under `_engine_lock`,
  which keeps the route deterministic but also prevents concurrency for bundle
  builds.
- SnapStore reads the whole JSON store on each `get()` call; acceptable at small
  scale, but structurally inefficient if snap count grows.
- First request still pays geolocation/timezone and chart-generation cost twice.

Assessment:

- `synastry` is not a steady-state slowness problem.
- It is a cold-start and orchestration problem.
- Main opportunities are:
  - bundle reuse for recent snaps
  - avoiding repeated location/timezone re-resolution for snap-based calls

### 5. `/api/astro-clock/forensic`

Current workflow:

1. resolve active clock context
2. build full dashboard payload with `include_modern=True`
3. recover full aspect list from chart result
4. extract forensic features from dashboard payload
5. load cached knowledge/dictionary bundles
6. evaluate findings
7. compute dominance
8. compute survivability
9. derive receptions and relationship star hits
10. optionally compute abduction local-space mapping
11. return a very large response payload including dictionaries and derived data

Current issues:

- Still built on top of the heavy dashboard route shape.
- Route body is structurally monolithic and does too much orchestration itself.
- Response payload is large and includes many dictionaries every request.
- Relationship star-hit derivation and fallback reception derivation add more
  per-request work on top of the dashboard path.
- Abduction mode adds more geospatial work and remains bolted onto the same
  endpoint.

Assessment:

- `forensic` is now the heaviest practical Astro Clock route.
- The problem is not YAML load churn; those loads are already cached.
- The problem is route shape and response breadth.

## Cross-cutting plumbing issues

### 1. INFO-level logging is still too chatty

Still emitted on routine requests:

- per-request geolocation trace messages
- Astro Clock engine routine chart-generation messages
- horary engine routine judge messages
- cusp-aspect summaries
- request/response logging in `app.py`

Impact:

- noisy console output
- harder profiling
- extra I/O overhead in packaged runtime

### 2. Forward-sampled secondary analyses instantiate fresh engine state

The clearest example is `compute_cusp_aspects()`, which creates a new
`AstroClockEngine()` and computes a future chart sample to classify phase.

Impact:

- extra initialization churn
- extra chart-generation work
- more INFO logging
- hidden cost inside dashboard/forensic

### 3. Global engine locking still constrains throughput

`_compute_chart_bundle_for()` uses `_engine_lock` around the shared engine call.

Impact:

- serializes bundle generation
- hurts concurrency for snap-heavy paths like synastry
- safe for correctness, but expensive under parallel load

### 4. Route design still mixes computation and response shaping

This is strongest in:

- `_build_dashboard_payload()`
- `forensic_analysis()`

Impact:

- hard to benchmark sub-stages cleanly
- hard to cache partial results
- higher regression risk when adding one more tile or one more forensic section

## Current priority order

### Priority A: logging discipline

Demote routine geolocation, chart-generation, and cusp-aspect narration from
`INFO` to `DEBUG`, while keeping actual failures/warnings at `WARNING` or
`ERROR`.

Reason:

- low-risk
- immediately improves packaged runtime noise
- makes remaining profiling easier

### Priority B: reduce dashboard hidden secondary chart work

Most likely first target:

- stop `compute_cusp_aspects()` from spinning up a fresh engine and future chart
  on every dashboard/forensic request

Reason:

- this is the clearest concrete cost still sitting inside the shared heavy path

### Priority C: split forensic from full dashboard dependency

Goal:

- build a forensic-specific compact payload instead of requiring the entire
  dashboard shape first

Reason:

- current forensic latency is mostly inherited from dashboard plus forensic-only
  enrichment

### Priority D: synastry snap/bundle reuse

Goal:

- cache or reuse computed bundles for snap-based synastry calls

Reason:

- hot path is already good
- this is mostly about the cold-start penalty and repeated chart rebuilds

## Current bottom line

After the trait refactor:

- `traits/profile` is no longer the main backend bottleneck
- `dashboard` is the main shared heavy route
- `forensic` is the heaviest route by shape
- `synastry` is mostly a cold-path orchestration issue, not a hot-path problem
- logging remains materially noisier than it should be

The backend is in a better state than the previous audit baseline, but the next
meaningful performance gains will come from:

1. reducing hidden secondary chart work inside dashboard
2. detaching forensic from full dashboard composition
3. cleaning up routine INFO logging
