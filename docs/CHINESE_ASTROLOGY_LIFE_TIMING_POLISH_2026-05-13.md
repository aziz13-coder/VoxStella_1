# Chinese Astrology Life Timing Polish

Date: 2026-05-13

## What The Tab Is

`Life Timing` shows how a natal BaZi chart is activated by time.

It is not a separate fate score. It is a timing layer that answers:

- which 10-year Luck Pillar sequence is active
- when the Luck Pillars begin
- whether the current year, month, day, and hour add support or pressure
- whether timing touches useful-element candidates
- whether timing creates relationship-code contacts against natal pillars

## Source And Correctness Scan

The current backend model matches the core source shape:

- Luck Pillars start from the Month Pillar.
- Direction moves forward or reverse according to calculation sex and the selected polarity rule.
- Start age is derived from distance to an adjacent solar-term boundary.
- Timing layers are read against the natal Day Master, Ten Gods, useful-element candidates, and relationship-code contacts.
- Timing evidence can raise or lower attention, but it should not create a final Useful God by itself.

Local source anchors:

- `bazi_augier`: Luck Pillars use the Month Pillar as the starting column; direction and solar-month distance set the sequence and start age.
- `bazi_destiny_code_book1_joey_yap`: core Luck Pillar plotting workflow and age-limit presentation.
- `bazi_destiny_code_revealed_book2_joey_yap`: correct Luck Pillar presentation, relationship-code checks against Luck Pillars, and annual/Luck Pillar examples.

Public cross-checks used for broad calendar terminology only:

- Four Pillars / BaZi overview: https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny
- 24 solar terms: https://www.hko.gov.hk/en/gts/time/24solarterms.htm

## Implemented Direction

- Keep Life Timing as a user-facing timing overview.
- Explain that calculation sex is required only when the user wants the decade sequence.
- Promote the important timing facts into top summary cards:
  - direction
  - start age
  - active decade
  - current year
  - live flow
  - relationship contacts
- Rename `BaZi Timing Rhythm` to `Current Timing Layers`.
- Display current timing layers as readable pillars with Ten God, growth stage, period, and contacts.
- Keep method/source evidence and calculation debug details dev-only.

## Follow-Up Candidates

- Add a compact timeline visualization for the decade sequence.
- Add first-five-years stem / second-five-years branch emphasis when the backend exposes stable period splitting.
- Add a plain-language glossary for Growth Stage names after the Day Master and Ten Gods tabs are audited.
