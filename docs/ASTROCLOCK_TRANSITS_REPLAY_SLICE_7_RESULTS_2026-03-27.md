# Astro Clock Transits Replay Slice 7 Results

Date: 2026-03-27

## Scope

Slice 7 adds a bounded marriage-support replay class.

Promoted cases:

- Charles and Diana wedding
- Prince Harry wedding

Claim level:

- This slice does **not** claim that royal wedding dates replay as a clean top prediction title across the transit engine.
- It does claim that the live `/api/astro-clock/transits` route preserves a bounded marriage-support layer on the promoted cases.
- The slice uses case-specific criteria because the current engine often keeps marriage support underneath stronger home, honor, or child-related clusters.

## Automated Coverage

Backend:

- [test_transit_marriage_support_replay_slice_7.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_marriage_support_replay_slice_7.py)
- fixture: [transit_marriage_support_replay_slice_7.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_marriage_support_replay_slice_7.json)

Frontend:

- [transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)

## Results

### Charles and Diana wedding

- Event date retained three explicit marriage predictions:
  - `Jupiter Semi-sextile Mercury`
  - `Jupiter Trine Sun (antiscia)`
  - `Jupiter Sextile Sun (contra-antiscia)`
- Nearby control retained only one explicit marriage prediction:
  - `Jupiter Semi-sextile Mercury`
- Additional event-date marriage support also remained visible in the transit hits, including `Venus Sextile Mercury`
- Measured event/control prediction count: `3` vs `1`

Interpretation:

- this case is replay-safe as a marriage-prediction-cluster example
- it is **not** promoted as a clean top-prediction-title example, because the absolute top prediction still sits in a broader home cluster

### Prince Harry wedding

- Event date retained an explicit partner-house support hit:
  - `Venus Conjunction C7`
- That hit carried the keyword family:
  - `engagement`
  - `family_celebration`
  - `marriage`
  - `partnership_strengthened`
  - `wedding`
- Nearby control retained only a weaker 7th-house marriage-support hit:
  - `Mars Semi-sextile C7 (contra-antiscia)`
- Measured marriage-specific support strength: `36.0` vs `18.0`

Interpretation:

- this case is replay-safe as an explicit 7th-house marriage-support example
- it is **not** promoted as a top-prediction-title example

## Outcome

Slice 7 is promoted as:

- bounded marriage-support coverage on the live single `/api/astro-clock/transits` route

It is **not** promoted as:

- a general marriage transit slice
- a clean wedding-date localization claim
- evidence that every family milestone class is replay-safe

## Implementation Note

- No production transit logic changed in this pass.
- Slice 7 is additive replay coverage only.
