# AstroClock Current Aspects Workflow

This note documents how the AstroClock "Current Aspects" panel is built, what was wrong in the April 2026 review, and what was changed.

## Current request flow

1. `frontend/src/features/astroclock/AstroClock.jsx`
   - Realtime mode requests `/api/astro-clock/dashboard`.
   - The response is normalized through `transformDashboard(...)`.
   - `CurrentAspectCard` reads from the transformed `data` snapshot.

2. `backend/astro_clock_api.py`
   - `/dashboard` resolves the active clock context.
   - `_build_dashboard_payload(...)` builds the AstroClock payload.
   - Standard current aspects prefer `compute_planetary_aspects_precise(...)`.
   - Morin mode adds `morin_aspects`, `morin_antiscia`, `morin_contra_antiscia`, `morin_combustion`, and `morin_patterns`.

3. `frontend/src/features/astroclock/AspectAnalysisModal.jsx`
   - The modal now consumes the already transformed AstroClock snapshot so the card and modal read from the same aspect data.

## Issues found

### 1. Morin toggle performed duplicate dashboard requests

When realtime SSE was disabled, AstroClock fetched the dashboard once for first paint and then immediately fetched it again before starting the polling interval. Morin mode always disables SSE, so toggling Morin caused two consecutive `/dashboard?morin=1` requests.

### 2. Aspect modal could drift from the visible AstroClock card

The modal used to request a fresh dashboard payload on open instead of reusing the already rendered AstroClock state. That caused two problems:

- the modal could show a slightly different orb because time had moved forward
- the modal could use a different toggle set than the card, including `includeModern`

### 3. Morin helpers repeated the same Swiss ephemeris lookups

The Morin backend computed the same longitude, latitude, declination, semi-diameter, and retrograde checks multiple times across:

- `compute_morin_aspects`
- `compute_morin_antiscia`
- `compute_morin_contra_antiscia`
- `compute_morin_combustion`

This did not change results, but it added avoidable latency.

### 4. Orb presentation was not guaranteed to match across surfaces

The card uses transformed aspect rows with normalized `orb_text`. The modal used raw fetched rows and formatted its own orb values. Even when the aspect row represented the same pair, the displayed orb text could differ.

## Fixes applied

### Frontend

- Removed the extra immediate fallback poll after the first realtime dashboard load.
- Passed the active transformed AstroClock dashboard snapshot into `AspectAnalysisModal`.
- Made the modal reuse the normalized transformed data path and orb labels.
- Passed `includeModern` through to the modal fallback request so the modal matches the current chart configuration.

### Backend

- Added cached Morin ephemeris helpers for:
  - longitude/latitude lookups
  - equatorial declination lookups
  - semi-diameter lookups
  - retrograde checks
- Included `max_orb` in standard precise aspect rows so the UI has an explicit orb cap from the same source.

## Expected behavior after the fix

- Toggling Morin should issue one dashboard request for the new state, not two.
- Opening "Aspect Analysis" should show the same snapshot the user already sees in the Current Aspects card.
- Standard aspect rows and the modal should agree on displayed orb text for the same snapshot.
- Morin mode may still be slower than standard mode because it performs more astronomy, but it should no longer do unnecessary duplicate frontend requests or duplicate ephemeris work.

## Important note about Morin vs standard orb values

Different orb values between standard mode and Morin mode are expected.

- Standard mode uses the standard precise planetary aspect engine.
- Morin mode uses Morin-style corrected rays and combined moieties.

So the same named aspect can legitimately have a different orb in Morin mode than it has in standard mode. That is not the bug fixed here.
