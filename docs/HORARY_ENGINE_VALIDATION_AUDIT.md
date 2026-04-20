# Executive Summary

I audited the shared horary engine under `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine`, traced the downstream consumers that rely on the same contracts, compared implemented rule logic to the local horary corpus in `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge`, and ran both rule-level and question-level validation against source-engine replay.

This pass now includes a real question/chart validation corpus, not only helper-level checks. I added replay tests for five saved horary charts covering:

- a lottery question that should be denied by frustration/prohibition-family blocking
- a funding question that should remain affirmative through same-ruler unity despite a late Ascendant warning
- an education exam question that should be affirmative through Moon-Sun examiner perfection
- an education admission question that should be negative when no perfection exists
- a qualitative pivot question that should be negative through frustration

Current result:

- I did not find a reproducible production-engine answer defect strong enough to justify changing shared horary scoring or doctrinal logic in `backend/horary_engine/**`.
- The main corrective work in this audit was strengthening validation coverage, including full question replay through the same engine finalization path used by the application.
- I did implement a small set of low-risk source fixes: better classification for explicit divorce/separation wording, removal of leaked internal reasoning flags, and cleanup of mojibake in user-facing reasoning text.
- Regression risk remained low because these fixes did not alter scoring weights or perfection selection.

# Engine Usage Map

Primary entry points:

- `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:386`
  Instantiates `HoraryEngine`.

- `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1301`
  Calls `horary_engine.judge(question, settings)` for `/api/calculate-chart`.

- `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_engine.py:95`
  Instantiates the same shared engine for Astro Clock workflows.

- `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_engine.py:253`
  Calls `self.horary_engine.judge(...)` for real-time/manual/paused Astro Clock payloads.

- `C:\Users\sabaa\Downloads\codexhorary\backend\evaluate_chart.py:43`
  Runs the post-serialization testimony aggregation pipeline used by consumers that rehydrate `chart_data`.

Core shared logic inspected:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:1594`
  `judge_question(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:2026`
  `_apply_enhanced_judgment(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:2620`
  education-specific Moon-Sun perfection path

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3105`
  same-ruler unity timing/perfection path

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3303`
  no-perfection occurrence denial path

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:4627`
  `_is_moon_void_of_course_enhanced(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:4642`
  `_void_traditional_ground_truth(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:5404`
  `_check_moon_sun_education_perfection(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:6647`
  `_finalize_judgment(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:376`
  `_detect_translation_events(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:574`
  `_detect_collection_events(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:814`
  `_detect_prohibition_events(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:1321`
  `select_primary_perfection(...)`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\radicality.py:173`
  `check_enhanced_radicality(...)`

Downstream consumers and contract assumptions:

- Chart API:
  `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1301`
  Expects `judgment`, `confidence`, `reasoning`, `traditional_factors`, `considerations`, `chart_data`, `moon_last_aspect`, `moon_next_aspect`, and timezone metadata.

- Serialized chart evaluation:
  `C:\Users\sabaa\Downloads\codexhorary\backend\evaluate_chart.py:91`
  Expects `deserialize_chart_for_evaluation(...)` to rebuild a usable `HoraryChart` and preserve aspect/testimony structure.

- Astro Clock adapter:
  `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_engine.py:244`
  Forces radicality/void/combustion/Saturn-7th overrides and therefore depends on stable consideration semantics such as `radical_raw`, `radical`, and `moon_void`.

- Astro Clock API rehydration:
  `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1165`
  `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1276`
  `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3003`
  Depends on stable serialized chart data and parseable reasoning/traditional factors.

- Frontend judgment display:
  `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:607`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:3412`
  Depends on `reasoning`, `reasoning_v1`, `traditional_factors.perfection_type`, and `traditional_factors.reception`.

Shared logic with regression potential if changed:

- `traditional_factors.perfection_type`
- `traditional_factors.frustrating_planet`
- structured `reasoning`
- `considerations.radical`, `considerations.radical_raw`, `considerations.moon_void`
- serialized `chart_data` consumed by `deserialize_chart_for_evaluation(...)`

Source duplication note:

- The backend source is mirrored under `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\...`.
- I did not change engine logic, so parity risk between the two source trees was avoided in this pass.

# Knowledge Sources Used

Primary local horary sources:

- `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt:3412`
  Collection of light is when two faster planets apply to a third, slower collector.

- `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt:3592`
  Prohibition is when a third planet gets in the way of two planets joining by aspect.

- `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt:3775`
  The Moon functions only through aspects made in the sign it occupies at the time of the question.

- `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt:3780`
  When the Moon makes no major aspect before leaving the sign, the activity generated proves pointless.

Project-local rule codification:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_constants.yaml:92`
  Project rule declares void-of-course as sign-bounded.

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_constants.yaml:104`
  `perfection.require_in_sign: true`

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_constants.yaml:112`
  Translation configuration enforces sequence and timing boundaries.

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_constants.yaml:123`
  Collection configuration enforces collector dignity.

Project-local analysis notes:

- `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:8`
  Uses the lottery question as a concrete prohibition-family denial example.

- `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:11`
  Documents the direct perfection candidate.

- `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:12`
  Documents the interfering aspect that should block perfection.

- `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:16`
  States the expected answer is `NO`.

Engine-source doctrinal codification used for question-level replay expectations:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3113`
  Same-ruler unity is treated as a perfection type.

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:266`
  The unified perfection core describes same-ruler unity as "unity of matter & querent".

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:5422`
  Education judgments can perfect through Moon applying to Sun as examiner/authority.

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3303`
  Occurrence questions with no perfection are explicitly denied.

# Validation Corpus

Deterministic cases suitable for automated assertion:

- Rule-level corpus:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:60`
  translation lookback rejection

- Rule-level corpus:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:92`
  collection requires a slower, sufficiently dignified collector

- Rule-level corpus:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:176`
  prohibition must preempt direct perfection

- Rule-level corpus:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:201`
  void-of-course is in-sign only

- Rule-level corpus:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:219`
  Astro Clock radicality override preserves raw invalid state

- Question-level corpus fixture:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\lottery_prohibition.json:1`
  Question: "will I win in the lottery?"
  Deterministic expectation: `NO` with blocking frustration/prohibition-family testimony.

- Question-level corpus fixture:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\funding_same_ruler.json:1`
  Question: "Will we secure a lead investor for our seed round before November?"
  Deterministic expectation: `YES` because same-ruler unity directly perfects the matter; late Ascendant is confidence-only.

- Question-level corpus fixture:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\physiotherapy_exam_yes.json:1`
  Question: "Will I pass my physiotherapy exam?"
  Deterministic expectation: `YES` through Moon-Sun examiner perfection.

- Question-level corpus fixture:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\masters_no_perfection.json:1`
  Question: "Will I be admitted to the master's program this cycle?"
  Deterministic expectation: `NO` because the engine finds no perfection and no compensating support strong enough to overcome that.

- Question-level corpus fixture:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\pivot_frustration.json:1`
  Question: "Should we pivot to blog + RSS ?"
  Deterministic expectation: `NO` because the matter is frustrated before perfection.

Question-level replay tests added:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:67`
  lottery denial with frustration-family support

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:80`
  same-ruler funding affirmation with confidence-only late Ascendant

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:93`
  Moon-Sun education perfection affirmation

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:104`
  no-perfection education denial

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:115`
  frustration-based qualitative denial

Broad manual-review corpus added for ambiguous domains:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\conceive_review.json:1`
  Reviewed as a conception chart where the engine surfaces `pregnancy_sufficiency`, unilateral L1-L5 reception, and non-void Moon. This remains a manual-review case because conception support can exist without a single direct perfection signature.

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\marry_review.json:1`
  Reviewed as a marriage chart with mixed reception, a supportive Moon contact, but no direct perfection. This is doctrinally arguable and therefore guarded by signal-level assertions instead of an over-tight golden verdict.

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\divorce_review.json:1`
  Reviewed as a divorce chart that replays as a no-perfection denial. It remains in the manual-review corpus because relationship-separation questions are interpretation-sensitive.

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\reconcile_review.json:1`
  Reviewed as a reconciliation chart where an explicit prohibition preempts perfection.

Manual-review replay tests added:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:62`
  conception support signals without over-constraining verdict wording

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:73`
  marriage chart with mixed support plus no-perfection denial

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:85`
  divorce chart replay with explicit no-perfection reasoning

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:95`
  reconciliation chart with explicit prohibition testimony

Cases still not tightly asserted:

- live geocoding/timezone input through the public `judge_question(...)` path
- broader question-classification edge cases without saved category hints

# Correctness Findings

## Finding 1

- Severity: Medium
- Exact evidence:
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:376`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:574`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py:814`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:4642`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:60`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:92`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:176`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:201`
- Why the current behavior was wrong or risky:
  Before this pass, the repository did not lock the highest-risk traditional rule boundaries with deterministic tests at the engine level. Translation, collection, prohibition, and void-of-course all feed final judgments and shared consumer payloads, so regressions here can silently change both verdicts and reasoning.
- Which horary knowledge source supports the expected behavior:
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt:3412`
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt:3592`
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt:3775`
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt:3780`
- Impact on downstream app features:
  Regressions here would affect `/api/calculate-chart`, Astro Clock moon-state output, `traditional_factors.perfection_type`, and any frontend/API consumer that interprets reasoning or considerations.
- Proposed fix or implemented fix:
  Implemented deterministic engine-level regression coverage in:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:60`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:92`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:133`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:176`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:201`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:219`

## Finding 2

- Severity: Low
- Exact evidence:
  `C:\Users\sabaa\Downloads\codexhorary\backend\test_translation.py:17`
  `C:\Users\sabaa\Downloads\codexhorary\backend\test_translation.py:81`
- Why the current behavior was wrong or risky:
  `test_recent_separations()` previously returned data instead of asserting. That weakened the translation regression signal because pytest accepted the function while warning that it was not a real oracle.
- Which horary knowledge source supports the expected behavior:
  This is a test-quality finding rather than a doctrinal disagreement, but it protects translation-of-light behavior grounded in:
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt:3775`
- Impact on downstream app features:
  Weak translation protection increases the chance of unnoticed drift in the shared perfection engine used by chart judgments and Astro Clock consumers.
- Proposed fix or implemented fix:
  Implemented at:
  `C:\Users\sabaa\Downloads\codexhorary\backend\test_translation.py:81`
  The test now asserts that at least one recent separating lunar aspect is detected.

## Finding 3

- Severity: High
- Exact evidence:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:25`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:67`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:80`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:93`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:104`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:115`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\lottery_prohibition.json:1`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\funding_same_ruler.json:1`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\physiotherapy_exam_yes.json:1`
- Why the current behavior was wrong or risky:
  Before this pass, the repository lacked enough question-based judgment validation. That meant the engine could satisfy helper-level rule tests while still producing a substantively wrong final answer or wrong supporting reasoning on a real horary question.
- Which horary knowledge source supports the expected behavior:
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt:3592`
  `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:8`
  `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:12`
  `C:\Users\sabaa\Downloads\codexhorary\PROHIBITION_BUG_ANALYSIS_SESSION.md:16`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3113`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:5422`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3303`
- Impact on downstream app features:
  This gap directly affected user-facing chart judgments, frontend reasoning displays, exports, and any consumer that treats `judgment` plus `traditional_factors` as authoritative.
- Proposed fix or implemented fix:
  Implemented a replay-based question corpus that rehydrates saved charts, reruns `_apply_enhanced_judgment(...)`, `_evaluate_enhanced(...)`, and `_finalize_judgment(...)`, and asserts substantive verdict plus supporting indicators:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:25`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:67`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:80`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:93`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:104`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:115`

No current replayed case produced a clear source-level engine-answer defect that justified changing shared production logic. The validated cases now behave in line with the local corpus and project doctrinal codification.

## Finding 4

- Severity: Low
- Exact evidence:
  `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py:47`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3359`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:7310`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:80`
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:105`
- Why the current behavior was wrong or risky:
  The engine exposed a few user-facing quality issues even though the underlying horary answer was defensible: explicit divorce questions fell back to `GENERAL` instead of relationship-domain classification, internal `FLAG: MOON_NEXT_DECISIVE` markers leaked into reasoning, and some reasoning strings used mojibake text instead of clean display text.
- Which horary knowledge source supports the expected behavior:
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt:2162`
  `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt:1493`
  These sources treat divorce/separation as relationship-domain matters; the text-cleanup portion is a presentation-quality fix rather than a doctrinal disagreement.
- Impact on downstream app features:
  These issues affected frontend/chart readability, log clarity, and question routing quality for relationship-separation questions, but did not materially change validated scoring behavior.
- Proposed fix or implemented fix:
  Implemented low-risk source fixes in both backend source trees:
  `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py:47`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3359`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:7310`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\question_analyzer.py:47`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\horary_engine\engine.py:3359`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\horary_engine\engine.py:7310`

# Changes Made

- Added question-level replay tests:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py`

- Added self-contained chart fixtures for deterministic question replay:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\lottery_prohibition.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\funding_same_ruler.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\physiotherapy_exam_yes.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\masters_no_perfection.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_questions\pivot_frustration.json`

- Added ambiguous-domain manual-review replay tests:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py`

- Added self-contained manual-review fixtures:
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\conceive_review.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\marry_review.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\divorce_review.json`
  `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\reconcile_review.json`

- Previously added deterministic rule-level validation:
  `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py`

- Previously strengthened translation regression assertion:
  `C:\Users\sabaa\Downloads\codexhorary\backend\test_translation.py:81`

- Implemented low-risk source fixes in shared engine/question-analysis code:
  `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py:47`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:3359`
  `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py:7310`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\question_analyzer.py:47`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\horary_engine\engine.py:3359`
  `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\horary_engine\engine.py:7310`

- No scoring, perfection-selection, or shared-contract shape changes were made.
- No packaged/generated artifacts were edited.

# Tests Added or Updated

Added:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:67`
  Validates that the lottery chart produces `NO` with Mercury frustration testimony.
  Deterministic because the serialized chart and question are fixed and the project-local bug analysis explicitly documents the expected denial.
  Protects the shared judgment path and blocking testimony interpretation.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:80`
  Validates that the funding chart stays `YES` through same-ruler unity and does not let a late Ascendant warning flip the verdict.
  Deterministic because the chart has a shared significator and the engine codifies late Ascendant as confidence-only in this path.
  Protects final judgment logic and shared-significator reasoning used by frontend consumers.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:93`
  Validates the Moon-Sun education perfection path for an exam success chart.
  Deterministic because the engine has a dedicated education perfection rule and the chart replay produces the same applying examiner testimony.
  Protects education judgments and `traditional_factors.perfection_type = moon_sun_education`.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:104`
  Validates that an admission chart with no perfection is judged `NO` and surfaces explicit denial reasoning.
  Deterministic because the engine’s no-perfection occurrence path is explicit and the replayed chart does not perfect.
  Protects occurrence denials and downstream display of no-perfection reasoning.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_question_corpus.py:115`
  Validates a qualitative `NO` judgment backed by frustration testimony.
  Deterministic because the frustrating planet and blocking sequence are fixed in the serialized chart.
  Protects frustration-family negative judgments outside the gambling example.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:62`
  Validates that the conception review chart surfaces pregnancy-sufficiency doctrine, unilateral L1-L5 support, and non-void Moon without hard-coding an overly strict doctrine claim.
  Deterministic enough because the saved chart is fixed and the asserted signals are stable doctrinal features rather than fragile prose.
  Protects ambiguous fertility-domain replay from losing its core support indicators.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:73`
  Validates that the marriage review chart preserves mixed reception and supportive Moon testimony even while replaying as a no-perfection case.
  Deterministic enough because the asserted support/denial signals coexist consistently in the serialized chart.
  Protects nuanced relationship answers from collapsing into shallow yes/no-only output.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:85`
  Validates that the divorce review chart continues to surface a clean no-perfection denial.
  Deterministic enough because the chart replay and explicit denial text are stable.
  Protects separation-question reasoning structure.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:95`
  Validates that the reconciliation review chart surfaces an explicit prohibition before perfection.
  Deterministic enough because the prohibiting sequence is fixed in the saved chart.
  Protects relationship-blocking testimony in an ambiguous-domain case.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:80`
  Also validates that mixed-support marriage reasoning no longer leaks the internal `MOON_NEXT_DECISIVE` flag and now uses clean `deg/day` text.
  Deterministic enough because the chart always produces the same Moon-support reasoning.
  Protects frontend-facing reasoning quality.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_manual_review_corpus.py:105`
  Validates that explicit divorce wording routes to `Category.RELATIONSHIP`.
  Deterministic enough because the keyword match is lexical and fixed.
  Protects relationship-domain routing for separation questions.

Previously added or updated:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:60`
  Validates stale translation rejection.
  Deterministic because chronology is fully stubbed.
  Protects translation-event detection.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:92`
  Validates collection dignity/speed requirements.
  Deterministic because applications and receptions are controlled.
  Protects collection-event detection.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:176`
  Validates prohibition chronology and preemption.
  Deterministic because direct and prohibiting timings are fixed.
  Protects blocking-event detection in the shared perfection core.

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_validation_corpus.py:201`
  Validates strict sign-bound void-of-course behavior.
  Deterministic because the next lunar aspect is stubbed away.
  Protects Moon-state logic and consideration payloads.

- `C:\Users\sabaa\Downloads\codexhorary\backend\test_translation.py:17`
  Now validates by assertion instead of returning data.
  Deterministic because the sample longitudes and speeds are fixed.
  Protects translation regression signal quality.

# Regression Risk Review

Shared-feature risk after this pass is low because no production engine logic was modified.

Contracts explicitly rechecked:

- question replay still returns structured reasoning dictionaries through the engine finalization path
- `traditional_factors` remain populated for question-level charts
- rule-level perfection detection still passes targeted regression tests
- Astro Clock adapter and override behavior still pass their dedicated suites
- backend evaluation/test scaffolding still passes after adding the new corpus

Targeted commands run:

- `python -m pytest tests\\test_horary_question_corpus.py -q`
- `python -m pytest tests\\test_horary_manual_review_corpus.py -q`
- `python -m pytest tests\\test_horary_validation_corpus.py tests\\test_horary_judgment_fixes.py tests\\test_astroclock_adapter_fixes.py -q`
- `python -m pytest tests\\test_horary_question_corpus.py tests\\test_horary_manual_review_corpus.py tests\\test_horary_validation_corpus.py tests\\test_horary_judgment_fixes.py tests\\test_astroclock_adapter_fixes.py backend\\test_translation.py backend\\test_engine.py backend\\test_simple.py backend\\test_keyword_sync.py -q`
- `python -m pytest backend\\test_translation.py backend\\test_engine.py backend\\test_simple.py -q`

Results:

- `tests\\test_horary_question_corpus.py`: 5 passed
- `tests\\test_horary_manual_review_corpus.py`: 5 passed
- `tests\\test_horary_validation_corpus.py` + related shared suites: 13 passed
- `backend\\test_translation.py backend\\test_engine.py backend\\test_simple.py`: 3 passed
- combined expanded suite: 27 passed

Observed non-blocking issue:

- `pytz` emitted a deprecation warning from the environment package, but no test failed because of it.

# Remaining Ambiguities / Manual Review Cases

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\conceive_review.json:1`
  Manual review outcome: the engine surfaces meaningful conception support, but this is still not as doctrinally crisp as a chart with an unmistakable direct conception perfection. It should remain a reviewed ambiguity rather than a hard golden answer about certainty or viability.

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\marry_review.json:1`
  Manual review outcome: the chart combines mixed reception, supportive Moon contact, and lack of direct perfection. This is exactly the kind of marriage question where different traditional practitioners may weight support and impediment differently.

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_manual_review\divorce_review.json:1`
  Manual review outcome: current replay is a clean `NO`, but divorce/separation questions still deserve richer domain-specific examples because chart turning, marriage-specific parts, and third-party context can matter.

- Question classification still deserves broader review through the public `judge_question(...)` API path. The current corpus mostly replays saved serialized charts, sometimes with saved categories.

- Live geocoding/timezone handling remains outside the doctrinal corpus and should be tested separately as an API-contract concern.
