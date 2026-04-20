# Horary Engine Hard Test Plan

## Purpose

This plan defines how to hard-test the horary engine while protecting Astro Clock and any other features that depend on the same engine output, chart serialization, route contracts, or frontend display logic.

The goal is not only to ask whether the engine returns `YES` or `NO`. The goal is to test:

- doctrinal correctness
- backend/frontend verdict parity
- consistency of reasoning and key testimonies
- safety of any engine modifications across shared consumers

## Implementation Status

The first executable phase of this plan is now in source.

## Current Resume State

The horary hard-test program is no longer fully paused.

Current interpretation:

- the Astro Clock receptions issue has been fixed in source
- the packaged/build verification is still pending a clean reinstall and user confirmation
- that means executable replay promotion remains gated, but source-pass corpus work can resume now

What is unblocked:

- doctrine extraction and source-note cleanup
- external-corpus classification
- promotion queue building
- chart-capture prioritisation

What remains gated:

- promoting new external examples into executable replay assertions
- treating packaged UI behaviour as fully verified until the rebuilt app is rechecked on the same chart

## Packaged Receptions Trace Status

The packaged-build receptions trace has now produced a concrete root cause.

Findings:

- the current source fix is present in packaged backend code
- a bare `/api/astro-clock/receptions` check without restoring the same manual/snap chart state is not a like-for-like comparison with a historical chart shown in the UI
- the earlier `No reception` payload came from the backend's active current state at launch time, not from the manual September 2025 chart shown in the UI screenshot
- the old `1.2.6` packaged frontend still contained the outdated receptions tile logic:
  - it treated `traditional_reception` as a string/type flag
  - it derived a boolean badge from `!!(w && M && M != "none")`
  - this is consistent with the old screenshot showing `Traditional true`
- the `1.2.7` packaged frontend contains the corrected summary logic:
  - it parses `traditional_reception` as an object
  - it uses `display_text`
  - it tracks `mutual_count` and `unilateral_count`
- the deeper chart-parity bug was also real in source:
  - `ReceptionsTile` fetched `/api/astro-clock/receptions` independently
  - the main Astro Clock screen rendered the active chart from dashboard `data`
  - this meant the tile could drift from the visible chart if its request was not tied to the same chart state
- implemented fix:
  - `/api/astro-clock/dashboard` now includes chart-scoped `receptions`
  - `transformDashboard(...)` preserves that field
  - `ReceptionsTile` now prefers chart-scoped receptions data and only falls back to `/receptions` when needed
- the machine had two packaged installs at the same time:
  - `C:\Users\sabaa\AppData\Local\Programs\Vox Stella\Vox Stella.exe` -> `1.2.6`
  - `C:\Program Files\Vox Stella\Vox Stella.exe` -> `1.2.7`
- the old `1.2.6` copy created build-drift risk during manual testing because the user could still launch an outdated renderer while a newer packaged backend was present elsewhere
- the old per-user install has been retired by renaming it to:
  - `C:\Users\sabaa\AppData\Local\Programs\Vox Stella 1.2.6-old`
- at one point the active Start Menu shortcut resolved to:
  - `C:\Program Files\Vox Stella\Vox Stella.exe`
- later reinstall behaviour showed that the installer may switch the live path back to:
  - `C:\Users\sabaa\AppData\Local\Programs\Vox Stella\Vox Stella.exe`
- therefore the durable rule is not a specific install path but:
  - only one active packaged install should exist during parity testing

Interpretation:

- the packaged issue had two contributing causes:
  - install drift from multiple packaged versions
  - a real tile/data-path mismatch where receptions were not bound to the same active chart payload
- the next required check is a clean relaunch of the surviving `1.2.7` packaged app and a confirmation that the tile now matches the active chart after manual/snap changes
- if reinstall changes the install root again, the path should be rechecked before drawing any conclusion from packaged behaviour

This means the blocker is no longer "unknown packaged bug" but "rebuild/relaunch verification of the implemented chart-scoped receptions fix"

## Priority Override

Until packaged receptions parity is confirmed after reinstall, the work order becomes:

1. keep the existing executable horary corpus frozen
2. continue external-corpus source-pass work only
3. prioritise chart-capture candidates with the clearest published metadata
4. confirm packaged build parity with current source
5. only then promote new external examples into executable tests

## Immediate Plan Order

### Step 1. Freeze the current horary hard-test baseline

Keep the current source-based horary harness as the active baseline:

- `tests/fixtures/horary_hard_test_corpus.json`
- `tests/test_horary_hard_test_corpus.py`
- `frontend/src/tests/horaryHardCorpusParity.test.mjs`
- `tests/fixtures/horary_external_cunning_man_corpus.json`

No further executable corpus promotion should happen until packaged receptions parity is confirmed.

Allowed work while that check is pending:

- classify external examples
- rank promotion candidates
- record blocking reasons
- prepare doctrine notes for later replay promotion

### Step 2. Reproduce the receptions discrepancy in packaged mode

Target question:

- why does the receptions tile behave correctly in developer/source mode but incorrectly in the packaged build?

Required check:

1. inspect `/api/astro-clock/receptions` data in source/dev
2. inspect the same endpoint/result path in packaged mode
3. compare:
   - `traditional_reception`
   - `mutual`
   - `top_unilateral`
   - rendered tile summary

### Step 3. Check for build drift first

The most likely first class of failure is not doctrine but packaging drift.

Verify:

- the packaged backend contains the current `backend/astro_clock_api.py`
- the packaged frontend contains the current `frontend/src/features/astroclock/ReceptionsTile.jsx` output
- the build was produced after the receptions fix
- no stale packaged resources or old installer are being tested

### Step 4. Confirm source/build contract parity

If build drift is not the cause, verify whether the packaged app changes behavior at one of these boundaries:

- Electron -> backend startup path
- packaged backend chart_result serialization
- `/api/astro-clock/receptions` route output
- packaged frontend response handling

This step should produce a simple parity table:

- source endpoint payload
- packaged endpoint payload
- source rendered tile
- packaged rendered tile

### Step 5. Fix receptions in the narrowest packaged-safe layer

If the issue is real in current packaged code:

- prefer fixing the receptions route or receptions tile only
- avoid touching shared horary verdict logic unless the packaged issue truly originates there
- keep the fix narrow to Astro Clock receptions display/route behavior

### Step 6. Rebuild and retest the packaged app

After any receptions fix:

- rebuild from source
- retest the same packaged flow
- confirm parity with developer mode

Current status:

- narrow route/tile fix already exists in source
- packaged backend parity is confirmed
- duplicate-install drift has been reduced by retiring the old `1.2.6` install
- remaining work is a clean packaged-app relaunch verification, not a new code change

### Step 7. Resume executable horary hard-test expansion

Only after packaged receptions parity is confirmed:

1. continue chart-capture work for external examples
2. promote source-backed examples into executable fixtures
3. compare backend verdict vs frontend verdict
4. compare engine logic vs source verdicts

Starter corpus and harness:

- `tests/fixtures/horary_hard_test_corpus.json`
- `tests/horary_hard_test_utils.py`
- `tests/test_horary_hard_test_corpus.py`
- `frontend/src/tests/horaryHardCorpusParity.test.mjs`

Current implemented starter corpus:

- 11 total cases
- 6 deterministic cases
- 5 manual-review cases

Current starter coverage includes:

- government office / career
- gambling / lottery
- funding
- education
- general quality question
- pregnancy / conception
- marriage
- divorce
- property advisability
- reconciliation

Current verification status:

- backend starter corpus and shared horary/Astro Clock slice:
  - `python -m pytest tests\test_horary_hard_test_corpus.py tests\test_horary_question_corpus.py tests\test_horary_manual_review_corpus.py tests\test_horary_government_job_case.py tests\test_astroclock_adapter_fixes.py tests\test_horary_internal_chart_passthrough.py tests\test_astroclock_internal_chart_passthrough.py -q`
  - result: `28 passed, 1 warning`
- frontend parity and shared verdict-path slice:
  - `npx vitest run src/tests/horaryHardCorpusParity.test.mjs src/tests/normalizeHoraryApiResult.test.mjs src/tests/buildChartPayload.test.mjs src/tests/astroclockApi.test.mjs --config vitest.config.mjs`
  - result: `20 passed`

## Non-Negotiable Safety Rule

No horary change should be made in isolation.

Any modification to shared horary logic must be treated as potentially affecting:

- the main horary route
- Astro Clock chart consumers
- Astro Clock judgment display
- receptions and determination views
- forensic chart consumers if they reuse shared chart/evaluation helpers
- export/share/AI-analysis payload builders
- saved chart replay and rerun flows

This means every horary correction must be paired with shared-regression verification.

## Shared Workflow Surfaces That Must Be Protected

### Backend

- `backend/app.py`
  - `/api/calculate-chart`
- `backend/horary_engine/engine.py`
- `backend/horary_engine/serialization.py`
- `backend/evaluate_chart.py`
- `backend/category_rules.py`
- `backend/question_analyzer.py`

### Astro Clock / shared backend consumers

- `backend/astro_clock_api.py`
- `backend/astro_clock_engine.py`
- shared chart deserialization and raw-chart passthrough helpers

### Frontend

- `frontend/src/App.jsx`
  - cast-chart request path
  - rerun path
  - chart save/replay path
  - displayed judgment/confidence path
- `frontend/src/utils/buildChartPayload.js`
- `frontend/src/utils/normalizeHoraryApiResult.mjs`

## Testing Strategy Overview

The hard-test process should run in seven phases.

### Phase 1. Freeze the current shared contract

Before adding new doctrinal pressure to the engine:

- pin the current backend output shape for `/api/calculate-chart`
- pin frontend rendering of `judgment`, `confidence`, and `outcome`
- pin saved chart replay behavior
- pin Astro Clock shared adapter behavior

Why:

- if a future doctrinal change causes a regression, we need to know whether the break happened in engine logic, route shape, serializer shape, or frontend normalization

### Phase 2. Build a doctrine-backed example corpus

Build a test corpus of at least 10 to 15 horary examples.

The examples should come from three sources:

1. existing repository fixtures and manual-review charts
2. historical/traditional examples from Lilly first, then Sahl/Bonatti where clear enough
3. app-relevant practical questions already supported by current categories

Minimum target distribution:

- 2 career / office questions
- 2 relationship / marriage / reconciliation questions
- 2 property questions
- 1 pregnancy / conception question
- 1 lawsuit / conflict question
- 1 funding / money question
- 1 health / illness question
- 1 lost-object or recovery question
- 1 explicit manual-review / ambiguous case

Each case should record:

- question text
- chart input data
- expected category
- expected primary significators
- expected verdict direction
- expected main testimonies
- source authority or reason for expectation
- whether the case is deterministic or manual-review only

### Phase 3. Split cases into deterministic vs manual-review

Not all horary examples are safe to automate at the same level.

#### Deterministic automated cases

Use these for hard assertions:

- clear perfection or clear denial
- clear house assignment
- clear doctrinal weight from Lilly or very strong traditional consensus
- stable expected direction

Automated assertions should check:

- backend verdict
- backend category
- key significators
- perfection type if relevant
- presence of key reasoning lines
- frontend parity with backend verdict

#### Manual-review cases

Use these when:

- doctrine is mixed
- multiple testimonies conflict
- the chart is better used to audit explanation quality than hard yes/no direction

Manual-review assertions should check:

- correct category
- correct house/significator selection
- presence of the right doctrinal factors
- no internal contradiction in the reasoning

### Phase 4. Backend truth-first execution

Run every corpus case through the backend first.

Required execution layers:

1. direct engine-level replay where useful
2. `/api/calculate-chart` contract replay
3. rerun/replay path for saved charts when relevant

For every case, record:

- backend `judgment`
- backend `confidence`
- backend `traditional_factors`
- key reasoning lines
- whether the result matches the doctrinal expectation

Current external replay note:

- article-derived replay is now possible when the source gives:
  - an exact timestamp
  - a published wheel image
- this lets us compare backend output to an external article without inventing a cast location
- the first external replay slice also surfaced and justified a shared boundary fix:
  - `serialization.py` now normalises human-readable planet names like `North Node` during deserialisation

Why:

- backend output is the source of truth for the app
- frontend should display and preserve the backend result, not reinterpret it

### Phase 5. Frontend parity verification

For each important case, confirm the frontend displays the same judgment that the backend returned.

This should cover:

- new cast path
- saved chart path
- rerun path
- export/share path where relevant

Specific parity checks:

- `backend judgment == saved chart judgment`
- `backend judgment == displayed judgment`
- `backend confidence == displayed confidence` unless explicitly rounded
- `outcome` must be derived from backend `judgment`
- no conflicting secondary field such as `result` may override `judgment`

### Phase 6. Category-local correction policy

If the corpus reveals a genuine horary error:

- change the narrowest category-local layer first
- prefer question classification, category rules, or category-local finalization before touching broad shared engine behavior
- only touch cross-category shared logic when the evidence is strong and repeated across multiple examples

Examples of safer first-change layers:

- `question_analyzer.py`
- `category_rules.py`
- category-specific helper modules

Examples of higher-risk layers:

- broad verdict finalization logic in `engine.py`
- shared serialization/deserialization behavior
- frontend display normalization

### Phase 7. Regression verification after every fix

After any horary change, rerun:

- horary doctrine corpus tests
- horary manual-review corpus tests
- frontend verdict normalization tests
- Astro Clock adapter and passthrough tests
- any route contract tests touching shared chart structures

No horary fix is complete until the shared slice is re-verified.

## Proposed Example Acquisition Plan

The next execution step should be to collect at least 10 examples before changing more horary logic.

### Source priority

1. Lilly examples and clear doctrinal chapters
2. existing repo fixtures and user-reported charts
3. Sahl / Bonatti only when the text is accessible and clear enough

## External Corpus Resume Queue

The Cunning Man external corpus can now advance in a controlled order.

### Queue A. Source pass and metadata cleanup

Apply structured tags to every external case:

- `source_pass_status`
- `promotion_priority`
- `manual_review_only`
- `blocking_reason`

This work is safe now because it does not affect engine behaviour.

### Queue B. Promote strongest chart-capture candidates first

Prioritise cases with the clearest published metadata and the clearest verdict direction:

1. `will_i_get_job`
2. `will_we_win_award`
3. `pay_rise`
4. `exams`
5. `x_romantically`
6. `pope_die`

These are the best early candidates for eventual executable replay.

Current status:

- first executable promotion is now in source for:
  - `pay_rise_article_spec`
  - `x_romantically_article_spec`
  - `pope_die_article_spec`
- only `pay_rise_article_spec` is currently source-aligned
- the other two are replay-ready manual-review disagreements, which is still useful because they isolate doctrine-vs-engine issues without speculative recasting

### Queue C. Keep certain cases manual-review only

Do not plan these as executable replay targets unless stronger source data is found:

- `does_he_love_me`
- `can_ai_help_horary`

Reasons:

- anonymised chart details
- meta-discussion rather than a standard querent/outcome case

### Queue D. Wait for packaged parity before executable promotion

Even high-priority external cases should remain source-pass only until the packaged receptions verification is completed on the rebuilt app.

### First target set

1. Government job / office attainment
2. Career advancement / preferment
3. Marriage question
4. Reconciliation question
5. Divorce or separation question
6. Property acquisition question
7. Property advisability / investment question
8. Pregnancy / conception question
9. Funding / money question
10. Lawsuit / conflict question
11. Lost object or recovery question
12. One deliberately mixed chart for manual review only

## What “Correctness” Means in This Plan

A case is not judged correct just because the engine says `YES` or `NO`.

The result must also be correct in:

- category assignment
- significator choice
- perfection logic
- treatment of Moon testimony
- treatment of receptions and prohibitions
- weighting of major testimonies
- internal consistency of the reasoning

Example:

- if the final verdict is plausible but the wrong significators were used, the case is still a failure
- if the verdict is plausible but frontend display flips or degrades it, the case is still a failure

## Concrete Test Layers to Build

### 1. Doctrine unit tests

Test pure rule helpers where possible:

- category classification
- property family split
- category-local doctrine helpers
- normalization helpers

### 2. Engine regression tests

Replay deterministic cases through the horary engine and assert:

- verdict
- confidence direction
- perfection type
- key reasoning

### 3. API contract tests

Hit `/api/calculate-chart` and assert:

- returned `judgment`
- returned `confidence`
- returned `chart_data`
- returned `question_analysis`
- stable route contract

### 4. Frontend parity tests

Assert that:

- cast path stores backend `judgment`
- rerun path preserves backend `judgment`
- saved chart path displays the same `judgment`
- conflicting secondary fields do not override backend `judgment`

### 5. Astro Clock regression tests

Assert that:

- shared chart handling still works
- shared adapters still accept the same chart structures
- no horary modification breaks Astro Clock consumers

## Execution Order

Recommended order:

1. collect 10 to 15 examples
2. classify them as deterministic or manual-review
3. run them against backend engine and route
4. run frontend parity checks
5. compare doctrinal expectation vs actual output
6. identify repeated failure patterns
7. make only the smallest safe fix
8. rerun horary and Astro Clock regressions

## Acceptance Criteria

The hard-test phase is successful when:

- a doctrine-backed corpus of 10+ examples exists
- deterministic cases have automated assertions
- manual-review cases have structured reasoning checks
- backend and frontend verdicts match on tested cases
- any identified fix is category-local unless strong evidence justifies broader change
- Astro Clock shared regressions remain green

## Recommended Immediate Next Step

The first doctrine-backed root-fix slice is now implemented.

Completed against the external replay corpus:

1. reciprocal-affection questions now use an affection-specific doctrine layer instead of bare perfection alone
2. explicit death questions now outrank generic health matching
3. titled third-party death questions can route to turned houses:
   - clergy/religious figures -> 9th
   - their death -> turned 8th from that subject
4. the first three promoted external replay cases are now source-aligned

Next step should be:

1. keep growing the external corpus with more source-backed cases
2. promote the next 3 to 5 capture-ready cases into executable replay fixtures
3. keep frontend parity checks paired with every backend corpus promotion
4. continue packaged/source parity checks for shared Astro Clock surfaces before widening engine changes
