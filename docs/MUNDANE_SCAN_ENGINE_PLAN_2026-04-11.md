# Mundane Scan Engine Plan

## Goal

Add a research-gated mundane scan workflow that can answer:

- where in a region the selected mundane pattern is strongest
- when inside a time window the selected pattern is strongest
- why the engine ranked those place or place-time cells highest

This is not a generic prediction surface.

It is a structured scan layer on top of the existing mundane context and domain engine.

## Product Shape

The scan feature should live inside the existing mundane workspace as an advanced mode, not as a separate product surface.

It should support two scan modes:

- `spatial_scan`
  - fixed event time
  - scan a region across space only
- `spatiotemporal_scan`
  - fixed region plus time window
  - scan across both space and time

The first user-facing question it answers is:

- at this time, where is the strongest candidate hotspot?

The second, more expensive question is:

- across this region and time window, where and when is the strongest candidate hotspot?

## Preconditions

This feature only makes sense because the following already exist:

- mundane chart-type resolution
- mundane domain evaluation
- benchmark calibration output
- astrocartography atlas and regional search architecture

The scan engine should reuse those assets rather than invent a new scoring family from scratch.

## Scan-Capable Chart Types

Do not allow every chart type to be scanned equally.

First-pass scan-capable types:

- `war_event`
- `eclipse`
- `lunation`
- `aries_ingress`

Do not use as a standalone scan basis in the first cut:

- `national_chart`

`national_chart` should remain an overlay or polity-reference layer, not the thing being scanned across geography by itself.

## Scan-Capable Domains

Initial scan domains:

- `war_conflict`
- `government_stability`
- `diplomacy_foreign_affairs`
- `public_health`
- `civil_unrest`
- `finance_economy`

The UI and API must keep research flags visible, especially for thinner domains.

## Inputs

Required scanner inputs:

- `chart_type`
- `domain`
- `polity_id`
- `national_chart_id` when available
- `scan_mode`
- `region`
- `location_context_type`

Then either:

- `fixed_datetime` for `spatial_scan`

or:

- `start_datetime`
- `end_datetime`
- `time_step`

for `spatiotemporal_scan`

Additional operational inputs:

- `grid_resolution`
- `top_k`
- `minimum_score`
- `visibility_scope`
- `source_preference`

## Outputs

The engine should not return only a map or only a score.

Each result row should include:

- `rank`
- `location`
- `datetime`
- `score`
- `level`
- `scan_level`
- `matched_rules`
- `primary_signals`
- `calibration`
- `research_flags`

The output must stay explainable.

`level` and `scan_level` should not be collapsed into one field.

- `level` is the absolute domain level from the source-backed mundane rule engine
- `scan_level` is the relative rank band inside one returned scan set

This keeps the doctrine honest. The books support chart judgment, but they do not define UI-grade hotspot bands across a returned atlas scan. Relative scan banding should therefore be benchmark-calibrated runtime metadata rather than presented as direct doctrine.

The correct product language is:

- candidate hotspots
- strongest scanned cells
- ranked results

Not:

- definitive prediction
- certain outbreak point
- guaranteed event timing

## Architecture

The scanner should be built as a sibling service to the mundane analyzer, reusing current runtime pieces.

Recommended backend files:

- `backend/mundane_scan_models.py`
- `backend/mundane_scan_service.py`
- `backend/mundane_scan_grid.py`

Possible API endpoints:

- `/api/astro-clock/mundane/scan/regions`
- `/api/astro-clock/mundane/scan/run`
- `/api/astro-clock/mundane/scan/status`
- `/api/astro-clock/mundane/scan/result`

Preferred runtime strategy:

1. coarse region scan
2. retain top candidate cells
3. optional refinement pass on top cells only

This avoids an expensive full-resolution search over every place-time combination.

## Reuse From Existing System

Use these existing layers:

- astrocartography atlas and regional search pattern
- mundane `resolve_context`
- mundane `analyze_context`
- benchmark calibration profile

Do not create:

- a second unrelated geography engine
- a scan result without doctrine notes
- a hidden score without calibration metadata

## Guardrails

The scan feature needs explicit constraints.

Required guardrails:

- cap region resolution
- cap time-window size
- cap number of returned cells
- show calibration on every returned result
- preserve research flags per result
- reject unsupported chart-type/domain combinations

Important UX rule:

If the calibration is thin, the UI must say so directly.

## Risks

### False Precision

The engine can always rank cells, even when doctrine support is only moderate.

Mitigation:

- always expose calibration
- always expose research gaps
- use candidate language, not certainty language

### Runtime Cost

Region x time scanning can become expensive quickly.

Mitigation:

- coarse-to-fine search
- bounded resolution
- async runs for larger scans

### Doctrinal Overreach

Some chart types and domains are more scan-safe than others.

Mitigation:

- restrict the first implementation scope
- keep thin doctrines research-gated

## Recommended Implementation Sequence

### Phase 1: Design And Contract

Deliverables:

- request model
- result schema
- scan-mode rules
- allowed chart-type/domain matrix

### Phase 2: Region Catalog And Grid

Deliverables:

- region definitions
- coarse scan grid builder
- spatial cell normalization

### Phase 3: Scanner Service

Deliverables:

- `run_spatial_scan`
- `run_spatiotemporal_scan`
- score aggregation from mundane analysis output

### Phase 4: API Surface

Deliverables:

- scan endpoints
- async status handling for large runs
- stable serialized result payload

### Phase 5: Frontend Workspace Integration

Deliverables:

- scan mode selector inside the mundane workspace
- fixed-time and time-window forms
- ranked results list
- map or regional table view
- result inspector with rules, signals, and calibration

## Acceptance Criteria

The first scanner slice is acceptable only if:

1. it reuses the mundane analyzer rather than bypassing it
2. every result is explainable
3. every result carries calibration and research flags
4. runtime is bounded by explicit scan limits
5. unsupported scan requests are rejected clearly

## Recommendation

This is a valid next feature after the current mundane workspace.

It should be treated as:

- a scan engine
- a hotspot ranking tool
- a research workspace extension

It should not be treated as:

- a definitive event predictor
- a hidden black-box scoring system
