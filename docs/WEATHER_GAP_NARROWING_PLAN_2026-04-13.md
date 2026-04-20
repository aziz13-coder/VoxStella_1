# Weather Gap Narrowing Plan

Status date: 2026-04-13
Implementation status: completed on 2026-04-13

## Scope

This plan narrows the current weather-runtime gaps identified in:

- `docs/WEATHER_RUNTIME_WORKFLOW_AUDIT_2026-04-13.md`

It applies to both execution paths:

1. `analysis`
2. `scan`

The goal is not to widen the runtime quickly.

The goal is to tighten the current seed runtime so that:

- analysis outputs better match the source-backed doctrine
- scan outputs better discriminate useful windows and places
- benchmark results improve for justified reasons rather than looser thresholds

## Current Gaps To Narrow

The main current gaps are:

1. locality is still proxy-only
2. eclipse timing is present in doctrine but absent in active runtime logic
3. wind remains under-discriminated
4. severe convective still loses on control-window competition
5. scan is coherent, but it is still only repeated family analysis rather than a stronger map/path engine
6. runtime family coverage is narrower than the benchmark branch

Not all of these should be addressed at once.

The order matters.

## Plan Order

1. tighten locality and path logic
2. tighten family discrimination in the weakest live families
3. align scan semantics with the tightened analysis logic
4. decide bounded eclipse support
5. only then decide whether any new family should graduate into runtime

## Phase A: Locality And Path Narrowing

This is the highest-leverage gap.

### Why first

The source corpus is much stronger on locality than the runtime.

Right now:

- analysis uses angular/nearest-angle proxies
- scan repeats those same proxies across place and time

That is acceptable for a seed engine, but it is the biggest source mismatch.

### Analysis-side work

1. add explicit locality-strength sub-signals instead of one flat locality note block
2. separate:
   - angle concentration
   - path concentration
   - repeated locality reinforcement across framework/trigger/forecast layers
3. expose a clearer locality-confidence payload in analysis results

### Scan-side work

1. stop treating every location equally once a family has path-sensitive doctrine
2. introduce path/locality-sensitive place-series weighting where the local sources justify it
3. keep the raw-cell list, but improve place-series ranking so scan does not reward broad background pressure more than concentrated target zones

### Acceptance criteria

1. flood and hurricane do not regress in predictive hindcast
2. place-series interpretation becomes more locality-sensitive without hiding raw cells
3. new locality rules are source-justified and family-specific, not generic score inflation

## Phase B: Weak-Family Discrimination

This phase is narrower and should happen after locality improvements start landing.

### Target families

1. `wind_event_pressure`
2. `severe_convective_pressure`

### Why these first

They are the weakest live runtime families:

- wind is still too permissive
- severe convective still loses to nearby competing windows

### Analysis-side work

1. reduce broad generic testimony where the source expects reinforced combinations
2. reward stacked trigger structures more than single-signal activation
3. separate broad seasonally risky periods from sharper event windows

### Scan-side work

1. make scan ranking reflect the tighter family logic instead of only raw repeated pressure
2. improve how place-series distinguish:
   - broad active band
   - concentrated event window
   - path-shifted nearby competitor window

### Acceptance criteria

1. wind improves mainly on control-window competition, not by looser pass rules
2. severe convective improves mainly on target/control separation
3. changes do not degrade flood or hurricane materially

## Phase C: Scan Semantics Tightening

This is partly separate from family scoring.

The scan runtime is coherent, but it still behaves as repeated analysis plus summarization.

That means scan can still over-reward broad pressure fields if the summary semantics are too simple.

### Work

1. keep both:
   - top raw cells
   - top place series
2. make place-series ranking more explicit about:
   - peak sharpness
   - peak window width
   - repeated tied peaks
   - path concentration
3. expose scan metadata that distinguishes:
   - concentrated event candidate
   - sustained background band
   - near-miss competitor window

### Analysis/scan connection

This phase should use the same family logic as analysis.

Scan should not invent a different doctrine layer.

It should be a stronger summary of the same underlying family model.

### Acceptance criteria

1. scan result interpretation becomes clearer without suppressing data
2. graph ranking and ranked-cells view tell the same story more often
3. predictive hindcast failures become easier to attribute to locality, timing, or control competition

## Phase D: Bounded Eclipse Decision

Eclipse timing is a doctrinal gap, but it should not be forced in casually.

### Why later

If eclipse support is added before locality and family discrimination improve, it risks becoming generic signal inflation.

### Work

1. review the weather doctrine corpus specifically for operational eclipse use
2. define a bounded eclipse layer only if the local sources justify:
   - when eclipse timing matters
   - for which families
   - whether it belongs in framework, trigger, or an optional timing overlay
3. if justified, add it first to analysis, then to scan

### Acceptance criteria

1. eclipse logic is family-bounded, not universal
2. benchmark behavior improves or stays stable
3. no eclipse layer is added if the source support is too thin or too vague

## Phase E: Runtime Family Graduation

Only after Phases A-D should the runtime consider expanding beyond the current four families.

### Candidate next families

Only candidates already present in the benchmark branch:

1. `snow / freezing precipitation`
2. `temperature extremes`
3. possibly `drought`

### Decision rule

A benchmark family should not graduate into runtime unless all are true:

1. source doctrine is operational enough
2. historical benchmark coverage is mature enough
3. predictive behavior or family-shape evaluation is good enough to justify runtime maintenance
4. the new family would not simply duplicate an existing runtime family

## Implementation Sequence

The recommended working order is:

1. Phase A on `flood_risk` and `hurricane_pressure`
2. Phase B on `wind_event_pressure`
3. Phase B on `severe_convective_pressure`
4. Phase C on scan-series semantics
5. Phase D bounded eclipse decision
6. Phase E runtime graduation decision

## What Not To Do

Do not:

1. add a generic weather super-score
2. widen scan regions or time bounds as a substitute for better locality logic
3. loosen benchmark thresholds to manufacture pass rate
4. add new runtime families before the current four are better localized and better discriminated
5. add eclipse scoring everywhere just because eclipse doctrine exists somewhere in the corpus

## Implementation Outcome

All five phases were implemented in bounded form:

1. Phase A:
   - locality-strength, path-concentration, and reinforcing-layer metrics were added to the live runtime
   - flood and hurricane now carry narrower locality/path concentration logic in both analysis and scan
2. Phase B:
   - weak-family discrimination was tightened through weighted duplicate-signal reinforcement, severe-convective short-window freshness, and stricter wind-structure handling
3. Phase C:
   - scan series now expose event-focus, peak-window width, recurring-peak breadth, and locality/path concentration
   - recurring equal peaks now widen the peak window instead of collapsing to one arbitrary slice
4. Phase D:
   - eclipse timing is implemented as an explicit deferred runtime decision rather than silent absence or premature scoring
5. Phase E:
   - runtime graduation was reviewed and explicitly deferred; no benchmark-only family graduates into runtime yet

## Current Post-Implementation Baseline

The predictive hindcast rerun after implementation produced:

1. `9` cases
2. `7` alignment passes (`77.8%`)
3. `4` target-window hits (`44.4%`)
4. `3` near passes (`33.3%`)
5. median target percentile `0.9722`
6. median peak distance `6.0h`

This is a real improvement over the prior hardened baseline, but it still does not justify claiming reliable prospective weather prediction.
