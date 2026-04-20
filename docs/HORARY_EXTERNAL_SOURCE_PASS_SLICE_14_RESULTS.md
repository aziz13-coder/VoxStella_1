# Horary External Source-Pass Slice 14

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice14.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice14.py`

## Purpose

This slice moves to another still-unprobed doctrine family: custody and family-court questions.

The goal here is to test whether the router can distinguish:

- a child or children as the substantive matter
- the opposing parent or claimant
- the family-court judge or authority
- the end of the matter or final custody disposition

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I win back custody of my kids?`
2. `Will my husband get custody of his child?`
3. `Will he succeed in taking the children?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `win_back_custody_of_kids_source_pass`
  - current router: `lawsuit`
  - houses: `[1, 7, 5, 10, 4]`
  - status: self-custody disputes now keep the child, implicit opposing parent, judge, and family-court outcome together

- `husband_get_custody_of_his_child_source_pass`
  - current router: `children`
  - houses: `[7, 11]`
  - status: turned-relative custody now keeps the husband on the `7th` and his child on the turned `5th`, or radical `11th`

- `child_custody_again_source_pass`
  - current router: `lawsuit`
  - houses: `[1, 7, 5, 10, 4]`
  - status: opponent-led custody disputes now keep the opponent, child, judge, and family-court disposition together

## Interpretation

This slice is now fully aligned after a shared custody / family-court doctrine pass.

What changed:

1. custody disputes now keep the child axis and family-court axis together instead of collapsing into `children` alone
2. turned-relative custody questions no longer get hijacked by marriage wording
3. opponent-led custody threats now keep the opposing parent, child, judge, and final outcome together in one reusable structure

This was implemented as a reusable custody doctrine family, not as a patch for one custody title.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice14.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice14_rules.py tests\\test_horary_external_source_pass_slice14.py -q`
  - result: `6 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\custody_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\custody_doctrine.py`
  - result: `passed`

Runtime routing changes were made in this pass in the shared custody / family-court doctrine layer.
