# AstroClock Transits Full Audit Report
## 2026-05-01

This report closes Phases 2-7 of the AstroClock Transits audit plan.

Primary logic authority for this pass was the local Morin corpus and Morin-derived repository notes. External astrology references were not needed to resolve the confirmed technical issues below; no external source was used to override local Morin logic.

## Phase 2. Backend Route And Contract Audit

Routes reviewed:
- `GET /api/astro-clock/transits`
- `GET /api/astro-clock/transits/window`
- `GET /api/astro-clock/transits/window/stream`
- `GET /api/astro-clock/predictor`
- `GET /api/astro-clock/transits/export`
- `GET /api/astro-clock/transits/window/export`

Confirmed backend findings:

### Finding 1. Exact-transit filters were serialized but not applied

Severity: P2

Feature/workflow:
- exact transit compute
- exact CSV export parity
- API contract parity

Current behavior before fix:
- `frontend/src/features/astroclock/api.mjs` serialized `transiting`, `natal`, and `aspect` filters for `AstroClockAPI.getTransits`.
- `backend/astro_clock_api.py` accepted the request but did not apply those filters in `/transits`.
- `/transits/export` did apply similar filters, so exact compute and exact export could disagree.

Expected behavior:
- If the API accepts filter parameters, exact compute must return the filtered hit set.
- Exact compute and exact export should use the same filtering semantics.

Resolution:
- Added shared `_apply_transit_hit_filters`.
- Applied it to `/transits`, `/transits/export`, and the streaming per-step path.
- Added `_sort_transit_hits_for_display` for stable exact/export ordering after enrichment.

Files:
- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`
- `backend/test_astro_clock_api_transits.py`
- `frontend/backend/test_astro_clock_api_transits.py`

Regression:
- `test_exact_transits_route_applies_serialized_filters`

### Finding 2. Invalid scan parameters could return internal errors

Severity: P2

Feature/workflow:
- window scan
- stream scan
- predictor
- window export

Current behavior before fix:
- scan routes parsed `step_minutes` with direct `int(...)`.
- invalid values such as `step_minutes=not-a-number` fell into the generic exception handler and returned a 500 `internal_error`.
- `/transits/window` also parsed `range_hours` with direct `float(...)` in the center/range fallback path.

Expected behavior:
- bad user/request parameters should return 400 with a clear validation error before any scan work starts.

Resolution:
- Added `_parse_transit_scan_step`.
- Added `_parse_transit_range_hours`.
- Added `_parse_transit_limit`.
- Normalized naive scan datetimes to UTC inside `_parse_transit_scan_datetime` so mixed naive/aware scan bounds do not become comparison errors.
- Applied validation to `/transits/window`, `/transits/window/stream`, `/predictor`, and `/transits/window/export`.

Files:
- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`
- `backend/test_astro_clock_api_transits.py`
- `frontend/backend/test_astro_clock_api_transits.py`

Regression:
- `test_transit_scan_routes_reject_invalid_step_before_scanning`
- existing oversized-window regression now also covers the stream route

## Phase 3. Frontend Workflow And State Audit

Workflows reviewed:
- exact compute
- window scan
- stream fallback
- predictor
- timeline replay
- auto-context windows
- manual context windows
- intersection helper
- exact/window exports

Confirmed frontend finding:

### Finding 3. Context windows used browser-local time semantics

Severity: P2

Feature/workflow:
- Suggest Context Windows
- manual PD/progression/solar-arc context windows
- Use Intersection as Scan Range
- scan/predictor requests with context windows

Current behavior before fix:
- auto-filled PD/progression/solar-arc fields used `new Date(...).getFullYear()` and `getHours()`, which are browser-local fields.
- manual context inputs stored raw `YYYY-MM-DDTHH:mm` strings on `window.__pdStart`, `window.__progStart`, and `window.__saStart`.
- later scan/predictor requests could send timezone-less context values or values shifted to the browser timezone.
- for charts outside the browser timezone, this could filter the wrong support window or cause stream/non-stream context behavior to diverge.

Expected behavior:
- visible context-window fields should be shown in the chart/natal timezone.
- manual context-window values should be converted to absolute ISO instants using the same chart timezone used by transit inputs.
- intersection output should write scan start/end fields in the chart timezone.

Resolution:
- Added `getTransitInputTimezone`.
- Added `buildContextIsoFromInputs`.
- Added `setStoredContextIso`.
- Added `writeInputDateTime`.
- Replaced browser-local context-window formatting with `formatIsoForInputFields`.
- Converted manual context-window edits to ISO instants before storing them for requests.
- Updated the intersection helper to compute from ISO instants and then format scan fields in the chart timezone.

Files:
- `frontend/src/features/astroclock/TransitsModal.jsx`
- `frontend/src/tests/transitsModalReplay.test.jsx`

Regressions:
- `keeps suggested context windows in the chart timezone`
- `sends manually entered context windows as chart-timezone instants`

## Phase 4. Morin Algorithm And Source-Alignment Audit

Local Morin baseline checked against implementation:
- radical determination leads quality
- transits act as triggers, not full causes by themselves
- meaningful targets are radical planets, cusps, aspect places, Fortune/lots, and antiscions
- agreement/contrariety affects tone
- slower planets and persistence matter
- principal signification should be surfaced without discarding secondary mixed signals

Algorithm files reviewed:
- `backend/transits_morin.py`
- `backend/morin_aspects.py`
- `backend/pd_morin.py`
- `backend/knowledge/morin_keywords.json`

Conclusion:
- No new Morin-rule implementation bug was confirmed in this pass.
- The primitive `_classify_quality` layer is simplified, but exact, scan, stream, predictor, and export flows enrich hits through determination/concordance logic before user-facing ranking or display.
- Existing tests already cover the main source-sensitive rule boundaries: honors examples, malefic crisis examples, weak concordance wording, house-domain labels, relationship/wealth/travel/spiritual/study vocabulary, and crisis-family selection.

Residual algorithmic review risk:
- completed by the controlled-chart stress suite in `docs/ASTROCLOCK_TRANSITS_MORIN_STRESS_SUITE_2026-05-01.md`.
- the suite now covers planet/aspect stereotypes conflicting with radical determination, empty-space downweighting, radical-place outranking, and contrary context tempering.

## Phase 5. Replay, Benchmark, And External Reference Cross-Check

Replay/test coverage reviewed:
- backend quality tests
- backend route tests
- frontend replay slices in `transitsModalReplay.test.jsx`
- API serialization tests in `astroclockApi.test.mjs`

External references:
- not used for this fix pass
- local Morin sources and current repo tests were sufficient for the confirmed issues
- future external references should be marked as secondary UX/product-positioning evidence, not as replacements for Morin-local rules

## Phase 6. Findings Triage

| Priority | Finding | Status |
| --- | --- | --- |
| P2 | Exact filters serialized but not applied by `/transits` | fixed |
| P2 | invalid scan parameters could return 500 | fixed |
| P2 | context windows used browser-local/timezone-less semantics | fixed |

No P0/P1 issue was confirmed in this pass.

## Phase 7. Implementation And Verification

Source files changed:
- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`
- `backend/test_astro_clock_api_transits.py`
- `frontend/backend/test_astro_clock_api_transits.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`
- `frontend/src/tests/transitsModalReplay.test.jsx`
- `docs/ASTROCLOCK_TRANSITS_FULL_FEATURE_AUDIT_PLAN_2026-05-01.md`
- `docs/ASTROCLOCK_TRANSITS_AUDIT_PHASE1_BASELINE_2026-05-01.md`
- `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`

Verification run:

```powershell
python -m pytest backend/test_astro_clock_api_transits.py backend/test_transits_quality.py
npm run test:ui -- transitsModalReplay.test.jsx astroclockApi.test.mjs
```

Results:
- backend: 20 passed, 1 warning
- frontend: 76 passed

Backend mirror parity:
- `backend/astro_clock_api.py` matches `frontend/backend/astro_clock_api.py`
- `backend/test_astro_clock_api_transits.py` matches `frontend/backend/test_astro_clock_api_transits.py`
- other checked transits/Morin backend mirror files still match

## Morin Stress Suite Follow-Up

Status: completed in `docs/ASTROCLOCK_TRANSITS_MORIN_STRESS_SUITE_2026-05-01.md`.

Implemented source changes:
- `backend/transits_morin.py`
- `frontend/backend/transits_morin.py`
- `backend/test_transits_quality.py`
- `frontend/backend/test_transits_quality.py`

Added controlled cases:
- benefic planet radically determined to a harmful topic
- malefic planet radically determined to a helpful/life-supporting topic
- strong geometric transit to empty zodiacal space downweighted
- weaker geometric transit to a radical place outranking empty space
- contrary context windows tempering, not erasing, the transit claim

Verification run:

```powershell
python -m pytest backend/test_transits_quality.py backend/test_astro_clock_api_transits.py
python -m pytest frontend/backend/test_transits_quality.py
```

Results:
- backend: 24 passed, 1 warning
- frontend backend mirror: 18 passed, 1 warning
