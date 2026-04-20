# Horary External Source-Pass Slice 20

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice20.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice20.py`

## Purpose

This slice probes vehicle acquisition and sale questions.

The goal is to test whether the router can distinguish:

- buying a specific car that still belongs to a seller
- selling the querent's own car
- a turned-relative question about a partner buying a car

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Should I buy the car?`
2. `Will I be able to sell my car in July?`
3. `Will my partner buy a new car within a month?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `buy_specific_car_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 7, 8]`
  - shared fix: current routing now keeps the seller visible on the `7th` and the seller's possession axis for the car on the radical `8th`

- `sell_own_car_july_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[1, 3, 7]`
  - shared fix: current routing now keeps the querent's car explicitly visible on the `3rd` while still keeping the buyer or sale axis on the `7th`

- `partner_new_car_astrologyweekly_source_pass`
  - current router: `money`
  - houses: `[7, 8, 9]`
  - shared fix: partner wording no longer hijacks the chart into relationship routing; the partner remains operative with turned possession and vehicle houses in view

## Interpretation

This slice is now closed by a shared doctrine pass rather than a question-specific patch.

The shared vehicle doctrine now distinguishes three reusable families:

1. a specific car being bought from a seller keeps the seller and the seller's possession axis visible
2. the querent's own car being sold keeps the vehicle on the `3rd` and the buyer on the `7th`
3. turned-relative vehicle acquisition keeps the relative first and turns the possession or vehicle houses from that person

The pass also generalizes beyond the exact slice wording:

- generic first-person acquisition like `Should I get a car now?` now keeps `[1, 2, 3]`
- delivery questions like `When will my car be delivered?` stay on the delivery doctrine and are not hijacked by the new vehicle family

## Sources

- [Astrology Weekly: Should I buy the car](https://astrologyweekly.com/threads/should-i-buy-the-car.132163/)
- [Astrology Weekly: Will I be able to sell my car in July](https://astrologyweekly.com/threads/will-i-be-able-to-sell-my-car-in-july.154154/)
- [Astrology Weekly blog: Will my partner buy a new car within a month?](https://blog.astrologyweekly.com/weekly-horary/buy-new-car.php)

## Verification

- `python -m pytest tests\\test_horary_external_slice20_rules.py tests\\test_horary_external_source_pass_slice20.py -q`
  - result: `8 passed`
- `python -m pytest tests\\test_horary_external_slice20_rules.py tests\\test_horary_external_source_pass_slice20.py tests\\test_horary_external_source_pass_slice19.py tests\\test_horary_external_source_pass_slice8.py tests\\test_horary_external_source_pass_slice6.py tests\\test_horary_question_corpus.py -q`
  - result: `22 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\vehicle_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\vehicle_doctrine.py`
  - result: passed

Runtime horary logic changed in this step through a shared vehicle / automobile doctrine pass. This slice now records the aligned post-fix state.
