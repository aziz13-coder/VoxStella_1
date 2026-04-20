# Mundane Eclipse Locality Memo

Date: 2026-04-13

## Purpose

This memo records what the runtime now implements for eclipse locality, what remains approximate, and why the current implementation stops where it does.

It closes Phase C of the gap-narrowing plan without pretending the runtime now has a full astronomical visibility engine.

## Doctrine Baseline

The local corpus is consistent on the main point:

- eclipses matter more when they are visible for the place concerned
- angular eclipses matter more than non-angular eclipses
- territorial scope matters; a regional or national judgment should not treat every eclipse as equally relevant everywhere

The strongest local references already in the benchmark corpus are:

- `green_visible_angular_eclipse`
- `bonatti_regional_clime_extent`
- `watters_eclipse_degree_activation`
- `green_royal_eclipse_leadership_transition`

These are enough to justify adding runtime locality structure.

They are not enough to justify a high-confidence physical-visibility map for every eclipse and polity.

## What The Runtime Now Does

For `eclipse` chart resolution, the runtime now adds an explicit `eclipse_locality` payload.

It carries:

- `visibility_classification`
- `visibility_status`
- `territorial_relevance`
- `locality_confidence`
- `observed_body`
- `observed_house`
- `visibility_scope`
- `summary`

The current logic is:

1. Resolve the nearest eclipse chart.
2. Determine whether the observed eclipse body is above or below the horizon in that chart.
3. Treat that as a locality proxy, not as literal visibility proof.
4. Combine that with the request context:
   - `event_chart`
   - `capital_chart`
   - `regional_chart`
   - `national`
   - `global`
5. Return a territorial relevance label and a confidence level.

## Implemented Classifications

### Visibility

- `above_horizon_proxy`
- `below_horizon_proxy`
- `unknown_proxy`

### Visibility Status

- `locally_observable_proxy`
- `not_locally_observable_proxy`
- `approximate`

### Territorial Relevance

- `event_locality`
- `capital_scope`
- `regional_scope`
- `national_scope`
- `global_scope`

### Confidence

- `moderate_proxy`
- `low_proxy`

## Why This Is Still A Proxy

The runtime does not yet compute:

- eclipse-path geography
- total versus partial visibility by territory polygon
- obscuration magnitude by place
- sunrise/sunset edge cases for visibility
- nation-wide visibility masks

Those are the missing pieces that would be needed for a real visibility engine.

The current implementation therefore narrows the gap by making locality explicit and inspectable, not by claiming physical-visibility precision that the corpus and tooling do not yet justify.

## What Improved Relative To The Old State

Before this pass, eclipse handling was mainly:

- nearest-eclipse selection
- node-orb logic
- later activation hits

Now the result contract also tells you:

- whether the eclipse is locally above or below the horizon in proxy terms
- whether the current judgment is event-local, capital, regional, national, or global
- how confident the runtime is in that locality reading

That is materially closer to the doctrine than a pure node-orb model.

## What Is Still Not Justified

The runtime should still not do any of the following:

- rank eclipses as if territorial visibility were exact astronomy
- raise eclipse-domain weights simply because an eclipse exists
- treat proxy locality as final locality
- widen eclipse scoring more aggressively until stronger visible-vs-non-visible benchmark cases are added

## Current Operational Position

The runtime now supports:

- explicit eclipse locality metadata
- research-visible proxy confidence
- chart-output inspection of territorial relevance

The runtime does not yet support:

- strict eclipse visibility validation by place
- doctrine-clean territorial weighting across all eclipse use cases

That is acceptable for the current system state.

It closes the hidden-locality gap without inventing false precision.
