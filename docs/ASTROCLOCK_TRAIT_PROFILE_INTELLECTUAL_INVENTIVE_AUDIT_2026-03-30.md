# Astro Clock Trait Profile Intellectual And Inventive Audit

Date: 2026-03-30

## Purpose

This pass targeted the specific replay weakness behind the held-back Einstein and Jobs cases.

The problem after the summary-eligibility pass was no longer pathology noise alone. It was that the intellectual and inventive catalog entries were still too narrow.

## What The Replay Check Showed

### Einstein

The chart was still showing:

- `scholarship` only at a weak replay-safe floor
- no activation for:
  - `invention_discovery`
  - `genius_inventive_scientific`

But the underlying chart factors did show a marked Uranian pattern:

- Aquarius emphasis present
- Uranus angular to MC/IC/DSC
- Mercury-Uranus close contact, but as `Quincunx`

The old catalog could not use that because it only rewarded soft Mercury-Uranus and soft Uranus-angle ties.

### Jobs

The chart already had some intellectual-family presence:

- `scholarship`
- `wisdom`
- `intelligence_general`

But inventive originality still failed to activate even though the chart showed:

- Mercury strong
- Mercury trine MC
- Uranus sextile ASC
- Jupiter-Uranus conjunction

Again, the old inventive rules were too soft-aspect-specific and too dependent on Aquarius emphasis.

## Real Engine Limitation Fixed

Implemented in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`

The trait engine now supports:

- `aspect` with `type: "any"`
- `angle_aspect` with `type: "any"`

This is important for inventive-originality families, because a chart can show marked Uranian or Mercury-Uranian originality through:

- conjunction
- opposition
- square
- quincunx

not only soft aspects.

The new logic still respects:

- `max_orb`
- optional `allowed_names`
- angle targeting such as `ASC` or `MC`

So the change is generic, but still bounded.

## Catalog Rework Applied

Updated in both source and packaged-source trees:

- `backend/traits/catalog/I/invention_discovery.json`
- `backend/traits/catalog/G/genius_inventive_scientific.json`
- `backend/traits/catalog/S/scholarship.json`
- `backend/traits/catalog/W/wisdom.json`
- matching files under `frontend/backend/traits/catalog/...`

### Invention & Discovery

Old bias:

- soft Uranus-MC
- soft Mercury-Uranus
- soft Sun-Uranus
- Aquarius emphasis

New rule:

- marked Uranus angularity via `ASC` or `MC`
- Mercury-Uranus contact of the main major-contact family
- Sun-Uranus and Jupiter-Uranus as supporting originality markers
- Mercury strength
- Mercury soft support to MC
- 10th/11th-house emphasis

### Genius (inventive/scientific)

Old rule:

- almost the same as invention/discovery, just thinner

New rule:

- Mercury strength added explicitly
- marked Uranus angularity allowed through `type: any`
- Mercury-Uranus contact broadened beyond soft aspects
- 10th/11th-house expression added
- dampening now includes afflicted Mercury as well as afflicted Saturn

### Scholarship

Old rule was too methodical and over-penalized fire and mutable charts.

New rule:

- Mercury strength carries more weight
- Mercury soft support to MC is now relevant
- Jupiter-Saturn soft support can reinforce learned discipline
- house emphasis focuses on `3`, `9`, and `10`
- fire and mutable penalties were softened instead of removed

### Wisdom

New support added for:

- Mercury strength
- Jupiter-Saturn soft relation

and the fire dampener was softened.

## Why This Is More Defensible

This does **not** claim that every hard Mercury-Uranus contact is genius.

It claims something narrower:

- if a chart shows strong Mercury, marked Uranian angularity, and close Mercury-Uranus contact, inventive-originality traits should not be missed purely because the contact is not soft

That is a more defensible engine rule than the old soft-aspects-only gate.

## Tests Added

Added backend contract coverage in:

- `backend/test_trait_engine_contract.py`

New assertion:

- a trait using `aspect type=any` and `angle_aspect type=any` can activate from:
  - Mercury-Uranus `Quincunx`
  - Uranus `Opposition` MC

## Result After Verification

The pass did what it was supposed to do at the family level:

- Einstein now retains:
  - `invention_discovery` `54.7` (`likely`)
  - `genius_inventive_scientific` `43.5` (`possible`)
- Jobs now retains:
  - `scholarship` `69.8` (`likely`)
  - `wisdom` `66.7` (`likely`)
  - `invention_discovery` `37.7` (`possible`)

But this alone was not enough to clean the headline summary. That is why the next pass introduced summary-bucket diversity and cognition-bucket priority.

So the accurate outcome is:

- inventive and intellectual families are no longer being missed
- summary selection still needed separate work
- this pass enabled the later summary-diversity fix; it did not by itself justify promotion of Einstein or Jobs into a stricter summary-cleanliness replay slice
