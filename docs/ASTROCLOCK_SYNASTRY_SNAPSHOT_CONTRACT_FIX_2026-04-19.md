# Astro Clock Synastry Snapshot Contract Fix

Date: 2026-04-19

## Problem

Saved Astro Clock snaps were presented as frozen synastry inputs, but the backend synastry loader rebuilt each chart from `effective_datetime` and `location` instead of using the saved snap chart. That let runtime changes drift the same saved pair across builds or settings changes. The frontend also forwarded the live Astro Clock `houseSystem` into synastry requests, which could silently alter a saved comparison.

## Resolution

- `backend/astro_clock_api.py`
  - `create_snap` now persists a dedicated minimal `chart_snapshot` for synastry.
  - `_synastry_bundle_from_snap_id` now prefers the saved `chart_snapshot`, then falls back to the legacy saved dashboard chart payload, and only recomputes when no saved chart snapshot exists.
  - Explicit `house_system_code` is therefore ignored for saved-snapshot comparisons and only remains relevant for the legacy recompute fallback.
- `frontend/src/features/astroclock/SynastryModal.jsx`
  - Synastry requests no longer forward the live workspace house system.
- `frontend/src/features/astroclock/AstroClock.jsx`
  - The synastry modal is opened without a live house-system override.

## Regression Coverage

- Backend tests lock the persisted snap snapshot path, the legacy dashboard fallback, and the final recompute fallback.
- Frontend tests lock that Synastry no longer serializes `house_system_code` unless a caller explicitly opts into it outside the saved-snap workflow.
