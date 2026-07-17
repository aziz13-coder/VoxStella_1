# Chinese Astrology Auxiliary Stars Polish

Date: 2026-05-13

## What The Tab Is

`Auxiliary Stars` is the Shen Sha / named-marker layer. It adds specific placement cues after the main BaZi chart has already been read through pillars, Day Master strength, Ten Gods, useful elements, palaces, relationships, and timing.

This tab answers:

- which named auxiliary markers are calculated from the chart
- which formula/reference point was used
- whether the marker appears in natal, current Luck, or annual layers
- whether relationship contacts pressure or support the marker branch
- what theme the marker can add to the reading

## Source And Correctness Scan

Current local source strength is strongest for Peach Blossom:

- `BaZi - The Destiny Code` pages 230-234: Peach Blossom is calculated from the Day Branch, can appear in natal, Luck Pillar, or annual pillar, and describes attraction/social visibility.
- `BaZi - The Destiny Code` page 252: too many Peach Blossom branches, or pressure on relationship structures, prevents a simple positive reading.
- `BaZi - The Destiny Code Revealed`: relationship and life-topic examples must be read through element quality, palace, contact pressure, and timing.

Chinese/English cross-checks used for the expanded deterministic marker formulas:

- `说八字 - 八字神煞概要总结`: compact Chinese Shen Sha formula table for Tao Hua, Yi Ma, Jiang Xing, Wen Chang, Tian Yi, Tian De, and Yue De.
- `FateMaster - Yi Ma`: English cross-check for Traveling Horse branch-triad formula.
- `FortuneCloud - Shen Sha`: UI and reading boundary cross-check that Shen Sha are auxiliary rather than the core BaZi structure.
- `OpenFate - Should You Use Shen Sha in Bazi?`: cross-check that Shen Sha should refine, not override, the main chart.

## Implemented Direction

The tab now shows deterministic marker cards instead of a single Peach Blossom-only panel:

- Peach Blossom / `桃花`
- Traveling Horse / `驿马`
- General Star / `将星`
- Wen Chang / `文昌`
- Tian Yi Nobleman / `天乙贵人`
- Heavenly Virtue / `天德`
- Moon Virtue / `月德`

Each card exposes:

- marker name, Chinese name, and pinyin
- status badge: `Active`, `Quiet`, `Pressured`, `Supported`, or `Mixed`
- formula reference such as Day Branch, Day Stem, Month Branch, or Year Branch
- target branches/stems
- natal/timing counts
- relationship-contact pressure when relevant
- short theme keywords

The backend now returns `auxiliary_stars.markers` while keeping `peach_blossom` for compatibility with existing palace and test contracts.

## Guardrails

Implemented as marker detection, not outcome scoring:

- no promise of marriage, rescue, promotion, exam success, travel, or disaster cancellation
- no star ranking or point score
- no override of Day Master strength, Ten Gods, useful elements, relationship contacts, or timing
- variant-heavy formulas carry `school_variant` metadata in the backend payload

## Follow-Up Candidates

- Add worked positive/negative examples for each marker family.
- Add optional dev-only formula/source drawer if the UI needs inspectable provenance.
- Add month/day/hour timing activations after the timing rhythm fixtures are broader.
- Add additional Shen Sha only when formulas and source examples are strong enough to avoid a decorative list.
