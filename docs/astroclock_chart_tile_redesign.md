# AstroClock Chart Tile Redesign

## Goal

Bring the central AstroClock chart tile closer to the refined design sketch while keeping the current product language:

- smaller chart tabs and control chrome
- larger wheel stage
- a quieter chart context row without a competing title
- compact ASC / MC metadata
- compact bottom readout rail
- no dignity block inside the chart tile
- hover on a planet shows that planet's aspects

## Implemented Phases

### Phase 1: Explicit chart metadata

The AstroClock dashboard payload now returns explicit `ascendant` and `midheaven` values on the main dashboard route instead of forcing the frontend to infer both from house cusps.

Source files:

- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`
- `frontend/src/features/astroclock/transform.mjs`

This lets the chart tile render the top-right ASC / MC meta block and the bottom rail from a single normalized model.

### Phase 2: Chart lens model

The chart tile now uses a three-state lens:

- `traditional`
- `modern`
- `bodies`

Implementation notes:

- `traditional` maps to the classical seven planets
- `modern` adds Uranus / Neptune / Pluto
- `bodies` shows every returned body/point in `data.planets`
- the lens drives the old `includeModern` fetch contract:
  - `traditional` -> `includeModern = false`
  - `modern` / `bodies` -> `includeModern = true`

That keeps the chart tile as the UI for modern-body visibility without inventing a second dashboard endpoint.

Source file:

- `frontend/src/features/astroclock/AstroClock.jsx`

### Phase 3: Chart card recomposition

`ChartMock` was rebuilt from a generic square card into a dedicated chart workspace panel.

Changes:

- added a title row so the tile reads as a dedicated workspace instead of a generic panel
- replaced the old single `Modern` toggle with compact lens pills
- shrank the house-system control
- added compact top-right ASC / MC meta
- removed the mini hour-of-day ring to free wheel space
- removed the dignity block from the chart tile
- added a compact bottom rail for:
  - Ascendant
  - Midheaven
  - Lot of Fortune
  - Sect
- added a restrained footer timestamp instead of a louder metadata strip inside the readout rail

Source file:

- `frontend/src/features/astroclock/AstroClock.jsx`

### Phase 4: Hover aspects in the wheel

`SketchWheel` now accepts richer aspect rows and shows hover-linked aspect detail.

Behavior:

- aspect lines are hidden until a planet is hovered or pinned
- hovering or pinning a planet highlights only that planet's aspect lines
- the tooltip now shows:
  - planet name
  - zodiac degree
  - house
  - aspect list for that planet

### Phase 5: Visual polish pass

The chart tile now keeps the original implementation doctrine but moves closer to the sketch's visual discipline.

Changes:

- removed the magnifier lens effect from the wheel to keep the stage calmer
- simplified the top row so it shows chart context without a competing workspace title
- improved angle label placement so `ASC / MC / DSC / IC` sit more deliberately around the ring
- changed planet degree labels to anchor inward/outward by quadrant instead of always reading to the right
- tightened crowded label sizing so dense clusters read more cleanly
- moved the hover inspector into the wheel's center whitespace
- changed active aspect lines from straight chords to calmer curved paths
- differentiated phase visually:
  - applying = solid, slightly stronger line
  - separating = dashed, slightly lighter line

Source files:

- `frontend/src/components/wheel/SketchWheel.tsx`
- `frontend/src/features/astroclock/AstroClock.jsx`

The wheel uses the already-normalized `planetary_aspects_precise` rows from the dashboard transform. No separate hover-aspect backend route was added.

Source files:

- `frontend/src/components/wheel/SketchWheel.tsx`
- `frontend/src/features/astroclock/AstroClock.jsx`

## Frontend Data Flow

1. `/api/astro-clock/dashboard` returns raw chart data, aspects, lots, sect, cusps, ascendant, and midheaven.
2. `transformDashboard()` normalizes the dashboard payload for AstroClock.
3. `ChartMock` derives:
   - visible planets from the active chart lens
   - visible aspect rows for the wheel
   - compact readout metadata for ASC / MC / Fortune / Sect
4. `SketchWheel` renders the wheel and handles hover/pin aspect inspection.

## Notes For Future Tweaks

- If the chart tile eventually needs separate visibility rules for nodes, Chiron, or asteroids, extend `filterChartPlanetsByLens()` rather than adding more wheel-only conditionals.
- If the tooltip needs more editorial treatment, keep the data contract in `SketchWheel` and move only presentation.
- If the chart tile gains a side inspector later, the current hover aspect index in `SketchWheel` can be lifted into `ChartMock` without changing the dashboard API.
- The AI sketch still uses a side readout stack and an editorial reading block. The current implementation deliberately keeps the bottom-rail composition from this plan; if that changes later, treat it as a layout doctrine change rather than a small polish tweak.
