# App Review And Fixes

Date: 2026-04-18

## Scope

This pass documented the latest application review findings and resolved the requested workflow and startup issues in source files only.

Findings addressed:

1. Silent timezone fallback could distort chart calculations
2. `Rerun same chart` did not replay the original resolved inputs
3. Location typing triggered live timezone resolution while the user was still editing
4. Electron startup waited on backend health before any window was shown
5. Astrocartography `General inspection` could not stay selected
6. Astrocartography startup failures looked like an empty workspace
7. Atlas search sessions could outlive the modal and accumulate in memory

Only source files were changed:

- `backend/**`
- `frontend/src/**`
- `frontend/main.js`
- `docs/**`

No packaged artifacts were edited.

## Findings Status

### 1. Silent timezone fallback could distort chart calculations [Resolved]

Problem:

- The chart-casting flow treated timezone detection failure as a recoverable convenience issue.
- When lookup failed, the frontend guessed a broad country timezone and finally defaulted to `America/New_York`.
- In horary work, that can materially alter houses, angles, and the judgment itself.

Fix:

- Removed the silent frontend fallback path.
- Auto-detected timezone mode now resolves through the backend only and treats failure as blocking for custom-time charts.
- If lookup cannot resolve a timezone, the UI now surfaces an explicit unresolved state and requires the user to either select a timezone manually or enter a more specific location.
- Successful detection now stores the resolved timezone, coordinates, and location name so later workflows can reuse the resolved chart context instead of guessing again.

Files:

- `frontend/src/App.jsx`
- `frontend/src/utils/normalizeHoraryApiResult.mjs`
- `frontend/src/utils/horaryReplay.mjs`
- `frontend/src/tests/horaryReplay.test.mjs`

### 2. `Rerun same chart` did not replay the original resolved inputs [Resolved]

Problem:

- The rerun action rebuilt the request from a saved location string, date, time, and timezone.
- That forced the backend to re-resolve the place name instead of replaying the originally resolved chart context.
- Ambiguous locations or changed geocoder results could therefore produce a different chart while overwriting the saved record.

Fix:

- Added a reusable replay-context shape that persists the resolved timezone, coordinates, and location label alongside saved chart data.
- Changed rerun to reconstruct the request from that stored replay context when available.
- Extended `/api/calculate-chart` to accept validated `latitude`, `longitude`, and `locationName` inputs and forward them into the horary engine.
- Charts created after this fix rerun deterministically from the original resolved context. Older saved charts continue to rerun from the best data they already contain.

Files:

- `frontend/src/App.jsx`
- `frontend/src/utils/normalizeHoraryApiResult.mjs`
- `frontend/src/utils/horaryReplay.mjs`
- `frontend/src/tests/horaryReplay.test.mjs`
- `backend/app.py`
- `backend/test_app_metadata_contract.py`

### 3. Location typing triggered live timezone resolution while the user was still editing [Resolved]

Problem:

- The Cast Chart form started timezone lookup on every non-empty location change after a short debounce.
- Because lookup resolves uncached strings through live geocoding, normal typing produced repeated network work against partial place names.
- That made the workflow slower and less reliable than necessary.

Fix:

- Removed the background auto-lookup effect while the user is typing.
- Timezone auto-detection now runs only when the user commits the location flow: on blur, on location suggestion selection, or on submit for custom-time charts.
- Editing the location invalidates stale resolved timezone state so the next lookup must match the final text input.

Files:

- `frontend/src/App.jsx`

### 4. Electron startup waited on backend health before any window was shown [Resolved]

Problem:

- App startup awaited backend health before `BrowserWindow` creation.
- If backend boot was slow, the user saw a blank launch delay instead of a visible shell with a recovering backend.

Fix:

- Changed startup ordering so the backend process is started, IPC handlers are registered, and the window is created immediately.
- Backend health is now checked asynchronously after window creation and logged instead of blocking the initial shell.

Files:

- `frontend/main.js`

### 5. Astrocartography `General inspection` could not stay selected [Resolved]

Problem:

- The goal picker exposed a blank `General inspection` option.
- A follow-up state effect treated the blank value as invalid and immediately rewrote it to the first shipped PathFinder goal.
- That made neutral astrocartography inspection unreachable in practice.

Fix:

- Changed goal-selection recovery so the modal now preserves an intentional blank selection.
- The repair effect only clears truly invalid non-empty goal ids when goal data changes.
- Added inline guidance explaining that `General inspection` keeps the workspace neutral while atlas ranking still requires an explicit PathFinder goal.

Files:

- `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- `frontend/src/tests/astrocartographyModal.test.jsx`

### 6. Astrocartography startup failures looked like an empty workspace [Resolved]

Problem:

- `loadSnaps` and `loadGoals` swallowed request failures.
- When those calls failed, astrocartography degraded to an empty or disabled state with no actionable explanation.
- That was especially misleading in the snap-first setup flow because the modal looked empty rather than broken.

Fix:

- Added dedicated snap-load and goal-load error state in the modal.
- Bootstrap requests now validate their responses, preserve existing data when possible, and surface actionable inline errors when loading fails.
- The preflight snap selector, the workspace snap rail, and the PathFinder goal section now all show the failure instead of silently falling back.

Files:

- `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- `frontend/src/tests/astrocartographyModal.test.jsx`

### 7. Atlas search sessions could outlive the modal and accumulate in memory [Resolved]

Problem:

- Each atlas search created a background session record and worker thread state in the backend.
- Closing the modal or invalidating a run on the frontend only abandoned the polling loop; the backend session kept running and completed sessions stayed resident indefinitely.
- Over longer desktop sessions that could waste CPU and grow memory unnecessarily.

Fix:

- Added an explicit atlas-search cancel endpoint and wired the modal to call it when the user closes the workspace or invalidates an active run.
- Added cooperative cancellation checks inside atlas search orchestration and atlas-city ranking so cancellation stops work promptly instead of waiting for the whole search to finish.
- Added bounded session retention with TTL-based pruning and terminal-session eviction so completed or cancelled atlas runs do not accumulate without limit.

Files:

- `backend/astro_clock_api.py`
- `backend/astrocartography_atlas_engine.py`
- `backend/test_astro_clock_api_astrocartography.py`
- `frontend/src/features/astroclock/api.mjs`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- `frontend/src/tests/astroclockApi.test.mjs`
- `frontend/src/tests/astrocartographyModal.test.jsx`

## Verification

Run after the fixes:

- `npm test` from `frontend/`
- `npm run build` from `frontend/`
- `python -m pytest backend\test_app_metadata_contract.py backend\test_license_workflow_contract.py backend\test_astro_clock_api_transits.py backend\test_astro_clock_api_weather.py`
- `npm run test:ui -- astrocartographyModal.test.jsx astroclockApi.test.mjs`
- `python -m pytest backend\test_astro_clock_api_astrocartography.py`

Results:

- Frontend test suite passed: 37 files, 253 tests
- Backend targeted suite passed: 24 tests
- Production Vite build passed
- Astrocartography frontend regressions passed: 2 files, 26 tests
- Astrocartography backend session suite passed: 5 tests

Notes:

- The production build still reports a large JavaScript bundle warning for the main chunk, so bundle splitting remains a separate performance follow-up.
