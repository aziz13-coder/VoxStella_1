Licensing Server (Ed25519) — Quick Start

Overview
- Issues signed activation tokens for Vox Stella using Ed25519.
- Enforces 1 device per license key (configurable).
- Supports activation, refresh, and deactivation.

Tech
- FastAPI + SQLite + PyNaCl (Ed25519 signing).

Endpoints
- GET /checkout/desktop-monthly: hardened public PayPal checkout intended for the OS system browser; returns a copyable subscription ID and receives no device/auth data.
- POST /license/activate: { key, deviceId, email? } -> { token }
- POST /license/activate-paypal: { subscriptionId, deviceId, email? } -> { token, status }
- POST /license/activate-paypal-purchase: { paypalId, deviceId, email? } -> { token, status }
- POST /license/refresh: { token, deviceId } -> { token }
- POST /license/deactivate: { token, deviceId, key? } -> { ok: true }. The signed token is mandatory; its exact device and license identity must match the request. The optional key is accepted only as a same-license compatibility field.
- POST /paypal/webhook: PayPal webhook listener that verifies PayPal signatures and updates subscription or one-time payment entitlements.

Token format
- Compact string: base64(signature).base64(payload)
- Payload JSON fields:
  - sub: string (user email or license id)
  - lic: string (license key id)
  - plan: string (e.g., "pro")
  - kind: string (`subscription` or `perpetual`)
  - device: string (sha256 of machine-id + app id)
  - iat: number (issued at, seconds)
  - verified_at: number (last authoritative verification time, seconds)
  - requires_entitlement_refresh: boolean
  - offline_capable: boolean
  - next_verify_at?: number (required when entitlement refresh is enabled)
  - exp?: number (expiry, when present; subscription tokens never exceed paid-through plus grace)
- Pending PayPal activation is an encrypted local record. It remains inactive and is never a signed license token or backend session.

Device limit
- Max devices per key: 1 enforced in /license/activate.

Generate keys
1) uv venv --python 3.12 .venv
2) uv pip sync --python .venv\Scripts\python.exe --require-hashes requirements-lock.txt
3) .venv\Scripts\python.exe keys/generate_keys.py
   - Produces `keys/ed25519_private.key` and `keys/ed25519_public.key`
   - **Do not commit these files.** They are ignored by Git and must be stored securely (e.g., Azure Key Vault, AWS Secrets Manager).
   - For production desktop releases, copy the public key (base64) into `frontend/license.config.json`, then update `PRODUCTION_LICENSE_PUBLIC_KEY_SHA256` in `frontend/main/security-policy.js` through the same reviewed source change.
   - Packaged Electron ignores public-key environment overrides. `LICENSE_PUBLIC_KEY_B64` is only for source-backend and development tooling.

Run server (dev)
- .venv\Scripts\python.exe app.py
- Default: http://127.0.0.1:8787

Dependency maintenance
- `requirements.txt` contains the reviewed direct pins; runtime/setup installs use the fully resolved `requirements-lock.txt`.
- `httpx2` is the transport dependency required by Starlette's `TestClient`
  for the licensing test suite; it is intentionally pinned even though server
  source does not import it directly.
- Regenerate the lock with CPython 3.12 resolution after intentionally changing a direct pin:
  `uv pip compile requirements.txt --python-version 3.12 --universal --generate-hashes --output-file requirements-lock.txt`
- Verify a clean environment with:
  `uv pip sync --python <path-to-python-3.12> --require-hashes requirements-lock.txt`

Mint license keys
- python scripts/mint_keys.py --count 5 --plan pro --max-devices 1
- Outputs keys and writes to SQLite db (licenses.db)

Deploy
- Host behind HTTPS (CORS allow your app origin if needed via `LICENSE_CORS_ORIGINS`).
- Protect mint_keys and admin operations by setting a strong `ADMIN_TOKEN`.
- Admin login is cookie-based (`/admin/login`); URL token query parameters are not used.
- The Cloudflare tunnel launcher defaults to HTTP/2 transport to avoid QUIC control-stream retries on networks that interfere with UDP. Override with `TUNNEL_TRANSPORT_PROTOCOL` if a different transport is needed.

Environment essentials
- `LICENSE_TOKEN_TTL_SECONDS` – positive integer; defaults to 7 days. A subscription token may be extended to cover its refresh grace, but is always capped at the authoritative paid-through time plus `LICENSE_SUBS_GRACE_SECONDS`.
- `LICENSE_VERIFY_INTERVAL_SECONDS` – subscription entitlement refresh cadence (default 7 days).
- `LICENSE_SUBS_GRACE_SECONDS` – optional subscription grace (default 48h). With the default settings, renewable tokens remain locally valid for up to 48 hours after the weekly refresh boundary if the server cannot be reached.
- `LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS` – optional refresh cadence for newly issued perpetual tokens (default `0` for both `python app.py` and `run-licensing-server.bat`, so perpetual tokens remain offline-capable).
- `LICENSE_PERPETUAL_GRACE_SECONDS` – grace window for newly issued perpetual tokens that require refresh (default 72h).
- `LICENSE_SUBSCRIPTION_TERM_DAYS` – default subscription term used when the admin UI leaves period end blank (default 30 days).
- `LICENSE_TOKEN_FUTURE_SKEW_SECONDS` – maximum accepted clock skew for refresh tokens (default 300 seconds). Refresh requires the signed token's exact device ID. An expired, validly signed token may recover only after the server confirms that the entitlement and same device activation remain active.
- `LICENSE_RATE_LIMIT_WINDOW_SECONDS` / `LICENSE_RATE_LIMIT_MAX_CLIENTS` – in-process rate-limit window and bounded client-state capacity (defaults 60 seconds / 4096 clients).
- `LICENSE_PUBLIC_RATE_LIMIT_REQUESTS`, `PAYPAL_ACTIVATION_RATE_LIMIT_REQUESTS`, `PAYPAL_WEBHOOK_RATE_LIMIT_REQUESTS`, `PAYPAL_CHECKOUT_RATE_LIMIT_REQUESTS`, and `ADMIN_LOGIN_RATE_LIMIT_REQUESTS` – request ceilings per client and window (defaults 60, 10, 120, 60, and 10).
- `LICENSE_CORS_ORIGINS` – comma-delimited origins allowed to call the API.
- `ADMIN_TOKEN` – required; admin UI refuses to start without it.
- `ADMIN_TOKEN_FILE` – optional explicit path to read admin token from disk.
- `LICENSE_PUBLIC_KEY_B64` – source-backend/development override for verifying issued tokens; packaged Electron uses the pinned `frontend/license.config.json` trust root.

PayPal environment
- The server auto-loads local `licensing_server\.env` and `licensing_server\paypal.env` files when present. `run-licensing-server.bat` also loads `paypal.env` and passes those values into the server window.
- Copy `paypal.env.example` to `paypal.env`, then fill in the real PayPal values. Do not commit `paypal.env`.
- `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` - server-side PayPal REST credentials used to verify subscriptions and webhook signatures.
- `PAYPAL_PLAN_ID` - legacy single expected subscription plan ID, for example `P-83N24493LW950963HNIIXO7Q`.
- `PAYPAL_ALLOWED_PLAN_IDS` or `PAYPAL_PLAN_IDS` - optional comma-delimited subscription plan IDs. The server also knows the current Vox Stella in-app $25 plan (`P-83N24493LW950963HNIIXO7Q`) and website $35 plan (`P-4L214935JK8549417NIAB5KY`).
- `PAYPAL_WEBHOOK_ID` - webhook ID from the PayPal app configuration, required for signature verification.
- `PAYPAL_API_BASE` - optional; defaults to `https://api-m.paypal.com`. Use `https://api-m.sandbox.paypal.com` for sandbox testing.
- `PAYPAL_DESKTOP_CLIENT_ID` and `PAYPAL_DESKTOP_PLAN_ID` - public browser-checkout identifiers used only by `/checkout/desktop-monthly`; both have the current in-app offer as a checked-in default. The configured plan must also be in the allowed plan set.
- `PAYPAL_LICENSE_PLAN` - optional license plan label stored in signed tokens; defaults to `premium-desktop-monthly`.
- `PAYPAL_LICENSE_MAX_DEVICES` - optional device limit for PayPal-created licenses; defaults to `1`.
- `PAYPAL_ONETIME_AMOUNT` - optional expected one-time payment amount; defaults to `250.00`.
- `PAYPAL_ONETIME_CURRENCY` - optional expected one-time payment currency; defaults to `USD`.
- `PAYPAL_ONETIME_LICENSE_PLAN` - optional license plan label for one-time website purchases; defaults to `premium-desktop-lifetime`.
- `PAYPAL_ONETIME_LICENSE_MAX_DEVICES` - optional device limit for one-time PayPal-created licenses; defaults to `1`.
- `PAYPAL_PAYEE_MERCHANT_ID` - required for every one-time capture activation and webhook, including sandbox, and matched against the authoritative capture/order payee.
- At least one stable purchase binding is also required in every environment: `PAYPAL_ONETIME_PRODUCT_ID`, `PAYPAL_ONETIME_CUSTOM_ID`, `PAYPAL_ONETIME_CUSTOM_ID_PREFIX`, `PAYPAL_ONETIME_INVOICE_ID`, or `PAYPAL_ONETIME_INVOICE_ID_PREFIX`. Configure every stable field the checkout supplies; missing or mismatched configured metadata is rejected.
- `PAYPAL_PAYEE_EMAIL` - optional additional exact payee binding. Merchant ID remains mandatory even when this email check is configured.

PayPal automation
- Configure the PayPal webhook URL as `https://license.voxstella.app/paypal/webhook` or your deployed equivalent.
- Subscribe it to subscription lifecycle events, especially `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.CANCELLED`, `BILLING.SUBSCRIPTION.SUSPENDED`, `BILLING.SUBSCRIPTION.EXPIRED`, `BILLING.SUBSCRIPTION.PAYMENT.FAILED`, and `PAYMENT.SALE.COMPLETED`.
- Also subscribe it to one-time payment events for the website $250 checkout: `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.REFUNDED`, `PAYMENT.CAPTURE.REVERSED`, `PAYMENT.CAPTURE.DENIED`, and `PAYMENT.CAPTURE.DECLINED`.
- Desktop checkout calls `/license/activate-paypal` immediately after PayPal approval so the app can unlock on the same device without manually emailing a key.
- The hardened `/checkout/desktop-monthly` alternative is designed to open with the operating system's external-browser API. It never receives an app token, license key, email, or device ID. After approval it displays and copies the PayPal subscription ID for the buyer to paste back into Vox Stella.
- Website buyers can use Settings -> License and Activation -> PayPal website purchase ID. For the $35 website subscription, they enter the PayPal subscription ID. For the $250 one-time checkout, they enter the PayPal transaction/capture ID from the PayPal receipt.
- Webhooks keep the existing subscription license current for renewals, cancellation, suspension, expiry, refunds, and PayPal retries.
- One-time payment webhooks create a normal perpetual license row in the same `licenses` table. Existing manually issued license keys continue to activate through `/license/activate`.
- PayPal resource transitions are serialized with entitlement writes. Subscription snapshots are ordered by PayPal's `status_update_time` and `update_time` clocks; older snapshots are consumed without changing the entitlement, and equal-clock conflicts deterministically retain the more restrictive state. A suspended subscription resumes only from a strictly newer `ACTIVE` snapshot.
- A nonterminal one-time `COMPLETED` transition requires the fetched capture's `update_time`; webhook notification time cannot substitute for a missing provider resource clock. Terminal refund/reversal/denial/decline tombstones may retain verified webhook time for audit without relying on it for their absorbing behavior.
- Verified one-time refunds, reversals, denials, and declines authoritatively resolve missing capture/order aliases and create permanent tombstones, even when the entitlement has not been created yet. A later `COMPLETED` snapshot can never reactivate those PayPal IDs.
- Webhook claims record an applied, stale, terminal-blocked, or unsupported disposition. The route is synchronous so FastAPI runs its blocking PayPal HTTPS verification/fetches in a worker thread instead of blocking the async event loop.
- Buyer-supplied email is only a fallback; authoritative PayPal subscriber/payer email wins when PayPal returns one.
- OAuth access tokens are cached in memory until shortly before PayPal expiry and are refreshed once on an API `401`.
