# Mundane Scan Series Graph Plan

Date: 2026-04-11

## Goal

Add a graph-oriented spatiotemporal scan output that can show:

- which places rise first inside a war or mundane time window
- where the strongest place-time peaks occur
- whether a place looks more like an opening-break candidate or a later campaign-pressure candidate

This feature should sit on top of the existing mundane scan engine. It should not replace the existing ranked-cell output.

## Problem

The current scanner returns ranked cells well enough for hotspot lookup, but it does not expose the place-time structure behind those rows.

That makes long-window scans hard to interpret:

- a city can dominate the top rows simply by repeating over nearby time slices
- early outbreak signals and later campaign pressure get mixed together
- the user cannot see how pressure rises, peaks, and fades per place

## Product Shape

Keep the existing ranked-cell scan view. Add a second output mode for series and graph interpretation.

The workspace should expose two result views:

- `Ranked Cells`
- `Break Graph`

The graph view should be available whenever the scan returns aggregated series data.

## Semantic Split

The graph output must preserve a strict separation between:

- `absolute domain score`
  - the source-backed mundane evaluation already returned per cell
- `scan score`
  - the scan-layer ranking score already used for hotspot ordering
- `breakout pressure`
  - a graph-oriented interpretation of how a place rises across the returned time window

The books support chart judgment. They do not define UI-grade heatmaps or breakout curves. So:

- `absolute score` stays doctrine-backed
- `scan score` stays scanner calibration
- `breakout pressure` is a research-oriented aggregation layer built on top of the scan result

## Required Output

The graph layer should return:

- `timeline`
  - ordered datetimes used in the scan
- `places`
  - per-place time series
- `breakout_candidates`
  - ranked place summaries for likely opening-break pressure
- `series_overview`
  - top-level summary for the current run

Each place series should include:

- `location`
- `peak_scan_score`
- `peak_datetime`
- `first_active_datetime`
- `peak_level`
- `breakout_index`
- `series`
  - a per-timepoint list with:
    - `datetime`
    - `scan_score`
    - `absolute_score`
    - `scan_level`
    - `absolute_level`

## Breakout Heuristic

The first implementation should not invent a new black-box model.

Use a transparent heuristic:

- start from the existing `scan_score`
- measure how early the place becomes meaningfully active
- reward a sharp rise into the top band
- preserve the peak cell and first active cell separately

This should let the graph distinguish:

- `opening-break candidate`
- `sustained theater candidate`
- `late campaign-pressure candidate`

## Backend Design

The scan service should do one evaluation pass, then branch into two outputs:

1. ranked-cell output
2. graph/series aggregation

Do not rerun the scan a second time just to build the graph.

Recommended implementation:

- refactor the scanner so cell evaluation is reusable
- add an optional `include_series` flag
- when enabled, attach a `series` object to the scan result

The API should support this for both:

- blocking run endpoint
- async start/result flow

## Frontend Design

Inside the existing mundane scan workspace:

- keep the current form and async run flow
- keep the current ranked-cell output
- add a result-view toggle once series data exists
- render the graph view as:
  - a breakout summary rail
  - a place-time heatmap
  - per-place peak metadata

The first graph does not need a large chart library. A heatmap-style grid is enough if it is readable.

## Acceptance Criteria

The first graph feature is good enough when:

- one scan run produces both ranked cells and graph-ready series data
- the graph makes it obvious which places rise earliest and peak highest
- long-window war scans become easier to read than the current repeated ranked rows
- the UI keeps calibration and research flags visible

## Non-Goals

- no replacement of the source-backed score engine
- no opaque trained model in the first cut
- no claim of certainty or prediction guarantee
- no removal of the ranked-cell scan result
