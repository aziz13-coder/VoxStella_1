# Forensic Benchmarks

This folder stores source-backed forensic event benchmark datasets.

## Recent documentary development fixture

Dataset:

- `tests/fixtures/forensic_recent_documentaries_2025_2026_cases.json`

It adds four independently sourced cases: Netflix's July 2026 Idaho murders
series, Netflix's Titan documentary, the Astroworld Trainwreck documentary,
and the 2026 Costa Concordia documentary. Documentary listings establish the
screen title; court, police, government-safety, and transport-investigation
records establish the event anchors and outcomes. Interval midpoints and
response markers are labeled as proxies and are never described as exact
times of death.

Run only these cases:

```powershell
python backend\forensic_statistical_benchmark_runner.py `
  --dataset tests\fixtures\forensic_recent_documentaries_2025_2026_cases.json
```

## Forensic house-system default

Compare all eight supported systems on declared development data:

```powershell
python backend\forensic_house_system_selection_runner.py
```

The selector rejects locked holdouts, retrospective-evaluation datasets, and
datasets with no declared development role. Its composite is 60% labeled-axis
balanced accuracy, 30% survivability partial-credit accuracy, and 10%
relationship macro-F1. This is development model selection for a symbolic
engine, not prospective validation.

## Worst Roommate Ever

Dataset:

- `worst_roommate_ever_cases.json`

Run:

```powershell
python backend\forensic_roommate_benchmark_runner.py
python backend\forensic_roommate_benchmark_runner.py --json
```

The dataset includes all released Netflix `Worst Roommate Ever` episodes available as of 2026-05-13. Cases without a precise or tight public event time stay in the inventory as holdouts and are not replayed by the live route. Runnable cases use documented last-seen, welfare-check, dispatch, or probable-sequence anchors and label those anchors explicitly; they are not treated as fabricated death times.

## Locked known-outcome aviation holdout

Dataset:

- `tests/fixtures/forensic_known_outcome_aviation_holdout_v1.json`

Run the real route and compare every engine classification with the documented occupant outcome:

```powershell
python backend\forensic_statistical_benchmark_runner.py `
  --dataset tests\fixtures\forensic_known_outcome_aviation_holdout_v1.json
```

The eight NTSB-sourced cases are balanced between fatal-dominant and survival-dominant outcomes. This is a locked external stress set, not a scoring calibration set. Do not change rule weights to make these eight cases pass; add a new versioned holdout for future prospective evaluation.

## Survivability tuning

The tuning runner accepts only fixtures with an explicit development role and refuses locked, holdout, prospective, and retrospective-evaluation data:

```powershell
python backend\forensic_survivability_tuning_runner.py
```

It performs a deterministic candidate search with leave-one-family-out evaluation and never writes a selected policy. The current 12-case calibration set is too small and already saturated, so no numeric policy change is eligible for promotion.

The file `tests/fixtures/forensic_holdout_30_cases_2026_05_20.json` is a contaminated retrospective set, not an untouched holdout; repository calibration documentation records that it was previously used for rule tuning.
