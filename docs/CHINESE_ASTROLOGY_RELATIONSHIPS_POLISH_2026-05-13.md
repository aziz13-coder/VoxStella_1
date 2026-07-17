# Chinese Astrology Relationships Polish

Date: 2026-05-13

## What The Tab Is

`Relationships` shows where BaZi stem and branch contacts press, combine, or activate the chart.

It is not a fixed relationship verdict. It is a contact map that answers:

- which natal stem/branch interactions are already present
- which current Luck, year, month, day, and hour layers activate the natal chart
- whether contacts lean supportive, challenging, or mixed
- whether the Day / partner palace is directly touched
- whether a saved second chart creates cross-chart contacts and Day Master exchange

## Source And Correctness Scan

The current backend model matches the core source shape for the implemented layer:

- Heavenly-stem and earthly-branch combinations are detected.
- Branch clashes, harms, punishments, self-punishments, destructions, and complete branch sets are detected.
- Current timing layers are checked against natal pillars.
- Day / partner-palace contact is treated as higher-salience evidence, not as a standalone fate claim.
- Pair compatibility uses relationship-code evidence and Day Master exchange, not animal-zodiac matching alone.

Local source anchors:

- `bazi_augier`: Day pillar and Day branch frame the relation between self and partner; stem/branch relationships include combinations, clashes, harms, punishments, self-punishments, destructions, and branch sets; Luck Pillar contacts are read against the Day pillar.
- `bazi_destiny_code_revealed_book2_joey_yap`: compatibility examples and Luck Pillar relationship examples support treating pair and timing contacts as evidence layers.
- `local.four_pillars_palace_context`: palace position changes what a contact means, so a Day / partner-palace touch should be surfaced separately from a generic contact count.

Public cross-checks used only for broad terminology and relationship-code categories:

- Four Pillars / BaZi overview: https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny
- BaZi clashes and combinations overview: https://www.masterseanchan.com/bazi-clashes-and-combinations/

## Implemented Direction

- Rename the production panel from `Relationship Codes` to `Relationships`.
- Add a plain-language sentence that explains contacts without turning them into a verdict.
- Replace the seven raw layer counters with four useful summary cards:
  - total contacts
  - main tone
  - Day / partner-palace contacts
  - timing contacts
- Keep active layers visible first.
- Collapse empty layers into a quiet-layer row instead of repeating empty panels.
- Keep source basis, source-confidence chips, pair score calibration, and raw scoring details out of the normal Relationships tab; audit evidence belongs in `Sources & Method`.
- Keep the pair score framed as an evidence index.

## Follow-Up Candidates

- Add a short glossary for combination, clash, harm, punishment, destruction, and branch set.
- Add positive and negative curated examples for each relationship-code family.
- Add relationship-contact sorting by Day palace, directness, timing recency, and tone.
- Add a compact pair-comparison view that separates romantic, family, friendship, and business contexts.
