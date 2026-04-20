# Transits Workflow Validation And Context Plan
Date: 2026-04-14

## Scope

This plan covers only two transits remediation tracks from the audit:

1. workflow validation benchmarks
2. context-layer maturity surfacing

It does not change transit scoring, prediction language, or frontend structure by itself.

## Why These Two Tracks Come First

The current transits engine has enough runtime depth to look mature, but two things are still too implicit:

- workflow behavior across exact analysis, window scan, and predictor is not benchmarked as one system
- context layers are exposed unevenly, while the runtime does not clearly state which layers are full, partial, or helper-only

If those two gaps stay open, later scoring or UI changes will be harder to evaluate honestly.

## Point 2. Workflow Validation Benchmarks

### Goal

Add a benchmark suite that validates runtime workflow behavior, not just doctrinal labels.

### Deliverables

- `backend/benchmarks/transits/`
  - `README.md`
  - `exact_scan_consistency_cases.jsonl`
  - `predictor_stability_cases.jsonl`
  - `documented_hindcast_cases.jsonl`
- `backend/validate_transits_benchmark_datasets.py`
- `backend/transits_workflow_benchmark_runner.py`
- `backend/run_transits_workflow_benchmarks.py`
- `backend/test_transits_workflow_benchmark_runner.py`

### Benchmark Families

#### A. Exact vs Window Consistency

Purpose:

- confirm that a timestamp evaluated directly through `/transits`
- is materially consistent with the matching row inside `/transits/window`

Case design:

- use timestamps that fall exactly on the scan cadence
- compare:
  - top transit signature overlap
  - top prediction family overlap

Acceptance shape:

- matching scan row exists
- at least one top transit signature overlaps
- at least one prediction family overlaps

#### B. Predictor Stability Across Step Sizes

Purpose:

- confirm that `/predictor` does not radically change its dominant family merely because scan step size changes

Case design:

- same natal and same date window
- run predictor twice with two step sizes
- compare:
  - dominant family key
  - matched family rank
  - dominant timestamp gap

Acceptance shape:

- expected family appears in both runs
- family rank remains inside a bounded threshold
- dominant timestamps remain within a bounded tolerance

#### C. Documented Hindcast Cases

Purpose:

- test the runtime against explicitly documented local-source cases

Initial seed:

- Morin doctorate example
- Morin near-drowning example

Acceptance shape:

- expected life area or event family appears in ranked predictions
- dominant timestamp falls within or near the documented target window

### Output Contract

The runner should emit:

- per-case result rows
- per-benchmark-family summary
- aggregate summary

The benchmark should stay critical:

- consistency is not prediction
- hindcast hit is not proof of general predictive validity

## Point 3. Context-Layer Maturity

### Goal

Make context maturity explicit in the runtime contract, especially for:

- primary directions
- solar arc
- progressions
- solar return
- lunar return
- focus suggestions

### Deliverables

- `backend/transits_context_maturity.py`
- `/api/astro-clock/context/auto` returns `context_maturity`
- `docs/TRANSITS_CONTEXT_MATURITY_2026-04-14.md`
- API and unit tests

### Required Classification

Each layer must be marked as one of:

- `full`
- `partial`
- `helper_only`

### Runtime Rule

The API should not imply that all context layers are equally implemented.

Instead, `context_maturity` should state:

- `level`
- `surface_scope`
- `summary`
- `available_outputs`
- optional `gaps`

### Expected Initial Classification

Expected starting shape from the audit:

- primary directions: `partial`
- solar arc: `partial`
- secondary progressions: `partial`
- solar return: `partial`
- lunar return: `helper_only`
- focus suggestions: `helper_only`

These levels may be adjusted during implementation if the source inspection shows a stronger or weaker contract than the audit memo stated.

## Implementation Order

1. create the plan-aligned benchmark datasets
2. add validator
3. add runner and CLI
4. add benchmark tests
5. add context maturity inventory module
6. expose `context_maturity` from `/context/auto`
7. add API tests for maturity payload
8. run targeted tests and benchmark command

## Acceptance Criteria

Point 2 is complete when:

- the new benchmark datasets validate
- the runner executes end to end
- the suite reports exact/scan consistency, predictor stability, and documented hindcasts separately

Point 3 is complete when:

- `/context/auto` returns explicit maturity metadata
- tests pin the shape and expected levels
- the repo has a written maturity memo

## Non-Goals

- no transit scoring retune
- no frontend refactor
- no claim that benchmark consistency proves predictive power
