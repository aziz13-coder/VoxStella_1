# Mundane Benchmarks

This directory holds the seed benchmark assets for the future mundane astrology layer.

These files are not tied to a production scoring runner yet. Their purpose is to freeze
the first textbook-backed claims and historical test cases into a format that can be
validated, expanded, and eventually executed by a dedicated mundane benchmark harness.

## Datasets

- `source_alignment_cases.jsonl`
  - Textbook-backed doctrine claims that a future interpretation layer must preserve.
- `historical_event_cases.jsonl`
  - Cross-domain benchmark cases for wars, leadership crises, unrest, and finance.
- `war_conflict_cases.jsonl`
  - Domain slice focused on war and direct hostilities.
- `government_stability_cases.jsonl`
  - Domain slice focused on rulers, administrations, and legislative disruption.
- `leadership_transition_cases.jsonl`
  - Focused slice for monarch deaths, accessions, coronation crises, and office instability.
- `alliance_stress_cases.jsonl`
  - Focused slice for allied-support failure, friendly-nation strain, and coalition backing rupture.
- `trade_and_commerce_cases.jsonl`
  - Focused slice for trade disputes, treaty-port blockades, shipping interruption, embargo pressure, and parliamentary blockage affecting commerce.
- `epidemic_wave_pressure_cases.jsonl`
  - Focused slice for epidemic surge, recurrence, secondary-wave timing, and subsiding pressure inside the broader public-health domain, including non-influenza wave anchors.
- `civil_unrest_cases.jsonl`
  - Domain slice focused on riot, lawlessness, and public disorder signals.
- `finance_economy_cases.jsonl`
  - Domain slice focused on depression, collapse, and prolonged financial stress.
- `diplomacy_foreign_affairs_cases.jsonl`
  - Domain slice focused on treaties, settlements, allies, and foreign-affairs reversals.
- `public_health_cases.jsonl`
  - Domain slice focused on epidemics, public sickness, hospitalization pressure, and mortality spikes.
- `national_chart_proving_cases.jsonl`
  - Historical proving pack that tests candidate national charts against benchmark events.
- `retrograde_mars_cases.jsonl`
  - Trigger-focused pack for leadership cases explicitly tied to retrograde Mars.
- `national_chart_candidates.jsonl`
  - Source-backed candidate national charts for benchmarked overlay testing.
- `scanner_cases.jsonl`
  - Operational scanner benchmark cases that test whether scan output keeps an expected place inside the returned ranked cells.
- `scanner_series_cases.jsonl`
  - Graph-oriented scanner benchmark cases that test timeline shape, place-series survival, breakout ranking, and breakout-kind semantics.
- `trigger_profile_cases.jsonl`
  - Trigger-profile benchmark cases that test computed angularity, retrograde Mars, eclipse-degree activation, and mutation/conjunction-cycle output directly against source-alignment doctrine refs.
- `war_scan_hindcast_cases.jsonl`
  - Predictive-style hindcast cases for `war_event` scan runs that test whether the runtime recovers the relevant theater and concentrates pressure in the event window better than matched control windows.

## Source Alignment Shape

Each JSONL line in `source_alignment_cases.jsonl` must include:

- `enabled`
- `case_id`
- `doctrine_area`
- `label`
- `source`
- `input_context`
- `expected_conclusions`

The `source` object records the book, file anchor, page span, and the doctrine claim being
frozen. The `input_context` object defines the chart setting or condition under which the
claim applies.

## Historical Benchmark Shape

Each JSONL line in `historical_event_cases.jsonl`, `leadership_transition_cases.jsonl`,
`national_chart_proving_cases.jsonl`, `retrograde_mars_cases.jsonl`, `public_health_cases.jsonl`,
`alliance_stress_cases.jsonl`,
`trade_and_commerce_cases.jsonl`,
`epidemic_wave_pressure_cases.jsonl`,
and the domain slice
files must include:

- `enabled`
- `case_id`
- `domain_id`
- `label`
- `benchmark_type`
- `chart_basis`
- `event`
- `expected_domain_lead`
- `expected_interpretations`
- `source_assertions`

These cases are deliberately modest. They capture source-backed expectations about what a
future mundane model should prioritize, not a claim that full predictive performance has
already been validated.

## National Chart Candidate Shape

Each JSONL line in `national_chart_candidates.jsonl` must include:

- `enabled`
- `case_id`
- `candidate_id`
- `polity_id`
- `label`
- `benchmark_type`
- `candidate_type`
- `candidate_status`
- `confidence`
- `event`
- `expected_uses`
- `source_assertions`

## Validation

Run:

```powershell
python backend/validate_mundane_benchmark_datasets.py
```

The validator checks required fields, duplicate case IDs per file, and basic shape
correctness for both doctrine and historical case datasets.

## Runner

Run:

```powershell
python backend/run_mundane_benchmarks.py
```

The runner uses the validated datasets to build a coverage report, verify that all cited
raw and normalized source files still exist, and emit a markdown summary suitable for
review while the mundane model family is still in research mode.

## Scanner Runner

Run:

```powershell
python backend/run_mundane_scan_benchmarks.py
```

This runner executes the live mundane scan engine against a small operational case set.
The current scanner benchmark is intentionally modest: it checks whether the expected
location survives into the returned ranked cells, then reports ranking-quality warnings
such as flat zero-score returns, uniform levels, and expected locations only appearing at
the edge of the allowed rank band. This is an operational scanner benchmark, not yet a
research-grade top-1 discrimination benchmark.

## Scanner Series Runner

Run:

```powershell
python backend/run_mundane_scan_series_benchmarks.py
```

This runner evaluates the graph-oriented scan layer. It checks:

- whether a series payload is returned
- whether the timeline matches the requested scan shape
- whether the expected place survives into the aggregated place series
- whether the expected place survives into the breakout candidate band
- whether breakout rank, peak score, breakout index, and breakout kind meet the case expectations

## Trigger Runner

Run:

```powershell
python backend/run_mundane_trigger_benchmarks.py
```

This runner evaluates the trigger-profile layer directly. It checks:

- whether the requested trigger returns the expected computed status
- whether the trigger is active or background-only when expected
- whether score, strength, evidence count, and selected metrics meet the benchmark case
- whether each trigger case stays tied back to source-alignment doctrine refs

## War Scan Hindcast Runner

Run:

```powershell
python backend/run_mundane_war_scan_hindcasts.py
```

This runner executes a narrower, predictive-style war scan hindcast suite. It checks:

- whether the expected target place survives into `series.places`
- the target place rank inside the aggregated place-series output
- whether the target window is one of the stronger windows in that matched place series
- how far the selected peak sits from the target window
- whether the target window beats matched non-event control windows

This is still a hindcast localization benchmark, not proof of prospective war prediction.

## National Chart Proving Runner

Run:

```powershell
python backend/run_mundane_national_chart_proving_benchmarks.py
```

This runner executes the chart-context proving layer directly. It checks:

- whether a proving case resolves to the expected polity chart
- whether multi-chart polities select the expected regime map by period
- whether alias handling still lands on the same registry-backed polity
- whether the selected chart came from `period_match` or a weaker fallback path
