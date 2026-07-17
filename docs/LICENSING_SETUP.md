# Licensing Setup

1. **Generate signing keys**
   ```bash
   cd licensing_server
   uv venv --python 3.12 .venv
   uv pip sync --python .venv\Scripts\python.exe --require-hashes requirements-lock.txt
   .venv\Scripts\python.exe keys/generate_keys.py
   ```
   Copy the printed `public key (base64)` – you'll embed this into the desktop app.

2. **Run the licensing API**
   ```bash
   set ADMIN_TOKEN=your-strong-token
   set LICENSE_TOKEN_TTL_SECONDS=604800
   set LICENSE_VERIFY_INTERVAL_SECONDS=604800
   set LICENSE_SUBS_GRACE_SECONDS=172800
   set LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS=0
   set LICENSE_CORS_ORIGINS=https://license.voxstella.app
   .venv\Scripts\python.exe app.py
   ```
   Expose it via Cloudflare Tunnel if you need public access.
   - Direct startup and `run-licensing-server.bat` use the same policy: subscription refresh every 7 days with 48 hours of grace; perpetual licenses are offline-capable and do not require periodic refresh.
   - To opt perpetual licenses into periodic verification, set `LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS` explicitly before either startup path. `LICENSE_PERPETUAL_GRACE_SECONDS` defaults to 72 hours.
   - A subscription token's `next_verify_at` and `exp` are capped at PayPal/admin paid-through plus subscription grace. Disabling the normal TTL cannot create an unbounded subscription token.
   - `/license/refresh` requires an exact match between the signed token device and request device. An expired signed token can recover only after the server revalidates the current entitlement and that same device activation; future-issued or malformed tokens are rejected.
   - `/license/deactivate` also requires a valid signed token and exact token/request device binding. Its license key is derived from the signed token; an optional request key is accepted only when it identifies that same license. Admin device removal remains a separate authenticated/CSRF-protected endpoint.
   - Public licensing, PayPal activation/webhook, and admin-login endpoints have bounded in-memory rate limits. See `licensing_server/README.md` for the tuning variables.

3. **Configure the desktop production trust root**
   - `frontend/license.config.json` is checked-in source containing only the public Ed25519 verification key and the fixed production origin. It is intentionally not a secret.
   - Rotate `publicKeyB64` through a reviewed source change and a new release, and update `PRODUCTION_LICENSE_PUBLIC_KEY_SHA256` in `frontend/main/security-policy.js` to the new public-key fingerprint. Packaged builds reject any other key or licensing origin.
   - Run `npm run verify:license-trust-root` before packaging. The release clean-tree/provenance gates ensure the bundled trust root comes from the tagged source.
   - `frontend/license.config.example.json` is a development template only; do not substitute it into a production package.

4. **Packaging**
   - Produce desktop packages only through the repository-root `package-app-new.bat`.
   - Do not use `npm run electron:build` for a release; it bypasses the pinned-runtime, audit, full-test, provenance, and packaged-smoke gates.
   - The packaged app reads `license.config.json` from `resources/` and uses the embedded public key and server URL for activation/verification.

5. **Development**
   - Local debug builds default to `http://127.0.0.1:8787`.
   - Dev bypass now requires `ALLOW_DEV_LICENSE_BYPASS=1` and is ignored in packaged runtime.
   - For browser-only testing with `start-backend.bat --strict-license`, set `VITE_DEV_LICENSE_TOKEN` to a valid server-signed test token before starting Vite. This value is exposed to the local browser bundle, so never use or commit a production credential.
   - When `VITE_DEV_LICENSE_TOKEN` is unset, browser development sends no license header and therefore requires the explicit backend bypass. Electron development obtains its short-lived renderer session through the preload bridge instead.
   - You can override server/public-key values with env vars for rapid testing without editing config files.

6. **Configure PayPal verification**
   - Copy `licensing_server\paypal.env.example` to `licensing_server\paypal.env`; never commit the populated file.
   - Configure `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, and the allowed subscription plan IDs.
   - Keep amount/currency checks enabled for one-time purchases. One-time capture activation and webhooks fail closed in every environment, including sandbox, unless `PAYPAL_PAYEE_MERCHANT_ID` and at least one stable product/custom/invoice binding are configured. Use bindings from the same PayPal environment as `PAYPAL_API_BASE`, and configure every stable identity field the checkout returns:
     - `PAYPAL_ONETIME_PRODUCT_ID`
     - `PAYPAL_ONETIME_CUSTOM_ID` or `PAYPAL_ONETIME_CUSTOM_ID_PREFIX`
     - `PAYPAL_ONETIME_INVOICE_ID` or `PAYPAL_ONETIME_INVOICE_ID_PREFIX`
     - `PAYPAL_PAYEE_MERCHANT_ID`
     - `PAYPAL_PAYEE_EMAIL`
   - `PAYPAL_PAYEE_EMAIL` is an optional additional check; it does not replace the required merchant-ID binding. Missing or mismatched configured capture/order metadata is rejected. Buyer-entered email never overrides an authoritative PayPal subscriber/payer email.
   - PayPal OAuth access tokens are cached only in memory until shortly before their reported expiry and refreshed once after an API `401`.
   - Keep PayPal resource timestamps in webhook/API fixtures. Subscription lifecycle and general updates are applied monotonically from `status_update_time`/`update_time`; activation and webhook reconciliation both fail closed when the fetched subscription omits both clocks. Webhook `create_time` is retained for event audit only and never orders subscription state. If two contradictory subscription snapshots have the same provider version, the more restrictive state wins regardless of delivery order; recovery requires a strictly newer PayPal version.
   - Completed one-time captures likewise require the fetched capture's `update_time`; webhook `create_time` never substitutes for a missing nonterminal capture clock. Terminal refund/reversal/denial/decline tombstones remain absorbing even when their notification clock is absent or malformed.
   - Refund/reversal/denial/decline notifications resolve missing capture/order aliases through PayPal and permanently tombstone them, including refund-before-entitlement delivery. Never delete these tombstones to retry an old purchase; a legitimate repurchase must use new PayPal resource IDs.
   - Database startup computes the fixed-point closure of explicit terminal one-time evidence across every connected capture/order alias before atomically consolidating duplicate IDs and creating unique indexes. This preserves terminal provenance even when duplicate cleanup clears an alias. A generic admin-disabled purchase is not inferred to be a PayPal terminal event. Migrated restrictive subscription state remains provisional until the first fresh, timestamped PayPal snapshot.
   - `PAYPAL_DESKTOP_CLIENT_ID` and `PAYPAL_DESKTOP_PLAN_ID` control the public `/checkout/desktop-monthly` page. The checked-in defaults match the existing in-app monthly offer; both values are validated before rendering.
   - Open this checkout with the operating system's external-browser API, never inside Electron. Do not append a token, device ID, email, or license key. The hardened page uses a nonce-based PayPal-only CSP and returns only a subscription ID for the buyer to copy back into Vox Stella.

7. **Verify and run the Cloudflare tunnel client**
   - Run the licensing suite after configuration changes:
   ```powershell
   licensing_server\.venv\Scripts\python.exe -m pytest -q licensing_server
   ```
   - The licensing tunnel launcher now prefers a managed user install at:
     - `%LOCALAPPDATA%\Cloudflared\cloudflared.exe`
   - Install or update it with:
   ```powershell
   powershell -ExecutionPolicy Bypass -File licensing_server\scripts\install-cloudflared.ps1
   ```
  - The launcher fallback order is:
     - `CLOUDFLARED_EXE` env var
     - `%LOCALAPPDATA%\Cloudflared\cloudflared.exe`
     - `cloudflared` on `PATH`
     - legacy `C:\Users\sabaa\Downloads\cloudflared-windows-amd64.exe`
  - The launcher defaults `TUNNEL_TRANSPORT_PROTOCOL` to `http2` to avoid noisy or unstable QUIC control-stream retries on networks that interfere with UDP.
  - To test another transport temporarily, set `TUNNEL_TRANSPORT_PROTOCOL` before running `licensing_server\run_cloudflared.bat`.
