# Astro Clock Transit Re-Audit: Phase 1
## 2026-03-28

This note restarts the transit audit from the source baseline instead of assuming the previous pass is still sufficient.

## Scope of this pass

This phase re-checks the Morin-facing house baseline against the current shared label layer used by:

- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

The goal is narrow:
- confirm whether the current house-domain summaries still match the source baseline closely enough
- tighten them where they drift into broader or more modern phrasing

## Source baseline used

Primary source reference:
- `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md`

Most relevant baseline:

- 2nd: wealth, gold, acquired goods
- 3rd: brothers, relations
- 4th: parents, inheritances
- 5th: children, bodily pleasures
- 6th: servants, subordinates, domestic animals
- 7th: marriage, open enemies, lawsuits
- 8th: death
- 9th: religion, journeys
- 10th: action, profession, dignity, fame
- 11th: friends
- 12th: sickness, imprisonment, exile, secret enemies, hardships

## Fresh findings

The previous audit had improved the labels materially, but several shared summaries were still broader than the baseline:

- `wealth` still read as generic finances/resources instead of acquired goods
- `children` still included a modern creative framing instead of bodily pleasures
- `health` still leaned toward daily-work wording instead of service/subordinates
- `relationships` was softer than Morin's mixed 7th-house baseline
- `death` still bundled crisis/debts into the main 8th-house summary
- `belief` still bundled study into the default 9th-house summary
- `honors` still defaulted to career/reputation instead of action/profession/dignity/fame
- `shared_resources` and `secrets` still needed clearer disclaimers as project shorthand rather than pure Morin wording

## Corrections made

Shared backend labels were tightened in:
- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`

Frontend visible labels were tightened in:
- `frontend/src/features/astroclock/TransitsModal.jsx`

Main corrections:

- `wealth` -> `wealth and acquired goods`
- `children` -> `children and bodily pleasures`
- `health` -> `illness, service, and subordinates`
- `relationships` -> `marriage, contracts, lawsuits, and open enemies`
- `death` -> `death and mortality`
- `belief` -> `religion and journeys`
- `honors` -> `action, profession, dignity, and fame`
- `shared_resources` -> `inheritance, debts, and shared burdens`
- `secrets` -> `seclusion, exile, or hidden adversity`

Frontend chip labels were aligned to the same direction:

- `belief` -> `religion/journeys`
- `relationships` -> `marriage/contracts/lawsuits/open enemies`
- `service` -> `servants/subordinates/animals`
- `health` -> `illness/service/subordinates`
- `shared_resources` -> `inheritance/debts/shared burdens`
- `hidden_enemies` -> `secret enemies/hardships`

## Claim boundary

This pass does not change ranking, event-family selection, or transit generation.

It only re-tightens the shared Morin-facing baseline used to describe what the backend is already returning.

## Verification target

This phase is complete when:

- backend label tests confirm the tightened house summaries
- frontend replay tests render the new baseline consistently

The next phase of the re-audit should return to event-family coverage and then backend ranking/parity.
