# Horary External Source-Pass Slice 15

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice15.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice15.py`

## Purpose

This slice moves to another still-unprobed doctrine family: surgery, medical procedures, and cosmetic operations.

The goal here is to test whether the router can distinguish:

- ordinary health and illness questions
- a doctor or surgeon as the operative other party
- surgery or operation as its own procedural matter
- cosmetic surgery as an appearance-and-cost question rather than a normal illness chart

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will I go for the full face lift?`
2. `Will the operation go smoothly?`
3. `Big surgery, yes or no?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `full_face_lift_cosmetic_surgery_source_pass`
  - current router: `general`
  - houses: `[1, 2]`
  - status: cosmetic surgery now keeps appearance and cost in view instead of falling to generic `1/7`

- `operation_go_smoothly_source_pass`
  - current router: `health`
  - houses: `[1, 6, 7, 8]`
  - status: operation questions now keep patient, illness, doctor, and surgery together, and the old pet false positive is gone

- `big_surgery_yes_no_source_pass`
  - current router: `health`
  - houses: `[1, 6, 7, 8]`
  - status: major surgery questions now stay inside a shared medical-procedure family

## Interpretation

This slice is now fully aligned after a shared surgery / procedure doctrine pass.

What changed:

1. surgery and operation wording now triggers a shared medical-procedure family instead of generic occurrence logic
2. the pet false positive on `operation` is fixed at the classifier level by using bounded pet matching rather than raw substring matching
3. cosmetic surgery questions now use a separate appearance-and-cost branch instead of being treated as either illness or generic other-party questions

## Sources

- [Skyscript: Cosmetic Surgery question, which house?](https://skyscript.co.uk/forums/viewtopic.php?t=5059)
- [Wroskopos: Will the operation go smoothly?](https://wroskopos.wordpress.com/2010/03/31/will-the-operation-go-smoothly/)
- [Astrology Weekly: Big surgery, yes or no?](https://astrologyweekly.com/threads/big-surgery-yes-or-no.153043/latest)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice15.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice15_rules.py tests\\test_horary_external_source_pass_slice15.py -q`
  - result: `7 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\surgery_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\surgery_doctrine.py`
  - result: `passed`

Runtime routing changes were made in this pass in the shared surgery / procedure doctrine layer.

## Doctrine-Only Strengthening

Because `operation_go_smoothly_source_pass` is still source-pass rather than replay, the doctrine-only assertions were strengthened after the initial slice pass.

The current tests now explicitly assert, for the surgery/procedure family:

- `surgery_family = medical_procedure`
- patient on the `1st`
- illness on the `6th`
- doctor on the `7th`
- procedure on the `8th`
- quesited house remains the procedure house
- the doctrine text explicitly keeps patient, illness, practitioner, and surgery together
- the old pet false positive stays absent

So this case is still not a full judgment replay, but it is no longer just a loose houses-only alignment check.
