# Horary External Source-Pass Slice 11

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice11.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice11.py`

## Purpose

This slice moves to a different still-unprobed doctrine family: property transition questions.

The goal here is to test whether the router can distinguish:

- moving house from generic travel
- buying a house from generic money or transaction logic
- selling a house from generic money or transaction logic

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will we move house?`
2. `Will we buy a new house?`
3. `Will we sell the house soon?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `move_house_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4]`
  - status: move-house wording already stays on the home axis

- `buy_new_house_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4, 7]`
  - status: aligned after shared property-transition pass keeps the house in the 4th and the seller or contracting counterparty in the 7th

- `sell_house_soon_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4, 7]`
  - status: aligned after shared property-transition pass keeps the house in the 4th and the buyer or contracting counterparty in the 7th

## Interpretation

This slice is now fully aligned after a shared property-transition doctrine pass.

What changed:

1. buy and sell phrasing with explicit house/property nouns now routes as `property` before generic money logic can take over
2. house acquisition questions now keep the house in the `4th` and the other contracting party in the `7th`
3. house sale questions now keep the same property/counterparty axis instead of flattening into generic transaction routing
4. property advisability questions now keep the `4th`, `7th`, and `10th` in view rather than dropping the counterparty side

This was implemented as a reusable property-transition pass, not as a patch for the three probe titles.

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice11.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice11_rules.py tests\\test_horary_external_source_pass_slice11.py tests\\test_property_doctrine_pass.py -q`
  - result: `11 passed`
- `python -m pytest tests\\test_property_doctrine_pass.py tests\\test_horary_external_slice11_rules.py tests\\test_horary_external_source_pass_slice11.py tests\\test_horary_external_source_pass_slice10.py -q`
  - result: `14 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\property_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\property_doctrine.py`
  - result: `passed`

Runtime routing changes were made in this pass in the shared property doctrine and router precedence layer.
