# Trait Profile Corpus Exploration

Date: 2026-04-04

## Executive Summary

The Trait Profile feature is structurally ready for source enrichment. Its backend route already assembles chart context, metrics, house influence, sect, summary traits, top traits by polarity, keywords, evidence, and guidance. The current weakness is not workflow shape, but source breadth: the trait catalog is still dominated by Carter-derived entries, while the Morin layer is compact and explicitly non-scoring.

The new inspection corpus under `extracted_text_docs/new_sources_inspection/` is best used first for:

1. source-backed citations,
2. broader source lineage,
3. richer non-scoring keyword and guidance enrichment,
4. trait-authoring support.

It should not be merged directly into the existing Morin keyword file without separation, or the Morin-facing layer will become conceptually dirty.

## Current Workflow Map

### Frontend

- `frontend/src/features/astroclock/api.mjs:713`
  - `getTraitProfile(opts={})`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:24`
  - modal entry point
- `frontend/src/features/astroclock/TraitProfileModal.jsx:59`
  - fetches trait profile from the backend
- `frontend/src/features/astroclock/TraitProfileModal.jsx:493`
  - consumes `summary_traits`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:495`
  - consumes `top_traits_by_polarity`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:1518`
  - uses `source_lineage`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:1567`
  - renders backend trait `keywords`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:1579`
  - renders backend trait `evidence`

### Backend

- `backend/astro_clock_api.py:3317`
  - route `GET /api/astro-clock/traits/profile`
- `backend/astro_clock_api.py:3335`
  - builds dashboard payload
- `backend/astro_clock_api.py:3345`
  - computes metrics
- `backend/astro_clock_api.py:3350`
  - computes house influence
- `backend/astro_clock_api.py:3356`
  - computes sect
- `backend/astro_clock_api.py:3410`
  - imports `TraitEngine`
- `backend/astro_clock_api.py:3411`
  - evaluates trait profile

### Trait Engine

- `backend/traits/engine.py:437`
  - `class TraitEngine`
- `backend/traits/engine.py:950`
  - `evaluate(...)`
- `backend/traits/engine.py:1218`
  - `compute_guidance(...)`
- `backend/traits/engine.py:1313`
  - `_load_morin_keywords_safe()`
- `backend/traits/engine.py:1347`
  - `_derive_trait_keywords(...)`

## Source Findings

### Trait Catalog

The trait catalog in `backend/traits/catalog/` is overwhelmingly Carter-derived.

Observed source census:

- 331 total trait JSON files
- 329 include Carter in `sources`
- 2 are non-Carter edge cases

Representative sample:

- `backend/traits/catalog/A/ability.json`
- `backend/traits/catalog/A/abruptness.json`
- `backend/traits/catalog/A/absentmindedness.json`

Each sampled file contains simple fields such as `id`, `name`, `description`, `domain`, `logic`, `confidence`, and `sources`, with `sources` often just `["Carter"]`.

### Morin Layer

The Morin keyword map is intentionally narrow:

- `backend/traits/knowledge/morin_keywords.json:7`
  - states it is an "Operational non-scoring keyword map"
- `backend/traits/knowledge/morin_keywords.json:9`
  - house keywords
- `backend/traits/knowledge/morin_keywords.json:71`
  - planet keywords
- `backend/traits/knowledge/morin_keywords.json:101`
  - sect hints

The current note is important:

> House keywords are kept tightly Morin-facing. Planet and sect keywords are compact classical/Morin-facing tags used for enrichment, not for scoring.

### Keyword Path

The keyword path is currently light-touch:

- `backend/traits/engine.py:1271`
  - Morin guidance additions are explicitly "non-replacing"
- `backend/traits/engine.py:1312`
  - section header says "Morin keywords helpers (non-scoring)"
- `backend/traits/engine.py:1347`
  - `_derive_trait_keywords(...)` parses evidence strings, infers top planet and area, then adds house and planet tags from the Morin dictionary

This means the current Morin layer functions as a compact enrichment vocabulary, not as the trait engine's main scoring doctrine.

## New Corpus Fit

The new corpus lives under:

- `extracted_text_docs/new_sources_inspection/README.md`
- `extracted_text_docs/new_sources_inspection/catalog.json`
- `extracted_text_docs/new_sources_inspection/chunk_index.jsonl`

Books currently available:

1. Demetra George
2. Compendium of Astrology
3. Dane Rudhyar

This corpus is useful because it is already normalized and chunked for retrieval, so it can support:

1. citation lookup,
2. trait-authoring support,
3. source-lineage diversification,
4. guidance enrichment,
5. domain vocabulary expansion.

## Improvement Ideas

### Safe, High-Value Improvements

1. Add `citations` to returned trait objects.
   - Keep current scoring.
   - Add 1-3 retrieved corpus snippets per visible top trait.

2. Add parallel source packs.
   - Keep Morin keywords canonical.
   - Add separate retrieval packs for:
     - `classical`
     - `modern`
     - `textbook`

3. Expand guidance from the corpus.
   - Use the new corpus to improve `compute_guidance(...)` output without changing trait score math.

4. Use the corpus for trait curation.
   - When revising catalog entries, attach corpus chunk references to the trait's doctrinal basis.

### Higher-Risk Improvements

1. Rewriting trait scoring directly from corpus retrieval.
2. Merging modern psychological language into Morin keyword storage.
3. Treating all chunk hits as equally authoritative.

These would blur source lineage and make it hard to tell whether a trait is Carter-derived, Morin-facing, generic classical, or modern psychological.

## Morin Purity Question

Question: if we improve point 3, will that preserve a true Morin-style process, or will the keywords become dirty?

Answer: it depends entirely on where the new corpus is wired.

### If We Expand `morin_keywords.json` Directly

Then yes, we risk making the Morin layer dirty.

Reasons:

1. The current file is intentionally compact and Morin-facing.
2. The new corpus includes non-Morin material, especially Rudhyar.
3. Once mixed into the same file, the UI and engine can no longer distinguish:
   - actual Morin-facing house determination tags,
   - general classical vocabulary,
   - modern psychological phrasing.

That would weaken doctrinal clarity.

### If We Keep Morin Canonical and Layer New Retrieval Beside It

Then no, we do not need to dirty the Morin process.

Recommended model:

1. Keep `backend/traits/knowledge/morin_keywords.json` narrow and canonical.
2. Add a separate file or retrieval layer for corpus-derived expansions, such as:
   - `backend/traits/knowledge/classical_trait_keywords.json`
   - `backend/traits/knowledge/modern_trait_keywords.json`
   - `backend/traits/knowledge/trait_citations_index.json`
3. Return source-aware payload fields like:
   - `keywords_morin`
   - `keywords_classical`
   - `keywords_modern`
   - `citations`
4. Let the UI label the provenance clearly.

This preserves Morin purity while still enriching the feature.

## Recommendation

Do not use the new corpus to enlarge `morin_keywords.json` directly.

Instead:

1. freeze the existing Morin keyword file as canonical,
2. add a parallel retrieval-backed evidence layer,
3. expose source-specific keywords separately,
4. only promote new terms into the Morin layer if they are explicitly verified as Morin-compatible and documented as such.

That keeps the Morin process clean and lets the new corpus improve the feature without collapsing doctrinal boundaries.

## Practical Next Step

The safest next implementation slice is:

1. add a backend retrieval helper over `chunk_index.jsonl`,
2. attach `citations` to top traits,
3. keep those citations source-labeled,
4. leave `morin_keywords.json` unchanged for now.
