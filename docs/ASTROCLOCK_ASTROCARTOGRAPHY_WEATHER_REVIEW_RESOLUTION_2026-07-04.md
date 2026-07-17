# AstroClock Astrocartography and Weather Review Resolution - 2026-07-04

## Scope

Reviewed AstroClock source logic for astrocartography PathFinder scoring, weather forecast resolution, weather scans, and the seed weather family models.

Runtime source twins under `backend/` and `frontend/backend/` were kept aligned. Generated Electron, dist, website, venv, and node_modules paths were not edited.

## Resolved Issues

1. Weather forecast datetimes now interpret naive UI timestamps as local to the requested timezone before converting to UTC. This applies to single weather analysis and place timeline scans.
2. Weather context resolution now preserves explicit `0.0` latitude and longitude values instead of falling back to the active AstroClock location.
3. Flood-risk lunar and forecast angular moisture rules now populate `trigger_notes`; only seasonal ingress moisture rules populate `framework_notes`.
4. Astrocartography goal scoring now excludes `kind="blend"` candidates from exact crossing components and crossing heuristics. Missing `kind` is still treated as an exact crossing for legacy payload compatibility.
5. Weather scan sessions now follow the atlas-search session pattern with terminal-session TTL and max-count pruning.

## Verification

Added regression coverage for local-time weather normalization, place scan timepoints, explicit zero coordinates, flood trigger buckets, exact-crossing-only goal scoring, and weather scan session pruning.
