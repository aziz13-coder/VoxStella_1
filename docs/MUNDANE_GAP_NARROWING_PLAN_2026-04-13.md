# Mundane Gap Narrowing Plan

Date: 2026-04-13

## Purpose

This plan narrows the concrete gaps identified in the current-state audit.

It is ordered by impact and dependency, not by convenience.

The main principle is:

- fix policy enforcement before adding new scoring
- fix scan semantics before widening scan scope
- fix locality implementation before deepening eclipse-driven claims
- fix framework depth only after the runtime stops blurring chart roles

## Implementation Status

Status as of 2026-04-13:

- Phase A: implemented
- Phase B: implemented
- Phase C: implemented in runtime with explicit proxy limits documented
- Phase D: implemented as a doctrine inventory and bounded runtime shortlist
- Phase E: implemented as a decision to keep `national_chart` scan analysis-only

The remaining work after this plan is not phase completion. It is later hardening:

- richer eclipse locality evidence if stronger territorial visibility sources are added
- broader revolution-family promotion only after benchmark seeding
- a future reconsideration of national-chart scan only if a distinct scan semantic is justified

## Gaps To Narrow

The audit identified 5 main gaps:

1. `war_outbreak` is still too permissive outside `war_event`
2. scan semantics still privilege `top_cells` over `top_places`
3. eclipse visibility and territorial relevance are only partial
4. revolution/framework handling is thinner than the doctrine corpus
5. `national_chart` is analysis-strong but scan-disabled

## Order Of Work

## Phase A. Enforce Chart-Type / Domain Semantics

### Goal

Stop the runtime from treating chart types as interchangeable when the doctrine clearly does not.

### Scope

- harden `war_outbreak` semantics so `war_event` is the preferred opening-hostilities chart in runtime, not only in docs and UI
- down-weight or restrict `war_outbreak` on:
  - `aries_ingress`
  - `lunation`
  - `eclipse`
- apply the same narrowing in both execution paths:
  - analysis mode
  - scan mode
- keep those chart types usable for:
  - `campaign_escalation`
  - `military_reversal`
  - broader framework/trigger war work
- reduce practical reliance on compatibility umbrellas in scoring:
  - `war_conflict`
  - `government_stability`
- enforce the policy at three layers:
  - catalog / frontend availability
  - request validation
  - backend scoring behavior

### Deliverables

- explicit backend enforcement policy for chart-type/domain pairings
- revised scoring path for `war_outbreak`
- scan-policy enforcement so non-`war_event` scan pairings do not present outbreak semantics as if they were event-anchor scans
- benchmark additions proving:
  - `war_event + war_outbreak` remains strongest
  - non-`war_event` outbreak pairings no longer overstate first-hostilities meaning

### Acceptance

- `war_outbreak` on non-`war_event` charts either:
  - refuses execution, or
  - returns a clearly reduced research-gated form with lower calibration confidence
- the same rule holds in scan mode:
  - invalid pairings are blocked, or
  - scan output is explicitly downgraded and does not masquerade as opening-hostilities localization
- no regression on existing war benchmarks

## Phase B. Correct Scan Semantics

### Goal

Make scan outputs reflect doctrinal meaning instead of raw-cell convenience.

### Scope

- return `top_places` and `top_cells` as separate first-class outputs
- stop letting long plateaus or repeated tied cells dominate the user’s first read
- make scan calibration explicit at both levels:
  - cell-level
  - place-series level
- review whether some scan modes should default to place-first output

### Deliverables

- revised scan payload contract
- place-deduped ranking path
- explicit top-place inspector path in frontend
- benchmark additions for:
  - plateau handling
  - repeated-cell deduping
  - framework-chart scan behavior

### Acceptance

- a framework chart no longer looks like a fake outbreak spike simply because repeated early cells sort first
- graph and inspector agree on the same primary ranking mode

## Phase C. Implement Real Eclipse Locality

### Goal

Bring eclipse handling closer to the doctrine before adding more eclipse-weighted scoring.

### Scope

- distinguish:
  - generic nearest eclipse logic
  - geographic visibility relevance
  - territorial/polity relevance
- add stronger eclipse locality data to runtime context
- only then revisit eclipse-domain weighting

### Deliverables

- eclipse locality model
- runtime payload additions for:
  - visibility classification
  - territorial relevance
  - locality confidence
- doctrine memo for what is implemented versus what remains approximate
- benchmarks for visible vs non-visible eclipse cases where source support exists

### Acceptance

- eclipse outputs are no longer relying mainly on node-orb and activation hits
- locality is visible in the result contract, not hidden in internal heuristics

## Phase D. Deepen Framework / Revolution Handling

### Goal

Close the gap between the current chart set and the broader revolution doctrine, but only after chart-role enforcement is stable.

### Scope

- review what the current corpus justifies beyond:
  - Aries ingress
  - lunation
  - eclipse
  - war event
  - national chart
- identify which framework or revolution structures are strong enough for runtime
- do not widen chart families until chart-role boundaries are stable

### Deliverables

- doctrine inventory for broader revolution hierarchy
- shortlist of runtime-worthy additions
- explicit “not yet justified” list for the rest

### Acceptance

- any new framework addition is source-backed and benchmark-seeded before runtime promotion

## Phase E. Decide National-Chart Scan Support

### Goal

Resolve whether `national_chart` should become scan-enabled or remain analysis-only by design.

### Scope

- evaluate the scan use cases where `national_chart` is doctrinally appropriate
- determine:
  - where it helps
  - where it misleads
  - where capital or event context is still superior
- if enabled, define separate scan semantics instead of reusing all current scan assumptions blindly

### Deliverables

- decision memo:
  - enable
  - defer
  - or enable in limited modes only
- if enabled:
  - payload contract
  - frontend workflow
  - benchmark slice

### Acceptance

- scan support only ships if it adds doctrinal clarity, not just option count

## Recommended Sequence

1. Phase A: enforce chart-type/domain semantics
2. Phase B: correct scan semantics
3. Phase C: implement eclipse locality
4. Phase D: deepen framework/revolution handling
5. Phase E: decide national-chart scan support

This order matters.

Doing Phase C before Phase A would deepen eclipse logic inside a still-blurry chart-role system.

Doing Phase E before Phase B would expand scan scope before fixing scan meaning.

Doing Phase D before A/B would widen the model surface before correcting the current semantic leaks.

Phase A and Phase B overlap intentionally in scan mode:

- Phase A narrows which chart/domain pairings are allowed to behave like outbreak scans.
- Phase B fixes how valid scan outputs are ranked and presented after that narrowing is in place.

## What Should Not Be Done Yet

- do not add more war weights before Phase A
- do not widen scan to more chart types before Phase B
- do not deepen eclipse-domain scoring before Phase C
- do not add more framework chart families before Phase D review
- do not enable `national_chart` scan by default before Phase E decision work

## Completion Note

This plan is now closed.

The runtime work completed under it does three concrete things:

1. narrows chart-type/domain pairings in both analysis and scan
2. separates place-series scan meaning from raw-cell convenience
3. documents eclipse locality, framework layering, and the national-chart scan decision explicitly rather than leaving them implied
