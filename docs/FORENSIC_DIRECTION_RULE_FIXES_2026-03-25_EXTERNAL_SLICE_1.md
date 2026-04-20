# Forensic Direction Rule Fixes 2026-03-25 External Slice 1

## Problem

The Idaho 4 candidate had a stronger event window than Delphi once the official affidavit was consulted, but the live forensic route still produced family and child false positives across the `4:12 AM`, `4:17 AM`, and `4:20 AM` anchors.

That made the case unsafe to promote into an executable replay slice even though the route was already surfacing the correct homicide pressure.

## Root Cause

This was not an Astro Clock request-context problem.

The live route was producing a stable chart and a stable homicide direction. The problem was in the forensic knowledge layer:

- `family_domestic_moon_signature` treated Moon in Cancer by itself as a family signal
- `family_home_axis_under_pressure` treated a 4th ruler merely sitting in its own 4th house as enough "pressure"
- `child_family_overlap` allowed a Moon-in-Cancer fallback to combine too easily with a routine 5th-house placement

That logic was broad enough to leak family or child direction into a non-family college homicide chart.

## Smallest Responsible Fix

Adjusted three rules in:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/forensic/knowledge/directional_context_rules.yaml)

Changes:

- Moon in Cancer no longer counts as a family signal by itself
- the home-axis pressure rule now requires actual 4th-house stress, not just a 4th ruler in its own house
- the child-family overlap rule now requires either real family-house stress or a Cancer Moon under hard malefic pressure

## Why The Fix Stayed Here

The external replay miss did not show:

- bad route parameters
- broken chart projection
- a route-contract failure

So the correct layer remained the forensic directional knowledge rules, not shared Astro Clock plumbing.

## Regression Protection

Added rule-level coverage in:

- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)

Added external live-route replay coverage in:

- [test_forensic_external_replay_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_external_replay_slice_1.py)

Existing slices 1 through 6 were re-run after the fix and remained aligned.
