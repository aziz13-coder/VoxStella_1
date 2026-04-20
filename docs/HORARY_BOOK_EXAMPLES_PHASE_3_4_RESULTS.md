# Horary Book Examples Phase 3/4 Results

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`

Primary book source:
`C:\Users\sabaa\Downloads\Horary Examples Traditional Horary Astrology By Example ( etc.) (z-library.sk, 1lib.sk, z-lib.sk).epub`

## What Was Implemented

Phase 3 and Phase 4 are now implemented for a first deterministic replay slice.

Artifacts added:

- replay fixture:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`
- backend replay helper:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\horary_book_examples_utils.py`
- backend replay tests:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- frontend parity tests:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`

The replay fixture records both:

- the book's expected route:
  - category
  - question family
  - primary houses
  - secondary houses when relevant
  - significator summary
  - expected verdict
- the current engine's observed route:
  - category
  - verdict
  - perfection type
  - relevant houses
  - significator houses
  - key reasoning snippets

This is deliberate. It lets Phase 5/6 target the actual faulty rule instead of flattening everything into a simple `YES/NO` comparison.

## Implemented Replay Slice

The first replay slice contains `10` cases from `Money & Jobs` and `Housing`:

- `Will I Get a Good Yearly Review of My Work?`
- `Will My Tenant Send Full Payment?`
- `Will I Get the Job at UW?`
- `Will I Profit from This Bet?`
- `Should I Start This Business?`
- `Will Investing in This Business Prove Profitable for Me?`
- `Will the Bank Foreclose?`
- `Should I Move to My Friend’s House?`
- `Should I Buy This Flat?`
- `Will We Rent the House?`

## Replay Results Summary

Header reconstruction:

- all `10/10` selected cases reproduced the book ascendant sign
- all `10/10` selected cases reproduced the ascendant degree within `1.2°`

This means the stored city coordinates are good enough for deterministic replay of this first slice.

Alignment summary:

- `2/10` cases are currently source-aligned at the primary route level
- `6/10` cases match the book verdict direction but not the route/houses/significators
- `2/10` cases disagree with the book verdict itself

Source-aligned cases:

- `will_i_get_the_job_at_uw`
- `should_i_start_this_business`

Verdict-aligned but route-misaligned cases:

- `will_i_get_a_good_yearly_review_of_my_work`
- `will_my_tenant_send_full_payment`
- `will_i_profit_from_this_bet`
- `will_investing_in_this_business_prove_profitable_for_me`
- `will_the_bank_foreclose`
- `should_i_buy_this_flat`

Verdict-disagreement cases:

- `should_i_move_to_my_friends_house`
- `will_we_rent_the_house`

## What These Results Mean

The first replay slice confirms that many present horary weaknesses are not simple polarity bugs.

Most mismatches are route-selection faults:

- right `NO`, wrong reason
- right `NO`, wrong houses
- right `NO`, wrong significators
- right category family, but wrong turned-house structure

This is exactly the type of issue that should be fixed in Phase 5/6. It is safer than flipping answers, and it is more likely to improve the whole engine.

## Phase 5/6 Targets Exposed By This Slice

### 1. Career Review vs 6th-House Work Routing

Example:

- `will_i_get_a_good_yearly_review_of_my_work`

Observed problem:

- the engine returned the correct `YES`
- but it routed the quesited through the `6th` instead of keeping the superior/review question anchored in the `10th`

Implication:

- career-review questions need a clearer rule for when the superior/judge/boss is `10th`, not generic `6th-house work`

### 2. Tenant / Tenant's Money Turning

Example:

- `will_my_tenant_send_full_payment`

Observed problem:

- the engine returned the correct `NO`
- but it treated the case like a self-money question

Implication:

- landlord/tenant payment questions need explicit turning:
  - tenant as `7th`
  - tenant's money as turned `2nd` from `7th`
  - querent's account/receipt path as secondary layer

### 3. Betting / Winnings Logic

Example:

- `will_i_profit_from_this_bet`

Observed problem:

- the engine returned the correct `NO`
- but it kept the quesited on `2nd-house` money instead of treating winnings as money coming from the bookmaker/opponent side

Implication:

- betting/profit-from-bet questions need a dedicated winnings rule, likely centering `8th` and/or the opponent/bookmaker money stream

### 4. Business Investment Profit Routing

Example:

- `will_investing_in_this_business_prove_profitable_for_me`

Observed problem:

- the engine returned the correct `NO`
- but routed through `4th-house` property/asset logic instead of business `10th` and business profit `11th`

Implication:

- business investment questions need a local category rule:
  - business = `10th`
  - business profit = `11th`
  - partner = `7th` when central

### 5. Bank / Contracting Counterparty Routing

Example:

- `will_the_bank_foreclose`

Observed problem:

- the engine returned the correct `NO`
- but treated the bank like a `2nd-house` money layer instead of a `7th-house` contracting party

Implication:

- foreclosure/refinancing questions need explicit contracting-party logic

### 6. Property Purchase Advisability

Example:

- `should_i_buy_this_flat`

Observed problem:

- the engine returned the correct `NO`
- but judged the flat through a `7th-house` counterparty frame instead of:
  - property condition = `4th`
  - price/value = `10th`

Implication:

- property advisability needs stronger category-local rules, even when a seller exists in the background

### 7. Friend's House Turning

Example:

- `should_i_move_to_my_friends_house`

Observed problem:

- the engine currently says `NO`
- the book says `YES`
- the engine used the radical `4th`, while the book explicitly uses the friend's house via the `11th`

Implication:

- friend-relative housing questions need turned-house support before polarity can be trusted

### 8. Sale-Already-Done / New-Owner Rental Logic

Example:

- `will_we_rent_the_house`

Observed problem:

- the engine currently says `NO`
- the book says `YES`
- the book judgment depends on the sale/new-owner layer already being effectively complete

Implication:

- rental questions can need intermediate-party state handling, not just querent-to-property perfection

## What Is Ready For Phase 5/6

The following are now ready:

- deterministic replay cases with stable metadata
- current engine snapshots for those cases
- explicit mismatch notes per case
- frontend parity coverage ensuring the renderer does not mutate backend verdicts

This means Phase 5/6 can focus on real rule families:

- 10th vs 6th career routing
- turned houses for tenant/friend/counterparty questions
- 8th-house winnings/profit logic
- business 10th/11th profit routing
- property condition/value vs counterparty routing
- already-done state handling in rental/sale questions

## Verification Performed

Backend:

- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary backend/venv/bin/python -m unittest tests.test_horary_book_examples_replay -v'`
- result: `5 tests passed`

Frontend:

- `cmd /c npx vitest run src/tests/horaryBookExamplesParity.test.mjs src/tests/normalizeHoraryApiResult.test.mjs --config vitest.config.mjs`
- result: `13 tests passed`
