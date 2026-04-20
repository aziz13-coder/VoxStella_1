# Horary External Source-Pass Slice 24

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice24.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice24.py`

## Purpose

This slice probes roommate and cohabitation questions.

The goal is to test whether the router can distinguish:

- a roommate as a person sharing the home by agreement
- a doctrine question about which house signifies a roommate
- moving in together as a cohabitation question rather than bare relationship only

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Where is my roommate?`
2. `What house for a roommate?`
3. `Should we move in together?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `where_is_my_roommate_astrologyweekly_source_pass`
  - current router: `general`
  - houses: `[1, 7]`
  - note: roommate whereabouts now stay on the 7th as a person-sharing-home question, not a lost-object chart

- `what_house_for_roommate_astrologyweekly_source_pass`
  - current router: `general`
  - houses: `[1, 7]`
  - note: roommate doctrine questions now surface the roommate as the operative 7th-house person

- `should_we_move_in_together_astrologyweekly_source_pass`
  - current router: `relationship`
  - houses: `[1, 7, 4]`
  - note: cohabitation questions now keep the relationship axis together with the 4th-house home

## Interpretation

This slice confirms a real doctrine-level fix rather than a wording patch.

The shared roommate / cohabitation doctrine now does three distinct jobs:

1. roommate whereabouts are judged as a person-sharing-home question, not as a possession
2. doctrine questions about roommates keep the roommate on the 7th
3. moving in together keeps the 4th-house home axis alongside the relationship axis

So slice 24 is now closed as a routing gap.

## Sources

- [Astrology Weekly: Where is my roommate?](https://astrologyweekly.com/threads/where-is-my-roommate.132438/)
- [Astrology Weekly: What house for a roommate?](https://astrologyweekly.com/threads/what-house-for-a-roommate.25695/)
- [Astrology Weekly: Should we move in together?](https://astrologyweekly.com/threads/should-we-move-in-together.17388/)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice24.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice24_rules.py tests\\test_horary_external_source_pass_slice24.py tests\\test_horary_external_source_pass_slice23.py -q`
  - result: `15 passed`

Runtime horary logic changed in this step through the shared roommate / cohabitation doctrine pass.
