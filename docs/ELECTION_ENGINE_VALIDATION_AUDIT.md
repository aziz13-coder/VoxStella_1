# Executive Summary

I audited the election engine from renderer UI through Electron transport, backend routes, chart/context helpers, and matter scorers, using both the repository code and Morin Book 26 at `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt`.

Baseline result before edits: the existing election suite already passed, but it was missing coverage for two real problems:

1. The surgery scorer was applying Morin Rule 13 twice, which double-weighted the same Moon-conjunction condition and could distort surgery ranking.
2. The renderer validation request was not serializing the same matter-specific election options as the stream request, so the UI was validating a different contract than it later executed on SSE failure.

I implemented targeted fixes only where the evidence was strong and the blast radius was low:

- Removed the duplicate Rule 13 block from both backend source trees:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\surgery.py`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\election_models\surgery.py`
- Introduced a shared election-query serializer in:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs`

I then re-ran the relevant backend and frontend tests:

- `python -m pytest tests\test_election_route_contracts.py tests\test_election_workflow_matrix.py tests\test_election_morin_rules.py tests\test_election_stress_matrix.py tests\test_battle_election.py tests\test_beautification_election.py tests\test_conception_gender.py tests\test_haircut_moon_phases.py tests\test_viral_content.py`
  - Result: `48 passed`
- `npx vitest run src/tests/astroclockApi.test.mjs` in `C:\Users\sabaa\Downloads\codexhorary\frontend`
  - Result: `16 passed`

No packaged/generated artifacts were edited.

# Election Workflow Map

## Renderer to backend path

1. Election UI entry:
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx:25`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx:204`
   - `AstroClock.jsx` imports `ElectionModal` and exposes the election workflow from the main Astro Clock screen.

2. Election option assembly and submission:
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:221-288`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:290`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:320`
   - `ElectionModal` builds a matter-specific `opts` object and sends it to `AstroClockAPI.electionStream(opts)`. If the SSE errors before a terminal payload, the modal calls `AstroClockAPI.validateElection(opts)` to surface a user-facing error.

3. Renderer API helper:
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:210-254`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:568-576`
   - `AstroClockAPI` now uses a shared `appendElectionParams(...)` helper for both validation and streaming so the two requests serialize the same election workflow options.

4. Electron transport:
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js:26-65`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:142-179`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:181-260`
   - `preload.js` exposes `API_BASE_URL` and `electronAPI` to the renderer. `main.js` resolves the backend command, preferring packaged executables under Electron resources and falling back to `..\backend\app.py` in dev.

## Backend route contracts

### `GET /api/astro-clock/election/validate`

- Source:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:4346-4420`
- Input contract:
  - Required: `start`, `end`, `location`
  - Optional/common: `matter`, `timezone`, `step_minutes`, `hour_start`, `hour_end`
  - Informational matter-specific validation currently implemented only for conception `gender`
- Response contract:
  - Success: `{"success": true}`
  - Error: `{"success": false, "error": "..."}`
- Purpose:
  - Structural validation only: parse datetimes, resolve location/timezone, validate step bounds, enforce window size, validate conception gender vocabulary.

### `GET /api/astro-clock/election/suggest/stream`

- Source:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:4423`
  - Model-option extraction: `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:4622-4705`
- Input contract:
  - Common: `matter`, `start`, `end`, `location`, `timezone`, `house_system_code`, `step_minutes`, `limit`
  - Filters: repeated `weekday`, `hour_start`, `hour_end`
  - Natal context: `natal_snap_id` or `natal_datetime` + `natal_location` + `natal_timezone`
  - Enhancers: `include_sr_lr`, `include_fixed_stars`, `include_lunation_screen`, `include_traditional_timing`
  - Matter-specific:
    - surgery: `surgery_sign`, `procedure`, `strict_surgery_never_rules`, eclipse-window toggles
    - contract: `prefer_fixed_asc`, `saturn_binding_ok`, `min_mercury_direct_days`, `contract_mode`
    - business: `business_mode`, `emphasize_commerce`
    - journey: `journey_type`
    - battle: `action_type`
    - haircut: `hair_goal`
    - legal: `legal_action`
    - beautification: `body_parts`, `body_signs`, `procedure_type`
    - conception: `gender`
- Response contract:
  - SSE progress events: `data: {"type":"progress","progress":...}`
  - SSE terminal event: `data: {"type":"done","data":{"top":[...],"location":"...","timezone":"...","stats":...,"series":[...]?}}`

## Engine/scoring pipeline

1. Route dispatch to scorer facade:
   - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:4458-4487`
   - `C:\Users\sabaa\Downloads\codexhorary\backend\election.py`
   - The route selects the matter scorer through `backend/election.py`, which re-exports isolated scorers from `backend/election_models/*`.

2. Chart generation:
   - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2460-2519`
   - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_engine.py:90-102`
   - `_compute_chart_for(...)` delegates to `_compute_chart_bundle_for(...)`, which builds a local `AstroClockSettings` and calls `AstroClockEngine.get_current_data(...)` without mutating global app state.

3. Natal overlay resolution:
   - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2592-2615`
   - `_natal_from_query(...)` resolves either a saved natal snap or a manual natal datetime/location/timezone and then reuses the same chart-bundle helper.

4. Shared scoring utilities:
   - `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\common.py:66-236`
   - Shared helpers include `Score`, house/sign resolution, aspect extraction, Moon via combusta checks, and angular separation math.

## Dependencies on shared context and timing layers

- Solar/lunar return windows:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\context_layers.py:141`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\context_layers.py:293`
- Planetary hours:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\planetary_hours.py:85`
- Moon VOC timeline helpers:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\moon_voc_schedule.py`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\moon_voc_timeline.py`

These are not election-only. The election route consumes the same underlying chart and timing layers used elsewhere in Astro Clock.

# Shared Dependency / Regression Map

## Shared modules that can be affected by election changes

| Shared module | Election use | Other feature exposure | Regression concern |
|---|---|---|---|
| `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py` | Validation route, SSE stream, natal overlay, model-option parsing | Dashboard/current chart endpoints, transits, synastry, trait/profile flows in same blueprint | Route-level parameter or helper changes can leak into non-election endpoints if shared helpers are changed carelessly |
| `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_engine.py` | Generates election chart data for each scan step | Current chart/dashboard retrieval and any feature calling `get_current_data` | Chart-data contract changes would break multiple app surfaces |
| `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\common.py` | Shared sign/house/aspect logic for all election scorers | Every election matter | A bug here would affect validation, streaming, and all matter scorers simultaneously |
| `C:\Users\sabaa\Downloads\codexhorary\backend\context_layers.py` | SR/LR windows for natal-aware election scans | Context layers and transit-oriented features | Changes can alter business and natal-overlay scoring as well as standalone context tools |
| `C:\Users\sabaa\Downloads\codexhorary\backend\planetary_hours.py` | Optional traditional timing boosts | Planetary-hours UI and any other timing-aware screens | Changes affect both election boosts and hours display logic |
| `C:\Users\sabaa\Downloads\codexhorary\backend\moon_voc_schedule.py` / `moon_voc_timeline.py` | Moon-state/VOC context used by scorers through chart data | Moon timeline tooling and other chart consumers | Moon-state interpretation changes could bleed into dashboard/current chart logic |
| `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs` | Election validate/stream request construction | All Astro Clock frontend API calls live in same helper file | Serializer regressions can silently desync renderer and backend contracts |

## Duplicate backend source trees

The repository has two active backend source trees:

- Dev/test backend:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\**`
- Packaged Electron backend resources:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\**`

Evidence:

- Electron dev fallback:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:149-150`
- Packaged-resource preference:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:143-148`

Regression implication:

- Any election-engine fix applied to `backend/**` but not `frontend/backend/**` would make dev/test behavior differ from packaged behavior. I therefore mirrored the surgery fix into both trees and verified parity with `fc`.

## What I re-tested to protect downstream consumers

- Backend election route and scorer matrix:
  - `tests\test_election_route_contracts.py`
  - `tests\test_election_workflow_matrix.py`
  - `tests\test_election_morin_rules.py`
  - `tests\test_election_stress_matrix.py`
  - `tests\test_battle_election.py`
  - `tests\test_beautification_election.py`
  - `tests\test_conception_gender.py`
  - `tests\test_haircut_moon_phases.py`
  - `tests\test_viral_content.py`
- Frontend serializer contract:
  - `frontend/src/tests/astroclockApi.test.mjs`
- Backend source-tree parity:
  - `backend\election_models\surgery.py` vs `frontend\backend\election_models\surgery.py`

# Morin Knowledge Sources Used

## Core extracted source ranges

- Natal promise and timing support:
  - `...book-26.txt:2148-2155`
  - `...book-26.txt:2167-2191`
- General election construction:
  - `...book-26.txt:2761-2819`
- Ascendant suitability, sect, and ruler condition:
  - `...book-26.txt:2844-2860`
- Moon doctrine:
  - `...book-26.txt:2891-2965`
- Urgent-election priorities, malefics, fixed stars:
  - `...book-26.txt:2966-3007`
- Matter-specific rules:
  - surgery/purgings: `...book-26.txt:3014-3025`
  - journey: `...book-26.txt:3026-3030`
  - battle: `...book-26.txt:3031-3034`
  - asking favors from rulers/magnates: `...book-26.txt:3035-3038`

## Practical validation checklist extracted from Morin

1. Do not treat elections as standalone. Morin requires natal promise plus favorable directions/revolutions/transits where possible.
2. Match the election to the relevant house of the matter and fortify that house, the ASC, the MC, and the Moon.
3. Use an Ascendant appropriate to the matter:
   - mobile for quick actions such as journeys
   - fixed for durable matters such as marriage or building
4. Keep the ASC ruler from retrogradation, slowness, malefic affliction, and especially application to malefics.
5. Keep the Moon from:
   - 6th/8th/12th
   - affliction by Saturn/Mars
   - application to retrograde planets
6. Respect Morin Rule 12:
   - avoid Moon applying to Mars from Venus signs
   - avoid Moon applying to Jupiter from Mercury signs
   - avoid Moon applying to Sun from Saturn signs
7. Respect Morin Rule 13 once per actual conjunction condition:
   - Moon conjunct Jupiter/Saturn while increased in light/swiftness is favorable
   - understand the contrary for Moon conjunct Mars/Venus
8. Use preceding lunation and immediate Moon application to judge how the matter begins and ends.
9. In urgent elections, fortify the ASC ruler first and place benefics in angles if full perfection is impossible.
10. For surgery:
    - do not cut the body part when the Moon is in the sign ruling that part
11. For purgings:
    - prefer Moon in water signs, especially Scorpio or Pisces
    - weaken if Moon conjunct Jupiter, in Leo, or in an earth sign
12. For journeys:
    - avoid afflicted 8th and its ruler
    - avoid fixed rising
    - avoid retrograde/malefic ASC ruler
    - avoid afflicted Moon
13. For battle:
    - avoid going out when the ASC ruler is especially weak/afflicted
    - avoid it going to the stronger ruler of the 7th, especially if that ruler is strong or in the 8th
    - avoid badly afflicted Moon

## Explicit ambiguities retained as ambiguities

- Morin explicitly criticizes planetary hours earlier in Book 26, so optional planetary-hour boosts in the app are not Morin-backed doctrine.
- Morin does not give equally explicit matter-specific doctrine for modern app matters such as viral content, haircut, beautification, or generic business launches.
- Morin rejects a blanket prohibition on Moon in the 1st and says the standard argument is groundless, while allowing that medicine/agriculture may occasionally justify caution. I treated that as ambiguous rather than a clear deterministic rule change.

# Election Validation Corpus

## Existing deterministic automated corpus already in repo

- Route/contract:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_route_contracts.py`
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_workflow_matrix.py`
- Morin-grounded scorer checks:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_morin_rules.py`
- Stress/regression matrix:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_stress_matrix.py`
- Matter-specific suites:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_battle_election.py`
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_beautification_election.py`
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_conception_gender.py`
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_haircut_moon_phases.py`
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_viral_content.py`

## New deterministic cases I added

1. Surgery Rule 13 regression:
   - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_morin_rules.py:90-113`
   - Validates that a Moon-Jupiter conjunction in waxing light is scored once, not twice.

2. Frontend validation/stream contract parity:
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs:176-227`
   - Validates that `validateElection(...)` serializes the same matter-specific and natal-aware election parameters as the stream workflow.

## Weaker or manual-review corpus

The following remain partly heuristic and should be reviewed manually when domain precision matters:

- marriage scoring
- contract scoring
- business scoring
- beautification scoring
- viral-content timing
- optional planetary-hour or fixed-star toggles
- non-natal election scans, because Morin prefers natal-aligned elections whenever possible

# Correctness Findings

## Finding 1: Surgery scorer was double-counting Morin Rule 13

- Severity: High
- Exact evidence:
  - Scorer dispatch path:
    - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:4467-4468`
  - Surviving single Rule 13 block after fix:
    - `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\surgery.py:595-631`
  - Regression lock:
    - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_morin_rules.py:90-113`
- Why the current behavior was wrong or risky:
  - Before this patch, the surgery scorer contained two materially identical Rule 13 blocks in the same function. The same Moon-conjunction condition could therefore add the same tag and numeric weight twice, inflating or depressing surgery rankings without any second astronomical event justifying it.
  - That is especially risky in surgery because this scorer is used by the election SSE stream that ranks candidate times, so duplicate weighting can reorder the top elections.
- Morin support:
  - `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt:2906-2914`
  - Morin’s Thirteenth rule is a single doctrinal judgment about Moon conjunctions to Jupiter/Saturn versus Mars/Venus. It does not support counting the same conjunction twice.
- Impact on other app features or shared engine consumers:
  - Direct impact: surgery election suggestions and any surgery validation reasoning derived from the same scorer.
  - Shared consumers:
    - backend stream route via `backend\astro_clock_api.py:4467-4468`
    - packaged Electron backend mirror under `frontend\backend\...`
  - No direct impact on marriage/business/journey/etc. because the change stayed inside the surgery scorer.
- Proposed fix or implemented fix:
  - Implemented.
  - Removed the duplicate later Rule 13 block from:
    - `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\surgery.py`
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\election_models\surgery.py`
  - Added a deterministic regression test asserting:
    - score is `6.2` for the crafted case
    - `"Rule13: Moon conj Jupiter/Saturn while waxing (good)"` appears exactly once

## Finding 2: Renderer validation and stream requests had drifted apart

- Severity: Medium
- Exact evidence:
  - The modal builds one shared `opts` object and uses it for both calls:
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:221-288`
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:290`
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:320`
  - Fixed shared serializer:
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:210-254`
  - Both API methods now use it:
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:568-576`
  - Regression lock:
    - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs:176-227`
- Why the current behavior was wrong or risky:
  - Before this patch, `electionStream(...)` serialized matter-specific fields such as `surgery_sign`, `procedure`, `include_fixed_stars`, `business_mode`, `journey_type`, `action_type`, beautification body fields, contract settings, and manual natal fields, but `validateElection(...)` only serialized a much smaller subset.
  - The result was a workflow mismatch: on SSE error, the UI validated a different request than the one it actually tried to run. That can hide the real failing parameter, reduce user feedback quality, and make future backend validation impossible to rely on.
- Which Morin-based rule or extracted text supports the expected behavior:
  - Indirect support from Morin’s insistence that elections be adapted to the specific matter and its relevant house/significators:
    - `...book-26.txt:2761-2781`
    - `...book-26.txt:2800-2819`
    - `...book-26.txt:3014-3038`
  - If the elected matter depends on matter-specific conditions, the validation path should inspect the same request conditions as the execution path.
- Impact on other app features or shared engine consumers:
  - Direct impact: renderer-side election workflow and user error reporting.
  - No backend scoring algorithm was changed.
  - Low risk to other frontend API helpers because the fix was isolated to the election serializer.
- Proposed fix or implemented fix:
  - Implemented.
  - Added `appendElectionParams(...)` and switched both `validateElection(...)` and `electionStream(...)` to use the same serializer.
  - Added a frontend contract test that asserts the validation URL now includes the same election workflow options as the stream path.

# Changes Made

1. Removed duplicate Morin Rule 13 surgery scoring block from:
   - `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\surgery.py`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\election_models\surgery.py`

2. Added a shared election parameter serializer and reused it in both:
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs`
   - `validateElection(...)`
   - `electionStream(...)`

3. Added regression tests in:
   - `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_morin_rules.py`
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs`

# Tests Added or Updated

## `tests/test_election_morin_rules.py::test_surgery_rule13_is_not_double_counted`

- What it validates:
  - A waxing Moon-Jupiter conjunction in the surgery scorer is only counted once.
- Why it is deterministic enough to automate:
  - The chart fixture is fully synthetic and only exercises one intended Morin Rule 13 branch plus surrounding stable score terms.
- Which workflow or shared dependency it protects:
  - Surgery scorer ranking for the election stream and any surgery validation output using the same scorer.

## `frontend/src/tests/astroclockApi.test.mjs::serializes validation requests with the same election workflow options`

- What it validates:
  - `validateElection(...)` now emits the same matter-specific and natal-aware parameters as the stream workflow.
- Why it is deterministic enough to automate:
  - It asserts pure query serialization in a mocked fetch environment with no backend/network dependency.
- Which workflow or shared dependency it protects:
  - Renderer UI fallback path in `ElectionModal.jsx`, ensuring validation and stream stay contract-aligned as new election options are added.

## Existing suites re-run after the changes

- Backend:
  - `test_election_route_contracts.py`
  - `test_election_workflow_matrix.py`
  - `test_election_morin_rules.py`
  - `test_election_stress_matrix.py`
  - `test_battle_election.py`
  - `test_beautification_election.py`
  - `test_conception_gender.py`
  - `test_haircut_moon_phases.py`
  - `test_viral_content.py`
- Frontend:
  - `src/tests/astroclockApi.test.mjs`

# Regression Risk Review

## Why the implemented changes are low blast-radius

- Surgery fix:
  - confined to the surgery scorer only
  - no shared helper signatures changed
  - mirrored into both backend source trees to avoid dev/package divergence
- Frontend serializer fix:
  - changes only query construction
  - does not change backend route names, HTTP methods, or SSE behavior
  - preserves existing stream URL order by reusing the same parameter order in the shared helper

## Safety checks completed

- Backend suite after edits: `48 passed`
- Frontend Astro Clock API suite after edits: `16 passed`
- Backend mirror parity check:
  - `fc backend\election_models\surgery.py frontend\backend\election_models\surgery.py`
  - result: no differences

## Residual risk that remains

- `election/validate` is still primarily structural and not a full matter-specific backend validator. The frontend fix keeps request contracts aligned, but server-side validation depth remains intentionally limited.
- Optional planetary-hour boosts remain a doctrinal/product choice that is not Morin-backed.
- Modern matters such as viral content or beautification still rely partly on broader traditional heuristics and product design, not only on explicit Morin text.

# Remaining Ambiguities / Manual Review Cases

1. Planetary-hour scoring:
   - Morin is not a clean authority for planetary-hour boosts, yet the app still offers optional traditional timing for several matters. I did not remove it because it is optional and shared across multiple matter scorers.

2. Non-natal elections:
   - Morin strongly prefers elections grounded in the nativity plus current directions/revolutions/transits.
   - The app still supports scans without natal context. That is a product choice, not a safe bug-fix target.

3. Marriage, contract, business, beautification, haircut, and viral-content heuristics:
   - These models include doctrine beyond explicit Morin Book 26 wording.
   - Their current automated tests validate internal consistency and ranking logic, but not every weight is strictly Morin-deterministic.

4. Moon in the 1st for medical matters:
   - Morin rejects the usual blanket prohibition but allows that medicine/agriculture may occasionally justify caution.
   - The surgery model still applies a medical caution for Moon in the 1st.
   - I left that untouched because the text is not deterministic enough to justify a low-risk production change.

5. Backend validation depth:
   - The renderer contract drift is fixed, but the backend validation endpoint still does not perform full matter-specific doctrinal validation.
   - If the product later wants strict preflight validation, that should be implemented deliberately and covered with separate route-contract tests.
