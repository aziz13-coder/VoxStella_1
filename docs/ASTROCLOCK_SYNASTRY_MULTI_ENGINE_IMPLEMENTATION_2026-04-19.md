# Astro Clock Synastry Multi-Engine Implementation

Date: 2026-04-19

## Summary

Synastry now supports four engine tabs behind the existing snap-to-snap workflow:

- `Memo`
- `Life Themes`
- `Union Dynamics`
- `Work Alliance`

The backend keeps a single `/api/astro-clock/synastry` route and selects the engine through `engine_id`.

## Source Basis

External source notes reviewed:

- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_engine_logic.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_common_helpers.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_canonical_fixtures.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_overall_logic.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_overall_agent_spec.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_marital_logic.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_marital_agent_spec.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_marital_validation.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_business_logic.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_business_agent_spec.md`
- `C:\Program Files (x86)\Galaxy\docs\research\compatibility_business_validation.md`
- `C:\Program Files (x86)\Galaxy\docs\research\README.md`

Confirmed source-backed mode split:

- full-house compatibility engine
- marital compatibility engine
- business compatibility engine

## Naming

UI labels intentionally avoid source-product naming.

- `Memo`
- `Life Themes`
- `Union Dynamics`
- `Work Alliance`

Internal ids:

- `memo`
- `life_themes`
- `union_dynamics`
- `work_alliance`

## Backend Shape

Implementation file:

- [backend/synastry_multi_engine.py](C:\Users\sabaa\Downloads\codexhorary\backend\synastry_multi_engine.py)

Route integration:

- [backend/astro_clock_api.py](C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py)

Contract:

- `engine_id=memo` returns the existing memo report
- structured engines return `report_kind=structured`
- every response now includes `engine_id`, `engine_label`, and `available_engines`

## Engine Mapping

### Memo

This remains the existing narrative report builder.

### Life Themes

Implements the documented full-house engine shape:

- `alaspT01..alaspT12`
- burden layer
- shared contact grid

Source notes describe full `GetAllAlmutens4House(...)` groups and fixed direct psychology pairs by house theme. The implementation preserves the direct theme-pair table and approximates the house groups from:
The implementation now uses the decoded helper exactly for the structured engines:

- ordered unique primary rulers for every zodiac sign crossed by the cusp arc
- inclusive forward span from cusp `n` to cusp `n+1`
- no occupants
- no angle injection
- no weighting

The overall burden layer now also follows the documented asymmetric pool:

- chart `0`: `Sun..Pluto`, `Ascendant`, house `1` representatives, objects physically in house `1`, and all `H1..H12` groups
- chart `1`: `Sun..Pluto`, `Descendant`, house `7` representatives, objects physically in house `7`, and all `H1..H12` groups
- fixed warning branch: houses `1..12`

### Union Dynamics

Implements the documented marital engine shape:

- `1-5-7` bond family
- `1-4` home family
- each split into psychology, role, and burdening
- shared contact grid

Because saved snaps do not currently persist explicit sex/profile metadata, the UI exposes:

- `Profile A`
- `Profile B`

Supported values:

- `Blended`
- `Feminine`
- `Masculine`

Current implementation status:

- `Feminine` and `Masculine` now use the exact decoded `alasp157P` and `alasp14P` hard-coded slot tables
- `alasp157B` and `alasp14B` now use the documented family-specific pools with the shared marriage-mode warning branch on house `5`
- role layers skip cosmogram charts, matching the source workflow
- `Blended` remains an app-side fallback when the source-side profile is not available from the saved snap

Profile defaults:

- if a snap carries `profile_hint` or `summary.profile_hint`, the modal now uses it automatically
- otherwise the selectors fall back to `Blended`

### Work Alliance

Implements the documented business house cluster:

- `1`
- `2`
- `6`
- `7`
- `10`

Current source basis:

- `compatibility_business_logic.md`
- `compatibility_business_agent_spec.md`
- `compatibility_business_validation.md`

Current implementation status:

- the theme table follows the dedicated business direct-pair mapping
- the role layer follows the documented `H1 <-> Hn` and `Hn <-> H1` business comparisons
- the house groups now use the decoded `GetAllAlmutens4House(...)` helper rather than the old proxy cache
- the burden layer follows the business-specific pool shape:
  - seed from the final `T10` direct pair state
  - merge houses `1`, `2`, `6`, `7`, `10`
  - apply fixed warning checks to houses `2`, `6`, `10`

## Frozen Snapshot Contract

Structured engines continue to respect the frozen snap contract.

Saved synastry snapshots now carry or recover:

- planets
- house cusps
- ascendant
- midheaven
- house rulers
- almutens

The backend still prefers the saved snapshot or saved dashboard payload before any recompute fallback.

## Frontend Shape

Main UI file:

- [frontend/src/features/astroclock/SynastryModal.jsx](C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\SynastryModal.jsx)

API client:

- [frontend/src/features/astroclock/api.mjs](C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs)

Behavior:

- top-level engine tabs switch the active synastry engine
- `Memo` keeps the original memo layout
- structured engines open into a workspace with an `Areas` page plus engine-specific section tabs
- the structured workspace now renders source-backed `MID` strings with astrology glyph support and row-level metadata
- the `Areas` page now renders the four-stripe diagram derived from the structured engine pools instead of a generic summary-card fallback
- `Union Dynamics` shows profile selectors only on that engine tab

## Known Gaps

- source-side sex/profile metadata is not yet guaranteed for every saved snap, so `Union Dynamics` still needs a `Blended` fallback when no hint is available
- parity is pinned to the decoded `B: Basic tool` fixture state; broader reversal and multi-instrument benchmarks are still not fully covered in repo tests
- the structured workspace still uses modern web layout conventions around the recreated stripe view, so it aims for functional parity rather than a pixel-identical legacy window chrome clone

## Verification

Targeted tests added or updated:

- [backend/test_synastry_multi_engine.py](C:\Users\sabaa\Downloads\codexhorary\backend\test_synastry_multi_engine.py)
- [backend/test_astro_clock_api_synastry.py](C:\Users\sabaa\Downloads\codexhorary\backend\test_astro_clock_api_synastry.py)
- [frontend/src/tests/synastryModal.test.jsx](C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\synastryModal.test.jsx)
- [frontend/src/tests/astroclockApi.test.mjs](C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs)
