# Astro Clock Transits Replay Slice 10 Results

Date: 2026-03-27

## Scope

Slice 10 is a bounded recent-war response slice, not a claim that the transit engine can classify the whole Israel-Iran war cleanly.

Why this slice is narrow:

- the June 13, 2025 Israel-Iran opening strike did not replay cleanly enough on the candidate charts that were probed
- the current 2026 war is still a weak class overall on the transit engine
- one source-backed same-day military-strike update *does* retain a stronger `attack_violence` cluster on the live single `/api/astro-clock/transits` route

Promoted case:

- Israel national chart on the February 28, 2026 IDF `22:28` broad-strike update

Claim level:

- the event timestamp keeps an explicit `attack_violence` row with `conflict` support
- after tightening Morin determination and 12th-house legal/imprisonment gates, the same row no longer degrades into `arrest_imprisonment`
- that row is materially stronger than the prior-day and prior-week controls
- this is a bounded same-day war-response slice on the single-route seam only

It is **not** a claim that:

- the full Israel-Iran war is replay-safe as a general transit class
- predictor/stream already localize the war cleanly
- every recent military event around this war is classifying correctly

## Automated Coverage

Backend:

- [test_transit_recent_war_replay_slice_10.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_recent_war_replay_slice_10.py)
- fixture: [transit_recent_war_replay_slice_10.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_recent_war_replay_slice_10.json)

Frontend:

- [transitsModalReplay.test.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/tests/transitsModalReplay.test.jsx)

## Results

### Israel Operation Roaring Lion broad strike update

- Natal chart used:
  - Israel national chart
  - `1948-05-14 16:00 Asia/Jerusalem`
  - `Tel Aviv, Israel`
- Source-backed event timestamp:
  - `2026-02-28 22:28 +02:00`
- Control dates:
  - `2026-02-27 22:28 +02:00`
  - `2026-02-21 22:28 +02:00`

Event-date retained war-response row:

- `Moon Quincunx C7 (contra-antiscia)`

Shared keyword family:

- `attack_violence`
- `conflict`

Event typing:

- `eventType: attack_violence`

Measured totals:

- event war-hit count: `1`
- control war-hit counts: `1`, `0`
- event war-significance sum: `30.0`
- control war-significance sums: `20.7`, `0.0`

Interpretation:

- the event timestamp keeps a stronger explicit attack/conflict row than the prior-day control
- it also clearly beats the prior-week control
- that is strong enough for a bounded recent-war replay slice on the single `/transits` route

## Source Basis

Event timing:

- [IDF real-time updates for February 28, 2026](https://www.idf.il/en/mini-sites/operation-roaring-lion/real-time-updates-day-by-day/february-28-2026-real-time-updates-operation-roaring-lion/)
  - the replay anchor uses the `22:28` update that says the Israeli Air Force is currently conducting a broad strike on military targets in western Iran

War context:

- [AP report on the 2026 Iran war](https://apnews.com/article/iran-us-israel-trump-lebanon-march-27-2026-195444c54cbb7545d0a77f8ffbc0e4c0)
  - used for the broader contextual claim that the war began on February 28, 2026

Natal source:

- [Astro-Databank: Nation: Israel](https://www.astro.com/astro-databank/Nation:_Israel)

## Holdbacks

Probed but not promoted in this pass:

- Benjamin Netanyahu on the June 13, 2025 opening strike
- Benjamin Netanyahu on the 2026 war-start day
- Israel national chart on the June 13, 2025 opening strike

Reason:

- they retained some conflict rows in places, but not cleanly enough across timings and controls to justify widening the slice

## Outcome

Slice 10 is promoted as:

- a one-case, single-route recent-war response slice

It is **not** promoted as:

- a broad Israel-Iran war transit class
- a predictor/stream war-localization slice
- proof that the transit engine has become generally reliable on war events
