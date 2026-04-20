# Astrocartography Atlas Resolution Slice

Date: 2026-04-04

## Purpose

This slice turns atlas search into a user-tunable best-city scan instead of one fixed-density pass.

The user can now choose how broad the candidate pool should be before the PathFinder engine applies line, crossing, and relocation scoring.

## Why Resolution Matters

The app's shared location service is still useful:

- `backend/horary_engine/services/geolocation.py`
- `/api/get-timezone`

It remains the right tool for:

- geocoding a single inspected city
- resolving timezone data
- supporting relocation chart casts for a shortlist

It is not the right tool for:

- generating thousands of candidates on demand
- controlling best-city search breadth

That is why atlas search continues to use the shipped local city catalog while the location service stays in the shortlist path.

## Resolution Presets

Search resolution is now explicit and source-backed by the local GeoNames-derived atlas catalog:

- `Coarse`
  - capitals, admin centers, and ordinary cities with population `>= 500000`
  - current catalog count: about `2872`
- `Standard`
  - capitals, admin centers, and ordinary cities with population `>= 200000`
  - current catalog count: about `3472`
- `Fine`
  - capitals, admin centers, and ordinary cities with population `>= 80000`
  - current catalog count: about `5463`

The shipped runtime catalog is now built at the `Fine` baseline so the backend can filter down to `Standard` or `Coarse` without swapping files.

## Backend Changes

- `scripts/build_astrocartography_city_catalog.py`
  - now builds the runtime catalog at the fine baseline
- `backend/astrocartography_city_catalog.py`
  - defines atlas resolution presets
  - filters candidate cities by resolution
- `backend/astrocartography_atlas_engine.py`
  - accepts `resolution`
  - varies shortlist depth by resolution
- `backend/astro_clock_api.py`
  - accepts `resolution` on `/api/astro-clock/astrocartography/atlas-search`
  - returns resolution metadata in the atlas payload

## Frontend Changes

`frontend/src/features/astroclock/AstrocartographyModal.jsx` now exposes a `Search resolution` selector in the `Search Atlas` form.

The modal keeps the same design language as the rest of Astro Clock:

- no new top-level surface
- no detached settings drawer
- same left-rail form grammar as the other controls

## Current Product Shape

The user can now choose between:

- a faster broad-strokes search
- a balanced default search
- a denser city scan for narrower or less obvious matches

This keeps the best-city engine explainable and responsive while letting the user decide how aggressively the atlas should search.
