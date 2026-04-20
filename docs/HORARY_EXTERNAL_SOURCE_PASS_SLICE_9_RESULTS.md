# Horary External Source-Pass Slice 9

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice9.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice9.py`

## Purpose

This slice revisits theft and stolen-item routing after the shared doctrine pass that was triggered by the earlier source-pass mismatch.

The goal here is to test whether the router can distinguish:

- plain money-loss or missing-object questions from explicit theft suspicion
- the thief on the `7th` from the item on the `2nd`
- the other party's possession or profit from the theft when the question is about stolen money

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Did my coworker steal the money?`
2. `Was my wallet stolen?`
3. `Was the laptop stolen at work?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `coworker_steal_money_skyscript_source_pass`
  - current router: `money`
  - houses: `[1, 2, 7, 8]`
  - status: aligned after suspected-money-theft pass

- `wallet_stolen_astrologyweekly_source_pass`
  - current router: `lost_object`
  - houses: `[1, 2, 7]`
  - status: aligned after stolen-object theft pass

- `laptop_stolen_at_work_astrologyweekly_source_pass`
  - current router: `lost_object`
  - houses: `[1, 2, 7]`
  - status: aligned after stolen-object theft pass

## Interpretation

This slice is now fully aligned after a shared theft / stolen-item doctrine pass.

What changed:

1. explicit theft wording now triggers a dedicated theft doctrine family before generic lost-object or possession heuristics
2. stolen-money charts keep the querent's money on the `2nd`, the thief on the `7th`, and the thief's possession on the `8th`
3. stolen-object charts keep the item on the `2nd` while still surfacing the thief on the `7th`
4. plain thief-identification questions now stay cleanly on the `1st/7th` axis

This was implemented as a reusable theft doctrine family, not as a patch for the three probe titles.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice9.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_source_pass_slice8.py tests\\test_horary_external_source_pass_slice9.py -q`
  - result: `6 passed`
- `python -m pytest tests\\test_horary_external_slice9_rules.py tests\\test_horary_external_source_pass_slice9.py tests\\test_horary_external_source_pass_slice8.py -q`
  - result: `9 passed`

Runtime routing changes were made in this pass in the shared theft doctrine layer.
