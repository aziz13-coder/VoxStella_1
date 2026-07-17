# Forensic Backend and Frontend Resolution - 2026-05-22

## Scope

This note documents the follow-up to the forensic backend/frontend review focused on the `/api/astro-clock/forensic` route and the Astro Clock forensic modal.

## Resolved Findings

1. Backend abduction corridor validation
   - Issue: `corridor_deg=nan`, `inf`, or `-inf` could pass through the forensic route and produce a non-JSON-compliant `NaN` value in the abduction map payload.
   - Resolution: `corridor_deg` is now parsed before chart context resolution when abduction mode is requested. Non-finite or non-positive values return HTTP 400 with `Invalid corridor_deg`.
   - Source files: `backend/astro_clock_api.py`, `frontend/backend/astro_clock_api.py`.
   - Regression: `tests/test_forensic_route_contract.py::ForensicRouteContractTests::test_forensic_route_rejects_non_finite_abduction_corridor_before_context_resolution`.

2. Frontend forensic request race
   - Issue: Rapid changes to forensic case type or chart context could allow an older in-flight response to overwrite newer modal state.
   - Resolution: The forensic dashboard now tracks a monotonically increasing request sequence. Responses update UI state only when they match the latest request.
   - Source file: `frontend/src/features/astroclock/AstroClock.jsx`.
   - Regression: `frontend/src/tests/astroClockModeFlow.test.jsx` test `ignores stale forensic responses after switching case type`.

3. Raw evidence audit payload
   - Issue: The backend returned `relationship_status`, but the frontend raw evidence group omitted it.
   - Resolution: The raw `Relationship & Survivability` group now includes `relationship_status`.
   - Source file: `frontend/src/features/astroclock/AstroClock.jsx`.
   - Regression: `frontend/src/tests/astroClockModeFlow.test.jsx` test `includes backend relationship status in forensic raw evidence`.

4. Backend forensic rule-engine failure visibility
   - Issue: `/api/astro-clock/forensic` swallowed rule load and evaluation failures, returning `success: true` with empty or degraded findings.
   - Resolution: rule loading and rule evaluation failures now log the backend exception and return HTTP 500 with `success: false`, `error: forensic_rule_engine_unavailable`, and an explicit detail message.
   - Source files: `backend/astro_clock_api.py`, `frontend/backend/astro_clock_api.py`, `backend/forensic/engine.py`, `frontend/backend/forensic/engine.py`.
   - Regressions: `tests/test_forensic_route_contract.py::ForensicRouteContractTests::test_forensic_route_reports_rule_load_failures` and `tests/test_forensic_route_contract.py::ForensicRouteContractTests::test_forensic_route_reports_rule_evaluation_failures`.

5. Local-space Swiss Ephemeris topocentric state race
   - Issue: local-space calculations called `swe.set_topo(...)` and then `swe.calc_ut(...)` without serialization, even though the production Flask server can handle requests concurrently.
   - Resolution: local-space and diagnostic local-space calculations now hold a module-level re-entrant lock across the topocentric observer update and Swiss Ephemeris calculations.
   - Source files: `backend/forensic/local_space.py`, `frontend/backend/forensic/local_space.py`.
   - Regression: `tests/test_forensic_local_space_threading.py::test_compute_local_space_serializes_topocentric_swe_state`.

6. Dominance scoring double-counted extracted aspect aliases
   - Issue: `extract_features()` stores both `A_to_B` and `B_to_A` aliases, and `compute_dominance()` added both aliases to each planet's aspect score.
   - Resolution: dominance scoring now de-duplicates reverse aliases per planet using a normalized aspect signature while preserving distinct real aspect records.
   - Source files: `backend/forensic/features.py`, `frontend/backend/forensic/features.py`.
   - Regression: `tests/test_forensic_core_rules.py::ForensicDominanceTests::test_compute_dominance_counts_extracted_aspect_alias_once_per_planet`.

7. Frontend forensic fetch errors were hidden or mislabeled
   - Issue: initial forensic fetch failures were caught silently, and the visible status path labeled failures as abduction fetch failures even when the failing request was the main dossier.
   - Resolution: the forensic modal now maintains a general `forensicError` state, clears it on retry/success, and renders a visible findings-view alert with a dossier-specific message.
   - Source file: `frontend/src/features/astroclock/AstroClock.jsx`.
   - Regression: `frontend/src/tests/astroClockModeFlow.test.jsx` test `shows forensic fetch failures in the dossier findings view`.

8. Frontend forensic report HTML export escaped only summary text
   - Issue: the export builder escaped only `<` in the AI brief while interpolating case header fields and section values directly into HTML before Electron export or browser print fallback.
   - Resolution: report generation now applies a shared HTML escape helper to dynamic case header values, summary text, tables, relationship lines, bearing labels, and SVG legend text.
   - Source file: `frontend/src/features/astroclock/AstroClock.jsx`.
   - Regression: `frontend/src/tests/astroClockModeFlow.test.jsx` test `escapes forensic report HTML before export and print fallback`.

## Verification

Commands run:

```powershell
python -m pytest tests/test_forensic_route_contract.py::ForensicRouteContractTests::test_forensic_route_rejects_non_finite_abduction_corridor_before_context_resolution
```

Result: passed.

```powershell
cd frontend
npx vitest run --config vitest.config.mjs src/tests/astroClockModeFlow.test.jsx -t "forensic"
```

Result: passed, 8 tests run and 54 skipped by filter.

```powershell
$files = Get-ChildItem -Path tests,backend -Filter 'test_forensic_*.py' -File | ForEach-Object { $_.FullName }
python -m pytest @files
```

Result: 198 passed, 1 existing `pytz` deprecation warning.

```powershell
cd frontend
npx vitest run --config vitest.config.mjs `
  src/tests/forensicAspectSummary.test.mjs `
  src/tests/forensicAbductionMap.test.mjs `
  src/tests/forensicAbductionCues.test.mjs `
  src/tests/forensicSurvivalSignal.test.mjs `
  src/tests/forensicReplayAxes.test.mjs `
  src/tests/forensicRelationshipLink.test.mjs `
  src/tests/astroclockApi.test.mjs `
  src/tests/astroClockModeFlow.test.jsx
```

Result: 132 passed.

Additional review verification:

```powershell
python -m pytest tests/test_forensic_route_contract.py -k "rule_load_failures or rule_evaluation_failures"
```

Result: 2 passed, 15 deselected, 1 existing `pytz` deprecation warning.

```powershell
python -m pytest tests/test_forensic_core_rules.py -k alias
```

Result: 1 passed, 6 deselected.

```powershell
python -m pytest tests/test_forensic_local_space_threading.py
```

Result: 1 passed.

```powershell
cd frontend
npx vitest run --config vitest.config.mjs src/tests/astroClockModeFlow.test.jsx -t "forensic fetch failures|escapes forensic"
```

Result: 2 passed, 63 skipped by filter.

```powershell
$files = @(Get-ChildItem tests -Filter 'test_forensic*.py' -File | ForEach-Object { $_.FullName }) + @(Get-ChildItem backend -Filter 'test_forensic*.py' -File | ForEach-Object { $_.FullName })
python -m pytest @files
```

Result: 202 passed, 1 existing `pytz` deprecation warning.

```powershell
cd frontend
npx vitest run --config vitest.config.mjs src/tests/astroClockModeFlow.test.jsx -t forensic
```

Result: 11 passed, 54 skipped by filter.

```powershell
cd frontend
npm run test:ui -- --run src/tests/forensicReplayAxes.test.mjs src/tests/forensicRelationshipLink.test.mjs src/tests/forensicSurvivalSignal.test.mjs src/tests/forensicAbductionCues.test.mjs src/tests/forensicAbductionMap.test.mjs src/tests/forensicAspectSummary.test.mjs
```

Result: 29 passed. NPM emitted the existing warning that `--run` is being parsed as a normal argument.
