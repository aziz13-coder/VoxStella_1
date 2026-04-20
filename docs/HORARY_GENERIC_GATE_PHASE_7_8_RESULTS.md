## Horary Generic Gate Phase 7/8 Results

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related docs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_7_8_VERIFICATION.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_5_6_RESULTS.md`

## Coverage Added

Backend:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_generic_gate_rules.py`

Frontend:

- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryGenericGateParity.test.mjs`

## What The New Tests Prove

Backend generic-gate rules:

- denial controls still resolve as `NO`
- denial controls now surface `denial_secondary_balance`
- the strongest mixed occurrence case now resolves as `UNCLEAR`
- the quality-path relationship case stays outside the occurrence-only generic balance
- mild mixed cases do not falsely flip to `YES`

Frontend parity:

- `UNCLEAR` survives normalization unchanged
- category tagging remains stable
- outcome mapping remains `uncertain`

## Shared Replay / Parity Verification

Backend verification command:

```powershell
python -m unittest tests.test_horary_generic_gate_phase1_baseline tests.test_horary_generic_gate_corpus tests.test_horary_generic_gate_rules tests.test_horary_hard_test_corpus tests.test_horary_book_examples_replay tests.test_horary_cunning_man_external_replay -v
```

Result:

- `16 tests OK`

Frontend verification command:

```powershell
cmd /c npx vitest run src/tests/horaryGenericGateParity.test.mjs src/tests/horaryHardCorpusParity.test.mjs src/tests/horaryBookExamplesParity.test.mjs src/tests/horaryExternalCunningManParity.test.mjs src/tests/normalizeHoraryApiResult.test.mjs src/tests/buildChartPayload.test.mjs --config vitest.config.mjs
```

Result:

- `53 passed`

## Net Outcome

The first-pass generic-gate remediation is complete for the focused corpus.

Confirmed:

- the generic branch no longer hard-defaults immediately to `NO` for every no-route occurrence chart
- the change is conservative and currently produces one validated `UNCLEAR` lift instead of broad permissiveness
- existing starter/book/external replay suites still pass after fixture re-pinning
- frontend verdict parity and export helpers remain stable

## Remaining Open Work

This first pass does not finish generic-gate work forever. It leaves two obvious future directions:

- extend the corpus with more mixed no-route occurrence cases before making the branch more permissive
- perform a separate review of quality-path no-route questions if you want mixed/conditional outputs there as well
