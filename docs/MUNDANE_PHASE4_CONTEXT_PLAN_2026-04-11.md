# Mundane Phase 4 Chart-Context And Polity Expansion Plan

## Goal

Expand chart-context and polity coverage without weakening provenance.

Phase 4 is not a bulk country-list exercise. It is the point where the runtime starts handling:

- more source-backed polity charts
- more than one chart per polity
- period-aware chart selection when regimes change
- stricter refusal when no chart matches the requested period

## Why This Phase Is Next

Phases 1 through 3 made the domain and trigger layers mature enough that the next accuracy limit is chart provenance.

The main risks now are:

- silently using the wrong regime chart for the selected period
- exposing polities with charts in the registry but no context-aware selection
- keeping proving coverage concentrated in only a few polities

## Scope

### Runtime registry expansion

Add source-backed chart entries for:

- Germany
  - `german_empire_1871`
  - `german_republic_1918`
  - `third_reich_1933`
- France
  - `france_fourth_republic_1946`
- Israel
  - `israel_proclamation_1948`
  - `israel_mandate_termination_1948`
- India
  - `india_dominion_1947`
  - `india_republic_1950`

### Context-aware chart selection

When a polity has multiple national charts and the user does not explicitly choose one:

1. prefer a chart whose `valid_from` / `valid_to` window matches the selected event period
2. if no period match exists, fail honestly for `national_chart` requests
3. avoid silently reusing historical or regime-limited charts outside their supported period

### Benchmark-visible registry growth

Every new runtime chart should also appear in benchmark-visible source files:

- `backend/benchmarks/mundane/national_chart_candidates.jsonl`
- `backend/benchmarks/mundane/national_chart_proving_cases.jsonl` when the source base supports at least seeded proving

## First Slice

The first Phase 4 slice is:

- make Germany, Israel, and India source-backed runtime polities
- add France Fourth Republic as a second French regime chart
- implement period-aware chart selection
- widen candidate coverage and seed additional German regime proving cases

## Acceptance Gate

Phase 4 first slice is complete when:

1. the runtime registry exposes additional source-backed polities and charts
2. context resolution auto-selects a matching regime chart when one exists
3. `national_chart` requests fail cleanly when no chart matches the selected period
4. candidate and proving datasets expand alongside the runtime registry
5. tests and benchmark validators remain green

## Completion Note

Phase 4 is now complete.

What closed the phase:

- source-backed runtime registry expansion for France, Germany, India, Israel, and Burma
- period-aware chart selection with honest refusal outside supported windows
- alias-aware polity resolution for Burma / Myanmar
- widened proving coverage beyond the United Kingdom, United States, and Germany
- an executable national-chart proving runner:
  - `backend/mundane_national_chart_proving_runner.py`
  - `backend/run_mundane_national_chart_proving_benchmarks.py`

The proving layer is intentionally mixed:

- `source_explicit` where the corpus makes direct later-event reuse explicit
- `source_seeded` where the corpus supports regime or founding comparison but not yet a fully explicit later-event overlay

That is enough to close Phase 4 because the chart-context layer is now:

1. wider in registry coverage
2. period-aware in runtime selection
3. benchmark-visible
4. executable through a dedicated proving harness

## Next Phase

Move to Phase 5 domain-family expansion only where new families satisfy the usual gate:

- source-backed doctrine exists
- benchmark pack exists
- runtime flags can expose the maturity honestly
