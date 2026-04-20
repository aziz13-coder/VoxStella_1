# Astro Clock Transits Replay Slice 3 Results

## Scope

This slice promotes the next replay-safe transit seam after the single-timestamp slices:

- **predictor/window localization on exact event rows**

This is intentionally narrower than a generic "predictor is correct" claim.

Why this slice:

- the earlier negative-control idea did not replay safely across the promoted office-elevation charts
- the live predictor route is noisier than the single `/transits` route and should only be asserted where the exact event row stays meaningfully localized
- Astro Clock exposes predictor results in the transit modal, so route-level localization is worth testing before any scoring refactor

## Method

Replay seam:

- hit the live `/api/astro-clock/predictor` route
- freeze natal geocoding exactly as in slices 1 and 2
- scan a `±24h` window around the known event timestamp
- request `include_series=1` so the exact event row can be inspected

Assertion style for slice 3:

- the exact event timestamp must be present in the returned predictor series
- that exact event row must retain a source-backed description already validated in slices 1 or 2
- the exact event row must stay near the top of the scanned window by `step_score`
- the nearest reported peak must stay within a bounded number of hours of the real event

This slice does **not** claim the predictor's top aggregated prediction title is always the best narrative label. It only claims that the real event row remains localized and keeps the validated transit signature.

## Promoted Cases

### 1. Sergio Mattarella elected President of Italy

- Natal source: [AstroDatabank - Sergio Mattarella](https://www.astro.com/astro-databank/Mattarella%2C_Sergio)
- Event source: [AstroDatabank - Sergio Mattarella](https://www.astro.com/astro-databank/Mattarella%2C_Sergio)
- Natal replay input:
  - `1941-07-23 11:40`
  - `Palermo, Italy`
  - `Europe/Rome`
- Event replay input:
  - `2015-01-31 13:00 +01:00`

Live predictor result:

- aligned
- exact event row retained `Jupiter Sextile Mercury (antiscia)`
- exact event row `step_score` rank: `25`
- nearest reported peak distance: `4.0h`

Why it was promoted:

- the exact event row retains the same public-recognition signature validated in slice 1
- the predictor keeps the event row inside a bounded local peak neighborhood without forcing an unrealistically exact hour claim

### 2. Barack Obama Nobel Peace Prize announcement

- Natal source: [AstroDatabank - Barack Obama](https://www.astro.com/astro-databank/Obama%2C_Barack)
- Event sources:
  - [Prize announcement](https://www.nobelprize.org/prizes/peace/2009/prize-announcement/)
  - [Press release](https://www.nobelprize.org/prizes/peace/2009/press-release/)
  - [Prize announcement dates](https://www.nobelprize.org/prizes/about/prize-announcement-dates/)
- Natal replay input:
  - `1961-08-04 19:24`
  - `Honolulu, Hawaii`
  - `Pacific/Honolulu`
- Event replay input:
  - `2009-10-09 11:00 +02:00`

Live predictor result:

- aligned
- exact event row retained `Jupiter Conjunction Asc`
- exact event row `step_score` rank: `8`
- nearest reported peak distance: `7.0h`

Why it was promoted:

- the exact event row kept the slice-2 recognition signature
- the event row stayed inside the upper predictor band of the scanned window

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

Live predictor result:

- aligned
- exact event row retained `Jupiter Trine Saturn`
- exact event row `step_score` rank: `23`
- nearest reported peak distance: `5.0h`

Why it was promoted:

- the exact event row still carries the slice-2 recognition signature
- the nearest peak remains close enough to the announcement window to automate without inventing a stronger claim than the route supports

## Holdbacks / Manual Review

Not promoted into slice 3:

- Donald Trump inauguration
- Kamala Harris inauguration

Reason:

- both are replay-safe on the single `/transits` route
- neither stayed localized tightly enough on the exact event row in the predictor/window seam
- promoting them into predictor assertions would push the suite toward weak or overfit thresholds

## Automated Coverage

Added:

- [test_transit_predictor_replay_slice_3.py](/C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_predictor_replay_slice_3.py)
- [transit_predictor_replay_slice_3.json](/C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_predictor_replay_slice_3.json)

What the test protects:

- live `/api/astro-clock/predictor` response shape on a replay-safe subset
- exact-event-row preservation inside predictor `series`
- bounded predictor localization using `step_score` rank and nearest-peak distance
- continuation of the source-backed transit descriptions already validated in slices 1 and 2

## Changes Made

- later production transit logic did change after this slice was first introduced:
  - predictor/window localization is now a modest, distance-weighted support bonus instead of a large flat window flood
  - predictor peaks are now spaced across the window instead of repeating adjacent hourly rows from the same support phase
- the slice remains valid as an exact-event-row retention and bounded peak-proximity seam
