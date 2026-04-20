# Horary Book Examples Phase 5/6 Results

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Baseline replay note:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_PHASE_3_4_RESULTS.md`

## Goal

Phase 5/6 was meant to fix rule-level faults exposed by the first 10 replayed book cases without making chart-specific patches and without breaking Astro Clock or other shared horary consumers.

The main target classes were:

- wrong category family selection
- wrong primary houses
- wrong turned-house targets
- wrong quesited-house resolution inside the engine after analysis
- unsafe occurrence logic for hostile bank/counterparty questions

## Source Changes Implemented

### 1. Economic doctrine routing

Added:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\economic_doctrine.py`

This new doctrine helper classifies narrow money/work families before the generic transaction rules can flatten them.

Implemented families:

- `career_review`
- `tenant_payment`
- `bet_profit`
- `business_start`
- `business_profit`
- `bank_counterparty`

This fixed the main route errors in:

- yearly review
- tenant payment
- profit-from-bet
- business-profit
- bank foreclosure

### 2. Property doctrine expansion

Updated:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\property_doctrine.py`

New or corrected property families:

- `friend_house_move`
- `rental_acquisition`
- improved `advisability_profit`
- improved `acquisition`

This fixed the route logic for:

- friend's house turned to the 11th
- property purchase/advisability through 4th and 10th
- rental questions keeping both current holder and property in frame

### 3. Analyzer routing fixes

Updated:

- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`

Core fixes:

- high-priority economic-family detection before generic money routing
- property purchase/rental/friend-house detection before generic transaction routing
- possession logic no longer swallows real-estate questions
- removed generic keyword-based house pollution that was adding irrelevant houses like the 6th to career-review questions
- explicit `quesited_house` support for economic and property families

### 4. Resolver precedence fix

Updated:

- `C:\Users\sabaa\Downloads\codexhorary\backend\taxonomy.py`

Root fix:

- explicit `significator_info["quesited_house"]` now takes precedence over blindly using the second house in `manual_houses`

This matters because many correct book routes need:

- more than two houses in the analysis
- but only one of them is the true quesited house

Without this fix, the analyzer could be right and the judgment engine could still revert to the wrong target.

### 5. Hostile bank-counterparty doctrine fix

Updated:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\economic_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

Implemented narrow family-local logic for foreclosure-style questions:

- strong reception between querent and bank can indicate accommodation/settlement
- indirect perfection by collection/translation should not automatically be read as the feared hostile act
- a weak/cadent bank significator counts against the hostile action

This corrected `Will the Bank Foreclose?` from a false `YES` to a doctrinally safer `NO`.

## Replay Results After Phase 5/6

First 10-case replay slice status:

- total replay cases: `10`
- source-aligned cases: `9`
- remaining disagreement cases: `1`

Now source-aligned:

- `will_i_get_a_good_yearly_review_of_my_work`
- `will_my_tenant_send_full_payment`
- `will_i_get_the_job_at_uw`
- `will_i_profit_from_this_bet`
- `should_i_start_this_business`
- `will_investing_in_this_business_prove_profitable_for_me`
- `will_the_bank_foreclose`
- `should_i_move_to_my_friends_house`
- `should_i_buy_this_flat`

Remaining disagreement:

- `will_we_rent_the_house`

## What The Remaining Disagreement Means

`Will We Rent the House?` is no longer failing because of the simple routing problems from Phase 3/4.

After the fixes:

- category is now `property`
- route is now `[1, 7, 4]`
- the engine now judges the property through `L4`

What still remains missing is the book's deeper chained-state logic:

- the sale is effectively already completed
- the new-owner layer matters
- that altered ownership state is what allows the later rental outcome

This is not another safe analyzer tweak. It is a deeper event-state problem and should stay manual-review only until a broader doctrine pass is done.

## Tests Added Or Strengthened

Added:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_phase56_rules.py`

Updated:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`

What these now protect:

- corrected analyzer routing for the phase 5 families
- resolver precedence for explicit `quesited_house`
- book replay alignment across the first 10-case slice
- one explicit remaining disagreement instead of many hidden route errors

Frontend safety already remained intact because the book parity tests and horary normalization tests do not reinterpret the backend verdict.

## Verification Performed

Backend:

- replay probe run in WSL backend environment against the 10-case book slice
- post-fix result: `9/10` source-aligned

Frontend:

- `cmd /c npx vitest run src/tests/horaryBookExamplesParity.test.mjs src/tests/normalizeHoraryApiResult.test.mjs src/tests/astroclockApi.test.mjs --config vitest.config.mjs`
- result: `18 passed`

## Safe Next Step

Do not force `will_we_rent_the_house` to `YES`.

The safe next phase is:

1. study the book's chained sale/new-owner logic in detail
2. model ownership-transfer state as a doctrine layer
3. add it only if it can be expressed as a reusable rule family
4. rerun book replay plus Astro Clock/shared horary regressions
