# Forensic Feature Audit - 2026-03-22

## Executive Summary

The forensic feature is a chart-overlay workflow inside Astro Clock, not a standalone feature stack. The renderer entry point lives inside the large Astro Clock component, the request goes through a thin Astro Clock API wrapper, and the backend route builds a dashboard-shaped chart payload before running a YAML-rule evaluator plus a heuristic dominance scorer.

That architecture is workable, but it has three important consequences:

1. Forensic correctness depends heavily on Astro Clock chart-state correctness.
2. Forensic request behavior can drift from the rest of Astro Clock if it does not reuse the shared request-context helpers.
3. Most current risk is in workflow integration, not in the tiny rule engine itself.

Current status after source scan:

- The backend forensic evaluator is present and active.
- Full-aspect injection and bidirectional aspect aliases are present in current source.
- A prior pause/sync fix appears to have regressed: forensic still opens before realtime pause completes.
- The forensic frontend request contract is still thinner than Trait Profile/Transits/Election and does not carry the full chart context.
- Automated coverage is light and mostly unit-level.

## Current Workflow Map

### Renderer / UI

- Astro Clock owns the feature entry point in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):751 and [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1081.
- The forensic overlay is rendered as an inline nested component, `ForensicDashboard`, inside the same file at [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1441.
- Astro Clock passes only `onClose`, `mode`, `manualIso`, and `manualLocation` into the forensic overlay at [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1395.

### Frontend API Layer

- The request helper is `AstroClockAPI.getForensic(opts)` in [api.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/api.mjs):490.
- It forwards:
  - `mode`
  - `datetime`
  - `location`
  - `timezone`
  - abduction extras (`abduction`, `origin`, `line_zones`, `corridor_deg`)
- It does not forward `houseSystem`.

### Frontend Modal Fetch Logic

- `ForensicDashboard` fetches through `fetchForensic` in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1460.
- That function currently sends:
  - manual mode context only when `mode === 'manual'`
  - `datetime`
  - `location`
  - optional abduction extras
- It does not pass:
  - `timezone`
  - `houseSystem`
- The initial fetch runs from a mount effect in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1487.

### Backend Route

- The backend endpoint is `GET /api/astro-clock/forensic` at [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py):2910.
- The route:
  1. Parses optional request overrides (`mode`, `datetime`, `location`, `timezone`)
  2. Builds temporary `AstroClockSettings`
  3. Calls `eng.get_current_data(settings=local)` or `eng.get_current_data()`
  4. Builds a dashboard-like payload via `_build_dashboard_payload(...)`
  5. Injects `all_aspects` when available
  6. Extracts forensic features
  7. Loads YAML rule lists and evaluates them
  8. Computes planetary dominance
  9. Adds receptions, relationship star hits, knowledge dictionaries, and optional local-space abduction output
  10. Returns a top-level JSON object, not the usual `{ success, data }` wrapper

### Shared Data Source

- The shared Astro Clock dashboard projection is built by `_build_dashboard_payload(...)` in [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py):647.
- That payload is the forensic input substrate. It carries:
  - planets
  - moon state / moon timeline
  - top aspects / tightest aspect
  - house cusps / rulers
  - fixed stars
  - arabic parts
  - solar conditions
  - sect
  - receptions
  - other chart metadata

### Forensic Core

- Rule loading/evaluation: [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/engine.py)
- Feature extraction: [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py):34
- Dominance scoring: [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py):267
- Abduction/local-space support: [local_space.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/local_space.py)
- Rule/dictionary files: [backend/forensic/knowledge](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge)

## What The Forensic Engine Actually Is

The forensic backend is not a second horary engine. It is a lightweight post-processing layer over Astro Clock output.

It does three main things:

1. Normalizes chart payload into a smaller `features` dictionary.
2. Runs YAML rules against those features.
3. Adds heuristic summaries such as planetary dominance and optional local-space bearings.

The rule evaluator in [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/engine.py) is a compact DSL engine. It supports:

- `all`
- `any`
- `not`
- equality / membership tests
- boolean presence tests
- numeric comparisons

This means most forensic interpretation behavior is knowledge-file driven, not hard-coded Python logic.

## Shared Dependency / Regression Map

The forensic feature depends on these shared layers:

### Astro Clock shared state

- realtime/manual/pause lifecycle in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx)
- shared feature pause/resume behavior used by forensic, trait profile, transits, and election

### Astro Clock backend chart production

- `AstroClockEngine.get_current_data(...)`
- `_build_dashboard_payload(...)`
- timezone/location normalization in [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)

### Horary / chart serialization substrate

- forensic consumes serialized chart output from the shared chart generation path
- any change to chart schema, planet naming, aspects, house rulers, or moon metadata can affect forensic extraction

### Fixed stars / receptions / solar conditions / lots

- forensic uses these as part of output or rule context
- regressions in those shared helpers can distort forensic summaries

## Tests Present Today

### Backend

- [test_forensic_features.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_features.py)

Current backend forensic test coverage is narrow:

- `all_aspects` is preferred when present
- reverse aspect aliases exist
- node-related rule path resolution works

### Frontend

- [astroClockModeFlow.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/astroClockModeFlow.test.jsx)

Current frontend forensic coverage is indirect:

- it mocks `getForensic`
- it verifies the current open/pause sequencing behavior
- it does not verify the forensic overlay’s own request contract or rendering logic

## Findings

### 1. The current source appears to have regressed the earlier pause-before-open fix

- Evidence:
  - current behavior in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):751
  - current test expectation in [astroClockModeFlow.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/astroClockModeFlow.test.jsx):249
  - earlier claimed fix in [FORENSIC_FIXES_IMPLEMENTED_2026-03-05.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_FIXES_IMPLEMENTED_2026-03-05.md):9
- Current behavior:
  - the modal opens immediately via `setShowForensic(true)`
  - `pauseRealtimeForFeature()` is fired afterward and not awaited
  - the current test suite explicitly expects this immediate-open behavior
- Risk:
  - the first forensic fetch can still be taken against moving realtime state rather than a frozen snapshot
  - that can produce non-reproducible output

### 2. The forensic overlay does not reuse the shared Astro Clock request-context builder

- Evidence:
  - shared context builder in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):355
  - forensic local fetch builder in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1460
- Current behavior:
  - Trait Profile and other features use richer shared clock context
  - forensic builds a smaller custom request object locally
- Risk:
  - forensic can drift from Astro Clock fixes for manual/realtime scoping
  - future fixes applied to shared context may not reach forensic

### 3. Forensic currently drops timezone and house-system context on the frontend side

- Evidence:
  - overlay props in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1395
  - modal signature in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1441
  - fetch builder in [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1460
  - API client in [api.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/api.mjs):490
- Current behavior:
  - forensic does not receive `timezone`
  - forensic does not receive `houseSystem`
- Risk:
  - manual/location timezone normalization can diverge from the visible chart
  - house-system-specific chart differences are not explicitly scoped by the request
  - forensic relies more on ambient engine state than on an explicit request contract

### 4. The backend forensic route duplicates request-context logic instead of using the shared resolver

- Evidence:
  - shared request-context resolver in [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py):1550
  - separate forensic override path in [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py):2912
- Current behavior:
  - forensic manually reconstructs override behavior
  - the rest of Astro Clock has a shared `_data_for_request_clock_context(...)`
- Risk:
  - duplicated logic can fall out of sync on timezone, mode, pause, or house-system behavior
  - this is the same class of bug that has already affected other Astro Clock features

### 5. The forensic route still uses a custom response contract

- Evidence:
  - forensic returns top-level JSON at [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py):3327
  - most Astro Clock routes return wrapped success/data payloads via `_json_ok(...)`
- Current behavior:
  - forensic returns `success`, `features`, `findings`, etc. at the top level
  - frontend forensic expects `res.features` directly
- Risk:
  - this makes forensic harder to normalize or reuse through shared clients
  - it increases the chance of one-off frontend handling bugs

### 6. Full aspect coverage and reverse aspect aliasing are present in current source

- Evidence:
  - all-aspect injection in [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py):2991
  - reverse aspect aliases in [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py):102
  - backend test coverage in [test_forensic_features.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_features.py)
- Status:
  - this earlier weakness appears fixed in current source
- Residual risk:
  - the test surface is still narrow and does not exercise the route end to end

### 7. Node-related deception rules look structurally reachable now

- Evidence:
  - corrected node rule paths in [deception_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/deception_rules.yaml):241
  - resolver test in [test_forensic_features.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_features.py):58
- Status:
  - this earlier dead-rule problem appears fixed

### 8. The dominance model is explicitly heuristic and only loosely grounded

- Evidence:
  - scoring rubric comment in [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py):268
- Current behavior:
  - angularity, house strength, essential dignity, aspects, and retrogradation are combined into a synthetic score
- Risk:
  - this is a product heuristic, not a strict traditional doctrine engine
  - if users read it as authoritative forensic astrology rather than a helper ranking, it may be over-trusted

### 9. The forensic UI is still monolithic and hard to regression-test

- Evidence:
  - `ForensicDashboard` is nested inside [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx):1441
- Current behavior:
  - most forensic rendering, briefing, abduction UI, export logic, and domain synthesis live inside a very large component file
- Risk:
  - even small forensic changes can regress unrelated Astro Clock behaviors
  - targeted frontend tests are harder to write and maintain

## Verification Notes

I verified current source behavior by reading:

- [AstroClock.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstroClock.jsx)
- [api.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/api.mjs)
- [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/engine.py)
- [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py)
- [local_space.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/local_space.py)
- [test_forensic_features.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_features.py)
- [astroClockModeFlow.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/astroClockModeFlow.test.jsx)

Attempted runtime verification:

- Command:
  - `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary backend/venv/bin/python -m pytest tests/test_forensic_features.py -q'`
- Result:
  - blocked in this environment with `Access is denied. Error code: Wsl/Service/CreateInstance/E_ACCESSDENIED`

So this audit is source-grounded and test-file-grounded, but I did not complete a fresh backend test run from this environment.

## Practical Next Steps

1. Move forensic request construction onto the shared Astro Clock context builder.
2. Pass `timezone` and `houseSystem` into `ForensicDashboard` and `getForensic(...)`.
3. Reconcile the forensic route with `_data_for_request_clock_context(...)` instead of keeping a duplicate override path.
4. Decide deliberately whether forensic should:
   - wait for pause before opening, or
   - open immediately and explicitly refetch after pause snapshot
5. Add real forensic tests:
   - backend route contract test for `/api/astro-clock/forensic`
   - frontend forensic overlay test for request payload and first-fetch timing
   - regression test for timezone/house-system scoping

## Bottom Line

The forensic feature is implemented and reasonably rich, but it is still integration-fragile.

The most important current concerns are:

- forensic’s request context is thinner than the rest of Astro Clock
- forensic duplicates backend clock-context logic
- the current source appears to have regressed the earlier pause-before-open fix
- coverage is too light for a feature this coupled to Astro Clock state

The rule engine itself is not the main problem. The workflow and contract boundaries are.
