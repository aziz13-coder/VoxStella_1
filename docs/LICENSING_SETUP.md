# Licensing Setup

1. **Generate signing keys**
   ```bash
   cd licensing_server
   python -m venv .venv && .venv\Scripts\activate
   pip install -r requirements.txt
   python keys/generate_keys.py
   ```
   Copy the printed `public key (base64)` – you'll embed this into the desktop app.

2. **Run the licensing API**
   ```bash
    set ADMIN_TOKEN=your-strong-token
    set LICENSE_TOKEN_TTL_SECONDS=604800
    set LICENSE_VERIFY_INTERVAL_SECONDS=259200
    set LICENSE_CORS_ORIGINS=https://license.voxstella.app
    python app.py
    ```
    Expose it via Cloudflare Tunnel if you need public access.
   - `LICENSE_VERIFY_INTERVAL_SECONDS` is the renewable-license outage tolerance window. The default is now 72 hours.
   - Perpetual licenses now issue offline-capable tokens after activation; they do not require periodic refresh while the app is offline.

3. **Configure the desktop build**
   - Copy `frontend/license.config.example.json` to `frontend/license.config.json` if it doesn't exist.
   - Fill `publicKeyB64` with the base64 from step 1.
   - Set `serverUrl` to the HTTPS endpoint you expose (e.g., `https://license.voxstella.app`).
   - This file is bundled automatically by electron-builder and read at runtime; end users never need to set environment variables.

4. **Packaging**
    Build as usual (`npm run electron:build`).  The packaged app reads `license.config.json` from `resources/` and uses the embedded public key and server URL for activation/verification.

5. **Development**
   - Local debug builds default to `http://127.0.0.1:8787`.
   - Dev bypass now requires `ALLOW_DEV_LICENSE_BYPASS=1` and is ignored in packaged runtime.
   - You can override server/public-key values with env vars for rapid testing without editing config files.

6. **Cloudflare tunnel client**
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
