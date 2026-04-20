# Horary Cunning Man Source-Pass Slice 4

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_source_pass_slice4.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice4.py`

## Purpose

This slice probes the next external doctrine gaps after the foreign-state / confidence-vote / treatment pass. It focuses on:

- weather judged through an event/festival significator
- medical-result timing/contact questions
- one short-transit timing control

This remains a source-pass slice, not a reconstructed replay slice.

## Cases Added

1. `What will the weather be for Lughnasadh?`
2. `When will my COVID test result arrive?`
3. `What time will the train arrive?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `weather_lughnasadh_source_pass`
  - current router: `general`
  - houses: `[9]`
  - status: aligned after event-weather router pass

- `covid_test_result_timing_source_pass`
  - current router: `health`
  - houses: `[1, 7]`
  - status: aligned after medical-result contact router pass

- `train_arrive_v2_source_pass`
  - current router: `travel`
  - houses: `[1, 3]`
  - status: aligned with the article's short-transit doctrine

## Interpretation

This slice is now fully aligned after a shared router/doctrine pass, not a one-question patch.

The substantive changes were:

1. event/weather questions now judge the weather from the event significator instead of defaulting to generic `1/7`
2. religious festivals and holy-day weather questions now route through the `9th`
3. medical-result timing questions now stay in a health contact family rather than being hijacked by the education keyword `test`
4. the short-transit control continues to hold, confirming no regression in the earlier travel pass

## Verification

- `python -m pytest tests\\test_horary_cunning_man_source_pass_slice4.py -q`
  - result: `4 passed`
- `python -m pytest tests\\test_horary_cunning_man_slice4_rules.py tests\\test_horary_cunning_man_source_pass_slice4.py tests\\test_horary_cunning_man_source_pass_slice3.py tests\\test_horary_book_health_rules.py tests\\test_horary_root_fixes.py -q`
  - result: `33 passed`

Runtime routing changes were made in this slice in the shared analyzer/doctrine layer.
