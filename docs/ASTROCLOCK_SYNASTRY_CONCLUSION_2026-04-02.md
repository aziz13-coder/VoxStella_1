# AstroClock Synastry Conclusion

Date: 2026-04-02

Related exploration:

- `docs/ASTROCLOCK_SYNASTRY_EXPLORATION_2026-04-02.md`

## Conclusion

AstroClock already has the right underlying structure to support a synastry feature.

The main conclusion is:

1. Synastry should be built on AstroClock's existing chart and context infrastructure.
2. It should not introduce a separate astrology calculation pipeline.
3. It should use two normalized chart bundles as inputs and add a dedicated synastry interpretation layer on top.

## What We Reuse

The strongest reusable pieces are:

- shared chart generation through the horary engine
- AstroClock chart bundle helpers
- realtime/manual/saved-snap source handling
- timezone, location, and house-system normalization
- dashboard enrichments such as aspects, receptions, house rulers, fixed stars, sect, and metrics
- the existing dual-source UX pattern already used by Transits

This means the foundation for synastry already exists.

## What We Do Not Reuse As The Core Logic

These systems should not become the synastry algorithm itself:

- transit predictor ranking and event-family logic
- election scorers
- forensic case rules

Those are feature-specific interpretation layers for different product goals.

## Architectural Decision

The recommended architecture for synastry is:

1. Resolve chart A from one of:
   - active AstroClock context
   - saved snap
   - manual birth data
2. Resolve chart B from one of:
   - saved snap
   - manual birth data
   - optionally the active chart if needed later
3. Build two chart bundles using the existing AstroClock backend helpers.
4. Pass both bundles into a new synastry service.
5. Return synastry-specific outputs such as:
   - cross-chart aspects
   - mutual receptions across charts
   - house overlays
   - supportive and difficult links
   - summary blocks or score buckets

## Product Direction

Synastry should be introduced as its own AstroClock feature surface, not folded directly into the main `AstroClock.jsx` shell logic.

Backend logic should also live in a dedicated synastry service/module, even if the route is ultimately exposed from the AstroClock blueprint.

## Next Step

The correct next step is a synastry design/spec pass, not implementation yet.

That spec should define:

1. source-A and source-B input rules
2. first-version outputs
3. scoring vs narrative expectations
4. classical-only vs optional modern support
5. backend service boundaries and API shape

## Final Decision

Synastry is feasible inside the current AstroClock architecture.

The right approach is to reuse AstroClock's chart-bundle and source-selection infrastructure, then build a new pair-analysis layer for relationship logic instead of extending transit or election scoring beyond their intended purpose.
