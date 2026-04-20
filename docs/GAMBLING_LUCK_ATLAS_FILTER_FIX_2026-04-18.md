# Gambling Luck Atlas Filter Fix

Date: 2026-04-18

## Problem

Running Astrocartography atlas search with the `Gambling Luck` goal could fail with:

- `Current body/angle filters exclude the selected goal model`

That message was misleading for the common case where all visible body and angle checkboxes were still enabled.

## Root Cause

Atlas search derives its compatible body and angle set from a goal model's `line` and `crossing` score components in `backend/astrocartography_atlas_engine.py`.

`gambling_luck` was intentionally rebuilt as a curated natal-relocation scorer and now uses only relocation `modifier` metrics in `backend/knowledge/astrocartography/place_goal_models.runtime.json`.

That meant:

1. The goal had no atlas-search signature under the old derivation logic.
2. `derive_goal_search_filters('gambling_luck')` returned empty bodies and angles.
3. The backend raised a filter-exclusion error even though the user's visible filters were not the real cause.

There was a second logic gap as well: when the user selected bodies or angles with zero overlap, the helper silently fell back to the goal's full signature instead of treating that as a real exclusion.

## Fix

Implemented three changes:

1. Added explicit `atlas_search_filters` to the `gambling_luck` goal model.
2. Updated atlas filter derivation to support explicit atlas signatures for relocation-scored specialist goals.
3. Changed filter handling so real zero-overlap user selections are treated as exclusions rather than silently ignored.

## Atlas Signature

`gambling_luck` now declares the atlas proxy set below for map-line generation and atlas candidate scanning:

- Bodies: `Moon`, `Mercury`, `Venus`, `Mars`, `Jupiter`, `Saturn`, `Neptune`
- Angles: `ASC`, `MC`, `IC`

This does not change the curated relocation scoring model itself. It only gives atlas search a compatible line set to build the scan around.

## Error Behavior After Fix

The backend now distinguishes between two states:

1. Goal missing atlas signature:
   - `Selected goal model is not configured for atlas-search line filtering yet`
2. User filters truly exclude the goal signature:
   - `Current body/angle filters exclude the selected goal model's atlas signature`

## Files

- `backend/astrocartography_atlas_engine.py`
- `backend/astro_clock_api.py`
- `backend/knowledge/astrocartography/place_goal_models.runtime.json`
- `backend/test_astrocartography_atlas_engine.py`
- `backend/test_astro_clock_api_astrocartography.py`

## Verification

Run:

- `python -m pytest backend/test_astrocartography_atlas_engine.py backend/test_astro_clock_api_astrocartography.py -q`

Expected outcomes:

- `gambling_luck` returns a non-empty atlas-search signature.
- Restrictive zero-overlap body/angle selections fail with the new precise exclusion message.
- Normal atlas search for `gambling_luck` no longer fails because the model lacks a line signature.
