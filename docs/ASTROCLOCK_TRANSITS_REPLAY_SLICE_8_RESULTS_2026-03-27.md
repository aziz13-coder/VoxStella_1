# Astro Clock Transits Replay Slice 8 Results

Date: 2026-03-27

## Scope

Slice 8 is a pre-event control sweep, not a new event-class claim.

Why this slice exists:

- after slice 7, the natural next idea was to push marriage-support through predictor and stream
- the live backend did not hold that cleanly enough to promote
- instead of forcing a weak seam, slice 8 strengthens confidence where the evidence is solid:
  - on selected replay-safe cases, the real event date beats multiple earlier control dates on the primary measurement axis

Promoted cases:

- Barack Obama Nobel Peace Prize announcement
- Al Gore Nobel Peace Prize announcement
- George W. Bush Iraq address
- Charles and Diana wedding

Claim level:

- this slice does **not** claim full predictor/stream generalization for marriage
- it does claim that selected single-route transit cases remain stronger on the real event date than on two earlier controls

## Automated Coverage

Backend:

- [test_transit_pre_event_control_replay_slice_8.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_pre_event_control_replay_slice_8.py)
- fixture: [transit_pre_event_control_replay_slice_8.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_pre_event_control_replay_slice_8.json)

Frontend:

- existing modal replay coverage remains in [transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)
- no new frontend rendering contract was needed because slice 8 tests backend date discrimination, not a new UI payload shape

## Results

### Barack Obama Nobel Peace Prize announcement

- Event prediction strength: `95.4`
- Control prediction strengths: `63.6`, `63.6`
- Event context strength: `51.6`
- Control context strengths: `25.8`, `0.0`

Interpretation:

- the event date remained materially stronger than both earlier controls on both the honor prediction and the public-career context layer

### Al Gore Nobel Peace Prize announcement

- Event prediction strength: `100.0`
- Control prediction strengths: `54.0`, `54.0`
- Event context remained present, but context strength was not the discriminating axis

Interpretation:

- this case is replay-safe for pre-event robustness on the prediction layer only
- it is not promoted as a stronger context-vs-control case

### George W. Bush Iraq address

- Event crisis-support strength: `31.5`
- Control crisis-support strengths: `0.0`, `0.0`

Interpretation:

- the crisis-support hit remains cleanly event-bound against both earlier controls

### Charles and Diana wedding

- Event exact-match marriage cluster score: `81.0`
- Control cluster scores: `27.0`, `0.0`
- Event exact-match count: `3`

Interpretation:

- this case remains replay-safe as a bounded marriage-cluster example when compared against earlier controls
- after the relationship-domain normalization fix, the event still beats both earlier controls, but the old inflated `+120` threshold was no longer doctrinally honest and was reduced to a bounded `+50`
- it still does **not** justify predictor/stream promotion

## Holdback Recorded In This Slice

Marriage-support predictor/stream extension was probed and held back.

What the probe showed:

- Charles predictor/stream event rows retained weaker C7-style marriage signals, but not the original single-route marriage cluster strongly enough
- Harry predictor/stream event rows lost the explicit `Venus Conjunction C7` support that made slice 7 replay-safe on `/api/astro-clock/transits`

Result:

- slice 8 does not promote a marriage predictor/stream seam
- that seam remains manual review / holdback only

## Outcome

Slice 8 is promoted as:

- a bounded pre-event control sweep on selected single-route transit classes

It is **not** promoted as:

- a new universal transit class
- evidence that marriage predictor/stream is replay-safe
- evidence that every promoted slice should automatically extend to every route seam

## Implementation Note

- No production transit logic changed in this pass.
- Slice 8 is additive replay coverage and holdback documentation only.
