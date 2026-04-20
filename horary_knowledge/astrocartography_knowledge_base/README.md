# Astrocartography Knowledge Base

This directory is a cleaned, AI-oriented layer built from the raw extracted astrocartography book corpus.

## Layout

- `normalized_books/`: full-book markdown versions with page headings and flatter paragraphs
- `guides/`: fast-scan per-book guides with role, relevance, headings, and keyword anchors
- `reference/`: distilled concept docs for implementation work
- `catalog.json`: machine-readable summary of the generated corpus

## Recommended Reading Order

1. `reference/01_core_concepts.md`
2. `reference/02_planetary_and_angular_reference.md`
3. `reference/03_techniques_and_ranges.md`
4. `reference/05_feature_notes.md`
5. `guides/hermes_map_interpretation.md`
6. `guides/dan_furst_best_places.md`
7. `guides/lewis_guttman_book_of_maps.md`

## Source Coverage

| Book | Role | Relevance | Best use |
| --- | --- | --- | --- |
| Astrocartography Map Interpretation (Hermes Astrology) | Interpretation encyclopedia | high | Use for line meanings, angle meanings, and crossing interpretations. |
| Finding Your Best Places | Conceptual and practical field guide | high | Use for workflow, line range assumptions, relocation vs. local-space distinctions, and user-facing guidance. |
| The Astro*Carto*Graphy Book of Maps | Case-study atlas and historical reference | high | Use for evidence patterns, angular framing, and examples of how lines were linked to places and life events. |
| Dictionary of Astrology | Supporting terminology reference | medium | Use for generic astrology vocabulary when the astrocartography books assume prior knowledge. |
| The Astrology of Death | Tangential supporting source | low | Treat as lower-priority support; it is not a primary astrocartography book. |
