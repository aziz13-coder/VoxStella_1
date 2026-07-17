# AstroClock Transits Full Feature Audit Plan
## 2026-05-01

This document defines the next transits audit pass. The purpose is to check every Transits feature for technical defects, workflow breaks, source-code drift, and algorithmic/logical mismatch against the intended Morin-based model.

This is a plan, not a findings report. Confirmed issues should be recorded separately with file, line, workflow, evidence, expected behavior, and recommended regression tests.

## Audit Phases

### Phase 1. Baseline and Inventory

Status: completed in `docs/ASTROCLOCK_TRANSITS_AUDIT_PHASE1_BASELINE_2026-05-01.md`.

Purpose:
- establish the source hierarchy
- map all Transits routes, frontend API wrappers, modal handlers, backend algorithm entry points, source mirrors, and tests
- identify candidate risk areas for deeper phases without prematurely calling them confirmed bugs

Exit criteria:
- feature and route map recorded
- local Morin source baseline recorded
- implementation source files identified
- backend mirror parity checked
- existing test coverage mapped
- candidate review queue prepared for Phase 2 and Phase 3

### Phase 2. Backend Route And Contract Audit

Status: completed in `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`.

Purpose:
- compare exact, window, stream, predictor, and export route contracts
- verify parameter parsing, defaults, validation, error shapes, and response field parity
- verify stream and non-stream equivalence for matching requests
- verify bounds, cancellation, timeout, and fallback behavior

Primary outputs:
- backend technical findings
- route parity matrix
- backend regression test list

### Phase 3. Frontend Workflow And State Audit

Status: completed in `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`.

Purpose:
- trace every Transits UI workflow from user action to request payload to rendered response
- verify date/time/timezone semantics, snap handoff, scan/predictor state, stream fallback, timeline replay, exports, filters, and context-window controls
- reproduce confirmed issues with frontend tests or browser checks when needed

Primary outputs:
- frontend technical findings
- workflow parity matrix
- frontend regression test list

### Phase 4. Morin Algorithm And Source-Alignment Audit

Status: completed in `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`.

Purpose:
- compare implementation logic against the local Morin source baseline
- verify radical determination, house determination, target significance, aspect/orb treatment, agreement/contrariety, concordance/context, and ranking logic
- separate Morin-correct behavior from modern-astrology compatibility expectations

Primary outputs:
- Morin/source-alignment findings
- algorithmic risk matrix
- controlled-chart test recommendations

### Phase 5. Replay, Benchmark, And External Reference Cross-Check

Status: completed in `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`.

Purpose:
- run or inspect existing replay slices and benchmark material
- check whether promoted claims still match source-backed evidence
- use external astrology references only as secondary context for terminology, UX expectations, or product-positioning concerns

Primary outputs:
- replay/benchmark status
- external-reference notes, explicitly marked as secondary
- claim-boundary updates

### Phase 6. Findings Triage And Fix Plan

Status: completed in `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`.

Purpose:
- consolidate confirmed issues from Phases 2-5
- assign severity and dependencies
- prioritize fixes by user impact, algorithmic correctness, and implementation risk

Primary outputs:
- final audit findings report
- ordered fix plan
- test plan

### Phase 7. Implementation And Verification

Status: completed in `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`.

Purpose:
- fix confirmed issues in source files only
- mirror backend source changes when required
- run targeted backend/frontend tests
- update documentation where behavior or claim boundaries change

Primary outputs:
- source patches
- passing verification notes
- residual risk list

## Source Authority

### Primary rule source

The main interpretive and algorithmic authority is the local Morin corpus and Morin-derived implementation notes already in the repository.

Primary local sources:
- `horary_knowledge/desktop_books_text/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt`
- `horary_knowledge/desktop_books_text/toaz.info-jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl-pr_c198dcbe1e631c7e9f774ec5e70b435c.txt`
- `horary_knowledge/desktop_books_text/631070060-Jean-Baptiste-Morin-Astrologia-Gallica-book-25.txt`
- `horary_knowledge/desktop_books_text/631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt`
- `backend/morin_transit_engine_specification(1).md`
- `backend/morin_transit_quality_determination(2).md`
- `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md`
- `docs/ASTROCLOCK_COMPLETE_TRANSIT_AUDIT_PLAN_2026-03-28.md`
- `docs/ASTROCLOCK_FINAL_TRANSIT_AUDIT_REPORT_2026-03-28.md`

The source rule for this pass:
- Morin-local evidence wins over modern simplifications.
- If the code follows Morin but conflicts with a modern astrology convention, that is not automatically a bug.
- If the code claims Morin logic but implements only generic modern transit logic, that is a source-alignment issue.

### Secondary references

External astrology references are allowed as secondary comparison material. They can be used to:
- clarify terminology
- identify common expected transit behavior
- test whether UI labels are misleading to users familiar with standard astrology
- flag areas where the app should state that it is using a Morin-specific method

External references must not override a clear local Morin rule unless the audit explicitly marks the issue as a product-positioning or compatibility concern rather than a Morin-correctness bug.

### Implementation source under test

Current local source files are the implementation under test. Generated or packaged artifacts are out of scope for edits.

Backend:
- `backend/transits_morin.py`
- `backend/astro_clock_api.py`
- `backend/morin_aspects.py`
- `backend/pd_morin.py`
- `backend/astro_clock_engine.py`
- `backend/knowledge/morin_keywords.json`

Frontend:
- `frontend/src/features/astroclock/TransitsModal.jsx`
- `frontend/src/features/astroclock/api.mjs`
- related AstroClock shell/state files only when they affect Transits entry, snap handoff, timezone, or context windows

Backend mirror:
- `frontend/backend/transits_morin.py`
- `frontend/backend/astro_clock_api.py`
- `frontend/backend/morin_aspects.py`
- `frontend/backend/pd_morin.py`
- `frontend/backend/knowledge/morin_keywords.json`

Tests:
- `backend/test_astro_clock_api_transits.py`
- `backend/test_transits_quality.py`
- `frontend/src/tests/transitsModalReplay.test.jsx`
- `frontend/src/tests/astroclockApi.test.mjs`
- any replay or benchmark docs/tests directly referenced by the transits model

## Feature Inventory To Audit

### Single-time exact transit compute

User action:
- enter natal data or choose saved snap
- enter Transit Date and Transit Time
- click compute exact time

Backend route:
- `GET /api/astro-clock/transits`

Primary questions:
- Does the route construct the same natal context as scan and predictor?
- Are natal datetime, natal location, transit datetime, transit location, and timezone interpreted as the same instant the UI shows?
- Are hit rows sorted by the intended principal Morin signal, not by incidental display order?
- Are empty, invalid, or partial inputs rejected consistently?
- Does CSV export use the same hit set and metadata as exact compute?

Algorithmic checks:
- radical determination is used as the primary quality factor
- meaningful targets include planets, cusps, lots/Fortune, aspect places, and antiscia when supported
- transits through empty space are not treated as equivalent to transits to radical places
- aspect type modifies the effect rather than replacing determination
- benefic/malefic wording follows determination and concordance, not simple planet/aspect stereotypes

### Window scan

User action:
- set scan start/end or center scan around transit datetime
- select step size
- optionally include context windows
- click Scan Window

Backend routes:
- `GET /api/astro-clock/transits/window`
- `GET /api/astro-clock/transits/window/stream`

Primary questions:
- Do streaming and non-stream scans produce equivalent results for the same request?
- Are request bounds, step size, cancellation, and fallback behavior consistent?
- Does scan result ordering preserve the strongest signal per timestamp?
- Are scan peaks stable and explainable?
- Does the UI handle progress, errors, and partial stream events without stale state?

Algorithmic checks:
- step-based sampling does not claim exactness unless refined
- peak extraction does not suppress lower-frequency but stronger Morin signals
- duplicated variants are grouped without losing support information
- context windows narrow the scan honestly and do not silently replace user-selected ranges

### Predictor

User action:
- choose scan/predictor window
- run predictor
- inspect prediction groups, support windows, supporting transits, and peaks

Backend route:
- `GET /api/astro-clock/predictor`

Primary questions:
- Does predictor use the same core scan logic as window scan?
- Does predictor step auto-tuning preserve semantics instead of hiding important short-lived signals?
- Are prediction groups merged by real semantic equivalence, not only by label coincidence?
- Are support windows contiguous, correctly bounded, and displayed in the observer/chart timezone?
- Does predictor produce defensible "principal" and "supporting" signals?

Algorithmic checks:
- principal event family follows the strongest determination/concordance
- repeated weak rows do not outrank a single strong radical activation
- conflicting families are preserved as mixed or secondary instead of collapsed into an overconfident label
- the output respects Morin's hierarchy: nativity, directions/revolutions/context, then transits as triggers

### Context windows: PD, progressions, solar arc

User action:
- fill context windows
- use context in scans/predictions
- apply intersection as scan range

Backend and frontend areas:
- `frontend/src/features/astroclock/TransitsModal.jsx`
- transits route request parameters for context windows
- `backend/transits_morin.py` concordance enrichment
- `backend/pd_morin.py` where relevant

Primary questions:
- Are context windows optional, explicit, and visible to the user?
- Does enabling context actually affect backend ranking/scoring?
- Does the intersection helper produce valid start/end ranges?
- Are out-of-range or non-overlapping windows handled without misleading results?

Algorithmic checks:
- context should increase confidence for concordant signals
- context should not manufacture an event that the radical chart does not support
- conflicting context should temper or demote the transit claim

### Timeline replay and row clicks

User action:
- click a scan peak, critical row, predictor peak, or timeline timestamp
- inspect the recomputed exact-time result
- optionally click Compute Exact Time again

Frontend areas:
- `onTimelineClick`
- visible Transit Date and Transit Time fields
- exact compute request construction

Primary questions:
- Does clicking a timestamp compute the exact intended instant?
- Do visible date/time inputs stay in the chart/natal timezone rather than browser timezone?
- Does repeated clicking avoid stale selected-row state?
- Does a later manual compute replay the same instant the user clicked?

Algorithmic checks:
- exact replay must be a refinement of the selected scan instant, not a new browser-local instant
- displayed compact timestamps and input fields must use the same timezone convention

### Filters, target sets, and modern planets

User action:
- toggle modern transiting planets
- filter/select transiting planets
- inspect table and summary rows

Backend and frontend areas:
- request query params in `frontend/src/features/astroclock/api.mjs`
- route filters in `backend/astro_clock_api.py`
- hit generation in `backend/transits_morin.py`

Primary questions:
- Are classical and modern body sets explicit and consistent?
- Do filters affect backend generation, not just frontend display?
- Are filtered results still ranked correctly?
- Do exports respect the same filters?

Algorithmic checks:
- if modern bodies are included, the UI should not imply those are Morin-original authorities
- classical Morin logic should remain valid when modern bodies are disabled

### Export

User action:
- export exact transits
- export window scan

Backend routes:
- `GET /api/astro-clock/transits/export`
- `GET /api/astro-clock/transits/window/export`

Primary questions:
- Do exports enforce the same validation and scan bounds as UI routes?
- Do exported rows match the visible rows for the same request?
- Are timestamp, timezone, orb, score, event family, target, and prediction columns stable?
- Are empty exports reported clearly?

Algorithmic checks:
- exported labels should preserve principal vs secondary signal distinctions
- export should not flatten mixed or context-tempered judgments into stronger claims than the UI makes

### Error, performance, and safety behavior

Areas:
- backend validation helpers
- stream setup and fallback
- frontend loading/error state
- route timeout risk

Primary questions:
- Are oversized scans rejected before heavy work starts?
- Is stream fallback blocked or handled correctly after validation failures?
- Are bad date/time/timezone inputs rejected predictably?
- Are missing Swiss ephemeris or optional Morin modules handled without broken UI assumptions?
- Are repeated clicks/debounced scans safe?

## Technical Audit Method

1. Build a route and component map.
   - List every Transits route, frontend API wrapper, UI handler, and test.
   - Mark exact, scan, stream, predictor, export, context, and replay workflows.

2. Trace request/response contracts.
   - For each route, document accepted query params, defaults, response fields, and error shape.
   - Compare frontend request builders with backend parsers.
   - Compare exact, window, stream, predictor, and export parity.

3. Validate time semantics.
   - For each workflow, identify the instant, the display timezone, and the timezone sent to the backend.
   - Test natal timezone, transit timezone, browser timezone, UTC, DST boundaries, and invalid timezone labels.

4. Check state and workflow behavior.
   - Review loading, error, stream progress, retry/fallback, debounce, cancellation, and selected-row state.
   - Reproduce workflows with targeted tests or browser runs when needed.

5. Check source mirror parity.
   - Compare canonical backend files under `backend/**` against `frontend/backend/**`.
   - Any backend fix must be mirrored where packaging expects the frontend backend source.
   - Do not edit generated bundles.

6. Check tests for each feature.
   - Existing tests should cover at least one successful path and one failure path per route/workflow.
   - Missing regression coverage should be named in the findings report even if no bug is found.

## Algorithmic And Source-Alignment Method

1. Extract the Morin rule baseline.
   - Use the local Book 24 and Book 22 excerpts as the primary transit/direction/revolution baseline.
   - Reuse `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md` as the starting summary.

2. Map rules to implementation points.
   - radical determination
   - house determination
   - target significance
   - aspect type and orb
   - partile/exactness
   - benefic/malefic quality
   - agreement/contrariety
   - context/concordance from directions, progressions, solar arc, revolution-like windows
   - timing role of transits as triggers

3. Compare code behavior against rule intent.
   - Identify places where the code uses generic transit assumptions instead of Morin determination.
   - Identify places where ranking favors quantity over principal significance.
   - Identify places where labels overclaim prediction certainty.
   - Identify places where the UI hides uncertainty or mixed signals returned by the backend.

4. Use external references only as secondary checks.
   - Flag conflicts between Morin-specific behavior and common modern expectations as UX/documentation issues.
   - Do not mark a Morin-correct behavior as a logic bug just because an external modern source differs.

5. Test with controlled charts.
   - Use fixtures where a planet is clearly determined to a house/topic.
   - Compare good/bad outcomes where planet/aspect stereotypes would give the opposite result.
   - Include cases where transits are geometrically present but weak by Morin target rules.

## Findings Template

Each confirmed issue should be reported in this shape:

```text
Title:
Severity:
Feature/workflow:
Files/lines:
Current behavior:
Expected behavior:
Evidence:
Morin/local-source comparison:
External-reference note, if relevant:
Technical impact:
Recommended fix:
Regression test:
```

Severity guide:
- P0: data corruption, app-breaking route failure, or runaway backend work likely in normal use
- P1: wrong instant, wrong chart context, materially wrong ranking, or misleading principal prediction
- P2: important workflow bug, route parity issue, missing validation, or repeated-state defect
- P3: wording, documentation, narrow edge case, or low-risk display issue

## Expected Deliverables

1. Full feature map.
   - Routes, frontend handlers, source files, tests, and generated-output exclusions.

2. Workflow parity matrix.
   - Exact compute, window scan, stream scan, predictor, exports, context windows, timeline replay, filters.

3. Technical findings report.
   - Confirmed implementation bugs only, with file/line evidence.

4. Algorithmic/source-alignment report.
   - Morin-rule mismatches, local-source ambiguities, and secondary external-reference notes.

5. Test gap list.
   - Missing backend/frontend coverage for each high-risk workflow.

6. Fix plan.
   - Ordered by risk and dependency.
   - Source-only edits under `backend/**`, `frontend/backend/**`, and `frontend/src/**`.

## Completion Criteria

This audit pass is complete when:
- every Transits feature listed above has been traced from UI to backend and back
- route contracts are documented and compared
- exact, scan, stream, predictor, export, context, and replay semantics are checked for parity
- timezone and instant semantics are tested across at least one non-browser-local chart timezone
- backend source mirror parity is checked
- confirmed issues are separated from speculative concerns
- Morin-local logic is clearly separated from external modern-reference comparison
- recommended fixes include focused regression tests
