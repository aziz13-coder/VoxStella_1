# Astrocartography Paran Layer

Date: 2026-04-04

## Purpose

This slice continues the Astrocartography parity work by resolving the largest remaining gap in the Intersections workspace: the old implementation only exposed geometry-based crossings and blended proximity. It did not yet expose a real paran layer.

## What Was Added

### 1. Target-Based Paran Engine

Implemented a target-based paran engine in `backend/astrocartography_service.py`.

New backend function:

- `build_paran_candidates_for_point(...)`

The current model:

- uses the actual body `RA` / `Dec` values at the selected moment
- derives target-latitude angular event `LST` values for:
  - `ASC`
  - `DSC`
  - `MC`
  - `IC`
- compares horizon events against meridian events across body pairs
- detects coincident angular events within a configurable orb
- projects the resulting paran point onto the target latitude and computes its distance from the inspected city

This makes the paran layer astronomical and event-based rather than purely geometric.

### 2. API Integration

Astrocartography target analysis now returns `parans` under both natal and transit contexts in `backend/astro_clock_api.py`.

The report builder in `backend/astrocartography_service.py` also now incorporates parans as their own report section and lead-card candidate.

### 3. Frontend Integration

The `Intersections` workspace in `frontend/src/features/astroclock/AstrocartographyModal.jsx` now displays:

- geometry crossings as one layer
- parans as a separate layer
- distinct markers and counts for each

The right inspector also now reads as `Parans / Intersections` rather than showing geometry-only crossing cards.

## What This Resolves

Before this slice:

- the feature had useful crossing logic
- but it did not yet offer a real paran concept

After this slice:

- the user can inspect nearby astronomical parans for a city
- the UI distinguishes parans from geometry intersections
- the delineation report can mention paran structure explicitly

## Important Boundary

This is a real paran layer, but it is still a target-based paran engine, not full legacy-suite parity.

What it does now:

- evaluates paran coincidence at the inspected latitude
- surfaces nearby paran points relative to the target city
- supports natal and transit contexts

What it does not yet do:

- generate a full global paran map network
- replace the entire geometry-first intersections surface with a purely paran-native cartographic model
- claim exact Almagest formula parity

So this closes the "no real paran layer" gap, but not the entire "full paran cartography suite parity" gap.

## Verification

Validated in this slice with:

- backend tests:
  - `backend/test_astrocartography_service.py`
  - `backend/test_astrocartography_goal_engine.py`
  - `backend/test_astrocartography_atlas_engine.py`
- frontend lint:
  - `AstrocartographyModal.jsx`
  - `api.mjs`
- production build smoke verification with Vite

