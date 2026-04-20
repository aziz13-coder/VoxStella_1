# Astro Clock Trait Profile Catalog Quality Audit

Date: 2026-03-30

## Scope

This pass moved past workflow and score normalization into catalog quality:

- dormant or ultra-thin entries
- duplicate rule families
- how duplicate families affect `top_traits` and the trait modal summary

## Findings

### 1. A small dormant tail exists in the catalog

Three traits currently have no effective positive support logic:

- `baldness_risk`
- `knock_knees`
- `lameness_gait`

These remain inert because their attainable positive support is `0`. They do not currently surface in normal output, so they are catalog-completeness debt rather than an active runtime bug.

### 2. There is a larger ultra-thin tail

A number of traits are still single-trigger or very low-support entries, for example:

- `goitre_thyroid`
- `influenza`
- `death_retreat_theme`
- `quick_adaptability`
- `changeability`
- `compassion_universalism`

These are not necessarily wrong, but they require careful band handling. The previous scoring pass already addressed the worst problem by normalizing score and requiring corroboration before `strong`.

### 3. Duplicate families were crowding the summary layer

The larger active issue was duplicate logic families.

Representative examples from the catalog:

- fixed/Saturn cluster:
  - `conservatism`
  - `fixed_reserve_possession`
  - `narrowness_rigidity`
  - `obstinacy`
  - `quiescence`
  - `quietness`
  - `stubbornness`

- mutable quickness/instability cluster:
  - `changeability`
  - `cowardice`
  - `indecision_mutable`
  - `quick_adaptability`

- Aries/Mars confrontation cluster:
  - `outgoingness`
  - `pugnacity`
  - `self_assertion`
  - `warlike`

Live engine sampling showed the practical problem clearly:

- one fixed/Saturn-style chart produced `narrowness_rigidity`, `obstinacy`, `quiescence`, `quietness`, and `stubbornness` all as top results
- one Aries/Mars-style chart produced `pugnacity`, `self_assertion`, and `warlike` together at full activation

That is not added interpretive value. It is multiple labels for the same underlying rule family.

## Fix Implemented

### Family collapse for summary surfaces

Implemented in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`
- `frontend/src/features/astroclock/TraitProfileModal.jsx`

The engine now computes a stable `family_key` from the normalized trait logic and groups identical logic families at the summary level.

Current behavior:

- `traits` still returns the full indicated list for inspection
- `top_traits` now uses one representative per identical logic family
- each trait now carries:
  - `family_key`
  - `family_size`
  - `family_representative`
  - `related_traits` for the representative item

This keeps the catalog intact while preventing the summary layer from pretending identical-rule synonyms are separate top findings.

### Frontend summary alignment

The trait modal now uses family representatives for the positive/neutral/negative summary split instead of the raw full list. It also shows when a summary trait stands in for related variants.

Practical result:

- the top summary is more diverse
- the full trait list still preserves the underlying catalog detail

## What Was Intentionally Not Changed

- dormant placeholder traits were not deleted
- near-duplicates with genuinely different rule logic were not merged
- the full `traits` list was not deduplicated, because inspection value still exists there

This pass only collapses **identical logic families** in the summary layer.

## Tests Added

Backend:

- duplicate-family representative selection in `backend/test_trait_engine_contract.py`

Frontend:

- neutral summary plus related-variant rendering in `frontend/src/tests/traitProfileModal.test.jsx`

## Current Assessment

After the scoring pass and this catalog-quality pass:

- trait scores are now comparable across the catalog
- strong labels require corroboration
- neutral traits are visible
- summary surfaces no longer get crowded by identical-rule duplicates

The next worthwhile pass, if needed, is catalog curation rather than engine mechanics:

- fill or retire dormant placeholder traits
- review ultra-thin single-trigger medical/pathology entries
- decide whether some near-duplicate but not identical families should be merged editorially
