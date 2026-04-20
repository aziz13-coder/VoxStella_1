# Forensic Corpus Replay Slice 5

## Scope

Fifth replay slice for the forensic overlay, focused on the two previously deferred disaster charts that had explicit local-source anchors but were still missing a stable `Disaster` direction through the real `/api/astro-clock/forensic` route.

Machine-readable fixture:

- [forensic_case_replay_slice_5.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_5.json)

## Why These Cases

The earlier slices already covered domestic homicide, family homicide, friend homicide, celebrity/public murder, aviation disaster, and maritime disaster.

The remaining grounded disaster holdbacks were:

- `twa_flight_800`
- `haiti_earthquake`

Both cases are source-backed in the local Salerno text, but they had been deferred because the live route was not producing a clear `Disaster` direction from the current rule set.

## Cases Promoted

### `twa_flight_800`

- source:
  - [Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensics%20by%20the%20Stars%20Astrology%20Investigates%20(B.%20D.%20Salerno)%20(Z-Library).txt)
- source basis:
  - the local text gives the date, Long Island departure context, and the chart signature that the Ascendant is zero degrees Aquarius at take-off
- replay choice:
  - `1996-07-17T20:31:00`, `Long Island, New York`, `America/New_York`
- metadata note:
  - the exact minute was solved internally by matching the local source chart signature, not by adding a new external source
- expected primary axis:
  - `accident_or_disaster`

### `haiti_earthquake`

- source:
  - [Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensics%20by%20the%20Stars%20Astrology%20Investigates%20(B.%20D.%20Salerno)%20(Z-Library).txt)
- source basis:
  - the local text explicitly states `January 12, 2010, at 4:58 PM local time`
- replay choice:
  - `2010-01-12T16:58:00`, `Haiti`, `America/Port-au-Prince`
- metadata note:
  - the book names the nation rather than a city, so the replay keeps the national anchor instead of inventing a narrower local source claim
- expected primary axis:
  - `accident_or_disaster`

## Slice-5 Goal

This slice was meant to answer a narrow question:

- can the forensic overlay now classify the two remaining grounded disaster holdbacks as disasters through the real route

It was not intended to solve every kind of natural-disaster or public-violence chart.
