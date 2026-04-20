# FRONTEND_BACKEND_WORKFLOW_AUDIT_2026-03-05

## 1) Executive Summary

This repository's runtime model is coherent at a high level: packaged Electron starts a local Flask backend, `preload.js` exposes a narrow bridge, the renderer talks to the backend through thin request helpers, and licensing flows through Electron main to a separate FastAPI licensing service. The Astro Clock SSE paths correctly use short-lived stream tickets to bridge EventSource authentication.

The main technical risks are not missing routes; they are workflow edge cases and contract drift:

- `P1`: the licensing server hard-fails process startup when the admin token is missing, which blocks public activation/refresh/verify endpoints even though they do not require the admin UI.
- `P1`: packaged Electron backend readiness and backend health status codes disagree; `waitForHealth()` rejects any non-`200` response even though the backend explicitly reports `"unhealthy"` via JSON, so restart/startup logic can false-negative and loop.
- `P2`: shutdown on Windows escalates to `taskkill /IM horary_backend.exe`, which can kill unrelated backend processes.
- `P2`: protected backend endpoints validate signed license tokens locally but do not enforce current server entitlement until token refresh/expiry.
- `P2/P3`: several error and parameter paths are lossy or dead-on-arrival, especially election streaming errors and some Astro Clock query params.

Checks run during this audit:

- `frontend`: `npm test` passed.
- `frontend`: `npm run lint` passed.
- `frontend`: `npm run test:communication` passed.
- `backend`: `python -m pytest backend -q --import-mode=importlib` passed (`9 passed`).
- `frontend/backend`: `python -m pytest frontend/backend -q --import-mode=importlib` failed in `test_keyword_sync.py` because the test expects `frontend/event_keywords_dictionary(2).md`, which does not exist.
- Combined Python collection with `python -m pytest backend frontend/backend tests -q` is blocked by duplicate test module basenames in `backend/` and `frontend/backend/`.

No `P0` issues were found.

## 2) Architecture & Runtime Workflow

### App Launch Flow

1. `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js`
   - Computes `PORT`/`API_BASE_URL`.
   - In packaged mode, resolves the backend executable or Python entrypoint, spawns it, and polls `GET /api/health?skip_network=true`.
   - Registers IPC handlers, then creates `BrowserWindow` with `contextIsolation: true`, `nodeIntegration: false`, and `sandbox: true`.

2. `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js`
   - Exposes `window.API_BASE_URL`.
   - Exposes `window.IS_PACKAGED`.
   - Exposes a constrained `window.electronAPI` surface for updater, licensing, shell, and report export.

3. Renderer bootstrap
   - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx` checks backend reachability via `GET /api/version`.
   - Horary chart casting uses `VoxStellaAPI`.
   - Astro Clock features use `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs`.

4. Backend bootstrap
   - `C:\Users\sabaa\Downloads\codexhorary\backend\app.py` creates the Flask app, enables CORS for `/api/*`, installs the license guard, and registers the Astro Clock blueprint from `backend/astro_clock_api.py`.
   - Protected Astro Clock SSE paths require a stream ticket or a valid license header.

### Licensing Flow

1. Renderer requests license actions via `window.electronAPI.*`.
2. `frontend/main.js` forwards those IPC requests to `LicenseManager` in `frontend/main/license.js`.
3. `LicenseManager`:
   - derives a device ID,
   - stores a signed license token locally,
   - refreshes the token near expiry,
   - optionally verifies current entitlement online.
4. `licensing_server/app.py` issues signed tokens at `/license/activate`, refreshes them at `/license/refresh`, and evaluates server-side entitlement at `/license/verify`.
5. `backend/app.py` protects local API endpoints by validating the token signature/claims/expiry with `backend/licensing.py`.
6. EventSource flows cannot send headers, so the frontend first calls `POST /api/astro-clock/stream-ticket`, then opens the SSE URL with `?stream_ticket=...`.

### Main User Flows

- Horary chart casting:
  - `POST /api/calculate-chart`
- Astro Clock realtime/manual state:
  - `GET /api/astro-clock/current`
  - `POST /api/astro-clock/mode`
  - `GET /api/astro-clock/dashboard`
  - `GET /api/astro-clock/planetary-hours`
  - `GET /api/astro-clock/stream` via stream ticket
- Saved snapshots:
  - `POST /api/astro-clock/snap`
  - `GET /api/astro-clock/snaps`
  - `GET|DELETE /api/astro-clock/snaps/<id>`
- Analysis and visualization:
  - `GET /api/astro-clock/receptions`
  - `GET /api/astro-clock/compass`
  - `GET /api/astro-clock/traits/profile`
  - `GET /api/astro-clock/forensic`
- Transit analysis:
  - `GET /api/astro-clock/transits`
  - `GET /api/astro-clock/transits/window`
  - `GET /api/astro-clock/transits/window/stream` via stream ticket
  - `GET /api/astro-clock/predictor`
  - `GET /api/astro-clock/context/auto`
  - `GET /api/astro-clock/transits/export`
  - `GET /api/astro-clock/transits/window/export`
- Election search:
  - `GET /api/astro-clock/election/validate`
  - `GET /api/astro-clock/election/suggest/stream` via stream ticket
- Dev-only research mode:
  - `POST /api/astro-clock/research/lotto/compile/start`
  - `POST /api/astro-clock/research/lotto/compile`
  - `GET /api/astro-clock/research/lotto/progress`
  - `POST /api/astro-clock/research/lotto/stop`
  - `POST /api/astro-clock/research/lotto/analyze`

### IPC Boundary Review

Observed renderer-facing surface:

- `API_BASE_URL`
- `IS_PACKAGED`
- `electronAPI.checkForUpdates`
- `electronAPI.restartToUpdate`
- `electronAPI.getLicenseStatus`
- `electronAPI.activateLicense`
- `electronAPI.deactivateLicense`
- `electronAPI.getLicenseToken`
- `electronAPI.verifyLicense`
- `electronAPI.openExternal`
- `electronAPI.exportReport`

Boundary/trust notes:

- `contextIsolation`, `sandbox`, and `nodeIntegration: false` are correctly enabled in `frontend/main.js`.
- `shell:open-external` is allowlisted to localhost backend URLs and explicit production hosts.
- `report:export` sanitizes scripts/inline handlers and disables JavaScript in the print window.
- IPC payload validation is light, but I did not find a critical trust-boundary escape in the reviewed surface.

## 3) Frontend<->Backend Contract Matrix

### Renderer HTTP Contracts

| Frontend call | Method + path | Backend handler | Auth | Contract notes |
|---|---|---|---|---|
| `VoxStellaAPI.calculateChart` | `POST /api/calculate-chart?useReasoningV1=...` | `backend/app.py -> calculate_chart()` | Protected | Body keys align with backend expectations; client timeout is 90s. |
| `VoxStellaAPI.getTimezone` | `POST /api/get-timezone` | `backend/app.py -> get_timezone()` | Public | Body `{ location }` matches. |
| `VoxStellaAPI.getCurrentTime` | `POST /api/current-time` | `backend/app.py -> get_current_time()` | Public | Body `{ location }` matches. |
| `VoxStellaAPI.getHealth` | `GET /api/health?skip_network=true` | `backend/app.py -> health_check()` | Public | Renderer helper exists, but startup readiness in Electron uses its own `waitForHealth()`. |
| `VoxStellaAPI.ping` / `getVersion` | `GET /api/version` | `backend/app.py -> get_version()` | Public | Used by the renderer to mark backend connected. |
| Legacy in-file Astro Clock component | `GET /api/astro-clock/current` | `backend/astro_clock_api.py -> get_current()` | Public | Present in `App.jsx`; appears superseded by `AstroClockPage`, but route exists and matches. |
| Legacy in-file Astro Clock component | `POST /api/astro-clock/mode` | `backend/astro_clock_api.py -> set_mode()` | Protected | Body matches `mode/datetime/location/timezone/house_system(_code)`. |

### Astro Clock HTTP/SSE Contracts

| Frontend call | Method + path | Backend handler | Auth | Contract notes |
|---|---|---|---|---|
| `AstroClockAPI.getCurrent` | `GET /api/astro-clock/current` | `get_current()` | Public | Straight match. |
| `AstroClockAPI.getDashboard` | `GET /api/astro-clock/dashboard` | `get_dashboard()` | Public | `include_modern` and `morin` are consumed; `special_degree` is consumed inside `_build_dashboard_payload()`. |
| `AstroClockAPI.getPlanetaryHours` | `GET /api/astro-clock/planetary-hours?date=...|datetime=...` | `get_planetary_hours()` | Public | `date` and `datetime` both supported. |
| `AstroClockAPI.createSnap` | `POST /api/astro-clock/snap` | `create_snap()` | Protected | Body `label/include_modern/special_degrees` matches. |
| `AstroClockAPI.listSnaps` | `GET /api/astro-clock/snaps` | `list_snaps()` | Protected | Match. |
| `AstroClockAPI.getSnap` | `GET /api/astro-clock/snaps/<id>` | `get_snap()` | Protected | Match. |
| `AstroClockAPI.deleteSnap` | `DELETE /api/astro-clock/snaps/<id>` | `delete_snap()` | Protected | Match. |
| `AstroClockAPI.setMode` | `POST /api/astro-clock/mode` | `set_mode()` | Protected | Body keys match both `house_system` and `house_system_code`. |
| `AstroClockAPI.setLocation` | `POST /api/astro-clock/location` | `set_location()` | Protected | Body `{ location }` matches. |
| `AstroClockAPI.getReceptions` | `GET /api/astro-clock/receptions` | `get_receptions()` | Public | Match. |
| `AstroClockAPI.createStream` | `POST /api/astro-clock/stream-ticket`, then `GET /api/astro-clock/stream?...&stream_ticket=...` | `backend/app.py -> issue_stream_ticket()` and `stream_ticks()` | Ticketed | Contract is correct; query params on `/stream` are currently unused server-side. |
| `AstroClockAPI.getCompass` | `GET /api/astro-clock/compass?...` | `get_compass()` | Public | Route exists, but frontend query params are not consumed; see Finding F6. |
| `AstroClockAPI.getTraitProfile` | `GET /api/astro-clock/traits/profile?special_degree=...` | `traits_profile()` | Protected | Repeated `special_degree` params are consumed. |
| `AstroClockAPI.getTransits` | `GET /api/astro-clock/transits?...` | `transits_compute()` | Protected | Request/handler align via `_natal_from_query()` plus transit filters. |
| `AstroClockAPI.getTransitsWindow` | `GET /api/astro-clock/transits/window?...` | `transits_window()` | Protected | Core scan params align; several optional metadata params are serialized but ignored server-side. |
| `AstroClockAPI.createTransitsWindowStream` | `POST /api/astro-clock/stream-ticket`, then `GET /api/astro-clock/transits/window/stream?...&stream_ticket=...` | `issue_stream_ticket()` and `transits_window_stream()` | Ticketed | Frontend precomputes `start/end`, which matches the stream handler requirement. |
| `AstroClockAPI.getPredictions` | `GET /api/astro-clock/predictor?...` | `transits_predictor()` | Protected | Core contract matches. |
| `AstroClockAPI.exportTransits` | `GET /api/astro-clock/transits/export?...` | `transits_export_csv()` | Protected | Blob handling and CSV headers align. |
| `AstroClockAPI.exportTransitsWindow` | `GET /api/astro-clock/transits/window/export?...` | `transits_window_export_csv()` | Protected | Blob handling and CSV headers align. |
| `AstroClockAPI.getAutoContext` | `GET /api/astro-clock/context/auto?...` | `auto_context()` | Protected | Natal context/year/anchor fields align; `residence_location` and `sr_window_days` are not consumed. |
| `AstroClockAPI.getForensic` | `GET /api/astro-clock/forensic?...` | `forensic_analysis()` | Protected | Query/body contract matches. |
| `AstroClockAPI.validateElection` | `GET /api/astro-clock/election/validate?...` | `election_validate()` | Protected | Only basic validation is performed; it is not a full mirror of stream computation. |
| `AstroClockAPI.electionStream` | `POST /api/astro-clock/stream-ticket`, then `GET /api/astro-clock/election/suggest/stream?...&stream_ticket=...` | `issue_stream_ticket()` and `election_suggest_stream()` | Ticketed | Main contract matches; error propagation is lossy if ticket acquisition fails. |
| `AstroClockAPI.researchCompileStart` | `POST /api/astro-clock/research/lotto/compile/start` | `research_compile_start()` | Protected/dev-only | Match. |
| `AstroClockAPI.researchCompile` | `POST /api/astro-clock/research/lotto/compile` | `research_compile()` | Protected/dev-only | Match. |
| `AstroClockAPI.researchProgress` | `GET /api/astro-clock/research/lotto/progress?session_id=...` | `research_progress()` | Protected/dev-only | Match. |
| `AstroClockAPI.researchStop` | `POST /api/astro-clock/research/lotto/stop` | `research_stop()` | Protected/dev-only | Body `sessionId` matches. |
| `AstroClockAPI.researchAnalyze` | `POST /api/astro-clock/research/lotto/analyze` | `research_analyze()` | Protected/dev-only | Body `sessionId/filter/rowLimit` matches. |

### Licensing and IPC Contracts

| Renderer bridge | Main-process handler | Downstream target | Contract notes |
|---|---|---|---|
| `electronAPI.getLicenseStatus` | `license:get-status` | `LicenseManager.getStatus()` | Local token signature/expiry check only. |
| `electronAPI.activateLicense` | `license:activate` | `POST /license/activate` | Body `{ key, email }` becomes `{ key, email, deviceId }`. |
| `electronAPI.deactivateLicense` | `license:deactivate` | `POST /license/deactivate` | Clears local token after best-effort server call. |
| `electronAPI.getLicenseToken` | `license:get-token` | `LicenseManager.getToken()` | May refresh online depending on expiry window. |
| `electronAPI.verifyLicense` | `license:verify` | `POST /license/verify` | Explicit online entitlement verification. |
| `electronAPI.checkForUpdates` | `update:check` | `frontend/main/updater.js` | IPC match is correct. |
| `electronAPI.restartToUpdate` | `update:restart` | `frontend/main/updater.js` | IPC match is correct. |
| `electronAPI.openExternal` | `shell:open-external` | `electron.shell.openExternal()` | Host/origin allowlist enforced in main. |
| `electronAPI.exportReport` | `report:export` | Hidden print window + `printToPDF()` | HTML is sanitized; payload validation is otherwise minimal. |

## 4) Findings (sorted by severity: P0/P1/P2/P3)

### F1. [P1] Licensing server startup is blocked by missing admin UI credentials

- Severity: `P1`
- Exact evidence:
  - `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:410`
  - `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:424`
  - `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:426`
- Impact:
  - `load_admin_token()` raises during module import, so the entire licensing service refuses to start when `ADMIN_TOKEN`/`ADMIN_TOKEN_FILE` is missing.
  - That blocks `/license/activate`, `/license/refresh`, `/license/verify`, and `/license/deactivate`, even though those public APIs do not require the admin UI.
- Proposed fix:
  - Load the admin token lazily inside `require_admin()` / admin route dependencies.
  - If no admin token is configured, disable only `/admin/*` routes or return `503` for admin paths, while still allowing the public licensing API to boot.
- Needed resolution:
  - Decouple public `/license/*` service startup from admin UI credential loading.
  - Closing this finding requires the licensing service to boot successfully without `ADMIN_TOKEN`, while `/admin/*` remains fail-closed.

### F2. [P1] Packaged backend readiness and backend health status codes disagree

- Severity: `P1`
- Exact evidence:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:760`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:764`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:275`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:282`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:292`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:254`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:260`
- Impact:
  - The backend health endpoint emits a valid JSON health body with `"status": "unhealthy"` but returns HTTP `503`.
  - `waitForHealth()` rejects every non-`200` response before it even inspects that JSON body.
  - In packaged mode this can make startup time out, and in restart mode it can kill/restart a live backend that is merely reporting `unhealthy`.
- Proposed fix:
  - Pick one readiness contract and enforce it consistently.
  - Either:
    - make `/api/health` always return `200` with JSON-only status semantics, or
    - teach `waitForHealth()` to accept `503` when the body parses and contains a structurally valid health payload.
- Needed resolution:
  - Define a single readiness contract shared by `backend/app.py` and `frontend/main.js`.
  - Closing this finding requires startup and restart logic to distinguish transport failure from a reported unhealthy state, without false restart loops.

### F3. [P2] Windows shutdown fallback can kill unrelated backend processes

- Severity: `P2`
- Exact evidence:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:173`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:174`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:504`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:507`
- Impact:
  - On shutdown, the app escalates from PID-based termination to `taskkill /IM <backendImageName> /T /F`.
  - That image-name kill is process-global, not scoped to the child process it spawned.
  - Closing one packaged app instance can therefore kill another running `horary_backend.exe`, including diagnostic or parallel app sessions.
- Proposed fix:
  - Remove the `/IM` fallback entirely, or replace it with a process tree/job object that is scoped to the spawned child PID.
  - If a last-resort fallback is required, persist the spawned PID and only kill descendants of that PID.
- Needed resolution:
  - Make backend shutdown strictly PID- or job-scoped.
  - Closing this finding requires app shutdown to terminate only the backend process tree created by the current Electron instance, never unrelated processes with the same executable name.

### F4. [P2] Protected backend endpoints do not enforce current server entitlement until token refresh/expiry

- Severity: `P2`
- Exact evidence:
  - `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:325`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:338`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\licensing.py:81`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\licensing.py:129`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:293`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:324`
  - `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:23`
  - `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:29`
- Impact:
  - The local backend accepts any correctly signed, unexpired token without consulting the licensing server.
  - `LicenseManager.getToken()` only refreshes when the token is within the refresh leeway window, so a revoked/deactivated token can continue to unlock protected local endpoints until refresh or expiry.
  - With the default licensing-server TTL, that window is up to 7 days.
- Proposed fix:
  - Shorten token TTL substantially and refresh aggressively, or add a backend-side entitlement freshness requirement.
  - A practical pattern is to include a `verified_at`/`next_verify_at` claim and reject tokens whose server verification age exceeds a short threshold.
- Needed resolution:
  - Enforce bounded entitlement freshness between the licensing server and protected local backend routes.
  - Closing this finding requires a revoked entitlement to stop authorizing protected local APIs within a short, defined verification window rather than the full token TTL.

### F5. [P2] Election streaming hides root-cause failures behind a generic "Unable to open stream" error

- Severity: `P2`
- Exact evidence:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:216`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:228`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:525`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:526`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:285`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:286`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:303`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:307`
- Impact:
  - Stream-ticket acquisition errors are swallowed and converted to `null`.
  - `ElectionModal` turns that into a generic `Unable to open stream` error before any backend detail reaches the UI.
  - The fallback validator only runs after an already-open EventSource emits `onerror`, so ticket/licensing/startup failures stay opaque.
- Proposed fix:
  - Return a structured error from `buildStreamUrlWithTicket()` instead of `null`.
  - Surface the backend message directly in `ElectionModal`.
  - If election scanning should remain usable without SSE, add a non-stream JSON endpoint and use it as a real fallback.
- Needed resolution:
  - Preserve backend error detail end-to-end across stream-ticket acquisition, EventSource setup, and UI presentation.
  - Closing this finding requires the renderer to show the actual backend or licensing failure reason, not a generic stream-open error.

### F6. [P3] Several frontend query parameters are serialized but ignored by the backend

- Severity: `P3`
- Exact evidence:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:533`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:536`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:550`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:552`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:287`
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:299`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1323`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1349`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2545`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2576`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2590`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1672`
  - `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1711`
- Impact:
  - `getCompass()` sends `origin`/`include_modern`, but `get_compass()` ignores query args and always returns classical-planet bearings.
  - `getAutoContext()` sends `residence_location` and `sr_window_days`, but `auto_context()` never reads them.
  - Transits-window requests serialize PD/SA metadata and extra toggles that `transits_window()` does not consume.
  - These silent no-op parameters make the contract appear richer than it is and complicate debugging/result interpretation.
- Proposed fix:
  - Remove the unused query serialization until the backend supports it, or implement the corresponding handler logic.
  - Add a contract test that diffs frontend-emitted query params against backend-consumed query args for each route.
- Needed resolution:
  - Bring request builders and backend handlers back into contract parity.
  - Closing this finding requires every emitted query parameter to be either consumed by the backend with tested behavior or removed from the frontend API surface.

## 5) Reproduction Steps for each finding

### F1. Licensing server startup blocked by admin token

1. Ensure `ADMIN_TOKEN` and `ADMIN_TOKEN_FILE` are unset.
2. Run `python licensing_server/app.py` from the repo root.
3. Observe immediate process exit with `RuntimeError: ADMIN_TOKEN is not configured; refusing to start licensing admin UI.`
4. No public licensing endpoint binds to `127.0.0.1:8787`.

### F2. Health/status-code readiness mismatch

1. Start the backend in an environment where one health probe becomes `unhealthy` while the process still serves HTTP.
2. Confirm `GET /api/health?skip_network=true` returns HTTP `503` with a JSON body containing `"status": "unhealthy"`.
3. Launch the packaged Electron app, or trigger the packaged backend restart path.
4. Observe `waitForHealth()` continue retrying until timeout because it rejects non-`200` responses before reading the JSON status.

### F3. Process-global backend kill on shutdown

1. Start one packaged app instance so it spawns `horary_backend.exe`.
2. Separately start another `horary_backend.exe` process on the same machine.
3. Quit the packaged app.
4. Observe the shutdown path call `taskkill /IM horary_backend.exe /T /F`, terminating both processes.

### F4. Revocation lag between licensing server and protected backend endpoints

1. Activate a license and obtain a valid stored token.
2. Use that token to call a protected local endpoint such as `/api/astro-clock/transits`.
3. Deactivate the device/license on the licensing server, but do not force a local verify/refresh yet.
4. Call the protected local endpoint again before the token enters the refresh window or expires.
5. Observe the backend still accepting the request because it only checks signature/claims/expiry locally.

### F5. Election stream errors are flattened

1. Cause `POST /api/astro-clock/stream-ticket` to fail for election scans, for example by using no license token or stopping the backend.
2. Start an election scan from the renderer.
3. Observe `AstroClockAPI.electionStream()` return `null`.
4. Observe the UI surface only `Unable to open stream`, without the backend's real error detail.

### F6. Dead-on-arrival query params

1. Call `/api/astro-clock/compass` with and without `include_modern=1`.
2. Compare responses; they remain classical-only.
3. Call `/api/astro-clock/context/auto` with and without `residence_location` or `sr_window_days`.
4. Compare responses; those parameters do not affect the payload.
5. Call `/api/astro-clock/transits/window` with and without `pd_label/pd_sig/pd_pro/pd_aspect/pd_type/sa_label`.
6. Compare handler behavior; the route ignores those metadata fields.

## 6) Recommended Fixes (specific, code-level)

- F1:
  - In `licensing_server/app.py`, replace the module-global `ADMIN_TOKEN = load_admin_token()` with a lazy helper inside `require_admin()`.
  - Guard admin routes with an `ADMIN_UI_ENABLED` flag derived at request time.
  - Leave `/license/*` routes independent from admin credential bootstrapping.

- F2:
  - In `frontend/main.js`, change `waitForHealth()` to parse the body for both `200` and `503`.
  - Alternatively, in `backend/app.py`, return `200` for `"healthy"`, `"degraded"`, and `"unhealthy"` and reserve `5xx` for actual handler failure, not health-state signaling.
  - Add an integration test covering `waitForHealth()` against `healthy`, `degraded`, and `unhealthy` bodies.

- F3:
  - Remove the image-name kill fallback on Windows.
  - If orphan cleanup is required, spawn the backend in a Windows Job Object or track descendant PIDs explicitly.
  - Keep shutdown behavior PID-scoped and idempotent.

- F4:
  - Shorten token lifetime from 7 days to something operationally tighter.
  - Force `LicenseManager.getToken()` to refresh on app launch or once per short interval, not only near expiry.
  - Add a backend claim check such as `next_verify_at`, and reject tokens whose verification age is stale.
  - Add an automated test where `/license/verify` flips from allowed to denied and the local backend stops accepting the token promptly.

- F5:
  - Make `buildStreamUrlWithTicket()` return `{ ok, url, error, status }` instead of `null`.
  - In `ElectionModal.jsx`, show the backend detail directly when stream-ticket acquisition fails.
  - Consider adding `GET /api/astro-clock/election/suggest` for JSON fallback so the UI can still complete the scan when SSE is unavailable.

- F6:
  - Delete unused query serialization from `api.mjs` unless the backend implements it immediately.
  - For `getCompass()`, either honor `include_modern`/`origin` in `get_compass()` or remove those params from the frontend.
  - For `auto_context()`, either read `residence_location`/`sr_window_days` or remove them from the request builder.
  - For transit metadata params, implement the advertised weighting behavior or stop sending them.

## 7) Test/Verification Gaps

- Combined Python collection is currently blocked:
  - Command: `python -m pytest backend frontend/backend tests -q`
  - Failure mode: duplicate module basenames in `backend/` and `frontend/backend/` cause import-file-mismatch errors during collection.

- One frontend/backend Python test has a broken repository assumption:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\test_keyword_sync.py:15-16` expects `C:\Users\sabaa\Downloads\codexhorary\frontend\event_keywords_dictionary(2).md`, which does not exist.

- I did not find any automated end-to-end test that covers:
  - packaged Electron main-process backend spawn and readiness polling,
  - `preload.js` bridge initialization against those IPC handlers,
  - stream-ticket issuance and SSE consumption for Astro Clock/election flows,
  - licensing server startup without admin credentials,
  - backend behavior after server-side license revocation,
  - Windows shutdown behavior against multiple backend processes.

- The existing frontend tests validate renderer/UI behavior, but not renderer-to-main IPC error propagation or main-to-backend startup/restart behavior.

## 8) Quick Wins (1-day fixes)

- Make `ADMIN_TOKEN` lazy/admin-only so the licensing API can boot without the admin UI.
- Align `/api/health` status codes with `waitForHealth()` expectations.
- Remove the `/IM` fallback kill path and stay PID-scoped.
- Propagate stream-ticket backend errors into the election UI instead of returning `null`.
- Add a contract test that enumerates frontend-emitted query params versus backend-consumed args for each Astro Clock route.
- Rename duplicate Python test modules or enforce `--import-mode=importlib` in repo-level pytest configuration so the full suite can be collected in one command.
