# Horary External Source-Pass Slice 10

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice10.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice10.py`

## Purpose

This slice revisits repayment, refund, and reimbursement routing after the shared doctrine pass that was triggered by the earlier source-pass mismatch.

The goal here is to test whether the router can distinguish:

- lent money owed back by a friend from simple friend-contact questions
- refund from an educational institution from generic funding language
- tax refund from the government from generic funding language

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I get back my money from my friend?`
2. `Will I get a refund from the college?`
3. `When will I receive my tax refund?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `friend_money_back_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 11, 2]`
  - status: aligned after friend repayment pass

- `college_refund_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 9, 10]`
  - status: aligned after institutional refund pass

- `tax_refund_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 10, 11]`
  - status: aligned after government refund pass

## Interpretation

This slice is now fully aligned after a shared repayment / refund / reimbursement doctrine pass.

What changed:

1. repayment and refund wording now triggers a dedicated economic doctrine family before communication or generic funding heuristics
2. friend repayment questions now keep the friend as the counterparty while preserving the querent's money as the thing to be recovered
3. college and government refunds now turn to the institution's own money instead of collapsing into generic funding
4. insurance claim reimbursement now also generalizes through the contracting counterparty axis

This was implemented as a reusable reimbursement doctrine family, not as a patch for the three probe titles.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice10.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_source_pass_slice9.py tests\\test_horary_external_source_pass_slice10.py -q`
  - result: `6 passed`
- `python -m pytest tests\\test_horary_external_slice10_rules.py tests\\test_horary_external_source_pass_slice10.py tests\\test_horary_external_source_pass_slice9.py -q`
  - result: `10 passed`

Runtime routing changes were made in this pass in the shared repayment and reimbursement doctrine layer.
