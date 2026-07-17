# AstroClock Engine Paths Review and Resolution - 2026-05-18

## Scope

This review traced how AstroClock state moves from the desktop UI into the backend engine and back into dashboard/export surfaces. The follow-up fix keeps source edits in the allowed paths only:

- `backend/**`
- `frontend/backend/**`
- `frontend/src/**`
- `tests/**`
- `frontend/src/tests/**`

No packaged artifacts under `frontend/dist-electron/**`, `frontend/backend/build/**`, `frontend/dist/**`, `website/**`, `win-unpacked/**`, `resources/**`, `venv/**`, or `node_modules/**` were edited.

## Runtime Workflow

1. Electron starts the React frontend and points it at the local Flask backend through the app API base URL.
2. `frontend/src/features/astroclock/AstroClock.jsx` owns the active clock mode:
   - realtime uses the backend engine's current clock.
   - manual uses the selected snap or manual datetime/location/timezone.
   - snap-backed manual views hydrate the selected snap into the same clock context shape used by API calls.
3. `frontend/src/features/astroclock/api.mjs` serializes the clock context into query parameters:
   - `mode`
   - `datetime`
   - `location`
   - `timezone`
   - `latitude`
   - `longitude`
   - `house_system_code`
4. `backend/app.py` registers the AstroClock blueprint and license/stream-ticket guards for `/api/astro-clock/*`.
5. `backend/astro_clock_api.py` resolves each request with `_data_for_request_clock_context(eng)` when the route can be chart-context-sensitive.
6. `backend/astro_clock_engine.py` builds the active AstroClock data and delegates chart construction to the horary engine with `include_internal_chart=True` so same-process routes can retain the raw chart object for calculations that need it.
7. Specialized surfaces such as dashboard, receptions, traits, transits, synastry, and astrocartography/pathfinder are route-level projections over that same resolved chart context.

## Resolved Issues

### Receptions route context

Problem: `/api/astro-clock/receptions` used `eng.get_current_data()` directly. If the dashboard ever lacked embedded receptions and the UI fallback called this route, manual and snap views could receive receptions for the backend's global realtime state.

Resolution:

- `backend/astro_clock_api.py` and `frontend/backend/astro_clock_api.py` now resolve receptions through `_data_for_request_clock_context(eng)`.
- `frontend/src/features/astroclock/api.mjs` now allows `AstroClockAPI.getReceptions(opts)` and serializes the full clock context.
- `frontend/src/features/astroclock/ReceptionsTile.jsx` now passes its fallback request context instead of making a context-free request.
- `frontend/src/features/astroclock/AstroClock.jsx` passes `buildAppliedClockContext()` into `ReceptionsTile`.

### Trait profile export completeness

Problem: `/api/astro-clock/traits/profile` built `chart_snapshot` from `_compact_dashboard`, which omitted dashboard-enriched values such as fixed star hits, Morin aspects/patterns, moon timeline, full solar conditions, and dashboard receptions. The frontend export view compensated for some of this, but the backend API was not self-contained.

Resolution:

- Trait profile now builds a dashboard-backed snapshot with `_build_dashboard_payload(..., include_morin=True, special_degrees=...)`.
- `_build_traits_chart_snapshot(...)` accepts the dashboard payload and prefers those enriched values directly.
- The route returns object-shaped `receptions` and `morin_patterns` at the top level, matching the chart snapshot.

### Coordinate-aware helper tests

Problem: the chart bundle helpers had already gained `latitude` and `longitude` support, but several tests still monkeypatched older signatures. This made the tests fail before they could validate the real behavior.

Resolution:

- `tests/test_astroclock_chart_bundle_helpers.py` now accepts the coordinate-aware helper signature.
- Snap context tests include explicit timezone and coordinates, avoiding implicit location fallback behavior.

## Verification

Focused red/green checks were run before and after the fix:

- `python -m pytest tests\test_astroclock_internal_chart_passthrough.py::test_receptions_route_honors_manual_request_context tests\test_astroclock_internal_chart_passthrough.py::test_trait_profile_includes_chart_snapshot_for_ai_exports tests\test_astroclock_chart_bundle_helpers.py -q`
- `npm --prefix frontend run test:ui -- src/tests/astroclockApi.test.mjs src/tests/receptionsTile.test.jsx`

Final targeted AstroClock verification:

- `python -m pytest tests\test_astroclock_adapter_fixes.py tests\test_astroclock_chart_bundle_helpers.py tests\test_astroclock_internal_chart_passthrough.py backend\test_astro_clock_dashboard_geocoding.py -q`
  - Result: `27 passed, 1 warning`
- `npm --prefix frontend run test:ui -- src/tests/astroClockModeFlow.test.jsx src/tests/astroclockApi.test.mjs src/tests/receptionsTile.test.jsx`
  - Result: `92 passed`

The backend source mirror was also checked:

- `cmd /c fc backend\astro_clock_api.py frontend\backend\astro_clock_api.py`
  - Result: `FC: no differences encountered`
