# AstroClock Exploration For Synastry

Date: 2026-04-02

## Purpose

This document maps the current AstroClock workflow before introducing a synastry feature.

The goal is to identify:

1. What AstroClock already computes once and reuses well
2. What the existing feature stack expects from chart data
3. Which parts a future synastry feature should reuse directly
4. Which parts should remain feature-specific and not be copied blindly

This is an exploration pass only. No synastry implementation is included here.

## High-Level Architecture

AstroClock is not a separate astrology engine.

It is a feature shell built on top of the existing horary engine plus a feature-oriented API layer:

- Chart generation:
  - `backend/astro_clock_engine.py`
  - wraps `HoraryEngine` and produces a normalized chart result for realtime or manual contexts
- AstroClock API layer:
  - `backend/astro_clock_api.py`
  - turns a chart snapshot into dashboard data, snaps, trait profiles, transit scans, election scans, forensic outputs, and research-mode endpoints
- Frontend orchestration:
  - `frontend/src/features/astroclock/AstroClock.jsx`
  - owns the active chart context, switching between realtime/manual/snaps, and opens feature modals

The key design fact is that AstroClock features mostly share a chart snapshot pipeline and then diverge into their own interpretation logic.

## Core Workflow

### 1. AstroClock entry and active context

The app mounts AstroClock through:

- `frontend/src/App.jsx`
  - renders `AstroClockPage`

AstroClock keeps one active chart context in the shell:

- mode: `realtime` or `manual`
- active timestamp
- location
- timezone
- house system
- include-modern and Morin toggles

The frontend drives that state in:

- `frontend/src/features/astroclock/AstroClock.jsx`

Key workflow:

1. User enters AstroClock
2. Shell starts in realtime unless manual/snap context is applied
3. Frontend requests dashboard data from `/api/astro-clock/dashboard`
4. Frontend requests planetary hours from `/api/astro-clock/planetary-hours`
5. In realtime mode, AstroClock uses SSE when possible and falls back to polling
6. Feature modals pause realtime, freeze the clock to a deterministic manual snapshot, then resume realtime on close

This pause/freeze behavior is important because many AstroClock features assume a stable chart while the modal is open.

### 2. Dashboard payload generation

The shared dashboard payload is assembled in:

- `backend/astro_clock_api.py`
  - `_build_dashboard_payload(...)`

That payload enriches the raw chart with:

- planets
- moon state
- moon VoC timeline
- top aspects
- Morin aspects
- fixed star hits
- Arabic parts
- sect
- metrics
- house rulers
- receptions
- special degrees
- cusp aspects

This is the main reusable chart-analysis layer for AstroClock.

### 3. Chart bundle pattern

The most important reusable backend abstraction is the chart bundle:

- `backend/astro_clock_api.py`
  - `_build_chart_bundle(...)`
  - `_compute_chart_bundle_for(...)`
  - `_compute_chart_for(...)`

The bundle carries:

- `chart_result`
- `chart_data`
- `meta`
- `raw_chart`

This is already the internal pattern used whenever AstroClock needs a chart outside the live dashboard flow.

For synastry, this is the strongest existing reuse point.

### 4. Snap workflow

Snaps are stored in:

- `backend/snaps_store.py`

AstroClock creates and reads snaps through:

- `/api/astro-clock/snap`
- `/api/astro-clock/snaps`
- `/api/astro-clock/snaps/<id>`

Each snap stores:

- effective datetime
- location
- summary
- full dashboard payload

This matters for synastry because AstroClock already has a UX and persistence pattern for selecting a chart source without retyping birth data every time.

## Existing Feature Workflows

### Trait Profile

Frontend:

- `frontend/src/features/astroclock/TraitProfileModal.jsx`

Backend:

- `/api/astro-clock/traits/profile`

Workflow:

1. Modal inherits the active AstroClock chart context
2. Backend resolves that context using `_data_for_request_clock_context(...)`
3. Backend rebuilds dashboard data for the same chart
4. Backend computes:
   - `compute_metrics(...)`
   - `compute_house_influences(...)`
   - `compute_sect_info(...)`
   - trait-engine evaluation
5. Backend returns both profile output and a `chart_snapshot`

Reuse pattern:

- Trait Profile does not own chart calculation
- It consumes the shared chart snapshot and adds a feature-specific scoring layer

### Transits

Frontend:

- `frontend/src/features/astroclock/TransitsModal.jsx`

Backend:

- `/api/astro-clock/transits`
- `/api/astro-clock/transits/window`
- `/api/astro-clock/predictor`
- `/api/astro-clock/context/auto`
- export and streaming variants

Workflow:

1. User selects a natal source:
   - manual natal datetime/location
   - or saved snap
2. User selects a transit time or time window
3. Backend resolves natal chart via `_natal_bundle_from_query(...)`
4. Transit engine computes one-to-natal or windowed transit hits
5. Predictor logic groups and ranks hits into event predictions

Important architectural point:

Transits already implement a dual-context request model:

- chart A = natal chart
- chart B = transit chart/time series

That dual-input pattern is highly relevant for synastry.

What is reusable from transits:

- dual-chart request shape
- manual-vs-snap source selection UX
- chart bundle resolution for the fixed chart
- scan/export/stream patterns if synastry later needs batch comparison

What is not directly reusable:

- Morin transit significance logic
- event prediction grouping
- predictor family/ranking heuristics

Those are event-oriented, not relationship-oriented.

### Election

Frontend:

- `frontend/src/features/astroclock/ElectionModal.jsx`

Backend:

- `/api/astro-clock/election/validate`
- `/api/astro-clock/election/suggest/stream`

Workflow:

1. User defines a time window, location, and election matter
2. Backend iterates through time
3. For each step, backend computes a chart using `_compute_chart_for(...)`
4. Matter-specific scorers in `backend/election.py` evaluate the chart
5. Optional natal context can enrich election scoring

Reuse pattern:

- Election reuses chart generation and optional natal context
- The scorers are matter-specific and intentionally separate from the shared chart pipeline

This is the right model for synastry too:

- shared chart acquisition
- dedicated synastry scoring/interpretation layer

## Reuse Map For Synastry

### Reuse directly

These are the best existing building blocks for synastry:

1. Chart bundle computation
   - `backend/astro_clock_api.py`
   - `_compute_chart_bundle_for(...)`
   - `_compute_chart_for(...)`

2. Active clock-context resolution
   - `_data_for_request_clock_context(...)`
   - useful if synastry wants to compare the active AstroClock chart against another stored/manual chart

3. Snap persistence and selection
   - `backend/snaps_store.py`
   - current frontend snap-selection patterns in `TransitsModal.jsx` and `ElectionModal.jsx`

4. Shared chart enrichments from dashboard payload
   - aspects
   - receptions
   - house rulers
   - fixed stars
   - sect
   - special degrees
   - metrics

5. Traditional reception logic
   - existing reception extraction in `backend/astro_clock_api.py`
   - fallback `TraditionalReceptionCalculator` usage in forensic logic

6. Aspect and pattern infrastructure
   - `compute_morin_aspects(...)`
   - dashboard aspect normalization
   - existing aspect rendering in AstroClock UI

7. House-system/timezone/location normalization
   - already solved repeatedly in AstroClock and should not be reimplemented inside synastry

### Reuse partially

These are useful patterns, but not drop-in logic:

1. Transits modal dual-source workflow
   - good UX precedent for person A vs person B
   - backend semantics must change from transit-to-natal into chart-to-chart

2. Trait Profile metrics
   - useful for “how each chart behaves” sections
   - less suitable for relationship compatibility scoring by themselves

3. Election scoring pattern
   - good example of “shared chart + dedicated scorer”
   - scorers themselves are not reusable for synastry

### Do not reuse as the synastry core

These should not become the core synastry algorithm:

1. Transit predictor/event-family logic
   - designed for forecasting events across time windows

2. Election matter scorers
   - designed for date selection, not mutual-chart comparison

3. Forensic case rules
   - some relationship analysis exists there, but the forensic domain model is not a compatibility model

## What Synastry Can Likely Be In This Architecture

The cleanest fit is:

1. A new AstroClock feature modal or page
2. A dedicated backend endpoint family under `/api/astro-clock/...`
3. Two chart bundles as inputs:
   - person A
   - person B
4. A synastry analysis layer that consumes both normalized charts and returns:
   - cross-chart aspects
   - mutual receptions across charts
   - overlay by houses
   - affinity/tension themes
   - optional domain-focused summaries

The feature should not start by inventing a new low-level ephemeris pipeline.

It should instead:

1. compute chart A through the existing chart bundle path
2. compute chart B through the existing chart bundle path
3. run a dedicated synastry interpreter over the two bundles

## Best Reuse Strategy

### Recommended backend shape

Add a new internal helper shaped like:

- `resolve_chart_source(source_spec) -> chart_bundle`

where a source can be:

- active AstroClock context
- saved snap
- manual datetime/location/timezone

Then add a synastry-specific service that accepts:

- `chart_a_bundle`
- `chart_b_bundle`
- options

and returns:

- pair metadata
- cross-chart aspect matrix
- house overlays
- receptions / rulership links
- summary blocks
- optional score buckets

### Recommended frontend shape

Base the UX on patterns already proven in `TransitsModal.jsx`:

- source A:
  - active chart
  - saved snap
  - manual birth data
- source B:
  - saved snap
  - manual birth data

Then keep the output visually close to AstroClock:

- aspect list / matrix
- top supportive links
- top friction links
- house overlay highlights
- concise summary tiles

## What Already Exists That Helps Relationship-Oriented Logic

There is no current synastry feature, but some relationship-adjacent logic already exists:

- receptions extraction in dashboard and forensic paths
- relationship-focused fixed-star lookups in forensic output
- house-ruler and aspect interpretation infrastructure
- saved-snap selection UI

This means synastry is new as a feature, but not new as a data-shape problem.

## Main Constraints

1. AstroClock currently assumes one active chart at the shell level
   - synastry introduces a true two-chart feature

2. The API currently has strong “active chart” and “natal chart” concepts
   - synastry should avoid hard-coding one party as “natal” unless that is a deliberate product choice

3. `frontend/src/features/astroclock/AstroClock.jsx` is already large
   - synastry should be introduced as its own modal/page and not merged into the shell component directly

4. `backend/astro_clock_api.py` is also large
   - synastry should likely get its own backend module or service file even if the route is registered from the AstroClock blueprint

## Recommended Next Exploration Questions

Before implementation, the next design pass should answer:

1. Is synastry positioned as:
   - compatibility
   - relationship dynamics
   - marriage potential
   - business partnership
   - general person-to-person comparison

2. Should the feature support:
   - active chart vs saved chart
   - saved chart vs saved chart
   - manual chart vs manual chart
   - all three

3. What is the primary output:
   - score
   - narrative summary
   - aspect matrix
   - house overlays
   - domain-specific sections

4. Should synastry use:
   - classical planets only
   - optional modern planets
   - optional asteroid/fixed-star overlays

5. Do we want one reusable pair-analysis core that can later support:
   - synastry
   - composite chart
   - relationship transits
   - partnership election support

## Recommended Direction

The best next step is not implementation yet.

The next step should be a synastry feature design memo that defines:

1. input model for chart A and chart B
2. first-version analysis outputs
3. reusable backend service boundaries
4. what is borrowed from transits UX vs what is unique to synastry

That will let the implementation reuse AstroClock’s chart and context infrastructure without inheriting the wrong scoring logic from transits or elections.
