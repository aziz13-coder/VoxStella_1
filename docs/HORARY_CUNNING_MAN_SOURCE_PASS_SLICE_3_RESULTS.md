# Horary Cunning Man Source-Pass Slice 3

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_source_pass_slice3.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice3.py`

## Purpose

This slice extends the external source-pass program with fresh Cunning Man cases from later archive pages so the router can be tested on questions outside the already-audited education/train set.

This is still a source-pass slice, not a full replay slice.

## Cases Added

1. `Will the Scottish Government hold another independence referendum in 2022?`
2. `Will Boris Johnson survive the vote of no confidence?`
3. `Where is my lost watch?`
4. `Will Russia invade Ukraine, and when?`
5. `Is my thyroid medicine helping or harming me?`

## Results

Summary:

- fetched source-pass cases: `5`
- source-aligned router observations: `5`
- source-misaligned router observations: `0`

Aligned:

- `scottish_independence_2022_source_pass`
  - current router: `general`
  - houses: `[1, 9]`
  - status: aligned after foreign-state constitutional router pass

- `boris_vote_no_confidence_source_pass`
  - current router: `career`
  - houses: `[10, 7]`
  - status: aligned after public-office confidence router pass

- `where_is_my_watch_source_pass`
  - current router: `lost_object`
  - houses: `[1, 2]`
  - status: aligned with article doctrine

- `ukraine_invasion_timing_source_pass`
  - current router: `general`
  - houses: `[9, 11]`
  - status: aligned after foreign-state military router pass

- `thyroid_medicine_source_pass`
  - current router: `health`
  - houses: `[1, 6, 7, 10]`
  - status: aligned after treatment/medicine health router pass

## Interpretation

The previous router pass generalized correctly for higher education and short transit, and this slice now shows the next three doctrine families can also be corrected at the router level without disturbing earlier work.

The substantive changes were:

1. foreign-state constitutional questions now route `1/9`
2. foreign-state military action now routes `9/11`
3. public-office confidence questions now stay on the office-holder axis instead of being hijacked by `survive`
4. treatment/medicine questions now enter a health-treatment family with `1/6/7/10`

No verdict fixtures were repinned in this pass, because this was still a source-pass/router correction rather than a promoted replay slice.

## Verification

- `python -m pytest tests\\test_horary_cunning_man_slice3_rules.py tests\\test_horary_cunning_man_source_pass_slice3.py tests\\test_horary_book_health_rules.py tests\\test_horary_root_fixes.py -q`
  - result: `33 passed`
- `python -m pytest tests\\test_horary_question_corpus.py tests\\test_horary_book_examples_replay.py tests\\test_horary_cunning_man_source_pass_slice2.py -q`
  - result: `15 passed`

## Next Safe Step

Use the next fresh external slice to test the remaining out-of-family gaps, especially weather questions and medical-result/contact timing questions that were not yet promoted into this slice.
