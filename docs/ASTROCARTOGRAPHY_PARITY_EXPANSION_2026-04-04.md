# Astrocartography Parity Expansion

Date: 2026-04-04

## Purpose

This memo documents the parity-expansion slice that addressed the main Astrocartography gaps identified after the first internal alpha.

The previous state was:

- the angular line engine was sound
- PathFinder had the first four weighted goal families
- atlas search and compare worked
- the modal was useful but still too map-centric

The missing or partial areas were:

- no dedicated Intersections workspace
- no Local Space technique surface
- no richer delineation/report layer
- only first-wave PathFinder goals
- atlas search was strong but only adjustable by resolution, not by region
- relocation interpretation existed but was still too thin for city-by-city reading

## Implemented In This Slice

### 1. Dedicated Intersections Workspace

Implemented a geometry-first Intersections workspace around inspected cities.

Backend:

- `build_intersection_workspace(...)` in `backend/astrocartography_service.py`
- target analysis now returns structured `intersections` payloads for natal and transit in `backend/astro_clock_api.py`

Frontend:

- new `Intersections` workspace tab in `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- target-centered geometry map with intersection markers and dedicated intersection counts/headline

This resolves the old problem where crossings existed only as a light side card.

### 2. Local Space As A Real Technique Surface

Implemented a first major Local Space technique layer.

Backend:

- `build_local_space_rays(...)` in `backend/astrocartography_service.py`
- target analysis now returns `local_space` payloads for natal and transit in `backend/astro_clock_api.py`

Frontend:

- new `Local Space` workspace tab in `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- target-centered map rendering the Local Space rays
- right-rail Local Space summary cards

This moves Local Space from "not present" to a real, usable technique surface.

### 3. Richer Delineation / Report Layer

Implemented a structured delineation/report layer for inspected cities.

Backend:

- `build_delineation_report(...)` in `backend/astrocartography_service.py`
- target analysis now returns a top-level `report` payload in `backend/astro_clock_api.py`

Frontend:

- new `Report` workspace tab in `frontend/src/features/astroclock/AstrocartographyModal.jsx`
- report headline, detail cards, and sectioned narrative blocks

This resolves the earlier gap where interpretation existed only as line-by-line cards and brief relocation notes.

### 4. Stronger Relocation Interpretation

Expanded relocation feature extraction and summaries in `backend/astrocartography_goal_engine.py`.

New relocation metrics now include:

- `community`
- `beliefs`
- `chemistry`
- `career_status`
- `home_base`

Relocation summaries now expose:

- `headline`
- `support_notes`
- `caution_notes`
- existing angular planet and prominent house data

This gives the UI a stronger city-detail layer even before PathFinder weighting is applied.

### 5. Second-Wave Goal Models

Extended the PathFinder runtime asset beyond the first four visible categories.

Added goal families:

- `home`
- `partners`
- `beliefs`
- `friends`
- `career`
- `sex`

Builder:

- `scripts/build_astrocartography_goal_models.py`

Runtime:

- `backend/knowledge/astrocartography/place_goal_models.runtime.json`

These are explicit Vox Stella models grounded in the corpus and aligned to inferred legacy `.HYP` families, not direct recovered runtime formulas.

### 6. Region Filtering For Atlas Search

Implemented region-aware atlas search on top of the existing catalog.

Builder:

- `scripts/build_astrocartography_city_catalog.py`

Runtime:

- `backend/knowledge/astrocartography/city_catalog.runtime.json`

Backend:

- `backend/astrocartography_city_catalog.py`
- `backend/astrocartography_atlas_engine.py`
- `backend/astro_clock_api.py`

Frontend:

- `frontend/src/features/astroclock/api.mjs`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

The catalog now stores continent metadata, and atlas search can be constrained by continent in addition to country, query, and resolution.

## Product Behavior After This Slice

The Astrocartography modal now has four explicit workspaces:

- `Map`
- `Intersections`
- `Local Space`
- `Report`

The feature still fits the Astro Clock design language:

- same modal shell
- same premium gate behavior
- same left/center/right rail composition
- same snap-first natal workflow
- same transit grammar as Astro Clock

## Source / Reference Comparison

### Areas Now Meaningfully Closer To Reference Apps

- multi-workspace map-first product shape
- dedicated geometry surface for intersections
- first real Local Space technique surface
- stronger city report / delineation behavior
- broader PathFinder model catalog

### Areas Still Partial

- Local Space is implemented as a real directional technique, but it is not yet full legacy-suite parity
- the new Intersections workspace is geometry-first and useful, but it is still not a full astronomical paran engine
- the atlas is still catalog-bound at 5463 cities
- the second-wave goal models are source-backed Vox Stella profiles, not exact recovered Almagest formulas

## Current Practical Status

Astrocartography is no longer just a correct angular map plus comparison tools. It now behaves like a multi-technique locational workspace with:

- angular line mapping
- city inspection
- PathFinder ranking
- atlas search
- Intersections
- Local Space
- structured delineation

That is a substantial parity step. It is still not exact reference parity, but the remaining gaps are now narrower and more specific.

## Remaining High-Value Follow-Ups

- true astronomical paran engine instead of geometry-first crossing emphasis
- deeper Local Space parity features and interpretation range
- optional denser atlas datasets beyond the current catalog
- more advanced report authoring/export surfaces
- refinement of second-wave goal weights through more corpus extraction and product tuning

