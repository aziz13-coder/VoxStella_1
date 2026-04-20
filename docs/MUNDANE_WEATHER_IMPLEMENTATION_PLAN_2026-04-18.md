# Mundane + Weather Frontend Implementation Plan

Date: 2026-04-18

## Scope

Frontend only. No backend behavior changes are required for this pass.

The design package in [astrocarto.zip](C:/Users/sabaa/Downloads/astrocarto.zip) delivers two related directions for the Astro Clock advanced workspaces:

- Direction A: Dossier
- Direction B: Console

Both keep the three-pane research workspace, but they replace the current card-heavy UI with a more editorial research shell:

- mono eyebrows and compact mode tabs
- serif-led workspace headlines
- thin dividers instead of repeated rounded cards
- summary bands once a run starts
- denser result rows and inspector rails

## Recommended Direction

Use Direction A as the primary implementation target for the first refactor, and borrow two elements from Direction B:

- keep Direction A's editorial hierarchy for scan and analysis screens
- adopt Direction B's tighter top chrome and monospace mode switching

Reason:

- it is closer to the current Astro Clock family
- it fits the existing three-column layout with less churn
- it can be rolled out incrementally without rewriting every result surface at once

## Visual Thesis

Calm research console, editorial center pane, restrained accents per module: indigo-violet for Mundane and teal-sky for Weather.

## Content Plan

1. Top chrome: module switcher, mode switcher, run status, summary band
2. Center pane: primary output artifact, not stacked cards
3. Right rail: inspector, scope, and explanation
4. Idle state: setup rail expands only before the first run

## Interaction Thesis

1. Left setup collapses into a summary band after the run begins.
2. KPI pills become compact metric blocks or strips with one visual accent line.
3. Result selection should highlight one row cleanly and drive the right inspector without opening new card layers.

## Shared Foundation Work

Create shared research-workspace primitives before touching the major modules:

- `frontend/src/features/astroclock/researchWorkspaceTheme.js` or `.jsx`
- `WorkspaceChrome`
- `WorkspaceModeTabs`
- `WorkspaceEyebrow`
- `WorkspaceHeadline`
- `SummaryBand`
- `MetricStrip`
- `SectionBar`
- `InspectorRail`
- `DataTableRow`

This should replace duplicated local tokens inside:

- [MundaneWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneWorkspace.jsx)
- [MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx)
- [WeatherWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/WeatherWorkspace.jsx)

## Module Plan

### 1. Mundane Scan

Target file: [MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx)

Implementation steps:

- convert the idle left column into a full setup rail with stacked labeled rows
- collapse setup into a top summary band once a scan is running
- replace the current metric pill grid with a single KPI strip
- convert result cards into a ranked table with one selected row state
- keep the right rail focused on selected-place interpretation and scan scope

### 2. Mundane Analysis

Target file: [MundaneWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneWorkspace.jsx)

Implementation steps:

- replace section-card mosaics with fewer editorial sections
- promote the main verdict and benchmark comparison into the center pane header
- convert signal chips into labeled rows with short interpretive copy
- keep supportive data in thin divided sections instead of nested rounded panels

### 3. Weather Scan + Analysis

Target file: [WeatherWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/WeatherWorkspace.jsx)

Implementation steps:

- keep the same shell as Mundane but switch the accent to teal-sky
- make the center artifact graph-first for weather scan results
- use compact metric strips above sparklines and peak-window surfaces
- reduce the number of bordered boxes around toggles and quick filters
- make the inspector read like a lab notebook, not a dashboard tile set

### 4. Astrocartography Convergence

Target file: [AstrocartographyModal.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstrocartographyModal.jsx)

Implementation steps:

- align the top chrome to the new mono-plus-serif research shell
- restyle workspace tabs and headers to match the planned Mundane/Weather shell
- keep map, atlas, intersections, and report logic intact
- avoid refactoring map controls until the shared research primitives are stable

This pass has already started: Astrocartography top chrome and workspace headers were adjusted to match the new direction.

## Delivery Order

1. Extract shared theme and chrome primitives.
2. Refactor `MundaneScanWorkspace.jsx`.
3. Refactor `WeatherWorkspace.jsx` scan mode.
4. Refactor `MundaneWorkspace.jsx` analysis mode.
5. Refactor `WeatherWorkspace.jsx` analysis mode.
6. Do a second Astrocartography polish pass once the shared primitives are proven.

## Testing

Frontend verification should cover:

- idle, running, partial, complete, selected, and error states
- mode switches between scan and analysis
- selected-row to inspector synchronization
- responsive behavior at desktop and narrow laptop widths

Target tests:

- `frontend/src/tests/astrocartographyModal.test.jsx`
- the existing Mundane and Weather UI tests, plus new state-based rendering tests if gaps remain
