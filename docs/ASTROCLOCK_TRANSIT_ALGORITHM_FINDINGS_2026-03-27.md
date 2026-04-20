# Astro Clock Transit Algorithm Findings
## 2026-03-27

This note records the transit-stack issues found while replaying the war/crisis slices and the fixes applied in source.

### Scope

- Backend transit engine: [backend/transits_morin.py](C:/Users/sabaa/Downloads/codexhorary/backend/transits_morin.py)
- Backend Astro Clock transit routes: [backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)
- Frontend transit modal: [frontend/src/features/astroclock/TransitsModal.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/TransitsModal.jsx)
- Replay coverage:
  - [tests/test_transit_war_response_replay_slice_9.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_war_response_replay_slice_9.py)
  - [tests/test_transit_recent_war_replay_slice_10.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_recent_war_replay_slice_10.py)
  - [backend/test_transits_quality.py](C:/Users/sabaa/Downloads/codexhorary/backend/test_transits_quality.py)
  - [frontend/src/tests/transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)

## Source Basis

Primary doctrinal basis:
- `C:\Users\sabaa\Desktop\astrolgy books\jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl_compress.pdf`

Relevant extracted points:
- Page 78 states that future effects from directions, revolutions, and transits must be judged from the planet's explicit partial determinations.
- Page 78-79 treats the houses as divided into multiple subtypes, not a single simplistic meaning.
- Page 78 explicitly says the 7th is the house of matrimony, contracts, lawsuits, and open enemies.
- Page 80 says the significator must be looked at first for the type of accident, then the promittor, and only after that should the quality/effect be judged.

Local design references already in the repo:
- [backend/morin_transit_engine_specification(1).md](C:/Users/sabaa/Downloads/codexhorary/backend/morin_transit_engine_specification(1).md)
- [backend/morin_transit_quality_determination(2).md](C:/Users/sabaa/Downloads/codexhorary/backend/morin_transit_quality_determination(2).md)

These local specs already state the same two principles:
- radical determination is primary
- target significance and concordance must shape the final event reading

## Findings

### 1. Relationship context was being collapsed into marriage too early

Observed symptoms:
- war rows hitting `C7` could come back as `relationships` or `marriage`, even when the same row already carried `attack_violence` and `conflict`
- generic 7th-house wedding control rows were being promoted into direct `marriage` results even when the chart only supported a broader relationship context

Why this was wrong:
- Morin does not reduce the 7th to marriage alone.
- For war/crisis/public-conflict charts, `C7` can legitimately mean open enemies and conflict.
- For relationship charts, generic partnership/contact testimony should not be normalized into marriage before stronger marriage determination exists.

Fix:
- added contextual house-domain expansion for mixed houses
- 7th now remains eligible for `relationships`, `marriage`, and `conflict`
- 12th now remains eligible for `secrets`, `hidden_enemies`, and `prison`
- contextual domain selection now uses the row's event tokens and enriched keywords before choosing the final domain
- `Relationship` is now normalized to `relationships`, not `marriage`
- domain synonym expansion no longer auto-promotes `relationships` into `marriage`
- life-area selection no longer rewrites generic `relationship` domains into `marriage`

Files:
- [backend/transits_morin.py](C:/Users/sabaa/Downloads/codexhorary/backend/transits_morin.py)
- [frontend/backend/transits_morin.py](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/transits_morin.py)

### 2. Prediction ranking and peak extraction were too score-first

Observed symptom:
- generic benefic public/honors rows could outrank a more relevant crisis row simply because the generic row had a higher raw score.

Why this was a real algorithm issue:
- Morin's method is not "highest raw score wins."
- determination and target relevance have to shape the ranking, especially when the system is deciding what event family a row belongs to.

Final fix kept after replay validation:
- explicit event rows rank ahead of generic rows with no `event_type`
- prediction ranking still keeps score and probability primary
- domain alignment and radical determination are now secondary tie-breakers, not the main sort order
- predictor/window/stream peak extraction still uses the narrower rule so replay-safe honor and marriage slices do not regress
- flat plateaus now choose the local highest-count row inside each plateau instead of an arbitrary midpoint representative

Additional predictor fix applied afterward:
- `/api/astro-clock/predictor` no longer reuses the generic peak extractor
- predictor peaks now use a dedicated plateau selector that chooses the strongest event-family row inside each flat plateau
- predictor peak payloads now expose additive metadata (`event_type`, `life_area`, `description`, `transit`, `support_score`, `keyword_tokens`) so the frontend can render what the peak actually represents

Why this narrower version was kept:
- a stronger determination-first reranker was tested
- it helped the war seam a little, but it knocked previously replay-safe honor and marriage slices off their expected event rows
- that broader rerank was therefore not kept as a production change

Files:
- [backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)
- [frontend/backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/astro_clock_api.py)

### 3. The transit scan preview in the frontend was bypassing the corrected backend row predictions

Observed symptom:
- the scan table was summarizing predictions only from `topHits`
- this could visually reintroduce generic labels even when the backend row already had a better `row.predictions` list

Why this mattered:
- it made the UI look less correct than the backend actually was
- it hid the corrected `conflict` reading on war rows

Fix:
- the scan table now summarizes from `row.predictions` first
- it falls back to `topHits` only if needed
- it also renders critical chips separately when a row carries crisis signals

File:
- [frontend/src/features/astroclock/TransitsModal.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/TransitsModal.jsx)

## What Was Fixed In Practice

After the fix, the replay-safe Israel war row:
- retains `eventType = attack_violence`
- resolves `lifeArea = conflict`
- no longer degrades into `relationships` merely because the target is `C7`

After the relationship-domain normalization fix, the replay-safe Charles wedding controls also changed shape:
- the event date now holds a cleaner marriage cluster than the pre-event controls
- the corrected single-route marriage-cluster scores are `81.0` on the event date vs `27.0` and `0.0` on the earlier controls
- this is still bounded wedding support, not justification for predictor/stream promotion

This is covered in:
- [tests/test_transit_recent_war_replay_slice_10.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_recent_war_replay_slice_10.py)
- [tests/test_transit_war_response_replay_slice_9.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_war_response_replay_slice_9.py)
- [backend/test_transits_quality.py](C:/Users/sabaa/Downloads/codexhorary/backend/test_transits_quality.py)
- [frontend/src/tests/transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)

## Important Limitation

Not every positive-looking top prediction on a national crisis chart is a bug.

Even after the domain fix, some national war charts still rank benefic/honors rows above the crisis row because:
- the crisis row can remain weakly determined
- concordance can remain weak
- the raw crisis row can still be lower-confidence than the strongest public/honors row

That remaining behavior is consistent with the repo's Morin weighting and is not being patched away here.

So the corrected claim is:
- there was a real domain-selection bug
- there was a real ranking/selection seam
- there was a real frontend render bypass
- but a crisis row not becoming the number-one overall prediction is not automatically a defect

## Later follow-up: additive row-localization scoring

The scan/window/predictor/stream stack now carries an additive row-localization score derived from the strongest per-row prediction support instead of leaving row ranking as raw transit-density only.

Current behavior:
- raw transit activity is preserved as `raw_step_score`
- determined row support is computed as `localization_score`
- effective row ranking uses `step_score = raw_step_score + localization_score`
- stream peaks now use the same predictor-aware plateau builder as window/predictor

This is an additive ranking fix, not a case-specific patch. It is meant to keep exact-time, scan, predictor, and stream closer together when a row has stronger determined support than neighboring generic rows.

## Later follow-up: exact-time critical-summary coherence

Observed symptom during live UI audit:
- a single exact timestamp could show `attack/violence`, `major accident`, `natural death`, and similar unrelated crisis chips together in the same `Critical Signals` block
- this made the card look less determined than the underlying row actually was

Why this was wrong:
- Morin's determination logic is not well represented by dumping every crisis-family token that happens to coexist at one timestamp
- the summary layer should present one coherent crisis family for the row, not a grab-bag of all crisis-adjacent tokens

Fix:
- the frontend now classifies crisis tokens into families (`conflict`, `prison`, `death`, `accident`)
- row-level exact summaries now choose the dominant crisis family using:
  - family-specific area support
  - family priority
  - explicit prediction support
  - total crisis score
- only the dominant family's chips and descriptions are shown in the exact-time summary

Effect:
- war/open-enemy rows now stay visually centered on conflict-family chips
- accident and death chips no longer spill into the same exact-time summary unless they belong to the dominant family

Files:
- [frontend/src/features/astroclock/TransitsModal.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/TransitsModal.jsx)
- [frontend/src/tests/transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)
