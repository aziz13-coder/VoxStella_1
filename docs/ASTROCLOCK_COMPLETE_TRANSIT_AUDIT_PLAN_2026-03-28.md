# Astro Clock Complete Transit Audit Plan
## 2026-03-28

This note turns the transit audit into a bounded workplan instead of a loose series of wording passes.

The purpose is not only to clean labels.

The purpose is to make the full transit feature more defensible across:
- source alignment
- backend algorithm correctness
- route parity
- frontend rendering
- workflow behavior
- claim boundaries

## Audit phases

### Phase 1. Source baseline

Goal:
- extract the Morin-facing baseline from the converted books

Output:
- house-domain baseline
- determination baseline
- concurrence baseline
- transit role relative to directions and revolutions
- admissible keyword families

Primary docs:
- `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md`
- `docs/ASTROCLOCK_TRANSIT_KEYWORD_SOURCE_AUDIT_2026-03-27.md`

### Phase 2. Event-family audit

Goal:
- review every major `eventType` family and make its wording more source-sensitive

Main families:
- career / honors
- relationship / legal / open-enemy
- wealth / inheritance / speculation
- home / parents / inheritances
- journeys / brothers / relations
- religion / study / publication
- health / illness / service
- crisis / death / imprisonment / war

Success condition:
- the backend wording and frontend chips do not sound narrower or more modern than the source justifies

### Phase 3. Backend algorithm audit

Goal:
- verify hit generation, determination, ranking, critical-signal extraction, tone, and peak selection

Primary code:
- `backend/transits_morin.py`
- `backend/astro_clock_api.py`

Questions:
- does exact-time share the same core logic as scan, stream, and predictor?
- are event families over-broad?
- does ranking surface the correct determined row?
- are predictor windows real contiguous support windows?
- do crisis and legal families stay high-bar?

### Phase 4. Route contract audit

Goal:
- keep semantics stable across all transit APIs

Routes in scope:
- `/api/astro-clock/transits`
- `/api/astro-clock/predictor`
- `/api/astro-clock/transits/window`
- `/api/astro-clock/transits/window/stream`

Success condition:
- the same inputs yield consistent semantics across routes

### Phase 5. Replay corpus audit

Goal:
- validate the engine against real public dated events

Current replay slices:
- public authority
- public honor
- predictor localization
- stream retention
- public crisis
- marriage support
- pre-event controls
- war response
- recent war response

Success condition:
- each promoted slice has a narrow and honest claim boundary

### Phase 6. Frontend rendering audit

Goal:
- verify the UI shows what the backend actually returns

Surfaces:
- scan graph
- top peaks
- exact-time card
- critical signals
- predictor support windows
- detailed row table

Success condition:
- backend and frontend agree on the principal visible signal

Latest source pass completed:
- exact-time `Critical Signals` no longer mixes unrelated crisis families in the same summary by default
- the summary now chooses a coherent crisis family for the current row, then renders only that family's chips and descriptions
- this keeps war/open-enemy rows from being visually buried under unrelated accident/death chips when both families coexist at the same timestamp
- remaining live-instance risk: a stale local backend can still return older exact-route payloads with missing per-hit `prediction` metadata, which weakens frontend parity until that backend instance is restarted or replaced

Latest predictor pass completed:
- predictor support windows now merge equivalent event-family windows that differ only by overlapping transit variants
- merged predictor windows preserve `supporting_transits`, so the UI can show one primary support window plus its reinforcing transit variants
- the per-step predictor pool was widened from 16 to 32 hits per target type to reduce family dropout in scan/predictor flows
- predictor window ordering now favors family diversity after merge, so one event family does not monopolize the top list through repeated near-identical variants

### Phase 7. Workflow and performance audit

Goal:
- verify the feature is usable, not only correct in theory

Checks:
- default flags
- scan-step ergonomics
- predictor timeout behavior
- exact-time compute workflow
- contradictory empty states
- graph peak readability
- stream-ticket fallback behavior when no usable license token is available

### Phase 8. Final claim-boundary report

Goal:
- state clearly what the transit feature can and cannot claim after the audit

Output:
- fixed bugs
- accepted limitations
- safe product claims
- risky areas still open

## Current implementation order

1. Complete the event-family wording passes.
2. Re-run targeted backend and frontend tests after each family cluster.
3. Stop wording churn once the major families are source-sensitive.
4. Do a final ranking/parity pass only if the principal visible signal is still wrong.
5. Close with a final audit report.

## Current focus

The current implementation focus has moved from wording to ranking/parity:
- row-level event-family selection
- principal-signal drift between mixed candidate families
- keeping exact-time, scan, predictor, and stream aligned on the same chosen family

Latest workflow pass completed:
- the Astro Clock streaming helpers no longer ask the backend for a stream ticket when the renderer already knows there is no usable license token
- this avoids noisy `402` stream-ticket failures in unlicensed or not-yet-activated states while preserving the existing non-stream fallback path
- licensed streaming behavior is unchanged

The first ranking/parity pass is documented in:
- `docs/ASTROCLOCK_TRANSIT_RANKING_PARITY_AUDIT_2026-03-28.md`

## Success criteria

The transit audit is done when:
- every major event family has a documented source-facing rationale
- backend and frontend labels match that rationale
- the replay corpus still passes
- the frontend renders the same principal signal the backend actually returns
- the remaining limitations are documented instead of hand-waved

## Current status

The current audit cycle is complete enough to close.

The closing report is:
- `docs/ASTROCLOCK_FINAL_TRANSIT_AUDIT_REPORT_2026-03-28.md`
