# Weather Runtime Schema

Status date: 2026-04-12

## Status

The repo now has a first seed weather runtime.

It is:

- `benchmark-backed`
- `research-gated`
- `seed_runtime`
- `not production-grade meteorology`

It is intentionally narrower than the mundane engine.

## Runtime Scope

The first runtime exposes four family-specific weather lenses:

1. `flood_risk`
2. `hurricane_pressure`
3. `severe_convective_pressure`
4. `wind_event_pressure`

These are implemented as a separate sibling runtime, not as new mundane domains.

## Endpoint Surface

The backend now exposes:

- `GET /api/astro-clock/weather/catalog`
- `GET /api/astro-clock/weather/context/resolve`
- `GET /api/astro-clock/weather/analyze`

## Request Schema

`/weather/context/resolve` and `/weather/analyze` accept:

- `family_id`
- `forecast_datetime`
- `location`
- `timezone`
- `latitude`
- `longitude`
- `house_system_code`
- `source_preference`

Fallback behavior:

- `forecast_datetime` falls back to the current Astro Clock timestamp
- `location` falls back to the current Astro Clock location
- `timezone` falls back to the current Astro Clock timezone
- `house_system_code` falls back to the active clock house system

## Context Schema

Resolved context contains:

- `request`
- `active_clock`
- `family`
- `event_context`
- `chart_resolution`
- `research_flags`
- `source_tags`

### `chart_resolution`

The first runtime resolves three chart layers:

- `primary_chart`
  - the forecast chart at the requested datetime and place
- `supporting_charts[0]`
  - the latest cardinal ingress before the forecast time
- `supporting_charts[1]`
  - the latest lunar phase before the forecast time

Signals include:

- seasonal ingress identity and angular hits
- lunar phase identity and angular hits
- forecast-chart angular hits

## Analysis Schema

`/weather/analyze` returns:

- `context`
- `framework_layer`
- `trigger_layer`
- `locality_layer`
- `family_assessment`
- `doctrine`
- `research`

### `framework_layer`

This is the seasonal backdrop.

It answers:

- what the latest ingress suggests as the broader weather frame
- whether the chosen family has a stronger seasonal predisposition

### `trigger_layer`

This is the shorter activation layer.

It answers:

- what the latest lunar phase is adding
- whether forecast-chart aspects or angular planets increase short-term pressure

### `locality_layer`

This is explicitly limited.

It does not yet implement a full weather map runtime.

Instead it uses:

- forecast-chart angularity
- nearest-angle emphasis
- target-zone proxy logic

This is why the runtime returns the research flag:

- `locality_proxy_only`

### `family_assessment`

This contains:

- `family_id`
- `family_label`
- `benchmark_family_id`
- `score`
- `level`
- `summary`
- `matched_rules`
- `signals`

The level is currently:

- `quiet`
- `watch`
- `elevated`
- `active`

### `doctrine`

This contains:

- `source_tags`
- `sources`
- `notes`

### `research`

This contains:

- `status`
- `runtime_scope`
- `calibration`
- `flags`
- `limitations`

The calibration payload is benchmark-driven and includes:

- `coverage_tier`
- `unique_case_count`
- `dataset_row_count`
- `source_count`
- `source_titles`
- `benchmark_type_counts`
- `chart_basis_counts`
- `gaps`

## Design Constraints

The first runtime is intentionally constrained:

- no generic weather super-score
- no earthquake runtime
- no climate model claims
- no full astrocartography-style weather line engine
- no claim of meteorological completeness

## Current Limitation

The seed runtime is suitable for:

- schema proving
- family-specific rule preservation
- benchmark-backed exploratory output

It is not yet suitable for:

- operational forecasting claims
- production map scanning
- generalized cross-family automation
