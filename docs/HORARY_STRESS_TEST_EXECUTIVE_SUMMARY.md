# Horary Stress-Test Executive Summary

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

## Purpose

This summary records the current state of the horary stress-test program so the work can be resumed without re-auditing the entire repo.

The stress-test effort is no longer just a plan. It is already implemented in source through replay corpora, backend regression suites, frontend parity tests, and doctrine-level rule fixes.

## Audit Layers

The current horary stress-test work uses two different audit layers, and they should not be conflated:

1. `source-pass` = routing audit
   This checks whether the analyzer is putting a question into the right family, houses, quesited house, and intent.
   Typical assertions:
   - `question_type`
   - `relevant_houses`
   - `quesited_house`
   - `question_intent`
   - doctrine focus notes from the source

2. `replay corpus` = judgment audit
   This checks the actual engine output on a chart payload, not just the routing.
   Typical assertions:
   - final verdict
   - perfection path
   - backend/frontend parity
   - reasoning alignment
   - replay stability on serialized chart data

Why this matters:

- the external source-pass slices are mostly doctrine and router checks because the source articles usually do not publish enough chart metadata for safe replay
- the hard corpus and book replay corpora are stronger judgment audits because they already have enough pinned chart data to test the engine's actual answer path

## Current Authoritative Documents

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_ENGINE_HARD_TEST_PLAN.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_STRESS_TEST_PLAN.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_PHASE_5_6_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_2_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_3_PHASE56_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_4_5_PHASE56_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_EXTERNAL_CORPUS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_AUDIT.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_REMEDIATION_PLAN.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_DOCTRINAL_REVIEW.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_DOCTRINAL_TIGHTENING_2026-03-24.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_SOURCE_PASS_SLICE_2_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_SOURCE_PASS_SLICE_3_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_SOURCE_PASS_SLICE_4_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_5_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_6_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_7_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_8_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_9_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_10_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_11_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_12_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_13_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_14_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_15_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_16_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_17_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_18_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_19_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_20_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_21_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_22_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_23_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_SOURCE_PASS_SLICE_24_RESULTS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_EXTERNAL_REASONING_COMPARISON_2026-03-25.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_ROUTER_LONG_TERM_DIRECTION.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_SOURCE_PASS_METADATA_CENSUS.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_SOURCE_PASS_TO_REPLAY_PLAN.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_ENGINE_ROOT_CAUSE_INVESTIGATION.md`

## Corpus Status

### Starter Hard Corpus

- `11` implemented cases
- deterministic and manual-review split
- backend replay harness in place
- frontend verdict-parity harness in place

Primary artifacts:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_hard_test_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_hard_test_corpus.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryHardCorpusParity.test.mjs`

### Book Corpus

- `64` extracted book examples total
- `30` replayed through the engine
- `27` source-aligned after doctrine/routing fixes
- `3` still deferred on purpose

Primary artifacts:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`

### External Cunning Man Corpus

- `14` extracted article cases
- `4` promoted into replay-ready external cases
- promoted cases are source-aligned
- `5` additional fetched source-pass cases now pinned as router/doctrine checks
- `5` more fresh source-pass cases now pinned as router/doctrine checks
- `3` additional weather and timing source-pass cases now pinned as router/doctrine checks
- `3` mixed external source-pass cases now pinned as generalization probes beyond the Cunning Man wording
- `3` mixed external source-pass cases now pinned for communication and delivery timing
- `3` mixed external source-pass cases now pinned for legal adjudication and court-battle routing
- `3` mixed external source-pass cases now pinned for turned-relative and person-whereabouts routing
- `3` mixed external source-pass cases now pinned for theft and stolen-item routing
- `3` mixed external source-pass cases now pinned for repayment, refund, and reimbursement routing
- `3` mixed external source-pass cases now pinned for property transition routing
- `3` mixed external source-pass cases now pinned for loans and borrowing routing
- `3` mixed external source-pass cases now pinned for visa, permit, and immigration-approval routing
- `3` mixed external source-pass cases now pinned for custody and family-court routing
- `3` mixed external source-pass cases now pinned for surgery, medical procedures, and cosmetic-operation routing
- `3` mixed external source-pass cases now pinned for publishing, manuscript acceptance, and gains from publication
- `3` mixed external source-pass cases now pinned for arrest, imprisonment, and release from prison
- `3` mixed external source-pass cases now pinned for inheritance, estate distribution, and inheritance-rights routing
- `3` mixed external source-pass cases now pinned for scholarships, grants, and public financial aid routing
- `3` mixed external source-pass cases now pinned for vehicle acquisition and sale routing
- `3` mixed external source-pass cases now pinned for citizenship, permanent residence, and green-card approval routing
- `3` mixed external source-pass cases now pinned for landlord, tenant, occupancy-change, and eviction routing
- `3` mixed external source-pass cases now pinned for passports and official travel-document routing
- `3` mixed external source-pass cases now pinned for roommate and cohabitation routing
- source-pass slice 2 records `5` aligned and `0` misaligned router observations after the router pass
- source-pass slice 3 now also records `5` aligned and `0` misaligned router observations after the family pass
- source-pass slice 4 now records `3` aligned and `0` misaligned router observations after the weather and medical-result contact pass
- mixed external slice 5 now records `3` aligned and `0` misaligned router observations after the secular celebration-event weather pass
- mixed external slice 6 now records `3` aligned and `0` misaligned router observations after the communication and delivery doctrine pass
- mixed external slice 7 now records `3` aligned and `0` misaligned router observations after the lawsuit / court-adjudication doctrine pass
- mixed external slice 8 now records `3` aligned and `0` misaligned router observations after the turned-relative and person-whereabouts doctrine pass
- mixed external slice 9 now records `3` aligned and `0` misaligned router observations after the theft and stolen-item doctrine pass
- mixed external slice 10 now records `3` aligned and `0` misaligned router observations after the repayment, refund, and reimbursement doctrine pass
- mixed external slice 11 now records `3` aligned and `0` misaligned router observations after the shared property-transition doctrine pass
- mixed external slice 12 now records `3` aligned and `0` misaligned router observations after the shared loan/lender doctrine pass
- mixed external slice 13 now records `3` aligned and `0` misaligned router observations after the shared visa / permit / immigration-approval doctrine pass
- mixed external slice 14 now records `3` aligned and `0` misaligned router observations after the shared custody / family-court doctrine pass
- mixed external slice 15 now records `3` aligned and `0` misaligned router observations after the shared surgery / procedure doctrine pass
- mixed external slice 16 now records `3` aligned and `0` misaligned router observations after the shared publication doctrine pass
- mixed external slice 17 now records `3` aligned and `0` misaligned router observations after the shared confinement doctrine pass
- mixed external slice 18 now records `3` aligned and `0` misaligned router observations after the shared inheritance doctrine pass
- mixed external slice 19 now records `3` aligned and `0` misaligned router observations after the shared scholarship / grant / public-aid doctrine pass
- mixed external slice 20 now records `3` aligned and `0` misaligned router observations after the shared vehicle / automobile doctrine pass
- mixed external slice 21 now records `3` aligned and `0` misaligned router observations after the shared citizenship / residency-status doctrine pass
- mixed external slice 22 now records `3` aligned and `0` misaligned router observations after the shared tenancy / landlord-tenant occupancy doctrine pass
- mixed external slice 23 now records `3` aligned and `0` misaligned router observations after the shared passport / travel-document doctrine pass
- mixed external slice 24 now records `3` aligned and `0` misaligned router observations after the shared roommate / cohabitation doctrine pass

Primary artifacts:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_replay.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_external_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_source_pass_slice2.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice2.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_source_pass_slice3.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice3.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_source_pass_slice4.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice4.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_slice4_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice5.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice5.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice6.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice6.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice6_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice7.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice7.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice8.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice8.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice8_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice9.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice9.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice10.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice10.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice11.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice11.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice12.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice12.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice12_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice13.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice13.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice13_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice14.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice14.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice14_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice15.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice15.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice15_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice16.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice16.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice16_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice17.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice17.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice17_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice18.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice18.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice18_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice19.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice19.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice19_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice20.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice20.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice20_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice21.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice21.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice21_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice22.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice22.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice22_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice23.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice23.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice23_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice24.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice24.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice24_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryExternalCunningManParity.test.mjs`

## What Was Improved

The example program was used to fix rule families, not to force individual example outputs.

### Economic / Work Doctrine

- career review
- tenant payment
- betting profit
- business start / business profit
- bank counterparty questions

### Scholarship / Aid Routing

- higher-study scholarship questions now keep the `9th` primary and the `2nd` secondary when eligibility or means are materially part of the question
- turned-relative scholarship questions now preserve the relative house first and then turn the higher-study axis from that subject
- public financial aid now keeps the official or governmental support axis on the `10th`

### Vehicle / Automobile Routing

- buying a specific car from a seller now keeps the seller on the `7th` and the seller's possession axis for the car on the radical `8th`
- selling the querent's own car now keeps the vehicle visible on the `3rd` and the buyer on the `7th`
- turned-relative car acquisition now keeps the relative first and turns possession and vehicle houses from that person

### Property Doctrine

- acquisition vs advisability vs property condition
- better `L4/L10` handling
- reduced misrouting into generic money logic

### Relationship Doctrine

- durability vs event/occurrence separation
- reciprocal affection vs bare contact/perfection

### Pregnancy / Children Doctrine

- conception vs diagnosis
- adoption routing
- first-person child questions preserved on proper houses

### Health / Death-Edge Doctrine

- diagnosis vs progression
- medical-result contact/timing versus the literal disease question
- pet survival / recovery
- stronger third-person health routing

### Event / Weather Routing

- weather for a named event now judges from the event significator rather than generic `1/7`
- religious festival and holy-day weather questions now route through the `9th`
- social celebration-event weather now routes through the `5th`

### Communication / Delivery Routing

- friend-contact questions now keep the friend on the `11th`
- message-receipt questions now surface the `3rd` house for the communication itself
- delivery-arrival questions now use a logistics family that keeps goods, home, courier, and others-in-possession in view

### Legal / Court-Adjudication Routing

- plain legal outcome questions now keep the court axis of `1/7/10/4` in view
- employment/compensation legal fights no longer collapse into `money`
- inheritance-rights court battles now keep the legal axis primary while adding the `8th` as subject matter
- third-person appeal and hearing questions can now turn the court axis instead of defaulting to a generic other-person frame

### Turned-Relative Routing

- explicit relative subjects like `my sister` and `my daughter` now stay operative even when later partner pronouns or nouns appear in the sentence
- relative marriage questions now turn from the relative's house to the turned `7th`
- relative relationship questions now keep the relative as subject and the partner on the turned `7th`
- person-whereabouts and welfare questions now keep the person as subject instead of collapsing into `lost_object`

### Theft / Stolen-Item Routing

- explicit theft wording now triggers a dedicated doctrine family before generic lost-object or possession heuristics
- stolen-object questions now keep the item on the `2nd` while also surfacing the thief on the `7th`
- suspected-money-theft questions now keep the querent's money on the `2nd`, the thief on the `7th`, and the thief's possession on the `8th`

### Refund / Reimbursement Routing

- repayment and refund wording now triggers a dedicated economic doctrine family before communication or generic funding heuristics
- friend repayment questions now keep the counterparty and the money-recovery axis in view
- institutional refund questions now turn to the institution's own money instead of collapsing into generic funding

### Property Transition Status

- move-house wording remains stable on the property axis
- buy/sell house phrasing now also stays in the property family instead of collapsing into generic money logic
- house acquisition and sale questions now keep the house in the `4th` and the counterparty in the `7th`
- property advisability keeps the `4th`, `7th`, and `10th` in view

### Lost-Object Doctrine

- no longer denies recovery too automatically because of Moon VOC alone
- recovery/location questions judged by recoverability and condition
- user-facing lost-object verdict wording now renders as `RECOVERABLE / NOT RECOVERABLE` while internal raw verdict remains `YES / NO`

### Competition / Public-Office Doctrine

- public-office contests via `1/10`
- champion/title-holder asymmetry via `10/4`

### Generic Gate

- focused generic-gate corpus implemented
- fallback buckets implemented: `affirmative_secondary_balance`, `mixed_or_inconclusive_secondary_balance`, `denial_secondary_balance`
- doctrinal review completed
- doctrinal tightening completed so no-route generic `YES` now requires a real connecting testimony

## Shared Safety Work Already Done

These fixes were not made in isolation. The horary work also hardened shared boundaries:

- backend/frontend verdict parity
- Astro Clock regression protection
- export/serialization fixes so copied or AI-audited charts match the actual engine context
- internal raw-chart passthrough to reduce fragile serialize-then-deserialize loops

## Main Implemented Test Surfaces

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_hard_test_corpus.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryHardCorpusParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_phase56_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_slice2_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_health_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_lost_contest_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_government_job_case.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_generic_gate_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice2.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice3.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice4.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_slice3_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_slice4_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice5.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice6.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice6_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice7.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice7_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice8.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice8_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice9.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice9_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice10.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice10_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice11.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice11_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice12.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice12_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice13.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice13_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice14.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice14_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice15.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice15_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice16.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice16_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice17.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice17_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice18.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_slice18_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\buildChartPayload.test.mjs`

## Open Items

### Deferred Book Disagreements

The following three book cases remain deferred on purpose because they appear to require broader doctrine, not safe one-case fixes:

- `will_we_rent_the_house`
- `will_grandfather_survive_this_time`
- `will_barrett_win`

### Structural Follow-Up

The generic gate is no longer just an open audit item. It has already had a completed first-pass remediation and a later doctrinal tightening pass.

The remaining structural follow-up is narrower:

- continue monitoring whether the tightened no-route `YES` criteria stay well-behaved across future corpus expansion
- the education `9th`-first routing and short-transit `3rd`-house routing have now generalized cleanly on the first fresh slice
- the foreign-nation/state-action, public-office confidence, and treatment/medicine families have now also been routed explicitly
- the weather/event and medical-result/contact timing gaps exposed by slice 4 are now routed explicitly as well
- the mixed external generalization probe is now also clean on wedding-event weather, secular celebration weather, and medical-result contact timing
- friend-contact, message-receipt, and goods-arrival timing questions are now routed explicitly as well
- legal adjudication is now routed explicitly as well, including mixed compensation and inheritance court fights
- turned-relative and person-whereabouts routing is now pinned cleanly on the first external slice after the doctrine pass
- theft and stolen-item routing is now pinned cleanly on the first external slice after the doctrine pass
- repayment, refund, and reimbursement routing is now pinned cleanly on the first external slice after the doctrine pass
- property transition routing is now pinned cleanly on the first external slice after the doctrine pass
- named-bank and lender-aware loan routing is now pinned cleanly on the first external slice after the doctrine pass
- source-pass analyzer intent labels are now pinned on the broader `OCCURRENCE / QUALITY / SAFETY` vocabulary instead of the stale `REUNION` catch-all
- visa, permit, and immigration-approval routing is now pinned cleanly on the first external slice after the doctrine pass
- custody and family-court routing is now pinned cleanly on the first external slice after the doctrine pass
- surgery, medical procedure, and cosmetic-operation routing is now pinned cleanly on the first external slice after the doctrine pass
- publishing, manuscript acceptance, and gains from publication routing is now pinned cleanly on the first external slice after the doctrine pass
- arrest, imprisonment, and release from prison routing is now pinned cleanly on the first external slice after the doctrine pass
- inheritance, estate-property, and inheritance-rights routing is now pinned cleanly on the first external slice after the doctrine pass

## Recommended Next Queue

If horary work resumes now, the best order is:

1. fetch the next external slice for another still-unprobed doctrine family
2. rerun backend/frontend parity and Astro Clock safety checks after any further routing change
3. continue choosing new work by doctrine gap rather than by random example count
4. revisit the three deferred cases once the next doctrine family is chosen

## Bottom Line

The horary stress-test effort is substantially advanced and already useful. The strongest result is the book replay program: `30` replayed cases with `27` aligned after rule-level fixes.

The stress-test program is now broad enough that new work should be chosen by doctrine gap, not by random example count. The higher-education `9th`-first and short-transit `3rd`-house router pass held up on a fresh slice, the newer state/confidence/medicine/event-weather families generalized cleanly, friend-contact/message-receipt/goods-arrival routing now generalizes beyond the earlier cases, and lawsuit/court-adjudication, turned-relative, theft, reimbursement, property-transition, loan/lender, visa or permit, custody or family-court, surgery or cosmetic-operation, publication or publication-gain, confinement/arrest/prison, and inheritance or estate-property routing now do as well. The next exposed gap should come from a fresh external slice in a still-unprobed doctrine family.
