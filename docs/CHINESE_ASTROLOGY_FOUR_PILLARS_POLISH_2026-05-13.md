# Chinese Astrology Four Pillars Polish

Date: 2026-05-13

## Scope

Polish the `Four Pillars` tab so it reads as a user-facing chart foundation rather than a raw technical table.

The tab should still preserve the BaZi structure:

- four birth layers: hour, day, month, year
- Heavenly Stem and Earthly Branch for each layer
- Day stem as the Day Master reference point
- hidden stems as branch-carried roots
- Ten God labels calculated relative to the Day Master
- month/year boundaries based on solar terms

## Implemented Frontend Changes

- Added Chinese characters for Heavenly Stems and Earthly Branches.
- Replaced comma-only hidden-stem output with compact chips that show stem, character, element, and Ten God/factor where available.
- Added a short domain note explaining that the Day stem is the Day Master and that hidden stems are read relative to it.
- Added a mobile-first pillar card layout while keeping the table for wider screens.
- Reworded the visible strength-model footer so production users see the concept, not internal weights.

## Backend Source Tightening

- Tightened `local.four_pillars_strength` to Augier page refs for:
  - Four Pillars as Tian Gan / Di Zhi columns and Day Master frame: pages 25-31.
  - Hidden stems as branch-carried roots: pages 44-46.
  - Day Master strength through season, root, and formation: pages 43-46.
  - Normal root / secret root and formation support across the eight palaces: page 46.
  - Hidden-stem comparison over time and Day Master force/state: page 66.
- Added `anchor.pillars.hidden_stems` so hidden stems are no longer only implicit under strength or Ten Gods.
- Enriched backend keywords with `normal root`, `secret root`, `formation`, `eight palaces`, `Tian Gan`, `Di Zhi`, `growth`, `cardinals`, and `graveyards`.
- Kept these source details out of the production frontend. They remain backend/dev provenance.

## Source Basis

- Local corpus anchors in `docs/iching_feature/source_manifest.yml`:
  - `Ba Zi - The Four Pillars of Destiny`
  - `BaZi - The Destiny Code`
  - `BaZi - The Destiny Code Revealed`
- Public cross-checks:
  - Four Pillars / BaZi overview: https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny
  - 24 solar-term reference: https://www.hko.gov.hk/en/gts/time/24solarterms.htm

## Follow-Up Candidates

- Add tone-safe tooltips for each Ten God label.
- Add branch element and hidden-stem root weighting once the strength model exposes stable user-facing explanations.
- Add a visual marker for the month pillar as the seasonal authority when the `Day Master` tab is audited.
