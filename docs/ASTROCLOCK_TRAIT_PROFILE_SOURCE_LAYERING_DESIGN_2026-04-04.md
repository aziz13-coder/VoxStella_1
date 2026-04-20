# Trait Profile Source Layering Design

Date: 2026-04-04

## Goal

Add corpus-backed enrichment to the Trait Profile feature without contaminating the existing Morin-facing keyword layer.

The main design rule is:

- keep canonical Morin-facing keywords separate,
- add corpus-derived classical and modern material in parallel,
- do not let retrieval output silently replace existing Morin fields.

## Current Backend Trait Shape

The current trait object returned by `TraitEngine.evaluate(...)` includes:

- `id`
- `name`
- `domain`
- `description`
- `confidence`
- `sources`
- `source_status`
- `source_lineage`
- `source_lineage_label`
- `score`
- `raw_score`
- `max_score`
- `support_hits`
- `support_total`
- `dampener_hits`
- `band`
- `polarity`
- `evidence`
- `keywords`

Reference:

- `backend/traits/engine.py:1031`

The frontend currently expects:

- `source_lineage`
- `source_lineage_label`
- `keywords`
- `evidence`

References:

- `frontend/src/features/astroclock/TraitProfileModal.jsx:1518`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:1567`
- `frontend/src/features/astroclock/TraitProfileModal.jsx:1579`

## Compatibility Rule

For the first iteration:

1. keep `keywords` as the current Morin-facing compact tag list,
2. keep `evidence` as the current rule-hit list,
3. add new fields rather than changing existing ones.

This avoids breaking:

- the compact trait chips,
- tests in `traitProfileModal.test.jsx`,
- any AI prompt or downstream consumer already using `keywords`.

## Recommended Top-Level Response Additions

Add a top-level metadata block:

```json
{
  "trait_enrichment_meta": {
    "morin_keywords_policy": "canonical_non_scoring",
    "corpus_enrichment_policy": "parallel_non_scoring",
    "corpus_index_path": "extracted_text_docs/new_sources_inspection/chunk_index.jsonl",
    "enabled_layers": ["morin", "classical", "modern", "textbook"],
    "citation_limit_per_trait": 3,
    "version": 1
  }
}
```

Purpose:

- tells the UI and audits what policy is active,
- makes it explicit that corpus retrieval is enrichment, not scoring.

## Recommended Trait-Level Additions

### 1. `keyword_layers`

Add a source-separated keyword payload:

```json
{
  "keyword_layers": {
    "morin": ["temperament", "life", "health"],
    "classical": ["constitution", "self-presentation"],
    "modern": ["identity formation", "self-image"],
    "textbook": ["personality", "vital force"]
  }
}
```

Rules:

- `morin` comes only from the canonical Morin-facing map.
- `classical` comes from vetted classical retrieval or structured extracts.
- `modern` comes from modern psychological sources such as Rudhyar.
- `textbook` is optional for generic handbook-style material.

Backward compatibility:

- existing `keywords` remains the compact `morin` display list.

### 2. `citations`

Add explicit, source-labeled support excerpts:

```json
{
  "citations": [
    {
      "citation_id": "demetra-george:chunk-0142",
      "source_lineage": "classical",
      "source_label": "Demetra George",
      "work_title": "Ancient Astrology in Theory and Practice",
      "author": "Demetra George",
      "locator": {
        "chunk_id": "Ancient_Astrology_in_Theory_and_Practice_A_Manual_of_--_Demetra_George_--_Auckland_Ne_d7110c0cb5__chunk_0142",
        "page_start": 188,
        "page_end": 190,
        "guide_path": "C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/new_sources_inspection/guides/Ancient_Astrology_in_Theory_and_Practice_A_Manual_of_--_Demetra_George_--_Auckland_Ne_d7110c0cb5.md"
      },
      "excerpt": "Concise excerpt text here.",
      "relevance": 0.84,
      "topic_tags": ["ascendant", "temperament", "ruler"]
    }
  ]
}
```

Rules:

- citations are non-scoring in phase 1,
- each citation must declare source lineage,
- each citation must point back to a corpus chunk,
- excerpt length should stay short enough for UI use.

### 3. `citation_summary`

Add a small helper summary for quick UI display:

```json
{
  "citation_summary": {
    "count": 2,
    "lineages": ["classical", "modern"],
    "top_source": "Demetra George"
  }
}
```

This avoids forcing the UI to parse the full citations array to render a small badge.

### 4. `enrichment_status`

Add a small state field:

```json
{
  "enrichment_status": {
    "morin_keywords": "present",
    "corpus_keywords": "present",
    "citations": "present"
  }
}
```

This helps testing and makes incomplete cases visible.

## Recommended Guidance Shape

Do not overwrite the current `guidance` array immediately. Add a parallel structure:

```json
{
  "guidance": [
    {
      "category": "Planet",
      "term": "Mercury",
      "do": "Use speech and analysis constructively",
      "dont": "Scatter attention"
    }
  ],
  "guidance_layers": {
    "canonical": [
      {
        "category": "Planet",
        "term": "Mercury",
        "do": "Use speech and analysis constructively",
        "dont": "Scatter attention"
      }
    ],
    "classical": [
      {
        "category": "Ascendant",
        "term": "Ascendant ruler",
        "do": "Anchor interpretation in the ruler's condition",
        "dont": "Over-read isolated sign language",
        "source_label": "Demetra George"
      }
    ],
    "modern": [
      {
        "category": "Selfhood",
        "term": "Identity pattern",
        "do": "Integrate conscious purpose with emotional habit",
        "dont": "Reduce the chart to fixed labels",
        "source_label": "Dane Rudhyar"
      }
    ]
  }
}
```

Rule:

- `guidance` remains the current stable output,
- `guidance_layers` is additive and provenance-aware.

## Recommended Backend JSON Example

For one trait:

```json
{
  "id": "scholarship",
  "name": "Scholarship",
  "domain": "cognitive_style",
  "description": "Study-oriented, structured, and reflective intelligence.",
  "source_status": "curated",
  "source_lineage": "carter",
  "source_lineage_label": "Carter lineage",
  "score": 78.4,
  "raw_score": 18.8,
  "max_score": 24.0,
  "support_hits": 3,
  "support_total": 4,
  "dampener_hits": 0,
  "band": "strong",
  "polarity": "positive",
  "evidence": [
    "+ Mercury strong (+6)",
    "+ area[belief,study] emphasized (+4)",
    "↑ Jupiter supports judgment (+3)"
  ],
  "keywords": ["learning", "doctrine", "speech"],
  "keyword_layers": {
    "morin": ["learning", "doctrine", "speech"],
    "classical": ["study", "judgment", "disciplined inquiry"],
    "modern": ["meaning-making", "intellectual development"]
  },
  "citations": [
    {
      "citation_id": "demetra-george:chunk-0142",
      "source_lineage": "classical",
      "source_label": "Demetra George",
      "work_title": "Ancient Astrology in Theory and Practice",
      "author": "Demetra George",
      "locator": {
        "chunk_id": "Ancient_Astrology_in_Theory_and_Practice_A_Manual_of_--_Demetra_George_--_Auckland_Ne_d7110c0cb5__chunk_0142",
        "page_start": 188,
        "page_end": 190,
        "guide_path": "C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/new_sources_inspection/guides/Ancient_Astrology_in_Theory_and_Practice_A_Manual_of_--_Demetra_George_--_Auckland_Ne_d7110c0cb5.md"
      },
      "excerpt": "The ruler of the ascending sign and Mercury jointly describe how the native learns and orders thought.",
      "relevance": 0.84,
      "topic_tags": ["mercury", "ascendant ruler", "study"]
    }
  ],
  "citation_summary": {
    "count": 1,
    "lineages": ["classical"],
    "top_source": "Demetra George"
  },
  "enrichment_status": {
    "morin_keywords": "present",
    "corpus_keywords": "present",
    "citations": "present"
  }
}
```

## UI Rollout Recommendation

### Phase 1

No breaking changes.

- Keep using `keywords` where the UI currently uses compact chips.
- Add an optional citations section under the evidence list.
- Add an optional badge such as `Classical support` or `Modern support`.

### Phase 2

Expose layered keywords:

- `Morin`
- `Classical`
- `Modern`

This should only be shown in expanded mode, not compact mode.

### Phase 3

Allow source filtering in the trait modal:

- all
- Morin-facing
- classical
- modern

## Testing Contract

Add tests that assert:

1. `keywords` still exists and still contains Morin-facing tags,
2. `keyword_layers.morin` matches or supersets `keywords`,
3. corpus-derived citations never overwrite `sources`,
4. traits with no corpus support still render correctly,
5. source lineage remains explicit per citation.

## Hard Boundary

Do not do this:

1. overwrite `keywords` with mixed-source retrieval output,
2. append Rudhyar-style psychological terms into `morin_keywords.json`,
3. let citation snippets become score inputs without structured curation,
4. collapse all enrichment into a single unlabeled keyword list.

That would destroy provenance and make the Morin-facing process doctrinally muddy.

## Recommended First Implementation Slice

1. Add top-level `trait_enrichment_meta`.
2. Add trait-level `keyword_layers`.
3. Keep `keywords = keyword_layers.morin`.
4. Add trait-level `citations`.
5. Leave scoring untouched.

That gives us a clean contract, zero doctrinal contamination, and minimal UI breakage.
