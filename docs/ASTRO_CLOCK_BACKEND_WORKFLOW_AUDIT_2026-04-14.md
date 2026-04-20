# Astro Clock Backend Workflow Audit - 2026-04-14

## Scope

This audit covers the backend execution flow for the Astro Clock runtime and the adjacent high-cost feature paths that sit on top of it:

- `/api/astro-clock/current`
- `/api/astro-clock/dashboard`
- `/api/astro-clock/traits/profile`
- `/api/astro-clock/synastry`
- `/api/astro-clock/forensic`

It also records one additional plumbing defect in `/api/astro-clock/transits/window`, because that route contains obvious duplicate work even though it was not the main focus of this pass.

This is a current-state audit only. No backend logic was changed in this pass.

## Route map

### Current

- Route: `backend/astro_clock_api.py:1698-1703`
- Flow:
  1. get shared engine instance
  2. call `eng.get_current_data()`
  3. serialize `RealTimeData`

This is the lightest Astro Clock route.

### Dashboard

- Route: `backend/astro_clock_api.py:2056-2064`
- Flow:
  1. resolve active clock context via `_data_for_request_clock_context`
  2. build full dashboard payload via `_build_dashboard_payload`
  3. return compact dashboard JSON

This is the baseline heavy route. Several other features reuse this path and pay for its work.

### Trait profile

- Route: `backend/astro_clock_api.py:4394-4529`
- Flow:
  1. resolve active clock context
  2. serialize real-time payload
  3. extract chart data
  4. build dashboard payload with `include_modern=True` and `include_morin=True`
  5. recompute metrics again
  6. recompute house influences
  7. derive planet-area scores
  8. instantiate `TraitEngine()`
  9. load and evaluate trait catalog

This route clearly layers extra work on top of the already-expensive dashboard path.

### Synastry

- Route: `backend/astro_clock_api.py:4309-4391`
- Flow:
  1. load both snaps from JSON file store
  2. rebuild both chart bundles from snap datetime/location
  3. extend chart data for synastry support
  4. call `build_synastry_report`

This route does not use the dashboard builder, but it does pay for full chart recomputation for each snap pair.

### Forensic

- Route: `backend/astro_clock_api.py:5697-5905` and beyond
- Flow:
  1. resolve active clock context
  2. build dashboard payload
  3. re-open chart result and chart data
  4. attach `all_aspects`
  5. extract features
  6. load knowledge and dictionary YAML
  7. evaluate findings
  8. compute dominance, survivability, receptions, star hits, and dictionaries
  9. continue with optional abduction and corridor logic later in the route

This route is a large orchestration function. It is not catastrophically slow in the hot path, but it is structurally fragile and difficult to optimize in pieces.

## Shared execution flow

### 1. Context resolution

Shared route entry for manual and realtime Astro Clock requests is `_data_for_request_clock_context` in `backend/astro_clock_api.py:2947-3020`.

What it does:

1. inspect request overrides:
   - mode
   - datetime
   - location
   - timezone
   - house system
   - explicit coordinates
2. if no overrides, call `eng.get_current_data()`
3. if overrides exist:
   - infer coordinates when needed via `_ensure_coords_for_location`
   - infer timezone via `_resolve_timezone_for_context`
   - normalize the manual datetime
   - create local `AstroClockSettings`
   - call `eng.get_current_data(settings=local)`

Implication:

- nearly every non-trivial Astro Clock route shares the same location and timezone resolution stack before it can do any feature-specific work

### 2. Engine snapshot generation

Core engine path is in `backend/astro_clock_engine.py:92-154`.

What it does:

1. acquire `self._lock`
2. apply temporary settings override
3. call `_build_real_time_payload`
4. inside `_build_real_time_payload`:
   - determine effective time
   - generate chart with horary engine
   - extract planet positions
   - compute moon state
   - compute dispositor chains
   - extract aspects

Important architectural consequence:

- every call to `get_current_data()` is serialized behind a single engine lock

That is acceptable for correctness, but it becomes a bottleneck when several routes hit chart generation concurrently.

### 3. Dashboard builder fan-out

`_build_dashboard_payload` in `backend/astro_clock_api.py:1706-2053` is the central shared cost center.

It performs all of these in one pass:

- planet normalization
- moon block
- moon timeline
- aspect sorting
- fixed star hits
- Arabic parts
- solar conditions
- sect
- cusp aspects
- dispositors
- timezone label
- metrics
- Morin payloads when enabled
- receptions

Routes that reuse this builder inherit that entire cost profile whether they need every field or not.

## Timed observations

Timings were measured with the Flask test client in development-bypass mode. Reported numbers are request latency, not isolated function timings.

### Hot-path timings

Five-call hot measurements after warm-up:

| Route | Avg ms | Min ms | Max ms |
| --- | ---: | ---: | ---: |
| `/api/astro-clock/current` | 7.9 | 7.5 | 8.4 |
| `/api/astro-clock/dashboard?include_modern=1&morin=1` | 546.6 | 544.1 | 549.4 |
| `/api/astro-clock/traits/profile` | 811.9 | 807.3 | 825.0 |
| `/api/astro-clock/forensic` | 532.7 | 525.8 | 537.9 |
| `/api/astro-clock/dashboard` manual Jerusalem override | 541.4 | 535.0 | 547.5 |
| `/api/astro-clock/synastry` | 25.4 | 24.8 | 26.3 |

### Synastry cold vs hot

Fresh-process sequential timings for the same synastry request:

- first call: 1277.0 ms
- second call: 26.3 ms
- third call: 25.6 ms

Interpretation:

- synastry is not a permanently expensive hot route
- but its first hit is expensive enough to matter
- cold-start cost likely comes from chart generation, location/timezone resolution, and associated one-time engine setup

### Trait profile instrumentation

Function-level instrumentation showed:

- `compute_metrics(...)` itself is cheap, about 1.2 ms average
- trait catalog load is not free, about 20.8 ms per request

Interpretation:

- trait profile slowness is not caused by `compute_metrics`
- trait profile overhead comes from repeated high-level orchestration and repeated secondary derivations

## Ranked findings

### 1. Shared engine lock serializes all chart generation

Evidence:

- `AstroClockEngine` holds `self._lock` across `get_current_data()` in `backend/astro_clock_engine.py:104-126`
- the full payload generation sits inside that locked section in `backend/astro_clock_engine.py:128-154`

Risk:

- concurrent Astro Clock requests queue behind each other
- this creates avoidable latency spikes when dashboard, traits, forensic, or synastry are requested at the same time

Impact:

- correctness-safe
- throughput-limiting

### 2. Trait profile duplicates dashboard work and then adds more work

Evidence:

- route is `backend/astro_clock_api.py:4394-4529`
- it first builds dashboard payload with Morin enabled
- then it recomputes metrics in `4421-4424`
- then recomputes house influences in `4425-4429`
- then derives planet-area scores in `4442-4484`
- then instantiates `TraitEngine()` and evaluates the full catalog in `4485-4490`

Risk:

- trait profile is structurally layered on top of dashboard instead of reusing a stable intermediate model
- makes the route slower and harder to reason about

Observed effect:

- trait profile is about 265 ms slower than hot dashboard on the measured path

### 3. Trait catalog is loaded from disk per request

Evidence:

- `TraitEngine()` is instantiated per request in `backend/astro_clock_api.py:4485-4490`
- `_load_traits_catalog` scans `traits/catalog/**` and reads JSON files every time in `backend/traits/engine.py:62-158`

Risk:

- unnecessary disk I/O on each trait-profile call
- cost grows with catalog size

Measured effect:

- about 20.8 ms per request in the instrumented path

### 4. Snap store is file-backed and O(n) for every read

Evidence:

- `SnapStore` re-reads the whole JSON file on every `list()` and `get()` in `backend/snaps_store.py:22-27`, `45-54`
- `get()` linearly scans the `snaps` array in `49-54`
- synastry uses `_snaps().get(...)` twice in `backend/astro_clock_api.py:4309-4317`

Risk:

- synastry scales poorly with snap volume
- repeated reads add avoidable file I/O and parse overhead

Impact:

- manageable now
- likely to degrade as users accumulate snapshots

### 5. Synastry rebuilds both charts from snap metadata on every request

Evidence:

- `_synastry_bundle_from_snap_id` loads a snap and recomputes the chart bundle in `backend/astro_clock_api.py:4309-4325`
- synastry calls it twice in `4357-4358`

Risk:

- first-hit latency is high
- snap-to-snap comparisons do not reuse any bundle cache

Observed effect:

- first synastry call in a fresh process was about 1277 ms
- repeated hot calls then dropped to about 25 ms

Interpretation:

- this is a cold-path and reuse-path gap, not necessarily a permanently slow algorithm

### 6. Forensic route is a large orchestration block with too many responsibilities

Evidence:

- route body starts in `backend/astro_clock_api.py:5697`
- immediate dashboard build in `5710-5711`
- chart re-open and aspect enrichment in `5713-5738`
- feature extraction and knowledge evaluation in `5740-5755`
- reception fallback rebuild in `5757-5849`
- additional fixed-star and dictionary work in `5851-5905`

Risk:

- fragile control flow
- difficult partial optimization
- harder to validate because feature extraction, knowledge loading, fallback receptions, and result shaping are interleaved

Observed effect:

- hot latency is similar to dashboard, which is acceptable
- structural risk is higher than current hot timing suggests

### 7. Manual location and timezone resolution can repeat across layers

Evidence:

- `_data_for_request_clock_context` resolves coordinates and timezone in `2963-3001`
- `_build_dashboard_payload` may again call `_ensure_coords_for_location` and `_tz_instance().get_timezone_for_location` while building cusp aspects in `1905-1935`
- `_resolve_timezone_for_context` can trigger both coordinate resolution and timezone lookup in `2161-2184`
- `_ensure_coords_for_location` may geocode again in `2235-2256`

Risk:

- duplicate lookup work
- extra variability in manual mode or ad hoc analysis mode

Observed effect:

- manual dashboard path is slightly slower and more variable than the warm current route

### 8. Timezone lookup path is noisy and not obviously cached

Evidence:

- `safe_geocode` uses an LRU-style cache in `backend/horary_engine/services/geolocation.py:32-87`
- `TimezoneManager.get_timezone_for_location` has extensive INFO logging in `195-240`
- no per-coordinate cache is visible in the timezone manager path

Risk:

- repeated timezone calls do more work than necessary
- logs are much louder than a hot path should be

### 9. Runtime debug printing is active in hot execution paths

Evidence:

- unconditional startup and evaluation prints in `backend/horary_engine/engine.py:32-43`, `266-312`, `7911-7945`
- reception debug prints in `backend/horary_engine/reception.py:180-255`
- more perfection-core prints in `backend/horary_engine/perfection_core.py:179-220`, `250-394`, `1392-1439`

Observed effect:

- request timing runs produced large volumes of stdout noise even with Python logging disabled

Risk:

- noisy production logs
- wasted I/O
- harder to profile and harder to inspect real failures

This is one of the clearest plumbing issues in the current backend.

### 10. `/transits/window` computes primary-direction windows twice

Evidence:

- first computation block in `backend/astro_clock_api.py:4681-4700`
- second computation block in `4708-4729`

Risk:

- guaranteed duplicate work on every transits-window request
- easy defect to remove

This was outside the main Astro Clock scope, but it is a clear hot-path issue in an adjacent backend route.

## Negative findings

These are useful because they narrow where the real cost is not.

- `compute_metrics(...)` is not the main problem. It measured at about 1.2 ms in the instrumented path.
- `forensic` is not currently slower than `dashboard` in the steady state. Its main issue is orchestration complexity, not raw latency.
- `synastry` is not always slow. It is mainly a cold-start and recomputation problem.

## Recommended hardening order

### Phase A - remove obvious wasted work

1. remove unconditional debug `print(...)` traffic from horary/reception/perfection hot paths
2. remove duplicate primary-direction computation in `/transits/window`
3. cache or singleton-load the trait catalog instead of reloading it per request

### Phase B - reduce redundant orchestration

1. refactor trait profile to reuse dashboard metrics instead of recomputing them
2. make house influence and trait inputs a single derived object rather than layered recalculations
3. reduce repeated location/timezone resolution across context and dashboard builder

### Phase C - fix scaling surfaces

1. replace JSON-file snap lookups with an indexed in-memory cache or lightweight database
2. add a chart-bundle reuse strategy for synastry and other snap-driven routes
3. add coordinate/timezone caching at the timezone manager layer, not just the geocoder layer

### Phase D - structural cleanup

1. split forensic route orchestration into:
   - chart preparation
   - feature extraction
   - knowledge evaluation
   - enrichment
   - response shaping
2. document which Astro Clock routes are baseline chart routes and which are derived-analysis routes
3. reassess whether the single engine lock is too coarse once redundant work is removed

## Bottom line

Current backend behavior is functionally coherent, but it has clear performance and plumbing debt:

- Astro Clock itself is fast for `/current`
- dashboard is the main shared heavy path
- trait profile is the most obviously over-stacked route
- forensic is structurally complex but not yet the worst hot-latency route
- synastry has a cold-start spike and avoidable snap-storage overhead
- debug printing in the horary stack is a real production-quality issue

The first changes should target wasted work and noisy plumbing before any deeper algorithm refactor.

## Implemented follow-up

The first hardening pass was applied after this audit.

Implemented:

- gated legacy stdout debug traces in `backend/horary_engine/engine.py`, `backend/horary_engine/reception.py`, `backend/question_analyzer.py`, and `backend/taxonomy.py`
- removed the duplicated primary-direction derivation path inside transits routes and replaced repeated ad hoc blocks with shared helpers plus a small in-process PD window cache in `backend/astro_clock_api.py`
- cached trait catalog loads in `backend/traits/engine.py`
- made `traits/profile` reuse dashboard metrics when the dashboard path has already computed them

Verification after the pass:

- targeted compile and regression tests passed
- a direct `traits/profile` request with stdout/stderr capture dropped from noisy debug output to `captured_stdout_chars = 0`
- a post-fix timing probe measured:
  - `traits/profile` hot average around `1052 ms` on the current local environment
  - `transits/window` hot average around `770 ms`

The second pass then addressed the main remaining `traits/profile` bottleneck directly.

Implemented:

- removed the route's dependency on `_build_dashboard_payload()` entirely
- switched `traits/profile` to a lightweight chart snapshot built from the current chart bundle plus cheap runtime fields
- stopped computing expensive dashboard extras for the trait path (fixed stars, cusp aspects, Morin aspect/pattern payloads, Arabic parts)
- added a singleton `TraitEngine` instance so repeated requests do not re-instantiate the engine on every call
- added a regression test proving `traits/profile` still succeeds even if `_build_dashboard_payload()` is forced to fail

Verification after the second pass:

- compile and regression tests still passed
- a direct `traits/profile` timing probe measured a hot average around `229 ms` on the same local environment

Net effect:

- `traits/profile` is no longer structurally layered on top of dashboard work
- the remaining user-visible cost is now mostly chart generation plus metric / house-influence work, not dashboard assembly

What remains open:

- routine INFO-level logging is still chatty in geolocation / Astro Clock chart generation and could be reduced separately
- `synastry` cold-start recomputation and `forensic` route structure remain audit findings, not yet refactored in this pass
