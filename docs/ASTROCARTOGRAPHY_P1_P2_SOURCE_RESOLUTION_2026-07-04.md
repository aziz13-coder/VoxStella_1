# Astrocartography P1/P2 Source Resolution - 2026-07-04

This note documents the source-code fixes for four astrocartography PathFinder issues found in the app review.

## Chiron computation and selection

Runtime goal models already score Chiron lines in health, protection, and accident-pressure models, but the backend body registry and frontend filter list did not expose Chiron. The source now includes Chiron in `DEFAULT_BODIES`, `PLANET_IDS`, color/priority metadata, and the Astrocartography modal body selector.

Swiss Ephemeris can require an asteroid ephemeris file for Chiron. To keep Chiron computable in builds where that file is absent, `astrocartography_service.py` still prefers `swe.calc_ut` but falls back to a scoped low-precision Chiron position computed from NASA/JPL SBDB orbital elements for 2060 Chiron, solution 171, epoch JD 2461200.5, J2000 equinox.

The body normalizer no longer broadens an explicit invalid-only body filter back to all default bodies. A request for only Chiron now produces only Chiron lines; a request for only unsupported bodies produces no lines.

Reference: https://ssd-api.jpl.nasa.gov/sbdb.api?sstr=Chiron&full-prec=true

## Full scoring rows for goal models

Location analysis and atlas candidate scoring now separate compact display readings from scoring inputs. Display payloads still use the existing nearest-line limit, but `build_goal_scoring_context` provides untruncated nearest-line rows and crossings to `evaluate_goal_model`.

This prevents a configured model component from being skipped just because its relevant line was not among the top 8 nearest display rows.

## Schema/runtime alignment

`place_goal_model.schema.json` now accepts the runtime model extensions already used by the live model file:

- `evaluation_strategy: "gambling_natal_curated"`
- `atlas_search_filters`
- `atlas_shortlist_strategy`
- `atlas_relocation_prepass_limit`
- newer gambling modifier metrics such as `asc_ruler_strength`, `gambling_ruler_strength`, and Moon/liability/support metrics

A regression test compares runtime strategies, top-level atlas fields, and modifier metrics against the schema.

## Atlas relocation prepass

Explicit relocation-heavy atlas models, including gambling models that declare `atlas_shortlist_strategy: "relocation_prepass"` or use relocation-aware evaluation strategies, now relocation-score the full candidate pool before final shortlisting.

Generic relocation-aware models without an explicit relocation-heavy strategy still use the existing bounded expanded prepass behavior.

## Source mirrors

The backend changes were applied to both source trees used by this repository:

- `backend/**`
- `frontend/backend/**`

Generated/package output paths remain untouched.
