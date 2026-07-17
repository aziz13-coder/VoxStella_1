# Startup Fetch and What's New Responsive Fix Plan

Date: 2026-05-05

## Scope

Resolve two customer-facing first-run issues:

1. The What's New modal does not fit small screens.
2. On a newly installed or unverified PC, the app can briefly show a fetch/offline error before data appears.

Both issues affect trial confidence. The app should read as still starting/checking until the backend is truly unavailable, and release notes should be usable on small displays.

## Observed Risk

The report came from an unverified PC, but the fetch symptom may not be license-specific. It can happen anywhere the renderer asks the local backend for data before the packaged Flask process is fully ready.

Do not assume activation is the root cause until verified. The main distinction to test is:

- Packaged app, activated license.
- Packaged app, unactivated license.
- Browser dev runtime.
- Electron dev runtime.

## Relevant Source Files

- `frontend/src/components/WhatsNewModal.jsx`
- `frontend/src/App.jsx`
- `frontend/src/utils/apiConnectivity.mjs`
- `frontend/src/utils/licenseFlow.mjs`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/main.js`
- `frontend/preload.js`
- `frontend/src/tests/whatsNewModal.test.jsx`
- `frontend/src/tests/apiConnectivity.test.mjs`
- `frontend/src/tests/astroClockModeFlow.test.jsx`

Generated paths remain off limits: `frontend/dist-electron/**`, `frontend/dist/**`, `frontend/backend/build/**`, `website/**`, and packaged `resources/**`.

## Likely Root Causes

### What's New Modal

`WhatsNewModal.jsx` renders a centered modal with a large fixed visual shell:

- `max-w-[980px]`
- `rounded-[28px]`
- outer overlay padding only
- no viewport max-height
- no internal scroll container
- desktop-oriented two-column body

On small or short screens, the modal can exceed the viewport and make content or the close control inaccessible.

### Startup Fetch Error

The app already has a `checking` API state, but there are still paths that can expose transient startup errors:

- Browser fallback uses `API_CONNECTIVITY_BOOT_GRACE_MS = 12000`, while observed packaged startup can take 10-30 seconds.
- `App.jsx` marks Electron backend status refresh failures as `offline` immediately.
- `AstroClock.jsx` starts dashboard requests without gating all bootstrapping on `apiStatus === 'connected'`.
- `getClockLoadErrorMessage()` returns raw browser fetch messages, so a temporary `Failed to fetch` can reach the UI.

The intended product behavior is:

- During startup: show `Checking...` / loading state only.
- During transient backend boot delay: keep retrying quietly.
- After confirmed failure: show one clear offline message with retry affordance.
- After data succeeds: clear any stale startup error.

## Implementation Plan

### Phase 1: Make What's New Responsive

Update `WhatsNewModal.jsx`:

- Constrain modal shell with `max-h-[calc(100dvh-2rem)]` and mobile-safe width.
- Make the body scroll internally with `overflow-y-auto`.
- Keep the header and close control reachable, either sticky or outside the scroll region.
- Reduce mobile radius and padding, for example `rounded-2xl sm:rounded-[28px]`, `p-3 sm:p-4`, `px-4 sm:px-8`.
- Change the body grid to one column by default and only use two columns on wider screens.
- Remove negative/tight letter spacing that risks overflow in compact layouts.
- Ensure long release text wraps with `min-w-0`, `break-words`, and sane line heights.

Acceptance:

- At 360x640, the close control is visible and all release notes can be scrolled.
- At 390x844, no horizontal overflow.
- At 768x1024 and desktop, the design still looks intentional.

### Phase 2: Separate Startup From Confirmed Offline

Update connectivity logic:

- Increase packaged startup grace to match real behavior. Target 45 seconds for Electron packaged startup, matching `frontend/main.js` backend status grace.
- Track consecutive failed probes before setting `offline`; one early failed request should not show a customer-facing offline/fetch error.
- In `App.jsx`, when Electron status bridge calls fail during startup, keep `checking` and retry instead of immediately setting `offline`.
- Keep the header label as `Checking...` while within the startup grace window.
- Only expose `API Offline` after:
  - startup grace elapsed, and
  - multiple backend reachability probes failed, or
  - Electron main process explicitly reports confirmed `offline`.

Acceptance:

- A slow first packaged launch does not show `Failed to fetch`, `Could not fetch`, or `API Offline` before the backend has had the full grace window.
- A genuinely missing backend eventually shows a single intentional offline message.

### Phase 3: Suppress Transient Astro Clock Fetch Errors

Update `AstroClock.jsx`:

- Gate initial realtime dashboard loading while `apiStatus === 'checking'`.
- Do not start dashboard, stream, snap, or planetary-hour boot requests until backend status is `connected`, except where a user explicitly clicks retry.
- If a fetch fails while app status is `checking`, keep the panel in loading/checking state and do not render the raw network error.
- Map raw `Failed to fetch` / `NetworkError` to a product message only after confirmed offline.
- Clear `clockLoadError` when status moves back to `checking` or `connected`.

Acceptance:

- Astro Clock first load shows loading/checking, not a red fetch error, while the backend is booting.
- If the backend becomes connected 10-30 seconds later, data appears without a stale error.
- If the backend never starts, the user sees one clear offline state after confirmation.

### Phase 4: Verify License Interaction

Test both activation states:

- Unverified packaged app should show activation messaging for gated chart casting, but backend readiness should still be checked independently.
- Verified packaged app should show the same startup checking behavior.
- License token fetch failures should not be conflated with backend reachability failures.

Acceptance:

- Unverified users are not shown backend fetch errors just because they are unverified.
- Activation-required states and backend-offline states are visually and semantically distinct.

## Test Plan

Automated:

- Extend `frontend/src/tests/whatsNewModal.test.jsx` to assert viewport-safe classes or structure:
  - modal shell has max viewport height.
  - body has internal overflow.
  - close button remains in the non-scrolling header.
- Extend `frontend/src/tests/apiConnectivity.test.mjs`:
  - startup failures remain `checking`.
  - repeated failures after grace become `offline`.
  - post-connected disconnect can still become `offline`.
- Extend `frontend/src/tests/astroClockModeFlow.test.jsx`:
  - `apiStatus="checking"` does not render a raw fetch error.
  - transition from `checking` to `connected` clears startup errors.

Manual:

- Package from source with `package-app-new.bat`.
- Fresh install on a machine/profile without an active license.
- Launch and observe first 45 seconds:
  - status says `Checking...` until connected.
  - no raw fetch error appears.
  - activation-required messaging remains clear.
- Repeat on verified install.
- Resize packaged app to:
  - 360x640
  - 390x844
  - 768x1024
  - desktop default
- Confirm What's New remains usable and no page-level horizontal scroll appears.

## Release Note

When complete, update `frontend/src/content/whatsNew.mjs` for the next version:

- Startup now stays in a checking state while the local engine warms up.
- What's New is now usable on small displays.

## Recommended Order

1. Fix the modal first. It is isolated and low risk.
2. Fix API status grace and retry semantics in `App.jsx` / `apiConnectivity.mjs`.
3. Gate Astro Clock startup requests and sanitize transient network messages.
4. Run focused frontend tests.
5. Package and perform first-run manual QA on unverified and verified installs.
