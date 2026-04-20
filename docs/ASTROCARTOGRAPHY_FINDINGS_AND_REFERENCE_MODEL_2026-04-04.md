# Astrocartography Findings And Reference Model

Date: 2026-04-04

## Purpose

This memo documents the Astrocartography findings gathered so far for the new Vox Stella feature.

It captures three things:

- the knowledge findings from the astrocartography book corpus
- the product-model findings from the Almagest reference application
- the current codebase fit and recommended feature direction

This memo is a findings summary. The implementation-oriented follow-up remains:

- `docs/ASTROCARTOGRAPHY_FEATURE_SPEC_AND_IMPLEMENTATION_PLAN_2026-03-30.md`

## Research Corpus Status

The source books from:

- `C:\Users\sabaa\Desktop\astrolgy books\new books`

were converted into AI-readable text and then normalized into a repo-local knowledge base.

Generated corpus:

- `horary_knowledge/astrocartography_books_text/`
- `horary_knowledge/astrocartography_knowledge_base/`

Builder script:

- `scripts/build_astrocartography_knowledge_base.py`

Knowledge-base structure:

- `normalized_books/`: markdown versions of the extracted books
- `guides/`: per-book scan guides with heading indexes and keyword anchors
- `reference/`: distilled implementation notes
- `catalog.json`: machine-readable corpus index

## Main Corpus Findings

### 1. The strongest sources for V1 are narrow and practical

The highest-value sources for a first release are:

- `Astrocartography Map Interpretation (Hermes Astrology)`
- `Finding Your Best Places`
- `The Astro*Carto*Graphy Book of Maps`

Their practical roles are distinct:

- Hermes is the best interpretation library for line meanings, angle meanings, and crossings.
- Dan Furst is the best practical workflow source for line usage, relocation distinctions, local-space framing, and line-range caveats.
- Lewis/Guttman is the best conceptual and historical source for case framing and the original locational worldview.

Supporting but lower-priority sources:

- `Dictionary of Astrology` for terminology
- `The Astrology of Death` as tangential and not needed for the MVP

### 2. The corpus agrees on the core product shape

The books consistently support this understanding:

- Astrocartography is a locational extension of the natal chart, not a replacement for it.
- The core angular model is based on the four angles:
  - Ascendant
  - Descendant
  - Midheaven
  - IC / Nadir
- Relocation charting is a necessary companion to map reading.
- Crossings / parans matter and should not be treated as noise.
- The method is best used to compare and narrow locations, not to produce deterministic destiny claims.

### 3. The corpus supports a layered feature, not a single answer engine

The books point toward a feature family rather than a single output:

- map view
- location inspection
- relocation-chart review
- crossings/parans
- compare cities
- later: local-space and extended search tools

### 4. Distance policy is approximate, not exact

The corpus does not provide one single canonical range.

Observed corpus signals:

- Hermes-style interpretation text uses about `150 miles / 250 km`.
- Dan Furst describes looser practice around `300 miles / 500 km`.

Practical product conclusion:

- use `300 km` as the primary interpretation radius
- use `500 km` as an extended influence radius
- avoid presenting distant lines as equally actionable

### 5. Product tone should be advisory, not absolute

The corpus supports language like:

- emphasis
- support
- challenge
- activation
- opportunity
- pressure

The corpus does not support language like:

- guaranteed success
- one best city
- destiny score
- perfect place

## Existing Knowledge Base Outputs

Important generated files already available for implementation work:

- `horary_knowledge/astrocartography_knowledge_base/README.md`
- `horary_knowledge/astrocartography_knowledge_base/catalog.json`
- `horary_knowledge/astrocartography_knowledge_base/reference/01_core_concepts.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/03_techniques_and_ranges.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/04_glossary.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md`

These docs are already usable as the source layer for:

- interpretation asset generation
- API design
- UX copy
- acceptance criteria

## Reference Application Findings

Reference application inspected:

- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\Almaatla.exe`

Observed running process:

- window title: `Almagest PathFinder`

Important safety note:

- the executable was not launched by the agent
- the user launched it
- analysis was based on screenshot evidence, static binary inspection, and process metadata

## Static Reverse-Engineering Findings

The executable and its folder strongly suggest an old desktop astrology atlas suite with multiple locational tools.

Important evidence:

- unsigned Windows GUI executable
- surrounding atlas/towns/world-map assets
- executable strings naming internal modules and workflows

Relevant adjacent files:

- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\Atlas.atl`
- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\TOWNS.ND`
- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\TOWNS.NDX`
- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\World.emf`
- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\AlmaAtlas.cfg`
- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL\AlmaAtla.doc`

Notable strings found inside the binary:

- `Optimal Place Finder`
- `Parans Intersections Line`
- `Change place for the Natal Chart`
- `Local Space`
- `Delineation`
- `Read Time Zone`
- `Dynamic Astrology`
- `Add Town`
- `Save Towns`

Internal module/form names visible in strings:

- `TWAlmaAtlasPlaceFinder`
- `TWAlmaAtlasLocSps`
- `TAlmaAtlasTechniques`
- `TWAlmaAtlasChart`
- `TWAlmaAtlasIntersection`
- `TWAlmaAtlasDeliniation`
- `TAlmaAtlasAddTown`

## Product-Model Findings From The Reference App

The reference app is not just a single map.

It appears to contain these core product models:

### 1. Angular Astrocartography Map

The screenshot clearly shows the classic locational map grammar:

- straight vertical lines
- curved pole-to-pole arcs
- planetary labels at map edges
- world atlas base map

Most likely interpretation:

- vertical lines correspond to `MC/IC`
- curved lines correspond to `AC/DC`

### 2. PathFinder / Place Finder

The running window title `Almagest PathFinder` plus the internal string `Optimal Place Finder` strongly suggest a dedicated location-search or ranking workflow rather than only manual map browsing.

### 3. Relocation Model

The string `Change place for the Natal Chart` suggests a dedicated relocation-chart mode tied to selected places.

### 4. Paran / Intersection Model

The strings `Parans Intersections Line` and `TWAlmaAtlasIntersection` strongly suggest a dedicated crossing/intersection workflow, not just incidental display on the main map.

### 5. Local Space Model

The strings `Local Space` and `TWAlmaAtlasLocSps` suggest a separate locational technique beyond standard astrocartography.

### 6. Delineation Model

The string `TWAlmaAtlasDeliniation` suggests a dedicated interpretation surface, likely tied to selected lines, places, or intersections.

### 7. Technique Selector

The string `TAlmaAtlasTechniques` suggests the atlas is organized around multiple techniques or modes rather than a single static map.

### 8. Place Database Model

The presence of town database files and strings like `Add Town`, `Save Towns`, `PlaceEdit`, and `ButtonChooseTownClick` indicate a built-in place database and place-management workflow.

### 9. Dynamic Time Model

The visible `Natal` and `Transit` toggle in the screenshot, plus strings like `Dynamic Astrology`, indicate the product treats locational astrology as both natal and time-dynamic.

## Screenshot Findings

From the supplied screenshot:

- the primary surface is a world atlas map
- the map is the central workspace, not a secondary visualization
- planetary lines are color-coded
- place markers are plotted across the map
- the UI includes explicit `Natal` and `Transit` modes
- the toolbar suggests multiple related locational or chart-analysis tools

This is important because it confirms the feature should be designed as a workspace with several linked tools, not only a one-shot report.

## What To Emulate

The reference app supports these product conclusions:

- astrocartography should begin with a map-centered workspace
- location search should be first-class
- relocation should be directly linked to location inspection
- crossings/parans deserve a dedicated workflow
- place comparison and place finding are core use cases
- the tool family likely grows naturally into local-space and dynamic overlays

## What Not To Copy

The reference app does not justify copying its UX literally.

We should avoid:

- opaque icons without labels
- over-dense line clutter by default
- excessive color overload
- exposing too many techniques at once in the first release
- treating every possible planet/point combination as an MVP requirement

## Codebase Fit Findings

The current Vox Stella codebase already has several useful fit points.

### Frontend fit

Existing relevant files:

- `frontend/src/App.jsx`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/api.mjs`
- `frontend/src/features/astroclock/astroClockViewState.mjs`

Important findings:

- Astro Clock already acts as a tool workspace with focused subfeatures.
- Astro Clock already includes a map stack via `react-leaflet`.
- Astro Clock already handles feature open/close, realtime pause/resume, and request-staleness concerns.

Conclusion:

- the first Astrocartography release should live inside Astro Clock
- it should open as another heavy analysis tool similar to `Transits`, `Election`, and `Forensic`

### Backend fit

Existing relevant files:

- `backend/app.py`
- `backend/astro_clock_api.py`

Important findings:

- Astro Clock already has a stable `/api/astro-clock/*` blueprint path.
- Existing helpers already resolve natal context, geocoding, timezone, and stateless chart bundles.
- Existing licensing flow already covers Astro Clock API surfaces.

Conclusion:

- Astrocartography should ship under `/api/astro-clock/astrocartography/*`
- relocation charting should reuse the existing chart-bundle helpers
- target-place resolution should reuse the existing geocoding and timezone path

## Current Recommended Product Shape

Based on both the corpus and the reference app, the right long-term product family looks like this:

- `Map`
- `City Inspector`
- `Relocation`
- `Compare`
- `Crossings / Parans`
- later: `Local Space`
- later: `Place Finder`
- later: `Dynamic / Transit Locational Overlay`

## Current MVP Recommendation

The reference app suggests a broad feature family, but the first implementation should stay narrower.

Recommended MVP:

- map view
- city search
- nearest-line inspector
- relocation-chart summary
- side-by-side compare
- nearby crossings/parans

Not recommended for V1:

- global place ranking
- local-space implementation
- transit-location overlays
- giant all-planets/all-points controls
- sprawling report-style interpretation output

## Open Questions

These are still unresolved:

- whether the first map should include only classical bodies or include modern bodies by default
- whether crossings/parans should appear on-map or mainly in the city inspector for V1
- whether comparison should remain city-driven or include broader country/region search
- whether later `PathFinder` functionality should be score-based, filter-based, or guided-question based
- whether local-space should be implemented as a separate mode or a toggle within the same workspace

## Immediate Next Step

The next engineering step should still follow the previously written implementation plan:

- generate compact runtime interpretation assets from the knowledge base
- scaffold backend astrocartography service modules
- add Astro Clock API endpoints for map, location, relocation, and compare

But from a product perspective, the findings now clearly support designing Astrocartography as a multi-tool workspace modeled more closely on:

- map first
- place workflow second
- interpretation third

rather than:

- report first
- map as decoration

That is the most important product finding gathered so far.
