# Technical Audit Report

Date: 2026-03-05  
Scope: Technical quality only (architecture, security, reliability, performance, packaging, CI/testing, maintainability)

## Section A: Executive technical summary

- No P0 issue found; highest risks are in token transport, shared mutable backend state, and streaming memory behavior.
- Electron boundary map: main process in `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:1` owns backend process and IPC; preload in `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js:14` exposes a narrow API; renderer entry is `C:\Users\sabaa\Downloads\codexhorary\frontend\src\renderer.jsx:1` mounting `App`.
- Python backend architecture: Flask app in `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:143`, license guard middleware in `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:182`, Astro Clock blueprint registration/fallback in `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:257`.
- Licensing server architecture: FastAPI + SQLite + Ed25519 token signing in `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:37`, `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:20`, `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:159`.
- Startup/runtime flow: app ready -> backend spawn -> health wait -> window create -> license IPC init (`C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:208`, `:219`, `:220`, `:227`, `:234`); renderer then pings API and reads license status (`C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:818`, `:825`).
- Security positives: `contextIsolation: true` + `nodeIntegration: false` on main window (`C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:187`, `:188`); backend and licensing server bind localhost (`C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:12`, `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1943`, `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:614`).
- Security-critical gap: license tokens are appended to SSE URLs (`license_token=...`) rather than kept in headers.
- Reliability/performance-critical gaps: shared global engine mutation in threaded backend and large in-memory SSE accumulators can degrade correctness and stability.
- Maintainability hotspots: very large renderer monolith and duplicated backend tree (`backend/**` and `frontend/backend/**`) with runtime fallback imports.
- CI has useful forbidden-path guard, but backend test signal quality and pipeline strictness (deterministic packaging/lint/security checks) need upgrades.

## Section B: Findings table (sorted by severity)

| Severity | Issue | Evidence (absolute file:line) | Impact | Recommended fix |
|---|---|---|---|---|
| P1 | License token leaks into URL query string for SSE | `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:203`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:127`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:243`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:365`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:560` | Token may appear in URL logs/history/proxies and be replayed while valid. | Replace query-token SSE auth with short-lived one-time stream tickets minted via authenticated POST; keep token only in Authorization header. |
| P1 | Shared mutable global engine under threaded server (race/cross-request bleed) | `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1945`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:66`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1284`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1332`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1032` | Concurrent requests can overwrite settings (location/timezone/house system), causing nondeterministic outputs. | Use per-request engine instances or protect mutable engine sections with locking and immutable settings snapshots. |
| P1 | Streaming endpoints accumulate large arrays in memory and return full series payloads | `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:63`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1993`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1995`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2079`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:2103`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3146`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3267` | High memory usage and large terminal payloads for wide scans; can stall/crash process. | Stream incremental rows only; bound retained rows; return summary/top-K by default; gate full series behind explicit flag and strict cap. |
| P1 | Expiring token policy vs client flow mismatch (Needs verification) | `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:25`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:28`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:269`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:275`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:206`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:284` | If default TTL is active, clients may become inactive without automatic token renewal. | In client, call `/license/refresh` before expiry and replace stored token atomically; keep `/license/verify` as entitlement check only. |
| P2 | Main renderer window is not sandboxed; renderer opens external URLs directly | `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:185`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:187`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:7194`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx:606` | Larger blast radius if renderer is compromised; weaker URL navigation control. | Enable `sandbox: true` on main BrowserWindow and route external navigation through IPC plus allowlisted `shell.openExternal`. |
| P2 | Admin endpoints are cookie-authenticated but have no CSRF token checks (Needs verification) | `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:427`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:450`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:497`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:529`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:593` | Cross-site request attempts against admin actions are not explicitly mitigated beyond cookie policy. | Add CSRF tokens for all admin POST forms and validate Origin/Referer. |
| P2 | Source duplication and fallback import logic increase drift/coupling risk | `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:257`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:268`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:276`; `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:62`; `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:85` | Two backend trees complicate debugging/release correctness and can drift over time. | Keep a single runtime source path (`backend/**`) and remove fallback import strategies that read `frontend/backend/**`. |
| P2 | Renderer monolith (7k+ lines) mixes API, storage, UI, settings, licensing | `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:147`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:269`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:1173`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:5520`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:6629`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:7327` | High change risk, difficult testing, slow onboarding. | Split into feature modules (API client, persistence, licensing UI, dashboard, settings) with isolated tests. |
| P2 | Unbounded localStorage growth for chart history | `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:301`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:324` | Storage bloat can hurt startup performance and eventually hit browser quota. | Add retention (count/age cap), compression, and pruning on write/read. |
| P2 | CI backend test target includes ad-hoc scripts with hardcoded/localhost dependencies | `C:\Users\sabaa\Downloads\codexhorary\.github\workflows\ci.yml:104`; `C:\Users\sabaa\Downloads\codexhorary\backend\test_engine.py:12`; `C:\Users\sabaa\Downloads\codexhorary\backend\test_simple.py:19`; `C:\Users\sabaa\Downloads\codexhorary\backend\test_api_request.py:11` | Flaky/non-portable CI signal and reduced trust in regression detection. | Exclude manual scripts from pytest discovery; convert them into deterministic tests with fixtures/mocks. |
| P2 | Packaging script allows non-deterministic dependency resolution | `C:\Users\sabaa\Downloads\codexhorary\package-app-new.bat:46` | Builds can differ across machines/time, undermining reproducibility. | Remove `npm install` fallback; fail build on `npm ci` failure. |
| P3 | Update event listeners have no cleanup/unsubscribe path | `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:6657`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:6663`; `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js:18`; `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js:22` | Potential duplicate callbacks/memory growth on remount cycles. | Expose unsubscribe functions in preload and return cleanup in renderer `useEffect`. |
| P3 | Verbose operational/health logging may expose internals | `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:54`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:135`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:521`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:551` | Information disclosure and noisy logs; potential leakage of paths/errors. | Reduce debug logging in production; sanitize/aggregate health error details for unauthenticated callers. |
| P3 | CI does not run lint/security checks even though lint script exists | `C:\Users\sabaa\Downloads\codexhorary\frontend\package.json:14`; `C:\Users\sabaa\Downloads\codexhorary\.github\workflows\ci.yml:87`; `C:\Users\sabaa\Downloads\codexhorary\.github\workflows\ci.yml:104` | Style/security regressions can merge undetected. | Add CI jobs for `npm run lint`, Python lint/type checks, and dependency vulnerability scanning. |

## Section C: Top 10 remediation backlog

| Priority | Remediation | Effort | Risk-reduction score |
|---|---|---|---|
| 1 | Replace SSE query-token auth with short-lived stream ticket flow | M | 10 |
| 2 | Remove global mutable `_engine` request sharing; enforce per-request isolation | L | 9 |
| 3 | Bound SSE memory/payloads (top-K only, optional full series) | M | 9 |
| 4 | Implement token refresh in desktop client and persist refreshed token | M | 8 |
| 5 | Add CSRF protection to licensing admin POST routes | M | 8 |
| 6 | Enable sandbox on main BrowserWindow and enforce external URL policy | M | 8 |
| 7 | Remove backend dual-path runtime fallback and package from one source tree | L | 7 |
| 8 | Refactor `App.jsx` into feature modules with isolated tests | L | 7 |
| 9 | Fix CI test scope (drop ad-hoc scripts, add deterministic license/electron tests) | M | 7 |
| 10 | Enforce deterministic packaging (`npm ci` only) plus add lint/security CI jobs | S | 6 |

## Section D: Fast wins in 1 day

- Remove `npm install` fallback from packaging script and fail hard on `npm ci` errors.
- Rename/move ad-hoc backend scripts (`backend/test_simple.py`, `backend/test_engine.py`) so CI does not treat them as unit tests.
- Add CI lint step using existing frontend lint script.
- Add chart retention cap in storage service (for example keep latest N items).
- Add preload unsubscribe helpers for update events and cleanup in settings `useEffect`.
- Disable high-verbosity startup/backend stdout mirroring in production builds.

## Section E: Open questions and assumptions

- `LICENSE_TOKEN_TTL_SECONDS` in production is unknown. If set to `0` (non-expiring), finding "token refresh mismatch" impact is lower. Needs verification.
- Expected concurrency model is unclear (single-user desktop vs parallel clients). If strictly single-client, race risk is lower but still present in threaded mode. Needs verification.
- Admin UI exposure model is unclear (private network/Cloudflare Access/public). CSRF risk depends on deployment boundary. Needs verification.
- It is unclear whether unsandboxed main renderer is intentional for compatibility constraints with current preload usage. Needs verification.
- The long-term source-of-truth strategy for `backend/**` vs `frontend/backend/**` is unclear; this report assumes single-source is desired. Needs verification.

## Section F: Remediation status (implemented 2026-03-05)

| Finding | Status | Implementation evidence |
|---|---|---|
| SSE URL token leakage | Resolved | Stream ticket mint/consume added at `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:298`, `:346`; renderer now mints tickets and uses `stream_ticket` at `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:121`, `:132`, `:246`, `:368`, `:563`. |
| Shared mutable engine under threaded server | Mitigated | Threaded serving disabled at `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:2028`, `:2051` and `C:\Users\sabaa\Downloads\codexhorary\backend\production_server.py:60`; engine mutation/read hotspots wrapped with lock at `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:989`, `:1036`, `:1318`; chart compute no longer restores shared settings (`:1283`). |
| Streaming memory growth | Resolved | Stream caps introduced at `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:65`; bounded buffers and dropped counters in transits stream at `:1981`, `:2000`, `:2099`, `:2139`; election stream bounding at `:3007`, `:3188`, `:3331`. |
| Token refresh flow mismatch | Resolved | Client refresh flow added in `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:28`, `:282`, `:291`, `:310`, and called from `getToken`/`verifyOnline` (`:273`, `:333`). |
| Unsandboxed renderer + direct external opens | Resolved | Main window sandbox enabled and navigation/window-open policy enforced in `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:227`, `:232`, `:238`; validated IPC open-external at `:311`; renderer callers migrated in `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:7223` and `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx:606`. |
| Admin CSRF gap | Resolved | CSRF token/origin validation added in `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:427`, `:484`, `:493`; enforced on admin POST routes (`:528`, `:584`, `:607`, `:617`, `:624`, `:657`, `:676`); hidden token fields added in templates at `C:\Users\sabaa\Downloads\codexhorary\licensing_server\templates\dashboard.html:5`, `:20` and `C:\Users\sabaa\Downloads\codexhorary\licensing_server\templates\license_detail.html:8`, `:12`, `:20`, `:69`. |
| Backend dual-path fallback import drift | Partially resolved | Runtime fallback import strategy removed; backend source import only at `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:369`. Packaging still copies backend into `frontend/backend/**` by design and should be revisited in a dedicated consolidation task. |
| Renderer monolith coupling | Not resolved (structural) | No large refactor performed in this pass; risk remains in `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx`. |
| Unbounded localStorage chart history | Resolved | Retention caps/pruning added in `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:270`, `:273`, `:329`, `:345`. |
| CI backend includes ad-hoc scripts | Resolved | CI test command now ignores manual scripts in `C:\Users\sabaa\Downloads\codexhorary\.github\workflows\ci.yml:110`. |
| Non-deterministic packaging dependency install | Resolved | `npm install` fallback removed; `npm ci` only at `C:\Users\sabaa\Downloads\codexhorary\package-app-new.bat:46`. |
| Update listener unsubscribe missing | Resolved | Preload now returns unsubscribe callbacks at `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js:9`, `:24`; renderer cleanup added in `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx:6681`. |
| Verbose health/startup logging | Resolved | Health error sanitization in `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:198`, `:604`, `:634`, `:694`, `:730`; production backend stdout mirroring gated in `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:147`, `:169`, `:175`. |
| Missing CI lint/security checks | Resolved | Frontend lint + backend bandit checks added in `C:\Users\sabaa\Downloads\codexhorary\.github\workflows\ci.yml:87`, `:104`, `:107`; lint config hardened in `C:\Users\sabaa\Downloads\codexhorary\frontend\package.json` and `C:\Users\sabaa\Downloads\codexhorary\frontend\.eslintrc.cjs`. |

## Section G: Runtime issue remediation log (2026-03-05)

| Reported runtime issue | Status | Implementation evidence |
|---|---|---|
| Dev server starts on `5173` but Electron dev shell still navigates `3000`, causing broken dev runtime/API path | Resolved | Electron app origin allowlist and dev URL aligned to `5173` in `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:17`, `:19`, `:255`; frontend launcher message aligned in `C:\Users\sabaa\Downloads\codexhorary\start-frontend.bat:47`. |
| Dev API calls from Vite origin fail due missing CORS allowlist for `5173` in packaged backend source tree | Resolved | `5173` origins added to both backend source trees: `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:156`, `:157` and `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\app.py:156`, `:157`. |
| Packaged AstroClock tabs show `Receptions` / `Compass` fetch failures while other tiles load | Resolved | Endpoints made public under AstroClock license guard in both backend trees: `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:183`, `:184` and `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\app.py:183`, `:184`; renderer error mapping improved in `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ReceptionsTile.jsx:93`, `:94` and `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\CompassTile.jsx:19`, `:20`. |
| `caniuse-lite` warning on frontend startup | Verified clean | `npx --yes update-browserslist-db@latest` in `C:\Users\sabaa\Downloads\codexhorary\frontend` now reports installed = latest with no target browser changes. |
| Closing packaged Electron app leaves backend process running in background (Windows) | Resolved | Added backend image-name tracking and fallback image kill on shutdown in `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js:29`, `:159`, `:389`, `:412`, `:415`, while preserving existing PID tree-kill and lifecycle hooks (`:400`, `:420`, `:421`, `:422`). |

Validation snapshot:
- Backend API smoke check from `Origin: http://localhost:5173` returned HTTP 200 for `/api/health?skip_network=true`, `/api/astro-clock/receptions`, and `/api/astro-clock/compass`.
