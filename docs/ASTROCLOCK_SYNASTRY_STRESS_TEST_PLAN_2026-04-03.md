# AstroClock Synastry Stress Test Plan

Date: 2026-04-03

## Goal

Stress test the new synastry engine so we can trust it under:

1. large input variation
2. chart edge cases
3. option-toggle combinations
4. directional overlay asymmetry
5. score and evidence stability across small chart perturbations

The current test suite proves the report shape and some governed rule activation. It does not yet prove that the engine is stable, well-bounded, or resistant to odd chart inputs.

## Implementation Status

Initial Phase 1 coverage is now in place:

1. deterministic seeded chart-pair fixtures in `backend/synastry_stress_support.py`
2. invariant stress coverage in `backend/test_synastry_stress_invariants.py`
3. option-matrix stress coverage in `backend/test_synastry_stress_options.py`
4. swap-direction symmetry coverage in `backend/test_synastry_stress_symmetry.py`

This means the plan is no longer purely aspirational. The first execution layer now exists and should run on every synastry regression pass.

Phase 2 coverage is also now in place:

1. perturbation stability coverage in `backend/test_synastry_stress_perturbation.py`
2. surgical boundary fixtures in `backend/test_synastry_stress_boundaries.py`
3. catalog-wide rule-family coverage accounting in `backend/test_synastry_rule_family_coverage.py`

The stress plan now covers doctrinal stability, threshold edges, and dead-rule detection in addition to basic report validity.

## What We Need To Prove

### 1. Engine safety

The engine should never crash or emit malformed output when given:

1. sparse chart payloads
2. unusual house layouts
3. missing optional points
4. extreme longitudes near sign and house boundaries
5. option matrices across modern planets, nodes, Chiron, and orb profiles

### 2. Output integrity

Every report should preserve core invariants:

1. every category score is finite and between `0` and `100`
2. `overall` exists and exposes components
3. negative categories keep negative polarity
4. evidence items carry source lineage and rule-family IDs
5. supportive and challenging links are sorted and internally coherent
6. governance accurately reflects active points and rule families

### 3. Doctrinal stability

Small input changes should produce proportionate output changes.

Examples:

1. moving an aspect from exact to slightly wider should reduce strength, not create wild swings
2. disabling modern planets should remove only the modern-layer evidence
3. swapping chart A and chart B should preserve symmetric structure while only directional overlays change
4. moving a planet across a house boundary should change only the overlay-related evidence it logically affects

### 4. Product reliability

The report should still feel usable under stress:

1. no duplicated or contradictory summary lines
2. no empty cards when evidence exists
3. no evidence bursts that overwhelm the UI with junk
4. no report-time blowups on larger stress runs

## Stress Test Layers

### Layer 1. Hard invariants

Add a dedicated invariant suite that runs the engine on many chart pairs and checks:

1. report generation succeeds
2. all required sections exist
3. every score is finite and bounded
4. `summary.overall_components` exists and uses numeric values
5. every evidence item has:
   - `source_key`
   - `source_anchor`
   - `rule_family_id`
6. governance lists remain deduplicated

This is the first safety net and should run on every PR.

### Layer 2. Option-matrix stress

Run a fixed corpus through all supported synastry options:

1. `include_modern = true/false`
2. `include_nodes = true/false`
3. `include_chiron = true/false`
4. `orb_profile = tight/balanced/wide`

What to assert:

1. modern-only rule families vanish when modern points are off
2. nodal families vanish when nodes are off
3. Chiron families vanish when Chiron is off
4. `wide` should not yield fewer aspect candidates than `tight`
5. the report remains valid under every combination

### Layer 3. Symmetry and directional asymmetry

For each chart pair, run:

1. `A -> B`
2. `B -> A`

Expected behavior:

1. symmetric aspect families and receptions should remain broadly consistent
2. directional overlay families may change
3. total support/challenge should stay in the same general band
4. the engine should not completely invert the relationship just because the charts are swapped unless the directional evidence is truly dominant

This is where we catch hidden one-sided weighting bugs.

### Layer 4. Perturbation testing

Take a stable corpus and slightly move planetary longitudes:

1. `±0.1°`
2. `±0.25°`
3. `±0.5°`
4. `±1.0°`

Use this to measure:

1. exactness sensitivity
2. abrupt score cliffs near aspect cutoffs
3. abrupt score cliffs near house-entry boundaries
4. summary instability from tiny coordinate changes

This should produce a delta report, not only pass/fail.

### Layer 5. Boundary tests

Create hand-built fixtures around the boundaries most likely to break logic:

1. planets at `29°59'` and `0°01'`
2. points exactly on angles
3. planets just inside and just outside orb limits
4. house cusp crossing cases
5. chart pairs with nearly identical longitudes
6. charts with heavy stacking in one sign or one house

These are not random tests. They are surgical doctrine-edge fixtures.

### Layer 6. Missing-data tolerance

Feed reduced chart bundles deliberately missing:

1. optional points
2. speed fields
3. retrograde flags
4. some house metadata
5. one or more optional governance fields

Expected behavior:

1. graceful degradation
2. no crashes
3. no invalid evidence items
4. no misleading claims that depend on absent data

### Layer 7. Corpus snapshot regression

Build a named corpus of real or semi-real pairs and snapshot the results.

Recommended corpus groups:

1. strongly harmonious pair
2. high chemistry but unstable pair
3. low chemistry but strong attachment pair
4. high burden / Saturn-heavy pair
5. strong lack-filling pair
6. modern-planet-sensitive pair
7. nodal-heavy pair
8. asymmetrical overlay pair

What to snapshot:

1. category scores
2. top supportive links
3. top challenging links
4. active source keys
5. active rule-family IDs
6. summary lines

This becomes the release-regression suite.

### Layer 8. Rule-family coverage

Measure whether each governed rule family actually fires in at least one test fixture.

This matters because source-governed logic can quietly go dead without breaking the report shape.

Coverage targets:

1. aspect families
2. element families
3. overlay families
4. reception families
5. partnership-ruler families
6. compensation families:
   - element lack fill
   - modality lack fill
   - empty-house fill
   - natal activation
   - hemisphere balance
   - sign-house affinity
   - directional overlay imbalance

### Layer 9. Performance burn

Run a medium-size stress batch and record:

1. total runtime
2. average runtime
3. `p95` runtime
4. slowest fixtures
5. option combinations that cause cost spikes

Initial target:

1. `500` to `1,000` chart-pair reports in one run
2. all option combinations sampled
3. no pathological slowdown from evidence expansion

## Data Strategy

### A. Hand-authored doctrinal fixtures

Use explicit chart pairs designed to trigger one major family at a time.

Purpose:

1. easy debugging
2. rule-family coverage
3. doctrinal sanity checks

### B. Seeded synthetic generator

Build a reproducible generator for synthetic chart pairs.

Recommended behavior:

1. deterministic seed input
2. valid angle and house structure
3. configurable inclusion of modern points, nodes, and Chiron
4. optional clustered-sign and clustered-house modes
5. optional near-threshold aspect mode

Purpose:

1. broad combinatorial pressure
2. repeatable failures
3. scalable stress runs

### C. Golden corpus

Maintain a small, curated set of named chart pairs for regression snapshots.

Purpose:

1. release comparison
2. human review of score drift
3. detection of unintended interpretation changes

## Metrics To Capture

Every stress run should emit machine-readable metrics:

1. run seed
2. report count
3. failure count
4. exception types
5. average runtime
6. `p95` runtime
7. category score ranges
8. max score deltas under perturbation
9. rule-family hit counts
10. option-matrix failure map

These metrics matter more than a raw "all tests passed."

## Recommended Test Files

### Backend pytest

Add these suites:

1. `backend/test_synastry_stress_invariants.py`
2. `backend/test_synastry_stress_options.py`
3. `backend/test_synastry_stress_symmetry.py`
4. `backend/test_synastry_stress_perturbation.py`
5. `backend/test_synastry_rule_family_coverage.py`

### Scripted runner

Add one non-PR stress runner:

1. `backend/run_synastry_stress.py`

Purpose:

1. large seeded batches
2. JSON/CSV metrics export
3. reproducible failure reproduction

## Pass Criteria

The synastry engine passes the first stress-test milestone when:

1. `1,000` seeded reports run without crashes
2. every report satisfies output invariants
3. all key rule families are exercised by at least one fixture
4. swap-direction runs stay within expected stability bands
5. perturbation deltas stay explainable and bounded
6. option toggles only affect the families they are meant to affect
7. no severe runtime spikes appear in the performance batch

## Priority Order

### Phase 1

Implement first:

1. invariant suite
2. option-matrix suite
3. symmetry suite

These give the fastest protection against silent logic breakage.

### Phase 2

Implement next:

1. perturbation suite
2. boundary fixtures
3. rule-family coverage

These improve trust in doctrine behavior.

### Phase 3

Implement after that:

1. seeded synthetic runner
2. golden corpus snapshots
3. performance burn reporting

These are best for pre-release confidence and long-term maintenance.

## Immediate Next Step

The cleanest next implementation step is:

1. add `test_synastry_stress_invariants.py`
2. add a small seeded chart-pair generator helper
3. run `100` chart pairs locally as the first batch

That will tell us very quickly whether the new synastry engine is robust or only well-structured on curated examples.
