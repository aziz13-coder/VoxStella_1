# Astro Clock Trait Profile: Source Restoration And Scoring Audit

Date: 2026-03-29

## What Was Restored

Two enrichment sources referenced by the trait engine were missing in the repo:

- `backend/traits/knowledge/morin_keywords.json`
- `backend/Phsychology traits/astrology_dictionary_starter.csv`

They are now restored and mirrored into the packaged-source twin:

- `frontend/backend/traits/knowledge/morin_keywords.json`
- `frontend/backend/Phsychology traits/astrology_dictionary_starter.csv`

## Runtime Fixes

The engine was also too narrow in how it searched for those files.

Updated:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`

New behavior:

- search backend-relative paths
- search `cwd`
- search `cwd/backend`
- search `HORARY_BACKEND_DIR`
- search frozen `_MEIPASS`
- search the frozen executable directory

This makes the restoration survive:

- local source runs
- packaged-source runs
- PyInstaller-style frozen backend layouts

## Build Fix

The backend build script now explicitly bundles the restored trait data:

- `backend/build_backend.py`

Added packaging inputs:

- `traits/catalog`
- `traits/traits.json`
- `traits/knowledge`
- `Phsychology traits`

Without that change, the packaged app could have remained degraded even after the source restoration.

## Source Comparison

### Morin keyword JSON

This file is intentionally compact and non-scoring.

It is based on:

- the repo’s Morin transit source summary
- the compact Morin house baseline already documented from Book 22
- Book 24’s rule that a transiting planet acts by:
  - its own nature
  - radical determination
  - current celestial state

What is tightly Morin-facing:

- house keywords

Examples:

- 1st: life, temperament, health
- 7th: marriage, contracts, open enemies
- 10th: action, profession, dignity
- 12th: sickness, imprisonment, secret enemies

What is intentionally compact rather than exhaustive quotation:

- planet keyword tags
- sect keyword tags

Those are operational labels for enrichment, not direct textual claims that Morin used those exact tag phrases.

### Guidance CSV

This file is a starter guidance layer for:

- Planet
- Sign
- House
- Aspect

Source grounding:

- Houses are aligned to the Morin baseline used elsewhere in the repo.
- Signs and many trait families remain Carter-heavy in the trait catalog itself, so the starter sign/planet guidance is deliberately aligned to the catalog’s existing classical/Carter framing rather than pretending to be pure Morin.

That is the honest design:

- houses = strongly Morin-facing
- signs/planets/aspects = compact classical starter guidance compatible with the current trait catalog

## Scoring Audit

## Important distinction

The restored files are non-scoring enrichment.

They affect:

- derived trait keywords
- guidance suggestions

They do not directly affect:

- condition weights
- total trait scores
- band thresholds

### What was audited

Current scoring behavior in `TraitEngine.evaluate(...)`:

- trait weights remain driven by the JSON rule files
- `traits` are still included from `min_score >= 18`
- bands remain:
  - `strong >= 70`
  - `likely >= 50`
  - `possible >= 30`
  - `weak < 30`

### Real issue found

The previous `top_traits` selection could surface weak-band traits even when stronger traits were available.

That was corrected.

New behavior:

- prefer non-weak traits for `top_traits` when any exist
- fall back to weak traits only when no stronger traits are available

This is the only scoring-selection change made in this pass.

### What was not changed

The underlying rule weights were not recalibrated in this pass.

Reason:

- the trait catalog is still largely Carter-derived
- restoring Morin keywords/guidance does not by itself justify changing the Carter-era weight schema
- a real weight recalibration would require auditing the trait JSON catalog itself, not just the enrichment layer

### Practical outcome

After restoration:

- keywords are now source-backed and non-empty
- guidance is now real and visible
- top-trait selection is less misleading when higher-confidence bands exist
- weak-only charts can still return weak top traits if the chart simply does not generate stronger indications

That last point is currently accepted behavior, not a bug.

## Verification

Backend:

- `python -m pytest backend\test_trait_engine_contract.py tests\test_trait_profile_route_contract.py -q`
- result: `5 passed`

Frontend:

- `npm exec vitest run src/tests/traitProfileModal.test.jsx --config vitest.config.mjs`
- result: `2 passed`

Build:

- `npm run build`
- result: passed

## Current Status

The missing enrichment layer is restored.

The trait profile feature is now more correct in three ways:

1. source-backed keyword enrichment exists again
2. guidance suggestions exist again
3. top-trait selection is less misleading when stronger bands exist

The next trait-profile pass, if needed, should not be another restoration pass.

It should be a curated audit of the actual trait rule catalog:

- representative traits
- source fidelity per trait
- weight calibration
- polarity semantics
