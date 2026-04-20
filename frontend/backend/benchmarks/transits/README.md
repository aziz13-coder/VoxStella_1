# Transits Benchmarks

This benchmark branch validates transits workflow behavior and context maturity.

It does not claim broad predictive validity.

## Dataset Files

- `exact_scan_consistency_cases.jsonl`
  - exact analysis vs matching scan-row consistency
- `predictor_stability_cases.jsonl`
  - predictor output stability across step sizes
- `documented_hindcast_cases.jsonl`
  - documented local-source Morin examples used as seed hindcasts

## Runner

- `python backend/run_transits_workflow_benchmarks.py`

## Validation

- `python backend/validate_transits_benchmark_datasets.py`

## Current Scope

This branch is deliberately small:

- workflow validation first
- doctrinally documented hindcasts second
- wider predictive claims deferred until the workflow contract is stable
