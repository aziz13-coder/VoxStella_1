# Mundane National-Chart Scan Decision

Date: 2026-04-13

## Decision

`national_chart` scan remains deferred.

Current status:

- analysis: enabled
- scan: disabled by design
- scan catalog status: `analysis_only`

This closes Phase E of the gap-narrowing plan.

## Why The Decision Is Defer, Not Enable

The issue is doctrinal clarity, not implementation difficulty.

The current scan model assumes:

- a chart/domain pairing
- a bounded region
- a set of candidate places
- a set of times
- repeated evaluation of location/time cells
- ranking of cells and then aggregated places

That works cleanly for:

- event-anchor charts
- framework charts
- trigger charts

It does not yet work cleanly for the national chart.

## Why National Chart Is Different

The national chart is a durable polity structure chart.

In the local doctrine, it is strongest as:

- a background polity map
- a validation overlay
- a structural strain frame

It is not yet justified in this repo as a direct spatial scan chart where location cells are treated as if they were independent outbreak or hotspot candidates.

That is the core reason for the defer decision.

## Main Risks If Enabled Too Early

1. false localization
   - a fixed polity chart can look spatially precise when it is really describing national structure

2. semantic collision with capital and event contexts
   - the user can mistake a national-chart scan result for an event-anchor result

3. too many options with weak doctrinal separation
   - scan becomes broader while meaning becomes blurrier

4. raw-cell ranking distortion
   - the existing scan engine is only now being corrected away from raw-cell-first semantics
   - widening to national-chart scan before a distinct national-chart scan contract exists would repeat the same mistake

## What Is Already Supported Instead

The runtime already supports the correct national-chart use cases:

- analysis of regime structure
- leadership and polity strain
- finance, trade, diplomacy, and alliance overlays
- comparison against event charts where appropriate

This is the right current role.

## What Would Need To Exist Before Reconsideration

National-chart scan should only be reconsidered if all of the following are true:

1. a distinct scan semantic is defined
   - not a copy of current event/framework scan logic

2. the payload distinguishes national-structure pressure from event-local pressure

3. the output is place-safe
   - meaning it does not imply false first-hostilities localization

4. a benchmark slice exists specifically for national-chart scan use cases

5. the UI clearly separates:
   - national-chart overlay scan
   - event-anchor scan
   - framework scan

## Limited Future Option

If scan support is revisited later, the cleanest first form would be limited, not broad.

For example:

- place-first national overlay scan
- no outbreak semantics
- no raw-cell outbreak ranking
- only domains where national-chart structure is genuinely primary

That would still need benchmark seeding first.

## Operational Outcome

The repo should now treat this as settled for the current phase:

- `national_chart` is intentionally analysis-only
- scan exclusion is a design decision, not a missing feature

That is the correct state for the current runtime.
