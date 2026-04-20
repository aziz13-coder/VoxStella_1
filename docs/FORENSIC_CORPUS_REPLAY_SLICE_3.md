# Forensic Corpus Replay Slice 3

## Scope

Third replay-ready forensic case slice promoted from the local forensic books documented in [FORENSIC_CORPUS_EVALUATION_PLAN.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_EVALUATION_PLAN.md).

This slice intentionally moves away from the already aligned slice-1 and slice-2 homicide families and pressure-tests:

- source-explicit spouse-linked homicide
- parental / celebrity homicide
- child-victim family homicide with disputed public narrative
- aviation disaster
- maritime disaster

## Promoted Cases

- `ronnie_lee_bakley`
- `marvin_gaye`
- `alice_crimmins`
- `air_france_447`
- `costa_concordia`

## Source-Metadata Basis

### High-confidence prose metadata

- `ronnie_lee_bakley`
  - shooting took place at approximately `9:40 p.m.` on `May 4, 2001`
  - `Studio City, California`

- `marvin_gaye`
  - police were called at `11:38 a.m.` on `April 1, 1984`
  - `West Adams`, Los Angeles

- `alice_crimmins`
  - documented phone call at `10:00 a.m.` on `July 14, 1965`
  - `Kew Gardens`, Queens, New York

- `air_france_447`
  - author explicitly used take-off at `7:03 PM BZT`
  - `Rio de Janeiro, Brazil`

- `costa_concordia`
  - ship set sail at `7:30 PM` on `January 13, 2012`
  - `Civitavecchia, Italy`

## Implemented Files

- [forensic_case_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3.json)
- [run_forensic_case_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_3.py)
- [test_forensic_case_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_3.py)

## Intended Next Step

Run this slice through the real `/api/astro-clock/forensic` route and record:

- response success/failure
- directional alignment
- missed axes
- contradicted axes
- category rollups
- whether the current direction layer can handle disaster cases without collapsing into family/child/domestic false positives

## Current Status

The third actual route replay has now been captured in:

- [FORENSIC_CORPUS_REPLAY_SLICE_3_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_3_RESULTS.md)
- [forensic_case_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3_results.json)

The follow-up knowledge-layer fix pass is documented in:

- [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md)
