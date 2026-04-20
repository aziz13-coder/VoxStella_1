# Horary Generic Gate Phase 3/4 Audit

Date:
2026-03-23

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related inputs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_AUDIT.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_PHASE_2_CORPUS.md`

## Scope

This document completes:

- Phase 3: audit the exact live generic branch
- Phase 4: define which non-route testimonies should become verdict-level factors

No runtime logic is changed in this phase.

## Current No-Route Control Flow

The live no-route branch in `backend/horary_engine/engine.py` currently behaves like this:

1. special doctrines get first chance to return early
   - relationship affection
   - bank counterparty
   - same-ruler unity
   - safety/pregnancy/property and other dedicated balance paths
2. fatal blockers are checked
3. enhanced denial conditions are checked
4. theft/loss-specific denials are checked
5. benefic support is calculated, but mostly logged as secondary testimony
6. occurrence questions append a no-perfection denial explanation
7. the branch still returns `NO`

The important practical point is:

- in the generic no-route branch, secondary testimonies can affect confidence and wording
- but they do not usually have the power to stop the final default denial

## Branch Matrix

### `perfection["perfects"] == False`

Current effect:

- generic branch initializes `result = "NO"`

Traditional interpretation:

- absence of direct route is serious
- but not every no-route chart should be collapsed immediately into hard denial before condition and testimony are weighed

Candidate change:

- replace immediate hard default with a secondary-balance evaluation step

### Moon next aspect result

Current effect:

- can adjust confidence
- can add reasoning
- does not usually stop no-route fallback from ending in `NO`

Traditional interpretation:

- Moon applying harmoniously to a significator or strong helper can materially change the tone of the judgment

Candidate change:

- allow strong favorable Moon-next testimony to contribute to a generic secondary-balance bucket

### Reception

Current effect:

- logged into supportive signals
- often visible in reasoning
- not generally verdict-level in the no-route branch

Traditional interpretation:

- substantial reception is more than a decorative modifier
- but weak face-only or vague reception should not become a false `YES`

Candidate change:

- promote only substantial reception measured by `traditional_strength`
- keep weak reception minor

### Benefic support

Current effect:

- benefic aspects are scored
- favorable/neutral support is logged
- branch still usually returns `NO`

Traditional interpretation:

- strong benefic aid tied to the quesited or significators can materially soften a chart
- isolated weak benefic contact should not reverse denial

Candidate change:

- promote only stronger benefic support tied directly to the matter
- do not let weak or diffuse benefic contact override no-route denial

### Quesited condition

Current effect:

- dignity/retrogradation/solar affliction are already considered elsewhere
- but they are not assembled into a dedicated generic secondary-balance score

Traditional interpretation:

- a quesited that is not retrograde, not terminally afflicted, and in workable condition should matter in a no-route chart
- a badly damaged quesited should resist soft positive testimony

Candidate change:

- let workable quesited condition add support
- let strong debility subtract support

### Moon VOC / Moon speed / separating benefic traces

Current effect:

- these are visible in reasoning
- they are sometimes treated as broad atmospheric testimony

Traditional interpretation:

- useful, but not decisive alone

Candidate change:

- Moon not void can add slight support
- Moon swift can remain minor context
- separating benefic traces should remain weak support only

## Corpus Observations From Phase 2

The focused no-route corpus shows two distinct groups:

### True-denial controls

Examples:

- `masters_program_no_perfection_no`
- `will_my_tenant_send_full_payment`
- `will_i_profit_from_this_bet`
- `divorce_no_manual_review`
- `pay_rise_article_spec`

These charts may show small supportive notes, but nothing strong enough to justify escaping generic denial.

### Elevated-support no-route charts

Examples:

- `marriage_no_manual_review`
- `is_there_any_hope_for_us_getting_back_together_should_i_wait_for_her`
- `will_investing_in_this_business_prove_profitable_for_me`
- `will_i_get_the_job_at_uw`

These charts already show combinations like:

- mixed or substantial reception
- Moon not void
- favorable Moon-next testimony
- one-way reception plus an applying supportive factor

These are the first charts that should test whether the no-route branch can yield `UNCLEAR` instead of an automatic hard `NO`.

## Testimony Promotion Rules

### Promote To Verdict-Level

These factors are strong enough to count in a generic secondary-balance score:

- substantial reception
  - use `traditional_strength`, not raw label text alone
- favorable Moon-next testimony
  - especially harmonious applying contact to a significator or strong helper
- strong benefic support
  - tied directly to the significators or quesited house
- workable quesited condition
  - not retrograde
  - not terminally afflicted
  - dignity not severely damaged
- Moon not void
  - minor supportive factor only

### Do Not Promote To Verdict-Level By Themselves

These should remain non-decisive alone:

- Moon swift by itself
- separating benefic traces alone
- weak face-only reception
- isolated benefic presence somewhere in the chart
- vague “supportive signals noted” without stronger tied testimony

## Target Hierarchy For Implementation

The no-route branch should split into:

- `affirmative_secondary_balance`
  - reserved for unusually strong secondary testimony
  - expected to be rare in the first pass
- `mixed_or_inconclusive_secondary_balance`
  - strong enough to stop automatic denial
  - should return `UNCLEAR`
- `denial_secondary_balance`
  - weak or insufficient support
  - remains `NO`

## Recommended First-Pass Safety Rule

The first implementation pass should be conservative:

- unlock `UNCLEAR` first
- keep `YES` for secondary-balance only at a higher threshold
- do not force the first corpus to produce affirmative no-route charts unless the testimony is truly exceptional

This keeps the remediation doctrinally cautious and reduces regression risk across Astro Clock and existing horary replay suites.
