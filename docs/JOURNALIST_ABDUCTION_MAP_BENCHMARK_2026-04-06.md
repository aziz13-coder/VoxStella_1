# Journalist Abduction Map Benchmark

## Purpose

This pass completed three follow-up tasks on top of the resolved journalist-abduction validation set:

1. freeze explicit origin coordinates for all six journalist cases
2. add a live abduction-map benchmark that compares map output to source-backed scene facts without inventing transport headings
3. isolate and remove the stray Moon fallback warning that appeared on venue-level manual forensic requests

## What Was Added

### 1. Explicit benchmark coordinates

All six cases in [forensic_external_journalist_abduction_candidates.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_journalist_abduction_candidates.json) now carry:

- explicit `latitude`
- explicit `longitude`
- explicit `origin`
- `map_validation` expectations

This freezes both:

- chart calculation coordinates
- abduction-map origin coordinates

so the benchmark no longer depends on live geocoder drift.

### 2. Live abduction-map benchmark

Added:

- [test_forensic_journalist_abduction_map_benchmark.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_journalist_abduction_map_benchmark.py)

The benchmark validates three things:

- the route returns `abduction_map` for all six cases
- the echoed map origin matches the frozen fixture origin
- the returned role bearings include the minimum scene-relevant roles for each case

### 3. Moon fallback warning fix

The stray warning was real, but it was not coming from the primary chart used by the forensic route.

Root cause:

- `compute_cusp_aspects()` builds a future Astro Clock snapshot to classify cusp-aspect phase
- that future snapshot was receiving only `location` and `timezone`
- on hard-to-geocode venue strings, especially the Basra hotel-cluster query, the future snapshot could degrade into an empty chart shape
- that empty future chart triggered the `Moon position not found in chart` warning even though the main forensic response still had a correct Moon payload

Resolution:

- `compute_cusp_aspects()` now accepts `latitude` and `longitude`
- `_build_dashboard_payload()` now forwards the active chart coordinates into that future snapshot helper
- `AstroClockEngine._calculate_moon_state()` was also hardened to check serialized top-level `planets` before falling back

This is a broad infrastructure fix, not a James-Brandon-only patch.

## Scoring Rule For The Map Benchmark

The new benchmark does **not** pretend to score actual abductor travel headings.

Reason:

- the public sources for this six-case set identify the seizure point or the scene type
- they do **not** generally publish a reliable transport heading, turn sequence, or route vector after the seizure

That means the benchmark can responsibly score:

- origin fidelity
- role-bearing coverage
- scene-type compatibility

It cannot responsibly score:

- exact escape direction
- exact transport corridor
- exact destination heading

So the fixture explicitly marks all six cases as:

- `geometry_status: not_scored_due_to_missing_public_heading`

This is deliberate and correct. It avoids fabricating certainty from public reporting that does not contain that level of movement detail.

## Current Frozen Origins

### Rory Carroll

- origin: `33.3905897, 44.4570662`
- basis: stable Sadr City district proxy
- required roles: `H7_ruler`, `H3_ruler`, `Moon`

### Giuliana Sgrena

- origin: `33.2726951, 44.3795485`
- basis: Baghdad University / Jadriyah public-location proxy
- required roles: `H7_ruler`, `H3_ruler`, `H12_ruler`

### Jill Carroll

- origin: `33.3331581, 44.3091987`
- basis: Adil district proxy
- required roles: `H7_ruler`, `H3_ruler`, `Moon`

### James Brandon

- origin: `30.51624, 47.84212`
- basis: source-backed Al-Istiqlal Street hotel-cluster proxy
- required roles: `H7_ruler`, `H3_ruler`, `H12_ruler`

### Alan Johnston

- origin: `31.5050311, 34.4641381`
- basis: Gaza City proxy for the Al Wehda Street seizure
- required roles: `H7_ruler`, `H3_ruler`, `H12_ruler`

### Steve Centanni / Olaf Wiig

- origin: `31.5050311, 34.4641381`
- basis: Gaza City proxy for the Omar al-Mukhtar Street ambush
- required roles: `H7_ruler`, `H3_ruler`, `H12_ruler`

## Live Route State

All six benchmark cases now return:

- `abduction_map`
- `origin_source: query_origin`
- the required role-bearing set for the case

Representative live state:

### Rory Carroll

- categories: `Abduction`, `Deception`, `Houses`
- map roles: `H1_ruler`, `H7_ruler`, `H3_ruler`, `H8_ruler`, `H12_ruler`, `Moon`

### Giuliana Sgrena

- categories: `Abduction`, `Associates`, `Deception`, `Houses`, `Stressors`, `Violence`
- map roles: `H1_ruler`, `H7_ruler`, `H3_ruler`, `H8_ruler`, `H12_ruler`, `Moon`

### Jill Carroll

- categories: `Abduction`, `Deception`, `Houses`, `Violence`
- map roles: `H1_ruler`, `H7_ruler`, `H3_ruler`, `H8_ruler`, `H12_ruler`, `Moon`

### James Brandon

- categories: `Abduction`, `Deception`
- map roles: `H1_ruler`, `H7_ruler`, `H3_ruler`, `H8_ruler`, `H12_ruler`

### Alan Johnston

- categories: `Abduction`, `Associates`, `Deception`, `Houses`, `Violence`
- map roles: `H1_ruler`, `H7_ruler`, `H3_ruler`, `H8_ruler`, `H12_ruler`

### Steve Centanni / Olaf Wiig

- categories: `Abduction`, `Deception`, `Houses`, `Witness`
- map roles: `H1_ruler`, `H7_ruler`, `H3_ruler`, `H8_ruler`, `H12_ruler`, `Moon`

## Validation

Executed:

```powershell
python -m pytest -q tests\test_forensic_route_contract.py tests\test_forensic_journalist_abduction_benchmark.py tests\test_forensic_journalist_abduction_map_benchmark.py backend\test_astro_clock_dashboard_geocoding.py
python -m pytest -q tests\test_forensic_direction_rules.py tests\test_forensic_drift_guards.py tests\test_forensic_features.py tests\test_forensic_route_contract.py tests\test_forensic_journalist_abduction_benchmark.py tests\test_forensic_journalist_abduction_map_benchmark.py backend\test_astro_clock_dashboard_geocoding.py
```

Results:

- targeted map/route/dashboard set: `20 passed`, `1 warning`, `18 subtests passed`
- broader targeted forensic matrix: `57 passed`, `1 warning`, `18 subtests passed`

Remaining warning:

- external `pytz` deprecation warning only

The Basra no-origin request was rechecked directly after the fix and no longer emitted:

- `Moon position not found in chart`

## Current Conclusion

The original journalist benchmark is now documented in two layers:

- forensic output alignment
- abduction-map output alignment

The map benchmark is intentionally conservative.
It validates what the public sources actually support:

- seizure-point fidelity
- stable origin coordinates
- scene-relevant role bearings

It does not pretend to validate route headings that the public record does not provide.
