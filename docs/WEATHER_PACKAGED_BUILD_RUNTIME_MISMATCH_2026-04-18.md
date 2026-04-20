# Weather Packaged Build Runtime Mismatch

Date: 2026-04-18

## Summary

The weather-module "internal" failure was traced to the packaged runtime path, not the current source weather logic.

The important distinction is:

- source development uses the repository backend directly
- packaged Electron builds launch the bundled backend executable under `resources/backend/runtime/horary_backend/horary_backend.exe`

That means a packaged weather failure can be caused by an older backend bundle even when the source tree is already fixed.

## Root Cause

The historical failure mode in the packaged backend was an async scan-session serialization error.

Observed backend error:

- `cannot pickle '_thread._ThreadHandle' object`

Failure shape:

1. Weather scan start created a background thread and stored it in session state.
2. A progress or result snapshot deep-copied that session.
3. The live thread object was not deepcopy-safe.
4. The backend returned a `500`, which surfaced in the UI as a generic internal error.

This was the same class of problem already observed in scan-session handling for other async Astro Clock surfaces.

## Why The Packaged App Matters

Electron does not launch the source backend during normal packaged use.

The app startup path in [main.js](</C:/Users/sabaa/Downloads/codexhorary/frontend/main.js:312>) resolves the backend command in this order:

1. `resources/backend/runtime/horary_backend/horary_backend.exe`
2. legacy packaged fallback locations
3. source `backend/app.py` only as a development fallback

So if a user reports that weather fails only in the installed build, the first suspect is the bundled backend runtime, not the current source module.

## Packaging Flow

The packaging chain is:

1. [build_backend.py](</C:/Users/sabaa/Downloads/codexhorary/backend/build_backend.py:1>) builds the standalone backend runtime bundle with PyInstaller
2. [prepare-backend.js](</C:/Users/sabaa/Downloads/codexhorary/frontend/scripts/prepare-backend.js:221>) copies backend source and runtime into `frontend/backend`
3. Electron Builder packages `frontend/backend` as `extraResources` from [package.json](</C:/Users/sabaa/Downloads/codexhorary/frontend/package.json:69>)

This means stale packaged behavior can come from:

- building before the source fix existed
- reusing an older copied backend inside `frontend/backend`
- file-locking during packaging that preserved older runtime artifacts

## Changes Made

### 1. Added backend build metadata

Added [build_metadata.py](</C:/Users/sabaa/Downloads/codexhorary/backend/build_metadata.py:1>) so the backend can report:

- build timestamp
- runtime kind
- builder Python version
- builder platform
- git branch and commit when available

### 2. Embedded metadata into packaged backend builds

[build_backend.py](</C:/Users/sabaa/Downloads/codexhorary/backend/build_backend.py:1>) now writes `build_metadata.json` before the PyInstaller build and includes it in the runtime bundle.

### 3. Exposed runtime metadata from the API

[app.py](</C:/Users/sabaa/Downloads/codexhorary/backend/app.py:145>) now exposes `backend_build` from:

- `/api/version`
- `/api/health`

This makes it possible to confirm whether a packaged app is running the expected backend bundle without guessing.

### 4. Locked the old weather failure with a regression test

[test_astro_clock_api_weather.py](</C:/Users/sabaa/Downloads/codexhorary/backend/test_astro_clock_api_weather.py:1>) now includes a weather scan-start regression test for the old uncopyable-thread failure mode.

## How To Verify A Packaged Weather Build

Use this workflow when a packaged app reports a weather-only internal error:

1. Start the packaged app.
2. Query `/api/version` from the bundled backend.
3. Inspect `backend_build` in the JSON response.
4. Compare:
   - `backend_build.built_at_utc`
   - `backend_build.git.short_commit`
   - `app_version`
   - `api_version`
5. If those do not match the expected source state, rebuild the installer.

## Expected Outcome After This Change

When a future build-only weather regression is reported, we should be able to answer two questions immediately:

1. Is the packaged app running the backend bundle we expect?
2. Is the failure coming from current source or from an older packaged runtime?

That removes the ambiguity that previously made packaged weather failures look like frontend or live-source bugs.
