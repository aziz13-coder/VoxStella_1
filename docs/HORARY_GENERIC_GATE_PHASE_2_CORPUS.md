# Horary Generic Gate Phase 2 Corpus

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related baseline:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_1_BASELINE.md`

## Scope

Phase 2 promotes the Phase 1 candidate queue into a dedicated generic-gate corpus.

This corpus is intentionally narrower than the full horary replay suite. It only includes charts that are useful for testing the generic no-route branch.

The purpose is not to prove every case should become `YES`. The purpose is to separate:

- true no-route denial controls
- no-route charts with meaningful secondary support
- no-route charts that should remain manual review until the generic gate is refined

## Current Corpus Split

### Denial Controls

These charts currently look like legitimate no-route denials and should remain the control group while the generic gate changes:

- `masters_program_no_perfection_no`
- `will_my_tenant_send_full_payment`
- `will_i_profit_from_this_bet`
- `divorce_no_manual_review`
- `pay_rise_article_spec`

### Mixed / Inconclusive Secondary-Balance Candidates

These charts already carry elevated secondary testimony even though the current generic branch still resolves them to `NO`:

- `marriage_no_manual_review`
- `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her`
- `will_investing_in_this_business_prove_profitable_for_me`
- `will_i_get_the_job_at_uw`

Important note:

- this first corpus does not yet include a source-backed affirmative generic no-route case
- that means the first remediation pass is expected to focus on distinguishing `NO` from `UNCLEAR` more intelligently before attempting any broader affirmative no-route doctrine

## Why These Candidates Were Chosen

### `marriage_no_manual_review`

Current replay already shows:

- mixed reception
- Moon trine Venus
- swift Moon
- no direct perfection

This is the cleanest current example of a chart that carries real secondary support while still collapsing into a generic denial.

### `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her`

Current replay already shows:

- Moon swift
- Moon not void
- mixed reception
- no direct perfection

This is useful because it stresses the same no-route logic in a relational occurrence chart without being a dedicated affection or durability doctrine override.

### `will_investing_in_this_business_prove_profitable_for_me`

Current replay already shows:

- Moon swift
- Moon not void
- one-way reception
- an applying Venus/Mercury support signal
- no direct perfection

This is useful for checking whether the generic branch can preserve a meaningful mixed assessment even when the final doctrinal answer still remains negative.

### `will_i_get_the_job_at_uw`

Current replay already shows:

- Moon not void
- one-way reception
- no direct perfection

This is useful as a milder secondary-support chart where the engine may still be right to deny, but should do so through a more explicit secondary-balance branch.

## Corpus Artifact

Machine-readable file:

- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_generic_gate_corpus.json`

Helper:

- `C:\Users\sabaa\Downloads\codexhorary\tests\horary_generic_gate_utils.py`

Initial validation test:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_generic_gate_corpus.py`

## Phase 2 Output

The dedicated generic-gate corpus now exists as the working input for:

- Phase 3 branch audit
- Phase 4 testimony-promotion rules
- Phase 5 hierarchy implementation

No runtime verdict logic has been changed in this phase.
