# Horary External Source-Pass Slice 5

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice5.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice5.py`

## Purpose

This slice is a mixed external source-pass probe used to test whether the newer weather-event and medical-result contact routing generalizes beyond the exact wording of the Cunning Man cases.

The sources here are mixed on purpose:

- Skyscript forum discussion for wedding weather
- Reddit horary doctrine discussion for secular event weather
- Reddit horary timing chart for medical-result arrival

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `What will the weather be for the wedding?`
2. `What will the weather be for the garden party?`
3. `When will the medical test result arrive?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `weather_wedding_skyscript_source_pass`
  - current router: `general`
  - houses: `[7]`
  - status: aligned with marriage-event weather routing

- `medical_result_arrive_reddit_source_pass`
  - current router: `health`
  - houses: `[1, 7]`
  - status: aligned with the medical-result contact family

- `weather_garden_party_reddit_source_pass`
  - current router: `general`
  - houses: `[5]`
  - status: aligned after secular celebration-event weather router pass

## Interpretation

This slice now shows full generalization across the mixed external probe.

What held:

1. marriage-event weather routing via the `7th`
2. medical-result arrival routing as a health contact question on `[1, 7]`
3. secular celebration-event weather routing via the `5th`

The substantive addition in this pass was a reusable celebration-event weather family. The weather is now judged from the event lord for parties and similar social celebrations instead of falling back to generic `1/7`.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice5.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_cunning_man_slice4_rules.py tests\\test_horary_external_source_pass_slice5.py tests\\test_horary_cunning_man_source_pass_slice4.py tests\\test_horary_cunning_man_source_pass_slice3.py -q`
  - result: `17 passed`

Runtime routing changes were made in this pass in the shared event-weather doctrine layer.
