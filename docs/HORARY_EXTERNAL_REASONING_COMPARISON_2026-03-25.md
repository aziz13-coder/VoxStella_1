# Horary External Reasoning Comparison

Date:
2026-03-25

## Purpose

This note answers a narrower question than the normal `source-pass` slices:

- not just whether the router picked the right houses
- but whether the backend's actual horary reasoning materially matches the source rationale where reconstruction is safe enough

## Comparison Levels

There are currently two different comparison levels in the external corpus:

1. `replay` comparison
   These cases have enough reconstructed chart structure to run through the serialized backend path and compare:
   - verdict
   - category
   - perfection family
   - reasoning snippets

2. `source-pass` comparison
   These cases currently compare only:
   - doctrine family
   - category
   - relevant houses
   - quesited house
   - question intent

So a `source-pass` slice can tell us that the engine is reading the question through the right doctrinal lens, but it does **not** yet prove that the backend's final judgment reasoning matches the source chart judgment.

## What Can Be Compared Today

At full reasoning level, the current safe external replay corpus contains four Cunning Man article reconstructions:

1. `will_i_get_job_article_spec`
2. `pay_rise_article_spec`
3. `x_romantically_article_spec`
4. `pope_die_article_spec`

Additionally, one image-reconstructable non-Cunning-Man case already has strong doctrinal comparison but has **not** yet been promoted to replay:

5. `operation_go_smoothly_source_pass`

## Full Reasoning Comparison: Replayed Cases

### 1. Will I Get the Job?

Source family:

- external article replay fixture:
  - `tests/fixtures/horary_external_cunning_man_replay.json`

Source rationale visible from the article:

- querent is Moon in the 10th
- job is Jupiter as Lord 10, hidden in the 12th and retrograde
- Saturn on the 10th cusp acts as a blocker
- Moon is void of course
- the Moon has already passed its aspect with Jupiter
- final verdict: `NO`

Backend replay result:

- verdict: `NO`
- perfection type: `denial_secondary_balance`

Backend reasoning core:

- occurrence question
- querent: Moon, quesited: Jupiter
- Jupiter retrograde
- Moon separates from Jupiter
- no direct perfection remains between Moon and Jupiter
- Moon is treated as void/excepted rather than as a rescue
- Jupiter is cadent

Assessment:

- materially aligned
- the backend is reproducing the article's main denial logic, not just the houses
- especially important is that it keeps the denial on lack of remaining perfection plus weakened job testimony, rather than forcing a positive answer from Moon in the 10th

### 2. Pay Rise

Source family:

- external article replay fixture:
  - `tests/fixtures/horary_external_cunning_man_replay.json`

Source rationale already pinned in fixture:

- article verdict: `NO`
- no perfection / no direct perfection

Backend replay result:

- verdict: `NO`
- perfection type: `denial_secondary_balance`

Backend reasoning core:

- event/occurrence question
- no direct perfection between significators
- Moon not void keeps the matter active
- some secondary support exists, but not enough to overturn denial

Assessment:

- materially aligned
- the backend is slightly more explicit than the article-spec fixture about secondary testimony
- but the core reasoning is the same: no clean perfection, therefore no pay rise

### 3. Romantic Mutual Liking

Source family:

- external article replay fixture:
  - `tests/fixtures/horary_external_cunning_man_replay.json`

Source rationale pinned in fixture:

- article verdict: `NO`
- reciprocal affection should be judged by reception
- one-way reception only

Backend replay result:

- verdict: `NO`
- perfection type: `relationship_affection_balance`

Backend reasoning core:

- relationship question treated as `QUALITY`, not simple occurrence
- applying conjunction exists
- one-way reception exists
- mutual liking is denied because reciprocity is not shown

Assessment:

- strongly aligned
- this is a good example of the backend following doctrine rather than just rewarding contact between significators
- the engine correctly lets reception logic outrank bare aspect contact in an affection question

### 4. Will the Pope Die Soon?

Source family:

- external article replay fixture:
  - `tests/fixtures/horary_external_cunning_man_replay.json`

Source rationale pinned in fixture:

- article verdict: `NO`
- Pope judged from the turned-house public/religious axis
- no direct perfection between significators

Backend replay result:

- verdict: `NO`
- perfection type: `none`

Backend reasoning core:

- occurrence question
- Pope routed through the turned public/religious axis
- no direct perfection between Moon and Jupiter
- some mixed support exists but not enough to perfect death soon

Assessment:

- materially aligned
- the important point is not just the final `NO`
- the backend is also matching the article's turned-house framing and denial structure

## Doctrine Comparison Only: Not Yet Replayed

### 5. Will the Operation Go Smoothly?

Source:

- `https://wroskopos.wordpress.com/2010/03/31/will-the-operation-go-smoothly/`

Source rationale visible from the article:

- patient on the `1st`
- illness/problem on the `6th`
- doctor on the `7th`
- operation itself on the `8th`
- the article explicitly denies the matter through the Moon's applying opposition to the Sun

Current backend/source-pass status:

- category: `health`
- houses: `[1, 6, 7, 8]`
- quesited house: `8`
- source alignment: `true`

Assessment:

- doctrinally aligned
- but not yet a full reasoning match
- doctrine-only coverage has now been strengthened to assert the shared `medical_procedure` family, the full `1/6/7/8` structure, and the absence of the old pet false positive
- today we can say the backend reads the question through the same medical-procedure doctrine as the source
- we cannot yet honestly claim that the backend reproduces the article's final operation judgment on the real chart, because this case has not been promoted into replay

## What The Source-Pass Slices Currently Prove

For the completed image-reconstructable source-pass slices, the backend is currently matching the article doctrine in cases such as:

- higher education and higher exams on the `9th`
- short-transit train arrival on the `3rd`
- foreign-state referendum and military action on the `9th`-based axis
- treatment/medicine questions on `1/6/7/10`
- religious-festival weather on the event's `9th`
- medical-result timing on the medical contact axis

That is real progress, but it is still routing-level progress.

It means:

- the backend is reading the question through the same doctrinal frame as the article

It does **not** yet mean:

- the backend has been shown to reproduce the article's final delineation on the reconstructed chart

## Bottom-Line Status

Current external reasoning comparison status is:

- full source-vs-backend reasoning comparison: `4` cases
- doctrine-only source-vs-backend comparison: the remaining completed source-pass slices

Current conclusion:

- where replay reconstruction has already been done, the backend reasoning is materially aligned with the external source rationale
- where only source-pass has been done, the backend is aligned at the doctrinal framing level, but final reasoning has not yet been proven

## Best Next Step

The highest-value next move is not another doctrine-only slice.

It is to promote one or more of the current `image_reconstructable` cases into replay, starting with:

1. `how_will_i_do_in_my_exams_source_pass`
2. `will_i_get_into_university_usa`
3. `operation_go_smoothly_source_pass`

That would let us compare:

- source verdict
- backend verdict
- source rationale
- backend reasoning chain

instead of only comparing doctrinal routing.
