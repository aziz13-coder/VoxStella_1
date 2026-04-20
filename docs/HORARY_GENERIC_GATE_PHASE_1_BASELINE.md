# Horary Generic Gate Phase 1 Baseline

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related plan:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_REMEDIATION_PLAN.md`

## Scope

Phase 1 freezes the current generic-gate baseline before any verdict-hierarchy changes are made.

This phase does not change horary runtime logic. It records:

- the current replay baseline
- the current excluded/deferred cases
- the first candidate queue for generic-gate work
- the boundary between generic-gate work and category-specific doctrine work

## Frozen Corpus Baseline

### Starter Hard Corpus

- total cases: `11`
- deterministic: `6`
- manual review: `5`

Primary files:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_hard_test_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_hard_test_corpus.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryHardCorpusParity.test.mjs`

### Book Replay Corpus

- extracted book entries: `64`
- replayed book cases: `30`
- aligned replay cases: `27`
- deferred disagreements: `3`

Primary files:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`

### External Cunning Man Replay Corpus

- extracted article cases: `14`
- replay-ready external cases: `3`
- aligned external replay cases: `3`

Primary files:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_replay.json`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_external_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryExternalCunningManParity.test.mjs`

## What Phase 1 Excludes

Generic-gate work must not begin by changing charts whose main issue is already known to be:

- a deferred doctrine family
- a category-specific balance doctrine
- a contextual analyzer problem

### Deferred Cases To Keep Out Of Generic-Gate Work

- `will_we_rent_the_house`
  - chained ownership / post-transfer property state
- `will_grandfather_survive_this_time`
  - kinship derivation / maternal-branch ambiguity
- `will_barrett_win`
  - contextual public-office identification

### Category-Local Doctrines To Keep Separate

These are already on dedicated tracks and should not be mixed into the first generic-gate corpus:

- lost-object recovery/location
- public-office contests
- champion/title-holder contests
- pregnancy sufficiency/status
- children/adoption balance
- health diagnosis/progression
- pet recovery/survival
- property advisability/sufficiency
- relationship durability/affection balances

## Phase 2 Candidate Queue

The purpose of the candidate queue is not to assert that these charts are wrong. The purpose is to isolate charts where:

- no recognized positive route survives
- the engine still reaches judgment through the generic no-route branch
- the question is useful for testing whether Moon/reception/condition are being underweighted

### Current Candidate Queue

1. `masters_program_no_perfection_no`
   - clean hard-corpus no-route denial
   - useful as the baseline true-denial control

2. `will_my_tenant_send_full_payment`
   - aligned no-route money chart
   - useful for checking whether weak-resource charts are being denied for the right reasons

3. `will_i_get_the_job_at_uw`
   - aligned no-route career chart
   - useful for checking no-route denial where another party overtakes the matter

4. `will_i_profit_from_this_bet`
   - aligned no-route profit chart
   - useful for Moon/VOC and resource-chain weighting

5. `will_investing_in_this_business_prove_profitable_for_me`
   - aligned no-route money/profit chart
   - useful for checking whether secondary testimonies are merely decorative

6. `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her`
   - aligned no-route relationship chart
   - useful for checking whether no-route reconciliation charts are over-denied

7. `marriage_no_manual_review`
   - manual-review no-route chart
   - useful as a controlled relational no-route review case

8. `divorce_no_manual_review`
   - manual-review no-route chart
   - useful as a controlled negative relational no-route review case

9. `pay_rise_article_spec`
   - external no-route chart
   - useful as an outside replay anchor for the same generic branch

## Phase 1 Deliverable Artifact

Machine-readable baseline:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_generic_gate_phase1_baseline.json`

This file records:

- frozen corpus totals
- candidate queue
- deferred exclusions
- doctrine-track exclusions

## Why This Is Enough For Phase 1

Phase 1 is complete when:

- the current replay state is frozen
- the generic-gate candidate queue is explicit
- the deferred doctrine cases are explicitly excluded
- the next phase can build a focused corpus without re-deciding scope

No generic verdict logic should be changed until Phase 2 turns the candidate queue into a real generic-gate corpus.
