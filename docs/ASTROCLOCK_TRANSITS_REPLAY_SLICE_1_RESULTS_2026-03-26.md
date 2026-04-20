# Astro Clock Transits Replay Slice 1 Results

## Scope

This slice promotes a narrow replay corpus for **public-authority elevation events** through the real `/api/astro-clock/transits` route.

Why this slice:

- route-contract coverage was already in place
- violent/accident/death examples were still too noisy to assert safely
- public-office elevation charts were the first transit class that replayed cleanly enough to automate without changing shared transit logic

## Method

Replay seam:

- hit the live Flask route at `/api/astro-clock/transits`
- keep the real Morin transit engine active
- freeze natal geocoding in tests by replacing location lookup with source-backed coordinates
- assert on substantive transit output, not prose similarity

Assertion shape:

- at least one top prediction in the first 12 rows must align on `promotion` in the `honors` area
- at least one transit hit in the first 40 rows must show the expected public/career keyword mix for the case

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

Live route result:

- aligned
- top matching prediction: `Jupiter Trine Sun`
- matched event type: `promotion`
- matched life area: `honors`
- matched public/career hit keywords:
  - `career`
  - `public_recognition`
  - `promotion`

Notes:

- This is the cleanest case in the slice.
- The constitutional noon handoff gives a stable event anchor.

### 2. Kamala Harris inauguration as Vice President

- Natal source: [AstroDatabank - Kamala Harris](https://www.astro.com/astro-databank/Harris%2C_Kamala)
- Event source: [20th Amendment](https://constitution.congress.gov/constitution/amendment-20/)
- Natal replay input:
  - `1964-10-20 21:28`
  - `Oakland, California`
  - `America/Los_Angeles`
- Event replay input:
  - `2021-01-20 12:00 -05:00`

Live route result:

- aligned
- matching promotion prediction present in top 12: `Sun Semi-sextile MC`
- matched life area: `honors`
- strongest public-authority transit hit: `Saturn Semi-sextile MC`
- matched public/career hit keywords:
  - `career`
  - `structure_established`
  - `authority_earned`

Notes:

- The route also ranks `opportunity_received` strongly on this chart.
- That is acceptable here because the promotion/honors signal is still clearly present and the MC-linked public-authority hit is clean.

### 3. Sergio Mattarella elected President of Italy

- Natal source: [AstroDatabank - Sergio Mattarella](https://www.astro.com/astro-databank/Mattarella%2C_Sergio)
- Event source: [AstroDatabank - Sergio Mattarella](https://www.astro.com/astro-databank/Mattarella%2C_Sergio)
- Natal replay input:
  - `1941-07-23 11:40`
  - `Palermo, Italy`
  - `Europe/Rome`
- Event replay input:
  - `2015-01-31 13:00 +01:00`

Live route result:

- aligned
- matching promotion predictions in top 12:
  - `Sun Trine Moon (antiscia)`
  - `Sun Sextile Moon (contra-antiscia)`
  - `Jupiter Sextile Mercury (antiscia)`
- matched life area: `honors`
- matched public/career hit keywords:
  - `career`
  - `public_recognition`

Notes:

- This case also shows a useful secondary authority signature through `Saturn Trine Sun` with `authority_earned` and `structure_established`.

## Automated Coverage

Added:

- [test_transit_public_authority_replay_slice_1.py](/C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_public_authority_replay_slice_1.py)
- [transit_public_authority_replay_slice_1.json](/C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_public_authority_replay_slice_1.json)

What the test protects:

- real `/api/astro-clock/transits` route output for a replay-safe class of public-authority events
- natal geocode determinism for those replay cases
- top prediction alignment on `promotion` / `honors`
- public/career keyword preservation in top transit hits

## Holdbacks / Manual Review

Not promoted into executable replay assertions:

- Barack Obama inauguration
- Barack Obama reelection
- Martin Luther King Jr. assassination
- accident/death cases previously probed through AstroDatabank-style event anchors

Reason:

- these cases did not produce a stable enough top-level transit signature to justify hard assertions without overfitting

## Changes Made

- no production transit logic changed in this replay pass
- no frontend transit logic changed in this replay pass
- this slice only adds replay fixtures, route-level tests, and source-grounded documentation
