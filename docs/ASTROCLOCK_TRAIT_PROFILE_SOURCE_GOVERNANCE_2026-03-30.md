# Astro Clock Trait Profile Source Governance

Date: 2026-03-30

## Purpose

After the source-lineage audit, the next step was to make the summary logic use that lineage instead of only displaying it.

The target behavior is narrow:

- if two summary candidates are close in score
- and one is source-backed while the other is editorial
- prefer the source-backed candidate in the summary surfaces

This is not a full source-first rewrite. It is a tie-breaking governance layer.

## Why This Was Needed

Before this pass:

- the trait profile could show `source_lineage`
- but summary ordering still only cared about:
  - summary priority
  - raw score

That meant an editorial synthesis trait could outrank a classical or Carter-derived trait even when the scores were effectively in the same range.

For a curated trait profile, that is not the best default.

## Fix

Implemented in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`
- `frontend/src/features/astroclock/TraitProfileModal.jsx`

The summary selectors now use a bounded source-aware ordering:

- score is grouped into 5-point tiers
- inside the same score tier, source-backed lineages are preferred

Current lineage priority:

1. `morin`
2. `classical`
3. `carter`
4. `modern`
5. `editorial`
6. `provisional`

This keeps the score model primary while still letting source quality matter when two candidates are broadly comparable.

## What Changed In Practice

- bucket representatives in `top_traits` are now source-aware when scores are close
- `summary_traits` ordering is now source-aware
- frontend fallback ordering for polarity panels matches the backend logic

## Tests Added

Backend:

- `backend/test_trait_engine_contract.py`

Frontend:

- `frontend/src/tests/traitProfileModal.test.jsx`

These tests now verify that a classical summary trait can outrank an editorial one when the two are in the same score neighborhood.
