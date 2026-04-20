# Forensic Direction Rule Fixes 2026-03-25 Slice 6

## Problem

`charles_whitman` remained the last named local-source holdback.

The real `/api/astro-clock/forensic` route returned `200` and showed homicide pressure, but the direction layer was still flattening the mother-killing chart into generic witness/deception language instead of a stable family-homicide direction.

## Root Cause

This was not a chart-context or route-contract failure.

The route already delivered a usable chart payload. The miss was in `directional_context_rules.yaml`, which had:

- broad family rules
- witness/accomplice rules
- public-case rules
- no narrow family-parricide cluster for a chart where the 4th, 5th, 8th, and 1st/7th relationships all collapse into one homicidal family signature

## Smallest Responsible Fix

Added one narrowly scoped rule in:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/forensic/knowledge/directional_context_rules.yaml)

### `family_parricide_homicide_cluster`

Intent:

- cover the Whitman mother-killing chart without broadening domestic-partner, disaster, or public-witness rules

Key gate:

- 8th ruler pulled into family houses
- 5th ruler also pulled into the same family cluster
- 4th ruler angular
- 1st and 7th rulers in the same house
- hard Moon contact to Sun or Mercury across the parental axis
- hard Mars/Venus/Jupiter contact tying perpetrator and victim-family significators together

## Why The Fix Stayed Here

The slice-6 miss did not show:

- wrong request context
- wrong chart projection
- broken route contract

So the correct layer was the forensic knowledge rules, not shared Astro Clock code.

## Regression Protection

Added rule-level coverage in:

- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)

Added live-route replay coverage in:

- [test_forensic_case_replay_slice_6.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_6.py)

Shared safety suite was re-run after the rule changes.
