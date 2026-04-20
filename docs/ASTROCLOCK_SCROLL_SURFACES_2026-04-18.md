# AstroClock Scroll Surfaces

## Goal

Unify the scroll treatment for dense AstroClock tiles so the scroller reads as part of the card instead of a separate UI strip.

## Visual Direction

- Quiet scrollbar thumb instead of a visible rail
- Transparent track so the card edge stays visually clean
- Narrow 4px scrollbar to reduce consumed width
- Soft bottom fade to imply overflow without a heavy gutter
- Same treatment across the main dense reference tiles

## Implementation

Added two shared frontend utilities in [frontend/src/index.css](C:/Users/sabaa/Downloads/codexhorary/frontend/src/index.css):

- `.astro-scroll-shell`
  - relative wrapper for in-card overflow areas
  - adds a subtle bottom fade
- `.astro-scroll`
  - narrow, transparent-track scrollbar
  - AstroClock-specific override of the broader app scrollbar skin

## Applied Tiles

- [frontend/src/features/astroclock/AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx)
  - Arabic Lots
  - Sect
  - Cusp Aspects
  - Current Aspects
- [frontend/src/features/astroclock/AlmutenTile.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AlmutenTile.jsx)
  - Almuten

## Notes

- This change is intentionally scoped to AstroClock tile bodies rather than replacing the app-wide scrollbar everywhere.
- The utility can be reused later for other dense AstroClock panels if the same treatment is wanted.
