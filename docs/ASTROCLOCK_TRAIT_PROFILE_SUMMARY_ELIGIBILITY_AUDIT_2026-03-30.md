# Astro Clock Trait Profile Summary Eligibility Audit

Date: 2026-03-30

## Why This Pass Was Needed

Trait replay slice 1 exposed a real summary-layer problem:

- the expected trait families for public figures could be present in the full indicated `traits` list
- but `top_traits` and the modal summary panels could still be dominated by specialized or pathological indicators

Representative examples from the live replay pass:

- `death_retreat_theme`
- `grief_bereavement`
- `hydrophobia_rabies`
- `kidneys_region`
- `maladjustment`

These are not always invalid as indicators. The problem is that they were being treated as headline personality-summary items.

## Source Of The Problem

The engine in `backend/traits/engine.py` was selecting `top_traits` from family representatives by:

- non-provisional preference
- non-weak band preference
- then raw score ordering

That meant any high-scoring trait could win the summary, regardless of whether it belonged to:

- general character or cognition
- cautionary shadow material
- specialized medical, anatomical, or symbolic indicator domains

## Curation Rule Added

This pass adds a summary-surface distinction:

- `general`
- `caution`
- `specialized`

The rule is applied automatically from trait domain, with optional explicit override via `summary_surface` in catalog entries.

### Specialized summary surfaces

These are now excluded from headline summary selection whenever the chart has any general or caution traits:

- `motif`
- `pathology`
- `pathophysiology`
- `anatomy_correspondence`
- `anatomy_disease`
- `physique`
- `physique_injury`
- `constitution`
- `reproductive_tendency`
- `environmental_risk`
- `risk_theme`
- any domain starting with `disease_`

### Caution summary surfaces

These remain eligible only as caution-layer summary items:

- `psychological`
- `affect_loss_processing`
- `affect_negative`
- `temperament_defensive`
- `temperament_negative`
- `temperament_shadow`
- `shadow_tendency`
- `behavioral_risk`
- `relationship_risk`
- `compulsion_addiction`
- `cognitive_limitation`
- `cognitive_shadow`
- `social_shadow`
- `ethical_shadow`
- `ethic_shadow`
- `shadow_affect`
- `shadow_of_belief`
- `shadow_of_will`

Everything else defaults to `general` unless the catalog says otherwise.

## Implementation

Applied in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`
- `frontend/src/features/astroclock/TraitProfileModal.jsx`

New trait payload fields:

- `summary_surface`
- `summary_eligible`

New selection behavior:

1. prefer curated over provisional, as before
2. prefer non-weak over weak, as before
3. exclude `specialized` summary surfaces if any `general` or `caution` candidates exist
4. prefer `general` over `caution`
5. only fall back to `specialized` when nothing else is available

The full `traits` list is unchanged. This pass affects only summary selection.

## Frontend Alignment

The modal previously built its summary panels from `traits`, which could drift away from backend `top_traits`.

Now the summary panels prefer:

- backend `top_traits` if present
- otherwise representative traits that remain `summary_eligible`

This keeps the frontend summary in line with the backend’s new summary-eligibility rule while preserving the full list below for inspection.

## Expected Effect On Held-Back Cases

This pass should improve noisy public-figure summaries, especially for cases like Einstein and Jobs, by:

- removing medical and anatomy entries from the headline summary
- pushing symbolic motif entries out of the default summary
- making the top summary read more like a character/cognition profile and less like a pathology list

It does **not** by itself guarantee that their expected intellectual or inventive family becomes strong enough for promotion. That still depends on the underlying catalog rules for:

- `scholarship`
- `wisdom`
- `invention_discovery`
- `genius_inventive_scientific`

## Next Step

If Einstein and Jobs are still not replay-safe after this pass, the next improvement should be catalog-level, not summary-level:

- widen inventive/intellectual family rules
- separate methodical scholarship from inventive brilliance more clearly
- then run a second trait replay slice aimed at `top_traits` correctness
