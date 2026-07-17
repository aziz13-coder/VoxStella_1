# Forensic Benchmarks

This folder stores source-backed forensic event benchmark datasets.

## Worst Roommate Ever

Dataset:

- `worst_roommate_ever_cases.json`

Run:

```powershell
python backend\forensic_roommate_benchmark_runner.py
python backend\forensic_roommate_benchmark_runner.py --json
```

The dataset includes all released Netflix `Worst Roommate Ever` episodes available as of 2026-05-13. Cases without a precise or tight public event time stay in the inventory as holdouts and are not replayed by the live route. Runnable cases use documented last-seen, welfare-check, dispatch, or probable-sequence anchors and label those anchors explicitly; they are not treated as fabricated death times.
