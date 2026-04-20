# Weather Scan Matrix Direction

Date: 2026-04-19

## Goal

Implement the weather scan sketch as the primary scan surface without changing the backend contract.

The target is the matrix-first design with:

- a left column for `location + peak window`
- timeline columns across the top
- compact score cells that also carry a short state code
- the peak interval shown as a highlighted span inside the row timeline

## Chosen Direction

This implementation uses the existing Astro Clock console language instead of copying the standalone mockup primitives from the external sketch archive.

That means:

- keep the existing three-zone workspace shell
- keep the shared command band and KPI strip
- make the matrix the dominant artifact in the center pane
- preserve the right-side inspector

## Data Mapping

The current weather scan payload already supports the sketch directly.

- `result.series.timeline` drives the matrix columns
- `result.series.places[]` drives the matrix rows
- `peak_window_start_datetime`, `peak_window_end_datetime`, and `peak_datetime` drive the row ribbon
- `series[].scan_level` drives the cell code and color treatment
- `series[].score` remains the main numeric value inside each cell

No API changes are required.

## Implementation Scope

Source files only:

- `frontend/src/features/astroclock/WeatherWorkspace.jsx`
- `frontend/src/tests/mundaneWeatherWorkspace.test.jsx`

Key UI changes:

- rename the graph toggle label to `Matrix`
- change the scan summary KPI from `Potential date` to `Peak window`
- replace the previous sparkline-plus-grid graph with a ranked pressure matrix
- color and label each matrix cell from `scan_level` instead of raw score thresholds alone
- keep the overall scan window visible on each row and mark the strongest interval inline

## Verification Target

The focused test should confirm that a completed weather scan renders:

- the matrix header
- a ranked place row
- scan-level short codes such as `DOM`, `CO`, `LEAD`, `ACT`, and `W`
- titles that reflect the relative scan state, not just the absolute level
