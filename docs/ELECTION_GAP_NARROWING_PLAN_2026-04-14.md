Date: 2026-04-14
Scope: Election feature gap narrowing from the current workflow audit baseline.

# Objective

Narrow the gap between the current election scan engine and the product surface without changing the matter scorers blindly.

The immediate priority is not backend scoring. It is exposing the backend scan shape the engine already computes so users can read the scan as a time series instead of a flat ranked list.

# Current Gaps

1. The frontend renders only `top` ranked rows and ignores backend `series`.
2. The scan has progress but no visual timeline for where pressure rises, clusters, or falls across the scan window.
3. Natal context is partially available in the backend but narrowly exposed in the UI.
4. Matter models are heterogeneous, but the product surface treats them as if they all have the same confidence and the same scan semantics.
5. Validation is structural only; there is no benchmark-first workflow equivalent to the newer mundane and weather branches.

# Narrowing Plan

## Phase A — Frontend Series Visualization

Goal: make the election scan readable as a scan.

Deliverables:
- Render the backend `series` payload in the modal.
- Add a timeline view showing retained scan rows across time.
- Add a selected-window detail surface tied to timeline interaction.
- Add peak-window shortcuts derived from series, not only from ranked `top` rows.
- Keep the existing ranked result list as a secondary output, not the only output.

Acceptance:
- A user can see where score concentration forms across the window.
- A user can inspect a specific retained timestamp without relying only on the top list.
- Timeline, selected window, and top rows all use the same underlying scan payload.

Priority:
- Immediate.

## Phase B — Scan Contract Stabilization

Goal: stop relying on accidental row semantics.

Deliverables:
- Make the election scan payload contract explicit:
  - `top`
  - `series`
  - `stats`
- Document retention semantics for `series_retained` vs `series_dropped`.
- If needed later, add explicit backend peak-window summaries instead of deriving them ad hoc in the UI.

Acceptance:
- Frontend does not need to infer hidden meaning from raw rows beyond timestamp, score, and tags.

Priority:
- After Phase A if the UI needs stronger guarantees.

## Phase C — Workflow Validation Benchmarks

Goal: validate scan behavior before tuning election scoring.

Deliverables:
- Add benchmark cases for exact-vs-scan consistency.
- Add a small documented hindcast set for selected election matters.
- Add a benchmark runner and dataset validator similar to the mundane and weather branches.

Acceptance:
- We can answer whether scan ranking is stable and whether it highlights historically plausible windows.

Priority:
- After the scan is readable in the frontend.

## Phase D — Natal Context Surface Rationalization

Goal: expose natal support honestly.

Deliverables:
- Make it explicit in the UI which matters are using natal promise or natal overlays.
- Decide whether to keep saved-snap-only natal input or widen the input path.
- Separate “no natal,” “natal helper,” and “natal gate” behavior in the UI copy and result surface.

Acceptance:
- Users can see when natal support is active and what kind of role it is playing.

Priority:
- After benchmarks start, not before.

## Phase E — Matter-by-Matter Model Consistency Review

Goal: review scoring maturity only after workflow and scan visibility are stable.

Deliverables:
- Identify which election matters behave like strict prohibition models.
- Identify which behave like lighter additive models.
- Prioritize benchmark-backed tuning only where failures or weak scans are measurable.

Acceptance:
- No score tuning without a measurable workflow or benchmark reason.

Priority:
- Last.

# Implementation Order

1. Phase A — frontend series visualization
2. Phase B — payload/contract stabilization if Phase A exposes ambiguity
3. Phase C — workflow validation benchmarks
4. Phase D — natal context surface rationalization
5. Phase E — matter-by-matter model consistency review

# Decision

Phase A is the correct next move and should be implemented before any new election benchmarking or scorer tuning.
