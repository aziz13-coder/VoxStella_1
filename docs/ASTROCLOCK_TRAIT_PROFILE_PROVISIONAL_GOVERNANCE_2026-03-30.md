# Astro Clock Trait Profile Provisional Governance

Date: 2026-03-30

## Purpose

This pass implements the first governance layer from the next curation plan:

- placeholder/TBD traits remain in the catalog
- placeholder/TBD traits remain visible in the full trait list
- placeholder/TBD traits are suppressed from summary surfaces by default when curated alternatives exist

This is an honesty and source-governance change, not a rewrite of the underlying trait rules.

## Why this pass was needed

The local converted source corpus under `horary_knowledge/desktop_books_text` does not yet contain the Carter primary source text that many fine-grained trait entries cite. That means a subset of the catalog still rests on:

- placeholder descriptions
- `TBD` source notes
- partial extraction notes
- provisional Carter-dependent medical/pathology entries

Those entries should not dominate `top_traits` or the modal’s summary split when stronger curated alternatives are present.

## Governance rule

Trait entries are now classified as either:

- `curated`
- `provisional`

Classification order:

1. explicit `source_status` if present
2. explicit boolean `provisional`
3. fallback text scan over `description` and `sources`

The fallback scan marks a trait as provisional if it contains markers such as:

- `placeholder`
- `tbd`
- `to extract`
- `to add`
- `to refine`
- `provisional`

## Runtime behavior

### Backend engine

Each indicated trait now carries:

- `source_status`
- `provisional`

`top_traits` selection now prefers:

1. curated family representatives
2. then provisional representatives only if no curated candidates exist
3. within that set, non-weak bands first

The full `traits` list is not filtered out. Provisional entries remain available for inspection.

### Frontend modal

Summary split (`Top Positive`, `Top Neutral`, `Top Negative`) now uses the curated-only representative list when at least one curated representative exists.

The full `All Traits` list still shows provisional entries and marks them visibly with:

- `Provisional source`
- `placeholder-derived`

## What this does not claim

This pass does not claim that provisional entries are false. It only claims that they are not source-secure enough to be allowed to dominate summary surfaces by default.

## Verification

This pass is covered by:

- backend engine contract tests for curated-vs-provisional summary preference
- backend fallback tests where provisional entries still surface if they are the only candidates
- frontend modal tests confirming:
  - curated summary preference
  - provisional full-list visibility
  - visible provisional labeling
