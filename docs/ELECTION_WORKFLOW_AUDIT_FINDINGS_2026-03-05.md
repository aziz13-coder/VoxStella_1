# Election Workflow Audit Findings (Analysis-Only)

Date: 2026-03-05  
Scope: Election workflow and logic correctness, with AstroClock↔Horary integration protection.

## 1. Election Wiring Map

### UI -> API -> Backend -> Engine/Model -> Response path

1. Election UI opens from `frontend/src/features/astroclock/AstroClock.jsx` (`handleOpenElection`, around line 646), pausing realtime via `pauseRealtimeForFeature` (around line 523).
2. Scan options are built in `frontend/src/features/astroclock/ElectionModal.jsx` (`doScan`, around line 185), and SSE starts via `AstroClockAPI.electionStream(...)`.
3. Client API builder in `frontend/src/features/astroclock/api.mjs`:
   - Builds query for `/api/astro-clock/election/suggest/stream` (around line 484+).
   - Mints stream ticket using `/api/astro-clock/stream-ticket` (`buildStreamUrlWithTicket`, around line 216).
4. License/ticket gate lives in `backend/app.py`:
   - Stream target allowlist includes election stream (around line 189).
   - Ticket issue route `/api/astro-clock/stream-ticket` (around line 366).
5. Backend election routes in `backend/astro_clock_api.py`:
   - Validate endpoint `/election/validate` (around line 3119).
   - Stream endpoint `/election/suggest/stream` (around line 3171).
   - Model dispatch (`_scorer`) by `matter` (around line 3211+).
6. Per-step chart generation uses `_compute_chart_for(...)` (around line 1396), which calls `AstroClockEngine.get_current_data(settings=local)` without mutating global mode/settings.
7. AstroClock engine delegates chart computation to Horary engine with permissive flags in `backend/astro_clock_engine.py` (`_generate_chart_with_horary_engine`, around line 170; flags around lines 244-248).
8. Horary serialization in `backend/horary_engine/serialization.py` provides `chart_data.planets/aspects/houses/house_rulers/timezone_info`, plus moon aspect payloads.
9. Stream sends:
   - `progress` events.
   - `done` with `top`, optional `series`, plus `location`, `timezone`, `stats`.
10. Jump path:
    - Election row Jump button in `ElectionModal.jsx` calls `onJumpToTime`.
    - `AstroClock.jsx` `jumpToIso(...)` sets manual mode, location/timezone, refreshes dashboard/hours.

### Critical coupling points that must not break

1. `chart_data` contract from Horary serialization (planets/aspects/houses/house_rulers/timezone_info + moon fields).
2. Stream ticket target canonicalization and allowlist for election SSE.
3. Election `done` payload fields consumed by Jump (`timestamp[_local]`, `location`, `timezone`).
4. Pause/resume feature guard logic around modal open/close.

### Where election results affect clock mode/chart state/jump behavior

1. Jump sets backend mode to manual and updates UI mode.
2. Jump can override active location/timezone from election result.
3. Close election attempts realtime resume depending on pause snapshot and whether user has moved to a different manual timestamp.

## 2. Findings (Ordered by Severity)

### Critical

#### [Critical] Undefined setters crash Viral/Legal model selection

- File + line:
  - `frontend/src/features/astroclock/ElectionModal.jsx:452`
  - `frontend/src/features/astroclock/ElectionModal.jsx:466`
- Current behavior:
  - Viral button calls `setViralMode('transit')`.
  - Legal button calls `setLegalMode('transit')`.
  - Neither setter exists in this component.
- Why incorrect:
  - Runtime `ReferenceError` can occur on click, preventing model selection and scan start.
  - Breaks required election UI trigger flow documented in `docs/HORARY_ASTROCLOCK_ENGINE_WORKFLOW.md` (frontend trigger and dedicated election endpoint flow).
- Integration risk:
  - Election workflow interruption before API call.
  - Can leave feature pause/resume flow in inconsistent state during user interaction.

### High

#### [High] Aspect-applying contract mismatch (`phase` expected, `applying` provided)

- File + line:
  - Producer:
    - `backend/horary_engine/serialization.py:133` (`aspects[*].applying`)
    - `backend/horary_engine/serialization.py:81` (`moon_next_aspect.applying`)
  - Consumers (examples):
    - `backend/election_models/legal.py:58`, `:192`, `:268`, `:275`
    - `backend/election_models/contract.py:138`, `:144`, `:162`
    - Similar pattern across multiple election models.
- Current behavior:
  - Many scorers inspect `phase` string (`"apply" in phase`), but serialized payload carries boolean `applying`.
  - Applying-dependent penalties/bonuses can silently fail.
- Why incorrect (knowledge citation):
  - Corpus stresses Moon applying/perfection testimony as central:
    - `extracted_text_docs/extracted_text_docs_horary/horary_astrology_and_judgment_of_events_ocr.txt:3787-3790`
    - `...:3727-3740` (besiegement and next-aspect implications).
- Integration risk:
  - Ranking instability and incorrect top windows across models.
  - Fragile coupling to Horary serialization schema.

#### [High] Surgery “never” contraindications are not consistently hard-gated

- File + line:
  - `backend/election_models/surgery.py`:
    - Moon target-sign rule: `:189-193`
    - VOC penalty: `:315-329`
    - Mars/Saturn house penalties: `:410-429`
    - No explicit Mercury-retrograde surgery gate.
- Current behavior:
  - Several contraindications are implemented as score reductions only.
  - Unsafe windows may still rank in top results when other bonuses dominate.
- Why incorrect (knowledge citation):
  - Corpus states explicit surgery prohibitions:
    - `...horary_astrology_and_judgment_of_events_ocr.txt:6280-6283` (Moon VOC, Via Combusta, Saturn rising/7th)
    - `...:6290-6292` (Mercury retrograde)
    - `...:6297-6299` (Moon in sign ruling body part).
- Integration risk:
  - Potentially unsafe “recommended” jump times.
  - High trust-risk for medical-adjacent workflow.

#### [High] Naive datetime interpretation diverges between filtering and chart computation

- File + line:
  - Frontend naive ISO builder: `frontend/src/features/astroclock/ElectionModal.jsx:14-17`
  - Stream parsing/filtering path: `backend/astro_clock_api.py:3268`, `:3479`, `:3504`
  - Chart normalize path: `backend/astro_clock_api.py:848-872`
- Current behavior:
  - Naive `start/end` are interpreted differently in loop-local filtering vs chart normalization.
  - Weekday/hour filters and chart timestamps can desynchronize.
- Why incorrect:
  - Violates scoped/stateless consistency expectations in `docs/HORARY_ASTROCLOCK_ENGINE_WORKFLOW.md` (single coherent chart derivation path and timezone metadata contract).
- Integration risk:
  - Wrong kept/filtered rows.
  - Jumping to times that do not match intended local scan window logic.

### Medium

#### [Medium] Legal scorer uses exact float equality for aspect geometry

- File + line:
  - `backend/election_models/legal.py:282-287`
- Current behavior:
  - Checks `sep in (0.0, 60.0, 120.0)` after orb guard, which almost never matches due to floating precision.
- Why incorrect:
  - Intended Moon-to-L1 linkage scoring can become effectively dead code.
- Integration risk:
  - Distorted legal model scoring and reduced differentiation quality.

## 3. Proposed Fixes (No Code Yet)

1. Remove undefined `setViralMode` / `setLegalMode` calls from Election modal model buttons.
2. Introduce a model-layer aspect adapter:
   - Treat `applying: true` as equivalent to applying `phase`.
   - Maintain backward compatibility with any legacy `phase` values.
3. Add strict contraindication gate (or hard cap) policy for surgery-critical “never” rules:
   - Moon VOC / Via Combusta / body-sign rule / Mercury Rx / Saturn Asc/7th.
4. Canonicalize election scan time handling:
   - Parse `start/end` into timezone-aware timestamps before weekday/hour filtering.
   - Use the same canonical local context for chart compute and filter checks.
5. Fix legal scorer aspect match to orb-based comparisons only (remove exact-float tuple equality branch).

### Backward-compatibility notes

1. Keep request/response payload schema unchanged.
2. Keep existing option names in frontend/backend contract.
3. If strict surgery gating is introduced, feature-flag it initially to avoid abrupt behavior shifts.

## 4. Validation Plan

### Exact checks/tests

1. UI scan smoke:
   - Open Election modal.
   - Click each model button (including Viral, Legal).
   - Ensure no runtime errors and scan starts.
2. SSE contract:
   - Verify progress/done event handling under normal and error paths.
3. Aspect-applying behavior:
   - Confirm applying-dependent tags/penalties trigger when `applying=true` even if `phase` absent.
4. Timezone/filter coherence:
   - Use location+timezone differing from machine timezone.
   - Verify weekday/hour filters align with returned `timestamp_local`.
5. Jump integration:
   - Jump from result row, verify manual mode switch, chart refresh, location/timezone application.
   - Close modal and confirm pause/resume behavior remains correct.
6. AstroClock↔Horary contract regression:
   - Assert `chart_data` keys required by election and dashboard remain present.

### Pass criteria

1. No model-selection runtime exceptions.
2. Top results stable and consistent with applying-aspect logic.
3. No mismatch between selected scan window filters and resulting timestamps.
4. Jump never breaks mode/state flow.
5. No regressions in transits/dashboard/other AstroClock features that share chart contract.

## 5. Implementation Plan

### Patch order

1. Frontend runtime crash fixes (Election model button handlers).
2. Aspect-applying normalization in election model layer.
3. Legal geometry scoring correction.
4. Timezone canonicalization in election stream loop.
5. Surgery contraindication hardening (flagged rollout).
6. Targeted UI/API/model regression tests.

### Rollback points

1. Keep each patch isolated to allow selective revert.
2. If scorer behavior shifts too broadly, rollback aspect normalization independently.
3. If timezone changes alter historical behavior unexpectedly, rollback only canonicalization patch.
4. Keep strict surgery mode behind a toggle for rapid fallback.

---

## Implementation Update (2026-03-05)

Implemented resolution for all documented findings in source files:

1. Frontend model-button crash fixed:
   - `frontend/src/features/astroclock/ElectionModal.jsx`
2. Aspect contract compatibility (`applying` + `phase`) added at Horary serialization boundary:
   - `backend/horary_engine/serialization.py`
3. Legal scorer orb logic corrected (removed exact-float equality dependence):
   - `backend/election_models/legal.py`
4. Election stream timezone canonicalization aligned for parse/filter/compute flow:
   - `backend/astro_clock_api.py`
5. Surgery contraindications hardened with strict gating (toggleable via `strict_surgery_never_rules`):
   - `backend/election_models/surgery.py`

### Detailed Fix Log

1. Frontend Election model buttons
   - Removed undefined `setViralMode`/`setLegalMode` calls from model switch handlers.
   - Preserved existing `matter`, `legalAction`, and jump/pause workflow behavior.
2. Horary serialization contract hardening
   - Added `phase` alongside `applying` for both planetary aspects and moon next/last aspect payloads.
   - Added backward-compatible deserialization fallback from `phase`/`motion` when `applying` is absent.
3. Legal scorer applying + geometry correctness
   - Normalized applying detection from either `phase`/`motion` or `applying`.
   - Replaced exact-float geometry branch with orb-based comparisons for conjunction/sextile/trine/square relation checks.
4. Election stream timezone canonicalization
   - Replaced direct `fromisoformat` parsing in `/election/suggest/stream` with `_normalize_manual_datetime` for `start/end`.
   - Introduced a canonical `scan_zone` used consistently for weekday/hour filtering and traditional timing checks.
   - Passed normalized timezone to transit observer context.
5. Surgery “never” contraindication enforcement
   - Added strict contraindication mode (`strict_surgery_never_rules`, default `true`).
   - Added hard contraindication tracking for:
     - Moon in target body-part sign
     - Mercury retrograde
     - Moon void-of-course
     - Moon in Via Combusta
     - Saturn rising / in 7th
   - Applied hard cap behavior when strict contraindications are present.

## Full UI/E2E Test Run (2026-03-05)

Note: No dedicated Playwright/Cypress E2E suite exists in this repo. Full available UI/E2E coverage was executed via frontend UI tests + backend integration-style tests + communication smoke checks.

### Executed commands

1. `python -m pytest tests -q`
2. `npm run test` (frontend)
3. `npm run test:communication` (frontend)

### Results

1. Backend tests: `37 passed, 1 skipped` (warnings: 1 deprecation in `pytz`).
2. Frontend tests:
   - unit: `2 scripts passed`
   - UI (Vitest): `1 file passed, 3 tests passed`
3. Communication smoke:
   - all checks `OK` (stream ticket, API port fallback, Electron dev API alignment, no legacy backend port).

### Pass/Fail status

- Overall status: **PASS**
- No failing tests detected in full available UI/E2E flow coverage.
