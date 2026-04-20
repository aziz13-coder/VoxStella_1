# Astro Clock Transits Replay Slice 5 Results

## Scope

This slice tests the next transit seam only after probing the harder war/death class:

- **bounded public-crisis support on real war/violent-event dates**

What this slice is **not** claiming:

- it is **not** claiming the current transit engine cleanly predicts `warfare_involvement`, `death_violent`, or other crisis titles as top event labels on demand
- it is **not** a general statement that the transit engine is already “good at war/death”

What this slice **does** claim:

- on a small replay-safe subset of real public-crisis dates, the live `/api/astro-clock/transits` route preserves specific conflict/violent-event support hits
- on those promoted cases, the real event date beats a nearby control date on that crisis-support layer

## Why The Slice Is Narrow

I probed a broader war/death candidate pool first, including:

- public assassinations
- war declarations and invasion starts

The current transit engine did **not** replay safely as a broad “war/death event type” slice:

- top prediction titles often stayed in `life`, `honors`, or generic obstruction labels
- the stronger crisis signal frequently lived in the supporting hit keywords instead

So slice 5 promotes only the support layer that was strong enough to automate without overstating the engine.

## Method

Replay seam:

- hit the live `/api/astro-clock/transits` route
- freeze natal geocoding exactly as in earlier slices
- compare the real event timestamp against a nearby control date for the same natal chart

Assertion style for slice 5:

- the event-date response must retain a specific source-backed crisis-support hit
- that hit must carry the expected crisis keyword family
- the event date must beat the nearby control date by a bounded minimum on the strongest crisis-support significance

## Promoted Cases

### 1. George W. Bush Iraq address

- Natal source: [AstroDatabank - George W. Bush](https://www.astro.com/astro-databank/Bush%2C_George_W.)
- Event source: [White House archive - President Bush Addresses the Nation](https://georgewbush-whitehouse.archives.gov/news/releases/2003/03/20030319-17.html)
- Natal replay input:
  - `1946-07-06 07:26`
  - `New Haven, Connecticut`
  - `America/New_York`
- Event replay input:
  - `2003-03-19 22:16 -05:00`
- Control replay input:
  - `2003-03-12 22:16 -05:00`

Live route result:

- aligned on the bounded crisis-support seam
- event-date crisis-support hit retained `Mars Quincunx Mercury`
- expected crisis keyword family: `accident_major`
- strongest event-date crisis-support significance: `69.6`
- strongest control-date crisis-support significance: `30.0`

Why it was promoted:

- the date is source-grounded to the official Oval Office address timestamp
- the event date materially outruns the nearby control on the crisis-support layer
- this is still a **support-hit** claim, not a clean “the engine labeled war” claim

### 2. Shinzo Abe assassination

- Natal source: [AstroDatabank - Shinzo Abe](https://www.astro.com/astro-databank/Abe%2C_Shinzo)
- Event source: [Asahi - Shinzo Abe shot while campaigning in Nara](https://www.asahi.com/ajw/articles/14664249)
- Natal replay input:
  - `1954-09-21 12:00`
  - `Tokyo, Japan`
  - `Asia/Tokyo`
- Event replay input:
  - `2022-07-08 11:30 +09:00`
- Control replay input:
  - `2022-07-01 11:30 +09:00`

Live route result:

- aligned on the bounded crisis-support seam
- event-date crisis-support hit retained `Jupiter Quincunx Mercury (contra-antiscia)`
- expected crisis keyword family: `accident_major`
- strongest event-date crisis-support significance: `60.0`
- strongest control-date crisis-support significance: `45.0`

Why it was promoted:

- the event timing is strong enough for a medium-confidence replay anchor
- the event date beats the nearby control without forcing a broader death-label claim

## Holdbacks / Manual Review

Probed but not promoted:

- John F. Kennedy assassination
- Martin Luther King Jr. assassination
- Winston Churchill war declaration
- Vladimir Putin Ukraine invasion

Reason:

- the current engine kept some danger/conflict support, but not strongly or consistently enough to justify a harder replay slice without weakening the thresholds
- several of those probes also stayed too mixed between crisis-support hits and unrelated top prediction titles

## Automated Coverage

Added:

- [test_transit_public_crisis_replay_slice_5.py](/C:/Users/sabaa/Downloads/codexhorary/tests/test_transit_public_crisis_replay_slice_5.py)
- [transit_public_crisis_replay_slice_5.json](/C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/transit_public_crisis_replay_slice_5.json)

What the test protects:

- real `/api/astro-clock/transits` replay on a bounded war/violent-event subset
- preservation of crisis-support hits on the exact event date
- event-vs-control comparison on the support-hit layer

## Changes Made

- no production transit logic changed in this pass
- no backend scoring weights changed in this pass
- this pass adds replay fixtures, bounded crisis-support tests, frontend replay checks, and documentation only
