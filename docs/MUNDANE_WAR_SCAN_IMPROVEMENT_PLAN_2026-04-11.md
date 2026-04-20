# Mundane War Scan Improvement Plan

Date: 2026-04-11

## Goal

Improve the mundane scan engine so war-domain regional scans stop behaving like weak inclusion filters and start behaving like explainable hotspot rankers.

The immediate target is the U.S.-Iran 2026 war scan benchmark. The current benchmark passes only as a weak pass because Baghdad or Tehran appear inside the returned set, while the scan still shows:

- all-zero scores
- no score separation
- uniform scan levels
- tied top scores

That behavior is not acceptable as a stable war scan result.

## Root Cause

The first failure is not doctrinal weakness. It is chart-resolution failure.

In the current scan path, the candidate cell already carries atlas coordinates, but the bundle resolver drops those coordinates before the chart is computed. The result is that some war-event scan cells resolve empty chart bundles, which then force the war domain to return zero scores.

This means:

1. scanner reproducibility must be fixed before any war ranking changes matter
2. war-domain tuning should only begin after the chart bundle is populated correctly per candidate cell

## Phase 1: Stabilize Scan Reproducibility

Objective:

- make the same war scan request resolve the same chart bundle and the same score path in direct execution and in the benchmark runner

Implementation:

- make the mundane bundle resolution path coordinate-aware
- pass scan-cell latitude and longitude through the chart-resolution path instead of relying only on the location string
- add regression tests proving that scanned war-event cells produce non-empty primary charts when atlas coordinates are available

Success criteria:

- war-event scan cells no longer resolve empty chart bundles
- U.S.-Iran war scan stops returning all-zero rows purely from missing chart data

## Phase 2: Add War Scan Geography Semantics

Objective:

- make war scans rank war-theater cells above incidental public-pressure cells

Implementation:

- add scan-layer ranking modifiers for war scans
- use event-location proximity when the chart type is `war_event`
- favor cells inside the event-theater region over distant cells with otherwise similar chart scores
- keep this logic in the scanner layer, not inside textbook doctrine claims

Guardrail:

- these are ranking heuristics for scan relevance
- they must not be presented as astrology doctrine

## Phase 3: Deepen War-Domain Signals

Objective:

- make `war_conflict` less dependent on one or two angularity checks

Implementation:

- strengthen polarity reading from the first and seventh houses
- separate aggressor activation from defender activation
- raise score when war-event polarity and malefic angularity appear together
- preserve Watters-backed retrograde Mars and eclipse activation rules

Source basis:

- Watters war-house logic
- Watters eclipse activation logic
- Green / Raphael / Carter public-affairs framing already in the runtime

## Phase 4: Expand the War Scanner Benchmark Corpus

Objective:

- stop calibrating against one regional war scan

Implementation:

- add more war scan rows to `backend/benchmarks/mundane/scanner_cases.jsonl`
- keep benchmark references tied to historical or contemporary war anchor files

Initial additions:

- U.S.-Iran 2026, U.S. lens
- U.S.-Iran 2026, Iran lens
- one additional historical war-theater scan case

## Phase 5: Tighten Scanner Benchmark Grading

Objective:

- convert the scanner benchmark from "location appears somewhere" into a stronger ranking test

Implementation:

- treat `all_zero_scores` as a hard failure for war scans
- treat `uniform_scan_levels` as a hard failure for war scans
- require a tighter maximum rank for expected war-theater cells after the scan stabilizes

Success criteria:

- the expected war-theater city is ranked at the top or near the top
- the scan produces non-zero score separation
- scan levels are not uniform background labels

## Execution Order

1. fix coordinate-aware chart resolution
2. add war scan ranking modifiers
3. expand war-domain rules
4. add more war scan cases
5. tighten benchmark grading
6. rerun the scanner suite and compare the warning profile

## Out of Scope

- frontend redesign
- bundled desktop rebuild policy changes
- new non-war scan domains
- replacing source-backed rules with opaque models

## Implementation Status

Implemented on 2026-04-11:

- Phase 1: scan chart resolution now forwards scan-cell coordinates into the chart bundle resolver
- Phase 2: war scans now expose a scan-specific theater proximity adjustment derived from the first-hostilities anchor
- Phase 3: the `war_conflict` evaluator now includes extra source-backed polarity and public-visibility rules
- Phase 4: the scanner corpus now includes three U.S.-Iran 2026 war scan rows
- Phase 5: war scan rows can now require non-zero top scores and scan separation in benchmark grading

Current scanner benchmark status after implementation:

- scanner cases: 7
- strong passes: 3
- weak passes: 4
- war scan strong passes: 2
- remaining war scan weak case: the Middle East spatiotemporal window, due to a tied top band between Baghdad and Tehran

Important distinction:

- `score` remains the absolute domain score from the source-backed mundane evaluator
- `scan_score` is scan-layer ranking metadata used to order candidate cells
- `scan_score` is not a new doctrine claim; it is a scan calibration layer on top of the doctrine-backed assessment
