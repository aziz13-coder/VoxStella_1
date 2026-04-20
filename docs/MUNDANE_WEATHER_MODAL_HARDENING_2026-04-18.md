# Mundane And Weather Modal Hardening

Date: 2026-04-18

## Scope

This pass resolved four workflow bugs in the Astro Clock mundane and weather modals:

1. Polity changes could keep the previous capital and timezone in mundane analysis.
2. Resolve and analyze requests could render stale results after the form changed.
3. Mundane scan controls could be edited mid-run, which dropped UI tracking for the active session.
4. Weather analysis and scan flows had the same stale-response and orphaned-session problems.

All changes were made in source files only:

- `frontend/src/features/astroclock/MundaneWorkspace.jsx`
- `frontend/src/features/astroclock/MundaneScanWorkspace.jsx`
- `frontend/src/features/astroclock/WeatherWorkspace.jsx`
- `frontend/src/tests/mundaneWeatherWorkspace.test.jsx`

## Fixes

### Mundane analysis defaults

`MundaneWorkspace` now distinguishes between auto-seeded and user-entered values for `referenceLocation` and `eventTimezone`.

- When the selected polity changes, auto-seeded values update to the new polity defaults.
- When the user types a custom location or timezone, that field becomes manual and is no longer overwritten by later polity changes.
- Clearing a manual field returns it to auto mode.

This removes the wrong-country failure mode while preserving legitimate manual overrides.

### Stale async responses

`MundaneWorkspace` and `WeatherWorkspace` now bind resolve and analyze responses to the exact form state that launched the request.

- Each request captures a signature of the current payload.
- The component keeps the latest signature in a ref.
- When a response returns, it is ignored unless its signature still matches the current form state and it is still the latest request.

This prevents slow responses from repainting the modal with outdated context or analysis after the user has already changed chart type, polity, domain, weather family, or overrides.

### Scan session safety

`MundaneScanWorkspace` and the weather scan mode inside `WeatherWorkspace` now disable the mutable scan controls while a scan is running.

- Users can still watch progress and results.
- Inputs that would reset `sessionId`, `progress`, or `result` are no longer editable mid-run.
- Reset and rerun remain blocked until the active scan finishes.

This keeps the frontend attached to the backend session for the full run instead of orphaning the job from the modal.

## Test Coverage

Added focused frontend coverage in `frontend/src/tests/mundaneWeatherWorkspace.test.jsx` for:

1. Mundane auto-seeded polity defaults updating on polity change.
2. Mundane stale analysis responses being ignored after form edits.
3. Mundane scan controls locking during an active session.
4. Weather stale analysis responses being ignored after family changes.
5. Weather scan controls locking during an active session.

## Verification

Executed:

- `python -m pytest backend/test_astro_clock_api_mundane.py backend/test_astro_clock_api_weather.py -q`
- `npm run test:ui -- --run src/tests/mundaneWeatherWorkspace.test.jsx`

Expected result after this pass:

- Backend mundane and weather API tests pass.
- The targeted frontend modal-hardening test file passes.
