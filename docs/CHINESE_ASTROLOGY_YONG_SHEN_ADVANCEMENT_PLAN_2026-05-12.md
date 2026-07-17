# Chinese Astrology Yong Shen Advancement Plan

Date: 2026-05-12

## Purpose

Advance the Chinese Astrology `Useful God / Yong Shen` feature from a conservative withheld/provisional state to a source-backed final recommendation path.

The current implementation is intentionally conservative. It can show favorable-element previews, climate/regulating candidates, damage checks, and special-structure warnings, but it does not name a final Yong Shen. This document records why, what source work is still needed, and how to implement the next logic slices safely.

## Current State

Primary implementation files:

- `backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `backend/chinese_astrology/curation.py`
- `frontend/backend/chinese_astrology/curation.py`
- `backend/chinese_astrology/validation.py`
- `frontend/backend/chinese_astrology/validation.py`
- `backend/test_chinese_astrology_bazi.py`
- `frontend/src/features/astroclock/ChineseAstrologyPage.jsx`
- `frontend/src/tests/chineseAstrologyPage.test.jsx`

Current behavior:

- Strong Day Master charts produce provisional favorable elements:
  - primary: Wealth
  - secondary: Output
  - conditional: Influence
- Weak Day Master charts produce provisional favorable elements:
  - primary: Resource
  - secondary: Companion
- Balanced or uncertain charts return `useful_elements.status = "withheld"`.
- All final Yong Shen results currently return `useful_god.final_status = "withheld"`.
- A candidate can be displayed as `candidate_preview` only when the useful-element payload is provisional, a primary candidate exists, confidence is medium/high, and the candidate is not absent or damaged.
- The frontend should treat this as a conservative engine boundary, not a UI bug.

Existing useful-element layers:

- Strength balance: `season_root_formation_v2`
- Element presence: natal/timing availability checks
- Damage assessment: pressured, absent, timing-assisted, supported, available
- Climate/regulating preview: seasonal regulating element candidates
- Special-structure screen: dominant-element and extreme-strength warnings
- Validation fixture ledger: V3 covers strength, useful elements, and special structures

## Why Final Yong Shen Is Withheld

The current engine does not yet have enough curated, source-backed cases to promote a candidate from "favorable element preview" to "final Yong Shen".

Final Yong Shen needs more than a strong/weak Day Master label. The implementation still needs reliable rule coverage for:

- balanced charts where no simple support/pressure path dominates
- strong charts where Wealth/Output/Influence priority changes by season, roots, and pressure
- weak charts where Resource/Companion priority changes by season, roots, and pressure
- climate-first charts where regulating element overrides simple strength balancing
- missing or damaged useful elements
- useful elements supplied only by luck pillar or annual timing
- special structures, follow structures, transformation patterns, and dominant-element charts
- cases where the useful element is present but unusable because of clash, punishment, combination, or palace pressure

The current source anchors are enough to justify provisional guidance, but not enough to guarantee final-candidate promotion.

## Advancement Principle

Do not jump directly from withheld to final for every chart.

Use three explicit levels:

- `withheld`: the chart is balanced/uncertain, structurally exceptional, or lacks usable evidence.
- `candidate_preview`: a likely useful element passes the current strength and damage checks, but final logic is not fully calibrated.
- `final`: the chart matches a source-backed fixture family and passes all release gates for that family.

The goal is to make final Yong Shen possible for narrow, validated families first, then expand coverage.

## Data Contract

Extend `useful_elements.useful_god` without breaking existing clients.

Recommended payload shape:

```json
{
  "final_status": "withheld | candidate_preview | final",
  "candidate_status": "withheld | candidate_preview | final",
  "element": "Wood | Fire | Earth | Metal | Water | null",
  "role": "Wealth | Output | Influence | Resource | Companion | regulating | null",
  "decision_path": "balanced_withheld | strong_balancing | weak_support | climate_override | special_structure_withheld",
  "confidence": "low | medium | high",
  "reason": "Human-readable summary",
  "blocking_reasons": [],
  "evidence": {
    "strength": {},
    "climate": {},
    "presence": {},
    "damage": {},
    "special_structure": {}
  },
  "source_ids": [],
  "fixture_ids": []
}
```

Keep existing fields during migration:

- `final_status`
- `candidate_status`
- `element`
- `role`
- `confidence`
- `reason`
- `source_confidence`

## Source Work Required

Add curated examples before implementing final status.

Minimum source/fixture set for the first release slice:

- 4 strong Day Master examples:
  - Wealth selected as primary
  - Output selected as primary
  - Influence selected conditionally
  - strong chart withheld because useful element is damaged or absent
- 4 weak Day Master examples:
  - Resource selected as primary
  - Companion selected as primary
  - weak chart withheld because support is absent or damaged
  - weak chart withheld because special structure is suspected
- 4 climate/regulating examples:
  - Winter chart where Fire regulates
  - Summer chart where Water regulates
  - Spring chart where Metal regulates/prunes
  - Autumn chart where Fire warms/refines
- 4 exception examples:
  - balanced chart withheld
  - dominant-element follow/special candidate withheld
  - useful element timing-assisted only
  - useful element present but damaged by relationship code

Each fixture should include:

- source id
- page or anchor reference
- chart input
- expected strength label
- expected useful-god status
- expected element or withheld reason
- expected decision path
- expected confidence
- reason text or rule note

## Implementation Plan

### Phase 1: Formalize Rule Families

Files:

- `backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `backend/chinese_astrology/curation.py`
- `frontend/backend/chinese_astrology/curation.py`
- `backend/chinese_astrology/validation.py`
- `frontend/backend/chinese_astrology/validation.py`

Work:

- Add explicit rule family ids:
  - `yong_shen.strong_balancing`
  - `yong_shen.weak_support`
  - `yong_shen.climate_override`
  - `yong_shen.damage_withheld`
  - `yong_shen.special_structure_withheld`
  - `yong_shen.balanced_withheld`
- Add source anchors for each rule family.
- Add fixture placeholders for each family in V3.
- Keep final status withheld.

Acceptance:

- Fixture ledger exposes every rule family.
- Existing tests still pass.
- Frontend Notes can show "final withheld" as a rule-family boundary, not vague uncertainty.

### Phase 2: Extract Decision Function

Files:

- `backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `backend/test_chinese_astrology_bazi.py`

Work:

- Replace the current inline `_useful_god_candidate` gate with a dedicated decision function:
  - `_decide_yong_shen(payload, damage_rows, analysis, counts)`
- Return a structured decision payload with:
  - decision path
  - blockers
  - evidence
  - source ids
  - fixture ids
- Keep `final_status = "withheld"` for all families until source fixtures graduate.

Acceptance:

- Tests assert decision path and blocking reasons.
- Existing frontend remains compatible.

### Phase 3: Graduate Narrow Final Cases

Files:

- `backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `backend/chinese_astrology/validation.py`
- `frontend/backend/chinese_astrology/validation.py`
- `backend/test_chinese_astrology_bazi.py`

Work:

- Allow `final_status = "final"` only when all conditions are true:
  - rule family has curated source fixtures
  - strength confidence is medium/high
  - score gap is above threshold
  - no special-structure flag blocks finalization
  - selected element is present, supported, or clearly timing-assisted
  - selected element is not damaged
  - fixture id matches the decision path
- Start with one narrow family:
  - strong Day Master, Wealth primary, useful element present and undamaged
  - or weak Day Master, Resource primary, useful element present and undamaged

Acceptance:

- At least one positive final fixture passes.
- At least one negative fixture per blocker still withholds.
- No broad charts are accidentally promoted.

### Phase 4: Add Climate Override Logic

Files:

- `backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `backend/test_chinese_astrology_bazi.py`

Work:

- Promote climate/regulating element from preview to decision input.
- Add rules for when climate candidate outranks strength-balancing candidate.
- Require source fixture match before finalizing.
- Keep climate finalization blocked when regulating element is absent/damaged unless timing support is explicitly accepted by fixture.

Acceptance:

- Seasonal climate fixtures pass.
- Balanced charts can still withhold.
- The payload explains when climate overrides strength balancing.

### Phase 5: Special Structure And Follow-Structure Handling

Files:

- `backend/chinese_astrology/interpretation.py`
- `frontend/backend/chinese_astrology/interpretation.py`
- `backend/chinese_astrology/validation.py`
- `frontend/backend/chinese_astrology/validation.py`

Work:

- Replace `special_structure_screen` warning-only behavior with classified gates:
  - no special structure
  - possible dominant/follow structure, withhold
  - confirmed special structure, separate rule family
- Do not finalize a standard Yong Shen when special-structure confidence is unresolved.

Acceptance:

- Dominant-element charts do not use standard strong/weak finalization.
- Confirmed special-structure fixtures have separate expected outcomes.

### Phase 6: Frontend Presentation

Files:

- `frontend/src/features/astroclock/ChineseAstrologyPage.jsx`
- `frontend/src/tests/chineseAstrologyPage.test.jsx`

Work:

- Show three clear states:
  - final Yong Shen
  - candidate preview
  - withheld with blockers
- Surface `decision_path`, `blocking_reasons`, and source/fixture ids in Details.
- Keep raw `needs_validation` hidden from user-facing chips.
- Avoid implying finality for provisional candidates.

Acceptance:

- User can see why a chart is final, preview-only, or withheld.
- Tests cover all three UI states.

## Test Plan

Backend:

- `python -m pytest backend/test_chinese_astrology_bazi.py`
- Add direct unit tests for `_decide_yong_shen`.
- Add profile fixture tests for every new V3 fixture.
- Add regression tests that balanced/uncertain and special-structure charts remain withheld.

Frontend:

- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs`
- Add UI tests for:
  - final state
  - preview state
  - withheld state with blockers
  - Details source/fixture display

Build:

- `npm --prefix frontend run build`

Live validation:

- Start Electron desktop dev mode:
  - `start-electron-dev.bat`
- Confirm the Useful tab shows the correct status for each test snap.
- Confirm Notes and Details explain the decision without exposing raw backend audit labels.

## Release Gates

Do not ship final Yong Shen until:

- every final-returning rule family has source anchors and profile fixtures
- every blocker family has at least one negative fixture
- source confidence no longer includes hidden validation-only tags for final outcomes
- all backend, frontend, and build checks pass
- live desktop smoke verifies Useful, Notes, and Details rendering

## First Implementation Slice

Recommended first slice:

1. Add rule family ids and fixture placeholders.
2. Extract `_decide_yong_shen`.
3. Keep all final statuses withheld.
4. Add structured blockers and decision paths.
5. Update frontend to display decision path and blockers.
6. Add tests for current withheld behavior.

This slice improves transparency without risking false final recommendations.

Recommended second slice:

1. Curate one strong Day Master final fixture family.
2. Curate one weak Day Master final fixture family.
3. Promote only those exact families to `final`.
4. Keep climate and special structures withheld.

This makes the feature visibly advance while keeping the logic defensible.
