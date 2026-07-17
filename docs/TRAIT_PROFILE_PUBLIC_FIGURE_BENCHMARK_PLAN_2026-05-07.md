# Trait Profile Public Figure Benchmark Plan

Date: 2026-05-07

## Goal

Implement a repeatable Trait Profile benchmark over the 68 baseline candidates from `docs/TRAIT_PROFILE_PUBLIC_FIGURE_BENCHMARK_CANDIDATES_2026-05-07.md`.

The benchmark exercises the production Flask route:

```text
GET /api/astro-clock/traits/profile
```

This benchmark is a route stability and output coverage benchmark. It is intentionally separate from the smaller scored logic benchmark in `backend/trait_logic_benchmark_profiles.py`, because broad public-figure biography scoring needs careful expected-cluster design before it should affect pass/fail behavior.

## Data Contract

Each baseline case must have:

- Rodden `AA` or `A` timing only.
- A source URL to the Arcadia AstroDB page that cites Astro-Databank / Rodden Rating.
- A source local birth time.
- A UTC datetime derived from the source page's displayed GMT offset.
- Explicit latitude and longitude.
- `timezone: Etc/GMT+0`, so the benchmark uses the stored UTC instant rather than live timezone resolution.
- `house_system_code: R`, matching the existing trait benchmark convention.

The executable data lives in source:

```text
backend/trait_logic_benchmark_profiles.py
```

## Pass Criteria

Two suites now exist.

### Route Coverage Suite

For every one of the 68 baseline candidates:

- `/api/astro-clock/traits/profile` returns HTTP 200.
- The response contains at least 10 trait rows.
- The response contains at least 3 summary trait rows.

This suite records top summary traits for comparison, but does not assert biography correctness.

### Biography Correctness Suite

For every one of the 68 baseline candidates:

- A documented public-life theme is encoded as an expected trait cluster.
- At least one expected trait in that cluster must appear in summary traits with score `>= 30`.
- That expected trait must be ranked `<= 12`.

This is intentionally strict. A case fails when Trait Profile computes traits but does not surface the biographically relevant public-life theme prominently enough.

## Implementation

Runner:

```text
backend/trait_logic_benchmark_runner.py
```

New entry points:

```python
get_trait_public_figure_baseline_cases()
run_trait_public_figure_baseline_benchmark()
run_trait_public_figure_biography_benchmark()
render_public_figure_baseline_report()
render_public_figure_biography_report()
```

CLI:

```powershell
python backend\trait_logic_benchmark_runner.py --suite public-figures
python backend\trait_logic_benchmark_runner.py --suite public-figures-bio
python backend\trait_logic_benchmark_runner.py --suite public-figures --json
python backend\trait_logic_benchmark_runner.py --suite public-figures --output docs\TRAIT_PROFILE_PUBLIC_FIGURE_BENCHMARK_RUN_2026-05-07.md
python backend\trait_logic_benchmark_runner.py --suite public-figures-bio --output docs\TRAIT_PROFILE_PUBLIC_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md
```

Targeted sample:

```powershell
python backend\trait_logic_benchmark_runner.py --suite public-figures --case-id emmanuel_macron --case-id barack_obama
python backend\trait_logic_benchmark_runner.py --suite public-figures-bio --case-id albert_einstein
```

Tests:

```powershell
python -m pytest backend\test_trait_logic_benchmark_runner.py
```

## First Biography Run

Run file:

```text
docs/TRAIT_PROFILE_PUBLIC_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md
```

Result:

- Cases passed: 18/68
- Clusters passed: 18/68
- Result: FAIL

The dominant failure mode is not route failure. It is ranking failure: expected traits such as leadership, reform, humanitarianism, mediation, endurance, or artistic grace often exist in the profile but are ranked below generic or pathological traits.

## Next Calibration Step

Use the failed biography report to tune ranking and domain summarization before changing individual case expectations. The first correction should target summary ranking so public-life, profession, leadership, creativity, service, athletics, and humanitarian traits are not crowded out by generic/pathological traits when the benchmark asks for a public-figure profile.
