## Horary Generic Gate Phase 5/6 Results

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related docs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_5_6_IMPLEMENTATION.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_3_4_AUDIT.md`

## Implementation Summary

The generic no-route branch now evaluates qualified secondary testimony before falling into a hard denial.

Implemented in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\horary_engine\engine.py`

## Root-Level Change

Added a dedicated helper:

- `_evaluate_generic_secondary_balance(...)`

This helper:

- only applies to occurrence-focused no-route charts
- excludes dedicated doctrine domains:
  - lost object
  - pregnancy / children
  - health / death-edge
  - property
  - pet recovery
- scores qualified secondary testimony instead of defaulting directly to `NO`

## New Generic Buckets

The no-route branch now resolves through three explicit verdict buckets:

- `affirmative_secondary_balance`
- `mixed_or_inconclusive_secondary_balance`
- `denial_secondary_balance`

First-pass behavior remained conservative:

- no new generic secondary-balance `YES` cases were introduced
- only the strongest mixed occurrence case rose to `UNCLEAR`

## Secondary Factors Used

The first-pass scoring promotes:

- meaningful mutual or substantial reception
- favorable Moon-next testimony
- strong benefic help that is not overridden by a weak quesited
- workable quesited condition
- Moon not void as minor support

It still resists:

- weak reception alone
- diffuse benefic presence
- severe quesited debility
- retrogradation / combustion penalties

## Observed Corpus Effect

Focused generic-gate corpus outcome after implementation:

- denial controls stayed `NO`
- `marriage_no_manual_review` moved from `NO` to `UNCLEAR`
- `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her` stayed on the quality path and remained outside the new occurrence gate
- `will_investing_in_this_business_prove_profitable_for_me` stayed `NO`
- `will_i_get_the_job_at_uw` stayed `NO`

## Replay Fixture Updates

Because the generic branch now surfaces explicit denial buckets, several book replay fixtures had to be repinned from:

- `engine_expected_perfection_type = "none"`

to:

- `engine_expected_perfection_type = "denial_secondary_balance"`

Updated cases:

- `will_my_tenant_send_full_payment`
- `will_i_get_the_job_at_uw`
- `will_i_profit_from_this_bet`
- `will_investing_in_this_business_prove_profitable_for_me`
- `will_barrett_win`

These were not verdict flips. They were explicit engine-observation updates reflecting the new generic hierarchy.

## Safety Outcome

The first pass achieved the intended shape:

- it did not weaken the denial controls
- it did not interfere with special doctrines
- it introduced a real mixed no-route outcome without creating permissive drift
