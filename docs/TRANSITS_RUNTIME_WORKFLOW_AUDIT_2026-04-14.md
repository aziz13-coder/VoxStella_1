# Transits Runtime Workflow Audit
Date: 2026-04-14

## Scope

This audit describes the current transits feature as it exists in source today:

- frontend workflow
- API path map
- backend runtime pipeline
- rule layers and scoring flow
- comparison against the local Morin specification documents
- current technical and methodological gaps

This is a current-state report. It does not change runtime behavior.

## High-Level Summary

The transits feature is not a simple "show current aspects" tool.

It is a layered Morin-style pipeline:

1. resolve natal context
2. compute raw transits to natal targets
3. enrich hits with determination and concordance context
4. derive event-like prediction objects
5. optionally scan a time window
6. optionally aggregate the scan into ranked predictions and peaks
7. optionally stream progress and export the result

Architecturally, the strongest part is the backend engine layering. The weakest part is separation of concerns: one large backend module mixes geometry, significance, event inference, localization, and prediction shaping.

## Frontend Workflow

Primary entry point:

- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/TransitsModal.jsx`

The modal currently supports three practical workflows.

### 1. Single-Time Transit Analysis

User inputs:

- natal source:
  - manual natal date/time/location/timezone
  - or saved snap
- transit timestamp
- model toggles:
  - modern planets
  - natal modern planets
  - cusps
  - antiscia
  - lots
- optional focus filters:
  - focus houses
  - focus planets
  - sensitive houses
  - sensitive planets

Behavior:

- frontend builds a single timestamp request
- calls `AstroClockAPI.getTransits(...)`
- sorts returned transits by significance and prediction score
- displays:
  - transit hits
  - predictions
  - revolution context

### 2. Window Scan

User inputs:

- same natal source
- start/end window, or center plus default range
- step size in minutes
- same feature toggles
- optional context-window filters:
  - PD
  - progressions
  - solar arc

Behavior:

- frontend builds a window request
- prefers SSE stream via `createTransitsWindowStream(...)`
- falls back to `getTransitsWindow(...)`
- accumulates time-series rows during stream progress
- stores:
  - `series`
  - `peaks`
  - `context_window`
  - per-row predictions

### 3. Predictor / Ranked Event Windows

User inputs:

- same natal source
- predictor window
- same transit filters
- optional context windows

Behavior:

- frontend calls predictor route
- backend performs a transit-window scan first
- then aggregates row-level predictions into ranked prediction groups

This is important: predictor is currently built on top of the scan engine, not on a separate predictive model.

### 4. Streaming and Export

The frontend also supports:

- SSE streaming for long scans
- exact transit CSV export
- window export CSV

## API Path Map

Current backend endpoints under `backend/astro_clock_api.py`:

- `/api/astro-clock/determinations`
  - returns natal determination objects
- `/api/astro-clock/transits`
  - exact single-time Morin transit computation
- `/api/astro-clock/transits/window`
  - window scan with ranked rows, peaks, and prediction rows
- `/api/astro-clock/predictor`
  - ranked event prediction groups built from window-scan output
- `/api/astro-clock/transits/window/stream`
  - SSE progress stream for window scan
- `/api/astro-clock/transits/export`
  - exact export
- `/api/astro-clock/transits/window/export`
  - window export

Operationally:

- exact compute is direct
- window scan is the central runtime path
- predictor is a higher-order aggregation path built from window scan
- stream is an alternate transport for window scan

## Backend Runtime Pipeline

Core implementation lives mainly in:

- `backend/transits_morin.py`
- `backend/astro_clock_api.py`
- `backend/context_layers.py`

### Layer 1. Natal Context Resolution

The API first resolves natal context from:

- saved snap
- or explicit natal datetime/location/timezone/house system

That becomes natal chart data plus metadata.

### Layer 2. Raw Morin Transit Computation

Core function:

- `compute_morin_transits_to_natal(...)`

This computes transiting planets against natal targets:

- natal planets
- cusps and angles
- antiscia and contra-antiscia
- lots

The engine considers:

- orb
- partile status
- aspect type
- phase
- direction
- target type
- effective window
- base score

This is the raw geometry and immediate scoring layer.

### Layer 3. Determination and Concordance Enrichment

After raw hits are computed, the backend enriches them with Morin-style context:

- natal determination alignment
- active primary direction windows
- solar revolution state
- lunar revolution state
- timing and concordance factors

Important fields added at this stage include:

- determination strength
- quality score
- quality label
- concordance object
- overall significance
- confidence

This is the doctrinal center of the runtime.

### Layer 4. Semantic/Event Inference

The engine then derives higher-level event semantics from enriched hits.

This includes:

- event domain
- event type
- target life area
- supporting signals
- event-oriented description tokens

This logic is extensive and currently lives in the same large module as the geometry and significance rules.

### Layer 5. Window Scan

Core function:

- `scan_morin_transits_window(...)`

This repeatedly evaluates exact transit logic across a time window and step interval.

Per row it produces:

- timestamp
- count of hits
- top hits
- prediction-support hits
- top planets
- top cusps/points
- step score
- tone

This scan function is the operational backbone for both visual timeline scans and predictor output.

### Layer 6. Predictor Aggregation

The API predictor route:

1. runs the scan
2. attaches row predictions
3. aggregates row predictions into groups
4. derives peak rows
5. ranks prediction groups for presentation

So predictor is not a separate transit theory engine. It is a structured aggregation layer above the scan.

### Layer 7. Streaming

The stream route mirrors window scan behavior but emits progress incrementally:

- progress events with partial rows
- done event with final series and peaks

This keeps frontend scans interactive without changing the underlying logic.

## Rules and Algorithm Layers

### What the engine is actually optimizing for

The runtime is not only ranking by raw aspect closeness.

The current scoring stack effectively combines:

1. radical determination
2. target relevance
3. aspect strength
4. natal condition
5. revolution state
6. direction concordance
7. clustering / mutual strengthening
8. timing support

This is substantially closer to the Morin doctrine documents than a modern cookbook transit engine.

### What the local doctrine documents emphasize

From `morin_transit_engine_specification(1).md`:

- determinations first
- directions next
- solar and lunar revolutions as context
- transits as triggers
- concordance as ranking filter

From `morin_transit_quality_determination(2).md`:

- a transit is not judged mainly by:
  - "benefic planet"
  - "easy aspect"
- it is judged mainly by:
  - radical determination
  - target significance
  - context

### Where the current runtime matches the sources

Strong alignment:

- radical determination is treated as primary
- concordance is explicit
- solar/lunar revolution support is included
- transit hits are not interpreted in isolation
- event predictions are downstream from determination and concordance

### Where the current runtime is only partial

Partial alignment:

- `context_layers.py` still treats progressions largely as stubbed helper windows
- the revolution/context stack is present, but not fully modularized as separate chart engines
- predictor is practical, but not doctrinally clean as a separate layer

### Where the implementation is overgrown

The main problem is not absence of theory. It is over-coupling.

`transits_morin.py` currently mixes:

- geometry
- target modeling
- determination logic
- concordance logic
- significance scoring
- event token derivation
- localized prediction shaping

That makes the feature harder to validate, benchmark, or refactor.

## Inputs

### Exact Analysis Inputs

- natal source:
  - snap id
  - or natal datetime/location/timezone
- house system
- transit datetime
- toggles:
  - include modern
  - include natal modern
  - include cusps
  - include antiscia
  - include lots
- focus filters:
  - focus house
  - focus planet
  - sensitive house
  - sensitive planet

### Window Scan Inputs

All exact-analysis inputs, plus:

- start/end
  - or center/range_hours
- step_minutes
- filters:
  - transiting
  - natal
  - aspect
- context windows:
  - PD
  - SA
  - progressions

### Predictor Inputs

All scan inputs, plus:

- limit
- include_series

## Outputs

### Exact Analysis Output

- natal metadata
- transit timestamp
- ranked transits
- predictions
- revolution context bundle

### Window Scan Output

- `series`
- `peaks`
- `context_window`
- `natal`
- per-row predictions
- ranked predictions
- context filters

### Predictor Output

- natal metadata
- scan window
- observer context
- context filters
- ranked predictions
- grouped predictions
- peaks
- optionally full series

## Current Technical Risks

### 1. Monolithic engine file

`backend/transits_morin.py` is too large and too mixed in responsibility.

Practical result:

- hard to reason about
- hard to benchmark per layer
- hard to isolate regressions
- hard to compare doctrinal rules with actual scoring behavior

### 2. Predictor is layered on scan, not independent

This is not necessarily wrong, but it means:

- predictor quality is downstream from scan quality
- any scan scoring bias leaks directly into predictor output

### 3. Tests are not yet workflow- or hindcast-centered

Current tests in `backend/test_transits_quality.py` mainly validate:

- doctrinal quality behavior
- label selection
- wording / rendering behavior

That is useful, but it does not answer:

- whether scan windows rank meaningful periods well
- whether predictor groups are stable
- whether the exact endpoint and scan endpoint stay semantically consistent

### 4. Frontend modal is feature-rich but dense

`TransitsModal.jsx` now carries:

- exact compute
- scan
- predictor
- export
- debug toggles
- context-window switching
- source-mode switching

That works, but it means the frontend workflow is broad and state-heavy.

### 5. Context-layer implementation is uneven

The architecture wants:

- directions
- solar returns
- lunar returns
- progressions

But the current implementation is deeper for some layers than for others. Progressions in particular appear more like helper windows than a full runtime layer.

## Source Comparison: Bottom Line

### What is substantively correct

The current system does respect the core Morin idea better than most transit tools:

- transits are triggers
- determination matters first
- context matters
- concordance matters

That part is structurally sound.

### What is only partially realized

The implementation is not as cleanly staged as the specification suggests.

The spec describes a pipeline of separate conceptual steps. The runtime often performs those steps inside one large, fused engine, which makes the doctrine harder to audit and the output harder to validate statistically.

## Recommended Next Corrections

If the goal is to improve the transits feature responsibly, the next order should be:

1. split the backend into clearer layers:
   - raw transit geometry
   - enrichment and concordance
   - event inference / prediction shaping
2. add workflow validation benchmarks:
   - exact vs scan consistency
   - predictor stability across step sizes
   - hindcast windows for selected documented cases
3. make context layers explicit by maturity:
   - full
   - partial
   - helper-only
4. reduce frontend state coupling by separating:
   - exact analysis
   - window scan
   - predictor

## Executive Assessment

Current transits runtime status:

- doctrine alignment: moderate to strong
- algorithmic layering: strong in concept
- implementation separation: weak
- current usability: high
- benchmarkability: weaker than it should be

The feature is already a serious transit engine. The problem is not that it lacks theory. The problem is that the theory, scoring, prediction shaping, and presentation are packed too tightly together.
