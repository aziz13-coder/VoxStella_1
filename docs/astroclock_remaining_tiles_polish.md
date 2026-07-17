# AstroClock Remaining Tile Polish

## Goal

Bring the remaining smaller AstroClock tiles into the same visual language as the already-polished hero surfaces:

- top control bar
- chart tile
- current aspects
- influence & afflictions
- compass

The intent is refinement, not redesign. The cards should stay light, analytical, and calm.

## Hover-Aspect Clarification

The wheel hover inspector only renders the major aspect set currently supplied to the wheel:

- conjunction
- sextile
- square
- trine
- opposition

This means a hovered planet can legitimately show no aspect list if it has no major aspect in the current wheel scope. That behavior is now explicit in the center tooltip so the UI does not look broken when a planet has no eligible rows.

Source file:

- `frontend/src/components/wheel/SketchWheel.tsx`

## Tiles Polished In This Pass

### Moon Condition

The Moon card was kept, not removed. It now reads as a proper lunar-status tile instead of a generic status panel.

Changes:

- stronger Moon headline
- clearer phase summary
- explicit Void-of-Course status
- dedicated `Next Aspect` and `Next Sign` blocks
- calmer sign-progress treatment
- reduced chip clutter

Source file:

- `frontend/src/features/astroclock/AstroClock.jsx`

### Positions + Dignity

This card now follows the refined right-column language more closely.

Changes:

- quieter eyebrow + title structure
- smaller sort controls
- denser rows with calmer track treatment
- serif emphasis for sign/degree readout
- clearer score emphasis

Source file:

- `frontend/src/features/astroclock/AstroClock.jsx`

### Current Cusps

The old table-like cusp presentation was replaced with calmer row cards.

Changes:

- removed utilitarian header-grid look
- added quieter metadata heading
- serif degree/sign emphasis
- lighter ruler line as secondary information

Source file:

- `frontend/src/features/astroclock/AstroClock.jsx`

### Left-Rail Support Cards

The left-rail support cards were brought closer to the sketch direction without introducing the sketch's ribbon-collapse system.

Changes:

- `Receptions`: stronger summary block and calmer row cards
- `Dispositors`: clearer chain presentation and final-dispositor emphasis
- `Arabic Lots`: calmer formula-options tray and cleaner point rows
- `Sect`: summary-first composition instead of chip soup
- `Degree Hits`: refined input tray and calmer result cards
- `Almuten`: promoted into a featured primary summary with clearer secondary rows

Source files:

- `frontend/src/features/astroclock/ReceptionsTile.jsx`
- `frontend/src/features/astroclock/DegreeHitsTile.jsx`
- `frontend/src/features/astroclock/AlmutenTile.jsx`
- `frontend/src/features/astroclock/AstroClock.jsx`

### Secondary Utility Cards

The remaining support cards also received light polish so they do not visually fall back to the older dashboard language.

Changes:

- `Fixed Stars`: cleaner value hierarchy
- `Saved Snaps`: stronger header and calmer record rows
- `Asteroids`: quieter status card and better item hierarchy

Source files:

- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/AsteroidsTile.jsx`

## Intentional Non-Changes

- The wheel still uses the major-aspect contract already shared with the current-aspects tile.
- The left rail still uses separate cards instead of the sketch's collapsible ribbons.
- No new backend route was added for these small-tile polish changes.

## Remaining Optional Follow-Ups

- move the left rail to grouped ribbon sections if you want to match the sketch more literally
- decide whether `Saved Snaps` should eventually become a compact drawer instead of a full card

## Follow-Up Pass

### Cusp Aspects

The `Cusp Aspects` tile was polished after the initial remaining-tiles pass so it no longer reads like an older utility filter panel.

Changes:

- quieter eyebrow + title structure
- calmer segmented filter controls
- denser but more legible grouped cusp sections
- serif emphasis on the main aspect row label
- better visual separation of phase, dexter/sinister, and tight/partile metadata

Source file:

- `frontend/src/features/astroclock/AstroClock.jsx`

## Surface Cleanup Pass

The later sketch review clarified a stricter rule for AstroClock support cards:

- do not nest pale grey information trays inside already-white tiles
- prefer content sitting directly on the panel surface
- when sub-grouping is needed, use thin borders, quiet dividers, or white bordered modules instead of tinted inset boxes

### Inner Surface Adjustments

This pass removed or reduced the old `bg-zinc-50` inset-card treatment across the remaining support surfaces.

Changes:

- `Moon Condition`: VoC and duration now sit in the panel rhythm instead of grey sub-cards; sign progress no longer lives in a tinted inset tray
- `Receptions`: the summary now reads as an open header block instead of a tinted summary card
- `Dispositors`: chain rows now use white bordered modules instead of grey inset rows
- `Positions + Dignity`: planet rows now sit on white bordered modules
- `Current Cusps`: cusp rows now use white bordered modules
- `Saved Snaps`: saved/search result rows now use white bordered modules and calmer utility-pill actions
- `Arabic Lots`, `Sect`, and `Cusp Aspects`: support grouping remains, but the grey tray treatment was reduced in favor of white panel surfaces
- `Asteroids`: unavailable/missing messaging no longer renders in a pale grey inset box

### Stricter Surface Rule

This rule is now enforced more strictly across the live AstroClock dashboard surfaces:

- do not use pale grey nested containers for informational content inside an already-white AstroClock card
- if a subsection needs structure, use white bordered modules, top borders, spacing rhythm, or semantic tint only
- neutral segmented controls and metadata chips should also bias toward white rather than pale grey when they sit inside the main dashboard cards

Additional cleanup applied:

- `Influence & Afflictions`: the element/modality summary module now uses a white bordered inner surface instead of a pale inset tray
- `Degree Hits`: the input tray now uses a white bordered inner surface, and the neutral state badge no longer uses a pale fill
- `Almuten`: the featured leader summary now uses a white bordered inner surface instead of a pale inset panel
- `Compass Bearings`, `Chart Lens`, `Cusp Aspects`, and related segmented controls now use white control rails instead of pale inset rails
- `Receptions`, `Asteroids`, and small metadata chips in the main AstroClock dashboard now default to white chips unless a semantic tint is needed

### Flattening Pass

The follow-up review tightened the rule further for the small support tiles:

- not only avoid pale grey inset trays
- also avoid unnecessary nested white mini-cards when the information can sit directly on the tile surface

Applied flattening:

- `Receptions`: removed the `Traditional Reception` eyebrow and flattened mutual/unilateral rows to divider-based entries
- `Moon Condition`: `Next Aspect` and `Next Sign` now sit in the tile rhythm instead of boxed sub-cards
- `Fixed Stars`: star hits now render as divider-based rows instead of nested cards
- `Sect`: summary, benefic/malefic, and planet rows now sit on the main tile surface with dividers
- `Cusp Aspects`: house groups and aspect rows now render as divider-based lists rather than nested cards
- `Degree Hits`: the input area and hit rows now use the tile surface with dividers instead of inset modules

### Compass Wiring Fix

The compass issue was not only visual. The backend dashboard payload already exposed chart coordinates, but the AstroClock frontend transform was dropping them before they reached the compass tile.

Fixes:

- `transformDashboard(...)` now preserves `latitude` and `longitude`
- `CompassTile` now receives real dashboard coordinates more reliably
- the compass empty state is more explicit about what is missing when local-space cannot render

Source files:

- `frontend/src/features/astroclock/transform.mjs`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/ReceptionsTile.jsx`
- `frontend/src/features/astroclock/CompassTile.jsx`
- `frontend/src/features/astroclock/AsteroidsTile.jsx`
