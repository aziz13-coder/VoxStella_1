# App Review And Fixes

Date: 2026-04-02

## Scope

This pass reviewed the desktop app as a source tree, with emphasis on:

1. End-to-end app workflow
2. User-visible feature surface
3. Privacy and logging behavior in packaged runs
4. Version/reporting consistency
5. Licensing and settings behavior in the horary flow

Only source files were changed:

- `backend/**`
- `frontend/src/**`
- `frontend/main.js`
- `docs/**`

No packaged artifacts were edited.

## Architecture And Workflow

The app is an Electron desktop shell over a local Flask backend.

- Electron main process:
  - starts the packaged or local backend
  - exposes updater, licensing, and external-link actions to the renderer
  - manages packaged-vs-dev runtime behavior
- React renderer:
  - hosts the main app shell, horary casting flow, saved chart views, settings, notebook, and AstroClock entry points
  - calls the local backend over `window.API_BASE_URL`
- Flask backend:
  - calculates horary charts
  - resolves timezone/current-time helpers
  - exposes health, metrics, and version endpoints
  - enforces packaged-license requirements

The primary user workflows are:

1. Open app
2. Electron starts the backend and the renderer probes `/api/health`
3. User casts a horary chart from the main form
4. Renderer submits to `/api/calculate-chart` or uses explicit demo mode when offline
5. Result is saved into local chart history and opened in chart view
6. User can continue in timeline, notebook, settings, or AstroClock

AstroClock is a second analysis workspace layered on the same shell. It supports realtime/manual chart state, transits, receptions, planetary hours, trait/research tooling, and election-style analysis workflows.

## Feature Surface

The app currently presents these major feature areas:

- Horary chart casting with question, location, date/time, timezone, and advanced override options
- Saved chart history and chart-detail review
- Notebook/timeline style follow-up workflow
- Settings for licensing, API/backend status, updater status, and app metadata
- AstroClock workspace for:
  - realtime or manual chart snapshots
  - transits and planetary condition views
  - research/forensic style supporting tools
  - trait and event-analysis workflows

## Findings Resolved

### 1. Sensitive horary inputs were being persisted to packaged logs

Problem:

- The backend logged raw question/location/date/time/timezone values for chart requests.
- Electron mirrored backend stdout/stderr into `backend.log` in packaged runs, which persisted those inputs to disk.

Fix:

- Backend request logging now records a redacted summary only:
  - question length
  - location length
  - whether date/time/timezone/manual houses were supplied
- Timezone/current-time logging now uses the same redacted style.
- Electron now disables stdout/stderr file capture in packaged runs by default.
- File capture remains available only when explicitly enabled with `VOX_STELLA_CAPTURE_BACKEND_STDIO=1`.

Files:

- `backend/app.py`
- `frontend/main.js`

### 2. Version reporting was inconsistent across package, UI, and backend

Problem:

- The packaged app version and updater version were `1.4.10`.
- The UI About surface hardcoded `2.0.0 Enhanced`.
- The backend `/api/version` response also hardcoded `2.0.0`.

Fix:

- Renderer now shows app version from the packaged frontend metadata.
- Electron passes the packaged app version to the backend through `VOX_STELLA_APP_VERSION`.
- Backend version/health/error metadata now use shared constants instead of scattered string literals.
- `/api/version` now clearly reports:
  - `app_version`
  - `api_version`
  - `engine_version`
  - `release_date`

Files:

- `frontend/src/App.jsx`
- `frontend/main.js`
- `backend/app.py`
- `backend/test_app_metadata_contract.py`

### 3. Packaged unlicensed users could complete the full horary form and only fail on submit

Problem:

- The main horary casting view was not using the license state to gate submission up front.
- In packaged unlicensed runs, users hit a token error only after filling the entire form.

Fix:

- Added a dedicated license-flow helper for horary submission state.
- The casting screen now detects packaged unlicensed runtime before submit.
- The screen shows a direct activation message and routes users to Settings or the product page instead of failing late.
- Submit-button disabled state and error messaging now use the same shared logic.

Files:

- `frontend/src/utils/licenseFlow.mjs`
- `frontend/src/tests/licenseFlow.test.mjs`
- `frontend/src/App.jsx`

### 4. Settings surfaced decorative metadata rather than actual state

Problem:

- Settings implied more configurable state than was actually wired.
- The visible theme-color control did not persist or affect runtime behavior.
- About/API status text mixed app version and engine metadata.

Fix:

- Removed the visible placeholder theme-color selector from the active settings surface.
- Settings/About now separate app version from backend API version and engine version.
- Demo chart metadata also avoids reporting a fake backend version.

Files:

- `frontend/src/App.jsx`

## Verification

Frontend:

- `npm test` passed
- `npm run lint` passed

Backend:

- `python -m pytest backend/test_app_metadata_contract.py backend/test_license_workflow_contract.py backend/test_trait_engine_contract.py backend/test_event_keywords_helper.py -q` passed
- Result: `24 passed, 1 warning`
- Observed warning:
  - `pytz` emits a `datetime.utcfromtimestamp()` deprecation warning from an installed dependency path

## Remaining Notes

- `frontend/src/App.jsx` remains a very large shell component and is still the main maintainability risk.
- The backend still exposes separate concepts for app version and engine/API version, which is now explicit, but future release process changes should keep those values intentionally managed together.
