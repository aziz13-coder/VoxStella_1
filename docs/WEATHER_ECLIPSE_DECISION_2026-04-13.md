# Weather Eclipse Decision

Status date: 2026-04-13

## Decision

Eclipse timing remains deferred in the live weather runtime.

It is now explicit in runtime metadata, but it is not active scoring.

## Why

The local source picture is not empty, but it is still too thin for live weather-family scoring.

What the current source base supports well:

1. seasonal ingress framework
2. lunar-phase trigger layering
3. family-specific weather logic
4. locality/path concentration work

What it does not yet support well enough in the current runtime branch:

1. family-bounded eclipse rules with clear operational thresholds
2. evidence that eclipse timing improves predictive behavior more than it inflates generic pressure

## Runtime Implementation

The runtime now records:

1. `eclipse_overlay.status = deferred`
2. `eclipse_overlay.decision = not_active_in_runtime`
3. `eclipse_runtime_deferred` as a research flag

That makes the decision visible without pretending the scoring is mature.

## Practical Meaning

This means:

1. eclipse timing is acknowledged
2. eclipse timing is not silently ignored
3. eclipse timing is not allowed to widen the live weather score yet

## Revisit Gate

Eclipse timing should only be reconsidered after both are true:

1. the current four runtime families are more stable on locality and control-window competition
2. the local corpus yields family-specific eclipse rules strong enough to benchmark separately
