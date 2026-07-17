# Astrocartography PathFinder Logic Resolution - 2026-07-04

## Scope

Reviewed the AstroClock astrocartography PathFinder flow across:

- `backend/knowledge/astrocartography/place_goal_models.runtime.json`
- `backend/astrocartography_goal_engine.py`
- `backend/astrocartography_atlas_engine.py`
- `backend/astrocartography_service.py`
- `backend/astro_clock_api.py`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

The map marker shown over water is not caused by a Leaflet rendering rule. The modal plots the latitude/longitude returned by the backend atlas result. The root class of problems was that backend PathFinder contracts allowed incomplete model evidence or stale model semantics to reach the frontend as valid ranked candidates.

## Issues Resolved

### Relocated chart evidence omitted modern bodies and Chiron

`extract_relocation_features()` scores Uranus, Neptune, Pluto, and Chiron metrics for uncertainty, growth, restoration, health risk, and gambling subfeatures. The relocation chart bundle used by single-location, compare, and atlas scoring only returned the base chart bodies, so those relocation metrics were silently undercounted.

Resolution:

- Added optional `include_modern` and `include_chiron` enrichment to `_compute_chart_bundle_for()`.
- Wired relocation analysis and atlas relocation prepass to request modern bodies and Chiron.
- Shared the Chiron fallback ecliptic position from astrocartography line generation so relocated chart scoring can still compute Chiron when Swiss Ephemeris asteroid files are unavailable.

### Gambling atlas filters did not match the custom gambling scorer

The `gambling_luck` model uses the `gambling_natal_curated` strategy, whose hardcoded scorer reads Sun support plus Uranus and Pluto cautions. Its explicit `atlas_search_filters` did not include Sun, Uranus, Pluto, or DSC, so atlas searches could build a line set that omitted evidence the scorer expects.

Resolution:

- Expanded `gambling_luck.atlas_search_filters.bodies` to include Sun, Uranus, and Pluto.
- Expanded `gambling_luck.atlas_search_filters.angles` to include DSC.
- Updated tests so the model signature must cover the scorer's body/angle contract.

### Warning models were ranked and labeled as positive goals

`health_risk` and `accident_prone` state that higher scores are worse, but atlas ranking and compare sorting treated higher scores as better. The frontend also labeled warning output as "Best Cities" and "Goal score."

Resolution:

- Added explicit `score_polarity: "higher_is_worse"` metadata to active warning models.
- Added schema support for score polarity.
- Made atlas ranking and compare sorting rank lower scores first for higher-is-worse models.
- Exposed polarity through goal summaries and score payload goal metadata.
- Updated the modal to label warning searches as "Search Lowest Risk", "Lowest-risk pins", and "Risk score".

### Direct location/compare scoring allowed partial goal evidence

Atlas search already rejected selected body/angle filters that excluded a goal model signature. Direct location and compare analysis did not, so the same goal could be scored on incomplete evidence depending on endpoint.

Resolution:

- Added direct route validation using the same `describe_goal_search_filters()` contract as atlas search.
- Location and compare now reject selected filters that exclude the selected goal model signature.

### Goal-model generator could overwrite live semantics

`scripts/build_astrocartography_goal_models.py` contained an older Gambling Luck template and only wrote the backend runtime file. Regenerating could silently downgrade the live curated gambling model or desync the desktop source twin.

Resolution:

- Added required model-id validation.
- Added a guard that refuses to overwrite the curated `gambling_natal_curated` Gambling Luck runtime model with the stale template.
- Added polarity validation for active warning models.
- Updated the generator to write both `backend` and `frontend/backend` runtime model source files.

## Verification Added

- Atlas filter tests now assert Gambling Luck includes every scorer-required body and all four angles.
- Atlas ranking tests now assert higher-is-worse models rank lower raw scores first.
- Goal summary tests now assert warning score polarity is exposed.
- AstroClock route tests now assert relocation chart enrichment requests modern bodies and Chiron.
- Direct filter-validation tests now assert location/compare use the same exclusion contract as atlas search.
- Frontend modal tests now assert warning goals show lowest-risk labels.
