# Forensic Corpus Replay Slice 2

## Scope

Second replay-ready forensic case slice promoted from the local forensic books documented in [FORENSIC_CORPUS_EVALUATION_PLAN.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_EVALUATION_PLAN.md).

This slice is intentionally broader than slice 1. It tests whether the current grounded directional layer generalizes across:

- filicide
- parricide
- familicide
- friend / close-associate homicide
- celebrity / public homicide

## Promoted Cases

- `andrea_yates`
- `darlie_routier`
- `lizzie_borden`
- `menendez_brothers`
- `john_list`
- `amityville_defeo`
- `bob_crane`
- `gianni_versace`

## Source-Metadata Basis

### High-confidence prose metadata

- `andrea_yates`
  - drownings began at approximately `9:00 a.m.` on `June 20, 2001`
  - suburban `Houston` home

- `darlie_routier`
  - telephone call placed at `2:31 a.m.` on `June 6, 1996`
  - `Rowlett, Texas`

- `menendez_brothers`
  - police call at `11:47 p.m.` on `August 20, 1989`
  - `Beverly Hills`

- `john_list`
  - killings commenced at `9:00 a.m.` on `November 9, 1971`
  - `Westfield, New Jersey`

- `amityville_defeo`
  - event chart cast for `6:30 p.m.` on `November 13, 1974`
  - Amityville family killings on `Long Island`

- `bob_crane`
  - forensic chart cast for `2:00 p.m.` on `June 29, 1978`
  - `Scottsdale, Arizona`

- `gianni_versace`
  - shooting took place at `8:44 a.m.` on `July 15, 1997`
  - South Beach / `Miami Beach, Florida`

### Medium-confidence OCR-backed metadata

- `lizzie_borden`
  - OCR chart text reads as `11:00 AM EST`
  - `Fall River, Massachusetts`
  - date: `August 4, 1892`

## Implemented Files

- [forensic_case_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2.json)
- [run_forensic_case_replay_slice_2.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_2.py)
- [test_forensic_case_replay_slice_2.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_2.py)

## Intended Next Step

Run this slice through the real `/api/astro-clock/forensic` route and record:

- response success/failure
- directional alignment
- missed axes
- contradicted axes
- category rollups
- whether slice-1 rules generalize without additional tuning
