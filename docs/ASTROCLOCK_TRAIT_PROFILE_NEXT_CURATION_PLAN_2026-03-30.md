# Astro Clock Trait Profile Next Curation Plan

Date: 2026-03-30

## Purpose

This plan sketches the next careful trait-profile curation pass after:

- source restoration
- score normalization
- polarity repair
- summary family collapse

The goal now is not more engine mechanics. It is controlled catalog curation using the source base that is actually available in the repo.

## Source Scan Result

### What the converted local book corpus currently contains

The converted local text corpus under `horary_knowledge/desktop_books_text` is dominated by:

- Morin
- Bonatti
- Schöner
- Montulmo
- Abu Ali al-Khayyat
- Arroyo

### What it does **not** currently contain as a primary source

The trait catalog is overwhelmingly Carter-derived, but the converted corpus does **not** currently include Carter’s primary reference book used by the catalog.

What the repo does have:

- many trait JSON files cite `Carter`
- one secondary mention of Carter appears in Arroyo

What the repo does **not** have:

- a converted primary Carter encyclopedia/source text that lets us verify the majority of the fine-grained trait catalog directly

## Practical consequence

Careful curation must now proceed in tiers.

### Tier 1: source-tight curation from current local corpus

These are safe to refine from the current book set:

- Morin-facing house/domain overlays
- broad traditional virtue/vice correspondences already present in Morin/Schöner/nativity texts
- clearly duplicated editorial variants
- clearly dormant placeholders

### Tier 2: Carter-dependent curation

These should **not** be aggressively rewritten from guesswork:

- ultra-specific medical/pathology traits
- degree-based disease rules
- very fine-grained temperament nuances that are cited only as `Carter`
- placeholder traits whose source line explicitly says `TBD`, `to extract`, or similar

For those, the honest choices are:

- keep them but mark them as provisional
- or retire/hide them from summary surfaces
- or wait until the Carter primary text is added to the local corpus

## Catalog-quality targets found in the scan

### 1. Dormant placeholders

Currently inert:

- `baldness_risk`
- `knock_knees`
- `lameness_gait`

These are strong candidates for one of:

- retirement from surfaced results
- explicit `provisional` tagging
- later reactivation only after Carter extraction

### 2. Ultra-thin Carter-dependent medical/pathology entries

Representative examples:

- `goitre_thyroid`
- `influenza`
- `gout`
- `insomnia`
- `kidney_disease_general`
- `kidney_stones`
- `blindness_predisposition`
- `dropsy_edema`
- `dyspepsia`

These are the highest-risk entries for overclaiming because they are narrow, medical, and often placeholder-like.

### 3. Editorial near-duplicate families

Already fixed at the summary layer for identical logic, but still good curation candidates:

- fixed/Saturn restraint-rigidity family
- mutable fluctuation/instability family
- Aries/Mars confrontation/assertion family

These should be reviewed editorally for whether:

- some should remain distinct
- some should be renamed
- some should be folded into a clearer canonical family plus aliases

## Recommended next passes

### Pass A: Provisional trait governance

Scope:

- add a `provisional` or `source_status` field to catalog entries that are explicitly placeholder/TBD
- suppress provisional traits from `top_traits` by default unless strongly requested or unless no non-provisional alternatives exist

Why first:

- lowest risk
- highest honesty gain
- especially important for medical/pathology entries

### Pass B: Dormant trait retirement or quarantine

Scope:

- review dormant zero-support entries
- either:
  - remove them from surfaced output entirely
  - or keep them cataloged but hidden until real rules are extracted

Why second:

- these traits currently add maintenance overhead without interpretive value

### Pass C: Editorial family consolidation

Scope:

- review near-duplicate but non-identical families
- define canonical family names for summary surfaces
- retain full catalog IDs internally if needed

Why third:

- this is a content-model pass, not a pure engine pass
- it should happen only after placeholder/provisional governance is in place

### Pass D: Carter source import

Scope:

- add the actual Carter source text to `horary_knowledge/desktop_books_text`
- then re-audit all Carter-cited medical/pathology and temperament entries against the real text

Why last:

- this is the only way to do high-confidence curation of the Carter-heavy catalog instead of careful containment

## Recommended immediate next implementation

If continuing now, the best next implementation is:

### Implement provisional governance for placeholder/TBD traits

That means:

- mark placeholder/TBD entries in the catalog
- exclude them from `top_traits` and summary splits by default
- leave them visible in the full trait list if needed, clearly marked as provisional

This is the most defensible next step because it improves honesty without pretending we have the missing Carter primary source.

## Current claim boundary

At this point, the trait profile can honestly claim:

- improved scoring comparability
- visible neutral traits
- reduced duplicate crowding
- restored enrichment guidance

It should **not** yet claim:

- source-complete trait curation
- medically reliable pathology profiling
- Carter-faithful fine-grained disease extraction

Those require the missing primary Carter text or a deliberate reduction of the unsupported catalog surface.
