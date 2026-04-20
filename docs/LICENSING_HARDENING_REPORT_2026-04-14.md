# Licensing Hardening Report

Date: 2026-04-14

## Scope

This pass audited and hardened the desktop-app licensing path with one clarified product decision:

- Astro Clock basic/public routes are intentionally free and remain exempt from premium enforcement.
- Premium remains a binary entitlement model by design for now: licensed versus unlicensed.

This means the hardening work in this pass is focused on the actual security gaps rather than changing product policy.

## Intended Access Model

### Public by design

The following Astro Clock prefixes remain intentionally public:

- `/api/astro-clock/current`
- `/api/astro-clock/dashboard`
- `/api/astro-clock/planetary-hours`
- `/api/astro-clock/receptions`
- `/api/astro-clock/compass`

These are part of the intentionally free Astro Clock surface.

### Protected by license

All other `/api/astro-clock/*` routes remain license-protected, as do core protected routes such as:

- `/api/calculate-chart`
- `/api/moon-debug`
- `/api/metrics`

## Findings From The Audit

### 1. Device binding was incomplete

Before this pass:

- Electron main checked device binding in `getStatus()`.
- Electron main did **not** enforce the same device check in `getToken()`.
- The backend only verified that the token contained a `device` claim, not that it matched the actual local device.

Impact:

- A copied valid token could potentially be replayed on another machine until refresh or expiry forced revalidation.

### 2. The renderer could obtain the long-lived license token

Before this pass:

- The preload bridge exposed `getLicenseToken()`.
- That method returned the stored signed license token itself.
- Frontend API clients attached that long-lived token directly to backend requests.

Impact:

- Renderer compromise or JS/runtime extraction could steal the full long-lived bearer token.

## Hardening Implemented

### A. End-to-end device binding

The backend now enforces runtime device binding whenever a packaged runtime provides a device identifier.

Implementation shape:

- Electron main resolves the packaged app's device identifier before starting the backend.
- Electron main passes the device identifier to the backend process through environment configuration.
- Backend token validation now rejects license tokens whose `device` claim does not match the packaged runtime device identifier.

Result:

- A copied token is no longer sufficient by itself if the device claim does not match the local packaged runtime.

### B. Renderer no longer receives the long-lived license token

The renderer-facing `getLicenseToken()` bridge is preserved for compatibility, but the returned value is now a short-lived local session token instead of the long-lived remote license token.

Implementation shape:

- Electron main still stores and refreshes the real signed license token.
- Electron main mints a short-lived local session token using an app-session secret.
- The backend accepts that local session token and validates:
  - signature
  - expiry
  - token type
  - device binding

Result:

- The renderer can still authenticate requests, but stealing a renderer token is materially less useful than stealing the original long-lived license token.

## Security Posture After This Pass

### Improved

- Backend license enforcement is real for protected routes.
- Stream routes remain protected through one-time stream tickets.
- Device mismatch now fails in both Electron main and the backend.
- Renderer no longer receives the durable remote license token in packaged runtime.

### Intentional decisions, not weaknesses

- Astro Clock public surface remains public by product design.
- Premium entitlement remains binary by design.

### Still true

- A determined attacker with full control of the local machine can still patch the packaged app or hook runtime behavior.
- This hardening makes casual token copying and renderer-side replay materially harder, but does not make local cracking impossible.
- Truly strong resistance would require server-backed per-feature authorization or remote execution for more sensitive features.

## Verification Targets

This pass should be considered valid only if all of the following remain true:

1. Public Astro Clock routes still answer without a token.
2. Protected routes still reject missing tokens with `402 license_required`.
3. Device-mismatched tokens are rejected.
4. Renderer session tokens are accepted by the backend.
5. The renderer no longer depends on the raw stored remote license token.

## Next Hardening Moves

If more resistance is needed later, the next justified steps are:

1. Route-level entitlement enforcement beyond binary active/inactive.
2. Hardware-backed or server-issued challenge binding during activation/refresh.
3. Narrower server-side observability for suspicious token reuse across devices.
