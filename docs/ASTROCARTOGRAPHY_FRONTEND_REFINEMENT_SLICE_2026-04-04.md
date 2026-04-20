# Astrocartography Frontend Refinement Slice

Date: 2026-04-04

## Scope

This slice tightens the Astrocartography modal after the first map-first polish pass. The goal is to improve hierarchy and visual consistency without drifting away from the existing Astro Clock design language.

## Findings

- The first polish pass fixed the dead space under the map, but the workspaces still felt uneven.
- `Map`, `Intersections`, `Local Space`, and `Report` did not open with the same visual rhythm.
- The right rail still treated the selected city like inline form data instead of a primary summary object.
- Status chips were more useful than before, but they still needed cleaner density and stronger visual grouping.

## Implemented

- Added a stronger `Selected City` summary card in the inspector rail.
  - location name
  - coordinates
  - active mode
  - active goal
  - natal/transit/goal scores
  - compare action
- Added a shared workspace header pattern across the Astrocartography workspaces so the tabs feel like one family instead of separate tools bolted together.
- Introduced compact metric chips for small summaries instead of repeating plain text rows.
- Tightened the workspace tab chrome and the map HUD pill styling so the controls feel cleaner and more deliberate.
- Turned the `Rules` block into a muted support card so it sits lower in the hierarchy.

## Result

- The selected city now reads as the main object in the right rail.
- The four workspaces now have a more consistent entry structure.
- Metrics are easier to scan and occupy less visual weight.
- The feature remains aligned with the broader Astro Clock UI rather than becoming a separate visual system.

## Follow-up

- Review the modal on smaller laptop widths and reduce control density if the left rail begins to feel cramped.
- Consider adding a single compact toolbar variant for `Intersections` and `Local Space` if those views gain more filters.
- Revisit map-label typography and chip color balance after more runtime usage.
