# Chinese Astrology Source and Model Audit

Date: 2026-07-17

Scope: Four Pillars / BaZi calculation, interpretation, timing, relationships, compatibility, auxiliary stars, and their presentation in Astro Clock

Status: source-and-code audit and bounded remediation complete; canonical/mirror/backend/frontend verification passed, with the deferred model limits and roadmap below still open

## Executive Summary

The Chinese Astrology feature already has a substantial and generally well-separated implementation: birth data is normalized at the API boundary, astronomical solar-term calculations create the Four Pillars, and downstream modules add strength, Ten Gods, useful-element decisions, relationship contacts, timing, palaces, auxiliary stars, life areas, and presentation. The architecture is suitable for a serious source-governed model.

The audit nevertheless found four different classes of issue that must not be conflated:

1. **Deterministic implementation defects.** These include a branch-punishment transcription error, timing self-punishments not being emitted, one sex value being reused for both members of a pair, valid timing layers being hidden when Da Yun is unavailable, and clock-basis inconsistencies around late Zi hour. These are software defects and can be corrected with exact regression tests.
2. **School conventions.** Li Chun versus Lunar New Year, civil versus apparent solar time, the late-Zi day boundary, Luck Pillar direction, hidden-stem weighting, and transformation criteria vary by lineage or purpose. The app should expose these as named, versioned presets rather than presenting one choice as the universal Chinese-calendar rule.
3. **Product heuristics.** Root coefficients, hidden-stem rank weights, special-structure thresholds, and timing scores are modern computational choices. Unweighted element totals are now separated as presence inventory, and the unsupported compatibility index has been retired rather than presented as a traditional measurement.
4. **Interpretive claims.** Useful God, relationship outcomes, body correspondences, timing outcomes, and divinatory readings belong to a traditional symbolic system. The sources document doctrines and methods; they do not establish empirical predictive truth. The product must describe these outputs as traditional interpretations or experimental evidence layers, not validated facts.

The best-supported immediate corrections were made in source and tests. The next model release should focus on uncertainty propagation at calendar boundaries, executable source fixtures, a clean separation between element presence and modeled qi strength, and a provenance-aware Useful God decision graph.

## Scope and Non-Claims

This audit asks three different questions:

- Does the app calculate dates, time zones, solar terms, and sexagenary positions correctly?
- Does it implement a chosen traditional rule consistently with its cited source?
- Does the presentation honestly communicate what is computed, what is a school choice, and what remains interpretive?

Only the first question is independently testable against astronomical and civil-time authorities. The second can be checked for fidelity to a documented tradition, but traditions and editions can disagree. The third is a product-governance question.

This report does **not** claim that astrology has empirically demonstrated predictive validity. “Source-backed” means traceable to an identified source and reproducible as an implementation rule. It does not mean scientifically proven.

## Current Workflow and Architecture

### Request and calculation flow

| Stage | Current source | Responsibility |
| --- | --- | --- |
| Frontend request | `frontend/src/features/astroclock/api.mjs` | Posts profile, pair, and I Ching requests. Profile requests include the birth source and calculation options. Pair requests now support separate primary and relationship calculation-sex values while preserving the legacy single-value field. |
| UI and orchestration | `frontend/src/features/astroclock/ChineseAstrologyPage.jsx` | Selects saved snaps or manual data, chooses calculation variants, renders profile tabs, pair evidence, timing, source notes, and Oracle results. |
| API normalization | `backend/astro_clock_api.py` | `_chinese_astrology_birth_context()` resolves saved-snap or direct birth input into `BirthContext`; the BaZi, compatibility, and Oracle routes call the source engines. |
| Pillar engine | `backend/chinese_astrology/bazi.py` | Resolves local time, Li Chun and Jie boundaries, year/month/day/hour pillars, optional apparent-solar conversion, day-boundary variants, Da Yun direction/start age, annual and flowing pillars, and then assembles the full response. |
| Tables | `backend/chinese_astrology/tables.py` | Heavenly stems, Earthly branches, hidden stems, elements, polarity, and Ten-God relationships. |
| Strength | `backend/chinese_astrology/strength.py` | Applies the current `season_root_formation_v2` model, including season, hidden-stem roots, formation, evidence labels, and confidence. |
| Useful elements and interpretation | `backend/chinese_astrology/interpretation.py` | Builds Five-Factor/Ten-God profiles, climate or tiao-hou rows, month-command structure, damage checks, special-structure screens, Tong Guan candidates, fixture-gated Yong Shen decisions, and narrative sections. |
| Relationship contacts and pair comparison | `backend/chinese_astrology/relationships.py` | Detects natal and timing stem/branch contacts. Pair comparison now orders independently curated individual natal spouse-palace, spouse-star, and timing evidence; directional comparisons remain contextual, while cross-chart contacts are isolated as a product overlay with no outcome authority. |
| Timing | `backend/chinese_astrology/timing_rhythm.py` | Normalizes Da Yun, Liu Nian, and flowing month/day/hour layers; adds Ten-God roles, relationship contacts, useful-element effects, growth stages, and preview scoring. |
| Secondary layers | `backend/chinese_astrology/auxiliary_stars.py`, `palaces.py`, `life_areas.py` | Adds secondary markers, palace context, and domain-oriented interpretation. |
| Curation and validation ledger | `backend/chinese_astrology/curation.py`, `validation.py` | Labels computed, local-source, school-variant, provisional, and needs-validation rules; records fixtures and release gates. |
| Tests | `backend/test_chinese_astrology_bazi.py`, `frontend/backend/test_chinese_astrology_bazi.py`, `frontend/src/tests/chineseAstrologyPage.test.jsx`, `frontend/src/tests/astroclockApi.test.mjs` | Exercises canonical backend behavior, legacy source-mirror parity, page behavior, and API contracts. |

`backend/**` is the canonical desktop backend source. `frontend/backend/**` remains a legacy/source mirror for parity checks; generated/package output under `frontend/backend/build/**`, `frontend/dist/**`, `frontend/dist-electron/**`, and any `resources/**` or `win-unpacked/**` tree must not be edited. Frontend source lives under `frontend/src/**`. This audit and its remediation do not rely on edits to packaged or generated artifacts.

### Functional dependency order

The calculation dependency is approximately:

```text
birth instant + time zone + coordinates + selected convention
  -> local/civil and optional apparent-solar clocks
  -> Li Chun/Jie solar-term boundaries and sexagenary pillars
  -> hidden stems, Ten Gods, visible/branch/hidden element presence
  -> Day-Master strength evidence
  -> month-command structure, climate, damage, special-structure screens
  -> provisional favorable elements / fixture-gated Yong Shen
  -> natal contacts, Da Yun/Liu Nian/flowing contacts, palaces, stars
  -> life-area narratives and qualitative pair-evidence doctrine
  -> frontend summaries, evidence panels, and warnings
```

This order is directionally sound. The main model-governance risk is that later layers sometimes treat a provisional upstream label as if it were a sufficiently validated fact. A useful-element or compatibility output should carry the uncertainty and convention metadata of every upstream calculation it depends on.

## Evidence Hierarchy

The following hierarchy should govern implementation and release decisions:

1. **Astronomical and civil-time authorities** for observable calculations: solar longitude, solar terms, apparent solar time, time-zone history, UTC offsets, and calendar definitions.
2. **Primary or classical texts** for historical rule provenance: hidden-stem tables, month-command structures, traditional relationship codes, and stated interpretive doctrines. A classical source establishes that a doctrine exists, not that it is empirically true.
3. **Scholarly historical or anthropological work** for development, variation, and context across periods and lineages.
4. **Modern practitioner texts** for explicit operational workflows, contemporary terminology, and worked examples. These should be labeled by school or author where they go beyond widely shared tables.
5. **Internal project notes and code fixtures** for implementation history. These are useful ledgers, not independent evidence.

When sources conflict, the app should not silently average them. It should either:

- choose and label a preset;
- expose multiple presets with a comparison;
- return an uncertain/candidate result; or
- withhold the derived interpretation until the user supplies the missing information.

## Local Source Inventory and Findings

The local source manifest is `docs/iching_feature/source_manifest.yml`. Extracted private corpora are under `output/` and are not suitable for publication. This report paraphrases and cites page references rather than reproducing copyrighted passages.

The Chinese originals are held under `C:/Users/sabaa/Desktop/chinese books`; the per-book `index.json` files under `output/chinese_books_private_corpus/` retain each original filename, page count, extraction method, and SHA-256 digest. The English-source manifest retains its original absolute file paths in the same way. Repo-relative extracted paths are used below because they are the reproducible research locations available to the project.

### English-language corpus

| Source | Local evidence path | Verified use in this audit | Limitation |
| --- | --- | --- | --- |
| Serge Augier, *Ba Zi – The Four Pillars of Destiny* | `output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.pages.jsonl` and matching `.md` | pp. 43–46 give hidden stems and the strength sequence; p. 44 explicitly gives Season 70%, Root 25%, Formation 5%; pp. 45–46 distinguish Day-branch “normal” root and Hour-branch “secret” root; pp. 46–48 describe month-pillar-derived Luck Pillars, polarity/sex direction, and three-days-per-year start-age logic; p. 63 gives the twelve growth stages; p. 66 applies stages across pillars and hidden stems. | A modern practitioner presentation. The 70/25/5 architecture is source-visible, but the app’s pillar coefficients, hidden-rank coefficients, score cutoffs, and confidence thresholds are additional product choices. The same strength passage contains tension between its seasonal table and its prose treatment of Earth, which the app currently handles with a provisional cap. |
| Joey Yap, *BaZi – The Destiny Code* | `output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.pages.jsonl` | Useful for chart plotting, Day Master, Five Factors/Ten Gods, basic strength, favorable-element framing, Peach Blossom, and Luck Pillar presentation. | Modern school-specific operational source; not an authority for astronomical truth or universal numeric weights. |
| Joey Yap, *BaZi – The Destiny Code Revealed* | `output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.pages.jsonl` | Useful for branch/stem relationship contacts, hidden stems, affected palaces, timing activation, and warnings against reading a contact as an automatic outcome. PDF p. 89 explicitly scopes Combination Codes to connections within one BaZi and says this does not mean compatibility between two people. | Modern school-specific interpretation; it cannot support applying natal contact codes directly as a sourced cross-person compatibility method, and it does not support the product’s numeric compatibility index. |
| Kay Tom, *Chinese Astrology* | `output/iching_private_corpus/chinese-astrology.pages.jsonl` | Plain-language orientation for pillars, elements, zodiac animals, and generating/controlling cycles. | Introductory; unsuitable as a release authority for advanced structure or Useful God classification. |
| G. L. Golding, *The Chinese Fortune Telling System: BaZi Method* | `output/iching_private_corpus_ocr/the-chinese-fortune-telling-system-bazi-method.ocr.pages.jsonl` | Secondary cross-check material. | Image-only source; OCR average confidence is approximately 0.848. Every table transcription needs image verification. |
| Kerson and Rosemary Huang, *I Ching* | `output/iching_private_corpus/i-ching.pages.jsonl` | Relevant to the separate Oracle feature and source orientation. | I Ching casting and interpretation must remain separate from BaZi strength and Useful God logic. |

### Chinese-language corpus

| Source ID | Private evidence path | High-value page clusters used or identified | Reliability note |
| --- | --- | --- | --- |
| `lu_zhiji_fate_search` | `output/chinese_books_private_corpus/ocr/lu_zhiji_fate_search/document.ocr.pages.jsonl` | pp. 108, 115: Day-Master-centered Zi Ping frame; pp. 133–136: selected Shen Sha tables; pp. 157–160: 得令, 得地, 得助 and opposing-force comparison; pp. 164–167: Luck Pillar direction, Jie distance, three days per year, and timing; pp. 188–193: Ten Gods and spouse evidence; pp. 219–226: damaged-useful and disease/medicine cautions; pp. 236, 240–246: day-stem-by-month regulating tables; pp. 251–255: ten-stem regulating summaries; pp. 281–298: dominant, follow, and transformation structures; pp. 301–303 and 317: source-flow/Tong Guan; pp. 340 and 411–417: timing activation, position contact, fill-in, Fu Yin/Fan Yin. | 479 OCR pages, average confidence about 0.848. Climate and auxiliary-star rows must be checked against images. Code references logical book pages around 240–246; durable renders currently under `output/chinese_books_private_corpus/page_images/` use PDF page indices around `p0249`–`p0255`, so future fixture metadata should record both logical and PDF indices. |
| `lu_zhiji_bazi_advanced` | `output/chinese_books_private_corpus/ocr/lu_zhiji_bazi_advanced/document.ocr.pages.jsonl` | pp. 19–21 and 47–50: climate/regulating logic; pp. 22–25: Ten Gods and staged useful-element workflow; pp. 79–111: contacts, roots, transformations, timing; p. 107: natal structure versus external timing; pp. 148–176: spouse palace/star and timing; pp. 299–308: traditional body correspondences. A durable image for p. 21 exists at `output/chinese_books_private_corpus/page_images/八字命理學進階教程 (陆_p0021.png`. | Lowest-confidence major OCR source in the local Chinese set, about 0.756 average. It must never be the sole release basis for a copied table without page-image inspection. |
| `yuanhai_ziping_daquan` | `output/chinese_books_private_corpus/ocr/yuanhai_ziping_daquan/1-2014.ocr.pages.jsonl` | pp. 35–36 and 52–55: relational categories and month-command/root/support cautions; pp. 53 and 75–76: useful-god damage; pp. 110–143: special structures; pp. 128–129: timing; pp. 21–29 and 181–183: auxiliary-star and void material. | Classical collection accessed through a modern OCR edition, average confidence about 0.865. Use page images and an independent public text where exact characters or tables matter. |
| `sanming_tonghui_part3` | `output/chinese_books_private_corpus/ocr/sanming_tonghui_part3/3-2009.ocr.pages.jsonl` | pp. 31–32 and 55–60: strength cannot be reduced to raw counts; pp. 205–217: root/use and transformation/follow cautions; pp. 303, 315–316, 355, 450–460: auxiliary markers and family/body examples. | OCR average confidence about 0.848. The work itself contains multiple traditional layers; auxiliary stars should remain subordinate to core structure. |

### Specific climate-table corrections established by page comparison

The following rows were checked against the Lu Zhiji material and are represented in the current remediation:

- Yi Day Master in Si month: Gui only; the previously added Bing is not listed in the checked row.
- Yi Day Master in Wei month: Gui and Bing; the previously added Geng is not supported by the checked row.
- Bing in Hai: Jia, Wu, Geng, and Ren, with Geng conditional when Wood is excessive.
- Geng in Yin: Wu, Jia, Ren, Bing, and Ding; Ding had been omitted.
- Gui in Si: Xin is primary; Geng is a fallback only when Xin is absent.
- Gui in Shen: Ding is the primary listed regulator.
- Gui in Chou: Bing then Ding; Geng and Xin are conditional on a Fire configuration.

The 120 month cells across all ten tables were visually checked against the original PDF pages 240–246. Lu’s footnote identifies these as his reproduction of Zhong Yiming’s tables, cross-checked against Liang Xiangrun and slightly revised. The source supplies stems and prose conditions; the app’s `primary`/`secondary`/`conditional`, function, and override fields remain computed product interpretation. These corrections do not prove that every lineage uses the same tiao-hou table or priority.

### Additional local-corpus cautions and corrections

- The Hong Yan row in Lu PDF p. 133 maps an Yi Day Stem to Wu, not Shen. The table value and per-marker source page were corrected and regression-tested.
- Lu pp. 131–133 describes the historical proliferation and instability of Shen Sha and presents a selected list for reference. Auxiliary stars should therefore stay secondary and carry no power to override month command, strength, structure, or a withheld result.
- Thirteen files under `docs/iching_feature/*.md` are 100% NUL bytes. They are corrupt placeholders and must not be cited as evidence; use `source_manifest.yml`, extracted source pages, and originals instead.
- No local full-text source was found for Zi Wei Dou Shu or Hosoki/Six-Star methods, so those systems should not be inferred from the BaZi corpus.

## Authoritative and Public Comparison Sources

### Astronomy and civil time

| Source | What it supports | What it does not support |
| --- | --- | --- |
| [Hong Kong Observatory: 24 Solar Terms](https://www.hko.gov.hk/en/gts/time/24solarterms.htm) | The terms divide the Sun’s apparent ecliptic path into 15-degree segments and identify their longitudes, including Li Chun at 315 degrees and Jing Zhe at 345 degrees. This is appropriate for testing the app’s solar-longitude crossings. | It does not establish a universal BaZi interpretive school. |
| [Hong Kong Observatory: solar-term dates and times](https://www.hko.gov.hk/en/gts/astronomy/Solar_Term.htm) | Published term instants are suitable external reference fixtures after explicit conversion from Hong Kong Time to UTC. | It is not a source for Useful God, structure, or compatibility. |
| [Hong Kong Observatory: Heavenly Stems and Earthly Branches](https://www.hko.gov.hk/en/gts/time/stemsandbranches.htm) | Public cross-check for the sexagenary nomenclature and cycle. | It does not settle all Four Pillars boundary conventions. |
| [Hong Kong Observatory: “What year is it today?”](https://www.hko.gov.hk/en/education/astronomy-and-time/time-service/00506-what-year-is-it-today.html) | The official Chinese-calendar sexagenary year changes with the first day of the first lunar month. This is important product terminology. | It should not be cited as evidence that the official calendar year changes at Li Chun. Li Chun is the selected BaZi year-pillar convention and must be labeled that way. |
| [Hong Kong Observatory: apparent solar time](https://www.hko.gov.hk/en/gts/time/basicterms-apparentsolartime.htm) | Apparent solar time is local mean solar time corrected by the equation of time. | It does not determine whether a BaZi school should use that clock for the hour or day boundary. |
| [U.S. Naval Observatory: equation of time](https://aa.usno.navy.mil/faq/eqtime) | Independent definition and astronomical cross-check for equation-of-time behavior. | It does not authorize a particular astrological day-boundary preset. |
| [NREL Solar Position Algorithm](https://www.nrel.gov/docs/fy08osti/34302.pdf) | A high-precision reference algorithm for apparent solar position and equation-of-time calculations. | It is an engineering reference, not an astrology source. |
| [IANA Time Zone Database](https://www.iana.org/time-zones) | Historical UTC-offset and daylight-saving transitions by zone. | A longitude correction cannot replace historical civil-time-zone data. |

### Classical and scholarly context

| Source | Relevant comparison |
| --- | --- |
| [Yuanhai Ziping on Chinese Text Project](https://ctext.org/wiki.pl?chapter=296619&if=gb) and [Wikisource edition](https://zh.wikisource.org/wiki/%E6%B7%B5%E6%B5%B7%E5%AD%90%E5%B9%B3%E5%A4%A7%E5%85%A8) | Public witnesses for hidden stems and Zi Ping doctrine. They support provenance checks but still require edition-aware comparison. |
| [Zi Ping Zhen Quan](https://ctext.org/wiki.pl?chapter=974137&if=gb) | Strong support for treating month-command/structure 用神 separately from a generic strong/weak “helpful element.” |
| [Di Tian Sui Zheng Yi](https://zh.wikisource.org/zh-hant/%E6%BB%B4%E5%A4%A9%E9%AB%93%E9%97%A1%E5%BE%AE) | Warns against treating in-season/out-of-season labels as sufficient without roots and support. |
| [Qiong Tong Bao Jian](https://zh.wikisource.org/zh-hant/%E7%A9%B7%E9%80%9A%E5%AF%B6%E9%91%92) | Public comparison for tiao-hou or climate-oriented doctrine. |
| [Sanming/encyclopedic luck material](https://zh.wikisource.org/zh/%E6%AC%BD%E5%AE%9A%E5%8F%A4%E4%BB%8A%E5%9C%96%E6%9B%B8%E9%9B%86%E6%88%90/%E5%8D%9A%E7%89%A9%E5%BD%99%E7%B7%A8/%E8%97%9D%E8%A1%93%E5%85%B8/%E7%AC%AC598%E5%8D%B7) | Historical comparison for Luck Pillar direction and contacts. |
| [Shen Feng Tong Kao](https://zh.wikisource.org/zh-hant/%E7%A5%9E%E5%B3%B0%E9%80%9A%E8%80%83) | Additional traditional comparison for structure and disease/medicine approaches. |
| [Sanming Tonghui, volume 3](https://zh.wikisource.org/zh-hant/%E4%B8%89%E5%91%BD%E9%80%9A%E6%9C%83_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29/%E5%8D%B703) | Useful caution that Shen Sha/auxiliary markers should not replace the core chart judgment. |
| [Chao Wei-pang, “The Chinese Science of Fate-Calculation” (1946)](https://asianethnology.scholasticahq.com/article/147961.pdf) | Historical description of day-centered Zi Ping practice, year-stem polarity/sex Luck direction, and the three-days-per-year method. It documents practice; it does not validate predictive truth. |
| [Historical study of Chinese fate calculation](https://doi.org/10.29933/SHSS.201105.0005) | Scholarly context for the development of methods and the need to avoid presenting one late synthesis as timeless uniform doctrine. |
| [KCI study of hidden-stem theory](https://journal.kci.go.kr/ipir/archive/articleView?artiId=ART003050084) | Evidence that hidden-stem theories and historical explanations vary. This supports explicit versioning of any weighting model. |
| [KCI study of Zi Ping structure](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002687772) | Scholarly comparison for structure classification and its interpretive development. |
| [Thesis on quantitative BaZi modeling](https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi/login?o=dnclcdr&s=id%3D%22108TFDU0785031%22.&searchmode=basic) | Useful evidence that numeric strength systems are modern formalizations rather than a single historically standardized scale. |

## Discrepancy Matrix

### A. Deterministic defects or contract defects

| Finding | Current consequence | Resolution or recommendation |
| --- | --- | --- |
| The uncivilized punishment pair was transcribed as Mao–Si instead of Zi–Mao. | False Mao–Si events and missing Zi–Mao events could affect natal, timing, auxiliary-star pressure, and narratives. | Corrected to Zi–Mao in both source copies, with positive Zi–Mao and negative Mao–Si regressions. |
| Dynamic timing detection did not emit repeated-branch self-punishments for Chen, Wu, You, or Hai. | Natal self-punishment could appear while the same relationship introduced by Da Yun/year/month/day/hour remained invisible. | The same detector now runs in dynamic scopes and requires the timing point to participate; regression coverage passes. |
| Pair calculation reused one calculation-sex value for both subjects. | Directional Da Yun and sex-dependent spouse-context evidence for one participant could be calculated with the other participant’s value. | `primary_calculation_sex` and `relationship_calculation_sex` are now separate end to end; legacy `calculation_sex` remains a fallback, both profiles are returned/retained, and independent-value tests pass. |
| The Life Timing UI treated Da Yun availability as the gate for the whole timing surface. | Annual and flowing month/day/hour results were hidden when calculation sex was absent even though those layers were valid. | Only Da Yun-specific cards are now gated; annual and flowing layers remain visible and focused UI tests pass. |
| Late-Zi day shifting could inspect a clock basis different from the selected civil/apparent-solar day basis. | A birth near a date or hour boundary could receive an internally inconsistent day and hour pillar. | Late-Zi now uses the selected clock basis, records that basis in debug output, and passes crossings in both directions. |
| Structure damage counts included the visible Day Master stem as a Companion. | A Wealth structure could appear automatically damaged simply because every chart necessarily contains its Day Master. | The visible Day Master is excluded while other same-element stems and hidden stems remain counted; a Wealth-structure regression passes. |
| Follow/transformation root blockers inspected the Day branch but did not consistently include the Hour “secret root.” | A chart with an Hour hidden same-element root could be incorrectly classified as rootless follow or successful transformation. | Return-to-root checks now include the Hour hidden same-element secret root; positive and blocker cases pass. |
| Same-element dominant structures depended on strength labels the real strength engine did not emit. | A documented code path was effectively unreachable for real profiles while synthetic test dictionaries could reach it. | The classifier now consumes the emitted `strong` band only under strict 70% dominance, month/frame, and no-controller gates; full-profile regressions pass. |
| Unknown birth time is represented through a default time while year/month boundaries may occur on that local date. | An exact-boundary unknown-time birth can receive one authoritative pillar result when two candidates are possible. | Return a candidate set and uncertainty interval whenever the unknown-time window crosses Li Chun, a Jie, or a selected day boundary; withhold dependent final interpretations. |
| Solar-term lookup failure can fall back to an approximate value and risk caching it. | A transient astronomical failure near a boundary can silently flip a pillar and persist the wrong result. | Fail closed inside a defined boundary band; do not cache a transient approximation as authoritative; expose method, tolerance, and error state. |
| Frontend requests are not consistently protected against stale out-of-order completion. | Rapid control changes can allow an older response to overwrite the newest chart. | Use `AbortController` and/or a request signature; only commit a response matching the current input signature. Add delayed-response UI tests. |
| Saved-snap date labels can be formatted in the operator’s zone rather than the snap’s declared zone. | A displayed date can differ from the calculation date, creating an auditability problem. | Pass the snap time zone into `Intl.DateTimeFormat` and test a UTC/date-boundary case. |

### B. School conventions that require explicit presets

| Convention | Evidence and conflict | Product rule |
| --- | --- | --- |
| BaZi year at Li Chun versus official Chinese-calendar year at Lunar New Year | The engine uses the astronomical Li Chun crossing. HKO’s official calendar explanation changes the sexagenary year at the first lunar month. These are different questions. | Label the current option “BaZi year-pillar convention: Li Chun.” Never label it simply “Chinese-calendar year.” Allow an almanac preset only if there is a documented use case and fixtures. |
| Month boundaries at the twelve Jie terms | This is well supported within the selected BaZi workflow and can be calculated astronomically. | Keep as the default BaZi month preset; expose the actual boundary instant, term longitude, source, and uncertainty. |
| Civil local time versus apparent solar time | Astronomy defines the conversion; BaZi schools differ over whether and where to apply it. | Keep civil time as a named default and apparent solar as an explicit option. Separately name hour-clock and day-boundary choices. |
| Day change at civil/apparent midnight versus 23:00 late Zi | The code already exposes standard and late-Zi variants; local sources do not settle a universal choice. | Version as presets and show a side-by-side pillar comparison when the choice changes the chart. |
| Luck direction | The selected year-stem polarity plus calculation-sex rule is supported in the local Augier and Lu material and historical scholarship; alternative polarity anchors exist. | Retain explicit `luck_direction_rule`; display the chosen rule and the forward/reverse derivation. Do not infer calculation sex from identity or name. |
| Luck start age | Three days per year is source-supported, but sources and software differ on rounding, fractional age, exact adjacent Jie, and calendar-age display. | Store exact duration and derived fractional years; derive a human label separately. Add fixtures for forward/reverse and exact remainder handling. |
| Hidden-stem composition and weighting | Basic hidden-stem tables are broadly documented, while historical theories and weighting schemes vary. | Version the table and the qi-weight model independently. Never present rank coefficients as astronomical quantities. |
| Combination versus transformation | A pair/set contact can be detected neutrally; successful transformation depends on season, roots, purity, blockers, and school rules. | Emit `contact_detected` first; allow `transformation_candidate` or `classified` only through a selected, source-identified structure preset. |

### C. Product heuristics

| Heuristic | Audit finding | Recommended treatment |
| --- | --- | --- |
| Strength 70/25/5 | The architecture is explicitly present in Augier p. 44. The app then maps seasonal states to numeric values, assigns Day/Hour/Month/Year root weights of 3/2/2/1, hidden-rank weights of 1/.65/.35, resource/control/drain discounts, caps, cutoffs, and confidence bands. Those additional numbers are not established by the cited passage. | The response now identifies `augier_school_heuristic_70_25_5_v1` and marks every secondary coefficient/threshold and the Earth reconciliation as product policy. Next, publish those parameters in a reader-facing method drawer and calibrate against worked cases; never call the score “traditional percent strength.” |
| Element balance | `_element_balance()` separately counts visible stems, branch bodies, and every hidden stem, then sums them. The primary hidden stem can repeat the branch’s body element, and every hidden rank counts equally in the total. | Keep “presence counts” as a descriptive inventory only. Build qi-strength from season, root depth, rank, exposure, and transformations in a separate model. Label the current UI “Unweighted element presence” and render zero as zero width. |
| Earth seasonal cap | The local passage says Earth is always medium while its adjacent table places Earth differently by season. The code caps severe Earth weakness. | Mark as an explicit reconciliation policy, not a fact. Add an Earth-policy preset or return the conflict in evidence until a chosen lineage is documented. |
| Structure ratios | Dominant/follow/transformation screens use modern ratios and thresholds. | Treat thresholds as classifier parameters, not classical constants. Require structural predicates and executable positive/negative cases before final release. |
| Timing weights and score | Da Yun, Liu Nian, and flowing layers use modeled stem/branch weights and a tone score. The broad layer hierarchy is source-informed, but the numbers are product choices. | Expose timing as activation evidence. Keep outcome language and “supportive/pressuring” scores provisional until worked examples are independently curated. |
| Retired compatibility `/100` | The former index began from a product baseline and weighted contacts, spouse palace, Day-Master exchange, timing, and raw element-count matches. Joey Yap Book 2 p. 89 expressly says its Combination Codes describe relations within one chart, not compatibility between two people; no local source supplies that formula, baseline, weights, or bands. | The formula, score, grade, weights, bands, and calibration claims have been removed. `bazi_pair_qualitative_doctrine_v1` keeps each subject's natal spouse-palace, sex-dependent spouse-star, and relationship-timing evidence separate. Day-Master and unweighted element-presence comparisons are contextual only; the cross-chart overlay has `outcome_authority: none`. |
| Auxiliary-star aggregation | Formula tables can be deterministic within a selected source, but their importance and combination are interpretive. | Give Shen Sha zero authority to override pillars, month command, strength, or structure. Present them as secondary traditional markers. |

### D. Interpretive or insufficiently validated claims

| Claim surface | Risk | Safeguard |
| --- | --- | --- |
| Final Yong Shen | The validation ledger historically counted narrative `rule_family_fixture` declarations. A prose fixture can release the same rule it declares without running a source chart through the engine, making the gate circular. | Release qualification now requires executable chart input plus assertions. Narrative fixtures remain documentation only, so all currently unsupported advanced families correctly remain withheld. |
| Collapsing all “useful element” doctrines | Month-command/格局 用神, support/suppression 喜用, climate/調候, Tong Guan, disease/medicine, and special-structure paths have different questions and can disagree. | Return them as parallel named analyses. A final recommendation, if offered, must show which path controls and why other paths were subordinate or blocked. |
| Combinations are good and clashes are bad | Classical and modern sources use contacts contextually; effect depends on element, palace, structure, timing, and whether transformation occurs. | Detect contacts neutrally first. Use “combination/contact,” “movement,” or “pressure” rather than destiny verdicts. |
| Timing predicts events | Sources offer traditional activation logic but the app lacks a large independently curated outcome corpus. | Use “activation window,” “traditional timing emphasis,” and “candidate trigger.” Do not promise that an event will occur. |
| Compatibility predicts relationship quality | The local corpus does not establish an aggregate 合婚 formula, and Book 2 p. 89 explicitly limits Combination Codes to one chart. | Do not compute an aggregate pair verdict. Put each natal profile and individual timing evidence first; label directional presence and cross-chart contacts as contextual observations with no outcome authority. |
| Health & Body Balance | Traditional organ/element correspondences are not medical diagnosis or evidence-based risk estimates. | Add a permanent, visible non-medical disclaimer; use symbolic wellbeing language; never diagnose, recommend treatment, or discourage professional care. |
| I Ching Oracle | A casting algorithm can be reproduced, but its divinatory meaning is interpretive. Coin casting initiated by software is simulated rather than a user’s physical toss. | Label “simulated coin cast”; label manual lines bottom-to-top; keep BaZi sources from changing the standalone Oracle; avoid certainty language. |

## Corrections in This Turn

The following bounded corrections were implemented in both source trees where applicable and verified:

| Correction | Final status |
| --- | --- |
| Mark `pillars.year_li_chun` as a BaZi school/convention rule and distinguish it from the official Chinese-calendar Lunar New Year rollover. | Implemented in both curation mirrors with HKO distinction/reference. |
| Correct Zi–Mao punishment, reject Mao–Si, and include dynamic timing self-punishments. | Implemented with positive, negative, and timing-participation regressions. |
| Separate primary and relationship calculation sex across React, API payload, backend route, returned profiles, local saves, and exports; retain legacy fallback. | Implemented; relationship input defaults unset, and end-to-end tests pass. |
| Keep annual and flowing timing visible without Da Yun. | Implemented; only Da Yun basis, active decade, sequence, and debug are gated. |
| Correct all six literal Lu table mismatches: Yi/Si, Yi/Wei, Bing/Hai, Geng/Yin, Gui/Si, and Gui/Shen; preserve verified Gui/Chou conditional prose. | Implemented after visual review of all 120 cells, with exact-order/condition mirrored tests. |
| Identify the climate table as Lu’s reproduction/revision of Zhong/Liang and mark app priority/function/override metadata as computed. | Implemented in source basis and notes. |
| Prevent an unresolved `needs_page_image_check` climate row from becoming an override/final Useful God. | Implemented and gate-tested. |
| Exclude the visible Day Master itself from structure-damage Ten-God counts. | Implemented with Wealth-structure regression. |
| Include the Hour hidden same-element “secret root” in follow/transformation blockers. | Implemented with positive and false-follow/failed-transformation cases. |
| Make same-element dominant structures reachable from emitted `strong` only under strict dominance/month/frame/no-controller gates. | Implemented and tested through the real profile path. |
| Apply late-Zi shifting to the selected civil/apparent-solar clock basis and record the basis. | Implemented with both directions of date crossing. |
| Restrict final Yong Shen gates to executable engine fixtures. | Implemented; narrative declarations contribute documentation counts but cannot release a family. |
| Correct Yi Day Stem Hong Yan from Shen to Wu and replace global Shen-Sha citations with per-marker Lu/Sanming pages. | Implemented with source-table regression. |
| Restrict Kui Gang to the source-defined natal Day Pillar; do not promote matching timing pillars without a source. | Implemented with a timing-negative regression. |
| Correct Tong Guan source references from unrelated Lu pages to pp. 301–303 and 317. | Implemented in both interpretation mirrors. |
| Preserve strength math but identify it as `augier_school_heuristic_70_25_5_v1`; mark secondary coefficients, thresholds, and Earth cap as product policy. | Implemented without silently recalibrating the model. |
| Replace unsupported pair math with independently curated qualitative doctrine and explicit scope guards. | Implemented; numeric score/grade/weights were removed. Romantic context starts with each natal spouse palace and spouse star, family/business exclude marriage-specific layers, and Book 2 p. 89 gates the cross-chart overlay to `outcome_authority: none`. |
| Relabel element bars as unweighted presence and render zero as zero width. | Implemented in the UI; the underlying qi-strength redesign remains a roadmap item. |

Final verification:

- Canonical backend: 96 passed.
- Mirrored backend: 96 passed.
- Focused frontend/API: 61 passed across two files.
- Focused frontend ESLint: passed.
- Python compilation for all relevant source/test/API files: passed.
- Chinese astrology source parity: every Python source twin is byte-identical except `bazi.py`, whose only difference is the pre-existing Swiss Ephemeris import/bootstrap block.
- Generated/package path guard: no changes under `frontend/dist-electron/**`, `frontend/backend/build/**`, `frontend/dist/**`, `website/**`, `resources/**`, or `win-unpacked/**`.
- Only warning: a third-party `pytz` deprecation for `datetime.utcfromtimestamp`.

## Recommended Target Model

### Separate four layers of state

The response contract should distinguish:

1. **Observed/computed state:** birth instant, civil offset, apparent-solar correction, solar longitude, term boundary, stem/branch, hidden-stem table row.
2. **Convention state:** year boundary, month boundary, day boundary, hour clock, Luck direction, start-age rounding, hidden-stem preset.
3. **Modeled state:** strength score, root grades, structure classifier, climate priorities, and timing weights.
4. **Interpretive state:** Useful God narrative, life-area themes, relationship interpretation, symbolic body correspondences, Oracle reading.

Each derived field should carry at least:

- `method_id` and semantic version;
- `status` such as computed, candidate, classified, withheld, or unavailable;
- source IDs and page/URL anchors;
- convention/preset IDs;
- uncertainty or blockers;
- fixture IDs that actually executed the rule;
- dependencies on upstream method versions.

### Keep Useful God paths distinct

A better response shape would preserve parallel paths:

- `ge_ju_month_command`: month-command structure and its success, damage, rescue, or mixture;
- `fu_yi_balance`: support/suppression based on strength;
- `tiao_hou_climate`: cold/heat/dryness/moisture regulation from a named table;
- `tong_guan_mediator`: a bridge that restores flow between opposed forces;
- `bing_yao_damage_rescue`: disease/medicine or damaged-useful analysis;
- `special_structure`: dominant, follow, transformation, false/failed, and return-to-root evidence.

The final decision layer should not average these into one score. It should state precedence, agreement, disagreement, and the reason for withholding.

### Separate element presence from qi strength

Retain the current visible/branch/hidden counts for auditability, but rename them as presence. A new strength representation should include:

- month-command state;
- real root versus resource support;
- hidden-stem rank and branch phase;
- visible support and control;
- storage/tomb handling;
- combination/transformation state;
- whether a force is exposed, rooted, absent, damaged, rescued, or timing-supplied;
- a confidence interval or categorical band rather than false numeric precision.

## Fixture and Validation Strategy

### 1. Astronomical fixtures

Create machine-readable fixtures for every Jie boundary used by the month engine and several Li Chun boundaries:

- source URL and publication;
- published local time and source time zone;
- converted UTC instant;
- expected solar longitude;
- allowed time tolerance;
- expected year/month pillar immediately before, at, and immediately after the boundary.

Include multiple longitudes and IANA zones, DST transitions, historical offset changes, and southern/eastern/western longitude extremes. Sweep at least ±1 second, ±1 minute, and the app’s declared uncertainty band.

### 2. Day and hour boundary matrix

For each relevant case, run:

- civil clock + civil midnight;
- civil clock + late-Zi next-day;
- apparent-solar hour + civil day;
- apparent-solar hour + apparent-solar midnight;
- apparent-solar hour + late-Zi on the selected apparent-solar clock.

Include eastward and westward longitude corrections that cross the civil date and cases within ten minutes of a two-hour branch boundary. Assert the selected basis, comparison payload, warning, and final pillar.

### 3. Unknown-time candidate fixtures

Represent unknown time as an interval, not noon. Test:

- an ordinary date with stable year/month/day and unknown hour;
- a local date containing Li Chun;
- a local date containing a Jie;
- a date where the selected apparent-solar or late-Zi rule can change the day.

Assert candidate pillars and that dependent root, structure, Useful God, spouse, timing, or life-area claims are withheld when they differ across candidates.

### 4. Table exhaustiveness

Use exhaustive tests for:

- all 10 stems × 12 branches and hidden-stem rows;
- all 60 sexagenary pairs and day-cycle anchors;
- all stem combinations;
- all branch combinations, clashes, harms, destructions, punishment pairs, self-punishments, three-harmony sets, seasonal sets, and incomplete-set negatives;
- all Ten-God relationships by polarity.

These tests should check symmetry, no unintended pairs, and no accidental duplicates across natal and timing scopes.

### 5. Strength and structure fixtures

Every source worked case should have:

- original birth/chart input when supplied;
- manually verified pillars;
- expected de-ling, de-di, de-zhu evidence;
- normal/secret/storage/rootless classification;
- expected strength band, with acceptable disagreement noted if the source is qualitative;
- expected structure candidates and blockers;
- an adversarial paired case that differs by one decisive root, season, or controller.

Synthetic pillar dictionaries are useful unit tests but cannot by themselves release an interpretive family. At least one positive and one negative fixture per rule must run from birth input through the production profile builder; higher-risk final families should require several independent cases and a holdout set.

### 6. Climate table curation

For all 120 Day-Stem × Month-Branch rows:

- verify the page image manually;
- record logical page, PDF page index, edition, source image hash, regulator order, conditions, and taboos;
- distinguish primary, secondary, conditional, and fallback;
- add a positive condition fixture and a negative “condition absent” fixture;
- make every unresolved OCR row non-final by construction.

The code should generate a coverage report so no missing row silently falls back to a generic season rule while appearing source-specific.

### 7. Executable Yong Shen release gates

A qualifying fixture should be considered executable only when it includes:

- a real engine input or a separately verified full pillar chart;
- selected convention and model versions;
- source anchor and page-image-verification status;
- assertions for intermediate strength, structure, climate, presence, damage, and timing evidence;
- an expected rule family and expected `final` or `withheld` state;
- a negative case that exercises the blocker rather than merely declaring one.

Fixture declarations that contain only prose, family name, polarity, and expected status should appear in documentation counts but contribute zero to release eligibility.

### 8. Compatibility and presentation tests

Pair fixtures should first assert neutral contact facts and separate sex-dependent timing profiles. Numeric-band calibration, if retained, needs an independently curated qualitative corpus and holdouts. Frontend tests should verify:

- separate primary/relationship sex values;
- profiles returned and displayed consistently;
- timing remains visible without Da Yun;
- zero element presence renders as zero;
- warnings and method labels are visible in production;
- stale requests cannot replace a newer result;
- no compatibility number, grade, band, or outcome claim is rendered;
- unresolved birth-time boundary profiles withhold pair doctrine before any cross-chart overlay is shown;
- body-balance and Oracle disclaimers are persistent.

## Prioritized Roadmap

### P0 — deterministic integrity and release gates

1. Finish and verify the corrections listed above in canonical backend, legacy mirror tests, API contract, and UI.
2. Replace silent solar-term fallback near boundaries with explicit failure/uncertainty behavior.
3. Represent unknown birth time as a candidate interval and propagate uncertainty downstream.
4. Add request cancellation/signatures in the Chinese Astrology page.
5. Complete astronomical, day-boundary, relationship-table, and separate-sex regression matrices.
6. Require executable fixtures for every final Yong Shen family; temporarily withhold any family supported only by narrative fixtures.

### P1 — model governance and source fidelity

1. Version the calendar convention preset separately from the interpretation model.
2. Split element presence from qi strength and publish all strength coefficients.
3. Complete the 120-row tiao-hou table with dual page indices and image hashes.
4. Build structure v2: month command, purity/mixing, success, damage, rescue, useful assistant, false follow, failed transformation, and return-to-root.
5. Keep support/suppression, climate, structure, Tong Guan, and disease/medicine paths separate through the API and UI.
6. Add a reader-facing “Method & evidence” drawer in production rather than hiding provenance behind a development flag.

### P2 — interpretation calibration

1. Turn timing into a transparent activation/ying-qi engine before attempting outcome language.
2. Expand independently curated spouse-palace, spouse-star, and individual timing fixtures without reintroducing an aggregate grade; keep Day-Master and element-presence comparisons contextual and cross-chart contacts non-authoritative.
3. Enrich auxiliary-star placement and timing only after formula tables are image-verified; never grant override power.
4. Improve body-balance wording and evidence while maintaining a non-medical boundary.
5. Keep the I Ching Oracle an independent module; improve casting labels and line-order UX without importing BaZi doctrine into it.

## Terminology and Presentation Safeguards

Use:

- “BaZi year-pillar convention: Li Chun,” not “the Chinese year starts at Li Chun.”
- “Apparent solar time” for the astronomical clock and “true-solar BaZi preset” only for the user-facing convention.
- “Unweighted element presence” for the current count display.
- “Traditional relationship contact” rather than “good/bad compatibility event.”
- “Candidate,” “classified under this preset,” “withheld,” and “uncertain” as first-class statuses.
- “Qualitative pair evidence” and “cross-chart comparison overlay” rather than a compatibility score, fate grade, or interpersonal verdict.
- “Traditional symbolic body correspondence; not medical guidance.”
- “Simulated coin cast” when the software generates coin values.
- “Line 1 — bottom” through “Line 6 — top” for manual I Ching lines.

Avoid:

- deterministic promises about marriage, wealth, illness, career, or event dates;
- interpreting an absent element as a literal deficiency or diagnosis;
- treating a combination as automatically fortunate or a clash as automatically harmful;
- calling a modern coefficient “classical percentage”;
- hiding school/model choice when it changes a pillar;
- using auxiliary stars to overturn the core chart;
- treating agreement among related practitioner books as independent empirical validation.

## Release Checklist

A Chinese Astrology release should be considered ready only when:

- all modified source files compile;
- canonical and legacy-mirror backend suites pass;
- focused API and React suites pass;
- source twins differ only where their bootstrap environments intentionally differ;
- no generated, runtime, packaged, `website`, `dist`, `build`, `resources`, or `win-unpacked` path was edited;
- every newly final rule has executable positive and negative fixtures;
- every OCR-derived table row used for finalization has a page-image verification record;
- boundary uncertainty, selected presets, method IDs, and blockers survive through the API to the UI;
- production wording retains provenance and non-medical/non-predictive safeguards.

## Conclusion

The feature does not need a wholesale rewrite. Its strongest path forward is stricter layering:

- treat astronomy and civil time as deterministic, tolerance-bounded, externally testable infrastructure;
- treat BaZi conventions as explicit presets;
- treat numeric strength, timing, and compatibility as versioned product models;
- treat classical interpretation as a transparent traditional framework with uncertainty and release gates.

That separation will make the calculations more reliable, the source comparison more honest, and future model improvements easier to evaluate without claiming more than the evidence supports.
