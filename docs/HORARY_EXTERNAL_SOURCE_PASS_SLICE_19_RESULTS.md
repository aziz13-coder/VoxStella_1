# Horary External Source-Pass Slice 19

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice19.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice19.py`

## Purpose

This slice probes grants, scholarships, and public financial aid.

The goal is to test whether the router can distinguish:

- higher education with scholarship eligibility
- a turned-relative scholarship question
- public financial aid or government support

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I be accepted for masters scholarship?`
2. `Will he be granted a scholarship?`
3. `Will I get the financial aid?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `masters_scholarship_astrologyweekly_source_pass`
  - current router: `education`
  - houses: `[1, 9, 2]`
  - shared fix: higher education stays primary on the `9th`, with income or eligibility visible on the `2nd`

- `brother_scholarship_astrologyweekly_source_pass`
  - current router: `education`
  - houses: `[3, 11]`
  - shared fix: the brother remains the operative subject on the `3rd`, and his turned `9th` scholarship axis lands on the radical `11th`
  - note: the fixture wording now preserves the source's explicit brother context instead of reducing the question to a bare pronoun

- `financial_aid_astrologyweekly_source_pass`
  - current router: `funding`
  - houses: `[1, 10]`
  - shared fix: public financial aid now keeps the official or government support axis on the `10th`

## Interpretation

This slice is now closed by a real doctrine pass, not a local example patch.

The shared aid doctrine now separates three reusable families:

1. scholarship questions tied to higher education keep the `9th` primary, with the `2nd` joining only when eligibility or means are materially part of the question
2. turned-relative scholarship questions preserve the relative first, then turn the higher-education house from that subject
3. public or government aid keeps the official or state funder visible on the `10th` instead of collapsing into the querent's money alone

So the result of this pass is:

- a shared scholarship / grant / public-aid doctrine family
- education-first, turned-relative, and official-funder variants kept distinct
- slice 19 promoted from open router gap to aligned source-pass coverage

## Sources

- [Astrology Weekly: will i be accepted for masters scholarship](https://astrologyweekly.com/threads/will-i-be-accepted-for-masters-scholarship.70538/)
- [Astrology Weekly: Grant for a scholarship?](https://astrologyweekly.com/threads/grant-for-a-scholarship.14045/)
- [Astrology Weekly: Will I get the financial aid?](https://astrologyweekly.com/threads/will-i-get-the-financial-aid.134185/)

## Verification

- `python -m pytest tests\\test_horary_external_slice19_rules.py tests\\test_horary_external_source_pass_slice19.py -q`
  - result: `6 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\aid_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\aid_doctrine.py`
  - result: passed

Runtime horary logic changed in this step through a shared aid doctrine pass. This slice now records the post-fix aligned state.
