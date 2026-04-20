# Forensic Workflow Audit Findings (Analysis-Only)

Date: 2026-03-05  
Scope: Forensic workflow and logic correctness audit, preserving AstroClock↔Horary integration contracts.  
Status: Analysis/documentation only. No implementation performed.

## 1. Forensic Wiring Map

### UI -> API -> Backend -> Forensic Engine -> Response

1. Frontend trigger and modal lifecycle
- Forensic opens from `AstroClock` via `handleOpenForensic` in `frontend/src/features/astroclock/AstroClock.jsx:604`.
- The modal is mounted immediately (`setShowForensic(true)`), then realtime pause is requested asynchronously via `pauseRealtimeForFeature()` (`frontend/src/features/astroclock/AstroClock.jsx:610`).
- Pause path snapshots time/location and jumps clock to manual through `jumpToIso(...)` (`frontend/src/features/astroclock/AstroClock.jsx:440`) which calls `AstroClockAPI.setMode(...)`.

2. API client call
- Forensic fetch is initiated in `ForensicDashboard` mount effect (`frontend/src/features/astroclock/AstroClock.jsx:1298`).
- Client wrapper: `AstroClockAPI.getForensic(opts)` in `frontend/src/features/astroclock/api.mjs:446`.
- Request target: `GET /api/astro-clock/forensic?...`.

3. Backend route flow
- AstroClock blueprint route: `forensic_analysis()` in `backend/astro_clock_api.py:2731`.
- Optional query overrides (`mode`, `datetime`, `location`, `timezone`) are parsed (`backend/astro_clock_api.py:2741`).
- Chart acquisition:
  - Override path uses temporary `AstroClockSettings` and `eng.get_current_data(settings=local)` (`backend/astro_clock_api.py:2776`).
  - Non-override path uses current singleton state (`backend/astro_clock_api.py:2778`).
- Dashboard enrichment base is built by `_build_dashboard_payload(...)` (`backend/astro_clock_api.py:444`), then forensic extraction/evaluation is applied.

4. Forensic feature extraction/evaluation/model flow
- Features: `extract_features(dash)` from `backend/forensic/features.py:34`.
- Rules loading/evaluation: `load_knowledge(...)` + `evaluate(...)` from `backend/forensic/engine.py:130` and `backend/forensic/engine.py:203`.
- Dominance scoring: `compute_dominance(...)` from `backend/forensic/features.py:262`.
- Additional forensic enrichments in route:
  - receptions (`backend/astro_clock_api.py:2814`)
  - relationship fixed-star hits (`backend/astro_clock_api.py:2906`)
  - knowledge dictionaries (`backend/astro_clock_api.py:2953`)
  - optional local-space abduction bearings/map (`backend/astro_clock_api.py:3041`, `backend/forensic/local_space.py:103`)

5. AstroClock/Horary dependencies
- Forensic depends on AstroClock chart generation, which is an adapter over Horary:
  - `AstroClockEngine.get_current_data(...)` (`backend/astro_clock_engine.py:102`)
  - `_generate_chart_with_horary_engine(...)` (`backend/astro_clock_engine.py:170`)
  - `HoraryEngine.judge(...)` (`backend/horary_engine/engine.py:7535`)
  - `serialize_chart_for_frontend(...)` (`backend/horary_engine/serialization.py:120`)
- Required chart contract used downstream: planets/aspects/houses/house_rulers/timezone info and moon fields (also documented in `docs/HORARY_ASTROCLOCK_ENGINE_WORKFLOW.md`).

### Coupling points that must not break

1. Mode and pause/resume coupling
- Forensic modal must not disrupt realtime stream lifecycle, manual snapshot state, or resume behavior (`AstroClock.jsx:523-602`).

2. Chart schema coupling
- Forensic extraction assumes dashboard payload shape: `planets`, `top_aspects`, `tightest_aspect`, `house_cusps`, `house_rulers`, `solar_conditions`, `fixed_star_hits`.

3. Horary serialization coupling
- AstroClock forensic depends on Horary `chart_data` serialization stability (`backend/horary_engine/serialization.py:186` onward).

4. Route/response coupling
- Forensic route returns top-level payload (not wrapped under `data`) and frontend expects `res.features` directly (`AstroClock.jsx:1287`).

5. Jump/sync behavior coupling
- Forensic open/close participates in shared `featurePauseRef` behavior used by transits/election/traits; any change can regress other modal flows.

## 2. Findings (Ordered by Severity)

### Critical

1. Forensic can fetch against moving realtime chart before pause completes
- File/line:
  - `frontend/src/features/astroclock/AstroClock.jsx:604`
  - `frontend/src/features/astroclock/AstroClock.jsx:610`
  - `frontend/src/features/astroclock/AstroClock.jsx:1298`
- Current behavior:
  - Modal is shown and fetch runs on mount immediately, while pause-to-manual snapshot runs asynchronously.
  - First forensic request can be realtime context rather than frozen event context.
- Why incorrect (knowledge citation):
  - Forensic texts emphasize charting from exact event/first-known time:
    - `Forensics by the Stars ...txt:196-199`
    - `Forensic Astrology for Everyone ...txt:1721-1724`
- Integration risk:
  - Forensic conclusions may drift per second and mismatch visible paused chart; reproducibility breaks.

2. Forensic feature extraction does not receive full aspects set
- File/line:
  - `backend/astro_clock_api.py:538-561`
  - `backend/forensic/features.py:89-95`
- Current behavior:
  - `_build_dashboard_payload` computes `top_aspects` and `tightest_aspect` but does not include `all_aspects`.
  - `extract_features` falls back to only `top_aspects + tightest`.
- Why incorrect (knowledge citation):
  - Forensic interpretation relies on full aspect context before synthesis:
    - `Forensic Astrology for Everyone ...txt:629-642`
- Integration risk:
  - False negatives/biased findings in deception/perpetrator logic when relevant aspects are outside top-3 orb summary.

### High

3. Directional aspect keying can silently miss valid forensic rules
- File/line:
  - `backend/forensic/features.py:102-113`
  - `backend/forensic/knowledge/deception_rules.yaml:66-83`
- Current behavior:
  - Aspect dictionary stores one direction key (`planet1_to_planet2`) per serialized aspect.
  - Several rules are directional and may fail if serialized order is opposite.
- Why incorrect (knowledge citation):
  - Aspect meaning in forensic delineation is relational; interpretation should be symmetric:
    - `Forensics by the Stars ...txt:2381-2383`
- Integration risk:
  - Non-deterministic rule firing dependent on serialization ordering, not astrology.

### Medium

4. Frontend/backend forensic `mode` parameter contract is inconsistent
- File/line:
  - `frontend/src/features/astroclock/api.mjs:448`
  - `backend/astro_clock_api.py:2741`
  - `backend/astro_clock_api.py:2761`
- Current behavior:
  - Frontend sends `mode`, but backend effectively keys behavior off `datetime` (`q_dt`) and ignores `q_mode`.
- Why incorrect:
  - Contract advertises `mode`; semantics are ambiguous and currently misleading.
- Integration risk:
  - Future callers may assume explicit mode override that is not honored.

5. Abduction map options are dropped on frontend pass-through
- File/line:
  - `frontend/src/features/astroclock/AstroClock.jsx:2278`
  - `frontend/src/features/astroclock/AstroClock.jsx:1281-1284`
  - `frontend/src/features/astroclock/api.mjs:458-459`
  - `backend/astro_clock_api.py:3093-3099`
- Current behavior:
  - UI invokes fetch with `line_zones`, but `fetchForensic` forwards only `abduction` and `origin`.
- Why incorrect:
  - Backend supports `line_zones/corridor_deg`; current UI call implies behavior that never reaches API.
- Integration risk:
  - Analyst-facing controls become non-functional without visible failure.

6. Temporal dead-zone bug in abduction brief builder
- File/line:
  - `frontend/src/features/astroclock/AstroClock.jsx:1387`
  - `frontend/src/features/astroclock/AstroClock.jsx:1393`
- Current behavior:
  - `firstRuler` is referenced before declaration in one branch inside `buildAIBrief`.
- Why incorrect:
  - Runtime exception path is swallowed, degrading report generation quality.
- Integration risk:
  - Partial/empty forensic briefing text, especially in abduction mode.

### Low

7. Some node-related rule keys are malformed/unreachable
- File/line:
  - `backend/forensic/knowledge/deception_rules.yaml:248-255`
  - `backend/forensic/engine.py:55-62`
- Current behavior:
  - Dot-path keys include quoted fragments and inconsistent token casing (`NEPTUNE`) that do not match extractor keyspace.
- Why incorrect:
  - Rule engine path resolution is exact; malformed keys are dead conditions.
- Integration risk:
  - Persistent false negatives in node/deception rules.

## 3. Proposed Fixes (No Code Yet)

1. Gate forensic initial fetch on completed pause snapshot
- Minimal safe strategy:
  - Delay first forensic fetch until snapshot/manual state is committed, or auto-refetch after pause resolution.
- Backward compatibility:
  - No API contract changes.

2. Provide full aspect inventory for forensic extraction
- Minimal safe strategy:
  - Add `all_aspects` (from `aspects_raw`) into forensic input while preserving existing `tightest/top_aspects` for UI.
- Backward compatibility:
  - Additive payload field only.

3. Symmetric aspect aliasing in feature extraction
- Minimal safe strategy:
  - Store both `A_to_B` and `B_to_A` keys for each aspect entry.
- Backward compatibility:
  - Existing keys preserved.

4. Reconcile forensic override contract
- Minimal safe strategy:
  - Either enforce/use `mode` explicitly or document/deprecate it and validate combinations.
- Backward compatibility:
  - Preserve `datetime/location/timezone` behavior.

5. Forward abduction options end-to-end
- Minimal safe strategy:
  - Pass `line_zones` and `corridor_deg` from UI helper to API client call.
- Backward compatibility:
  - Optional params only.

6. Stabilize abduction brief/report composition
- Minimal safe strategy:
  - Fix variable declaration order in brief builder.
- Backward compatibility:
  - Output quality improvement only.

7. Normalize malformed rule keys
- Minimal safe strategy:
  - Align node/aspect keys with extractor naming conventions.
- Backward compatibility:
  - Rule-only correction.

## 4. Validation Plan

1. API deterministic context checks
- Check:
  - Repeat `GET /api/astro-clock/forensic` with fixed `datetime/location/timezone`.
- Pass criteria:
  - Stable `timestamp` and `features` across runs.

2. UI modal timing and sync checks
- Check:
  - Open forensic from realtime and inspect first request context.
- Pass criteria:
  - First effective forensic analysis reflects paused/manual snapshot time, not moving realtime.

3. Mode pause/resume integrity checks
- Check:
  - Open forensic, close forensic, verify mode returns to realtime and stream resumes.
- Pass criteria:
  - No stuck manual mode, no stale stream, no jump desync.

4. Aspect completeness checks
- Check:
  - Use a chart fixture with relevant aspect not in top-3 by orb.
- Pass criteria:
  - Aspect appears in forensic features and can trigger intended rule.

5. Symmetric rule matching checks
- Check:
  - Validate same aspect with opposite serialization ordering.
- Pass criteria:
  - Identical rule outcomes regardless of planet order.

6. Abduction parameter propagation checks
- Check:
  - Trigger abduction fetch with `line_zones/corridor_deg`.
- Pass criteria:
  - Query parameters reach backend and are reflected in `abduction_map`.

7. Report/brief generation checks
- Check:
  - Build AI brief and HTML report with abduction mode on.
- Pass criteria:
  - Non-empty sections and no runtime errors.

## 5. Implementation Plan (Patch Order + Rollback Points)

1. Frontend modal sequencing and forensic fetch timing
- Target:
  - `frontend/src/features/astroclock/AstroClock.jsx`
- Rollback point:
  - Revert modal lifecycle changes only.

2. Backend forensic data completeness (aspects)
- Target:
  - `backend/astro_clock_api.py`
  - `backend/forensic/features.py`
- Rollback point:
  - Remove additive full-aspect field/path while keeping current summary output.

3. Contract and parameter propagation cleanup
- Target:
  - `frontend/src/features/astroclock/api.mjs`
  - `frontend/src/features/astroclock/AstroClock.jsx`
  - `backend/astro_clock_api.py`
- Rollback point:
  - Revert only override/abduction param handling.

4. Rule/schema hygiene fixes
- Target:
  - `backend/forensic/knowledge/deception_rules.yaml`
- Rollback point:
  - Restore prior rules file if downstream users rely on existing dead keys.

5. Regression tests
- Target:
  - Add/extend tests under `tests/` for forensic endpoint behavior and AstroClock pause/resume interactions.
- Rollback point:
  - Keep tests isolated so they can be temporarily skipped without removing fixes.

## Knowledge Corpus Citations Used

- `extracted_text_docs/text_forensics/Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt`
  - `:196-199` (event chart at exact first-known time)
  - `:208-211` (Ascendant as victim in crime chart)
  - `:2375-2378` (event/crime Ascendant and ruler significance)
  - `:2381-2383` (aspects as core relational evidence)
- `extracted_text_docs/text_forensics/Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve… (Caroline J. Luley) (Z-Library).txt`
  - `:611-617` (7th house as other person/offender starting point)
  - `:658-661` (angular houses first; 1/4/7/10 roles)
  - `:629-642` (aspect analysis and whole-chart synthesis requirement)
  - `:1721-1724` (exact last-sighting/first-known time usage)
- `extracted_text_docs/text_forensics/Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt`
  - `:200-203` (Asc/Desc victim/perp; Sun/Moon consideration in spousal contexts)
  - `:212-214` (essential dignities relevance)

