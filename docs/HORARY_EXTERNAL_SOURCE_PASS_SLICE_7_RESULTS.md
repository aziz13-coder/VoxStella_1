# Horary External Source-Pass Slice 7

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice7.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice7.py`

## Purpose

This slice moves to a different still-unprobed doctrine family: legal adjudication and court-battle routing.

The goal here is to test whether the router can distinguish:

- an ordinary court case from a generic opponent-only `1/7` chart
- an employment-related court battle from a simple money question
- an inheritance-rights court fight from a pure `8th`-house inheritance question

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I win the case?`
2. `Will I win the legal battle against my ex-employer?`
3. `Will I win the court battle for my inheritance rights?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `legal_case_astrologyweekly_source_pass`
  - current router: `lawsuit`
  - houses: `[1, 7, 10, 4]`
  - status: aligned after court-adjudication doctrine pass

- `ex_employer_legal_battle_astrologyweekly_source_pass`
  - current router: `lawsuit`
  - houses: `[1, 7, 10, 4]`
  - status: aligned after compensation-litigation guard against money hijack

- `inheritance_rights_court_battle_astrologyweekly_source_pass`
  - current router: `lawsuit`
  - houses: `[1, 7, 10, 4, 8]`
  - status: aligned after inheritance-litigation pass

## Interpretation

This slice is now fully aligned after a shared legal-adjudication doctrine pass.

What changed:

1. plain legal outcome questions now keep the `1/7/10/4` court axis in view
2. employment/compensation legal fights no longer collapse into `money`
3. inheritance-rights court battles no longer collapse into `death`; the `8th` now joins as subject matter while the legal axis remains primary
4. third-person appeal/hearing questions can turn the court axis instead of defaulting to a generic other-person chart

This was implemented as a reusable lawsuit doctrine family, not as a patch for the three probe titles.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice7.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice7_rules.py tests\\test_horary_external_source_pass_slice7.py tests\\test_horary_external_source_pass_slice6.py -q`
  - result: `10 passed`
- `python -m pytest tests\\test_horary_external_source_pass_slice5.py tests\\test_horary_external_source_pass_slice6.py tests\\test_horary_external_source_pass_slice7.py tests\\test_horary_question_corpus.py -q`
  - result: `14 passed`

Runtime routing changes were made in this pass in the shared lawsuit / court-adjudication doctrine layer.
