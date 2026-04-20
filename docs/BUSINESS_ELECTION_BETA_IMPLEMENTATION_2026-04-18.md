# Business Election Beta Implementation

Date: 2026-04-18

## Goal

Add a first-class `business beta` election path to Astro Clock, modeled on the decoded Galaxy business regime in:

- `C:\Program Files (x86)\Galaxy\docs\research\electioner_business_astrological_logic.md`

The key design choice is that business beta is not a two-person compatibility model like marriage beta. It is:

- one event election line
- plus one founder-owner fit line per selected saved chart

## Source Workflow

Frontend path:

- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/ElectionModal.jsx`
- `frontend/src/features/astroclock/api.mjs`

Backend path:

- `backend/astro_clock_api.py`
- `backend/election.py`
- `backend/election_models/business.py`
- `backend/election_models/business_beta.py`

## Request Contract

Business alpha:

- `matter=business`
- `business_algorithm=alpha`
- optional natal overlay via `natal_snap_id`

Business beta:

- `matter=business`
- `business_algorithm=beta`
- repeated `participant_snap_id` params for founder-owner charts

Example shape:

```text
/api/astro-clock/election/suggest/stream
  ?matter=business
  &business_algorithm=beta
  &participant_snap_id=snap-founder-a
  &participant_snap_id=snap-founder-b
```

## Backend Changes

- `backend/election.py` now re-exports `score_business_beta_election`.
- `backend/astro_clock_api.py` now validates `business_algorithm` separately from `marriage_algorithm`.
- Business beta validation requires at least one `participant_snap_id` and rejects duplicates.
- The stream route now loads founder-owner snap bundles, enriches them with the same beta chart augmentation layer used by marriage beta, and passes them as `business_participants` into the scorer.
- Business beta forces traditional timing context on the backend so planetary day and planetary hour logic are always available.
- Stream payloads now return:
  - `matter`
  - `business_algorithm`
  - `participants.items`
  - `participants.participant_snap_ids`

## Scoring Split

Business alpha remains the existing scorer in:

- `backend/election_models/business.py`

Business beta is isolated in:

- `backend/election_models/business_beta.py`

Business beta implements two layers:

1. Event chart scoring
2. Founder-owner fit scoring per selected participant

The beta event layer includes:

- Moon sign preferences
- Moon waxing bonus
- Moon-day rules
- slow-sign bonuses for Moon and Asc
- direct-motion checks for business targets
- planetary day and hour bonuses
- Moon damage penalties
- business-support aspect network
- house topology rules

The participant layer includes:

- participant business-target aspects to event Moon, Venus, and Jupiter
- Ascendant resonance with the event Asc
- participant Asc ruler to event Moon
- event Fortuna to natal Asc
- event 10th-house population bonus
- participant Asc ruler house placement inside the event chart

## Frontend Changes

- `frontend/src/features/astroclock/ElectionModal.jsx` now exposes a dedicated business alpha-beta toggle.
- Business beta hides the natal overlay path and replaces it with founder-owner saved chart selection.
- Business beta uses multi-select founder-owner charts instead of marriage-style A/B selectors.
- Business beta always sends `businessAlgorithm` and repeated `participantSnapIds`.
- Weighted beta tags are sanitized in the UI using the returned algorithm in the scan result, not only the currently selected toggle state.

## Verification

Backend:

- `python -m pytest backend\test_business_beta_contract.py -q`

Frontend:

- `npm run test:ui -- src/tests/electionModalHelpers.test.mjs src/tests/astroclockApi.test.mjs`

Results:

- backend: `5 passed`
- frontend: `28 passed`
