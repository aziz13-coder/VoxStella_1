# Astrocartography Frontend Polish

Date: 2026-04-04

## Goal

Improve Astrocartography's layout, spacing, and visual hierarchy while preserving the existing Astro Clock design language.

## Findings

- The map was not behaving like the primary workspace. Important telemetry lived in a loose text block under the map, which created dead vertical space and made the center pane feel unfinished.
- Too much implementation-facing information was visible at once. Items like basemap details and label-placement notes were useful during development but too technical for normal users.
- The side rails were over-explaining the feature. Repeated helper copy and always-visible empty sections made the modal feel denser than the rest of Astro Clock.
- The right rail gave equal visual weight to empty and populated sections. That flattened the hierarchy and made inspection feel noisy before a city was selected.

## Implementation

- Converted the center pane into a map-first card with a dedicated toolbar row, one dominant viewport, and compact in-map HUD chips.
- Removed the old below-map telemetry dump and moved the useful status into map overlays:
  - natal line count
  - transit line count
  - global paran count
  - live atlas augmentation state
  - active goal
  - selected target
  - natal/transit timestamps
- Kept the map frame visually aligned with Astro Clock by retaining the existing card chrome, rounded borders, muted rails, and simple action buttons.
- Tightened left-rail copy and grouping so the sections read more like operator controls than documentation.
- Shortened helper text where the control label already carries the meaning.
- Made the right rail conditional:
  - compact empty inspector state before a city is selected
  - reading, parans/intersections, relocation, and local-space sections only when a city is active
  - atlas and compare sections only when they actually have work to show

## Result

- The modal now reads as a three-rail workspace with a clear hierarchy:
  - left rail: setup and search
  - center: primary map canvas
  - right rail: interpretation and ranking
- The most obvious blank-space issue under the map is removed.
- The feature stays visually consistent with the rest of Astro Clock instead of introducing a separate design system.

## Next Design Moves

- Replace some repeated helper copy with inline tooltips or lighter secondary labels.
- Add a compact selected-city summary card directly above the strongest interpretation block in the right rail.
- Normalize visual density between workspace tabs so `Map`, `Intersections`, `Local Space`, and `Report` feel like one family.
- Revisit chip styling and line-label density after more runtime testing at different zoom levels.
