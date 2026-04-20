# Horary Generic Gate Remediation Plan

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary baseline:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_AUDIT.md`

Doctrinal comparison:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_DOCTRINAL_REVIEW.md`

Doctrinal tightening:
`C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_DOCTRINAL_TIGHTENING_2026-03-24.md`

## Purpose

This plan defines the next horary work queue for the generic verdict gate.

Status:

- Phase 1 baseline complete
- Phase 2 focused corpus complete
- Phase 3/4 audit complete
- Phase 5/6 first-pass implementation complete
- Phase 7/8 verification complete
- Doctrine review complete
- Doctrine-tightening implementation complete

The goal is not to weaken the engine into permissive `YES` answers. The goal is to make the generic branch more traditionally structured when no recognized perfection route survives.

That means:

- keep the existing perfection system
- keep translation / collection / prohibition / refranation / frustration / abscission
- reduce over-fast fallback to generic `NO`
- promote selected non-route testimonies to real verdict-level significance
- protect Astro Clock and every shared consumer while doing so

## Problem Statement

Per `HORARY_GENERIC_GATE_AUDIT.md`, the current engine already does more than direct perfection. The structural problem is the final hierarchy:

- if a recognized perfection route survives, the engine is comparatively rich
- if no route survives, the generic branch still tends to deny too quickly
- Moon condition, receptions, dignities, benefic support, and contextual condition are often treated as secondary modifiers rather than as decisive testimonies

The result is that some classically arguable charts can still be over-denied by the generic branch even when the chart is not a clean failure.

## Safety Constraint

No generic-gate change is allowed to land without checking shared consumers.

At minimum, every phase must be verified against:

- `C:\Users\sabaa\Downloads\codexhorary\backend\app.py` route output
- saved/rerun horary flows
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\utils\normalizeHoraryApiResult.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\utils\buildChartPayload.js`
- Astro Clock consumers that rely on the same chart serialization or shared helpers

## Work Queue

### Phase 1. Freeze The Current Generic Baseline

Before changing logic:

- preserve the current book/external replay results as baseline
- identify the subset of cases where the main issue is not routing but generic-gate weighting
- avoid mixing generic-gate remediation with unresolved deferred doctrine families

Target baseline artifacts:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_hard_test_corpus.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_external_replay.py`

### Phase 2. Build A Focused Generic-Gate Corpus

Create a separate focused corpus for charts where:

- no recognized positive perfection survives
- direct perfection is absent or blocked
- but the chart still contains meaningful secondary testimonies

Split the corpus into:

- `generic_supportive_no_route`
  - no surviving perfection route
  - supportive Moon/reception/condition
  - classically arguable positive or mixed result
- `generic_true_denial`
  - no surviving route
  - severe denial factors
  - classically arguable negative result
- `generic_manual_review`
  - strong ambiguity
  - not safe for deterministic automation yet

Recommended minimum first slice:

- `6` to `10` charts
- mixed across relationship, property, missing/recovery, and general occurrence

### Phase 3. Audit The Exact Current Generic Branch

Map the live control flow in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

Focus on:

- where `perfection["perfects"]` becomes the main branch split
- where no-route cases are set to default `NO`
- where Moon testimony, receptions, benefics, and dignities are applied only as confidence modifiers
- which category-local doctrines already bypass generic denial correctly

The output of this phase should be a short matrix:

- branch condition
- current effect
- traditional interpretation
- candidate change

### Phase 4. Define Verdict-Level Secondary Testimonies

Select which non-route testimonies deserve decision-level status in the generic branch.

Likely candidates:

- Moon applying harmoniously to quesited or strong helper
- strong mutual or substantial one-way reception
- strong essential/accidental condition of quesited with no terminal affliction
- strong benefic support tied to the quesited
- context-specific recoverability or condition logic

These must be defined narrowly enough that the engine does not turn into:

- `no perfection but a benefic exists somewhere -> YES`

This phase should produce reusable rules, not category-specific ad hoc exceptions.

### Phase 5. Implement A Generic Verdict Hierarchy

Refactor the generic no-route branch into three buckets:

- `affirmative_secondary_balance`
- `mixed_or_inconclusive_secondary_balance`
- `denial_secondary_balance`

The key change is:

- do not default immediately to `NO` before evaluating qualified secondary testimonies

The key non-change is:

- do not allow weak softeners to overrule hard denials

### Phase 6. Keep Category-Specific Doctrines Separate

Do not pull category-local logic back into the generic branch.

Keep dedicated doctrine modules for:

- lost object
- competition/public office
- pregnancy/children
- health/death-edge
- property advisability
- relationship durability/affection

Generic-gate remediation should improve the fallback hierarchy, not replace the special doctrines already working.

### Phase 7. Add Regression Coverage

Required new tests:

- backend unit/integration tests for the generic no-route hierarchy
- targeted frontend parity tests proving display/output remains stable
- regression tests proving existing special doctrines still override generic fallback where intended

Suggested test files:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_generic_gate_rules.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_generic_gate_corpus.json`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryGenericGateParity.test.mjs`

### Phase 8. Re-Verify Shared Safety

After every generic-gate change, rerun:

- horary replay corpus
- frontend parity suites
- Astro Clock API tests tied to chart serialization/export

Minimum verification set:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_hard_test_corpus.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_external_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryHardCorpusParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryExternalCunningManParity.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\normalizeHoraryApiResult.test.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\buildChartPayload.test.mjs`

## Files Most Likely To Change

Primary:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\perfection_core.py`

Possible supporting files:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\aggregator.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\polarity_weights.py`

The special doctrine modules should only change if the generic work uncovers a real overlap bug.

## Deferred Cases To Revisit Later

Do not fold these directly into generic-gate work at first:

- `will_we_rent_the_house`
- `will_grandfather_survive_this_time`
- `will_barrett_win`

These remain broader doctrine problems and should be revisited only after the generic branch is improved.

## Exit Criteria

The generic-gate remediation can be considered successful when:

- a focused generic-gate corpus exists
- the generic branch no longer defaults to `NO` before evaluating qualified secondary testimonies
- existing special doctrines still pass
- frontend parity still holds
- Astro Clock/shared helpers remain stable
- the remaining deferred cases are still deferred for principled reasons, not hidden by generic drift

## Immediate Next Task

The next concrete step is:

1. create `horary_generic_gate_corpus.json`
2. promote `6` to `10` no-route charts into that corpus
3. add the first backend replay suite
4. only then change the generic branch
