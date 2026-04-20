# Forensic Feature Fixes - 2026-03-22

## Scope

Follow-up implementation after the current-state forensic audit in [FORENSIC_FEATURE_AUDIT_2026-03-22.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_FEATURE_AUDIT_2026-03-22.md).

Goal:

- move forensic onto the shared Astro Clock request-context path
- pass timezone and house-system context end to end
- reconcile the backend route with the shared request-context resolver
- add route and overlay regression coverage

## Changes Made

### 1. Forensic overlay now waits for the pause snapshot before opening

- File:
  - [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx)
- Change:
  - `handleOpenForensic` now awaits `pauseRealtimeForFeature()` before showing the forensic overlay.
- Why:
  - prevents the first forensic fetch from racing against a moving realtime chart
  - aligns forensic open behavior with the safer modal sequencing already used by Trait Profile

### 2. Forensic frontend now uses the shared Astro Clock clock context

- File:
  - [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx)
- Change:
  - parent Astro Clock now passes `clockContext={buildClockContext()}`
  - `ForensicDashboard` consumes that shared context instead of hand-building a smaller request
- Why:
  - keeps forensic in sync with manual/realtime scoping fixes already made elsewhere in Astro Clock

### 3. Forensic requests now carry timezone and house-system context

- Files:
  - [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx)
  - [api.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/api.mjs)
- Change:
  - forensic fetches now inherit full shared chart context, including `timezone` and `houseSystem`
  - `AstroClockAPI.getForensic(...)` now emits `house_system_code`
- Why:
  - reduces drift between the visible Astro Clock chart and the forensic route inputs

### 4. Backend forensic route now uses the shared request-context resolver

- File:
  - [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)
- Change:
  - replaced the duplicated forensic override block with `_data_for_request_clock_context(eng)`
  - preserved explicit invalid-mode handling for forensic
- Why:
  - removes duplicated clock-context logic
  - keeps forensic aligned with dashboard and trait profile request resolution

## Tests Added / Updated

### Frontend

- Updated [astroClockModeFlow.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/astroClockModeFlow.test.jsx)
  - now verifies forensic waits for the pause snapshot
  - verifies the forensic request carries:
    - `mode`
    - `datetime`
    - `location`
    - `timezone`
    - `houseSystem`

- Updated [astroclockApi.test.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/astroclockApi.test.mjs)
  - added forensic API contract coverage for:
    - `timezone`
    - `house_system_code`
    - abduction extras

### Backend

- Added [test_forensic_route_contract.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_route_contract.py)
  - verifies `/api/astro-clock/forensic` uses the shared request-context resolver
  - verifies invalid `mode` still returns `400`

## Verification

### Frontend

- Command:
  - `cmd /c npx vitest run src/tests/astroclockApi.test.mjs src/tests/astroClockModeFlow.test.jsx --config vitest.config.mjs`
- Result:
  - `11 passed`

### Backend

- Command:
  - `& '.\backend\venv\bin\python' -m unittest tests.test_forensic_route_contract -v`
- Result:
  - completed successfully with exit code `0`

- Command:
  - `& '.\backend\venv\bin\python' -m pytest tests/test_forensic_features.py -q`
- Result:
  - completed successfully with exit code `0`

- Command:
  - `python -m py_compile backend\astro_clock_api.py`
- Result:
  - passed

## Remaining Notes

- The forensic route still returns a top-level payload instead of the common `{ success, data }` wrapper.
- The forensic UI is still embedded inside the large Astro Clock component, which keeps regression risk higher than it should be.
- Those are still valid cleanup targets, but the main context-drift issues are now fixed at the shared integration layer.
