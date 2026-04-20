# Astro Clock Synastry Benchmarking

## Scope

This benchmark path separates synastry evaluation into three tracks:

- `logic benchmarking`: stable chart-pair replay to measure score shape, directional asymmetry, and engine drift
- `predictive benchmarking`: ordered partner retrieval to measure where the known partner ranks inside a fixed candidate pool
- `work outcome benchmarking`: pair-level separation between `durable_success` and `productive_then_breakdown` work cases

The benchmark runner lives in [backend/synastry_benchmark_runner.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_benchmark_runner.py) and follows the same repo pattern used by the weather and transit benchmark modules.

## Why These Tracks

The models are doing two different jobs:

- `Memo` and the structured engines must remain internally coherent and stable on frozen chart pairs
- benchmark-side partner retrieval needs a single scalar per engine so old and new models can be compared on the same ranking task
- the work engine also needs an outcome-aware read so durable business pairs can be compared against productive pairs that later broke down

Treating those as one blended test would hide whether a regression came from:

- chart loading
- directional asymmetry
- aggregation choice
- retrieval quality
- outcome separation quality

## Logic Track

The logic track replays frozen chart-data fixtures and records:

- forward score
- reverse score
- absolute reverse delta
- structured totals where present: `theme_total`, `aspect_total`, `burden_total`

Current logic models:

- `memo_overall_score`
- `life_themes_composite_total`
- `union_dynamics_composite_total`
- `work_alliance_composite_total`

Default logic fixtures:

- [synastry_historical_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1.json)
- [synastry_historical_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_2.json)
- [synastry_historical_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_3.json)

## Predictive Track

The predictive track uses ordered candidate retrieval. For each case:

1. load the anchor chart
2. load a fixed candidate pool
3. score every anchor-candidate pair
4. rank candidates by the selected benchmark scalar
5. record where the known partner lands

Primary metrics:

- `top-1 hit rate`
- `top-3 hit rate`
- `MRR`
- `mean rank`

Directional diagnostic:

- `mean_abs_reverse_delta`

## Work Outcome Track

The work outcome track is separate from collaborator retrieval.

It answers a different question:

- retrieval asks whether the true collaborator ranks highly inside a candidate pool
- outcome asks whether the engine gives stronger pair scores to `durable_success` work pairs than to `productive_then_breakdown` work pairs

This track operates on the already-scored true work pairs and then groups them by unordered pair id, so `A -> B` and `B -> A` are treated as one collaboration pair.

Current outcome labels:

- `durable_success`
- `productive_then_breakdown`

Primary metrics:

- `mean_durable_pair_score`
- `mean_breakdown_pair_score`
- `durable_minus_breakdown_mean`
- `pairwise_win_rate`
- `pairwise_tie_rate`

`pairwise_win_rate` is the key separation metric. It compares every durable pair score against every breakdown pair score. A random or non-separating model should drift around `0.5`.

## Model Scoping

Do not mix the structured engines into the wrong task family.

Use these predictive comparisons:

- `overall` cases:
  - `memo_overall_score`
  - `memo_legacy_score`
  - `life_themes_theme_total`
  - `life_themes_aspect_total`
  - `life_themes_composite_total`
- `union` cases:
  - `memo_overall_score`
  - `union_dynamics_theme_total`
  - `union_dynamics_aspect_total`
  - `union_dynamics_composite_total`
- `work` cases:
  - `memo_overall_score`
  - `work_alliance_theme_total`
  - `work_alliance_aspect_total`
  - `work_alliance_composite_total`

`random_expected` is included as a deterministic sanity floor.

## Dataset Support

Predictive datasets support three person sources:

- `chart_data`: embedded chart payloads for deterministic repo fixtures
- `raw`: public-source birth data with compact coordinates and UTC offset token
- `bank`: Galaxy local bank rows via `bank_000.dbf`

The validator lives in [backend/validate_synastry_benchmark_datasets.py](C:/Users/sabaa/Downloads/codexhorary/backend/validate_synastry_benchmark_datasets.py).

Default predictive datasets:

- external overall pilot when available:
  - [compatibility_public_pairs.json](</C:/Program Files (x86)/Galaxy/docs/research/compatibility_public_pairs.json>)
- repo real-public union/work expansion:
  - [real_public_pairs.json](C:/Users/sabaa/Downloads/codexhorary/backend/benchmarks/synastry/real_public_pairs.json)

Repo deterministic predictive sample:

- [predictive_pairs_sample.json](C:/Users/sabaa/Downloads/codexhorary/backend/benchmarks/synastry/predictive_pairs_sample.json)

Repo sample logic fixture:

- [synastry_benchmark_logic_fixture.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_benchmark_logic_fixture.json)

The sample predictive dataset is only for deterministic tests and smoke checks. The default benchmark path is now real-case first.

## Memo Headline Hardening

The benchmark now keeps two memo-side overall models:

- `memo_overall_score`: the live memo headline score used by the narrative report
- `memo_legacy_score`: the previous component-blend formula preserved as a benchmark baseline

The live headline now uses doctrine-level category weights instead of the older component blend that leaned too hard on raw support-volume and a second reception bonus.

Source basis for the hardening:

- the memo catalog's `compatibility_conflict_gate` says compatibility should reflect lived ease, not just significance, compensation, or binding force when hard themes dominate
- `mutual_reception_support` already contributes to memo categories, so the old headline was double-counting willingness by adding a separate reception bonus
- the benchmark notes in [compatibility_benchmark_plan.md](</C:/Program Files (x86)/Galaxy/docs/research/compatibility_benchmark_plan.md>) and [compatibility_baseline_logic.md](</C:/Program Files (x86)/Galaxy/docs/research/compatibility_baseline_logic.md>) both warn that broader aggregates should downweight noisy contribution instead of assuming the most dramatic full aggregate is the best ranking scalar

Current live memo headline formula:

- `0.26 * compatibility`
- `1.2 * communication`
- `0.12 * attachment`
- `0.18 * attraction`
- `-0.06 * friction`
- `-0.4 * burden`
- then pass the weighted total through a sigmoid normalizer centered at `40` with scale `18`

The intent is general:

- raise lived-ease signal
- keep a light bond signal
- penalize overt conflict and chronic heaviness directly
- stop saturating the headline at `100` just because the linear sum spilled over the display cap
- avoid double-counting saturated activity terms such as `growth`, raw support-volume balance, and a second reception bonus

Current public-`overall` read after the live headline change:

- `memo_overall_score`: top-1 `0.4000`, top-3 `0.6000`, `MRR 0.5900`
- `memo_legacy_score`: top-1 `0.0000`, top-3 `0.2000`, `MRR 0.2200`

So the live memo headline is materially better than the legacy memo blend on public partner retrieval, even though `Life Themes theme_total` remains stronger overall.

## Real-Case Benchmarking

Real-case benchmarking in this repo means:

1. keep `overall`, `union`, and `work` as separate retrieval families
2. use public figures with explicit source citations or clearly public Galaxy bank examples
3. score a fixed candidate pool instead of trying to predict free-form relationship success
4. benchmark the ranking, not the prose

Current default real-case coverage:

- `overall`: `5` public pilot cases from the external overall benchmark file
- `union`: `6` real public partner cases from the repo local expansion file
- `work`: `10` real public collaboration cases from the repo local expansion file

The work expansion now includes:

- durable-success business pairs such as `Warren Buffett / Charlie Munger`
- productive-then-breakdown founder pairs such as `Elon Musk / Sam Altman`

This keeps the benchmark honest about task scope:

- `Life Themes` is measured on general partner retrieval
- `Union Dynamics` is measured on partner and marriage-style retrieval
- `Work Alliance` is measured on collaboration retrieval

The work outcome track then asks a second question on that same work subset:

- does the work model score durable collaborations above collaborations that later fractured?

If you want to benchmark narrative output later, do it as a second track with blind review and a rubric. Do not mix narrative grading into the scalar retrieval metrics.

## Commands

Validation only:

```powershell
python backend/validate_synastry_benchmark_datasets.py
```

Full benchmark, markdown output:

```powershell
python backend/synastry_benchmark_runner.py
```

Full benchmark, JSON output:

```powershell
python backend/synastry_benchmark_runner.py --json
```

Run against repo-only deterministic fixtures:

```powershell
python backend/synastry_benchmark_runner.py `
  --predictive-dataset backend/benchmarks/synastry/predictive_pairs_sample.json `
  --logic-fixture tests/fixtures/synastry_benchmark_logic_fixture.json
```

Run the deterministic work-outcome fixture:

```powershell
python backend/synastry_benchmark_runner.py `
  --predictive-dataset backend/benchmarks/synastry/predictive_work_outcome_sample.json `
  --logic-fixture tests/fixtures/synastry_benchmark_logic_fixture.json
```

Pin a different house system for raw and bank chart casting:

```powershell
python backend/synastry_benchmark_runner.py --house-system-code P
```

## Current Limits

- The public-pair benchmark depends on local chart-casting availability and Galaxy bank access for bank-backed people.
- The predictive benchmark compares old vs new only within the correct task family; it does not pretend `Union Dynamics` or `Work Alliance` are universal partner-retrieval models.
- Several real public cases are still culturally strong examples rather than laboratory-clean labels. A real collaboration case can still include romance overlap or celebrity-noise effects.
- The work outcome track is only as strong as its public outcome labels. It is useful for separation, not as a final causal model of why a collaboration endured or broke.
- The benchmark currently measures scalar ranking quality, not prose quality. If narrative-output benchmarking is needed later, add a separate blind-review track instead of mixing it into score retrieval.
