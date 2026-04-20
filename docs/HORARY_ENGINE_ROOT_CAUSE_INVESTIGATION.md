# Horary Engine Root Cause Investigation

## Executive Summary

This investigation was opened for a reported logic drift on the question:

- `Will I get a job? (government position)`
- asked `2001-05-15 10:20`
- `Washington, District of Columbia`
- timezone `America/New_York`

Current source reproduction does **not** show a core horary-engine flip from `YES` to `NO`.
The source engine still judges this chart `YES` with direct perfection, Moon as `L1`, and Mars as `L10`.

The strongest root-cause finding is elsewhere:

1. the frontend "Analyze with AI" export path was emitting an incomplete chart payload for external review, and
2. that payload could omit the actual serialized house rulers and could fall back to `general` instead of the real chart category when `tags` were absent.

That makes external-model judgments unstable and can easily explain why a copied prompt once came back `YES` and later came back `NO`, even though the app's own source engine still returns `YES`.

Because the horary engine is shared with Astro Clock and Astro Clock feeds multiple downstream features, the implemented fix was intentionally narrow:

- fix the exported AI-analysis payload
- add a backend regression proving the source horary engine still returns `YES` on this chart
- avoid speculative shared-engine rule edits until doctrine and downstream impacts are fully mapped

## Investigation Scope

- No chart-specific patching.
- No packaged/build-artifact edits.
- No speculative shared-engine change while Astro Clock dependencies remain exposed.
- Primary focus: root cause, shared-risk mapping, and the safest correct fix.

## Phase Status

1. Source collection and extraction: completed for the current office/property pass
2. Dependency and regression mapping: completed for the shared horary/Astro Clock slice
3. Deterministic reproduction of the target case: completed
4. Doctrine-to-engine comparison: in progress
5. Root-cause isolation: completed for the reported drift path
6. Minimal shared fix: completed for the export-contract defect
7. Regression verification: completed for the implemented change set

## Traditional Source Packet

### Fetched Sources

- William Lilly, *Christian Astrology*: [Wikisource](https://en.wikisource.org/wiki/Christian_Astrology)
- William Lilly, *Christian Astrology* Book II OCR/PDF with chapter index including the tenth-house office chapter: [astrology.gr PDF](https://www.astrology.gr/images/-_ca_ii_-a-.pdf)
- Sahl ibn Bishr / Māshā’allāh excerpt PDF: [Bendykes excerpt](https://bendykes.com/wp-content/uploads/2016/08/wsm-exerpt.pdf)
- Bonatti property contents page: [Project Hindsight Bonatti contents](https://www.projecthindsight.com/archives/medieval%20contents/bonatti.html)
- Sahl ibn Bishr source index / catalog entry: [Open Library](https://openlibrary.org/books/OL27345270M/The_Astrology_of_Sahl_b._Bishr_Volume_I/widget)
- Bonatti source index / catalog entry: [Open Library](https://openlibrary.org/books/OL24560609M/The_book_of_astronomy)

### What Was Extracted Reliably in This Pass

- Lilly Book II chapter index confirms the relevant office/preferment material:
  - tenth house = government, dignity, office, command
  - chapter `444`: whether the querent shall obtain the office desired
  - chapter `456`: if attain the preferment desired
- Lilly property chapters were extracted directly enough to support implementation:
  - chapter `204`: buying and selling lands, houses, farms
    - `L1`/Asc = querent or buyer
    - `L7`/Desc = seller
    - `L4` plus Moon = house, ground, manor, inheritance
    - `L10` = price
  - chapter `205`: goodness or badness of the land or house
    - strong infortunes in the 4th, or a badly afflicted `L4`, damage the quality/endurance of the property
    - benefics in the 4th, or a strong `L4`, support good success and increase for the money
  - chapter `208`: whether it is good to hire/take the house, farm, or land desired
    - `L10` explicitly signifies profit from the undertaking
    - `L4` signifies the end of the matter
    - fortunes in the 10th/4th support the bargain; infortunes there oppose it
- Bonatti property contents confirm two distinct question families:
  - `Concerning a House or an Inherited Property Which Someone Intends to Buy`
  - `Whether the Hiring of Land or a House Would Be Profitable`
- Sahl's accessible excerpt supports the general method:
  - the Lord of the Ascendant and the Moon remain the principal operators in questions
  - if the Lord of the Ascendant cannot adequately carry the matter, the Moon's testimony becomes the operative fallback
- A comparison reading of Lilly's office example, summarized by Anthony Louis from Lilly chapter 86, was used only as a secondary explanatory aid:
  - office questions are judged from the Ascendant/querent and the tenth house/office
  - placement of the office significator in the tenth supports attainment
  - Moon testimony and later impediments can show difficulty without canceling the final acquisition
  - false-friend/hidden-enemy testimony can complicate or delay preferment rather than deny it outright

### Current Doctrine Working Checklist

This checklist is the working baseline for the present root-cause pass:

- For office/government preferment, judge from `L1` and `L10`.
- Direct applying perfection between the querent and office significators carries high weight.
- Moon testimony matters heavily in office questions.
- Debility or retrogradation of the office significator weakens, delays, or complicates the result.
- Later affliction after perfection can describe obstacles or corruption after acquisition, not necessarily denial of acquisition.
- Hidden-enemy or twelfth-house testimony can obstruct or delay office attainment.
- Property doctrine now adds:
  - acquisition and advisability/profit property questions should not be treated as one rule family
  - `L2` does not become co-primary in Lilly's property chapters; it remains secondary at most
  - advisability/profit questions should weigh `L10` for profit and `L4` for the property/end
  - no-perfection quality questions can still be favorable when profit and property/end testimonies are jointly strong
  - severe `L4` affliction, or a strong infortune in the 4th, should dominate against a favorable answer

### Source Limits Still Open

- Full translated property text from Sahl and Bonatti was not already present in the repo; the accessible online material in this pass was limited to excerpt/methodology material and Bonatti contents.
- The property-family split and the `L10`/`L4` implementation are grounded primarily in Lilly, with Bonatti used to confirm the family distinction and Sahl used for general question-method support.

## Shared Dependency / Regression Map

### Main Horary Route

- `backend/app.py`
  - `/api/calculate-chart`
  - calls `HoraryEngine`
  - then attempts auxiliary `evaluate_chart(...)`

### Core Horary Engine Surface

- `backend/horary_engine/engine.py`
  - `HoraryEngine.judge(...)`
  - `EnhancedTraditionalHoraryJudgmentEngine.judge_question(...)`
  - serialization of `chart_data`
- `backend/horary_engine/serialization.py`
  - shared serialization/deserialization contract
- `backend/evaluate_chart.py`
  - auxiliary ledger/rationale path
- `backend/category_rules.py`
  - auxiliary category weighting/rule scope

### Astro Clock Shared Consumers

- `backend/astro_clock_api.py`
  - imports `deserialize_chart_for_evaluation`
  - imports `TraditionalReceptionCalculator`
  - uses shared chart structures for:
    - receptions
    - determinations
    - forensic analysis
    - election validate
    - election stream

### Frontend Consumer Relevant to the Reported Drift

- `frontend/src/App.jsx`
  - `handleAnalyzeWithAI`
  - exports a prompt for an external model
- `frontend/src/utils/buildChartPayload.js`
  - builds the exported chart payload

### Regression Surface Protected Before Shared Logic Edits

- Horary route output contract
- Astro Clock chart-data consumers
- election validation / election stream chart helpers
- receptions fallback paths using shared deserialization
- any downstream consumer expecting `chart_data.house_rulers`

## Deterministic Reproduction

### Reproduction Method

The target chart was replayed directly through the source horary engine with:

- location: `Washington, District of Columbia`
- date: `2001-05-15`
- time: `10:20`
- timezone: `America/New_York`
- house system: `R`
- `use_current_time=False`

### Current Source Result

- judgment: `YES`
- confidence: `66`
- category: `career`
- relevant houses: `[1, 10]`
- `L1 = Moon`
- `L10 = Mars`
- perfection type: `direct`
- reception: `none`

### Key Engine Signals Present

- Moon is not void of course.
- Quesited significator Mars is retrograde, which weakens and complicates the result.
- The engine still finds a direct perfection.
- Serialized chart data includes `house_rulers`, including:
  - house `1` -> `Moon`
  - house `10` -> `Mars`

## Root Cause Findings

### Finding 1: The reported YES -> NO drift is reproducible in the external AI export path, not in the core engine

Evidence:

- `backend/horary_engine/engine.py` still returns `YES` for the target chart.
- `frontend/src/App.jsx` copies a prompt for a third-party AI assistant rather than reusing the backend verdict.
- `frontend/src/utils/buildChartPayload.js` was exporting `rulers: chart.chart_data?.rulers || {}` even though the backend serializes `house_rulers`, not `rulers`.

Why this matters:

- The external AI was being asked to judge from incomplete data.
- Missing `house_rulers` makes significator assignment less reliable in traditional horary, especially for an office/government question where `L1` and `L10` are central.
- If `tags` were absent, the exported payload could also report the chart as `general` instead of `career`, weakening downstream prompt interpretation further.

Conclusion:

- The strongest supported root cause of the observed drift is an export-contract defect, not a demonstrated core-engine flip.

### Finding 2: The core engine's present judgment is doctrinally plausible

Evidence from the current source run:

- `L1 = Moon`
- `L10 = Mars`
- direct perfection
- Mars retrograde
- later difficult testimony also present

Doctrinal reading:

- This is consistent with a `YES, but with obstacles / delay / complication` style judgment rather than a clean denial.
- That is closer to the present source engine output than to an outright `NO`.

### Finding 3: There is a secondary shared-risk inconsistency in the auxiliary evaluation path

Observed during investigation:

- `evaluate_chart(...)` is a separate scoring/ledger path.
- `backend/category_rules.py` currently has no specific `Category.CAREER` ruleset.
- The default rule set is not office-specific.

Implication:

- Auxiliary evaluation and primary horary judgment are not guaranteed to align on career questions.
- This was documented but not changed in this pass because it affects shared helpers and needs a dedicated doctrine-backed review.

### Finding 4: Deserialization remains brittle around serialized planet names with spaces

Observed during direct evaluation replay:

- `deserialize_chart_for_evaluation(...)` expects enum-style planet keys.
- serialized chart payloads can include `North Node`.

Implication:

- Some shared deserialization consumers can fail or silently fall back.
- This is documented as a follow-up risk because correcting it without also reviewing auxiliary scoring could change downstream behavior in unexpected ways.

## Changes Made

### 1. Export-contract fix for external horary review

Updated:

- `frontend/src/utils/buildChartPayload.js`

Changes:

- export `house_rulers` explicitly
- alias `rulers` to the same serialized house-ruler map for compatibility
- preserve `category` from `chart.category` when `tags` are absent
- include `ascendant`, `midheaven`, `considerations`, and Moon next/last aspect context when present

Reason:

- external horary review needs the same core significator data the app itself uses
- this is the narrowest fix that addresses the reported drift without touching the shared horary engine

### 2. Regression proving the source engine still judges the chart affirmatively

Added:

- `tests/test_horary_government_job_case.py`

Reason:

- protects against future accidental changes that would silently flip the app's own verdict on this chart
- monkeypatches geocoding to keep the test deterministic and local

### 3. Regression protecting the AI export path

Added:

- `frontend/src/tests/buildChartPayload.test.mjs`

Reason:

- ensures exported AI-analysis payloads retain the house-ruler and core horary context needed for auditable judgment

### 3A. Frontend live verdict-path normalization

Updated:

- `frontend/src/App.jsx`
- `frontend/src/utils/normalizeHoraryApiResult.mjs`

Added:

- `frontend/src/tests/normalizeHoraryApiResult.test.mjs`

Changes:

- extracted a shared frontend normalization helper for `/api/calculate-chart` responses
- made the renderer treat backend `judgment` as the canonical display field
- ensured the cast and rerun paths both derive `outcome` from `judgment` in one place
- explicitly ignored any conflicting secondary `result` field when `judgment` is present
- preserved fallback confidence derivation from `confidence_breakdown` / `scoring_trace`

Reason:

- the live renderer trace did not reproduce a separate in-app `YES -> NO` inversion
- this hardens the exact response -> saved chart -> displayed verdict path so future frontend drift cannot silently prefer a secondary field over the backend verdict

### 4. Safe raw-chart passthrough for same-process consumers

Updated:

- `backend/horary_engine/engine.py`
- `backend/app.py`
- `backend/astro_clock_engine.py`
- `backend/astro_clock_api.py`

Changes:

- added optional internal raw-chart passthrough for same-process backend callers
- kept `serialization.py` as the external contract for UI/export/replay
- changed `/api/calculate-chart` to prefer the in-memory chart object before deserializing `chart_data`
- changed Astro Clock receptions/forensic fallback paths to do the same when the chart was freshly computed in-process

Reason:

- this removes unnecessary serialize -> deserialize churn without breaking the shared payload contract used by Astro Clock, exports, saved scans, or frontend consumers

### 5. Internal chart-bundle helpers for Astro Clock natal/context paths

Updated:

- `backend/astro_clock_api.py`

Added:

- `tests/test_astroclock_chart_bundle_helpers.py`

Changes:

- added `_compute_chart_bundle_for(...)` as an internal helper under `_compute_chart_for(...)`
- added `_natal_bundle_from_query(...)` as an internal helper under `_natal_from_query(...)`
- kept the public wrapper contracts unchanged at `(chart_data, meta)`
- ensured the raw chart object stays internal to the backend helper layer instead of being pushed into `chart_data` or `meta`

Reason:

- this is the next safe step after the first passthrough change
- it extends the same-process raw-chart path deeper into Astro Clock natal/context resolution without changing any frontend or route payload contract
- it creates a safe internal seam for later consumers that may need the live chart object, while preserving compatibility for current chart-data-based features

### 6. Quality-question no-perfection blocker cleanup

Updated:

- `backend/horary_engine/engine.py`

Added:

- `tests/test_horary_judgment_fixes.py`

Issue:

- quality-form horary questions such as property/advisability cases were still inheriting occurrence-style `no_perfection` handling
- the engine comments already stated that quality questions should be judged more by condition and secondary testimonies when no direct perfection exists
- in practice, the no-perfection path still labeled the result as a denial and could synthesize a `no_perfection` blocker during hybrid confidence calculation

Changes:

- quality questions with `perfection_type == none` no longer synthesize a `no_perfection` blocker during hybrid confidence calculation
- the no-perfection quality path now records:
  - a neutral quality-assessment line for absence of direct perfection
  - separate secondary-support testimonies such as one-way reception
- the old mixed denial/support string is no longer used for quality questions

Reason:

- this removes an internal occurrence-vs-quality contradiction without forcing a speculative doctrinal flip on any specific chart
- it keeps occurrence-style strict no-perfection handling intact for event/reunion questions
- it narrows the blast radius to quality-question finalization and reasoning structure only

### 7. Property-investment case status after the fix

Reproduced case:

- question: `should I invest in this house?`
- category: `property`
- datetime: `2025-09-27 17:25 Europe/London`

Observed source behavior after the cleanup:

- the analyzer still routes the case correctly to `Category.PROPERTY`
- the engine still classifies the wording as a `QUALITY` question
- the output remains `NO`, but now for coherent condition-based reasons instead of an occurrence-style synthetic `no_perfection` blocker
- direct replay after the doctrine pass now returns:
  - `result = NO`
  - `confidence = 65`
  - `perfection_type = none`
  - `property_family = advisability_profit`
- the replayed reasoning now makes the doctrinal balance visible:
  - `Mercury under beams`
  - `No direct perfection found between Saturn and Mercury; judging the question by condition and secondary testimonies`
  - `10th-house profit testimony: L10 (Jupiter) is strongly dignified`
  - `4th-house property condition: L4 (Mercury) is somewhat weakened`

Why this matters:

- a real logic bug was present and has been fixed
- but the chart's final verdict was not forcibly changed to `YES`
- doing that without a dedicated property doctrine pass would be speculative

Current doctrinal status:

- no direct perfection exists between `L1` and `L4`
- `L4` Mercury is under the beams
- there is some secondary support, but not enough current evidence to justify an automatic affirmative flip

Current implementation stance:

- keep the structural fix
- defer any chart-result or category-policy change until property/advisability doctrine is reviewed explicitly against Lilly/Sahl/Bonatti

### 8. Property doctrine pass implemented

Implemented source changes:

- `backend/horary_engine/property_doctrine.py`
- `backend/question_analyzer.py`
- `backend/category_rules.py`
- `backend/horary_engine/engine.py`

What changed:

- property questions are now classified into doctrine families:
  - `acquisition`
  - `advisability_profit`
  - `condition`
- property routing now carries explicit metadata for:
  - `property_house = 4`
  - `seller_house = 7`
  - `profit_house = 10`
  - `end_house = 4`
- category-local property rules were corrected from the old `[2, 8, 11]` outcome emphasis to a Lilly-style `[4, 7, 10]` emphasis
- `L2` was kept secondary, not promoted to co-primary
- property `QUALITY` questions now run a doctrine-specific no-perfection assessment:
  - 10th-house profit testimony
  - 4th-house property/end testimony
  - querent readiness in the 1st
  - clear yes/no only when the property testimony is sufficiently decisive
  - otherwise the engine falls back to the generic quality path and preserves a mixed/manual-review style case

Validation corpus added:

- deterministic doctrine-unit cases:
  - clear `YES` property-advisability snapshot
  - clear `NO` property-advisability snapshot
  - analyzer family split
  - property rule-derivation / `L2` audit
- manual-review corpus:
  - the real `should I invest in this house?` chart now replays with explicit profit-vs-property doctrine reasoning instead of generic property handling

## Validation Run

### Backend

Executed:

- `python -m pytest tests\\test_horary_government_job_case.py -q`
- `python -m pytest tests\\test_horary_internal_chart_passthrough.py tests\\test_astroclock_internal_chart_passthrough.py tests\\test_astroclock_adapter_fixes.py -q`
- `python -m pytest tests\\test_astroclock_chart_bundle_helpers.py -q`
- `python -m pytest tests\\test_horary_judgment_fixes.py tests\\test_horary_question_corpus.py tests\\test_horary_manual_review_corpus.py tests\\test_horary_government_job_case.py -q`
- `python -m pytest tests\\test_property_doctrine_pass.py tests\\test_horary_manual_review_corpus.py tests\\test_horary_question_corpus.py tests\\test_horary_judgment_fixes.py tests\\test_horary_government_job_case.py -q`
- `python -m pytest tests\\test_astroclock_adapter_fixes.py tests\\test_horary_internal_chart_passthrough.py tests\\test_astroclock_internal_chart_passthrough.py -q`
- `python -m pytest tests\\test_property_doctrine_pass.py tests\\test_horary_manual_review_corpus.py tests\\test_horary_question_corpus.py tests\\test_horary_judgment_fixes.py tests\\test_horary_government_job_case.py tests\\test_astroclock_adapter_fixes.py tests\\test_horary_internal_chart_passthrough.py tests\\test_astroclock_internal_chart_passthrough.py -q`

Observed result:

- `26 passed, 1 warning`

Expected protection:

- target government-job chart remains `YES`
- category and key significators stay stable
- same-process backend callers reuse the live chart object instead of redundantly deserializing serialized payloads
- internal Astro Clock chart/natal helper bundles retain the raw chart while the legacy public wrappers still return only `chart_data` and `meta`
- quality-form no-perfection cases no longer get a synthetic occurrence-style blocker or a misleading positive-weight denial line
- property questions now:
  - split into acquisition / advisability / condition families
  - keep `L2` secondary
  - elevate `L10` only for property profit/advisability handling
  - replay the real property-investment chart with explicit 10th-vs-4th doctrine notes

### Frontend

Executed:

- `npx vitest run src/tests/buildChartPayload.test.mjs --config vitest.config.mjs`
- `npx vitest run src/tests/astroclockApi.test.mjs src/tests/buildChartPayload.test.mjs --config vitest.config.mjs`

Observed result:

- `6 passed`

Expected protection:

- AI export preserves `house_rulers`
- AI export preserves category fallback
- AI export includes core context without leaking the app verdict when `includeVerdict=false`

## Current Interpretation of the Reported Cases

At this stage, the defensible interpretation is:

- for the reported government-job chart, the app's source horary engine still reads the chart as affirmative with notable obstacles; the unstable `NO` is best explained by the copied external-AI analysis path receiving incomplete horary context
- for the property-investment chart, the engine now gives an explicit doctrine-local `NO` trace grounded in:
  - no direct perfection between `L1` and `L4`
  - `L4` Mercury under the beams
  - strong `L10` profit testimony that helps, but does not overpower the weakened property testimony
- the important fix is not that every former `YES` becomes `YES` again; it is that the engine now distinguishes property acquisition from property advisability and explains the property result with the correct house logic

## Remaining Work

1. complete fuller Lilly extraction from the office/preferment chapters themselves, not only the chapter map and comparison note
2. obtain fuller translated Sahl/Bonatti property text before making stronger property-sufficiency overrides on live charts
3. review whether `backend/category_rules.py` needs a dedicated `Category.CAREER` rule set
4. review whether serialized planet-name normalization should be fixed in shared deserialization, with Astro Clock and auxiliary evaluation retested together
5. identify any additional Astro Clock/internal consumers that should move from the wrapper helpers onto the new bundle helpers when they need a live chart object
6. if desired, build a larger real-chart property corpus so more property verdicts can be pinned end-to-end instead of only at doctrine-helper level

## Doctrine Pass Record

Completed in practical order:

1. Extracted Lilly property doctrine and used Bonatti/Sahl only where the accessible text supported the split.
2. Split property questions into `acquisition`, `advisability_profit`, and `condition` families.
3. Audited significators and kept `L2` secondary rather than promoting it to co-primary.
4. Defined a category-local no-perfection property-advisability assessment using `L10` for profit and `L4` for property/end.
5. Built a property-only validation corpus with deterministic `YES`, deterministic `NO`, and manual-review coverage.
6. Kept all logic changes local to property routing, rules, and finalization, then reran horary and Astro Clock regressions.

## Current Recommendation

Do **not** make broader shared horary verdict changes beyond the category-local property doctrine pass now in source.

The present evidence supports:

- keeping the current core horary judgment logic unchanged
- fixing the export path that fed incomplete data to external reviewers
- keeping the property change local to the property family classifier / property rules / property quality helper
- continuing a second pass on shared auxiliary scoring only after the doctrine extraction is more complete

## Root-Fix Slice Implemented

Two further doctrine-backed root fixes are now in source.

### 1. Reciprocal-affection relationship questions

Problem:

- the engine treated `Will X and I like one another romantically?` as a generic occurrence question
- a direct applying aspect plus one-way reception could therefore produce an affirmative verdict
- that logic was too crude for a mutual-liking question

Fix:

- relationship questions now carry a local doctrine split between:
  - `affection`
  - `outcome`
- affection questions are classified as `QUALITY`
- a new relationship doctrine helper judges reciprocal affection by reception before bare contact
- one-way reception is no longer treated as enough to prove that both parties like one another

Source check used:

- Lilly Book I: the 7th covers love questions and the person inquired after
- Lilly Book II: mutual reception is what shows the parties "still love one another"

Result:

- `x_romantically_article_spec` now replays `NO`

### 2. Third-person death routing

Problem:

- explicit death questions could be typed as health because `die` matched the health bucket too early
- when a later category override forced `death`, the stale health houses/significators could still remain in place
- this produced false positives such as the Pope chart replay using the wrong operative house pair

Fix:

- explicit death-event language now outranks generic health matching
- titled third-party subjects can infer a subject house:
  - clergy / religious men -> 9th
  - rulers / authorities -> 10th
- third-person death questions now use:
  - subject house as operative ascendant
  - turned 8th from that subject as the death house

Source check used:

- Lilly Book I: the 9th signifies clergy and religious men
- Lilly Book I: in turned-house work, the house signifying the party becomes that party's ascendant
- Lilly Book II: death should not be pronounced rashly on a single testimony

Result:

- `pope_die_article_spec` now replays `NO`
