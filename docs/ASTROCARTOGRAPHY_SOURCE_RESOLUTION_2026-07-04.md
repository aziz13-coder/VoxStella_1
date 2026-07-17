# Astrocartography Source Resolution - 2026-07-04

## Scope

This note documents the source-code resolution for the AstroClock astrocartography review. Changes were made only in source paths:

- `backend/**`
- `frontend/backend/**`
- `docs/**`

Packaged artifacts under `frontend/dist-electron/**`, `frontend/backend/build/**`, `frontend/dist/**`, and generated site output were not edited.

## Resolved

### Antimeridian distance handling

Nearest-line scoring now unwraps segment longitudes around the inspected point before projecting to local kilometers. This prevents a line at `179E` and a city at `179W` from being treated as nearly a full world circumference apart.

Regression: `test_nearest_lines_for_point_wraps_antimeridian_distance`.

### Swiss Ephemeris process-global guard

Astrocartography equatorial position reads now use the shared `swisseph_lock` when available. This aligns map and atlas calculations with the rest of the backend paths that guard Swiss Ephemeris process-global state.

### Validation status codes

The shared Astro Clock API error handler now maps `ValueError` to HTTP 400. Normal astrocartography input failures such as missing `target_location`, too few comparison targets, or missing `goal_id` no longer return `500 internal_error`.

Regression: `test_astrocartography_validation_errors_return_400`.

### Relocation-aware atlas prepass

Atlas ranking now defaults to the relocation-aware prepass for goal models that include relocation, modifier, or constraint score components, and for bespoke relocation-aware evaluation strategies. This prevents line-only prefiltering from excluding strong relocated-chart matches before they are scored.

Regression: `test_rank_candidate_pool_for_goal_defaults_to_relocation_prepass_for_relocation_models`.

## Product Contract Notes

The backend still marks `travel_fun` and `travel_relax` active in `place_goal_models.runtime.json`, while the React modal hides those goals from the current PathFinder picker. That is preserved as a product decision rather than changed in this source pass.

## Verification

Run:

```powershell
python -m pytest backend/test_astrocartography_service.py backend/test_astrocartography_goal_engine.py backend/test_astrocartography_atlas_engine.py backend/test_astro_clock_api_astrocartography.py
```

Frontend modal/target smoke:

```powershell
npm run test:ui -- src/tests/astrocartographyTargets.test.mjs src/tests/astrocartographyModal.test.jsx
```
