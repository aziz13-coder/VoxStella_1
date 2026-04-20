## Horary Generic Gate Phase 5/6 Implementation

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related inputs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_REMEDIATION_PLAN.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_3_4_AUDIT.md`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_generic_gate_corpus.json`

## Scope

This phase implements the generic no-route remediation itself.

The goal is not to create a loose permissive fallback. The goal is to stop the generic branch from collapsing immediately into `NO` when a chart has meaningful secondary testimony but no surviving recognized perfection route.

## Live Insertion Point

The implementation belongs in the no-route branch of:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

Specifically:

1. after special doctrine returns
2. after blocker / denial / theft-loss denial returns
3. after benefic support and reception are collected
4. before the final hard no-route `NO` return

## Guardrails

The implementation must not:

- override fatal blockers
- override explicit denial families already returned earlier
- replace working category-local doctrines
- turn weak generic softeners into automatic `YES`

The following categories stay primarily under their dedicated doctrine layers:

- lost object
- pregnancy / children
- health / death-edge
- property advisability
- competition / public office

The generic refinement may still run for their unresolved residual cases only when no dedicated doctrine has already returned.

## Verdict Hierarchy

The new secondary-balance step should use three buckets:

- `affirmative_secondary_balance`
- `mixed_or_inconclusive_secondary_balance`
- `denial_secondary_balance`

First-pass safety rule:

- `affirmative_secondary_balance` should be rare
- the main intended new outcome is `UNCLEAR`
- denial controls in the focused corpus must stay `NO`

## First-Pass Secondary Factors

Promoted to verdict-level:

- substantial reception
  - measured from `traditional_strength`
- favorable Moon-next testimony
  - applying harmonious contact to a significator or strong helper
- strong benefic support
  - only when not overridden by a badly damaged quesited
- workable quesited condition
  - not retrograde
  - not severely debilitated
  - not severely solar-damaged
- Moon not void
  - minor support only

Not decisive by themselves:

- Moon swift alone
- weak face-only reception
- separating benefic traces
- isolated benefic presence

## Conservative Threshold Policy

The first implementation should behave like this:

- weak / scattered support -> `NO`
- meaningful but mixed support -> `UNCLEAR`
- only unusually strong secondary agreement -> `YES`

The current phase is expected mainly to promote selected mixed no-route charts from `NO` to `UNCLEAR`.

## Expected Corpus Effect

Target behavior in the focused generic-gate corpus:

- denial controls remain `NO`
- the strongest mixed cases become `UNCLEAR`
- if any `YES` appears, it must come from clearly exceptional combined testimony and will be reviewed case-by-case

## Shared-Safety Requirement

After implementation, phase 7/8 must rerun:

- generic-gate backend tests
- starter/book/external horary replay suites
- frontend parity suites
- serialization/export safety checks

No later phase should start before those results are documented.
