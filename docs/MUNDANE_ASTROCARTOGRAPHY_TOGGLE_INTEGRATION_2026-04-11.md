# Mundane Toggle Integration

## Decision

The mundane frontend should not ship as a second top-level modal parallel to astrocartography.

It should live inside the existing astrocartography entry surface as an analysis-mode toggle:

- `Astrocartography`
- `Mundane`

## Reason

The two features share the same frontend shell characteristics:

- premium modal entry from AstroClock
- left-rail controls
- large center workspace
- right-rail interpretation/details
- research-style inspection flow rather than one-click chart output

Creating a second modal would duplicate:

- modal lifecycle
- realtime pause and resume behavior
- workspace chrome
- visual language and control layout

That duplication would raise maintenance cost without adding any product value.

## Boundary

The shell is shared.

The semantics are not shared.

Astrocartography remains:

- natal snap first
- location and line based
- goal-driven place scoring

Mundane becomes:

- public-event and polity analysis
- chart-type and domain selection
- benchmark-calibrated result display
- explicit research-status presentation

## Frontend Shape

`frontend/src/features/astroclock/AstrocartographyModal.jsx`

- remains the single modal entrypoint
- owns the analysis-mode toggle
- renders the astrocartography workspace when mode is `astrocartography`
- renders the mundane workspace when mode is `mundane`

`frontend/src/features/astroclock/MundaneWorkspace.jsx`

- owns mundane catalog loading
- owns chart-type / domain / polity controls
- calls the mundane backend endpoints
- renders:
  - context summary
  - framework layer
  - trigger layer
  - activation layer
  - domain assessment
  - calibration metadata
  - source and research notes

`frontend/src/features/astroclock/api.mjs`

- adds:
  - `listMundaneChartTypes`
  - `resolveMundaneContext`
  - `analyzeMundane`

## UI Rules

- Do not present mundane as a location score.
- Do not hide calibration.
- Always show:
  - calibrated score
  - raw score
  - coverage tier
  - benchmark case count
  - source breadth
  - research flags

## Current Scope

The first frontend cut should expose these domain lenses:

- `war_conflict`
- `government_stability`
- `diplomacy_foreign_affairs`
- `public_health`
- `civil_unrest`
- `finance_economy`

The frontend should treat `civil_unrest` and `finance_economy` as usable but visibly thinner than `government_stability` and `public_health`.

## Expected User Outcome

Users open one advanced workspace from AstroClock and then choose whether they want:

- place-based astrocartography analysis
- public-event mundane analysis

The entry feels unified, but the interpretation model remains domain-correct.
