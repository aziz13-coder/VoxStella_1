# Lunar Fertility Election Model Plan

Date: 2026-04-22

Scope: add a new Astro Clock Election model based on the Galaxy SkyLiner research note at `C:\Program Files (x86)\Galaxy\docs\research\skyliner_reverse_engineering.md`.

Implementation status: the initial runtime slice is implemented. The scanner, route key, frontend controls, API serialization, and focused tests now exist. Export-specific work and richer reporting remain future work.

Implemented source files:

- `backend/election_models/lunar_fertility.py`
- `frontend/backend/election_models/lunar_fertility.py`
- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`
- `backend/election.py`
- `frontend/backend/election.py`
- `frontend/src/features/astroclock/api.mjs`
- `frontend/src/features/astroclock/ElectionModal.jsx`

## Decision

Add a separate model named:

- UI label: `Lunar Fertility Windows`
- route matter key: `lunar_fertility`
- backend module: `election_models/lunar_fertility.py`

Do not name the new model `Conception`, `Fertility`, `SkyLiner`, `Jonas`, or `Favorable Conception Periods`.

Reason:

- `conception` is already an existing election scorer in this repo.
- `fertility` is currently treated as an alias for the existing conception scorer in `astro_clock_api.py`.
- `SkyLiner` is the Galaxy module name, not the Vox Stella product name.
- `Jonas` describes the source-like technique family, but the UI should use a neutral product name.
- `Favorable conception periods` is the phrasing used by the reference module; using a different name keeps the new model distinct.

## What Was Scanned

Reference material:

- `C:\Program Files (x86)\Galaxy\docs\research\skyliner_reverse_engineering.md`

Current source areas:

- `backend/election.py`
- `backend/election_models/conception.py`
- `backend/astro_clock_api.py`
- `frontend/src/features/astroclock/ElectionModal.jsx`
- `frontend/src/features/astroclock/api.mjs`
- `tests/test_election_workflow_matrix.py`
- `tests/test_election_route_contracts.py`
- `docs/ELECTION_ENGINE_VALIDATION_AUDIT.md`
- `docs/astro_clock/VOX_STELLA_ASTRO_CLOCK_ELECTION_GUIDE.md`

Generated/package artifacts were not edited.

## Existing Conception Model

The current `conception` model is a normal point-in-time election scorer.

Backend:

- `backend/election_models/conception.py`
- exported through `backend/election.py`
- selected in `backend/astro_clock_api.py` when `matter in {"conception", "fertility"}`

Current behavior:

- scores one election chart at a time
- weighs 5th-house conditions, Moon condition, Venus, Jupiter, Ascendant, malefics, and optional natal overlays
- supports an optional `gender` preference
- returns the standard `Score(value, tags, pros, cautions)` shape used by the existing election stream

This model should stay in place. The new model should not be implemented as a small option flag inside `conception.py`.

## New Model Shape

The reference SkyLiner model is not a general chart scorer.

It is a natal Sun-Moon phase recurrence scanner:

1. Read the natal Sun-Moon elongation.
2. Determine whether the natal Moon is on the same cycle branch as the Sun-Moon relation.
3. Search future dates for returns of that same elongation.
4. Optionally include the opposite branch.
5. Expand each anchor into a favorable window.
6. Project the windows onto an hourly grid.
7. Assign each favorable hour:
   - strength
   - phase or antiphase
   - male or female Moon-sign polarity
8. Group contiguous favorable hours into periods.

That means `lunar_fertility` should be implemented as a specialized election scanner, not only as a `score_lunar_fertility_election(chart)` function.

## Naming Boundary

Reserved names:

- `conception`: existing chart scorer
- `fertility`: existing alias to conception route behavior
- `skyliner`: external reference/module name
- `jonas`: technique-family reference, not UI name

New names:

- UI label: `Lunar Fertility Windows`
- request key: `matter=lunar_fertility`
- Python module: `election_models/lunar_fertility.py`
- scorer/adapter function if needed: `score_lunar_fertility_election(...)`
- scanner function: `scan_lunar_fertility_windows(...)`

## Algorithm Contract

Constants from the reference behavior:

- lunar cycle step: `27.321582794` days
- half-cycle step: `13.660791397` days
- anchor search end extension: one lunar cycle beyond visible end
- anchor solver max iterations: `13`
- solver tolerance: `1` arcsecond
- correction divisor: `18.505416991` deg/day, matching Galaxy's Moon max-speed style correction scale
- favorable window: `-12` hours before anchor through `+24` hours after anchor
- output grid: hourly

Phase semantics:

- `phase`: same Sun-Moon elongation on the same waxing/waning branch as natal
- `antiphase`: same elongation on the opposite waxing/waning branch

Do not treat `antiphase` as `180 deg` away. It is branch polarity at the same elongation.

Consider modes:

- `phase`: include only the main phase branch
- `phase_and_antiphase`: include both branches
- `antiphase`: include only the opposite branch

Sex label:

- compute the Moon longitude for each favorable hour
- masculine signs produce `male`
- feminine signs produce `female`

The label is descriptive. It is not the same as the existing conception scorer's `gender` preference.

Strength:

- strength peaks at the anchor
- strength tapers linearly toward the `-12h` and `+24h` window edges
- public row score should use a stable `0..100` value, rounded for display

## Backend Design

Add a new source module:

- `backend/election_models/lunar_fertility.py`
- `frontend/backend/election_models/lunar_fertility.py`

The frontend/backend copy is still a source twin in this repository, so it should remain in sync until packaging sync fully owns that duplication.

Recommended pure functions:

- `extract_natal_lunar_signature(natal_chart_data) -> LunarFertilitySignature`
- `moon_branch_and_elongation(sun_lon, moon_lon) -> tuple[bool, float]`
- `solve_lunar_phase_anchor(jd_ut, target_elongation, ephemeris) -> Anchor`
- `generate_lunar_fertility_anchors(start_dt, end_dt, signature, consider_mode, ephemeris) -> list[Anchor]`
- `project_lunar_fertility_series(start_dt, end_dt, anchors, timezone) -> list[dict]`
- `group_lunar_fertility_periods(series) -> list[dict]`
- `scan_lunar_fertility_windows(...) -> dict`

Use dependency injection for ephemeris calls in tests. The unit tests should not require real Swiss Ephemeris files for every branch test.

### Route Integration

Add `matter=lunar_fertility` handling in:

- `GET /api/astro-clock/election/validate`
- `GET /api/astro-clock/election/suggest/stream`

Validation rules:

- require `start`, `end`, and `location`
- require a natal source:
  - preferred: `natal_snap_id`
  - fallback: `natal_datetime`, `natal_location`, optional `natal_timezone`
- require `consider_mode` to be one of:
  - `phase`
  - `phase_and_antiphase`
  - `antiphase`
- accept `level_percent` as a display/filter threshold, default `33`
- keep existing scan bounds validation

Do not map `matter=fertility` to this model in the first implementation because that would silently change existing conception behavior.

### Stream Shape

The existing SSE endpoint can still be used, but `lunar_fertility` should use a specialized branch rather than the standard per-step `_compute_chart_for -> _scorer` loop.

Terminal payload should include:

- `matter: "lunar_fertility"`
- `top`: strongest favorable hours
- `series`: hourly favorable series, respecting `include_series`
- `periods`: grouped contiguous favorable periods
- `stats`: scan counts
- `location`
- `timezone`

Recommended row fields:

- `timestamp`
- `score`
- `strength`
- `phase_kind`: `phase` or `antiphase`
- `sex_label`: `male` or `female`
- `moon_sign`
- `anchor_timestamp`
- `anchor_offset_hours`
- `period_id`
- `tags`

Suggested tags:

- `Lunar fertility window`
- `Phase` or `Antiphase`
- `Moon in masculine sign` or `Moon in feminine sign`
- `Near anchor` for high-strength rows

## Frontend Design

Update:

- `frontend/src/features/astroclock/ElectionModal.jsx`
- `frontend/src/features/astroclock/api.mjs`

UI additions:

- add model button: `Lunar Fertility Windows`
- require saved snap or manual natal source before scan
- expose `Consider` segmented control:
  - `Phase`
  - `Phase + Antiphase`
  - `Antiphase`
- expose `Level %` numeric input, default `33`
- hide current conception `gender` controls for this model
- show periods table when `result.periods` exists

Result display:

- keep the ranked top list for compatibility
- add a period-focused section for this model:
  - start
  - end
  - peak time
  - peak score
  - sex label
  - phase kind
- timeline points can reuse the existing election series visualization, but rows should show phase and sex labels in detail.

API serialization:

- add `considerMode` -> `consider_mode`
- add `levelPercent` -> `level_percent`
- keep `gender` only for `matter=conception`

## Test Plan

Pure model tests:

- natal phase extraction gets target elongation and branch correctly
- `phase`, `phase_and_antiphase`, and `antiphase` modes select the right branches
- anchor windows expand to `-12h` and `+24h`
- hourly projection produces nonzero rows inside windows and zero outside
- strength peaks at anchor and tapers at borders
- Moon sign polarity maps to `male` and `female`
- grouping splits when phase or sex label changes

Route tests:

- validation rejects `lunar_fertility` without natal source
- validation rejects invalid `consider_mode`
- stream returns `top`, `series`, `periods`, and `stats`
- `matter=fertility` still routes to the existing conception behavior
- `matter=conception` still honors `gender`

Frontend tests:

- API serializer emits `consider_mode` and `level_percent`
- API serializer does not send `gender` for `lunar_fertility`
- Election modal exposes the new model and hides conception-specific controls
- result renderer can show `periods`

Packaging/source tests:

- add the new module to both source trees
- confirm `backend/election.py` exports any public adapter if one is needed
- run existing election route/workflow tests after integration

## Suggested Implementation Order

1. Add pure backend model module with injected ephemeris adapter and unit tests.
2. Add route validation for `matter=lunar_fertility`.
3. Add specialized stream branch returning `top`, `series`, `periods`, and `stats`.
4. Add frontend API params.
5. Add Election modal controls and period rendering.
6. Add route/UI tests.
7. Update user docs after runtime behavior exists.

## Open Implementation Questions

1. Manual natal input: the current modal primarily exposes saved snaps. Decide whether MVP requires saved snap only or also supports manual natal fields.
2. Level behavior: the reference treats `Level (%)` mainly as a visual inspection threshold. Decide whether Vox Stella should use it only for display or also filter periods in the table.
3. Series density: the reference uses hourly points. Decide whether `step_minutes` is ignored, clamped to `60`, or allowed to be denser while periods remain hourly.
4. Ephemeris backend: prefer direct Swiss Ephemeris Sun/Moon calls for speed, but keep a chart-engine fallback for environments where direct calls are unavailable.
5. Export format: first implementation should return structured JSON. The fertility-only PDF-style wrapper is documented below.

## Fertility Reporting Implementation

Status: implemented in the frontend for `matter=lunar_fertility` only.

Scope:

- Do not add report buttons or report payloads to the standard election models.
- Keep `matter=fertility` as the existing conception alias; the new report belongs to `Lunar Fertility Windows`.
- Build the report from the already verified scan payload so report output matches the visible result.

Report shape:

1. Shared header:
   - feature title
   - selected scan period
   - forecast place/timezone/coordinates when available
   - selected natal saved chart details
   - house system
   - consider mode
   - level percent
2. Graphic timeline:
   - bar height = strength
   - color = Moon-sign sex polarity
   - opacity = phase vs antiphase
   - dashed line = selected level
3. Grouped fertility periods:
   - period start/end
   - peak time
   - peak score
   - sex label
   - phase kind
   - peak Moon sign
4. Top timepoints:
   - top ranked hours from the scan payload
5. Full hourly favorable table:
   - every retained nonzero fertility hour
   - strength bar
   - numeric strength
   - sex and phase
   - Moon sign

Wiring:

- `frontend/src/features/astroclock/ElectionModal.jsx` exports `buildLunarFertilityReportHtml(...)`.
- The modal shows `Export Fertility Report` only when the completed result has `matter === "lunar_fertility"`.
- Electron uses the existing `window.electronAPI.exportReport(...)` bridge and now accepts caller-provided save-dialog title/default path.
- Browser/dev fallback opens the printable report, or downloads HTML if a print window is blocked.

## Non-Goals For First Implementation

- Do not replace the existing `conception` scorer.
- Do not reuse the `fertility` alias for the new model.
- Do not implement hidden score blending with the existing conception model.
- Do not copy Galaxy UI labels into the Vox Stella UI.
- Do not change generated Electron or packaged files.
