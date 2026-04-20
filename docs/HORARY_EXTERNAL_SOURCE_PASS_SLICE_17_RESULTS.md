# Horary External Source-Pass Slice 17

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice17.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice17.py`

## Purpose

This slice records the confinement doctrine pass for arrest, imprisonment, and release from prison.

The goal here was to test whether the router could distinguish:

- arrest as an authority-side question rather than a generic other-person chart
- imprisonment and jail as 12th-house confinement matters
- spouse or other-person release from prison without letting marriage wording swallow the confinement axis

This remains a source-pass slice, not a replay slice, but it now captures the post-fix aligned state.

## Cases Added

1. `Will I be arrested?`
2. `Will i be imprisoned?`
3. `Will my husband get out of prison sooner?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `will_i_be_arrested_source_pass`
  - current router: `general`
  - houses: `[1, 10]`
  - focus: arrest keeps the authority side visible on the `10th`

- `will_i_be_imprisoned_source_pass`
  - current router: `general`
  - houses: `[1, 12]`
  - focus: prisons and jail keep the `12th`-house confinement axis in view

- `husband_release_from_prison_source_pass`
  - current router: `general`
  - houses: `[1, 7, 12]`
  - focus: spouse release from prison keeps the spouse and confinement together rather than collapsing into marriage logic

## Interpretation

This slice is now a closed doctrine pass.

What changed in substance:

1. arrest now keeps the authority visible on the `10th`
2. prison and imprisonment now surface a shared `12th`-house confinement family
3. spouse or relative prison-release questions now keep the subject and confinement together
4. bounded subject matching prevents the old substring error where words like `imprisoned` could drift into a false turned-child inference

This was implemented as a shared confinement doctrine, not as a one-question patch.

## Sources

- [Astrology Weekly: Will I be arrested?](https://astrologyweekly.com/threads/will-i-be-arrested.148736/)
- [Astrology Weekly: Will i be imprisoned?](https://astrologyweekly.com/threads/will-i-be-imprisoned.114711/)
- [Astrology Weekly: 12th house matter: release from prison](https://astrologyweekly.com/threads/12th-house-matter-release-from-prison.68929/post-510952)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice17.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice17_rules.py tests\\test_horary_external_source_pass_slice17.py -q`
  - result: `6 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\confinement_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\confinement_doctrine.py`
  - result: `passed`

Runtime horary logic was changed in this step through the shared confinement doctrine pass.
