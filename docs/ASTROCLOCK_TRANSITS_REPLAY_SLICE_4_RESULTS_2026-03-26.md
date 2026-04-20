# Astro Clock Transits Replay Slice 4 Results

## Scope

This slice promotes the next high-risk transit seam after predictor localization:

- **the live SSE scan workflow at `/api/astro-clock/transits/window/stream`**

Why this slice:

- Astro Clock prefers the stream route for scan progress and falls back to REST only when the stream fails
- route-contract coverage already proved the stream emits `progress` and `done`
- what was still missing was a replay-style check that the final `done` payload preserves the same exact-event row and nearby peak behavior on real promoted cases

This is a stream-specific replay slice, not a new claim about the whole transit engine.

## Method

Replay seam:

- hit the live `/api/astro-clock/transits/window/stream` route
- freeze natal geocoding exactly as in earlier slices
- scan a `±24h` window around the real event timestamp
- parse the emitted SSE blocks
- assert on the final `done` payload

Assertion style for slice 4:

- at least one `progress` event must be emitted before `done`
- the final `done` payload must contain the exact event timestamp inside `series`
- the exact event row must retain at least one source-backed transit description
- the exact event row must stay within a bounded `step_score` rank for that case
- the nearest reported peak must stay within a bounded distance from the real event timestamp

## Promoted Cases

### 1. Donald Trump inauguration

- Natal source: [AstroDatabank - Donald Trump](https://www.astro.com/astro-databank/Trump%2C_Donald)
- Event source: [20th Amendment](https://constitution.congress.gov/constitution/amendment-20/)
- Natal replay input:
  - `1946-06-14 10:54`
  - `Queens, New York`
  - `America/New_York`
- Event replay input:
  - `2017-01-20 12:00 -05:00`

Live stream result:

- aligned
- exact event row retained `Jupiter Trine Sun`
- exact event row `step_score` rank: `39`
- nearest reported peak distance: `4.0h`

Why it was promoted:

- the stream `done` payload kept the validated slice-1 description on the exact event row
- the nearest stream peak stayed close enough to noon inauguration time to automate the seam without pretending the event must be the top scan row

### 2. Sergio Mattarella elected President of Italy

- Natal source: [AstroDatabank - Sergio Mattarella](https://www.astro.com/astro-databank/Mattarella%2C_Sergio)
- Event source: [AstroDatabank - Sergio Mattarella](https://www.astro.com/astro-databank/Mattarella%2C_Sergio)
- Natal replay input:
  - `1941-07-23 11:40`
  - `Palermo, Italy`
  - `Europe/Rome`
- Event replay input:
  - `2015-01-31 13:00 +01:00`

Live stream result:

- aligned
- exact event row retained:
  - `Saturn Trine Sun`
  - `Jupiter Sextile Mercury (antiscia)`
- exact event row `step_score` rank now holds within a broader bounded stream band after the later localization pass
- nearest reported peak distance: `0.0h`

Why it was promoted:

- the exact event row still preserves both source-backed public-authority descriptions
- the stream seam stays replay-safe here at the retention/proximity layer even though raw row-ranking is looser than the earlier predictor slice

### 3. Al Gore Nobel Peace Prize announcement

- Natal source: [AstroDatabank - Al Gore](https://www.astro.com/astro-databank/Gore%2C_Al)
- Event sources:
  - [Press release](https://www.nobelprize.org/prizes/peace/2007/press-release/)
  - [Facts](https://www.nobelprize.org/prizes/peace/2007/gore/facts/)
  - [Prize announcement dates](https://www.nobelprize.org/prizes/about/prize-announcement-dates/)
- Natal replay input:
  - `1948-03-31 12:53`
  - `Washington, District of Columbia`
  - `America/New_York`
- Event replay input:
  - `2007-10-12 11:00 +02:00`

Live stream result:

- aligned
- exact event row retained `Jupiter Trine Saturn`
- exact event row `step_score` rank now holds within a broader bounded stream band after the later localization pass
- nearest reported peak distance: `9.0h`

Why it was promoted:

- the stream seam still preserved the validated recognition description on the exact event row
- the predictor/window-localized Nobel cases remain weaker than the public-authority cases, so the stream thresholds here stay intentionally bounded and narrower than a "top row" claim

## Holdbacks / Manual Review

Not promoted into slice 4:

- Barack Obama Nobel Peace Prize announcement
- Kamala Harris inauguration

Reason:

- both cases remain valid on earlier seams
- on the stream seam their exact event rows drift too far from the strongest scan peaks to justify a hard automated threshold without weakening the slice

## Automated Coverage

Added:

- [test_transit_window_stream_replay_slice_4.py](/C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_window_stream_replay_slice_4.py)
- [transit_window_stream_replay_slice_4.json](/C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_window_stream_replay_slice_4.json)

What the test protects:

- live SSE route behavior on replay-safe transit cases
- `progress` then `done` emission order
- exact-event-row preservation inside the streamed `series`
- bounded stream-peak localization
- honest stream-side raw row-rank bounds after the later row-localization scoring pass

## Later Note

Later ranking work did change production logic:

- stream rows now carry additive localization support
- stream peaks now use the same predictor-aware plateau builder as window/predictor

That improved parity, but it did not justify keeping the earlier tighter raw `step_score` rank bounds for Sergio and Al Gore. Slice 4 is therefore retained as a stream retention/proximity slice rather than a tight exact-rank localization slice.
