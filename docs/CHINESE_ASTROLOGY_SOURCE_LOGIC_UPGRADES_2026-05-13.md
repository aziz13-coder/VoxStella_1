# Chinese Astrology Source Logic Upgrades - 2026-05-13

## Source Inventory

Private OCR corpus used for this pass:

- `output/chinese_books_private_corpus/ocr/lu_zhiji_bazi_advanced/document.ocr.pages.jsonl`
- `output/chinese_books_private_corpus/ocr/lu_zhiji_fate_search/document.ocr.pages.jsonl`
- `output/chinese_books_private_corpus/ocr/sanming_tonghui_part3/3-2009.ocr.pages.jsonl`
- `output/chinese_books_private_corpus/ocr/yuanhai_ziping_daquan/1-2014.ocr.pages.jsonl`

Extraction status:

- Lu Zhiji tiao hou tables: usable OCR, but compact matrix rows have OCR damage. The detailed day-stem tables on `lu_zhiji_fate_search:pp240-246` were used first; compact tables on `lu_zhiji_bazi_advanced:p21` and `lu_zhiji_fate_search:p247` were used as cross-checks.
- Geng and Gui tiao hou rows contain the most OCR damage. They are implemented with row-level `needs_page_image_check` flags where appropriate.
- Timing, relationship, body-balance, Tai Yuan, Kong Wang, Lu/Ma, and Na Yin references are usable as paraphrased rules with page refs.

## Usable Rules Implemented

- Full tiao hou table: ten Day Stems by twelve Month Branches, with regulating stems, priority, condition, source refs, and OCR confidence flags.
- Root-grade Day Master strength: hidden-stem roots now distinguish main/root residue rank, Day Branch normal root, Hour Branch secret root, and resource-root support.
- Ge ju selection: month-command structures now expose usable, damaged, rescued, mixed, and unclassified status; rescue and Ji/Xiang evidence are returned.
- Special structures: existing dominant/follow/transformation engine remains active, now contextualized behind structure selection and useful-element evidence.
- Damaged useful logic: source damage patterns now expose damage channels, rescue candidates, functional state, and two-against-one style pressure.
- Tong Guan: bridge candidates are surfaced as their own useful-element path when source damage creates a controlling-cycle conflict.
- Ying Qi timing: timing layers now show event activation, main-position links, spouse-palace synchronization, and layer roles for Da Yun, Liu Nian, month, day, and hour.
- Compatibility: spouse-star evidence now starts from calculation sex, using Wealth for male charts and Influence for female charts, before generic scoring.
- Health & Body Balance: Life Areas now include hidden-stem body-balance counts, element excess/deficiency, Day/Hour palace pressure, timing activation, and classical body correspondences.
- Auxiliary stars: marker output now includes placement interpretation, flowing month/day/hour activations, source refs, and readable Chinese labels via escaped Unicode.
- Classical extras: profile output now includes Tai Yuan, Ming Gong preview, and Na Yin rows as secondary comparison layers.

## Conflicts With Previous Implementation

- Climate logic was partly day-stem specific but still fell back to day-stem configuration or season-only rules for many cells. It now uses a full Day Stem + Month Branch table before any fallback.
- Root strength previously counted hidden stems too flatly. It now grades hidden-stem rank and root place.
- Compatibility previously proxied spouse-star support through useful-element exchange. It now exposes sex-based spouse star separately and keeps useful-element exchange as secondary.
- Life Areas health/body previously only reported strongest/lightest element counts. It now includes hidden stems, palace pressure, and timing evidence.
- Timing previously detected contacts but did not explicitly say what the timing was activating. It now returns `event_activation` and per-layer `ying_qi`.

## Implementation Plan Status

Completed in source files only:

- `backend/chinese_astrology/*`
- `frontend/backend/chinese_astrology/*`
- `frontend/src/features/astroclock/ChineseAstrologyPage.jsx`
- `backend/test_chinese_astrology_bazi.py`
- `frontend/backend/test_chinese_astrology_bazi.py`

Generated/package artifact folders were not edited.

Remaining recommended source work:

- Page-image verification for OCR-fragile Geng/Gui tiao hou cells.
- More worked examples for Tong Guan finalization and mixed ge ju clearing.
- UI polish for dense classical extras if users want it outside the More Analysis menu.
