# Chinese Astrology Chinese Books Audit

Date: 2026-05-13

## Scope

This audit inspected the four Chinese-language books supplied in `C:/Users/sabaa/Desktop/chinese books` and compared them with the current Astro Clock Chinese Astrology implementation.

Full extracted text is kept only under `output/chinese_books_private_corpus/`, which is gitignored and outside generated app artifacts. The notes below use page references and paraphrase source rules; they do not reproduce long copyrighted passages.

## Source Inventory And Extraction

| ID | Source | Pages | Extraction Status | Private Output |
| --- | --- | ---: | --- | --- |
| `lu_zhiji_bazi_advanced` | `八字命理學進階教程 (陆致极).pdf` | 327 | Native text was sparse; OCR forced. 327/327 pages recovered, average confidence `0.756`. | `output/chinese_books_private_corpus/ocr/lu_zhiji_bazi_advanced/document.ocr.pages.jsonl` |
| `lu_zhiji_fate_search` | `命运的求索 中国命理学简史及推演方法 (陆致极.pdf` | 479 | Image-only by native extraction. OCR recovered 479/479 pages, average confidence `0.848`. | `output/chinese_books_private_corpus/ocr/lu_zhiji_fate_search/document.ocr.pages.jsonl` |
| `yuanhai_ziping_daquan` | `四库存目 子平汇刊 1 渊海子平大全 -- [宋] 徐子平 -- 四库存目子平汇刊, 2014 -- 华龄出版社 .pdf` | 272 | Image-only by native extraction. OCR recovered 272/272 pages, average confidence `0.865`. | `output/chinese_books_private_corpus/ocr/yuanhai_ziping_daquan/1-2014.ocr.pages.jsonl` |
| `sanming_tonghui_part3` | `图解三命通会 第3部论命精要 - 2009.pdf` | 490 | Image-only by native extraction. OCR recovered 490/490 pages, average confidence `0.848`. | `output/chinese_books_private_corpus/ocr/sanming_tonghui_part3/3-2009.ocr.pages.jsonl` |

Tools used:

- `tools/iching_corpus/inspect_pdf_metadata.py`
- `tools/iching_corpus/extract_private_pdf_text.py`
- `tools/iching_corpus/ocr_image_only_pdf_text.py`

The OCR workflow used per-book output folders because the existing slugifier collapses Chinese filenames to generic names like `document`. This avoids overwriting corpus outputs.

## Usable Rules

### Four Pillars And Luck Pillars

- Lu Zhiji supports the modern four-pillar, Day-Master-centered frame after older fetal-pillar models fell away (`lu_zhiji_fate_search`, pp. 108, 115).
- Luck pillars derive from the month pillar. Direction follows year-stem yin/yang plus calculation sex: yang male/yin female forward, yin male/yang female reverse (`lu_zhiji_fate_search`, pp. 164-166).
- Start age uses the distance to the prior or next solar term, explicitly a `jie` solar term rather than a `zhongqi`, with three days equaling one year (`lu_zhiji_fate_search`, pp. 165-166).
- Current implementation matches this main line in `backend/chinese_astrology/bazi.py`. True-solar time and late-Zi variants remain exposed options, but these four books did not provide a clear anchor for those variants.

### Day Master Strength

- The books support strength as season/month command first, then rootedness and assistance: `得令`, `得地`, `得助`, plus same-side versus opposing-side comparison (`lu_zhiji_fate_search`, pp. 157-160).
- `渊海子平大全` and `三命通会` both reject raw element counting as sufficient; month command, depth of qi, roots, support, control, and balance matter (`yuanhai_ziping_daquan`, pp. 52-55; `sanming_tonghui_part3`, pp. 31-32, 55-60).
- Current `season_root_formation_v2` is directionally valid, but it is a coarse scoring model. Future work should add finer strength gradations and source examples.

### Ten Gods

- Ten Gods are Day-Stem-relative and include visible stems and hidden stems (`lu_zhiji_bazi_advanced`, pp. 22-23; `lu_zhiji_fate_search`, pp. 115, 188-190).
- `渊海子平大全` gives the classic relational categories: what controls me, what produces me, what I control, what I produce, and same-kind (`yuanhai_ziping_daquan`, pp. 35-36, 52).
- Current direct/indirect polarity logic is structurally correct. Product copy should keep modern neutral language and avoid literal archaic gendered/social judgments.

### Useful Elements / Yong Shen

- The supported workflow is staged: strength and climate establish preliminary likes/dislikes, structure refines the Ten-God useful path, then image/special structures can override ordinary balancing (`lu_zhiji_bazi_advanced`, pp. 24-25, 107).
- `渊海子平大全` emphasizes `用神不可损伤`: if the useful god is damaged, other auspicious factors do not automatically compensate (`yuanhai_ziping_daquan`, pp. 53, 75-76).
- The current ordinary strong/weak favorable-element families can remain final only when confidence, presence, damage, and fixture gates are clear. Advanced families need stricter criteria before final release.

### Climate / Regulating Useful God

- Lu Zhiji strongly supports climate/regulating analysis and the priority of cold/heat/dryness/moisture correction (`lu_zhiji_bazi_advanced`, pp. 19, 47-50).
- However, Lu emphasizes day-stem-by-month regulating tables, not a simple season-only mapping (`lu_zhiji_fate_search`, pp. 236, 240, 249-255).
- Implemented first release: the engine now uses Lu's Jia day-stem by month regulating-stem table (`lu_zhiji_fate_search`, p. 240), the Yi/Wei example (`lu_zhiji_fate_search`, p. 250), plus the ten-day-stem preferred configuration summary (`lu_zhiji_fate_search`, pp. 251-255).
- The old season-only mapping remains as a preview fallback and cannot finalize Yong Shen.
- Climate finalization is now allowed only when a source-table regulating stem is selected, its element is present or timing-supported, no relationship-pressure blocker is active, and no special-structure blocker is active.

### Special Structures

- The corpus supports strict treatment of special structures such as `专旺`, follow structures, transformation structures, and two-element image structures (`lu_zhiji_fate_search`, pp. 281-298; `yuanhai_ziping_daquan`, pp. 110-112, 130, 143).
- These are exceptions where ordinary strong/weak balancing can be wrong.
- Current count-ratio and stem-pair screens are acceptable warning/evidence layers, but not yet source-grade classifiers. Final release for dominant, follow, and transformation structures has been disabled.

### Damaged Useful Element Logic

- Lu's damaged-useful logic is more specific than "any challenging contact." It includes structural damage such as officer harmed by output, wealth harmed by companions, resource harmed by wealth, output harmed by resource, and two-against-one injury (`lu_zhiji_fate_search`, pp. 219-221, 352).
- Current relationship-code pressure checks may overflag. Damaged-alternate finalization has been disabled until damage rules are tied to specific useful-god damage patterns.

### Timing

- Natal structure is the internal cause; luck/year/month/day/hour are external activators (`lu_zhiji_bazi_advanced`, p. 107).
- Da Yun and Liu Nian should modify confidence and timing/actionability, not independently release a final Yong Shen without natal source support (`lu_zhiji_fate_search`, pp. 166-167; `yuanhai_ziping_daquan`, pp. 128-129).
- Current timing-assisted finalization remains blocked, which is source-consistent.

### Compatibility

- The books do not provide strong explicit `合婚` scoring rules for the current compatibility engine.
- They support spouse palace/day branch, spouse star, Day Master strength, useful elements, and timing as relevant relationship evidence (`lu_zhiji_fate_search`, pp. 190-193, 429; `yuanhai_ziping_daquan`, p. 53; `sanming_tonghui_part3`, pp. 215-217).
- Current compatibility now remains qualitative: each natal spouse-palace, spouse-star, and timing layer is reported separately; no classical certainty score or aggregate pair verdict is produced.

### Auxiliary Stars

- Lu Zhiji and the classical corpus support auxiliary stars as secondary markers, not primary scoring (`lu_zhiji_fate_search`, pp. 132-136; `yuanhai_ziping_daquan`, pp. 38-47; `sanming_tonghui_part3`, pp. 303, 315-316, 355, 457).
- Current implemented subset is valid but incomplete: Peach Blossom, Traveling Horse, General Star, Wen Chang, Tian Yi, Tian De, Yue De.
- Candidate future additions: Gan Lu, Yang Ren, Hong Yan, Hua Gai, Jie Sha, Wang Shen, Gu Chen/Gua Su, Kong Wang.

### I Ching Oracle

- These four books do not provide standalone I Ching Oracle casting or changing-line rules.
- Mentions of `易经`, `周易`, and `卦` are historical, philosophical, BaZi-borrowing, or catalog context.
- No I Ching Oracle implementation changes are recommended from this corpus.

## Conflicts With Current Implementation

1. Climate finalization was too permissive. The app used season-generic climate override candidates, while Lu's regulating useful god work is day-stem-by-month and table-specific. This is corrected for the first released slice: Jia month table plus ten-day-stem configuration rows.
2. Special-structure finalization was too permissive. The app's broad dominant/follow/transformation screens do not yet enforce classical branch-completion, purity, seasonal confirmation, failure, and return-to-root rules.
3. Damaged-alternate finalization was too permissive. Current damage detection is broader than the specific `损用` and `破格` patterns in the corpus.
4. Strength scoring is directionally valid but too compressed. The corpus preserves finer gradations and warns against mechanical counting.
5. Auxiliary stars are valid as a subset but incomplete.
6. Compatibility lacks explicit source support for numeric scoring. The former index has therefore been removed in favor of transparent qualitative evidence and an explicitly non-authoritative cross-chart overlay.

## Corrections Implemented

Full source-enrichment update:

- Added `Bing` in `Hai` and `Geng` in winter month regulating rows from Lu Zhiji in addition to the earlier `Jia`/`Yi` slice.
- Added month-command structure selection before ordinary strong/weak balancing.
- Re-enabled final release for classified `dominant_element`, `follow_structure`, `transformation_structure`, and `damaged_alternate` families. The release is conditional: suspected dominant patterns, false follow, failed transformation, return-to-root blockers, generic pressure, and timing-only alternates stay withheld.
- Replaced broad damaged-useful finalization with source-pattern damage checks: officer damaged by output, wealth damaged by companions, resource damaged by wealth, and output damaged by resource.
- Added timing interpretation fields that distinguish Da Yun branch emphasis, Liu Nian stem emphasis, rescue, damage, activation, arrival/contact, movement, pressure, and exposure.
- Replaced compatibility scoring and judgement with `bazi_pair_qualitative_doctrine_v1`: individual natal spouse-palace, sex-dependent spouse-star, and timing evidence remain separate; Day-Master and unweighted presence comparisons are contextual; cross-chart contacts carry no outcome authority.
- Expanded auxiliary stars with Hua Gai, Yang Ren, Gan Lu, Hong Yan, Jie Sha, Wang Shen, Gu Chen, Gua Su, Kong Wang, Kui Gang, and San Qi as secondary markers.
- Frontend Useful Elements, Life Timing, Compatibility, and Auxiliary Stars panels now surface these added evidence rows.

- Replaced season-only climate finalization with a source-table climate/regulating layer:
  - `Jia` Day Master month table from `lu_zhiji_fate_search`, p. 240.
  - `Yi` Day Master in `Wei` month example from `lu_zhiji_fate_search`, p. 250.
  - Ten-day-stem regulating configuration summary from `lu_zhiji_fate_search`, pp. 251-255.
  - Season fallback remains evidence-only.
- Re-enabled final release for:
  - `climate_override`, gated by source row, regulator availability, pressure checks, fixture coverage, and special-structure blockers.
- Re-enabled advanced final release for classified:
  - `dominant_element`
  - `follow_structure`
  - `transformation_structure`
  - `damaged_alternate`
- Kept ordinary `strong_balancing` and `weak_support` finalization available when all gates are clear.
- Updated backend mirror files and tests in both source copies:
  - `backend/chinese_astrology/interpretation.py`
  - `backend/chinese_astrology/validation.py`
  - `backend/chinese_astrology/timing_rhythm.py`
  - `backend/chinese_astrology/relationships.py`
  - `backend/chinese_astrology/auxiliary_stars.py`
  - `frontend/backend/chinese_astrology/interpretation.py`
  - `frontend/backend/chinese_astrology/validation.py`
  - `frontend/backend/chinese_astrology/timing_rhythm.py`
  - `frontend/backend/chinese_astrology/relationships.py`
  - `frontend/backend/chinese_astrology/auxiliary_stars.py`
  - `backend/test_chinese_astrology_bazi.py`
  - `frontend/backend/test_chinese_astrology_bazi.py`

## Recommended Implementation Plan

1. Complete the full manually verified ten-day-stem by twelve-month `regulating useful god` table. The current release covers the Jia month table, the Yi/Wei example, and the all-stem configuration summary, but not every month-specific row for every stem.
2. Add source fixtures for special-structure success and failure: `专旺`, `从财`, `从杀`, `从儿`, `从势`, `假从`, `化气`, failed transformation, and return-to-root.
3. Replace generic damage pressure with a source-backed useful-god damage classifier: harmed officer, harmed wealth, harmed resource, harmed output, and two-against-one injury.
4. Add finer strength evidence labels for `得令`, `得地`, `得助`, same-side/opposing-side comparison, and "too strong / too weak / neutral" gradations.
5. Add missing auxiliary stars only after formula tables are manually checked against page images.
6. Keep compatibility qualitative and avoid presenting contextual natal or cross-chart evidence as a classical `合婚` verdict.
7. Do not change the standalone I Ching Oracle from this corpus.

## Verification Notes

OCR is research-grade. The Lu advanced text has lower confidence and traditional/simplified drift. Any table copied into logic must be manually checked against page images before it becomes a released rule family.
