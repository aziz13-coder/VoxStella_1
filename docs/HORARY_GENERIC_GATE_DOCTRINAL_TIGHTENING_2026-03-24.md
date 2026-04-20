# Horary Generic Gate Doctrinal Tightening

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related docs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_DOCTRINAL_REVIEW.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_REMEDIATION_PLAN.md`

## Purpose

Apply the narrow doctrinal correction identified in the generic-gate review:

- no-route `YES` should require a genuine connecting testimony
- reception, benefic help, and workable condition may still elevate a chart to `UNCLEAR`
- those softer testimonies should not by themselves complete the matter

## Runtime Changes

Changed in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\horary_engine\engine.py`

### Rule change

The generic fallback now tracks:

- `connecting_testimony`
- `strong_connecting_testimony`

Current implementation:

- a positive Moon next aspect marks `connecting_testimony`
- a decisive positive Moon next aspect marks `strong_connecting_testimony`

### New affirmative rule

`affirmative_secondary_balance` now requires:

- existing score thresholds
- plus `strong_connecting_testimony`

That means:

- reception + benefics + a workable quesited can still produce `UNCLEAR`
- but they cannot produce a generic `YES` without a stronger bridge

### Mixed rule wording

The `UNCLEAR` branch now distinguishes:

- strong secondary testimony with some bridge, but not enough for a clean affirmative
- strong secondary testimony with no strong traditional bridge

## Expected Behavioral Effect

This change is intentionally conservative.

It should:

- preserve denial controls
- preserve the existing `UNCLEAR` use-case for arguable no-route charts
- make generic `YES` rarer and more traditionally defensible

It should not:

- affect special doctrine families
- replace the main perfection system
- convert soft secondary testimony into a broader permissive engine

## Test Coverage Added

Updated:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_generic_gate_rules.py`

New doctrinal guards:

- reception plus benefic help plus workable quesited without connecting testimony returns `UNCLEAR`
- a decisive Moon bridge can still return generic `YES`

## Summary

This is a doctrinal tightening, not a behavior expansion.

The generic fallback remains available, but it is now less willing to let stacked soft testimonies stand in for actual completion of the matter.
