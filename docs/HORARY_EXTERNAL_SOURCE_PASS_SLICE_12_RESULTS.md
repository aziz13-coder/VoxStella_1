# Horary External Source-Pass Slice 12

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice12.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice12.py`

## Purpose

This slice moves to a different still-unprobed doctrine family: loans and borrowing questions.

The goal here is to test whether the router can distinguish:

- generic loan or borrowing questions from general money questions
- named bank or lender questions from anonymous borrowing questions
- the core 8th-house borrowing axis from the explicit 7th-house counterparty axis

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I get the loan I applied for?`
2. `Will my bank loan be approved?`
3. `Will I recieve the loan I deperatley need?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `loan_applied_for_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 8]`
  - status: generic borrowing wording already stays on the querent / other-people's-money axis

- `loan_desperately_need_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 8]`
  - status: generic borrowing or financial-assistance wording also stays on the querent / other-people's-money axis

- `bank_loan_approved_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 7, 8]`
  - status: aligned after shared loan/lender pass keeps the named bank as the counterparty in the 7th and the loan itself on the 8th

## Interpretation

This slice is now fully aligned after a shared loan / lender doctrine pass.

What changed:

1. named bank or lender wording now keeps the counterparty explicitly in the `7th`
2. the loan itself remains in the `8th` as other people's money
3. generic unnamed borrowing questions still stay on the simpler `1/8` axis
4. hostile bank questions such as foreclosure remain on the `1/7` counterparty route instead of being confused with loan approval
5. source-pass fixture intent labels were later cleaned from the stale catch-all `REUNION` wording to the broader `OCCURRENCE / QUALITY / SAFETY` vocabulary; the slice-12 loan cases now pin as `OCCURRENCE`

This was implemented as a reusable loan/lender doctrine family, not as a patch for one bank-loan title.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice12.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_source_pass_slice11.py tests\\test_horary_external_source_pass_slice12.py -q`
  - result: `6 passed`
- `python -m pytest tests\\test_horary_external_slice12_rules.py tests\\test_horary_external_source_pass_slice12.py tests\\test_horary_root_fixes.py -q`
  - result: `23 passed`
- `python -m pytest tests\\test_horary_external_source_pass_slice11.py tests\\test_horary_external_source_pass_slice12.py tests\\test_horary_question_corpus.py -q`
  - result: `11 passed`
- `python -m py_compile backend\\horary_engine\\economic_doctrine.py backend\\question_analyzer.py frontend\\backend\\horary_engine\\economic_doctrine.py frontend\\backend\\question_analyzer.py`
  - result: `passed`

Runtime routing changes were made in this pass in the shared loan/lender doctrine layer.
