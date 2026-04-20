# Transits Context Maturity
Date: 2026-04-14

## Purpose

This memo makes transits context maturity explicit.

The runtime already exposes context helpers and concordance support, but the layers are not equally complete. This inventory prevents the frontend and the API from implying a uniform maturity level where none exists.

## Maturity Levels

- `full`
  - first-class runtime layer with stable surface and clear output contract
- `partial`
  - materially implemented, but still exposed mainly as windows, helpers, or concordance support
- `helper_only`
  - useful support logic exists, but it is not a standalone runtime layer

## Inventory

### Primary Directions

- level: `partial`
- reason:
  - computed and used in exact analysis, scan, predictor, and auto-context
  - still surfaced mainly as windows rather than a full directions workspace

### Solar Arc

- level: `partial`
- reason:
  - auto-context exposes solar-arc windows and a selected window
  - no dedicated solar-arc interpretive runtime layer

### Secondary Progressions

- level: `partial`
- reason:
  - progressed Moon and progressed-planet windows are present
  - the runtime does not expose a full progression chart surface

### Solar Return

- level: `partial`
- reason:
  - solar-return markers and similarity helpers are active in analysis/concordance
  - auto-context does not yet surface solar return as a first-class layer

### Lunar Return

- level: `helper_only`
- reason:
  - lunar-return timing helpers exist
  - there is no first-class lunar-return runtime surface in transits

### Focus Suggestions

- level: `helper_only`
- reason:
  - focus houses/planets are heuristic assistance only
  - they are not an autonomous context layer
