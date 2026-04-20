# Technical Findings Memo (2026-03-05)

## Section A: Executive technical summary
- Electron boundary is mostly correct: main process handles backend lifecycle and IPC in `C:\Users\sabaa\Downloads\codexhorary\frontend\main.js`, preload exposes a limited bridge in `C:\Users\sabaa\Downloads\codexhorary\frontend\preload.js`, renderer consumes only `window.API_BASE_URL` and `window.electronAPI` from `C:\Users\sabaa\Downloads\codexhorary\frontend\src\App.jsx` and `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs`.
- Python API architecture is a Flask monolith (`C:\Users\sabaa\Downloads\codexhorary\backend\app.py`) plus a very large Astro Clock blueprint (`C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py`) with many heavy compute and SSE endpoints.
- Licensing server architecture is a FastAPI service (`C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py`) using SQLite (`licenses`, `activations`) and Ed25519 token signing/verification.
- Startup/runtime flow is: Electron `app.whenReady` -> spawn backend -> wait on `/api/health` -> create BrowserWindow -> initialize licensing/update IPC -> renderer pings `/api/version` and fetches license status.
- Highest-risk security issue: sensitive materials are present in-tree (admin token and Ed25519 private signing key), which can enable full admin takeover and token minting if leaked.
- Highest-risk runtime issue: two streaming endpoints can run very large scan loops without hard caps, allowing expensive requests to consume CPU for long periods.
- License/auth boundary is conceptually sound for request/response APIs (Bearer token + Ed25519 verification), but streaming uses EventSource without token injection while backend requires a token for most `/api/astro-clock/*` paths.
- Development runtime is permissive: license guard bypasses in dev mode and server binds to `0.0.0.0` with debug enabled.
- Reliability gaps: licensing network calls in Electron main process have no timeout/retry semantics; failures can hang long-running IPC calls.
- Maintainability risk is structural: backend source is mirrored into `frontend/backend`; current content is identical now, but the dual-tree model is drift-prone.
- Packaging pipeline robustness is mixed: build orchestration exists, but `prepare-backend.js` copies too much source content before packaging (including artifact-heavy folders).
- Test/CI coverage is partial: frontend `npm test` runs only two node scripts; Vitest-based UI test file exists but is not wired into package scripts; no repo-level CI workflow is present.

## Section B: Findings (sorted by severity)

| Severity | Issue | Evidence (absolute file:line) | Impact | Recommended fix |
|---|---|---|---|---|
| P0 | Ed25519 private signing key is present in repository tree | `C:\Users\sabaa\Downloads\codexhorary\licensing_server\keys\ed25519_private.key:1`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:21`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:132`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:149` | Anyone obtaining this key can mint valid license tokens and bypass licensing controls. | Immediately rotate signing keys, remove key material from repository/history, load private key from a secret store or deployment-only file outside repo, and force token reissue. |
| P0 | Plain admin token file is present in repository tree | `C:\Users\sabaa\Downloads\codexhorary\licensing_server\.admin_token:1`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:398`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:414`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:418` | Exposure of this token grants admin UI access (license creation, revocation, deletion). | Rotate admin token immediately; remove file from repo/history; require `ADMIN_TOKEN` from deployment secrets only; optionally replace static token auth with short-lived session login. |
| P1 | Development backend runs with license bypass + debug on network interface | `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:184`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:187`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1949`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1950`; `C:\Users\sabaa\Downloads\codexhorary\start-backend.bat:64` | In dev launches, backend is reachable on LAN and protected endpoints bypass license checks. | Default dev host to `127.0.0.1`, keep debug off unless explicitly requested, and gate bypass on a dedicated explicit dev flag plus loopback-only bind. |
| P1 | Streaming auth mismatch: backend requires license token, frontend SSE cannot send one | `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:197`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:202`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:229`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:350`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:544` | Licensed streaming features can fail in production (402/403) or force insecure auth workarounds. | Replace EventSource auth path with `fetch` streaming that carries `Authorization`, or add short-lived signed query token validated server-side for SSE only. |
| P1 | Unbounded scan loops in SSE endpoints (resource exhaustion risk) | `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1929`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:1944`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3105` | Very large time windows can tie up worker threads and degrade overall API responsiveness. | Enforce max window size + max step count at request validation, and hard-stop loops with a server-side cap similar to `scan_morin_transits_window` safeguards. |
| P1 | Licensing server calls from Electron main process have no timeout/retry controls | `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:140`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:166`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:192` | Activation/verification/deactivation can hang under network faults and block UX-critical IPC paths. | Wrap each fetch with `AbortController` timeouts and bounded retry/backoff; return explicit timeout errors to renderer. |
| P2 | License token persistence falls back to plaintext file when keytar is unavailable | `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:43`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:75`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:90`; `C:\Users\sabaa\Downloads\codexhorary\frontend\main\license.js:92` | Local token theft/tampering risk increases on systems without keytar. | Use OS-protected encryption fallback (e.g., DPAPI/Keychain wrapper) with integrity check; avoid raw JSON token storage. |
| P2 | API returns raw internal exception text to clients | `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:314`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:315`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1355`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:1365` | Internal implementation details leak to callers and create unstable, non-contractual error surfaces. | Return stable public error codes/messages, log full exception server-side with correlation IDs. |
| P2 | Packaging prep script copies entire backend tree into `frontend/backend` (artifact-heavy) | `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:14`; `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:37`; `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:60` | Build speed/disk usage regressions and higher risk of artifact contamination or accidental commits. | Switch to allowlist copy (runtime `.py/.yaml` + executable only), explicitly exclude `build`, `dist`, `venv`, caches, and logs. |
| P2 | Dual backend trees increase long-term drift/coupling risk | `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:37`; `C:\Users\sabaa\Downloads\codexhorary\frontend\scripts\prepare-backend.js:38`; `C:\Users\sabaa\Downloads\codexhorary\frontend\package.json:106`; `C:\Users\sabaa\Downloads\codexhorary\frontend\package.json:122` | Parallel trees complicate code ownership, reviews, and release confidence. | Keep only one authoritative backend tree and generate packaged mirror as a build artifact that is excluded from source control. |
| P2 | Test wiring is incomplete (frontend Vitest file not executed; backend test stack not pinned) | `C:\Users\sabaa\Downloads\codexhorary\frontend\package.json:34`; `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\verification.test.js:5`; `C:\Users\sabaa\Downloads\codexhorary\backend\requirements.txt:47` | Important UI/license paths can regress without automated detection. | Add `vitest` + Testing Library deps/scripts and include in CI; add `pytest` dev dependencies and standardized backend test command. |
| P2 | Snap persistence uses code-directory JSON storage with no retention controls | `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:841`; `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:842`; `C:\Users\sabaa\Downloads\codexhorary\backend\snaps_store.py:10`; `C:\Users\sabaa\Downloads\codexhorary\backend\snaps_store.py:36` | Risk of write failures in installed locations and gradual disk growth. | Move snap storage to user-writable app data path and cap retained snapshots (count/age). |
| P3 | Timezone cache is unbounded in Flask app process | `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:674`; `C:\Users\sabaa\Downloads\codexhorary\backend\app.py:754` | Long-running process can accumulate memory with high-cardinality locations. | Replace with bounded LRU/TTL cache. |
| P3 | Admin license key generation uses non-cryptographic RNG | `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:450`; `C:\Users\sabaa\Downloads\codexhorary\licensing_server\app.py:453` | Lower entropy guarantees vs CSPRNG in a security-sensitive identifier. | Use `secrets.choice` (or `secrets.token_urlsafe` with formatting) for generated keys. |

## Section C: Top 10 remediation backlog

| Priority | Remediation | Effort | Risk-reduction score (1-10) |
|---|---|---|---|
| 1 | Rotate/remove committed secrets (`.admin_token`, signing key), move to deployment secret management | M | 10 |
| 2 | Enforce loopback-only + explicit debug flag for dev backend; disable implicit license bypass | S | 9 |
| 3 | Add authenticated streaming strategy (fetch-stream or signed SSE token) | M | 8 |
| 4 | Add server-side hard limits for streaming/scanning ranges and steps | M | 8 |
| 5 | Add timeout + retry/backoff in `frontend/main/license.js` network paths | S | 7 |
| 6 | Replace plaintext token fallback with OS-protected encrypted storage | M | 7 |
| 7 | Standardize API error contracts; remove raw exception echoing | S | 6 |
| 8 | Convert backend mirror workflow to single source-of-truth + allowlist copy | M | 6 |
| 9 | Wire complete frontend/backend test commands and CI execution | M | 6 |
| 10 | Move snap storage to user data + retention policy; bound timezone cache | S | 5 |

## Section D: Fast wins in 1 day
- Rotate `ADMIN_TOKEN`, regenerate Ed25519 keys, and invalidate old tokens.
- Set dev backend default host to `127.0.0.1` and require explicit opt-in for debug mode.
- Add per-endpoint request guards for max `range_hours`, max date span, and min/max `step_minutes` in streaming routes.
- Add `AbortController` timeout wrapper (e.g., 10s/20s) around all licensing-server fetch calls.
- Change `_error_handler`/`calculate_chart` responses to stable public errors while logging full internals server-side.
- Add cache cap for `_timezone_cache` and retention cap for `snaps_store` as interim safeguards.
- Update `prepare-backend.js` to exclude `build`, `dist`, `venv`, logs, and cache directories.
- Add `npm run test:ui` (Vitest) and backend `pytest` command hooks, then run both in a CI workflow.

## Section E: Open questions / assumptions
- Needs verification: whether `licensing_server/.admin_token` and `licensing_server/keys/ed25519_private.key` are committed in git history or only present in local workspace.
- Needs verification: intended production auth design for SSE endpoints (`/transits/window/stream`, `/election/suggest/stream`, `/stream`) since current frontend transport cannot attach Bearer headers.
- Assumption: packaged backend process is expected to remain localhost-only (`127.0.0.1`) and not internet-exposed.
- Assumption: `frontend/backend/**` is generated/prepared packaging input rather than a manually maintained second source tree.
- Needs verification: whether a CI system exists outside this repository (no in-repo workflow files found).
