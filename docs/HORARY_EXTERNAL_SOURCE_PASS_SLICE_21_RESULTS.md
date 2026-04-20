# Horary External Source-Pass Slice 21

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice21.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice21.py`

## Purpose

This slice probes citizenship, permanent residence, and green-card approval questions.

The goal is to test whether the router can distinguish:

- first-person citizenship timing
- permanent-resident status as an immigration authorization
- a turned-relative green-card approval question

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `When will I get my citizenship?`
2. `When will i get permanent resident?`
3. `When will my husband's green card be approved?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `citizenship_timing_astrologyweekly_source_pass`
  - current router: `travel`
  - houses: `[1, 9, 10]`
  - fix: citizenship now stays in a shared immigration-status family, with the status on the `9th` and the approving authority on the `10th`

- `permanent_resident_status_astrologyweekly_source_pass`
  - current router: `travel`
  - houses: `[1, 9, 10]`
  - fix: permanent residence is now treated as a foreign-status authorization rather than a generic other-person question

- `husband_green_card_astrologyweekly_source_pass`
  - current router: `travel`
  - houses: `[7, 3, 4]`
  - fix: the husband is now the operative subject, so the green card and authority are correctly turned from him

## Interpretation

This slice confirms a real family-level fix, not a title patch.

The shared doctrine now does three things:

1. citizenship and permanent-resident status are treated as immigration-status authorizations in their own right
2. communication-style `get` or `hear back` wording no longer hijacks those charts away from the immigration family
3. turned-relative green-card approval now turns the status and authority houses from the operative subject

So slice 21 is now closed as a routing gap.

## Sources

- [Astrology Weekly: When will I get my citizenship](https://astrologyweekly.com/threads/when-will-i-get-my-citizenship.61547/)
- [Astrology Weekly: When will i get permanent resident](https://astrologyweekly.com/threads/when-will-i-get-permanent-resident.30240/)
- [Astrology Weekly: When will my husband's green card be approved](https://astrologyweekly.com/threads/when-will-my-husbands-green-card-be-approved.64921/)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice21.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice21_rules.py tests\\test_horary_external_source_pass_slice21.py tests\\test_horary_external_source_pass_slice13.py tests\\test_horary_question_intent_labels.py -q`
  - result: `15 passed`

Runtime horary logic changed in this step through the shared citizenship / residency-status doctrine pass.
