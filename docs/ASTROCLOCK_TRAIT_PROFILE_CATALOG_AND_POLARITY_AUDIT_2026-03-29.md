# Astro Clock Trait Profile Catalog And Polarity Audit

Date: 2026-03-29

## Scope

This pass audited the trait-profile catalog itself rather than only the route/workflow shell:

- backend scoring in `backend/traits/engine.py`
- packaged-source twin in `frontend/backend/traits/engine.py`
- frontend trait presentation in `frontend/src/features/astroclock/TraitProfileModal.jsx`

The goal was to determine whether the trait scores, bands, and polarity handling were internally coherent and whether the UI presented those semantics honestly.

## Findings

### 1. The previous trait `score` was not truly normalized

The engine previously did:

- accumulate raw weights into `total`
- clamp `total` into `0..100`
- assign `weak/possible/likely/strong` from fixed thresholds

That looked like a percentage, but it was not comparable across the catalog because most traits had much lower total attainable support.

Catalog scan summary:

- trait count: `331`
- median attainable positive support: `24`
- 90th percentile attainable positive support: `34`
- maximum attainable positive support: `65`
- traits with attainable support under `30`: `263`
- traits with attainable support under `50`: `319`

Implication:

- most traits could never reach `possible`, `likely`, or `strong` under the old fixed thresholds even when fully activated
- the UI was rendering those raw totals as percentages, which overstated precision while understating activation

### 2. The frontend hid the neutral family entirely

The catalog uses all three polarity families:

- positive: `174`
- negative: `119`
- neutral: `38`

But the modal only allowed:

- `all`
- `positive`
- `negative`

and only rendered:

- `Top Positive`
- `Top Negative`

That buried semantically important neutral traits such as:

- `self_assertion`
- `warlike`
- `sensuality`

These are not errors in the catalog. They are mixed or descriptive tendencies and needed first-class presentation.

### 3. Strong labels needed corroboration

If a trait had only one positive condition in its rule, full activation of that one condition could look indistinguishable from a trait supported by several concordant conditions.

That is too blunt for a trait engine based on multiple astrological factors. A high normalized score still needs some corroboration before it earns the strongest band.

## Fixes Implemented

### Backend scoring

Implemented in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`

Changes:

- `score` is now normalized against each trait's own attainable positive support
- the engine now emits:
  - `raw_score`
  - `max_score`
  - `support_hits`
  - `support_total`
  - `dampener_hits`
- `strong` now requires both:
  - high normalized score
  - corroborated support
- `likely` can still be reached by a single fully activated rule, but not `strong`

Practical result:

- the trait percentage now means "how fully did this rule activate relative to its own design"
- trait scores are now comparable across short-rule and long-rule entries

### Frontend polarity handling

Implemented in:

- `frontend/src/features/astroclock/TraitProfileModal.jsx`

Changes:

- added `neutral` to the polarity filter
- changed polarity sorting to:
  - positive
  - neutral
  - negative
- replaced the two-column split with:
  - `Top Positive`
  - `Top Neutral`
  - `Top Negative`

Practical result:

- neutral traits are no longer silently dropped from the main summary surfaces

### Frontend scoring transparency

Implemented in:

- `frontend/src/features/astroclock/TraitProfileModal.jsx`

Each trait card now exposes:

- active supports: `support_hits/support_total`
- normalized score
- raw support vs attainable support: `raw_score/max_score`

This keeps the new normalized score legible instead of feeling arbitrary.

### Accessibility

While updating the polarity controls, explicit `aria-label`s were added to the filter selects:

- `Band`
- `Polarity`
- `Sort`
- `Top count`

## Tests Added Or Updated

Backend:

- `backend/test_trait_engine_contract.py`

New coverage:

- restored-source enrichment still works with normalized scoring
- non-weak `top_traits` preference still holds
- corroboration gate prevents one-trigger traits from being labeled `strong`

Frontend:

- `frontend/src/tests/traitProfileModal.test.jsx`

New coverage:

- neutral polarity option exists
- neutral traits render in the split summary
- the modal continues to load and render with the updated trait payload

## What Was Not Changed

This pass did **not** recalibrate the underlying Carter-heavy trait catalog itself.

Still true:

- the weights are curated, not source-exhaustive
- some catalog entries remain placeholders or low-information entries
- a few traits have effectively dormant rules (`max_score = 0`) and will not surface until their logic is filled in

Those are catalog completeness issues, not the same bug as the old false-normalization problem.

## Current Assessment

After this pass, the trait profile is materially more honest:

- backend scores are now comparable across traits
- the strongest bands require corroboration
- neutral traits are no longer hidden by the UI
- trait cards expose enough support context to make the scores interpretable

The next logical pass, if needed, is catalog-quality rather than scoring mechanics:

- review dormant or ultra-thin traits
- audit family duplication across adjacent traits
- tighten domain naming where the Carter-derived taxonomy is too broad
