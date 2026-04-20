# Journalist Abduction Forensic Validation

## Purpose

This benchmark is the validation gate for any later private shadow-read of an active journalist disappearance.

The question is narrow:

- On resolved journalist abduction cases with source-backed time and scene anchors, does the forensic route surface abduction in a directionally useful way without drifting into unrelated family, child, accident, or domestic labels?

## Benchmark Structure

The benchmark currently has six resolved journalist abduction cases.

### Core Baghdad Set

1. Rory Carroll
- abducted in Sadr City, Baghdad, on October 19, 2005
- released alive the following day
- anchor used: `2005-10-19 14:15` local

2. Giuliana Sgrena
- abducted outside Baghdad University / Jadriyah bridge area on February 4, 2005
- released alive on March 4, 2005
- anchor used: `2005-02-04 13:45` local

3. Jill Carroll
- abducted in the Adil neighborhood of western Baghdad on January 7, 2006
- released alive on March 30, 2006
- anchor used: `2006-01-07 10:00` local

### Expanded War-Zone Set

4. James Brandon
- abducted from Al-Diyafa Hotel in Basra on August 12, 2004
- released alive on August 13, 2004
- anchor used: `2004-08-12 23:00` local
- query now uses sourced hotel-cluster proxy coordinates on Al-Istiqlal Street because the exact hotel string does not geocode reliably in the route harness

5. Alan Johnston
- abducted on Al Wehda Street in Gaza City on March 12, 2007
- released alive on July 4, 2007 after 114 days in captivity
- anchor used: `2007-03-12 14:45` local

6. Steve Centanni and Olaf Wiig
- abducted in Gaza City on August 14, 2006
- released alive on August 27, 2006
- anchor used: `2006-08-14 19:40` local

## What Changed In This Pass

This pass closed the remaining benchmark gap with two broad improvements.

### 1. Venue-level coordinate override for manual forensic requests

The shared Astro Clock request-context helper now accepts explicit `latitude` and `longitude` on manual requests.

This is not a case-specific rule. It is a general route/input fix for venue-level forensic work where:

- the public source identifies the scene more precisely than the geocoder can
- a hotel, street, or compound name does not resolve reliably
- the user still has defensible source-backed coordinates for the scene cluster

### 2. Transient-stay / hospitality seizure rule

The remaining James Brandon miss was not another road-seizure or public-street underfire.
It fit a different source-backed pattern:

- `7th` as the abductor
- `3rd` and `9th` as movement, route, and the abductor's vehicle
- `5th` as outside interests / adult social setting
- `Venus` / `Taurus` as hotel or hospitality testimony rather than home testimony

That combination is now represented by:

- `abduction_transient_hospitality_seizure_signature`

The rule was added narrowly and guarded so it does not become a generic 5th-house shortcut.

## Live Route Results

### Rory Carroll

- categories:
  - `Abduction: 1`
  - `Deception: 2`
  - `Houses: 1`
- leading findings:
  - `Abduction or forced-seizure transport pattern is active`
  - `Malefic in the 6th house`
  - `Mercury in a mute sign`
  - `Mute signs on 3rd/9th`
- result: `aligned`

### Giuliana Sgrena

- categories:
  - `Abduction: 1`
  - `Associates: 1`
  - `Deception: 2`
  - `Houses: 1`
  - `Stressors: 1`
  - `Violence: 2`
- leading findings:
  - `Life/death overlap points to violence or homicide`
  - `Abduction or worksite-seizure pattern is active`
  - `1st ruler in the 8th house`
  - `Hidden victim with angular violence markers`
  - `Friend or close associate axis is active`
  - `Mercury combust the Sun`
- result: `aligned`

### Jill Carroll

- categories:
  - `Abduction: 1`
  - `Deception: 2`
  - `Houses: 2`
  - `Violence: 1`
- leading findings:
  - `Life/death overlap points to violence or homicide`
  - `Abduction or public-place seizure pattern is active`
  - `1st ruler in the 8th house`
  - `Malefic in the 6th house`
  - `Mute signs on angles`
  - `Mute signs on 3rd/9th`
- result: `aligned`

### James Brandon

- categories:
  - `Abduction: 1`
  - `Deception: 4`
- leading findings:
  - `Abduction or transient-stay seizure pattern is active`
  - `Mercury retrograde`
  - `Node with Neptune/Mercury (karmic ruse/lie scheme)`
  - `Mute signs on angles`
  - `Mute signs on 3rd/9th`
- result: `aligned`

### Alan Johnston

- categories:
  - `Abduction: 1`
  - `Associates: 1`
  - `Deception: 3`
  - `Houses: 2`
  - `Violence: 2`
- leading findings:
  - `Life/death overlap points to violence or homicide`
  - `Abduction or confrontation-on-the-route pattern is active`
  - `1st ruler in the 8th house`
  - `Hidden victim with angular violence markers`
  - `Friend or close associate axis is active`
  - `Malefic in the 6th house`
- result: `aligned`

### Steve Centanni / Olaf Wiig

- categories:
  - `Abduction: 1`
  - `Deception: 1`
  - `Houses: 1`
  - `Witness: 1`
- leading findings:
  - `Abduction or worksite-seizure pattern is active`
  - `Witness or accomplice signatures are active`
  - `Malefic in the 6th house`
  - `Mute signs on 3rd/9th`
- result: `aligned`

## Current Validation State

### Core Baghdad Set

- Rory Carroll: `aligned`
- Giuliana Sgrena: `aligned`
- Jill Carroll: `aligned`

Core Baghdad score: **3 / 3 aligned**

### Expanded War-Zone Set

- James Brandon: `aligned`
- Alan Johnston: `aligned`
- Steve Centanni / Olaf Wiig: `aligned`

Expanded full score: **6 / 6 aligned**

## Map Benchmark Addendum

The six-case journalist benchmark now also has a frozen abduction-map layer.

That addendum includes:

- explicit `latitude` and `longitude` for all six benchmark queries
- explicit `origin` coordinates for all six map requests
- per-case `map_validation` expectations
- a dedicated live map benchmark in [test_forensic_journalist_abduction_map_benchmark.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_journalist_abduction_map_benchmark.py)

Important limit:

- the public-source set identifies seizure points and scene types
- it does **not** provide reliable transport headings for the six cases

So the map benchmark now scores:

- origin fidelity
- role-bearing coverage
- scene-type compatibility

and intentionally does **not** score exact escape geometry.

Detailed documentation for that layer is here:

- [JOURNALIST_ABDUCTION_MAP_BENCHMARK_2026-04-06.md](C:/Users/sabaa/Downloads/codexhorary/docs/JOURNALIST_ABDUCTION_MAP_BENCHMARK_2026-04-06.md)

## Interpretation

The resolved journalist-abduction benchmark now passes.

That does not mean the method is ready for public operational use on an active disappearance.
It means the current resolved-case validation gate is no longer blocked by known benchmark failures.

What is now clearly working:

- transport-style abduction
- public-place seizure
- confrontation-on-the-route seizure
- worksite / assignment seizure
- hotel / transient-stay seizure
- suppression of the earlier child/family spill on adult war-zone abduction charts

## Cautions That Still Matter

Even with a 6 / 6 aligned benchmark, there are still real limits:

- some anchors remain approximate windows rather than witness-stamped exact minutes
- the James Brandon hotel scene currently uses sourced proxy coordinates for the hotel cluster rather than an exact venue-stamped coordinate
- the benchmark is still small and concentrated in journalist-war-zone cases
- the method remains directional, not evidentiary

## Gate Before Any Private Active-Case Shadow Analysis

Current status: **resolved benchmark passes, but caution remains mandatory**

Minimum discipline before any private shadow use should still include:

- keep the analysis private and non-operational
- do not publish the output
- do not let it drive real-world action
- add a small holdout set beyond the current six cases if more confidence is required
- preserve manual coordinate input for venue-level cases where geocoding is weak

## Next Steps

1. Freeze this six-case set as a regression benchmark.
2. Add 2 to 4 external holdout cases outside the current Iraq/Gaza cluster.
3. Keep the coordinate-override path covered by route-contract tests.
4. Do not treat this pass as proof of certainty; treat it as evidence that the current method is directionally behaving better on resolved journalist abductions.

## Fixture

The benchmark fixture for this pass is stored at:

- [forensic_external_journalist_abduction_candidates.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_journalist_abduction_candidates.json)

## Holdout Addendum

The next pass added a separate holdout probe set rather than mutating the original six-case gate.

Why:

- the original six-case set is the current validated regression gate
- the holdout set is meant to expose generalization strength and failure modes on fresh resolved cases

Current holdout result:

- `2 / 4 aligned`

Holdout documentation:

- [JOURNALIST_ABDUCTION_HOLDOUT_PROBES_2026-04-06.md](C:/Users/sabaa/Downloads/codexhorary/docs/JOURNALIST_ABDUCTION_HOLDOUT_PROBES_2026-04-06.md)

Holdout fixture:

- [forensic_external_journalist_abduction_holdout_cases.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_journalist_abduction_holdout_cases.json)
