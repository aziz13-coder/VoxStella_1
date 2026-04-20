# Astro Clock Transits Replay Slice 6 Results

Date: 2026-03-27

## Scope

Slice 6 extends the slice-5 public-crisis cases across the predictor and stream seams.

Promoted cases:

- George W. Bush Iraq address
- Shinzo Abe assassination

Claim level:

- This slice does **not** claim tight predictor localization on war/violent-event dates.
- It does claim that the event-row crisis-support transit survives through:
  - `/api/astro-clock/predictor`
  - `/api/astro-clock/transits/window/stream`
- It does **not** require those crisis-support transits to rank inside the aggregated top-50 predictor summary.

## Root Issue Found

Before this pass, predictor/window/stream derived row predictions from an aggressively truncated per-step hit list.

Observed effect:

- the single `/api/astro-clock/transits` route still exposed the slice-5 crisis-support transit
- but predictor/stream dropped that transit from the event row before predictions were built

Smallest responsible fix:

- keep the visible `top` hits and step scoring narrow
- preserve a deeper per-step prediction candidate pool for row-level prediction derivation

Files changed for the fix:

- [backend/transits_morin.py](C:/Users/sabaa/Downloads/codexhorary/backend/transits_morin.py)
- [backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)
- [frontend/backend/transits_morin.py](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/transits_morin.py)
- [frontend/backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/astro_clock_api.py)

## Automated Coverage

Backend:

- [test_transit_public_crisis_replay_slice_6.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_public_crisis_replay_slice_6.py)
- fixture: [transit_public_crisis_replay_slice_6.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_public_crisis_replay_slice_6.json)

Frontend:

- [transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)

## Results

### George W. Bush Iraq address

- Predictor event row retained: `Mars Quincunx Mercury`
- Stream event row retained: `Mars Quincunx Mercury`
- Predictor event-row prediction count: `36`
- Stream event-row prediction count: `32`
- Nearest predictor peak distance: `19h`
- Nearest stream peak distance: `19h`

Interpretation:

- crisis-support retention is good enough to automate
- localization is still broad, so this remains a support-layer slice rather than a strict peak-localization slice

### Shinzo Abe assassination

- Predictor event row retained: `Jupiter Quincunx Mercury (contra-antiscia)`
- Stream event row retained: `Jupiter Quincunx Mercury (contra-antiscia)`
- Predictor event-row prediction count: `36`
- Stream event-row prediction count: `32`
- Nearest predictor peak distance: `7h`
- Nearest stream peak distance: `7h`

Interpretation:

- both support retention and bounded localization are acceptable for this slice

## Outcome

Slice 6 is promoted as:

- predictor/stream crisis-support retention coverage

It is **not** promoted as:

- precise war/death event localization
- a general transit prediction claim for violent events
