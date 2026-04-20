# Extended Goal Domains

## Purpose

This note documents two advanced astrocartography goal extensions that are not part of the original four visible PathFinder presets:

- speculative or gambling-oriented place scanning
- warning-oriented health and injury hotspot scanning

These are not direct recovered Almagest formulas. They are Vox Stella goal models built from the existing source base already present in the repo.

## Gambling / Speculation Domain

### House logic

From the current Morin knowledge map:

- the `5th house` explicitly includes `speculation` and `gambling`
- the `2nd`, `8th`, and `11th` remain relevant supporting money and gains contexts

This makes a speculation model meaningfully different from a general money model:

- `money` is broader and can be earned through career, trade, or stable income
- `gambling / speculation` is narrower and should lean harder on `5th-house` risk and pleasure signatures

### Planet logic

From the astrocartography planetary baseline reference:

- `Jupiter` = luck, opportunity, expansion
- `Venus` = ease, attraction, social flow
- `Mercury` = trade, calculation, quick judgment
- `Sun` = confidence, boldness, visible participation

Main caution factors:

- `Neptune` can distort judgment through glamour, fantasy, or leakage
- `Saturn` can flatten or constrict speculative flow

## Health / Injury Risk Domain

### Angle logic

From the astrocartography angular reference:

- `ASC` interprets a planet through `selfhood, body, projection, personal identity`

That makes the ASC the clearest map-first bodily axis for a risk-oriented location model.

### House logic

From the current Morin knowledge map:

- the `6th house` explicitly includes `health, illness, service, work, daily routines`
- malefics in the `6th` are explicitly marked as `illness-prone`
- the broader engine already treats `1st`, `6th`, `8th`, and `12th` as the strongest bodily-risk and danger cluster

This supports a warning-oriented model that scans for:

- bodily strain
- accident exposure
- chronic depletion
- illness pressure

### Planet logic

From the astrocartography planetary baseline reference:

- `Mars` = heat, haste, cuts, irritation, conflict
- `Saturn` = heaviness, depletion, chronic burden
- `Uranus` = shock, instability, sudden disruption
- `Neptune` = confusion, lowered clarity, diffuse weakening
- `Pluto` = crisis, compulsion, extreme pressure

Protective or lowering factors:

- `Jupiter` can provide protection, resilience, and recovery support
- `Venus` can soften environmental harshness

## Product rule

The `health_risk` model is not a positive destination goal.

Its score means:

- higher score = harsher / riskier place
- lower score = less risk-signaled place

Any UI surface that uses this model should present it as a warning-oriented ranking, not as an aspirational “best city” recommendation.
