# AstroClock Forensic Review Fixes - 2026-04-24

## Scope

This note documents the forensic workflow fixes applied after review of the AstroClock forensic feature.

## Fixed Findings

- Exact chart coordinates are now preserved when `AstroClockAPI.getForensic()` builds the `/api/astro-clock/forensic` query. Manual charts, loaded snaps, and custom-coordinate charts now pass `latitude` and `longitude` through the same clock-context helper used by dashboard and trait requests.
- The live forensic route now builds dashboard data with modern chart extension enabled and merges `planetary_aspects_precise` into `all_aspects` before feature extraction. This keeps Uranus, Neptune, and Pluto available to production forensic rules and normalizes precise aspect `phase` into `applying`.
- Abduction origins are validated before chart context resolution. Malformed or out-of-range `origin=lat,lon` values return `400` with `Invalid origin coordinates`; non-validation abduction map failures now return an explicit `abduction_map_error` instead of a silent missing map.
- Relationship-link scoring is centralized in `scoreForensicRelationshipLink()`. The visible UI and copied forensic brief now use the same weights for house crossover, rulership, reception, aspect, fixed-star, light-mediation, and degree signals.

## Source Paths

- `frontend/src/features/astroclock/api.mjs`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/forensicRelationshipLink.mjs`
- `backend/astro_clock_api.py`
- `backend/forensic/features.py`
- `frontend/backend/astro_clock_api.py`
- `frontend/backend/forensic/features.py`

## Regression Coverage

- Frontend API serialization now asserts forensic requests include explicit coordinates.
- Relationship helper tests cover the shared scoring rubric and guard against the previous critical-house overcount.
- Backend route tests cover early invalid abduction-origin rejection, modern precise-aspect merging, and live modern planet/aspect presence.
- Feature extraction tests cover precise aspect `phase=applying`.
