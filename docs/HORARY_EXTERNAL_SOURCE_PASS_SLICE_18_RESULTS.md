# Horary External Source-Pass Slice 18

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice18.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice18.py`

## Purpose

This slice records the inheritance doctrine pass for inheritance, estate distribution, and inheritance-rights disputes.

The goal here was to separate three closely related but not identical question forms:

- inheritance as a turned-person money or estate question
- inheritance of a specific house or estate property
- inheritance rights as a court-adjudication question

This remains a source-pass slice, not a replay slice, but it now records the post-fix aligned state.

## Cases Added

1. `Will I get the house inheritance?`
2. `Will my mother receive her inheritance?`
3. `Will I win the court battle for my inheritance rights?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `house_inheritance_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4, 8]`
  - focus: house inheritance now keeps the property axis visible alongside the estate axis

- `mother_inheritance_astrologyweekly_source_pass`
  - current router: `death`
  - houses: `[10, 5]`
  - focus: turned-person inheritance for the mother is already preserved correctly

- `inheritance_rights_litigation_astrologyweekly_source_pass`
  - current router: `lawsuit`
  - houses: `[1, 7, 10, 4, 8]`
  - focus: inheritance-rights litigation already keeps the court axis primary and the estate on the `8th`

## Interpretation

This slice is now a closed doctrine pass.

What changed in substance:

1. estate-property inheritance now keeps the `4th` visible when the inherited thing is a house, home, land, or other immovable property
2. ordinary inheritance transfer still stays on the turned `8th`
3. inheritance-rights litigation still remains lawsuit doctrine first, with the estate on the `8th` as subject matter

This was implemented as a shared inheritance doctrine, not as a single-question patch.

## Sources

- [Astrology Weekly: Will I get the house (inheritance)?](https://astrologyweekly.com/threads/will-i-get-the-house-inheritance.141513/)
- [Astrology Weekly: Inheritance Horary](https://astrologyweekly.com/threads/inheritance-horary.107174/)
- [Astrology Weekly: Will I win the court battle for my inheritance rights?](https://astrologyweekly.com/threads/will-i-win-the-court-battle-for-my-inheritance-rights.146199/)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice18.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice18_rules.py tests\\test_horary_external_source_pass_slice18.py tests\\test_horary_external_source_pass_slice17.py -q`
  - result: `10 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\inheritance_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\inheritance_doctrine.py`
  - result: `passed`

Runtime horary logic was changed in this step through the shared inheritance doctrine pass.
