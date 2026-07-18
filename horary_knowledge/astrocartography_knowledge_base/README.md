<!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->

# Astrocartography Knowledge Base

This directory is a traceable, AI-oriented layer built from the governed local astrocartography corpus. Stable IDs prove where a claim came from; they do not prove astrology or a retrospective case interpretation scientifically valid.

## Layout

- `normalized_books/`: governed source books with stable page and paragraph chunk IDs
- `guides/`: source-specific scan guides with token-bounded keyword anchors
- `reference/`: classified direct, synthesis, legacy-parity, and experimental notes
- `catalog.json`: portable source catalog with repository-relative paths
- `chunk_index.jsonl`: retrieval index keyed by source, page, and chunk IDs
- `../astrocartography_sources/`: canonical source and claim registries

## Recommended Reading Order

1. `reference/00_source_governance.md`
2. `reference/01_core_concepts.md`
3. `reference/02_planetary_and_angular_reference.md`
4. `reference/03_techniques_and_ranges.md`
5. `guides/lewis_guttman_book_of_maps.md` — canonical doctrine
6. `guides/dan_furst_best_places.md` — secondary practitioner variants
7. `guides/hermes_map_interpretation.md` — tertiary comparison only

## Source Coverage

| Rank | Source ID | Book | Retrieval | Best use |
| ---: | --- | --- | --- | --- |
| 1 | `acg-src-lewis-guttman-1989` | The Astro*Carto*Graphy Book of Maps: The Astrology of Relocation — How 136 Famous People Found Their Places | astrocartography-doctrine, historical-case-studies | Use first for canonical line, angle, crossing, natal-condition, and remote-activation doctrine. Treat retrospective cases as illustrations, not independent validation. |
| 2 | `acg-src-furst-best-places-2015` | Finding Your Best Places: Using Astrocartography to Navigate Your Life | astrocartography-doctrine, practitioner-variants, workflow | Use for practitioner workflow, explicit technique variants, local-space and relocation distinctions, range sensitivity, and cautionary interpretations. |
| 3 | `acg-src-hermes-map-2023` | Astrocartography Map Interpretation | tertiary-comparison | Use only for comparison copy and candidate interpretations that are checked against higher-tier sources. |
| 4 | `acg-src-lee-dictionary-1968` | Dictionary of Astrology | terminology | Use only to define generic astrology vocabulary when an astrocartography source assumes prior knowledge. |
| 5 | `acg-src-houck-death-1994` | The Astrology of Death | excluded — Non-astrocartography health/death material can create unsafe and false location-risk inferences. | Do not use in astrocartography retrieval, interpretations, risk scoring, or validation. |

The Astrology of Death remains inventoried in `catalog.json` but is intentionally absent from normalized books, guides, and retrieval chunks. The dictionary is restricted to the `terminology` scope.
