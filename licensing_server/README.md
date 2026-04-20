Licensing Server (Ed25519) — Quick Start

Overview
- Issues signed activation tokens for Vox Stella using Ed25519.
- Enforces 1 device per license key (configurable).
- Supports activation, refresh, and deactivation.

Tech
- FastAPI + SQLite + PyNaCl (Ed25519 signing).

Endpoints
- POST /license/activate: { key, deviceId, email? } -> { token }
- POST /license/refresh: { token, deviceId } -> { token }
- POST /license/deactivate: { token? , key?, deviceId } -> { ok: true }

Token format
- Compact string: base64(signature).base64(payload)
- Payload JSON fields:
  - sub: string (user email or license id)
  - lic: string (license key id)
  - plan: string (e.g., "pro")
  - device: string (sha256 of machine-id + app id)
  - iat: number (issued at, seconds)
  - exp: number (expires at, seconds)
  - provisional?: boolean (client-created 24h fallback, not signed)

Device limit
- Max devices per key: 1 enforced in /license/activate.

Generate keys
1) python -m venv .venv && .venv\Scripts\activate
2) pip install -r requirements.txt
3) python keys/generate_keys.py
   - Produces `keys/ed25519_private.key` and `keys/ed25519_public.key`
   - **Do not commit these files.** They are ignored by Git and must be stored securely (e.g., Azure Key Vault, AWS Secrets Manager).
   - Copy the public key (base64) into an environment variable (`LICENSE_PUBLIC_KEY_B64`) used by both the backend and Electron main process.

Run server (dev)
- python app.py
- Default: http://127.0.0.1:8787

Mint license keys
- python scripts/mint_keys.py --count 5 --plan pro --max-devices 1
- Outputs keys and writes to SQLite db (licenses.db)

Deploy
- Host behind HTTPS (CORS allow your app origin if needed via `LICENSE_CORS_ORIGINS`).
- Protect mint_keys and admin operations by setting a strong `ADMIN_TOKEN`.
- Admin login is cookie-based (`/admin/login`); URL token query parameters are not used.

Environment essentials
- `LICENSE_TOKEN_TTL_SECONDS` – positive integer; defaults to 7 days, but renewable tokens are extended when needed to preserve the refresh grace window.
- `LICENSE_VERIFY_INTERVAL_SECONDS` – subscription entitlement refresh cadence (default 7 days).
- `LICENSE_SUBS_GRACE_SECONDS` – optional subscription grace (default 48h). With the default settings, renewable tokens remain locally valid for up to 48 hours after the weekly refresh boundary if the server cannot be reached.
- `LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS` – optional refresh cadence for newly issued perpetual tokens (default 0 in code; `run-licensing-server.bat` sets 21 days).
- `LICENSE_PERPETUAL_GRACE_SECONDS` – grace window for newly issued perpetual tokens that require refresh (default 72h).
- `LICENSE_SUBSCRIPTION_TERM_DAYS` – default subscription term used when the admin UI leaves period end blank (default 30 days).
- `LICENSE_CORS_ORIGINS` – comma-delimited origins allowed to call the API.
- `ADMIN_TOKEN` – required; admin UI refuses to start without it.
- `ADMIN_TOKEN_FILE` – optional explicit path to read admin token from disk.
- `LICENSE_PUBLIC_KEY_B64` – injected into the desktop app/backend to verify issued tokens.
