# Astrocartography Feature Spec And Implementation Plan

Date: 2026-03-30

## Scope

This memo turns the Astrocartography research pass into a concrete product and engineering plan for the current Vox Stella codebase.

Primary source inputs:

- `horary_knowledge/astrocartography_knowledge_base/reference/01_core_concepts.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/03_techniques_and_ranges.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/api.mjs`
- `frontend/src/features/astroclock/astroClockViewState.mjs`
- `backend/astro_clock_api.py`
- `backend/app.py`

## Product Decision

The first Astrocartography release should live inside the existing Astro Clock workspace, not as a brand-new top-level shell.

Reasoning:

- `AstroClock.jsx` already hosts advanced chart-analysis tools as focused panels and modals: transits, election, forensic, traits, research.
- `AstroClock.jsx` already bundles `react-leaflet`, `MapContainer`, `Marker`, `Polyline`, `Circle`, and `Polygon`, so the map stack is already present.
- `backend/astro_clock_api.py` already owns reusable natal-context helpers, geocoding, timezone resolution, stateless chart computation, and snapshot handling.
- Keeping Astrocartography under `/api/astro-clock/*` lets it inherit the existing license guard path and frontend request plumbing.

Recommendation:

- UI entry point: add an `Astrocartography` action beside `Transits`, `Election`, and `Forensic` in `frontend/src/features/astroclock/AstroClock.jsx`.
- Backend namespace: add endpoints under `/api/astro-clock/astrocartography/*`.
- If adoption becomes large enough, the feature can be promoted later into its own top-level workspace without changing the core engine contract.

## User Problem

Users need a way to answer location questions with natal data:

- Where are my strongest career lines?
- What city is better for love, home life, writing, or study?
- What lines are close to this city, and how close do they need to be to matter?
- What changes in the relocation chart if I move there?
- Are there crossings or intensified zones near a target place?

This feature should act as a decision-support tool, not a deterministic "best place on Earth" oracle.

## MVP Goals

- Accept precise natal birth data and derive a usable astrocartography map.
- Let the user search a location and inspect the nearest angular lines plus distances.
- Explain nearby lines with corpus-backed interpretation text.
- Show a relocation chart for the inspected city.
- Compare two or more cities side by side.
- Surface nearby crossings/parans when they are relevant to a chosen city.

## Non-Goals For V1

- No global "rank every city in the world" scanner.
- No local-space astrology in the first implementation.
- No full case-study encyclopedia UI.
- No automatic life-outcome guarantees or single-score "destiny" rankings.
- No approximate-birth-time workflow in V1. Astrocartography requires a reliable birth time.

## User-Facing Workflow

### Flow 1: Inspect A City

1. Open Astro Clock.
2. Click `Astrocartography`.
3. Provide natal context:
   - preferred: select an existing natal snap
   - fallback: enter birth date, exact birth time, birthplace, and timezone
4. Search a target city.
5. See:
   - world map with selected planetary/angular lines
   - target marker
   - nearest lines sorted by distance
   - plain-language interpretation blocks
   - nearby crossings/parans if any
   - quick relocation-chart summary

### Flow 2: Compare Cities

1. Start from an established natal context.
2. Add 2-4 candidate cities.
3. Compare each city on:
   - nearest lines
   - exact distance to each line
   - dominant planetary themes
   - relocation chart angle/house highlights
   - nearby crossings/parans

### Flow 3: Explore The Map

1. Toggle planet groups and angle groups.
2. Pan and zoom the map.
3. Click a line or target marker to open the inspector.
4. Optionally promote a clicked city into the comparison set.

## UX Shape

Recommended first-pass UI: one modal/workspace component launched from Astro Clock.

Proposed frontend files:

- `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- `frontend/src/features/astroclock/AstrocartographyMap.jsx`
- `frontend/src/features/astroclock/AstrocartographyInspector.jsx`
- `frontend/src/features/astroclock/astrocartographyTransform.mjs`

Recommended layout:

- Left rail:
  - natal context selector
  - city search
  - body toggles
  - angle toggles
  - radius controls
- Center:
  - leaflet world map
  - line overlays
  - target markers
  - crossing markers
- Right rail:
  - nearest lines
  - interpretation cards
  - relocation-chart summary
  - compare actions

Recommended interaction rules:

- Opening the feature from realtime Astro Clock should pause realtime updates in the same way `Transits`, `Election`, and `Forensic` already do.
- The feature should be snapshot-based once opened. It should not drift with realtime clock ticks while the user is evaluating locations.
- The modal should refuse to run without exact birth time and a resolvable birthplace.

## Core Product Rules

- Default interpretation radius:
  - primary: `300 km`
  - extended: `500 km`
- If a line is beyond `500 km`, do not present it as "nearby".
- Crossings/parans should be shown only when close enough to matter, not as noisy map clutter everywhere.
- Line meaning copy should be concise and goal-aware:
  - career
  - love/partnership
  - home/family
  - study/writing
  - creativity
  - healing/spirituality
- The UI should make it explicit that:
  - lines describe emphasis, not guaranteed outcomes
  - relocation charts add context and can refine or soften a line reading
  - house system matters for the relocation chart summary, but not for the raw angular line geometry

## Backend Architecture

The backend should stay inside the Astro Clock blueprint, but the calculation logic should be extracted into focused modules rather than bloating `backend/astro_clock_api.py`.

Recommended backend files:

- `backend/astrocartography_service.py`
- `backend/astrocartography_interpretation.py`
- `backend/astrocartography_cache.py`
- `backend/tests/test_astrocartography_service.py`

Recommended reuse points in the current code:

- Use `_natal_bundle_from_query(args)` in `backend/astro_clock_api.py` for natal context resolution.
- Use `_compute_chart_bundle_for(...)` for relocation-chart generation.
- Use `_ensure_coords_for_location(...)` and the existing `safe_geocode(...)` flow for target places.
- Use the `raw_chart` bundle payload when available so line generation is based on the richest astronomical data available, not only the flattened frontend serialization.

## API Proposal

### 1. `GET /api/astro-clock/astrocartography/map`

Purpose:

- Return map-ready polyline data for selected bodies and angles.

Accepted natal context:

- `natal_snap_id`
- or `natal_datetime`, `natal_location`, `natal_timezone`

Suggested query params:

- `house_system_code`
- repeated `body`
- repeated `angle`
- `include_modern=1`
- `include_node=1`
- `include_chiron=1`

Response shape:

- `natal`
- `map.lines[]`
- `defaults.primary_radius_km`
- `defaults.extended_radius_km`

### 2. `GET /api/astro-clock/astrocartography/location`

Purpose:

- Resolve one target place and return nearby lines, crossings, and summary interpretation.

Suggested query params:

- natal context
- `target_location`
- optional `goal`
- optional repeated `body`
- optional repeated `angle`

Response shape:

- `target`
- `nearest_lines[]`
- `nearby_crossings[]`
- `interpretation`
- `distance_policy`

### 3. `GET /api/astro-clock/astrocartography/relocation`

Purpose:

- Return a full relocation chart bundle for wheel rendering and summary cards.

Suggested query params:

- natal context
- `target_location`
- `house_system_code`

Response shape:

- `target`
- `relocation.chart_data`
- `relocation.meta`
- `summary`

### 4. `GET /api/astro-clock/astrocartography/compare`

Purpose:

- Compare 2-4 target cities with a normalized scoring and explanation structure.

Suggested query params:

- natal context
- repeated `target_location`
- optional `goal`

Response shape:

- `targets[]`
- `comparison.rows[]`
- `comparison.summary`

## Calculation Strategy

### Natal Context

- Resolve natal context through the existing snap/manual query path.
- Convert the natal chart into a stable internal bundle.
- Cache by a signature built from natal UTC instant, birthplace, and selected object set.

### Line Geometry

For each selected body:

- generate `MC`
- generate `IC`
- generate `AC`
- generate `DC`

Recommended implementation approach:

- use the internal chart bundle plus precise astronomical helpers to derive angularity at the natal instant
- emit map polylines as sampled latitude/longitude points
- store map lines in a GeoJSON-like internal shape even if the frontend receives a lighter custom payload

Pragmatic algorithm notes:

- `MC/IC` lines are straightforward meridian-style solutions and should be implemented first.
- `AC/DC` lines require horizon solutions and should be generated through numerical solving on a longitude grid.
- Start with a stable sampled solution, then optimize; do not over-engineer symbolic exactness before the UI works.

### Distance To A Target

- Resolve target coordinates via existing geocoding infrastructure.
- Compute nearest distance from target point to each sampled polyline.
- Sort by geodesic distance.
- Mark whether the target is inside the primary radius or the extended radius.

### Crossings / Parans

For MVP:

- treat crossings as line-to-line proximity events derived from sampled polylines
- return only crossings that are near the inspected target or requested compare cities
- do not render a full global crossings atlas initially

This keeps the first release useful without making the map unreadable or the payload too large.

### Relocation Chart

This should reuse `_compute_chart_bundle_for(...)`, but it must preserve the natal birth instant exactly.

Implementation rule:

- derive the natal UTC instant once
- convert that same instant into the target location timezone
- pass the target-local timestamp and target location into `_compute_chart_bundle_for(...)`

This preserves astronomical continuity while allowing the relocation chart to produce the correct local angles and houses.

## Runtime Knowledge Packaging

The raw research corpus should not be queried at runtime for every request.

Recommended split:

- keep research and normalized markdown under `horary_knowledge/astrocartography_knowledge_base/`
- generate compact runtime assets under `backend/data/astrocartography/`

Recommended runtime assets:

- `line_interpretations.json`
- `crossing_interpretation_rules.json`
- `goal_modifiers.json`
- `source_attribution.json`

These assets should be derived from the knowledge base, not handwritten ad hoc in UI components.

## Frontend Integration Plan

### API Layer

Extend `frontend/src/features/astroclock/api.mjs` with:

- `getAstrocartographyMap(opts)`
- `getAstrocartographyLocation(opts)`
- `getAstrocartographyRelocation(opts)`
- `getAstrocartographyCompare(opts)`

### Astro Clock Host

Update `frontend/src/features/astroclock/AstroClock.jsx` to:

- add `showAstrocartography`
- add open/close handlers
- pause/restart realtime around the feature just like the other heavy tools
- surface the action button in the existing action row

### UI Components

The modal should manage:

- natal context form
- target city search
- selected bodies
- selected angles
- compare list
- inspector tabs:
  - `Overview`
  - `Relocation`
  - `Compare`

### Reuse

- Reuse the existing map stack already imported in `AstroClock.jsx`.
- Reuse the same styling language as the Astro Clock tool surfaces.
- Reuse existing request staleness patterns from `astroClockViewState.mjs` to avoid stale response application when users change cities rapidly.

## Phased Implementation Plan

### Phase 1: Corpus To Runtime Assets

Deliverables:

- curate runtime JSON assets from the generated knowledge base
- define standardized line labels and interpretation templates
- encode the `300 km` and `500 km` policy centrally

Success criteria:

- one runtime source of truth for line meanings
- no long markdown parsing in request handlers

### Phase 2: Backend Geometry And Inspection

Deliverables:

- `astrocartography_service.py`
- `/map`
- `/location`
- `/relocation`

Success criteria:

- can inspect a single city against a natal chart
- returns stable nearest-line ordering
- relocation chart preserves natal planetary positions while changing angular and house context

### Phase 3: Frontend Modal And Map

Deliverables:

- Astrocartography modal
- line rendering
- target marker
- right-hand inspector

Success criteria:

- user can open the feature from Astro Clock
- user can search a city and read the nearest lines
- user can view a relocation summary without leaving the modal

### Phase 4: Comparison Workflow

Deliverables:

- compare endpoint
- compare table/cards UI
- goal-aware summary copy

Success criteria:

- user can compare 2-4 cities without manually switching back and forth

### Phase 5: Crossings/Parans And Optimization

Deliverables:

- nearby crossing detection
- caching/memoization
- payload trimming and map smoothing

Success criteria:

- crossings are useful, not noisy
- map requests feel responsive on repeated runs

## Acceptance Criteria

- The feature requires exact birth time and gives a clear validation error when missing.
- A user can inspect a city from manual natal input without first creating a persistent app-wide chart.
- A user can inspect a city from an existing natal snap.
- The map draws selected line families without crashing the Astro Clock view.
- The nearest-lines list is distance-sorted and uses the documented radius policy.
- The relocation chart uses the same natal instant as the source chart.
- Comparison mode can evaluate at least two target cities in one request/flow.
- All new endpoints respect the existing license-protected API path.

## Testing Plan

### Backend

- line generation invariants:
  - valid coordinate ranges
  - stable identifiers
  - no empty lines for supported objects
- relocation invariants:
  - natal planetary longitudes remain stable
  - angles/houses change for different locations
- distance invariants:
  - exact target-on-line distance near zero
  - sorting remains monotonic
- compare invariants:
  - repeated city inputs normalize cleanly

### Frontend

- API query-shape tests in `frontend/src/tests/astrocartographyApi.test.mjs`
- modal flow tests in `frontend/src/tests/astrocartographyModal.test.jsx`
- map/interpreter staleness tests when rapidly changing target city

### Manual QA

- verify opening/closing the modal does not leave Astro Clock stuck in paused mode
- verify map rendering in packaged Electron build
- verify geocoding and timezone failures fail clearly
- verify line meaning copy stays concise and non-deterministic

## Risks

- `AC/DC` geometry is the most mathematically error-prone part of the feature.
- Crossings/parans can become noisy if treated as a global map layer too early.
- Using research markdown directly at runtime would create latency and packaging problems.
- If the feature over-relies on a single summary score, it will drift into false precision.

## Recommended First Build Slice

Build this first:

- one modal
- manual natal input only plus optional snap selection
- seven traditional bodies plus Sun and Moon
- `MC/IC/AC/DC`
- single-city inspection
- relocation summary

Do not start with:

- worldwide city ranking
- local-space lines
- giant interpretation essays
- all possible bodies and special points at once

This keeps the first release technically tractable and aligned with the current Astro Clock architecture.
