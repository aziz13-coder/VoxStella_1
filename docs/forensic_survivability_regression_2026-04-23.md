# Forensic Survivability Regression - 2026-04-23

## Context

The Astro Clock forensic route builds a dashboard-style chart payload, extracts forensic features, evaluates YAML rules, and then computes survivability. The route historically used the chart data produced by the horary engine as its truth source.

Recent Astro Clock dashboard work added synthetic modern-body enrichment inside `_build_dashboard_payload()` whenever `include_modern=True`. That is useful for UI tiles that need Uranus, Neptune, and Pluto even when the base chart payload does not include them.

## Regression

The forensic route also calls `_build_dashboard_payload(..., include_modern=True)`. After synthetic modern-body enrichment was added, forensic feature extraction began seeing additional modern-body placements and derived water/abduction signals. That changed survivability calibration for nonfatal survivor benchmarks.

Observed focused-suite failures before the fix:

- `reagan_assassination_attempt_survived` classified as `Lower / fatal_pressure_dominant`.
- `john_paul_ii_assassination_attempt_survived` classified as `Lower / fatal_pressure_dominant`.

Both are known nonfatal violent-event benchmarks and should remain outside the fatal band.

## Fix Direction

At the time of this April regression fix, `_build_dashboard_payload()` exposed `extend_modern_chart_data` so consumers could opt out of synthetic modern-body enrichment.

## Current behavior

This historical note no longer describes the live route. The forensic route now intentionally passes `extend_modern_chart_data=True`, and the route contract test requires modern-body placements and precise aspects to reach feature extraction. Treat any calibration numbers in this note as historical; use the current statistical benchmark and locked known-outcome holdout for present behavior.

Regression command:

```powershell
python -m pytest tests\test_forensic_route_contract.py tests\test_forensic_homicide_documentary_probe.py tests\test_forensic_homicide_season3_probes.py tests\test_forensic_survivability_stratified_benchmark.py -q
```
