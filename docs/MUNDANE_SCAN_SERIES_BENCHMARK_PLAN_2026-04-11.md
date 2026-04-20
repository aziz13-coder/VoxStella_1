# Mundane Scan Series Benchmark Plan

Date: 2026-04-11

## Goal

Benchmark the new graph-oriented spatiotemporal scan layer so it is judged on more than hotspot inclusion.

The new benchmark target is not only:

- did the expected place appear in the returned rows

It is also:

- did the expected place rise early enough
- did it peak strongly enough
- did the graph distinguish opening-break pressure from later campaign pressure

## Current Baseline

The current scanner benchmark stack already exists:

- dataset: `backend/benchmarks/mundane/scanner_cases.jsonl`
- runner: `backend/mundane_scan_benchmark_runner.py`
- CLI: `backend/run_mundane_scan_benchmarks.py`
- dataset validator: `backend/validate_mundane_benchmark_datasets.py`

That stack grades:

- returned rows
- matched rank
- score separation
- scan-level separation

It does not yet grade the new graph-oriented series output.

## What Has To Be Benchmarked Now

The new series graph adds three distinct claims:

1. `timeline fidelity`
   - the scan should return the expected timepoints for the request window
2. `place-series quality`
   - the expected place should have a coherent time series, not just one surviving cell
3. `breakout interpretation quality`
   - the expected place should rank correctly as an opening-break or sustained-theater candidate

## Benchmark Layers

### Layer 1: Structural Series Benchmarks

These are correctness checks, not astrology checks.

For each series-enabled scan case, verify:

- `series.timeline` exists
- timeline length matches the expected time-slice count
- `series.places` is non-empty
- each kept place has a series aligned to the returned timeline
- `series.breakout_candidates` exists
- `series.series_overview` exists

These should be hard failures.

### Layer 2: Place-Series Benchmarks

These test whether the expected place survives as a meaningful series.

For each case, verify:

- expected place appears in `series.places`
- expected place has non-zero `peak_scan_score`
- expected place has a `peak_datetime`
- expected place has either:
  - `first_active_datetime`, or
  - a peak score explicitly greater than zero

These should also be hard failures for war-series cases.

### Layer 3: Breakout-Ordering Benchmarks

These test the graph’s ranking logic.

For each case, allow expectations such as:

- expected place in `breakout_candidates`
- expected place maximum breakout rank
- expected place minimum peak score
- expected place minimum breakout index

This is the graph-layer equivalent of the existing rank-based scanner benchmark.

### Layer 4: Semantic Shape Benchmarks

These are weaker but important.

For selected cases, verify:

- the expected place is classified as:
  - `opening_break_candidate`
  - or `sustained_theater_candidate`
- a clearly late place is not misclassified as an early break candidate

These should begin as warnings, not hard failures, until the graph layer matures.

## Dataset Strategy

Do not overload `scanner_cases.jsonl` with graph-specific expectations.

Create a sibling dataset:

- `backend/benchmarks/mundane/scanner_series_cases.jsonl`

Each row should contain:

- `case_id`
- `enabled`
- `label`
- `request`
- `series_expectation`
- `benchmark_refs`

`request` should reuse the same shape as the existing scanner cases.

`series_expectation` should support:

- `expected_time_slices`
- `expected_place_tokens_any`
- `expected_breakout_place_tokens_any`
- `max_breakout_rank`
- `minimum_peak_scan_score`
- `minimum_breakout_index`
- `expected_breakout_kind_any`
- `require_nonzero_series`
- `require_series_alignment`

## Initial Case Set

Start with a narrow set.

### War-Series Cases

- U.S.-Iran 2026, Persian Gulf, U.S. lens
- U.S.-Iran 2026, Persian Gulf, Iran lens
- U.S.-Iran 2026, Middle East short window

### Non-War Control Cases

At least two control cases to keep the graph layer from overfitting war:

- UK 1910 government
- UK 1919 public health

The control cases do not need breakout semantics as strong as war, but they do need structural series validation.

## Runner Design

Add a dedicated runner:

- `backend/mundane_scan_series_benchmark_runner.py`

Responsibilities:

- load `scanner_series_cases.jsonl`
- run the existing scan engine with `include_series=True`
- evaluate structure, place-series, breakout ordering, and semantic-shape expectations
- emit:
  - pass/fail
  - strong pass / weak pass
  - warning flags

Recommended warning flags:

- `missing_series`
- `timeline_length_mismatch`
- `expected_place_missing_from_series`
- `expected_place_missing_from_breakout_candidates`
- `expected_breakout_not_top_rank`
- `low_breakout_index`
- `low_peak_scan_score`
- `unexpected_breakout_kind`

## Grading Policy

### Hard Failures

- no series returned
- timeline shape mismatch
- expected place missing from series
- required non-zero series not met
- required breakout candidate not met

### Weak Passes

- expected place survives but only at the rank limit
- breakout index is low but above threshold
- expected breakout kind is only partially matched

### Strong Passes

- expected place is present in the series
- expected place appears near the top of breakout candidates
- non-zero peak is clear
- breakout kind is correct
- no structural warnings

## Calibration Sequence

Benchmarking should proceed in this order:

1. structural series correctness
2. breakout candidate ranking
3. breakout-kind semantics

Do not calibrate semantic-shape thresholds before the structural layer is stable.

## Source Policy

The graph benchmark should stay tied to the same source-backed benchmark anchors already in the repo:

- war anchor summaries
- historical event benchmark rows
- scanner benchmark references

No new book ingestion is required just to benchmark the graph layer.

If graph semantics later need stronger historical support, add that through the benchmark anchor files first, not through ad hoc UI tuning.

## Recommended Implementation Order

1. add `scanner_series_cases.jsonl`
2. extend dataset validation
3. build `mundane_scan_series_benchmark_runner.py`
4. add CLI wrapper
5. seed the three U.S.-Iran war series cases
6. add two non-war control series cases
7. run the suite and inspect weak-pass warnings

## Acceptance Gate

The graph-series benchmark layer is good enough when:

- every series-enabled case returns structurally valid graph data
- the expected place survives in the series layer
- war cases produce non-zero breakout candidates
- the graph benchmark can distinguish strong passes from weak passes

## Non-Goals

- replacing the existing scanner benchmark runner
- using the graph benchmark as a doctrine claim
- forcing all scan domains into breakout semantics immediately
