# Astro Clock Trait Profile Workflow Audit

Date: 2026-03-29

## Scope

This audit covers the Trait Profile feature in Astro Clock across:

- frontend workflow
- backend route workflow
- trait engine workflow
- data dependencies
- current correctness and reliability risks

This is a workflow/code audit, not yet a full source-validation pass on the trait rules themselves.

## Entry Points

Primary source files:

- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/TraitProfileModal.jsx`
- `frontend/src/features/astroclock/api.mjs`
- `backend/astro_clock_api.py`
- `backend/traits/engine.py`
- `backend/traits/traits.json`
- `backend/traits/catalog/**`

Packaged-source twin:

- `frontend/backend/traits/engine.py`
- `frontend/backend/traits/catalog/**`

## Frontend Workflow

### Launch path

The feature is launched from Astro Clock via the `Trait Profile` button in `AstroClock.jsx`.

Current workflow:

1. User clicks `Trait Profile`
2. Astro Clock pauses realtime mode before opening the modal
3. `TraitProfileModal` mounts with:
   - `specialDegrees`
   - mode (`manual` or `realtime`)
   - chart context (`manualIso`, `manualLocation`, `timezone`, `houseSystem`)
   - `chartSnapshot`
   - `fixedStarHits`
4. The modal builds a request context and calls `/api/astro-clock/traits/profile`
5. Returned payload is rendered into:
   - summary
   - positive/negative top split
   - topic maps
   - house influence
   - all traits
6. Closing the modal resumes realtime mode

### Request-building behavior

`TraitProfileModal.jsx` builds clock context through `buildTraitClockContext(...)`.

Manual mode sends:

- `mode=manual`
- `datetime`
- `location`
- `timezone`
- `houseSystem`

Realtime mode sends:

- `mode=realtime`
- `location`
- `timezone`
- `houseSystem`

The request is made through `AstroClockAPI.getTraitProfile(...)` in `api.mjs`.

### UI behavior

The modal is largely a presentation layer over backend data:

- `SummaryBlock` renders:
  - dominant element
  - dominant modality
  - special degrees
  - two flags:
    - `mercury_shock`
    - `neptune_station_or_angular`
- `TopSplit` separates top traits by polarity
- `TopicMapsSection` is frontend-synthesized from house influence data
- `HouseInfluenceSection` renders detailed influence rows and determinator panels
- `AllTraits` groups traits by domain

Important note:

The feature looks backend-rich, but much of the “Morin” display is assembled in the frontend from `house_influences`, not produced as a unified trait judgment by the trait engine itself.

## Backend Route Workflow

Route:

- `GET /api/astro-clock/traits/profile`

Current route flow in `backend/astro_clock_api.py`:

1. Resolve chart context through `_data_for_request_clock_context(...)`
2. Serialize current/request clock state with `_serialize_real_time(...)`
3. Extract chart data with `_extract_chart_data_from_result(...)`
4. Read repeated `special_degree` query params
5. Attempt dashboard payload via `_build_dashboard_payload(...)`
6. Attempt astro metrics via `compute_metrics(...)`
7. Attempt house influence via `compute_house_influences(...)`
8. Attempt sect info via `compute_sect_info(...)`
9. Build `planet_area_scores` from house influence
10. Run `TraitEngine.evaluate(metrics)`
11. Assemble `chart_snapshot`
12. Return JSON with summary, traits, guidance, house influence, and chart snapshot

### Important route characteristic

The route uses broad `try/except Exception` fallback blocks around nearly every computation step.

Effect:

- the endpoint is resilient
- but silent degradation is easy
- frontend can render a “valid” response even when multiple data layers failed

This is the biggest workflow risk in the route.

## Trait Engine Workflow

Engine:

- `backend/traits/engine.py`

### Catalog loading

`_load_traits_catalog(...)` loads traits from:

1. `traits/catalog/**/*.json`
2. `traits.json`

It deduplicates by `id` or `name`, preferring catalog entries over monolithic ones.

This part is robust and has packaged-runtime fallbacks:

- explicit root
- local `backend/traits`
- `cwd/traits`
- `HORARY_BACKEND_DIR/traits`
- `sys._MEIPASS/traits`

### Condition evaluation

The engine supports rules based on:

- element share
- modality share
- sign emphasis
- grouped sign emphasis
- planet status
- planetary aspects
- angle aspects
- house emphasis
- house affliction
- solar conditions
- special degree hits
- planet-area determination scores
- planet in sign/house
- sign relation
- affliction by specific planets
- sect roles
- boolean flags

### Scoring

Per trait:

1. start from `base`
2. add `boosts`
3. add `dampeners` (negative weights)
4. add `escalators`
5. clamp into `0..100`
6. assign band:
   - `strong >= 70`
   - `likely >= 50`
   - `possible >= 30`
   - `weak < 30`

Output includes:

- `score`
- `band`
- `polarity`
- `description`
- `sources`
- `evidence`
- derived `keywords`

The engine summary is currently very small:

- dominant element
- dominant modality
- raw flags

## Data Dependencies

### Present and working

- `backend/traits/catalog/**`
- `backend/traits/traits.json`

### Missing or currently inactive

#### Morin keyword dictionary

The engine attempts to load:

- `backend/traits/knowledge/morin_keywords.json`
- `backend/traits/morin_keywords.json`

Current repo state:

- neither file exists

Observed behavior:

- `_load_morin_keywords_safe()` returns `{}`
- trait-level derived `keywords` become thin or empty

#### Psychology dictionary CSV

The engine attempts to load:

- `backend/Phsychology traits/astrology_dictionary_starter.csv`

Current repo state:

- the directory does not exist

Observed behavior:

- `_load_dictionary_csv()` returns `[]`
- `compute_guidance(metrics)` falls back to the smaller Morin/sect additions only

### Practical consequence

The feature still works, but two advertised enrichment layers are currently degraded:

- trait keyword enrichment
- guidance enrichment

This is a real correctness/quality gap, even though the route does not crash.

## Existing Test Coverage

### Present

- `frontend/src/tests/traitProfileModal.test.jsx`
- one backend passthrough check inside `tests/test_astroclock_internal_chart_passthrough.py`

### Missing before this pass

- dedicated route contract tests for `/api/astro-clock/traits/profile`
- dedicated trait engine fallback tests
- tests around missing enrichment resources

## Findings

### Confirmed workflow strengths

- launch/open/close flow is straightforward
- trait catalog loading is robust
- packaged-source trait catalog pathing is already better than some other features
- frontend is mostly a stable renderer once backend data exists

### Confirmed workflow risks

1. Silent degradation in the route
   - multiple broad fallbacks can hide missing backend computations

2. Missing auxiliary data sources
   - `morin_keywords.json` is absent
   - `astrology_dictionary_starter.csv` is absent

3. Thin backend summary
   - trait summary is too sparse for a feature that presents itself as a synthesized profile

4. Frontend “Morin” presentation is partly assembled from house influence
   - useful, but not the same as a single source-grounded trait judgment engine

5. Backend coverage was too thin
   - one existing passthrough test was not enough for safe iteration

## Recommended Next Steps

Recommended order:

1. Lock route and engine fallback behavior with dedicated tests
2. Decide whether the missing enrichment files should be:
   - restored
   - replaced
   - or removed from the design
3. Audit trait scoring and polarity on a curated subset of traits
4. Do a live packaged-app parity check for:
   - summary
   - keywords
   - guidance
   - house influence rendering

## Step Started In This Pass

This pass starts step 1:

- dedicated route contract tests
- dedicated trait engine fallback tests

No production logic has been changed yet in this audit pass.
