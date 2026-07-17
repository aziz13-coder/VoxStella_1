# Chinese Astrology Source Enrichment Implementation

Date: 2026-05-13

## Full Source-Enrichment Update

This document originally recorded the first climate-only release. The current source pass now implements the broader Chinese-source enrichment requested for Astro Clock while keeping all edits in source folders only.

Implemented now:

- Real regulating Useful God rows keyed by Day Stem and Month Branch for the new verified slice:
  - `Jia` month table from Lu Zhiji, `lu_zhiji_fate_search`, p. 240.
  - `Yi` in `Wei` month from Lu Zhiji, p. 250.
  - `Bing` in `Hai` month from Lu Zhiji, p. 242: water-command winter requires warmth/wood-led handling before ordinary balance.
  - `Geng` in `Hai`/`Zi`/`Chou` winter months from Lu Zhiji, p. 244: Fire warmth/refinement is judged before ordinary Wealth/Output logic.
  - The prior ten-stem configuration summary remains as a fallback row set for non-month-specific stem rules.
- Month-command structure selection:
  - Month hidden stem selects standard structures such as Direct Officer, Seven Killings, Wealth, Resource, Eating God, Hurting Officer, and companion/blade style structures.
  - The payload exposes `use_mode` (`shun_yong`, `ni_yong`, neutral), usable/damaged status, damage patterns, and whether ordinary useful-element rules still apply.
- Special-structure final rulings, no longer just warnings:
  - Dominant structures: `qu_zhi`, `yan_shang`, `jia_se`, `cong_ge`, `run_xia`.
  - Follow structures: `cong_cai`, `cong_sha`, `cong_er`, `cong_qiang`, `cong_shi`.
  - Transformation structures: `hua_qi` from day-stem combination with month support and no return-to-root blocker.
  - Suspected, false-follow, and failed-transformation cases stay withheld.
- Specific damaged-useful logic:
  - Wealth damaged by Companion/Rob Wealth.
  - Officer/Killing damaged by Output/Hurting Officer.
  - Resource damaged by Wealth.
  - Output/Eating God damaged by Resource/Owl.
  - Generic relationship pressure is still shown, but it cannot finalize a damaged alternate unless it matches a source damage pattern.
  - Timing-only alternates remain withheld with `alternate_timing_only`.
- Timing is now interpretive:
  - Da Yun weights branch more heavily than stem.
  - Liu Nian weights stem more heavily than branch.
  - Timing effects classify rescue, damage, activation, movement, pressure, arrival/contact, or exposure.
- Compatibility now has a BaZi-first judgement layer before score display:
  - spouse palace / Day Branch,
  - spouse-star/useful-element exchange,
  - Day Master exchange,
  - cross-chart contacts,
  - current timing activation of relationship palaces.
- Auxiliary stars were expanded as secondary markers:
  - Hua Gai, Yang Ren, Gan Lu, Hong Yan, Jie Sha, Wang Shen, Gu Chen, Gua Su, Kong Wang, Kui Gang, San Qi.
- Frontend surfaces now expose the added evidence:
  - month-command structure in Useful God decision evidence,
  - source damage type,
  - Day Stem + Month Branch climate conditions,
  - timing weights and interpretive effects,
  - compatibility judgement order,
  - expanded Shen Sha marker cards.

Released final Yong Shen families now include:

- `strong_balancing`
- `weak_support`
- `climate_override`
- `dominant_element`
- `follow_structure`
- `transformation_structure`
- `damaged_alternate`

Still blocked from final release:

- `timing_assisted`, because timing activates or modifies natal logic but does not independently create a final Yong Shen.
- `damage_withheld` and `special_structure_withheld`, because these are explicit blocker states.

Source files changed in this full pass:

- `backend/chinese_astrology/interpretation.py`
- `backend/chinese_astrology/validation.py`
- `backend/chinese_astrology/timing_rhythm.py`
- `backend/chinese_astrology/relationships.py`
- `backend/chinese_astrology/auxiliary_stars.py`
- mirrored files under `frontend/backend/chinese_astrology/`
- `backend/test_chinese_astrology_bazi.py`
- `frontend/backend/test_chinese_astrology_bazi.py`
- `frontend/src/features/astroclock/ChineseAstrologyPage.jsx`

## Implemented In This Pass

The first non-conservative source-backed correction is climate/regulating Useful God logic.

Implemented source rules:

- `Jia` Day Master month-specific regulating stems from Lu Zhiji, `lu_zhiji_fate_search`, p. 240.
- `Yi` Day Master in `Wei` month from Lu Zhiji, `lu_zhiji_fate_search`, p. 250.
- Ten-day-stem regulating configuration summary from Lu Zhiji, `lu_zhiji_fate_search`, pp. 251-255.
- Season-only climate rows remain visible as preview evidence, but they cannot finalize Yong Shen.

Final `yong_shen.climate_override` can now emit only when all of these are true:

- The regulating stem comes from a source row, not the old season fallback.
- The regulating element is present in natal placements or supplied by timing.
- The regulating element is not pressured by configured relationship-contact damage.
- No special-structure screen is active.
- The `climate_override` rule family fixture gate is released.

Source files changed:

- `backend/chinese_astrology/interpretation.py`
- `backend/chinese_astrology/validation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/validation.py`
- `backend/test_chinese_astrology_bazi.py`
- `frontend/backend/test_chinese_astrology_bazi.py`

## Why This Improves The Logic

The old model treated climate mostly by season: summer suggested Water, winter suggested Fire, and so on. The Chinese sources are more specific. Lu's method names regulating stems by Day Master and month, then reads whether the regulator is actually available. This prevents a generic seasonal override from winning, while allowing a real source-backed climate rule to outrank ordinary strong/weak balancing.

Example released behavior:

- `Jia` Day Master in `Wu` month selects `Gui` as primary regulating stem from Lu p. 240.
- If Water is present and no blocker is active, the engine can finalize `Water` as regulating Yong Shen.
- If Water is absent, the same source row remains a withheld candidate with `climate_candidate_absent`.
- If a special-structure screen is active, ordinary climate override is withheld for structural review.

## Remaining Aggressive Enrichment Targets

Next implementation slices should be source-first but not timid:

1. Complete the full ten-stem by twelve-month regulating table.
2. Replace broad special-structure ratio screens with strict success/failure classifiers for dominant, follow, transformation, false-follow, failed transformation, and return-to-root cases.
3. Replace generic damaged-useful pressure with source-backed damage patterns: harmed officer, harmed wealth, harmed resource, harmed output, and two-against-one injury.
4. Expand Day Master strength from coarse strong/weak into month command, root, assistance, same-side/opposing-side, excessive, deficient, and neutral gradations.
5. Add missing auxiliary stars only after formulas are manually verified against page images.
6. Keep compatibility evidence transparent unless a source-backed matching corpus is curated.

## Verification Target

This pass is complete only if both backend source twins pass their Chinese astrology tests and the frontend build succeeds from source files.
