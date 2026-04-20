# Weather Benchmarks

This directory holds the benchmark branch for weather research.

The branch now has two distinct layers:

- doctrine / coverage benchmarks
- predictive hindcast benchmarks

The doctrine branch freezes local-source weather doctrine and worked historical cases into
a form that can be validated and reviewed.

The predictive hindcast branch asks a different question:

- when the seed runtime scans a known historical location across a benchmark window
- does the model concentrate pressure near the real event window
- and does the target window beat matched nearby non-event control windows

That still does not prove prospective prediction. It only measures hindcast timing alignment.

False-positive policy for the current predictive suite:

- false positives are penalized when non-event control windows at the same place beat the event window
- nearby-place spillover is allowed and is not treated as a benchmark failure in the current place-timeline hindcast setup
- if spatial spillover needs to be audited later, that should be a separate benchmark layer rather than folded into the same-place hindcast score

## Runtime Calibration Notes

- Family calibration profiles combine historical benchmark rows with doctrine/source-alignment citations when a source-backed claim maps to that family.
- This keeps the runtime coverage panel from understating source breadth when doctrine support exists outside the historical rows alone.
- Weather locality in the seed runtime still remains a proxy layer, but it now includes horizon/meridian target-zone intersections in addition to plain angular emphasis.

## Datasets

- `source_alignment_cases.jsonl`
  - Source-backed weather doctrine claims that a future benchmark-first weather branch must preserve.
- `historical_event_cases.jsonl`
  - Aggregate historical weather cases across the seeded families.
- `flood_cases.jsonl`
  - Narrow seeded flood cases.
- `hurricane_cases.jsonl`
  - Narrow seeded hurricane cases.
- `thunderstorm_tornado_cases.jsonl`
  - Narrow seeded thunderstorm, hail, and tornado cases.
- `drought_cases.jsonl`
  - Narrow seeded drought cases.
- `snow_freezing_precipitation_cases.jsonl`
  - Narrow seeded snow, blizzard, and freezing-precipitation cases.
- `temperature_extremes_cases.jsonl`
  - Narrow seeded heat-wave and cold-wave cases.
- `wind_cases.jsonl`
  - Narrow seeded wind and front-driven windstorm cases.
- `generalized_seasonal_temperature_cases.jsonl`
  - Narrow seeded seasonal baseline temperature-trend cases.
- `predictive_hindcast_cases.jsonl`
  - Place-timeline hindcast cases used to test whether the seed runtime concentrates pressure near known historical event windows and beats matched control windows.
  - Runner output includes per-case and per-family failure reasons so weak spots can be traced back to control losses, percentile weakness, rank weakness, or timing drift.
  - Cases may be marked `source_backed` when they are directly tied to the source corpus, or `novel_holdout` when they are historical weather events not cited in the source corpus and used to test out-of-source generalization.
- `prospective_forecast_cases.jsonl`
  - Forward-looking benchmark scaffold. Empty until intentionally populated with prospective weather cases.

## Source Alignment Shape

Each JSONL line in `source_alignment_cases.jsonl` must include:

- `enabled`
- `case_id`
- `doctrine_area`
- `label`
- `source`
- `input_context`
- `expected_conclusions`

## Historical Weather Benchmark Shape

Each JSONL line in the historical weather files must include:

- `enabled`
- `case_id`
- `weather_family_id`
- `label`
- `benchmark_type`
- `chart_basis`
- `event`
- `expected_weather_lead`
- `expected_interpretations`
- `source_assertions`

## Validation

Run:

```powershell
python backend/validate_weather_benchmark_datasets.py
```

## Predictive Hindcast Shape

Each JSONL line in `predictive_hindcast_cases.jsonl` must include:

- `enabled`
- `case_id`
- `runtime_family_id`
- `benchmark_family_id`
- `label`
- `scan_scope`
- `location`
- `timezone`
- `benchmark_window`
- `target_window`
- `control_windows`
- `time_step_hours`
- `scoring_expectations`
- `source_assertions`

Optional or conditional fields:

- `case_origin`
  - defaults to `source_backed`
  - may be set to `novel_holdout` for historical cases that are not cited in the source corpus
- `source_case_id`
  - required for `source_backed`
  - omitted for `novel_holdout`

For `novel_holdout` cases, `source_assertions` should cite event-verification material for the historical flood, storm, or other weather event rather than treating the source corpus itself as the case source.

## Doctrine / Coverage Runner

Run:

```powershell
python backend/run_weather_benchmarks.py
```

## Predictive Hindcast Runner

Run:

```powershell
python backend/run_weather_predictive_benchmarks.py
```

## Prospective Scaffold Runner

Run:

```powershell
python backend/run_weather_prospective_benchmarks.py
```
