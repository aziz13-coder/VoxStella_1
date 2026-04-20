## Astrocartography Remaining Gaps Resolved

Date: 2026-04-04

This memo records the parity-expansion step that closes the major remaining
implementation gaps after the first Astrocartography alpha.

### What was missing before this slice

- The map endpoint only exposed angular lines. Paran logic existed only as a
  target-based point analysis and not as a global cartography layer.
- Local Space existed as a set of rays, but not yet as a richer technique
  workspace with directional sectors, range context, and clearer interpretation.
- Atlas search was still bounded by the shipped catalog and could not reach
  outside it except through manual single-city inspection.
- The productized goal models were source-backed and explicit, but not exact
  recovered legacy formulas from the old Almagest file grammar.

### What is resolved in code now

#### 1. Global paran cartography

Implemented in:

- `backend/astrocartography_service.py`
- `backend/astro_clock_api.py`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

New behavior:

- The map payload now includes `global_parans` for the natal map and
  `transit_global_parans` for the optional transit overlay.
- These are latitude-sampled paran corridors, not just target-local paran
  hits.
- The frontend exposes them as a dedicated map overlay toggle so the user can
  inspect paran cartography without losing the core line map.

Result:

- The feature now supports a real paran cartography layer rather than only
  target-based paran points.

#### 2. Deeper Local Space parity

Implemented in:

- `backend/astrocartography_service.py`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

New behavior:

- Local Space is now surfaced through `build_local_space_workspace`, which
  enriches the ray payload with:
  - dominant compass sectors
  - range rings
  - peak rays
  - shadow rays
  - orientation notes
- The Local Space workspace now renders map rings and sector summaries rather
  than only bare rays.
- The inspector also surfaces sector summaries and ray-specific interpretation.

Result:

- Local Space now behaves like a real technique workspace instead of a thin
  geometric add-on.

#### 3. Denser atlas coverage and live query augmentation

Implemented in:

- `scripts/build_astrocartography_city_catalog.py`
- `backend/knowledge/astrocartography/city_catalog.runtime.json`
- `backend/astrocartography_city_catalog.py`
- `backend/astrocartography_atlas_engine.py`
- `backend/horary_engine/services/geolocation.py`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

New behavior:

- The shipped runtime atlas has been rebuilt from the GeoNames `cities15000`
  source at a denser threshold and now contains `20,636` cities.
- Atlas resolutions now include:
  - `Coarse`
  - `Standard`
  - `Fine`
  - `Ultra`
- `Ultra` uses the deepest shipped atlas scan and also augments typed queries
  with live Nominatim search candidates.
- The UI labels this as `Atlas+` when live augmentation contributes candidates.
- The map workspace can now plot the best-match atlas results as pins.

Reference smoke result after rebuild:

- `JP` candidate counts expanded to:
  - `coarse = 49`
  - `standard = 55`
  - `fine = 73`
  - `ultra = 517`

Result:

- Best-city search is no longer effectively capped by the earlier `5,463`-city
  corpus.
- Typed searches can now reach beyond the shipped atlas when the user needs a
  less common location.

### What is still not exact parity

One important boundary remains and should be stated plainly:

- The Vox Stella PathFinder models are transparent, explicit, source-backed
  models.
- They are not exact recovered Almagest formulas.

Why:

- The legacy application exposes visible presets and hidden rule-pack files,
  but the exact runtime binding and numeric weighting grammar were not fully
  recoverable from the available assets alone.
- We can infer model families, semantics, and intent from `.PLS` / `.HYP`
  files and from product behavior.
- We cannot honestly claim byte-level or formula-level equivalence without
  direct recovered runtime formulas or a larger observed I/O corpus from the
  original app.

Current product stance:

- preserve the product shape
- preserve the goal families
- preserve the astrological intent
- replace opaque formulas with explicit, inspectable Vox Stella scoring rules

### Verification

Passed during this slice:

- `python -m py_compile backend/astrocartography_service.py backend/astro_clock_api.py backend/astrocartography_city_catalog.py backend/astrocartography_atlas_engine.py backend/horary_engine/services/geolocation.py scripts/build_astrocartography_city_catalog.py`
- `python -m pytest backend/test_astrocartography_service.py backend/test_astrocartography_atlas_engine.py backend/test_astrocartography_goal_engine.py`
- `npm run test:unit`
- `npx eslint src/features/astroclock/AstrocartographyModal.jsx src/features/astroclock/api.mjs`
- `npx vite build --outDir C:\Users\sabaa\AppData\Local\Temp\codexhorary-astrocartography-gap-verify`

### Product status after this step

Astrocartography is now substantially closer to the reference-app shape:

- global angular map
- global paran cartography
- target inspection
- intersections workspace
- local space workspace
- delineation/report layer
- weighted PathFinder goals
- compare
- atlas search with resolution tiers
- denser atlas corpus
- live query augmentation

The remaining work is now refinement work rather than missing-system work.
