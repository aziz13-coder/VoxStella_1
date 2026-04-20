# Astrocartography Atlas Search Slice

Date: 2026-04-04

## Purpose

This slice adds the first atlas-style "best city" search on top of the Astrocartography PathFinder engine.

It also documents what the app's existing location service can and cannot do for this task.

## Existing Location Service

The app already had a useful shared location stack:

- `backend/horary_engine/services/geolocation.py`
  - `safe_geocode(...)`
  - `TimezoneManager`
- `backend/app.py`
  - `/api/get-timezone`
- frontend location helpers in `frontend/src/App.jsx`

What this existing service helps with:

- turning one user-entered place string into coordinates
- resolving timezone labels from coordinates
- caching repeated geocode and timezone requests
- supporting relocation chart casts for a small shortlist of candidate cities

What it does not provide:

- a local searchable atlas corpus
- bulk candidate generation
- a practical way to score thousands of cities by repeatedly geocoding them one by one

Conclusion:

- keep using the existing location service for inspect flows and shortlisted relocation casts
- add a local city catalog for atlas search candidate discovery

## Atlas Catalog

New builder:

- `scripts/build_astrocartography_city_catalog.py`

New runtime asset:

- `backend/knowledge/astrocartography/city_catalog.runtime.json`

Current catalog shape:

- source: GeoNames `cities15000`
- always include:
  - `PPLC`
  - `PPLA`
- include ordinary cities (`PPL`) only when population is at least `200000`

That produces a medium-size atlas corpus suitable for live ranking rather than a full raw dump.

## Atlas Engine

New modules:

- `backend/astrocartography_city_catalog.py`
- `backend/astrocartography_atlas_engine.py`

The engine works in two passes:

1. Candidate pass
   - search the local city catalog
   - derive goal-relevant bodies and angles
   - score each city by nearby lines and nearby crossings

2. Shortlist pass
   - keep the top candidate set
   - cast relocation charts only for the shortlist
   - rerun the goal model with relocation scoring included

This keeps the search practical and allows the existing geocoding/timezone service to help where it adds value.

## API

New endpoint:

- `/api/astro-clock/astrocartography/atlas-search`

Inputs:

- required:
  - `goal_id`
  - natal source params
- optional:
  - `query`
  - `country_code`
  - `limit`
  - transit context
  - body/angle filters

Outputs:

- atlas query metadata
- candidate and shortlist counts
- ranked best-match results
- per-result target payload
- nearby natal and transit readings
- nearby crossings
- relocation summary
- weighted goal score

## Frontend

The Astrocartography modal now includes:

- a `Search Atlas` form in the left rail
- a `Best Matches` section in the right rail
- actions to:
  - inspect a ranked city
  - add a ranked city directly to the compare tray

## Current Boundary

This is a real atlas search layer, but it is still lexical and catalog-bound:

- it does not yet understand continent polygons or custom radius searches
- it does not yet search every possible town on Earth
- it ranks against the shipped medium-size catalog only

That is the correct tradeoff for this product slice because it keeps searches fast and explainable while reusing the app's existing location service where it is strongest.
