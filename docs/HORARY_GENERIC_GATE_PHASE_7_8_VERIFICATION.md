## Horary Generic Gate Phase 7/8 Verification

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related inputs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_5_6_IMPLEMENTATION.md`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_generic_gate_corpus.json`

## Verification Goal

This phase verifies that the new generic secondary-balance branch behaves conservatively and does not break the existing horary or Astro Clock safety surface.

## Expected Immediate Behavior

The first-pass implementation should demonstrate:

- denial controls remain `NO`
- the strongest mixed no-route occurrence case can rise to `UNCLEAR`
- quality-path questions that are not part of the occurrence fallback stay on their existing path
- no dedicated special doctrine is silently replaced by the generic branch

## Required Backend Coverage

Add focused regression tests for:

- denial controls still resolving through `denial_secondary_balance`
- the strongest mixed no-route case resolving through `mixed_or_inconclusive_secondary_balance`
- quality-path exceptions staying outside the new generic occurrence branch

## Required Frontend Coverage

Add parity coverage for:

- `UNCLEAR` verdicts produced by the generic branch
- preserved category tags and uncertain outcome mapping
- no regression in normalization/export helpers

## Required Replay Safety Sweep

Run the minimum shared verification set:

- `tests\test_horary_generic_gate_phase1_baseline.py`
- `tests\test_horary_generic_gate_corpus.py`
- `tests\test_horary_generic_gate_rules.py`
- `tests\test_horary_hard_test_corpus.py`
- `tests\test_horary_book_examples_replay.py`
- `tests\test_horary_cunning_man_external_replay.py`
- `frontend\src\tests\horaryGenericGateParity.test.mjs`
- `frontend\src\tests\horaryHardCorpusParity.test.mjs`
- `frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `frontend\src\tests\horaryExternalCunningManParity.test.mjs`
- `frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `frontend\src\tests\buildChartPayload.test.mjs`

## Exit Criteria

Phase 7/8 is complete when:

- the focused generic-gate tests pass
- the shared replay/parity sweep passes
- the observed result changes are documented
- any remaining no-route hard denials are still explainable by the conservative thresholds rather than by silent failures
