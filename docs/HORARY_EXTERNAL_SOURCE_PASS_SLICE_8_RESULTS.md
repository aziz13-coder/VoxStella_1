# Horary External Source-Pass Slice 8

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice8.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice8.py`

## Purpose

This slice revisits turned-relative questions after the shared doctrine pass that was triggered by the earlier source-pass mismatch.

The goal here is to test whether the router can distinguish:

- a relative as the operative subject rather than the querent
- the turned matter belonging to that relative, such as her marriage or boyfriend
- a missing person's whereabouts and welfare from a lost-object chart

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will my sister get married this year?`
2. `Will my daughter be happy with her boyfriend?`
3. `Where is my Dad? Is he ok?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `sister_marriage_astrologyweekly_source_pass`
  - current router: `marriage`
  - houses: `[3, 9]`
  - status: aligned after turned-relative marriage pass

- `daughter_boyfriend_happiness_astrologyweekly_source_pass`
  - current router: `relationship`
  - houses: `[5, 11]`
  - status: aligned after turned-relative relationship pass

- `dad_whereabouts_health_skyscript_source_pass`
  - current router: `health`
  - houses: `[4, 9]`
  - status: aligned after person-whereabouts and welfare pass

## Interpretation

This slice is now fully aligned after a shared turned-relative doctrine pass.

What changed:

1. explicit relative subjects like `my daughter` and `my sister` now outrank later partner wording when choosing the operative subject house
2. relative marriage and relationship questions now turn from the relative's house instead of collapsing back to the querent axis
3. person-whereabouts questions now keep the person as subject, with welfare questions turning to the person's `6th` instead of being misrouted as `lost_object`

This was implemented as a reusable turned-relative doctrine family plus subject-inference tightening, not as a patch for the three probe titles.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice8.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice8_rules.py tests\\test_horary_external_source_pass_slice8.py tests\\test_horary_external_source_pass_slice7.py -q`
  - result: `10 passed`
- `python -m pytest tests\\test_horary_external_source_pass_slice7.py tests\\test_horary_external_source_pass_slice8.py tests\\test_horary_question_corpus.py -q`
  - result: `11 passed`

Runtime routing changes were made in this pass in the shared turned-relative doctrine layer.
