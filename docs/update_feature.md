Update Feature (Web-first, Electron-ready)

Overview
- Adds a non-intrusive update check visible in dev/prod web builds.
- Checks a JSON manifest (appcast) for the latest version and shows a banner.
- Provides a web fallback (open download URL) and future hook for Electron auto-updates.

What was added
- `frontend/src/utils/updateService.mjs`: Fetches manifest, compares versions, exposes `checkForUpdate` and `startUpdate`.
- `frontend/src/components/UpdateBanner.jsx`: UI banner shown only when a newer version exists.
- `frontend/src/Root.jsx`: Wraps `App` and `UpdateBanner` together.
- `frontend/public/appcast.json`: Sample manifest so you can test immediately in dev.
- Minimal change in `frontend/src/renderer.jsx` to render `Root` instead of `App`.

How it works
- Current version is read from `frontend/package.json` (Vite JSON import).
- Manifest URL is resolved from `VITE_UPDATE_MANIFEST_URL` or falls back to `/appcast.json` (same-origin).
- Version comparison is a small semver-like compare (major.minor.patch only).
- When an update is available, the banner offers:
  - “What’s new”: toggle release notes from the manifest
  - “Get update”: opens `downloadUrl` from the manifest in a new tab

Local testing (dev server)
1) From `frontend`, run the dev server as you normally do: `npm run dev`.
2) The included `public/appcast.json` specifies `latestVersion: 1.1.1`, while `frontend/package.json` is `1.1.0`, so the banner should appear.
3) Adjust `public/appcast.json` as you like to test different states.

Configuring for production
- Host a JSON manifest at a stable URL (e.g., on your site or CDN):
  {
    "latestVersion": "1.2.0",
    "downloadUrl": "https://your.domain/downloads/vox-stella-setup.exe",
    "notes": "Changes in 1.2.0..."
  }
- Set `VITE_UPDATE_MANIFEST_URL` in `frontend/.env` or CI environment:
  VITE_UPDATE_MANIFEST_URL=https://your.domain/appcast.json

Electron integration (future)
- `startUpdate()` checks for a `window.electronAutoUpdater` or `window.api.autoUpdater` surface.
- When you introduce Electron main/preload, expose a method like `checkAndInstall()` to hook into `electron-updater` and call `autoUpdater.checkForUpdatesAndNotify()` (or your flow) from the main process.
- Renderer then needs no changes; the banner will use the injected API when present.

Notes
- The banner is purely additive and does not affect existing flows.
- If you want to temporarily disable the check in a given environment, do not provide a manifest (or point it to a 404), and the banner stays hidden.

