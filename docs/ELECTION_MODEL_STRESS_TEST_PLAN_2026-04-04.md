# Election Model Stress Test Plan

## Goal

Build a stress-testing layer for election scorers that checks logic stability, ranking direction, and prohibition dominance under controlled mutations, not just route reachability.

This plan extends the audit in [ELECTION_ENGINE_VALIDATION_AUDIT.md](C:/Users/sabaa/Downloads/codexhorary/docs/ELECTION_ENGINE_VALIDATION_AUDIT.md).

## What to stress test

### 1. Deterministic invariants

These should always hold:

- adding a hard contraindication must not improve score
- weakening the relevant significator must not improve score
- strengthening the relevant significator must not lower score
- prohibition conditions must dominate soft positives
- direct scorer behavior must be stable under single-factor mutations

### 2. Pairwise interaction matrices

Per matter, vary two factors at a time around a stable control chart. Examples:

- surgery:
  - target body sign x Moon house
  - Mercury motion x Moon next aspect
  - strict never-rules x eclipse window
- journey:
  - Asc modality x L1 retrograde
  - 8th ruler condition x Moon affliction
- battle:
  - L1/L7 relation x Moon condition
  - Mars dignity x action type
- contract:
  - Mercury motion x contract mode
  - Desc sign quality x malefics on angles
- business:
  - MC ruler condition x Mercury condition
  - 2nd ruler condition x Moon next aspect

### 3. Ranking stress

Generate nearby candidate charts and assert relative ordering:

- clearly prohibited charts belong at or near the bottom
- clearly fortified charts must outrank neutral charts
- a single soft positive cannot offset a hard prohibition

### 4. Shared-helper safety

Stress shared functions in:

- [common.py](C:/Users/sabaa/Downloads/codexhorary/backend/election_models/common.py)

Specifically:

- sign resolution
- house resolution
- aspect extraction
- angular separation
- Moon via combusta checks
- finite-score behavior when optional fields are missing

### 5. Workflow parity

Once model-level invariants are stable, extend stress checks across:

- direct scorer calls
- backend election stream route
- frontend validation/stream serialization

## Implementation phases

### Phase 1: Pure-model invariant layer

Files:

- [election_stress_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/election_stress_utils.py)
- [test_election_model_invariants.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_election_model_invariants.py)

Scope:

- shared baseline charts
- chart mutators
- deterministic control-vs-mutation assertions

Status:

- Started and implemented in this change set

### Phase 2: Pairwise rank matrices

Planned file:

- `tests/test_election_rank_stress.py`

Scope:

- 20-40 generated cases per priority matter
- ordered assertions instead of snapshot-only outputs

Status:

- Started and implemented for surgery, journey, and battle in this change set

### Phase 3: Route/scorer parity stress

Planned extension:

- [test_election_route_contracts.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_election_route_contracts.py)

Scope:

- assert backend route output preserves scorer directionality on mocked chart fixtures

Status:

- Started and implemented for surgery, journey, and battle in this change set

### Phase 4: Fuzz and sparse-data stability

Planned file:

- `tests/test_election_fuzz_matrix.py`

Scope:

- partial chart payloads
- missing optional fields
- randomized aspect-list order
- no crash, finite score, list-of-tags guarantee

Status:

- Started and implemented for shared helpers plus surgery, journey, battle, contract, and business scorers in this change set

## First slice implemented

### Shared helper layer

Implemented:

- `whole_sign_cusps`
- `clone_chart`
- `set_planet`
- `set_aspects`
- `set_moon_next_aspect`
- `set_whole_sign_asc`
- baseline charts for:
  - surgery
  - journey
  - battle
  - contract
  - business

### Invariant tests added

Implemented:

- surgery:
  - Mercury retrograde never beats direct control
  - Moon applying to a retrograde planet never beats control
- journey:
  - fixed rising never beats movable control
  - retrograde ASC ruler never beats direct control
- battle:
  - L1 applying to stronger L7 triggers prohibition dominance
- contract:
  - new-contract Mercury retrograde scores below direct control
- business:
  - improving MC ruler never lowers score

## Why this structure

- It keeps the first pass deterministic and cheap to run.
- It avoids embedding route/UI assumptions in the first stress layer.
- It makes future matrix generation reusable instead of duplicating fixtures across files.
- It supports both Morin-grounded and product-heuristic models without pretending every weight is equally doctrinal.

## Recommended next additions

1. Split CI into:
   - PR tier: invariant suite + critical route parity
   - heavier tier: rank matrices + fuzz cases

## CI Tier Commands

The GitHub Actions workflow now splits the election stress layer like this:

- fast election tier:
  - `pytest -q tests/test_election_route_contracts.py tests/test_election_model_invariants.py`
- heavy election tier:
  - `pytest -q tests/test_election_rank_stress.py tests/test_election_fuzz_matrix.py`

The general backend job excludes those four files so the election tiers own them explicitly.
