# Horary External Source-Pass Slice 6

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice6.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice6.py`

## Purpose

This slice moves to a different still-unprobed doctrine family: communication and delivery timing.

The goal here is to test whether the router can distinguish:

- a friend as `11th`-house contact rather than a generic `7th`
- a message as a 3rd-house communication object inside a relationship/contact question
- delivered goods arriving home as a logistics/delivery problem rather than only a simple property/home question

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I hear from my friend?`
2. `Has he received my message?`
3. `When will the goods arrive at home?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `hear_from_friend_skyscript_source_pass`
  - current router: `friend_enemy`
  - houses: `[1, 11]`
  - status: aligned after friend-contact router pass

- `received_message_skyscript_source_pass`
  - current router: `general`
  - houses: `[1, 7, 3]`
  - status: aligned after message-receipt router pass

- `goods_arrive_home_skyscript_source_pass`
  - current router: `money`
  - houses: `[1, 2, 4, 6, 8]`
  - status: aligned after delivery-arrival router pass

## Interpretation

This slice is now fully aligned after a shared communication/delivery doctrine pass.

The substantive changes were:

1. friend-contact questions now keep the friend on the `11th`
2. message-receipt questions now surface the `3rd` house for the communication itself
3. delivery-arrival questions now use a logistics family that keeps goods, home, courier, and others-in-possession in view

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice6.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice6_rules.py tests\\test_horary_external_source_pass_slice6.py tests\\test_horary_external_source_pass_slice5.py tests\\test_horary_cunning_man_source_pass_slice4.py tests\\test_horary_question_corpus.py -q`
  - result: `19 passed`

Runtime routing changes were made in this pass in the shared communication/delivery doctrine layer.
