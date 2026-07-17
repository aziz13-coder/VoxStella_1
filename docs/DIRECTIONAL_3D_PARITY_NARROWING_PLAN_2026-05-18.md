# Directional 3D Parity Narrowing Plan

Date: 2026-05-18

## Scope

Directional 3D is a coordinate-system geometry viewer. This plan keeps the feature scoped to geometry, chart context, and inspection workflows. It does not add astrological scoring, interpretation, or renamed user-facing concepts.

## Current Baseline

Implemented:

- Current AstroClock chart context can drive Directional 3D.
- Saved snaps with embedded coordinates avoid stale `0/0` chart locations.
- Backend exposes separate `EQL`, `EQU`, and `HOR` coordinate blocks per usable chart object.
- House cusps are included as non-full geometry rows.
- Frontend supports coordinate-system switching, rotation, tilt, object table, selected-object details, and house-boundary rendering.

## Gap Closure Plan

### 1. Stepping Controls

Target:

- Add lightweight controls inside Directional 3D for stepping the currently inspected geometry without leaving the modal.
- Support time, latitude, and longitude stepping.
- Keep state/API compatible with future finer stepping controls.

This pass:

- Add `-1h` and `+1h` time stepping for manual/saved-snap contexts.
- Add `-1` and `+1` degree latitude/longitude stepping.
- Route stepped context through the existing Directional 3D API.
- Preserve the source mode: Current Auto remains live/realtime, while manual and saved snap stepping produces explicit manual geometry.

Deferred:

- Custom step sizes.
- Continuous animation.
- Batch stepping.
- Full keyboard step bindings.

### 2. Reference Layer Variants

Target:

- Expand beyond the first-pass object/grid/back-half toggles into geometry reference layers that match the coordinate viewer model.

This pass:

- Add tropic reference circles.
- Add polar reference circles.
- Keep ecliptic, equator, horizon, axes, houses, and back-half controls.

Deferred:

- World-side labels.
- Custom user-defined circles.
- Additional named great circles beyond the current system rings.

### 3. Equatorial Speed Parity

Target:

- Use native equatorial speed when the chart source provides it.
- Make fallbacks explicit when native equatorial speed is unavailable.

This pass:

- Annotate each row with coordinate metadata for `EQL`, `EQU`, and `HOR`.
- Mark `EQU.speed_source` as `native`, `derived`, `fallback`, or `cusp_static`.
- Add `EQU.latitude_speed` and mark `EQU.latitude_speed_source` as `native`, `derived`, `unavailable`, or `cusp_static`.
- Add chart-level `data_gaps` when exact or derived equatorial speed is unavailable for full objects.

Deferred:

- Exact speed parity for chart rows that serialize neither native equatorial speed nor ecliptic latitude speed.

### 4. Legacy Snap Coordinate Recovery

Target:

- Avoid geocoding vague legacy labels when stored coordinates exist.

Already implemented:

- The Directional 3D saved-snap flow fetches full snap detail when snap summaries omit coordinates.
- It uses stored `coords` before falling back to location resolution.

Remaining blocker:

- Snaps with neither stored coordinates nor resolvable location text still need user cleanup or a backend data migration.

## Acceptance Checks

- Backend payload tests cover metadata, speed-source fallbacks, and data-gap reporting.
- Frontend tests cover stepping requests and new layer toggles.
- Browser validation confirms the modal renders non-empty after stepping and layer changes.
- No user-facing text exposes internal source names.
