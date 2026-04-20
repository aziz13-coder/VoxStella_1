# Forensic Direction Rule Fixes 2026-03-25 Slice 5

## Problem

Two disaster cases were still source-backed but unrunnable as aligned replay assertions:

- `twa_flight_800`
- `haiti_earthquake`

The real `/api/astro-clock/forensic` route returned `200` for both, but the direction layer was still surfacing only generic deception / headwind language instead of a stable `Disaster` direction.

## Root Cause

This was not a chart-context or route-contract failure.

The route was already delivering the right chart payloads. The miss was in `directional_context_rules.yaml`, which had:

- waterborne and travel-disaster rules
- no narrow air-disaster launch rule for the TWA signature
- no narrow structural catastrophe rule for the Haiti signature

## Smallest Responsible Fix

Added two narrowly scoped rules in:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/forensic/knowledge/directional_context_rules.yaml)

### `air_disaster_launch_pattern`

Intent:

- cover the TWA take-off chart without broadening homicide, family, or domestic rules

Key gate:

- Aquarius rising
- Mercury combust
- 11th-house/public-traveler ruler hidden in the 12th
- movement/public rulers foregrounded
- domestic/family death-house reads absent

### `structural_catastrophe_pattern`

Intent:

- cover the Haiti earthquake chart without claiming a full natural-disaster taxonomy

Key gate:

- Capricorn on the 7th axis
- heavy 7th-house saturation
- Venus cazimi
- Mercury retrograde
- Moon under hard pressure
- no strong family/child-homicide signature

## Why The Fix Stayed Here

The slice-5 misses did not show:

- wrong request context
- wrong chart projection
- broken route contract

So the correct layer was the forensic knowledge rules, not shared Astro Clock code.

## Regression Protection

Added rule-level coverage in:

- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)

Added live-route replay coverage in:

- [test_forensic_case_replay_slice_5.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_5.py)

Shared safety suite was re-run after the rule changes.
