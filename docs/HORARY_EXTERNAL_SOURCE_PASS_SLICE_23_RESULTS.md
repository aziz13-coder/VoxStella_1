# Horary External Source-Pass Slice 23

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice23.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice23.py`

## Purpose

This slice probes passport and official travel-document questions.

The goal is to test whether the router can distinguish:

- passports arriving or being delivered to the querent
- passports as documents rather than as an education or exam question
- passport renewal approval as a travel-document authorization

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will the passports be here on time?`
2. `Will I get the passports in 3days?`
3. `Will my Passport Renewal be Approved?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `passport_arrive_on_time_astrologyweekly_source_pass`
  - current router: `general`
  - houses: `[1, 3]`
  - note: passport arrival now routes as a document-receipt question instead of an education false positive

- `passports_in_three_days_astrologyweekly_source_pass`
  - current router: `general`
  - houses: `[1, 3]`
  - note: waiting for passports now keeps the papers on the `3rd` as documents

- `passport_renewal_approved_astrologyweekly_source_pass`
  - current router: `travel`
  - houses: `[1, 9, 10]`
  - note: passport renewal approval now stays on the travel-document authorization axis

## Interpretation

This slice confirms a real doctrine-level fix rather than a keyword patch.

The shared passport doctrine now distinguishes:

1. passport arrival or receipt as a document question on the `3rd`
2. passport renewal or approval as a travel-document authorization on the `9th` with authority on the `10th`
3. real passport wording from accidental education matches caused by the `pass` substring

So slice 23 is now closed as a routing gap.

## Sources

- [Astrology Weekly: Passport help](https://astrologyweekly.com/threads/passport-help.140237/post-1128172)
- [Astrology Weekly: The passports!](https://astrologyweekly.com/threads/the-passports.129913/)
- [Astrology Weekly: Will my Passport Renewal be Approved?](https://astrologyweekly.com/forums/horary-questions-on-traveling-moving-relocation.49/page-22)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice23.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice23_rules.py tests\\test_horary_external_source_pass_slice23.py tests\\test_horary_external_source_pass_slice13.py tests\\test_horary_question_intent_labels.py -q`
  - result: `15 passed`

Runtime horary logic changed in this step through the shared passport / travel-document doctrine pass.
