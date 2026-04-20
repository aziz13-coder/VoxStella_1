# Astro Clock Transits Replay Slice 2 Results

## Scope

This slice expands transit replay testing into a second, weaker but still source-grounded class:

- **formal public-honor announcement events**

This is intentionally not treated as the same class as slice 1.

Why:

- the transit engine was clean on office elevation and inauguration charts
- award and recognition charts did not replay cleanly enough to justify a hard `promotion` contract
- the stable pattern was instead:
  - event-day `opportunity_received` or recognition-type signal is present
  - that event-day signal is materially stronger than a nearby control date
  - public/career context still appears in the top transit hits

## Method

Replay seam:

- real `/api/astro-clock/transits` route
- real transit engine
- frozen natal geocoding in tests

Assertion style for slice 2:

- the event date must produce a source-expected recognition/opportunity prediction
- the event date must still contain a public/career context hit
- the event date must beat a nearby control date on:
  - top recognition/opportunity prediction strength
  - top recognition/public-honor hit strength

Control choice:

- seven days earlier at the same local announcement time

## Promoted Cases

### 1. Barack Obama Nobel Peace Prize announcement

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
- Control replay input:
  - `2009-10-02 11:00 +02:00`

Time basis:

- official Norwegian Nobel Committee announcement slot
- confidence: medium

Event-date route result:

- matching recognition prediction: `Jupiter Conjunction Asc`
- matching event type: `opportunity_received`
- public/career context hit: `Saturn Sextile MC`
- context keywords:
  - `career`
  - `authority_earned`
  - `structure_established`

Event vs control:

- prediction strength:
  - event `95.4`
  - control `63.6`
  - delta `+31.8`
- public-honor hit strength:
  - event `95.4`
  - control `63.6`
  - delta `+31.8`

### 2. Al Gore Nobel Peace Prize announcement

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
- Control replay input:
  - `2007-10-05 11:00 +02:00`

Time basis:

- official Norwegian Nobel Committee announcement slot
- confidence: medium

Event-date route result:

- matching recognition prediction: `Jupiter Trine Saturn`
- matching event type: `opportunity_received`
- public/career context hits:
  - `Saturn Semi-sextile Venus (antiscia)`
  - `Saturn Quincunx Venus (contra-antiscia)`
- context keywords:
  - `career`
  - `authority_earned`
  - `structure_established`

Event vs control:

- prediction strength:
  - event `100.0`
  - control `0.0`
  - delta `+100.0`
- public-honor hit strength:
  - event `100.0`
  - control `60.0`
  - delta `+40.0`

## Holdbacks / Manual Review

### Bob Dylan Nobel Prize in Literature announcement

Why it was not promoted:

- the event-date signal did not beat the one-week-earlier control
- both dates carried roughly the same `opportunity_received` strength
- that is not replay-safe enough for an automated assertion

Held-back candidate:

- Bob Dylan Nobel Literature announcement

## Automated Coverage

Added:

- [test_transit_public_honor_replay_slice_2.py](/C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_public_honor_replay_slice_2.py)
- [transit_public_honor_replay_slice_2.json](/C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_public_honor_replay_slice_2.json)

What the test protects:

- route-level recognition/opportunity signal on public-honor announcement charts
- event-vs-control strength comparison
- public/career context preservation in top transit hits

## Changes Made

- no production transit logic changed in this pass
- no frontend transit logic changed in this pass
- this pass adds only replay fixtures, route-level tests, and slice documentation
