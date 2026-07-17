# Chinese Astrology Advanced Resolution Plan

Date: 2026-05-12

## Purpose

This plan turns the current "still missing" list into an implementable sequence for the Chinese Astrology feature. The release standard is source-backed: final Yong Shen / Useful God and Oracle rulings graduate only when the app has source anchors, positive fixtures, negative fixtures, backend gates, frontend evidence, and tests.

The original reason final Useful God was withheld was that the plumbing existed, but the rule families were not sufficiently graduated. After the 2026-05-13 Chinese-source audit, only the ordinary `strong_balancing` and `weak_support` families remain eligible to emit final rulings when all gates are clear. Climate override, dominant element, follow structure, transformation structure, damaged alternate, timing-assisted finalization, and extreme-strength exceptions remain evidence-only until their stricter Chinese-source criteria are curated and tested.

## Hosoki / Six-Star Boundary And BaZi Rhythm Scope

The product will not implement Kazuko Hosoki's Six-Star Divination system, its branded star labels, or its named fortune-cycle terminology. The local source audit already treats Hosoki/Six-Star as bibliographic only: there is no full-text local source to extract, verify, or legally use as a rule basis.

The useful feature underneath the user's question is the older BaZi timing rhythm:

- `Da Yun`: 10-year Luck Pillars, derived from the natal month pillar, forward/reverse direction, and adjacent solar-term distance.
- `Liu Nian`: the annual flowing pillar layered over the natal chart and current Luck Pillar.
- Flowing month/day/hour pillars for a selected reference datetime.
- Ten God / Five Factor role of each timing stem against the natal Day Master.
- Useful-element support or pressure by timing layer.
- Stem/branch relationship contacts between timing layers and natal pillars.
- 12 growth-stage / qi-state evidence for the Day Master against each timing branch.

Research basis used for this implementation:

- Local corpus: `BaZi - The Destiny Code` pages 85-99 for Luck Pillar direction, month-pillar sequencing, and age-limit calculation; `BaZi - The Destiny Code Revealed` for annual/Luck Pillar relationship contacts; `Ba Zi - The Four Pillars of Destiny` page 63 for 12 growth-stage table evidence.
- Local audit: `docs/iching_feature/CHINESE_ASTROLOGY_SOURCE_AUDIT_2026-05-11.md`, which states Hosoki/Six-Star is bibliographic only and not locally available as full text.
- Public cross-checks: [HKO 24 Solar Terms](https://www.hko.gov.hk/en/gts/time/24solarterms.htm), [USNO Equation of Time](https://aa.usno.navy.mil/faq/eqtime), [CosmicTao Luck Pillars](https://www.cosmictao.com/library/luck-pillars), [DeepOracle Liu Nian glossary](https://www.deeporacle.ai/en/bazi/glossary/liu-nian), and [Imperial Harvest 12 Stages of Growth](https://imperialharvest.com/blog/the-12-stages-of-growth/).

Implementation rule: the UI may describe this as "BaZi Timing Rhythm"; it must not label it as Hosoki, Six-Star, destiny-star, great-killing-world, or any branded fortune-cycle system.

## Current Status

Last updated: 2026-05-12 19:45 Asia/Jerusalem.

Finished or working:

- BaZi profile route exists at `POST /api/astro-clock/chinese-astrology/bazi`.
- Compatibility route exists at `POST /api/astro-clock/chinese-astrology/compatibility`.
- I Ching Oracle route exists at `POST /api/astro-clock/chinese-astrology/iching-oracle`.
- Chinese Astrology frontend has a usable multi-tab UI.
- I Ching Oracle is a real tab with coin casting, manual line entry, primary hexagram, changing lines, relating hexagram, and source evidence.
- Calculation Sex is global and is sent to profile and compatibility APIs.
- Luck Pillar sequence, direction, start age, current decade, and current year overlay are implemented.
- BaZi Timing Rhythm is implemented as a source-backed preview across current decade/year/month/day/hour layers.
- Flowing month/day/hour relationship contacts are now promoted into the shared Relationship Codes panel, while staying preview-only for outcome calibration.
- Strength, useful-element preview, climate candidates, damage checks, source notes, and validation summary are displayed.
- Final Yong Shen is explicitly gated with decision path, blockers, evidence, source IDs, and fixture gates.
- The UI no longer exposes raw `needs_validation` labels as user-facing status.
- Backend and UI tests cover released, blocked, and source-evidence behavior.

Current live source-runtime smoke:

- Backend is healthy on `http://127.0.0.1:52525` from source runtime.
- Frontend is running on `http://localhost:5173/index.html`.
- Browser smoke confirmed the Timing tab renders `BAZI TIMING RHYTHM`, flowing month/day/hour cards, rhythm source evidence, and the explicit "not Six-Star Divination" boundary.
- Browser smoke confirmed the Relationship Codes tab renders flowing month/day/hour timing groups and the source-basis sentence for those layers.
- Browser smoke screenshot: `chinese-astrology-bazi-timing-rhythm.png`.
- Browser smoke screenshot: `chinese-astrology-relationships-flowing-layers.png`.

Latest validation snapshot:

- `pytest backend/test_chinese_astrology_bazi.py`: 54 passed.
- `pytest frontend/backend/test_chinese_astrology_bazi.py`: 54 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 40 passed.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.

Implementation pass 1 completed on 2026-05-12:

- Workstream 1: added runtime Yong Shen family gates with positive/negative fixture counts, release blockers, released-family lists, and validation-summary output.
- Workstream 2: enabled final Yong Shen only for released narrow families (`strong_balancing`, `weak_support`) when confidence, presence, damage, special-structure, and fixture gates are clear.
- Workstream 3: made climate/regulating Useful God a first-class decision path with override-candidate metadata, while keeping final climate override blocked until its fixture gate is deliberately enabled.
- Workstream 4: upgraded special-structure screening into a structured classifier shape for dominant-element, follow-structure, transformation, and extreme-strength candidates.
- Workstream 5: kept damaged and timing-only candidates as final-release blockers, with fixture-gate evidence exposed in the Useful God payload.
- Workstream 6: added Luck Pillar/annual useful-element interaction payloads so timing can show whether it supplies, supports, drains into, or pressures useful candidates.
- Workstream 7: added compatibility calibration metadata and source evidence to pair scoring.
- Workstream 8: added frontend evidence panels for Useful God gates, timing interaction, and compatibility calibration.

Validation for this pass:

- `python -m pytest backend/test_chinese_astrology_bazi.py -q`: 42 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 36 passed.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.

Implementation pass 2 completed on 2026-05-12:

- At this historical pass, climate override was treated as a released Yong Shen family once its fixture gate passed.
- Added enough climate positive/negative fixtures to meet the release threshold.
- At this historical pass, climate could emit final `yong_shen.climate_override` when the regulating element was present, confidence was high enough, and no special-structure blocker was active.
- Climate stays withheld when the regulating element is absent.
- Special/follow/transformation review continues to block climate finalization.
- Notes UI now shows advanced rule-family release status instead of saying final Yong Shen is universally withheld.
- 2026-05-13 source-audit update: this release status is now superseded. Climate override remains visible as evidence, but final climate Yong Shen is blocked until a verified day-stem-by-month regulating table is implemented.

Validation for this pass:

- `python -m pytest backend/test_chinese_astrology_bazi.py -q`: 45 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 36 passed.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.

Implementation pass 3 completed on 2026-05-12:

- Phase 4: released narrow fixture-gated special-structure families for `dominant_element`, `follow_structure`, and `transformation_structure`.
- Phase 4: kept suspected special structures and extreme-strength labels as blockers instead of allowing ordinary final Yong Shen.
- Phase 5: released `damaged_alternate` so a damaged or absent primary candidate can reroute to a clear natal alternate when no special-structure blocker is active.
- Phase 5: added a visible but unreleased `timing_assisted` family; timing can supply evidence, but it still cannot independently finalize Yong Shen.
- Phase 5: expanded compatibility calibration fixtures for `general`, `romantic`, `family`, and `business` contexts and reports seeded calibration per context.
- Phase 6: added a Decision Evidence panel that summarizes strength, climate, presence, damage, special-structure, timing, and fixture-family evidence in the Useful tab.
- Packaging source drift was reconciled by syncing `backend/chinese_astrology/{interpretation,validation,relationships}.py` to `frontend/backend/chinese_astrology/`.
- Repaired NUL-byte corruption in source modules used by the profile path: `auxiliary_stars.py`, `palaces.py`, `strength.py`, and the packaged-backend mirror `tables.py`.

Validation for this pass:

- `python -m pytest backend/test_chinese_astrology_bazi.py -q`: 50 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 36 passed.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.

Implementation pass 4 completed on 2026-05-12:

- Phase 7: added `backend/chinese_astrology/oracle.py` as a standalone I Ching Oracle engine independent from BaZi/Yong Shen.
- Phase 7: added `POST /api/astro-clock/chinese-astrology/iching-oracle` in both root backend source and packaged-backend source mirror.
- Phase 7: implemented complete 64-hexagram King Wen structural resolution from upper/lower trigrams, manual six-line entry, three-coin casting, old-line changing logic, primary hexagram, changing lines, and relating hexagram.
- Phase 7: exposed source evidence in the API response, including the local Huang I Ching manifest/audit and public method/list references.
- Phase 7: replaced the disabled Oracle pill with a real frontend tab and result view.
- Phase 7: added V7 validation fixtures for all-yang Qian, all-yin Kun, changing-line resulting-hexagram logic, and coin-throw line values.
- Phase 7: added UI/API tests for the Oracle tab and endpoint contract.

Validation for this pass:

- `python -m pytest backend/test_chinese_astrology_bazi.py -q`: 53 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 38 passed.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.

Implementation pass 5 completed on 2026-05-12:

- Added `backend/chinese_astrology/timing_rhythm.py` as a pure BaZi timing-rhythm builder.
- Extended timing payloads with flowing month, flowing day, and flowing hour pillars for the selected reference datetime.
- Normalized active `Da Yun`, `Liu Nian`, flowing month, flowing day, and flowing hour into `timing.rhythm.layers[]`.
- Each rhythm layer now exposes pillar, Ten God, useful-element effects, relationship-code contacts, 12 growth-stage preview, tone, score, period metadata, source basis, source evidence, and explicit limits.
- Added curation anchors and validation fixtures for `timing_rhythm.current_layers_reference` and `timing_rhythm.growth_stage_day_master_branch`.
- Added a Timing tab `BaZi Timing Rhythm` panel with layer cards and rhythm source evidence.
- Kept timing-assisted final Yong Shen blocked; rhythm evidence is visible but cannot independently release a final Useful God.
- Mirrored backend source into `frontend/backend/chinese_astrology/` for packaging.

Validation for this pass:

- `python -m pytest backend/test_chinese_astrology_bazi.py`: 54 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 39 passed.
- `npm --prefix frontend run build`: passed with the existing large chunk warning.

Implementation pass 6 completed on 2026-05-12:

- Spawned a research agent to verify local source anchors for BaZi timing rhythm calibration.
- Research confirmed strong local support for Da Yun / Luck Pillars, annual cycles, timing relationship contacts, and 12 growth stages.
- Research found only partial local support for flowing month/day/hour interpretation: computed timing and qi-state evidence is supported, but outcome-calibrated worked examples are not yet sufficient.
- Promoted flowing month, flowing day, and flowing hour contacts into `relationships.events` and `relationships.summary` so the Relationship Codes panel now separates natal, luck, year, month, day, and hour timing layers.
- Added per-layer rhythm provenance fields: `calculation_basis`, `evidence_role`, `source_strength`, and `release_gate`.
- Added growth-stage page references and relationship-event source anchors to the rhythm payload.
- Added rhythm calibration metadata that explicitly keeps timing-assisted finalization blocked.
- Added validation fixtures for flowing-month contacts and flowing day/hour contacts.
- Updated the Timing UI to show source strength and rhythm calibration status.
- Updated the Relationship Codes UI to show flowing month/day/hour groups and counts.
- Mirrored backend source into `frontend/backend/chinese_astrology/` for packaging.

Validation for this pass:

- `python -m py_compile backend/chinese_astrology/timing_rhythm.py backend/chinese_astrology/relationships.py backend/chinese_astrology/validation.py frontend/backend/chinese_astrology/timing_rhythm.py frontend/backend/chinese_astrology/relationships.py frontend/backend/chinese_astrology/validation.py`: passed.
- `pytest backend/test_chinese_astrology_bazi.py`: 54 passed.
- `pytest frontend/backend/test_chinese_astrology_bazi.py`: 54 passed.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`: 40 passed.

Current released rule families:

- `strong_balancing`: can emit final Yong Shen when a strong Day Master has a usable balancing candidate, confidence is high enough, and no damage/special/timing-only blocker is active.
- `weak_support`: can emit final Yong Shen when a weak Day Master has a usable support candidate, confidence is high enough, and no damage/special/timing-only blocker is active.
- `climate_override`: can emit final Yong Shen when a Lu Zhiji source-table regulating stem is selected, its element is present or timing-supported, and no pressure/special-structure blocker is active.

Current evidence-only blocked families:

- `dominant_element`: blocked until strict special-structure confirmation rules are curated.
- `follow_structure`: blocked until strict follow-structure success/failure rules are curated.
- `transformation_structure`: blocked until transformation success, failure, and return-to-root rules are curated.
- `damaged_alternate`: blocked until useful-god damage is tied to source-backed `损用` / `破格` patterns.

Current evidence surfaces:

- Useful God payloads include rule family, decision path, fixture gate, source IDs, fixture IDs, blockers, and source evidence.
- Luck Pillar timing now reports useful-element interaction for active decade/year layers.
- BaZi Timing Rhythm now reports decade/year/month/day/hour timing layers with Ten God, useful-element, relationship-code, and growth-stage evidence.
- Relationship Codes now surfaces flowing month/day/hour contacts as explicit timing evidence.
- Compatibility scoring now reports context-specific seeded calibration status and source evidence.
- Notes UI now reports advanced family release status.
- Useful tab now includes a Decision Evidence summary for strength, climate, presence, damage, special-structure, timing, and fixture-family state.
- Oracle tab now includes source-backed casting controls, primary/relating hexagram cards, changing-line focus, line stack visuals, and source evidence.

Still missing or intentionally blocked:

- Extreme-strength exceptions still block ordinary finalization; they are screened but not released as final structure families.
- Timing-assisted Useful God is not released; timing can inform evidence but cannot independently finalize.
- BaZi Timing Rhythm is a source-backed preview; monthly/day/hour computed contacts are visible, but outcome interpretation and growth-stage scoring need more curated worked examples before becoming calibrated.
- Compatibility scoring has context-seeded calibration metadata, but still needs a larger source-backed qualitative pair set before score bands should be considered outcome-calibrated.
- Some calendar/source cases still need stronger external/source anchors, especially Li Chun/Jie boundary examples and true-solar day-boundary doctrine examples.
- I Ching yarrow-stalk probability casting is implemented as a fixture-backed probability model. The Oracle now supports manual lines, three-coin casting, yarrow-model casting, primary/relating hexagrams, nuclear hexagram structure, and a named Zhu Xi changing-line focus policy.

## Source And Implementation Ground Rules

Do not edit packaged artifacts. All implementation work must land in source paths only:

- Backend source: `backend/**`
- Packaged backend source mirror: `frontend/backend/**`
- Frontend source: `frontend/src/**`
- Documentation: `docs/**`

Do not edit:

- `frontend/dist-electron/**`
- `frontend/backend/build/**`
- `frontend/dist/**`
- `website/**`
- any `win-unpacked/**`, `resources/**`, `venv/**`, or `node_modules/**`

For backend changes, keep `backend/chinese_astrology/**` and `frontend/backend/chinese_astrology/**` in sync. Packaging should continue to consume source through `package-app-new.bat` and `frontend/scripts/prepare-backend.js`.

## Implementation Map

Core API entry points:

- `backend/astro_clock_api.py`
  - `_chinese_astrology_birth_context(payload)`
  - `chinese_astrology_bazi()`
  - `chinese_astrology_compatibility()`
  - `chinese_astrology_iching_oracle()`
- `frontend/src/features/astroclock/api.mjs`
  - `getChineseAstrologyBazi()`
  - `getChineseAstrologyCompatibility()`
  - `getChineseAstrologyIChingOracle()`

Backend calculation surfaces:

- `backend/chinese_astrology/bazi.py`
  - profile assembly
  - true solar and day-boundary handling
  - Luck Pillar direction/start-age/timeline
- `backend/chinese_astrology/timing_rhythm.py`
  - Da Yun / Liu Nian / flowing month-day-hour layer normalization
  - Ten God timing roles
  - useful-element timing support/pressure
  - relationship-code contacts by timing layer
  - 12 growth-stage preview
- `backend/chinese_astrology/interpretation.py`
  - `build_useful_element_recommendations`
  - `_decide_yong_shen`
  - `_climate_adjustment`
  - `_damage_assessment`
  - `_special_structure_screen`
- `backend/chinese_astrology/relationships.py`
  - `analyze_pair_relationships`
  - `_pair_scoring`
- `backend/chinese_astrology/oracle.py`
  - `cast_iching_oracle`
  - King Wen hexagram resolution
  - manual and three-coin line casting
  - primary/changing/relating hexagram output
  - source evidence payload
- `backend/chinese_astrology/curation.py`
  - source anchors
  - rule notes
  - curation backlog
- `backend/chinese_astrology/validation.py`
  - fixture ledger
  - phase gates
  - source-reference status

Frontend surfaces:

- `frontend/src/features/astroclock/ChineseAstrologyPage.jsx`
  - Useful tab
  - Timing tab
  - Oracle tab
  - Compatibility panel
  - Notes/source panel
- `frontend/src/tests/chineseAstrologyPage.test.jsx`
- `frontend/src/tests/astroclockApi.test.mjs`

## Release Principle

Every advanced ruling must pass this order:

1. Source anchor exists.
2. Positive fixtures prove when the rule applies.
3. Negative fixtures prove when the rule must not apply.
4. Backend emits a structured decision, blockers, and evidence.
5. Frontend shows the ruling and why it was made.
6. Tests cover route payload, backend decision, frontend rendering, and no-regression withheld cases.
7. Packaged build smoke confirms source-only changes made it into the desktop app.

No advanced feature should graduate because it "looks right" in one chart.

## Data Contracts To Add Or Tighten

### Useful God Decision

Extend `useful_elements.useful_god` into a stable evidence object:

```json
{
  "final_status": "withheld | candidate_preview | final",
  "rule_family": "strong_balancing | weak_support | climate_override | dominant_element | follow_structure | transformation_structure | damaged_alternate | timing_assisted | extreme_strength",
  "decision_path": "yong_shen.strong_balancing",
  "element": "Wood | Fire | Earth | Metal | Water | null",
  "role": "Wealth | Output | Influence | Resource | Companion | regulating | null",
  "confidence": "low | medium | high",
  "blocking_reasons": [],
  "source_ids": [],
  "fixture_ids": [],
  "evidence": {
    "strength": {},
    "climate": {},
    "presence": {},
    "damage": {},
    "special_structure": {},
    "timing": {}
  }
}
```

Backward compatibility requirement: keep existing fields currently consumed by the UI.

### Source Evidence

Add a normalized evidence list to advanced payloads:

```json
{
  "source_id": "anchor.useful_elements.climate_damage",
  "rule_id": "useful_elements.climate_override",
  "claim": "Summer month charts may require regulating Water before ordinary balancing.",
  "reference": "local corpus path or external source id",
  "strength": "primary | cross_check | fixture_only",
  "fixture_ids": []
}
```

The UI should show source evidence in a details drawer or expandable evidence panel, not only as opaque source IDs.

### Fixture Format

Each advanced fixture should include:

```json
{
  "id": "yong_shen.strong_balancing.positive.001",
  "area": "useful_elements",
  "family": "strong_balancing",
  "polarity": "positive | negative",
  "birth_context": {},
  "expected": {},
  "source_anchor": "anchor.useful_elements.climate_damage",
  "source_reference_status": "anchored",
  "notes": "Why this chart should or should not graduate."
}
```

Minimum release gate for a narrow family:

- 2 independent source anchors where available, or 1 primary source anchor plus 1 modern cross-check.
- 3 positive fixtures.
- 3 negative fixtures.
- At least 1 fixture proving the family stays withheld when a blocker appears.

Preferred mature gate:

- 5 positive fixtures.
- 5 negative fixtures.
- 1 calendar-sensitive case when birth date is close to a solar term.
- 1 timing-sensitive case when Luck Pillar or annual pillar changes interpretation.

## Workstream 1: Source And Fixture Graduation

Goal: turn placeholder validation families into real release gates.

Implementation steps:

1. Audit local corpus references under `output/iching_private_corpus*`.
2. Add or repair source anchors in `backend/chinese_astrology/curation.py` and the frontend/backend mirror.
3. Replace placeholder statuses in `backend/chinese_astrology/validation.py`.
4. Add positive/negative fixture IDs for each advanced rule family.
5. Add backend tests that fail if a family is marked final without enough fixtures.
6. Keep unresolved families visible as withheld with clear blocker reasons.

Initial fixture families:

| Family | Positive fixtures | Negative fixtures | First release status |
| --- | ---: | ---: | --- |
| strong_balancing | 3 minimum | 3 minimum | released |
| weak_support | 3 minimum | 3 minimum | released |
| climate_override | 3 minimum | 3 minimum | released for source-table regulating rows |
| dominant_element | 3 minimum | 3 minimum | fixture-seeded but release disabled |
| follow_structure | 3 minimum | 3 minimum | fixture-seeded but release disabled |
| transformation_structure | 3 minimum | 3 minimum | fixture-seeded but release disabled |
| damaged_alternate | 3 minimum | 3 minimum | fixture-seeded but release disabled |
| timing_assisted | 3 minimum | 3 minimum | fixture-seeded but release disabled |
| extreme_strength | 3 minimum | 3 minimum | not released |
| compatibility_calibration | context seeds present | broader corpus pending | scoring calibration only |

Acceptance gates:

- `validation_summary()` reports no placeholder status for a released family.
- Every released family has both positive and negative fixtures.
- Backend tests assert final status only for released families.
- Existing balanced/uncertain charts remain withheld.

## Workstream 2: Final Yong Shen Narrow Graduation

Goal: release final Useful God only for narrow, validated strong/weak families.

Implementation steps:

1. Refactor `_decide_yong_shen` in `backend/chinese_astrology/interpretation.py` into explicit family evaluators:
   - `_evaluate_strong_balancing_yong_shen`
   - `_evaluate_weak_support_yong_shen`
   - `_evaluate_climate_override_yong_shen`
   - `_evaluate_special_structure_yong_shen`
   - `_evaluate_damage_gate`
2. Add a fixture-gate helper that checks whether a rule family is allowed to emit `final`.
3. Promote only these first:
   - strong Day Master with decisive strength, clear non-damaged candidate, no special-structure flag, and fixture-backed role priority.
   - weak Day Master with decisive weakness, clear Resource/Companion support, no special-structure flag, and fixture-backed role priority.
4. Preserve `candidate_preview` for charts that pass current logic but fail final fixture gates.
5. Preserve `withheld` for balanced, uncertain, damaged, missing, or structurally exceptional charts.

Tests:

- strong chart final fixture returns `final`.
- weak chart final fixture returns `final`.
- balanced chart remains `withheld`.
- damaged candidate remains `withheld` or `candidate_preview` with blocker.
- special-structure flag prevents ordinary final promotion.
- source IDs and fixture IDs are present for every final result.

Acceptance gate:

- The frontend may display "Final Yong Shen" only when `final_status === "final"` and `fixture_ids.length > 0`.

## Workstream 3: Climate Override As First-Class Logic

Goal: climate/regulating Useful God becomes a decision path, not just a preview panel.

2026-05-13 implementation update: first release completed. The engine now uses Lu Zhiji's Jia day-stem month table, the Yi/Wei example, and the ten-day-stem configuration summary. Season-only climate rows remain preview-only and cannot finalize.

Implementation steps:

1. Extend `_climate_adjustment` to return:
   - candidate regulating element
   - source regulating stem
   - override priority
   - source IDs
   - source page references
   - blockers
2. Add `_evaluate_climate_override_yong_shen`.
3. Define precedence rules:
   - climate can override strength balancing only when a source-table regulating stem is selected and the regulating element is usable.
   - climate cannot override if the regulating element is absent, pressured, or unsupported.
   - climate cannot override special/follow/transformation structures until those classifiers are released.
4. Add climate positive/negative fixtures:
   - summer heat requiring Water.
   - winter cold requiring Fire.
   - cases where ordinary balancing should still win.
   - cases where regulating element is damaged or absent.

Tests:

- climate override final when source and fixtures approve.
- climate candidate remains preview when override gate fails.
- frontend shows "Climate override" as the decision path with evidence.

## Workstream 4: Special, Follow, Transformation, And Extreme Structures

Goal: replace warning-only screening with classified structure gates.

Implementation steps:

1. Replace or extend `_special_structure_screen` into a classifier that returns:
   - `structure_status`: `none | suspected | classified | excluded`
   - `structure_type`: `follow | transformation | dominant_element | extreme_strength | ordinary`
   - confidence
   - evidence
   - source IDs
   - blockers
2. Implement source-gated classifiers:
   - follow strength: very weak Day Master with overwhelming other-element support and no meaningful root.
   - transformation: recognized stem combinations with seasonal and branch support.
   - dominant element: one element overwhelms seasonal/root/branch support.
   - extreme strength: Day Master/root support exceeds ordinary balancing thresholds.
3. Feed classifier result into `_decide_yong_shen`.
4. Withhold ordinary final Yong Shen whenever structure is suspected but not classified.
5. Release special-structure final logic only after fixtures prove it.

Tests:

- ordinary charts do not get false special flags.
- suspected special charts block ordinary final Yong Shen.
- classified follow/transformation fixtures emit structure details.
- frontend shows the structure classification and evidence.

## Workstream 5: Damaged Useful-Element Finalization

Goal: keep damage as a blocker now, then support fixture-backed alternate rulings later.

Implementation steps:

1. Tighten `_damage_assessment` and `_damage_status` output:
   - present and usable
   - absent
   - damaged by clash/punishment/harm/destruction
   - supported by combination/root
   - supplied by timing only
2. Add fixtures where the ordinary candidate is damaged and the final result must remain withheld.
3. Add fixtures where an alternate candidate is source-backed after the primary is damaged.
4. Do not allow timing-only supply to produce final Yong Shen until timing fixtures are mature.

Tests:

- damaged primary candidate blocks final status.
- alternate candidate can be previewed only when fixture-backed.
- frontend shows the blocker and does not call it final.

## Workstream 6: Luck Pillar Useful-Element Interaction

Goal: expand timing beyond sequence into useful-element interaction.

Implementation steps:

1. Add a timing interaction payload, probably in `bazi.py` or `interpretation.py`:
   - active Luck Pillar stem/branch element effects
   - annual pillar element effects
   - whether timing supplies, damages, strengthens, or pressures the useful candidate
   - decade/annual interaction summary
2. Keep timing as an influence layer, not a final Yong Shen source in the first release.
3. Add UI rows in the Timing tab:
   - useful element supplied by decade
   - useful element pressured by decade
   - annual activation
   - timing-only warning when not natal.
4. Add backend tests for timing interaction.
5. Add frontend tests for Timing tab rendering.

Acceptance gate:

- Timing may modify confidence and evidence, but must not independently release a final Useful God until a separate timing-assisted fixture family is graduated.

## Workstream 7: Compatibility Calibration

Goal: make compatibility scores more source-backed and less arbitrary.

Implementation steps:

1. Keep the current compatibility model as a preview/calibration layer.
2. Add relationship-example fixtures:
   - supportive pair.
   - high attraction/high conflict pair.
   - spouse-palace pressure pair.
   - useful-element supply pair.
   - timing pressure pair.
3. Calibrate `_pair_scoring` in `backend/chinese_astrology/relationships.py` by context:
   - romantic
   - business
   - family
   - friendship
4. Record source evidence per scoring component.
5. Add score-band tests rather than exact fragile score tests where appropriate.

Acceptance gate:

- Compatibility UI shows component evidence and calibration status.
- The score remains labeled calibrated only for fixture-backed relationship contexts.

## Workstream 8: Source Evidence UI

Goal: users can see why a ruling was made.

Implementation steps:

1. Add an evidence details component in `ChineseAstrologyPage.jsx`.
2. Show:
   - decision path
   - source rule IDs
   - fixture IDs
   - blockers
   - strength evidence
   - climate evidence
   - damage evidence
   - special-structure evidence
   - timing evidence
3. Keep labels user-facing:
   - "Final"
   - "Preview"
   - "Withheld"
   - "Blocked by damaged candidate"
   - "Blocked by special-structure review"
4. Do not show raw backend labels like `needs_validation`.

Tests:

- final result displays evidence.
- withheld result displays blockers.
- source IDs are human-readable or expandable.
- no raw validation jargon leaks into the main UI.

## Workstream 9: I Ching Oracle

Goal: ship the Oracle as a standalone source-backed module, not a disabled promise.

Status: implemented for manual lines and three-coin casting.

Source basis:

- `docs/iching_feature/source_manifest.yml`: `local.iching_huang` local source anchor for I Ching casting terminology and reading structure.
- `docs/iching_feature/CHINESE_ASTROLOGY_SOURCE_AUDIT_2026-05-11.md`: product decision to keep I Ching as a standalone Oracle, store six lines bottom-to-top, and derive primary/changing/resulting hexagrams.
- `public.iching_divination_method`: public method anchor for 6/7/8/9 old/young yin/yang line values and old-line changes.
- `public.king_wen_hexagram_list`: public cross-check for King Wen hexagram numbers, English titles, and trigram identities.

Backend implementation:

1. Added `backend/chinese_astrology/oracle.py` and mirrored it to `frontend/backend/chinese_astrology/oracle.py`.
2. Add route:
   - implemented: `POST /api/astro-clock/chinese-astrology/iching-oracle`
3. Support casting methods:
   - implemented: three coins
   - implemented: manual line input
   - implemented: yarrow-style generated probability model
4. Return:
   - implemented: primary hexagram
   - implemented: changing lines
   - implemented: relating hexagram
   - implemented: nuclear hexagram
   - implemented: named changing-line reading policy
   - implemented: original concise guidance and line-focus notes
   - implemented: source evidence
   - not implemented: optional BaZi context link, intentionally kept separate.

Frontend implementation:

1. Replaced disabled `I Ching Oracle` pill with a real Oracle tab.
2. Added casting controls, result view, source evidence, and JSON export.
3. Kept the Oracle independent from final Yong Shen logic.

Alternative path:

No longer needed. The surface is functional.

Acceptance gate:

- Disabled surface is not shipped as a dead promise. Completed: the surface is functional.

## Phase Order

### Phase 0: Evidence Lock

- Status: completed for the currently released runtime families.
- Local source anchors and fixture metadata are now present for strong balancing, weak support, climate override, dominant element, follow structure, transformation structure, and damaged alternate.
- Historical corrupted docs remain outside the runtime path; this plan supersedes stale status wording.
- Remaining evidence work is focused on extreme-strength exceptions, timing-assisted finalization, broader qualitative compatibility calibration, and calendar/source edge cases.

### Phase 1: Fixture Gate Infrastructure

- Status: completed.
- Runtime helpers determine whether a Yong Shen family can emit `final`.
- Validation summary reports released and blocked advanced rule families.
- Tests prove released families can finalize and blocked paths stay withheld.

### Phase 2: Strong/Weak Final Yong Shen Slice

- Status: completed.
- `strong_balancing` and `weak_support` are released behind fixture, confidence, damage, timing-only, and special-structure gates.
- UI final/candidate/withheld status is driven by backend `final_status` and fixture-gate evidence.

### Phase 3: Climate Override

- Status: first final release completed after the 2026-05-13 Chinese-source audit.
- `climate_override` is released behind source-row, fixture, confidence, presence, pressure, and special-structure gates.
- Climate can override ordinary balancing only through Lu Zhiji source rows: Jia month table p. 240, Yi/Wei example p. 250, or ten-day-stem configuration summary pp. 251-255.
- Absent climate regulators and special-structure cases remain withheld.

### Phase 4: Special Structures

- Status: evidence layer completed; final release disabled after the 2026-05-13 Chinese-source audit.
- Dominant, follow, and transformation screens remain warning/evidence layers until strict success/failure criteria are curated.
- Dominant-element, follow-structure, and transformation candidates now have structured classifier output and fixture-gated final decision paths.
- Suspected structures still block ordinary final Yong Shen.
- Extreme-strength candidates remain screening flags until a separate fixture family is mature enough to release.

### Phase 5: Timing And Compatibility

- Status: evidence layer completed for damaged alternate rerouting and context calibration seeds; timing-assisted finalization remains blocked.
- Luck Pillar useful-element interaction payload exists and is used as evidence.
- `damaged_alternate` remains visible when a damaged or absent primary candidate can reroute to a clear natal alternate, but final release is disabled after the 2026-05-13 Chinese-source audit.
- Compatibility calibration metadata and source evidence exist for general, romantic, family, and business contexts.
- Remaining work: timing-assisted final Useful God remains blocked, and compatibility scoring needs a broader qualitative calibration set before score bands are outcome-calibrated.

### Phase 6: Evidence UI

- Status: completed for summary-level evidence.
- Useful, Timing, Compatibility, and Notes tabs expose source/fixture evidence and family-gate state.
- Useful tab now shows Decision Evidence across strength, climate, presence, damage, special-structure, timing, and fixture-family state.
- Remaining optional work: convert this into a deeper drawer/details view if the UI needs more drill-down.

### Phase 7: I Ching Oracle Decision

- Status: completed for source-backed manual, three-coin, and yarrow-probability casting.
- Standalone Oracle route and UI exist.
- Disabled surface has been removed.
- Backend returns source evidence, line order, primary hexagram, changing lines, relating hexagram, nuclear hexagram, named reading policy, and original concise guidance.
- Yarrow-stalk probability casting is now fixture-backed; future optional work is full hand-step yarrow simulation if the UI needs to teach each stalk operation.

## Test And Validation Commands

Backend:

```powershell
python -m pytest backend/test_chinese_astrology_bazi.py
```

Frontend focused tests:

```powershell
npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs
```

Frontend build:

```powershell
npm --prefix frontend run build
```

Desktop/package smoke:

```powershell
package-app-new.bat
```

Live backend smoke after starting the app:

```powershell
Invoke-WebRequest http://127.0.0.1:52525/api/health
```

## Definition Of Done

The advanced work is complete when:

- Final Yong Shen appears only for released fixture-backed rule families. Current released families: `strong_balancing`, `weak_support`, and source-table `climate_override`.
- 2026-05-13 update: special-structure, damaged-alternate, timing-assisted, and extreme-strength families remain evidence-only.
- Climate/regulating Useful God can override balancing only through a tested source-table path. Remaining work is the full ten-stem by twelve-month regulating table.
- Special/follow/transformation structures are classified, not only warned. Pending strict source-backed success/failure criteria.
- Damaged useful-element cases can block or reroute final logic based on curated examples. Pending source-backed damage pattern classifier.
- Luck Pillars and BaZi Timing Rhythm explain decade/year/month/day/hour interaction with useful elements and relationship codes. Interaction payload and UI exist; timing-assisted finalization is still blocked.
- Compatibility scoring exposes source-backed component evidence and calibrated status. Context calibration seeds exist; broader qualitative calibration is still needed.
- The frontend shows why a ruling was made with source and fixture evidence. Summary evidence panel exists; a deeper drawer/details UI remains optional.
- I Ching Oracle is implemented as a working source-backed module for manual lines and three-coin casting.
- Backend tests, frontend tests, frontend build, and packaged smoke pass from source files.

## Recommended Next Implementation Slice

Start with calibration and packaging hardening now that the BaZi rhythm surface exists:

1. Add an `extreme_strength` fixture family only after source examples distinguish true extremes from ordinary strong/weak charts.
2. Expand BaZi Timing Rhythm fixtures with sourced monthly/day/hour examples and keep timing-assisted finalization blocked until timing examples show when support can graduate from evidence to final ruling.
3. Expand compatibility from context seeds into a qualitative corpus with positive, friction, mixed, and timing-pressure examples per context.
4. Optional: add full hand-step yarrow simulation only if the product needs an educational stalk-by-stalk workflow beyond the current yarrow probability model.
5. Add packaged desktop smoke coverage after the next source build to verify the mirrored backend matches the root backend behavior.

This is now the highest-value slice because the main false-finalization risk has moved from ordinary strong/weak/climate/special/damaged paths into extreme structures, timing-only support, monthly/day/hour rhythm interpretation, yarrow-method probability fidelity, and score-band overconfidence.
