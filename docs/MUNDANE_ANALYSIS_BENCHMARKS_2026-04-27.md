# Mundo / Mundane Analysis Benchmarks

This benchmark compares known historical mundane events against the live
Mundane analysis engine. It is not a fixture-only scorer: every executed case
is converted into a real analysis request, resolved through `resolve_context`,
and analyzed through `analyze_context`.

## Source Files

- Runner: `backend/mundane_analysis_benchmark_runner.py`
- CLI wrapper: `backend/run_mundane_analysis_benchmarks.py`
- Tests: `backend/test_mundane_analysis_benchmark_runner.py`
- Historical datasets: `backend/benchmarks/mundane/*.jsonl`

## Runtime Cost

The default dataset set contains overlapping aggregate and per-domain files.
Several historical cases appear in both `historical_event_cases.jsonl` and a
domain-specific JSONL file. The runner now dedupes matching `case_id` values by
default so the same true event is not executed twice.

Chart resolution can still be expensive because it uses the same chart bundle
path as the application. War-event charts resolve an event chart. Ingress,
lunation, and eclipse charts may run ephemeris searches before resolving the
final chart bundle. Eclipse cases are the heaviest because they scan candidate
lunations/eclipses and then validate node proximity.

The runner now wraps the bundle resolver with an in-run memoization cache by
default. This avoids recomputing identical chart bundles inside a case or across
duplicate/raw rows. The cache is process-local; it does not persist to disk and
does not change engine output.

`resolve_chart_resolution` also avoids computing the active overlay chart unless
the selected chart type needs it. At present, the overlay is used by eclipse
analysis for eclipse-degree activation and supporting-chart reporting.

## Commands

Full deduped run:

```powershell
python backend\run_mundane_analysis_benchmarks.py --output-json mundane_analysis_benchmark.json --output-md mundane_analysis_benchmark.md
```

Focused runs:

```powershell
python backend\run_mundane_analysis_benchmarks.py --domain war_outbreak
python backend\run_mundane_analysis_benchmarks.py --case-id war_outbreak_fort_sumter_1861
python backend\run_mundane_analysis_benchmarks.py --max-cases 10
```

Raw dataset-row run, including duplicate `case_id` rows:

```powershell
python backend\run_mundane_analysis_benchmarks.py --include-duplicate-cases
```

Profiling run without in-process chart bundle memoization:

```powershell
python backend\run_mundane_analysis_benchmarks.py --no-bundle-cache --max-cases 10
```

## Report Fields

- `case_count`: executed result rows after input filtering and default dedupe.
- `executed_count`: rows that reached an engine score.
- `skipped_count`: rows skipped by the engine path, such as unsupported domains.
- `input_skipped_count`: input rows skipped before execution.
- `duplicate_input_count`: skipped input rows with duplicate `case_id`.
- `bundle_cache`: process-local cache calls, hits, misses, and size.

## Practical Notes

Run by domain when investigating calibration. Full-suite runs are useful for a
rollup, but domain-sized reports make it easier to see whether failures are
coming from chart selection, location resolution, or domain-rule scoring.

If a run is unexpectedly slow, inspect `bundle_cache.misses` and the selected
chart types. High eclipse/lunation volume or cold geocoding can dominate runtime.
