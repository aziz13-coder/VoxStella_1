# Astro Clock Transits Replay Slice 9 Results

Date: 2026-03-27

## Scope

Slice 9 is a bounded war-response slice, not a broad war-prediction claim.

Why this slice is narrow:

- the broader war-class probe remains mixed
- classical and modern candidates like Churchill, FDR, and Putin did not replay cleanly enough to justify a multi-case war slice
- George W. Bush's Iraq address does show a real, source-grounded war-response layer on the live single `/api/astro-clock/transits` route

Promoted case:

- George W. Bush Iraq address

Claim level:

- the live single-route transit output preserves a denser 7th-house conflict cluster on the event date than on two earlier controls
- this is a war-response keyword-layer claim
- after the March 27 general fix, those war-layer rows now at least classify as explicit `attack_violence` event types instead of collapsing into unrelated relationship labels
- it is still **not** a claim that the transit engine cleanly labels wars as top prediction titles

## Automated Coverage

Backend:

- [test_transit_war_response_replay_slice_9.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_war_response_replay_slice_9.py)
- fixture: [transit_war_response_replay_slice_9.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_war_response_replay_slice_9.json)

Frontend:

- [transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)

## Results

### George W. Bush Iraq address

- Source-backed event timestamp:
  - `2003-03-19 22:16 -05:00`
- Control dates:
  - `2003-03-12 22:16 -05:00`
  - `2003-03-05 22:16 -05:00`

Event-date war-response cluster:

- `Jupiter Opposition C7`
- `Saturn Quincunx C7 (antiscia)`
- `Moon Quincunx C7 (contra-antiscia)`

Shared keyword family:

- `attack_violence`
- `conflict`

Post-fix event typing on the retained war rows:

- `eventType: attack_violence`
- description layer now persists and renders the violent-attack wording instead of dropping `prediction.eventType`

Measured totals:

- event war-hit count: `3`
- control war-hit counts: `2`, `2`
- event war-significance sum: `62.6`
- control war-significance sums: `43.5`, `43.5`

Interpretation:

- the event date carries a denser 7th-house conflict/attack cluster than either earlier control
- that is strong enough for a bounded automated war-response slice
- the route still presents broader honor/life predictions around the same timestamp, so the slice remains at the keyword/support layer

## Holdbacks

Probed but not promoted in this pass:

- Winston Churchill war declaration
- Franklin D. Roosevelt Day of Infamy speech
- Vladimir Putin invasion announcement

Reason:

- they retained danger/conflict hints in places, but not strongly or cleanly enough to justify deterministic automated assertions without weakening the slice

## Outcome

Slice 9 is promoted as:

- a one-case, single-route war-response replay slice

It is **not** promoted as:

- a broad war transit class
- a predictor/stream war-localization slice
- evidence that the transit engine now cleanly predicts war labels as top outcomes

## Implementation Note

- A shared production fix was applied after the initial slice-9 probe.
- Root cause:
  - the prediction object was only being persisted on the exception fallback path in `backend/transits_morin.py`
  - generic 7th-house relationship tokens could also outrank explicit crisis tokens like `attack_violence`
- General fix:
  - persist `prediction` before description rendering and always keep the selected `eventType`
  - prioritize explicit crisis/war tokens over generic relationship/honor tokens when both are present
- The fix was mirrored into the packaged-source twin and the frontend fallback priority path.
