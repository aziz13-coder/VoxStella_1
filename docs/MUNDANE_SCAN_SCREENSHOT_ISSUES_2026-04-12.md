# Mundane Scan Screenshot Issues

Date: 2026-04-12  
Scope: screenshot-based investigation of the Advanced Workspace `Mundane > Scan` flow, focused on `Lunation` scan setup.

## Reported Screens

The screenshots show:

- `Chart Type = Lunation`
- `Domain Lens = War / Conflict`
- `Scan Mode = Spatiotemporal Scan`
- a visible validation error: `This chart type requires a polity.`
- a `Polity` dropdown that contains only the placeholder `Select polity...`

## Confirmed Issues

### 1. Impossible polity state in scan mode

Severity: high

Observed behavior:

- `Lunation` is marked as requiring a polity.
- The scan form enforces that requirement before allowing the scan to start.
- The scan catalog payload was not including any `polities`, so the dropdown had no real options.

Result:

- the user is blocked in an impossible state:
  - polity is required
  - polity cannot be selected

Root cause in source before fix:

- [backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py) endpoint `/api/astro-clock/mundane/scan/regions` filtered and passed `chart_types` and `domains`, but omitted:
  - `polities`
  - `context_types`

Frontend impact:

- [frontend/src/features/astroclock/MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx) correctly reads `catalog.polities`, but the array was empty because the backend endpoint did not return it.

Status:

- fixed in source by passing `polities` and `context_types` through the scan catalog endpoint
- fixed in source by adding a clearer frontend guard when a required-polity chart type has no loaded polity options

### 2. Missing context-type options in scan catalog

Severity: medium

Observed behavior:

- the `Polity Context` select shows only the placeholder state

Root cause:

- same backend omission as above: `/mundane/scan/regions` was not returning `context_types`

Impact:

- scan mode could still infer a default context internally, but the UI looked incomplete and misleading

Status:

- fixed in source together with issue 1

### 3. Secondary time-slice failure hidden behind the polity failure

Severity: medium

Observed behavior:

- the provided scan window is:
  - `2026-02-01 01:00`
  - to `2026-03-01 09:00`
  - at `6` hour steps

Computed effect:

- this is about `114` time slices
- current backend limit is `24` time slices

Impact:

- even after the polity issue is fixed, this exact run should still be rejected on scan-size limits

Relevant source:

- [backend/mundane_scan_service.py](C:/Users/sabaa/Downloads/codexhorary/backend/mundane_scan_service.py)
- [frontend/src/features/astroclock/MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx)

Status:

- not a bug
- current behavior is correct
- the user-facing problem is discoverability, not correctness

Recommended UX follow-up:

- show an inline estimated slice count before the user presses `Run Scan`
- keep the current hard stop

### 4. Product-copy mismatch around lunation scan requirements

Severity: medium

Observed behavior:

- chart-type summary text for `Lunation` says:
  - `selected polity or region`
- runtime metadata still marks `lunation.requires_polity = true`
- scan-mode validation enforces polity as mandatory

Impact:

- the copy implies a region-only path that the current runtime does not allow

Relevant source:

- [backend/knowledge/mundane/mundane_chart_types.runtime.json](C:/Users/sabaa/Downloads/codexhorary/backend/knowledge/mundane/mundane_chart_types.runtime.json)

Status:

- investigated
- not changed in this pass because it is a product/doctrine decision, not just a transport bug

## Fixes Applied In Source

Implemented:

- `/api/astro-clock/mundane/scan/regions` now returns:
  - `polities`
  - `context_types`
- scan-mode API test now asserts those fields exist
- the scan UI now surfaces a direct message when a required-polity chart type has no loaded polity options

Files changed:

- [backend/astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py)
- [backend/test_astro_clock_api_mundane.py](C:/Users/sabaa/Downloads/codexhorary/backend/test_astro_clock_api_mundane.py)
- [frontend/src/features/astroclock/MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx)

## Remaining Recommendations

### Recommendation A

Clarify the doctrine/product rule for `lunation` in scan mode:

- option 1: keep polity mandatory and update the copy
- option 2: allow region-only lunation scans and relax validation for scan mode only

Do not leave the current mixed message in place.

### Recommendation B

Add proactive scan-budget guidance in the UI:

- estimated time slices
- estimated evaluated cells
- warning before submit, not only after submit

### Recommendation C

If packaged builds are still reported with the old empty-polity behavior after this source fix:

- treat that as a packaging/version issue, not a scan-workspace logic issue
- verify the installed package was rebuilt from current source
