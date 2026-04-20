# AstroClock Synastry Source-Backed Tuning Plan

Date: 2026-04-03

## Implementation Status

Implemented in the current pass:

1. narrowed `compatibility_conflict_gate` so only stronger ease markers block the cap:
   - `moon_moon_soft`
   - `venus_venus_soft`
   - `benefic_support_pairs`
2. narrowed `burden_saturn_context_relief` so Saturn-heavy burden is only moderated when:
   - stronger ease markers are present
   - corroborating heaviness comes from genuinely oppressive families, not generic activation or nodal heaviness
3. added `burden_oppressive_cluster_floor`, a governed burden-elevation rule that only fires when:
   - hard Saturn families are present
   - emotional-strain families are present
   - obstructive conflict families are present
4. replayed the first historical slice and updated the replay artifact in [synastry_historical_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1_results.json)

Current replay outcome after implementation:

1. `Paul Newman / Joanne Woodward` moved from `partially_aligned` to `aligned`
2. `Charles / Diana` moved from `partially_aligned` to `aligned`
3. the remaining doctrinal task is no longer this replay miss, but widening the validation corpus so the same burden logic is tested on more than one oppressive relationship archetype

## New Doctrine Applied

### 5. Oppressive Burden Requires Repeated Hard Themes, Not Generic Saturn Weight

Best anchors:

1. Arroyo, `The Preponderance of the Same Message or Theme Symbolized`
2. Davison, `Chapter 6 - Saturn aspects`
3. March / McEvers, `Lesson 9 - The Moon`
4. March / McEvers, `Lesson 9 - Interaspects`

Doctrine implication:

High `burden` should not be assigned because Saturn appears at all.

It should rise into the oppressive range when the same message is repeated through:

1. hard Saturn binding or Saturn overlays
2. emotional strain, especially Moon-involved stress
3. obstructive or resentment-producing conflict, especially Mars/Saturn

Tuning consequence:

The engine should elevate `burden` only when hard Saturn is corroborated by emotional and obstructive families. That keeps the rule general and source-governed, and it prevents durable Saturn bonds from being treated as uniformly oppressive.

## Purpose

Turn the first historical-validation replay slice into a doctrine-backed tuning plan.

This document is not a generic "improve the model" memo.

It answers:

1. which current miss patterns are real
2. which rule families are driving them
3. what the source books imply should change
4. what should be tuned first

## Current Evidence Base

Replay baseline:

1. [synastry_historical_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1.json)
2. [synastry_historical_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1_results.json)

Current governance surface:

1. [synastry_rule_catalog.json](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_rule_catalog.json)
2. [synastry_engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_engine.py)
3. [ASTROCLOCK_SYNASTRY_SOURCE_GOVERNANCE_2026-04-02.md](C:/Users/sabaa/Downloads/codexhorary/docs/ASTROCLOCK_SYNASTRY_SOURCE_GOVERNANCE_2026-04-02.md)

Source stack in scope:

1. Ronald C. Davison, `Synastry: Understanding Human Relations Through Astrology`
2. Stephen Arroyo, `Person-to-Person Astrology`
3. March / McEvers, `The Only Way to Learn About Relationships, Vol. 5`

## What The First Replay Slice Actually Shows

### Paul Newman / Joanne Woodward

Observed:

1. `attachment` aligned high
2. `compatibility` aligned high
3. `burden` massively overstated

Main compatibility drivers:

1. `unilateral_reception_support`
2. `venus_venus_soft`
3. `benefic_support_pairs`
4. `overlay_jupiter_major`
5. `mutual_reception_support`

Main burden drivers:

1. `saturn_hard_bond`
2. `node_personal_hard`
3. `overlay_saturn_major`
4. `empty_house_fill_heavy`

Interpretation:

The engine is correctly seeing binding and some real heaviness, but it is currently allowing Saturn-heavy and "fated/heavy activation" signals to flood the `burden` bar without enough context about whether the relationship was merely serious or actually oppressive.

### Charles / Diana

Observed:

1. `burden` aligned high
2. `friction` aligned high
3. `compatibility` materially overstated

Main compatibility drivers:

1. `mutual_reception_support`
2. `unilateral_reception_support`
3. `overlay_jupiter_major`
4. `element_sun_sun`
5. `overlay_venus_major`
6. `sign_house_affinity`

Main burden drivers:

1. `saturn_hard_bond`
2. `overlay_saturn_major`
3. repeated `empty_house_fill_heavy`

Interpretation:

The engine is correctly seeing the bond as consequential and difficult, but it is currently letting compensation and affinity signals inflate `compatibility / ease` too much, even when the core lived tone is conflict-heavy.

## Core Tuning Principle

The first replay slice does not justify a rewrite.

It justifies tightening the meaning of three categories:

1. `compatibility`
2. `burden`
3. `growth`

The current engine often treats:

1. compensation as ease
2. binding as ease
3. significance as ease
4. heaviness as always burden-maximizing

The sources do not support those equivalences cleanly.

## Source-Backed Doctrine For The Next Pass

### 1. Compatibility Must Mean Lived Ease, Not Mere Significance

Best anchors:

1. Arroyo, `Compatibility on the Elements' Energy Level`
2. Arroyo, later compatibility discussion around "stepping together" and mutual rhythm
3. Davison, `Venus/Venus`

Doctrine implication:

Compatibility means:

1. mutual rhythm
2. flowing together
3. day-to-day accord
4. emotional or social ease

It does not automatically mean:

1. karmic significance
2. strong attachment
3. developmental usefulness
4. inability to let go

Tuning consequence:

Rule families that mainly show `bond significance`, `development`, or `compensation` should stop inflating `compatibility` as strongly as they do now.

### 2. Saturn Can Bind Without Being Easy

Best anchors:

1. Davison, `Chapter 6 - Saturn aspects`
2. Davison, `Part Two - House Interchanges`

Doctrine implication:

Davison repeatedly treats Saturn as:

1. stabilizing
2. delaying
3. duty-producing
4. binding
5. often heavy

That means Saturn should often increase:

1. `attachment`
2. sometimes `burden`

But Saturn should not easily convert into:

1. `compatibility`
2. emotional ease

Tuning consequence:

The engine should distinguish:

1. constructive Saturn support
2. heavy-but-enduring Saturn
3. oppressive Saturn

It currently compresses those too aggressively.

### 3. Lacks And Empty-House Filling Mean Compensation, Not Necessarily Comfort

Best anchors:

1. March / McEvers, `Lesson 8 - The Importance of Lacks`
2. March / McEvers, `Lesson 8 - Filling Another's Empty Houses`
3. March / McEvers, `Lesson 8 - Affinities`

Doctrine implication:

March / McEvers treat missing factors and house activation as:

1. something one yearns for
2. borrowed development
3. activation of otherwise dormant life areas
4. sometimes a useful correction
5. sometimes uneven or difficult

That is closer to:

1. `growth`
2. `activation`
3. `compensation`

than to:

1. `compatibility / ease`

Tuning consequence:

`element_lack_fill`, `modality_lack_fill`, `empty_house_fill_light`, `empty_house_fill_heavy`, and some affinity logic should be pulled away from ease scoring and treated as developmental first.

### 4. Preponderance Matters More Than Isolated Positives

Best anchors:

1. Arroyo, `The Aspects`
2. Arroyo, `The Preponderance of the Same Message or Theme Symbolized`

Doctrine implication:

Arroyo's method is not:

1. count one nice factor, call it compatible

It is:

1. look for the dominant message
2. weigh repeated themes
3. judge whether the relationship tone is easy, stimulating, conflicted, or mixed

Tuning consequence:

The engine needs stronger category-level gating so one stack of support signals does not automatically push `compatibility` to 100 when the dominant lived tone is conflict-heavy.

## Rule-Family Adjustments To Make First

### A. Reclassify reception effects

Targets:

1. `mutual_reception_support`
2. `unilateral_reception_support`

Current problem:

Both cases receive a large `compatibility` lift from reception logic.

Source-backed adjustment:

1. move more of `mutual_reception_support` from `compatibility` into `attachment`
2. reduce the `compatibility` cap on `mutual_reception_support`
3. remove or sharply reduce `compatibility` contribution from `unilateral_reception_support`
4. keep unilateral reception as `growth`, `cooperation`, or mild `attachment`, not lived ease

Why:

Davison and March/McEvers support receptivity and carrying power, but that is not the same thing as smooth day-to-day compatibility.

### B. Reclassify lack-fill and empty-house logic

Targets:

1. `element_lack_fill`
2. `modality_lack_fill`
3. `empty_house_fill_light`
4. `empty_house_fill_heavy`
5. `sign_house_affinity`

Current problem:

These families can stack into very high `growth` and `compatibility` even in strained relationships.

Source-backed adjustment:

1. treat `lack_fill` as primarily `growth`
2. make `empty_house_fill_light` mostly `growth` with at most a small `compatibility` tail
3. make `empty_house_fill_heavy` mostly `growth + burden`, not ease
4. keep `sign_house_affinity` as a light harmony marker, but do not let it compete with hard Moon/Saturn/Mars evidence

Why:

March/McEvers describe filling lacks as developmental and compensatory, not automatically restful.

### C. Tighten Saturn burden logic

Targets:

1. `saturn_soft_bond`
2. `saturn_hard_bond`
3. `overlay_saturn_major`
4. `mars_saturn_hard`

Current problem:

Durable cases can hit very high `burden` simply because several Saturn families fire at once.

Source-backed adjustment:

1. keep `saturn_soft_bond` strongly in `attachment`
2. let `saturn_soft_bond` add only a small amount of `burden`
3. require stronger corroboration before `saturn_hard_bond` fully loads `burden`
4. prevent `overlay_saturn_major` from double-counting heaviness when hard Saturn aspects already dominate
5. allow `mars_saturn_hard` to remain a major friction marker, but stop it from dragging all Saturn cases into the same burden ceiling

Why:

Davison treats Saturn as serious and binding, but not every Saturn-heavy bond should look maximally oppressive.

### D. Add compatibility gating by dominant theme

Targets:

1. compatibility category assembly
2. overall model support-balance logic

Current problem:

`compatibility` can stay near max even when the bond is visibly conflict-heavy.

Source-backed adjustment:

1. if multiple core strain signals are present, cap `compatibility` unless direct ease signals also exist
2. core strain signals should prioritize:
   - hard Moon links
   - hard Mercury links
   - hard Saturn-to-luminary/personal links
   - hard Mars/Saturn links
3. direct ease signals should prioritize:
   - Moon harmony
   - Mercury harmony
   - Venus harmony
   - Jupiter smoothing
   - Ascendant fit

Why:

This follows Arroyo's preponderance logic and preserves the meaning of `compatibility / ease`.

## Concrete Implementation Order

### Phase 1. Catalog-only rebalance

Change only:

1. reception family score splits
2. lack-fill and empty-house score splits
3. Saturn burden weights

Do not change:

1. aspect detection
2. point set
3. UI

Purpose:

See whether the first replay slice becomes more plausible through governed weight shifts alone.

### Phase 2. Category gating

In [synastry_engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_engine.py):

1. add a `compatibility_cap_from_conflict()` style helper
2. gate `compatibility` when repeated hard-theme evidence outweighs ease evidence
3. optionally add `burden_cap_relief()` when Saturn heaviness lacks corroborating strain

Purpose:

Prevent category inflation from additive stacking.

### Phase 3. Replay and compare

Replay:

1. [synastry_historical_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1.json)

Success condition for the next pass:

1. Paul/Joanne `burden` drops materially
2. Charles/Diana `compatibility` drops materially
3. primary dimensions remain aligned

### Phase 4. Expand validation before deeper tuning

Only after Phase 1 and 2 should we promote:

1. a high-chemistry unstable couple
2. a growth-heavy burdened couple

That will tell us whether the fixes generalized or only solved the first two cases.

## Exact Rule-Family Priority List

Highest priority:

1. `mutual_reception_support`
2. `unilateral_reception_support`
3. `element_lack_fill`
4. `empty_house_fill_light`
5. `empty_house_fill_heavy`
6. `saturn_hard_bond`
7. `overlay_saturn_major`

Medium priority:

1. `sign_house_affinity`
2. `overlay_jupiter_major`
3. `overlay_venus_major`
4. `node_personal_soft`
5. `node_personal_hard`

Leave alone for now:

1. direct Moon/Moon logic
2. direct Venus/Venus logic
3. direct Mars/Saturn hard detection
4. point-set expansion
5. orb profiles

## Recommendation

The next implementation pass should be narrow and source-governed:

1. rebalance reception, lack-fill, and Saturn families in the catalog
2. add a compatibility cap driven by dominant hard themes
3. rerun replay slice 1

That is the smallest responsible next move consistent with the sources and with the historical-validation evidence already captured.
