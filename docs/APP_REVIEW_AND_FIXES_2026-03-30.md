# App Review And Fixes

Date: 2026-03-30

## Scope

This pass reviewed the main Vox Stella application flow, the horary chart casting path, the Astro Clock realtime and research workflows, and the licensing/settings surface.

Only source files were changed:

- `frontend/src/**`
- `docs/**`

No packaged artifacts were edited.

## Workflow Summary

The current application flow is:

1. Dashboard entry point
2. Cast Chart form for horary questions
3. Chart View for the active reading
4. Timeline and Notebook for saved work
5. Settings for API status, licensing, and updates
6. Astro Clock as a separate live/manual analysis workspace

The app runs as an Electron shell over a local backend. The renderer talks to the local API for chart calculation, Astro Clock dashboards, and research-mode jobs. Licensing also flows through Electron APIs in packaged builds, with a source-run development bypass for local development.

## Findings Fixed

### 1. Chart submission no longer saves fake demo charts on connected-backend failures

Problem:

- When the UI believed the backend was connected, a failed `calculate-chart` request could still fall back to a randomly generated demo chart.
- That silently polluted real user chart history with fake data.

Fix:

- Demo chart generation now happens only when the app is explicitly offline / disconnected.
- Connected-mode failures now show a submission error and do not save a chart.

Files:

- `frontend/src/App.jsx`

### 2. Stored chart history is resilient to malformed rows

Problem:

- A single malformed saved timestamp could break `getCharts()` and hide the entire saved history.

Fix:

- Added chart hydration logic that skips malformed rows instead of failing the whole list.
- Derived fields like `confidence`, `timestamp`, and `date` are normalized in one place.

Files:

- `frontend/src/utils/chartStorage.mjs`
- `frontend/src/App.jsx`

### 3. Astro Clock no longer double-polls in realtime fallback mode

Problem:

- When SSE was unavailable, the Astro Clock realtime view ran both the 10-second fallback poll and a separate 30-second dashboard refresh loop.
- That duplicated requests and could race updates.

Fix:

- Removed the extra realtime refresh loop and kept the single fallback polling path.

Files:

- `frontend/src/features/astroclock/AstroClock.jsx`

### 4. Research compile polling now supports timeout and cancellation cleanly

Problem:

- Research Mode could poll forever if compilation stalled.
- There was no dedicated polling helper, no hard timeout, and weak guardrails around cancellation/unmount.

Fix:

- Added a reusable polling helper with timeout support.
- Added active-run tracking in `ResearchMode` so stopped or unmounted runs do not keep mutating state.
- Tightened the polling helper so it does not perform an extra backend poll after the timeout has already expired.

Files:

- `frontend/src/features/astroclock/researchPolling.mjs`
- `frontend/src/features/astroclock/ResearchMode.jsx`

### 5. Licensing verification UI was extracted into a focused component

Problem:

- The license verification test imported and rendered the full monolithic `App.jsx`.
- That made the test slow, brittle, and previously caused collection/runtime hangs.

Fix:

- Extracted the license activation panel into a dedicated component.
- Updated Settings to render that component directly.
- Rewrote the verification test to target the dedicated component instead of the entire app shell.

Files:

- `frontend/src/components/LicenseActivationSection.jsx`
- `frontend/src/App.jsx`
- `frontend/src/tests/verification.test.jsx`

## Test Coverage Added Or Updated

- `frontend/src/tests/chartStorage.test.mjs`
- `frontend/src/tests/researchPolling.test.mjs`
- `frontend/src/tests/verification.test.jsx`

## Verification

Frontend:

- `npm run test:unit` passed
- `npm run test:ui` passed
- Targeted vitest run for the new/changed coverage passed

Backend:

- `python -m pytest` is not fully green in the current repo state
- Current unrelated failure:
  - `backend/test_trait_engine_contract.py::test_top_traits_diversify_summary_buckets_before_reusing_one_bucket`
  - expected summary bucket: `character`
  - actual summary bucket: `drive`

This backend failure was observed during verification but was not introduced by the frontend/source changes above.

## Remaining Notes

- `frontend/src/App.jsx` is still very large and contains multiple major UI surfaces. The licensing extraction improves one seam, but the file remains a maintenance risk.
- There is still duplicated license-token logic between the main app shell and the Astro Clock API client. That was not changed in this pass.
