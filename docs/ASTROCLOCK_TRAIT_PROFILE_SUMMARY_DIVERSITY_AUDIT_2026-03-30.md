# Astro Clock Trait Profile Summary Diversity Audit

Date: 2026-03-30

## Purpose

This pass addressed the remaining summary problem after:

- provisional-governance filtering
- summary-eligibility filtering
- inventive/intellectual catalog broadening

Those earlier passes made the full trait list better and helped the inventive families score, but the headline `top_traits` summary could still be monopolized by one high-scoring bucket such as broad character or social temperament.

## Problem Found

Two replay probes made the issue clear:

### Albert Einstein

After the inventive-catalog expansion, the full indicated list already contained:

- `invention_discovery` `54.7`
- `genius_inventive_scientific` `43.5`
- `scholarship` `34.9`

But the headline summary was still dominated by:

- `conservatism`
- `constancy`
- `fixed_reserve_possession`
- `headstrong_obstinate`

So the engine was no longer *missing* inventive families. It was still selecting too many traits from the same broad summary bucket.

### Steve Jobs

After the same pass, the full indicated list already contained:

- `scholarship` `69.8`
- `wisdom` `66.7`
- `intelligence_general` `41.7`
- `questioning_mind` `36.8`
- `invention_discovery` `37.7`

But the headline summary was still led by:

- `charity`
- `hospitality`
- `luxury_love_of_pleasure`

The problem again was not raw absence. It was summary selection.

## Fix Applied

Implemented in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`

### 1. Summary buckets

Traits now derive a coarse `summary_bucket` for headline selection, for example:

- `cognition`
- `social`
- `affective`
- `drive`
- `worldview`
- `material`
- `vocation`
- `aesthetic`
- `character`

This is additive metadata. It does not remove anything from the full trait list.

### 2. Bucket-diverse summary selection

`top_traits` no longer takes the highest-scoring headline candidates in a flat list.

It now:

1. builds the usual summary-safe pool
2. chooses one representative per bucket first
3. only fills remaining slots with duplicates after bucket coverage is established

This prevents one strong bucket from consuming the entire summary.

### 3. Cognition-bucket priority

Within the cognition bucket, the selector now prefers canonical intellectual families over generic cognition-adjacent traits.

Examples of preferred headline families:

- `invention_discovery`
- `genius_inventive_scientific`
- `scholarship`
- `wisdom`
- `intelligence_general`
- `knowledge_general_intellect`
- `questioning_mind`
- `vision_big_picture`

That means a generic communication or imagination trait does not automatically beat a more diagnostic intellectual family just because its raw score is slightly higher.

## Result

### Einstein

Headline summary now includes:

- `conservatism`
- `quarrelsomeness`
- `vision_big_picture`
- `valor`
- `greed_covetousness`
- `libido_sexual_drive_style`
- `invention_discovery`
- `grace_artistic`

Important change:

- `invention_discovery` now appears in `top_traits`
- it previously did not survive the headline selector

### Jobs

Headline summary now includes:

- `charity`
- `luxury_love_of_pleasure`
- `yare_readiness`
- `unity_of_humankind`
- `home_domesticity`
- `scholarship`
- `yearning_for_order`
- `grace_artistic`
- `vision_big_picture`

Important change:

- `scholarship` now appears in `top_traits`
- it previously lost the cognition slot to a looser generic cognition-family item

## What This Fix Does Not Claim

This pass improves summary representation. It does **not** prove that Einstein and Jobs should already be promoted into a stricter summary-replay slice.

Why they remain cautious:

- Einstein still has several broad non-intellectual headline traits above `invention_discovery`
- Jobs still leads with hospitality/pleasure/social-family traits before scholarship

So the current honest claim is:

- the summary is materially more diverse and more diagnostic
- the headline selector now preserves the key intellectual family for both probes
- a stricter summary-cleanliness replay slice still needs its own promotion threshold

## Tests Added

Added backend contract coverage in:

- `backend/test_trait_engine_contract.py`

New checks:

- summary bucket diversity before repeating a bucket
- cognition-bucket priority preferring headline intellectual families over generic cognition-adjacent traits

## Verification

- `python -m pytest backend/test_trait_engine_contract.py tests/test_trait_profile_route_contract.py tests/test_trait_profile_replay_slice_1.py -q`
  - `15 passed`
- `npm exec vitest run src/tests/traitProfileModal.test.jsx --config vitest.config.mjs`
  - `5 passed`
- `npm run build`
  - passed
