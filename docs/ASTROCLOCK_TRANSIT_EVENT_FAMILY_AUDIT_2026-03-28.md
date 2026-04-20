# Astro Clock Transit Event-Family Audit
## 2026-03-28

This note starts the next transit audit phase after the house-domain cleanup.

The question here is narrower than the house audit:
- not "which house does this belong to?"
- but "which event-family labels are defensible from the Morin source, and which are too modern, too narrow, or too absolute?"

## Scope

Code surfaces in scope:
- `backend/transits_morin.py`
- `backend/nlg_templates.py`
- `frontend/backend/transits_morin.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

Source basis:
- `horary_knowledge/desktop_books_text/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt`
- `horary_knowledge/desktop_books_text/toaz.info-jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl-pr_c198dcbe1e631c7e9f774ec5e70b435c.txt`
- `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md`

## Source-facing standard

From the Morin material already summarized:
- event judgment is determination-led
- the same structural contact can signify multiple kinds of accidents
- the astrologer should preserve multiple possibilities, then surface the strongest principal one
- labels should remain conservative when the source itself is mixed

That means the event-family layer should prefer:
- broad but source-defensible labels
- explicit house-type language where appropriate
- avoiding modern overstatement when the source only supports a looser class

## Event-family buckets

### 1. Near-literal or strongly source-defensible

These are close enough to the source to keep with minimal concern:
- `marriage`
- `lawsuit`
- `legal_victory`
- `legal_defeat`
- `settlement`
- `attack_violence`
- `death_natural`
- `death_violent`
- `arrest_imprisonment`
- `exile_or_forced_travel`
- `short_journey`
- `long_journey`
- `honor_award`
- `new_job`
- `job_loss`

These are not always Morin's exact wording, but they map closely to:
- marriage
- lawsuits/open disputes
- open enemies/conflict
- death/danger to life
- imprisonment/exile
- journeys
- dignity/profession/honour

### 2. Acceptable modern shorthand if kept conservative

These are product-layer labels that are still usable if phrased carefully:
- `public_recognition`
- `recognition`
- `public_approval`
- `business_deal`
- `contract_signing`
- `financial_gain`
- `financial_loss`
- `salary_increase`
- `recovery_health`
- `communication_breakthrough`
- `romantic_connection`

These should not sound more certain or more specific than the source allows.

Examples:
- `public_recognition` is better rendered as fame/distinction than as celebrity-style approval
- `contract_signing` is better rendered as contract/agreement than as a fully modern corporate action
- `recovery_health` is better rendered as recovery from illness than as a broad medical success claim

### 3. High-risk or high-bar families

These require stricter determination and wording:
- `death_natural`
- `death_violent`
- `death_of_family`
- `near_death_experience`
- `imprisonment_risk`
- `war_declaration_offensive`
- `war_response_defensive`
- `internal_conflict_war`

These should remain high-bar:
- because Morin's houses are mixed
- because the same houses also signify broader adversity
- because overstatement here damages trust faster than under-statement

## Initial findings

The first wording targets that still looked more modern than needed were:
- `public_recognition`
- `recognition`
- `public_approval`
- `business_deal`
- `contract_signing`
- `financial_gain`
- `financial_loss`
- `salary_increase`
- `recovery_health`

These were not severe algorithm bugs.

They were wording-layer drift:
- useful for a product UI
- but not as source-sensitive as they should be after the Morin house/domain cleanup

## First pass applied

This first pass tightens only the clearest labels and leaves higher-risk ranking logic untouched.

Direction of the changes:
- `public_recognition` -> fame/distinction language
- `recognition` -> fame/recognition language
- `public_approval` -> favor/approval language
- `business_deal` -> business/contract agreement language
- `contract_signing` -> contract/agreement language
- `financial_gain` -> gain in wealth/income language
- `financial_loss` -> loss of wealth/expense language
- `salary_increase` -> increase in salary/income language
- `recovery_health` -> recovery from illness language

This is intentionally a wording pass, not a re-ranking pass.

### Implemented status

Applied in code:
- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

First-pass label changes now live in the product:
- `public_recognition` -> `public fame/distinction`
- `recognition` -> `fame/recognition`
- `public_approval` -> `public favor/approval`
- `business_deal` -> `business/contract agreement`
- `contract_signing` -> `contract/agreement`
- `financial_gain` -> `gain in wealth/income`
- `financial_loss` -> `loss of wealth/expense`
- `salary_increase` -> `increase in salary/income`
- `recovery_health` -> `recovery from illness`

Pinned by tests:
- backend label assertions in `backend/test_transits_quality.py`
- frontend modal assertions in `frontend/src/tests/transitsModalReplay.test.jsx`

Verification:
- backend wording suite passed
- frontend replay suite passed after updating stale expectations from the older `public recognition` wording
- frontend production build passed

## What comes next

After this first event-family wording pass, the next likely high-value checks are:
1. audit the relationship-family set:
   - `romantic_connection`
   - `reconciliation`
   - `partnership_strengthened`
   - `partnership_strained`
2. audit the wealth-family set:
   - `speculation_gain`
   - `speculation_loss`
   - `inheritance_windfall`
   - `shared_resource_loss`
3. then return to ranking/parity:
   - does the backend still surface the wrong principal event family even when the wording is corrected?

## Second pass applied: relationship-family wording

This pass tightens the relationship-family layer toward Morin's 7th-house baseline:
- marriage
- agreements/contracts
- lawsuits/open disputes
- open enemies

It does not try to modernize Morin into relationship psychology.

Direction of the changes:
- `romantic_connection` -> courtship/attachment language
- `reconciliation` -> renewed accord language
- `engagement` -> engagement/betrothal language
- `divorce` -> dissolution of union language
- `separation` -> estrangement language
- `relationship_conflict` -> partnership/open-dispute language
- `betrayal` -> breach-of-trust language
- frontend partnership chips softened toward confirmation/dispute rather than generic emotional wording

Applied in code:
- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

Pinned by tests:
- backend label assertions in `backend/test_transits_quality.py`
- frontend modal assertions in `frontend/src/tests/transitsModalReplay.test.jsx`

Verification:
- backend wording suite passed
- frontend replay suite passed
- frontend production build passed

One real UI improvement came out of this pass:
- the exact-time summary now has relationship-family chip curation so courtship rows surface courtship/reconciliation/engagement-strengthening signals, and dispute rows surface dispute/separation/breach/strain signals, instead of dropping them behind a generic summary cap

## Third pass applied: wealth-family wording

This pass tightens the wealth-family layer toward Morin's 2nd/4th baseline:
- wealth
- acquired goods
- salary or income
- inheritances/successions

It avoids making project-taxonomy debt/shared-resource language sound like literal Morin wording.

Direction of the changes:
- `speculation_gain` -> gain through speculation or hazard
- `speculation_loss` -> loss through speculation or hazard
- `inheritance_windfall` -> inheritance/succession gain language
- `shared_resource_loss` -> debts/shared burdens language
- frontend wealth chips now curate gain/loss families instead of mixing all financial labels together

Applied in code:
- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

Pinned by tests:
- backend label assertions in `backend/test_transits_quality.py`
- frontend modal assertions in `frontend/src/tests/transitsModalReplay.test.jsx`

Verification:
- backend wording suite passed
- frontend replay suite passed
- frontend production build passed

## Goal

The goal is not to make the UI archaic.

The goal is:
- keep the product readable
- keep the labels source-sensitive
- keep the event-family layer from sounding narrower, more modern, or more certain than Morin's doctrine justifies

## Fourth pass applied: home, travel, study, and spiritual wording

This pass tightens four adjacent clusters against the Morin house baseline:
- 3rd house: brothers, relations, short journeys
- 4th house: parents, inheritances, home
- 9th house: religion and journeys
- mixed study/publication shorthand attached to the 9th or related determination

Direction of the changes:
- `degree_completion` -> completion of studies/degree language
- `exam_success` / `exam_failure` -> examination/trial language
- `enrollment_admission` -> admission/entrance into study language
- `spiritual_awakening` / `religious_conversion` / `pilgrimage` / `mystical_experience` -> religion/faith/journey language instead of looser modern spirituality
- `publication` / `artistic_success` -> issued-work / distinction language
- `family_celebration` / `family_conflict` / `moving_home` / `purchase_property` / `relocation_permanent` -> family, household, property, and residence language
- `short_journey` / `long_journey` -> short/local movement and long/distant travel language
- frontend domain chips now prefer:
  - `parents/home/inheritance`
  - `brothers/relations and short journeys`
  - `religion/belief`
  - `illness/service/daily work`

Applied in code:
- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

Pinned by tests:
- backend label assertions in `backend/test_transits_quality.py`
- frontend modal assertions in `frontend/src/tests/transitsModalReplay.test.jsx`

Verification target for this pass:
- backend wording suite
- frontend modal replay suite
- frontend production build
