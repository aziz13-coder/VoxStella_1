# Astrocartography Source Governance

This directory is the checked-in source of truth for the local astrocartography corpus.

- `source_registry.json` records stable source IDs, bibliographic metadata, source and extraction hashes, page coverage, extraction provenance, rights status, retrieval scope, and authority tier.
- `claim_registry.json` records implementation-facing claims as `direct`, `synthesis`, `legacy-parity`, or `experimental`, with page locators where a local source is relevant.

The authority order is deliberate:

1. Jim Lewis and Ariel Guttman: canonical Astro*Carto*Graphy doctrine.
2. Dan Furst: secondary practitioner workflow and variants.
3. Hermes Astrology: tertiary explanatory comparison.
4. Dal Lee: terminology only.
5. Richard Houck: inventoried but excluded from astrocartography retrieval.

A page or chunk locator proves traceability to the local corpus. It does not prove that astrology, a case interpretation, or a Vox Stella score is scientifically valid.

Run `python scripts/validate_astrocartography_sources.py` after changing the registry, claims, extraction, or knowledge-base builder.
