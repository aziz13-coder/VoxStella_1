# AstroClock Solar Condition Workflow Resolution - 2026-05-16

## Active workflow

AstroClock solar condition data reaches the UI through this source path:

1. `frontend/src/features/astroclock/AstroClock.jsx` asks `AstroClockAPI.getDashboard()`.
2. `backend/astro_clock_api.py` serves `/api/astro-clock/dashboard`.
3. `_data_for_request_clock_context()` or `_data_for_payload_clock_context()` resolves the requested mode, datetime, location, timezone, coordinates, and house system.
4. `AstroClockEngine.get_current_data()` calls the horary engine.
5. `EnhancedTraditionalHoraryJudgmentEngine.judge_question()` builds a `HoraryChart`, computes `chart.solar_analyses`, and precomputes per-planet derived state.
6. `serialize_chart_for_frontend()` emits per-planet `solar_condition` plus `solar_conditions_summary`.
7. `_build_dashboard_payload()` and `_solar_conditions_from_chart()` normalize the compact dashboard payload.
8. `buildSolarConditionEntries()` maps either traditional dashboard solar rows or Morin combustion rows for the AstroClock tile.

## Solar systems involved

- Enhanced horary solar analysis: cazimi, combustion, under beams, free of Sun, including exact cazimi and traditional exception metadata.
- Dashboard summary: compact grouped data used by AstroClock, metrics, traits, and downstream tiles.
- Per-planet serialization: full planet rows with individual `solar_condition`.
- Morin combustion overlay: optional UI mode with independent `morin_combustion` rows.
- Override workflow: `ignore_combustion=True` suppresses penalties but should still report that the factor was present and ignored.

## Issues resolved

- Planet positions did not receive the computed `SolarAnalysis` object. Engine rules that looked at `position.solar_condition` missed combustion/cazimi states even though `chart.solar_analyses` existed.
- Several engine checks compared `SolarCondition` enums to literal strings such as `"Combustion"`, so they still failed after attaching the analysis object.
- `solar_conditions_summary` dropped `traditional_exception` for under-beams planets, while per-planet serialization kept it. Dashboard consumers that prefer the summary could lose the exception.
- Deserialized charts rebuilt `chart.solar_analyses` but did not reattach each analysis to the corresponding `PlanetPosition`.
- Manual/realtime AstroClock context resolution geocoded a changed location before honoring a valid explicit timezone, blocking the horary engine from resolving coordinates later.
- `ignore_combustion=True` suppressed combustion and under-beams counts before the ignored-factor summary was built, making the ignored-note path unreachable.
- The Morin solar tile included every free planet as an empty-label row instead of showing an empty state when there were no active solar afflictions.

## Fixes applied

- Added robust solar-condition normalization in the horary engine and replaced string-only condition checks with enum-aware checks.
- `_precompute_planet_state()` now attaches `solar_condition` alongside `visibility`.
- Serialization now preserves under-beams `traditional_exception` in the summary and reattaches deserialized analyses to planet positions.
- AstroClock request/mode context now treats a valid explicit timezone as enough context to defer location geocoding to the horary engine.
- Ignored combustion and under-beams are tracked separately from effective penalty counts, so suppressed conditions remain visible in analysis output.
- Moved the AstroClock solar row mapper into `frontend/src/features/astroclock/solarConditions.mjs` and filters Morin `free` statuses before rendering.
- Mirrored backend source fixes under `frontend/backend/**`; packaged/generated directories were not edited.

## Regression coverage

- `backend/test_solar_condition_workflow.py`
- `frontend/backend/test_solar_condition_workflow.py`
- `frontend/src/tests/astroClockSolarConditions.test.mjs`
- Existing manual-mode valid-timezone regression in `test_astro_clock_extra_tiles.py`

## Verification run

- `python -m pytest backend/test_solar_condition_workflow.py backend/test_astro_clock_extra_tiles.py::test_manual_mode_with_valid_timezone_defers_location_resolution_to_engine -q`
- `python -m pytest frontend/backend/test_solar_condition_workflow.py frontend/backend/test_astro_clock_extra_tiles.py::test_manual_mode_with_valid_timezone_defers_location_resolution_to_engine -q`
- `npm run test:ui -- astroClockSolarConditions.test.mjs`
