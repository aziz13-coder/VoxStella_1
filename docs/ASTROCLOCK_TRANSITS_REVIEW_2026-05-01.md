# AstroClock Transits Review

Date: 2026-05-01

Scope: document the two P2 findings from the AstroClock Transits feature review, define how the feature should behave instead, and record the implemented resolution.

Files involved:

- `backend/astro_clock_api.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`
- `frontend/src/features/astroclock/api.mjs`

No packaged artifacts were reviewed or changed.

Resolution status: resolved in source.

## Summary

The Transits feature is structurally sound: the modal can seed natal data from the active AstroClock chart or saved snaps, compute an exact transit timestamp, scan a time window, stream scan progress, replay selected peaks, and run predictor aggregation with optional Primary Directions, Progressions, and Solar Arc context windows.

The two issues below are workflow guardrail problems. They do not invalidate the Morin transit calculation itself, but they can make the feature behave unreliably under edge cases:

1. Oversized scans can bypass the streaming route limits through the non-stream fallback.
2. Clicking a scan timeline point can rewrite the visible transit date/time using the browser timezone instead of the chart timezone.

## Finding 1: Stream Scan Limits Can Be Bypassed

Location: `backend/astro_clock_api.py`, around `/api/astro-clock/transits/window`.

Severity: P2.

### Current Behavior

The streaming route `/api/astro-clock/transits/window/stream` validates the requested scan span and step size with `_validate_stream_scan_bounds`. This limits CPU-heavy requests by capping both maximum window hours and maximum total steps.

The non-stream route `/api/astro-clock/transits/window` performs the same type of scan, but it does not enforce the same bounds before calling `scan_morin_transits_window`.

The frontend normally tries streaming first. If streaming cannot be created or fails, `TransitsModal.jsx` falls back to `AstroClockAPI.getTransitsWindow(req)`. That means a request that the stream route would reject can still run through the fallback route.

Related frontend path:

- `TransitsModal.jsx`: `doScan()` calls `createTransitsWindowStream(req)` first, then falls back to `getTransitsWindow(req)` on stream failure.

### Why This Matters

Window scans can be expensive because each step recalculates transit hits and enriches them with prediction/concordance context. A large date range combined with a small step interval can produce thousands of steps.

Without consistent backend validation, a user or malformed request can:

- Trigger a long-running synchronous scan.
- Tie up the local backend process.
- Make the desktop app appear frozen or degraded.
- Create inconsistent behavior where stream requests are rejected but fallback requests continue.

### How It Should Act Instead

All scan-capable routes should enforce the same resource limits before doing expensive work.

Expected behavior:

- If the requested scan exceeds configured limits, every scan endpoint returns a clear `400` response.
- The frontend should show the limit error to the user instead of silently retrying the same oversized scan through another route.
- The stream fallback should only run for recoverable stream transport failures, not for validation failures.

Affected backend routes that should share bounds validation:

- `/api/astro-clock/transits/window`
- `/api/astro-clock/predictor`
- `/api/astro-clock/transits/window/export`
- `/api/astro-clock/transits/window/stream` already has this guard.

Implementation direction:

- Parse `start`, `end`, and `step_minutes` before scan execution.
- Call `_validate_stream_scan_bounds(start_dt, end_dt, step)`.
- Return `400` with the same error message if bounds validation fails.
- Consider renaming `_validate_stream_scan_bounds` to a route-neutral name such as `_validate_transit_scan_bounds`, since it should apply to all scan surfaces.
- In the frontend, do not fall back to `getTransitsWindow` when the stream request failed because the backend returned a validation error.

Test coverage to add:

- Backend test: `/transits/window` rejects a range that exceeds max hours or max steps.
- Backend test: `/predictor` rejects the same oversized range.
- Backend test: `/transits/window/export` rejects the same oversized range.
- Frontend test: stream creation/failure with a validation-style error surfaces the error and does not call `getTransitsWindow`.

Acceptance criteria:

- Oversized scans produce the same failure behavior on stream, non-stream, predictor, and export routes.
- No route calls `scan_morin_transits_window` after bounds validation fails.
- The UI reports the range/step problem instead of retrying through fallback.

Implemented resolution:

- Added shared backend scan validation for transit scan ranges.
- Applied it to `/transits/window`, `/predictor`, and `/transits/window/export`.
- Kept the existing stream route protected through the same underlying validator.
- Added a backend regression test proving oversized non-stream, predictor, and export requests return `400` before the scanner runs.

## Finding 2: Timeline Clicks Rewrite Time In Browser Timezone

Location: `frontend/src/features/astroclock/TransitsModal.jsx`, around `onTimelineClick`.

Severity: P2.

### Current Behavior

When the user clicks a scan timeline point, the modal receives the selected row timestamp. The exact transit calculation is correct because the handler passes the selected ISO timestamp directly into `handleCompute()`.

However, the handler also updates the visible Transit Date and Transit Time inputs with:

- `new Date(ts).getFullYear()`
- `new Date(ts).getMonth()`
- `new Date(ts).getDate()`
- `new Date(ts).getHours()`
- `new Date(ts).getMinutes()`

Those methods use the browser/system timezone, not the natal/chart timezone shown in the transits workspace.

### Why This Matters

The first exact compute after clicking the timeline is correct, but the input fields can display a shifted local time if the chart timezone differs from the user's machine timezone.

That creates a replay hazard:

1. User scans a chart for `Asia/Jerusalem`.
2. User clicks a peak timestamp.
3. The modal computes the intended ISO instant correctly.
4. The visible date/time inputs are rewritten in the browser timezone.
5. User later clicks `Compute Exact Time`.
6. The modal rebuilds an ISO value from the shifted visible fields and chart timezone, producing a different instant.

The user sees one timestamp selected but the next exact compute may target another timestamp.

### How It Should Act Instead

Visible Transit Date and Transit Time fields should always represent the same timezone context that will be used when rebuilding the transit ISO.

Expected behavior:

- If the modal has a natal/window timezone, timeline clicks format the visible inputs in that timezone.
- The timestamp passed to exact compute and the timestamp implied by the visible fields remain identical.
- If no chart timezone is known, the UI should avoid rewriting the fields from browser-local time, or clearly use UTC.

Implementation direction:

- Add a helper such as `formatIsoForInputFields(iso, timezone)` that uses `Intl.DateTimeFormat(..., { timeZone })` and `formatToParts`.
- Prefer timezone in this order:
  1. `windowTz`
  2. `result.natal.timezone`
  3. `result.natal.timezone_label`
  4. `natalTimezone`
  5. UTC fallback
- Use that helper in `onTimelineClick` before calling `setTransitDate()` and `setTransitTime()`.
- Keep passing the selected row ISO directly to `handleCompute()` to avoid async state timing issues.

Test coverage to add:

- Frontend test: for a chart in `Asia/Jerusalem` on a browser in another timezone, clicking a peak writes the chart-local date/time into the inputs.
- Frontend test: clicking a timeline point and then pressing `Compute Exact Time` calls `getTransits` with the same ISO instant.
- Frontend test: UTC fallback is stable when no natal/window timezone is available.

Acceptance criteria:

- Timeline peak replay remains exact on the first click.
- The visible date/time inputs match the selected chart-local instant.
- Recomputing from those fields does not drift to another timestamp.

Implemented resolution:

- Added chart-timezone input formatting for selected timeline timestamps.
- Timeline clicks now write `Transit Date` and `Transit Time` using the modal's known timezone context, falling back to UTC instead of browser-local time.
- The exact compute still receives the selected ISO directly, preserving first-click replay correctness.
- Added a frontend regression test proving that recomputing after a timeline click targets the same instant.

## Recommended Fix Order

1. Fix backend scan bounds first because it protects the local backend from expensive requests.
2. Add matching backend route tests.
3. Fix timezone formatting in `onTimelineClick`.
4. Add replay/drift frontend tests.
5. Re-run focused suites:

```powershell
python -m pytest backend/test_astro_clock_api_transits.py backend/test_transits_quality.py
cd frontend
npm run test:ui -- transitsModalReplay.test.jsx astroclockApi.test.mjs
```
