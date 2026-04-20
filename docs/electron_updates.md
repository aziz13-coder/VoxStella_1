Electron Release Workflow (Version Bump, Repackage, GitHub Upload)

Purpose
- This is the canonical release playbook for the Electron desktop app in this repo.
- Use it when the task is "bump the build one notch, repackage, and upload to GitHub Releases."
- Keep this repo-specific. The paths, packaging script, and GitHub upload target here are not generic.

Guardrails
- Edit source files only. Never hand-edit generated artifacts under:
  - `frontend/dist-electron/**`
  - `frontend/dist/**`
  - `frontend/backend/build/**`
  - `website/**`
  - any `win-unpacked/**`, `resources/**`, `venv/**`, or `node_modules/**`
- Produce release artifacts only through `package-app-new.bat`.
- Upload release assets from `frontend/dist-electron/`, but do not treat those generated files as source.

Release target
- GitHub Releases repo:
  - `https://github.com/aziz13-coder/VoxStella_1/releases`
- Electron publish target is configured in:
  - `frontend/package.json`
- Relevant fields:
  - `version`
  - `build.buildVersion`
  - `build.publish[0].owner`
  - `build.publish[0].repo`

Versioning rule
- Use semantic patch bumps only, one notch at a time:
  - `1.4.8` -> `1.4.9`
- Keep these values aligned:
  - release tag: `v1.4.9`
  - release title: `v1.4.9`
  - installer: `VoxStella-Setup-1.4.9.exe`
  - `latest.yml` contents

Files to update
- `frontend/package.json`
  - bump `"version"`
  - bump `"build.buildVersion"`
- `frontend/package-lock.json`
  - bump the root `"version"`
  - bump the top-level package entry `"packages"."".version"`

Release procedure
1. Bump the source version in:
   - `frontend/package.json`
   - `frontend/package-lock.json`
2. Rebuild the release artifacts from source:
   - PowerShell:
     - `$env:NO_OPEN_EXPLORER='1'; cmd /c package-app-new.bat`
3. Wait for packaging to finish successfully.
4. Verify these files exist under `frontend/dist-electron/` for the new version:
   - `builder-debug.yml`
   - `latest.yml`
   - `VoxStella-Setup-X.Y.Z.exe`
   - `VoxStella-Setup-X.Y.Z.exe.blockmap`
5. Open `frontend/dist-electron/latest.yml` and confirm:
   - `version: X.Y.Z`
   - `path: VoxStella-Setup-X.Y.Z.exe`
   - file size and sha512 refer to the new installer
6. Publish GitHub release `vX.Y.Z` and upload the four files above.
7. Verify the release page shows all four assets in state `uploaded`.

Packaging notes
- `package-app-new.bat` does the right repo-specific sequence:
  - builds the backend runtime bundle
  - installs frontend dependencies
  - builds the frontend
  - prepares backend resources
  - creates the unpacked Electron app
  - creates the NSIS installer
- The packaged backend is intentionally built as a PyInstaller `onedir` bundle:
  - source builder: `backend/build_backend.py`
  - packaged runtime location before Electron build: `frontend/backend/runtime/horary_backend/`
  - packaged runtime location after Electron build: `resources/backend/runtime/horary_backend/`
  - rationale: avoid the cold-start extraction penalty from PyInstaller `onefile`, which caused build-only API status lag and false offline flashes
- Backend preparation is fail-fast:
  - `frontend/scripts/prepare-backend.js` now treats any backend copy error as fatal
  - it verifies the copied backend source manifest in `frontend/backend/`
  - it separately verifies the copied PyInstaller runtime bundle in `frontend/backend/runtime/horary_backend/`
  - if a required backend source file or copied runtime asset is missing, packaging must stop instead of shipping a partial backend
- Process cleanup is workspace-scoped:
  - `package-app-new.bat` uses `scripts/stop-workspace-packaging-processes.ps1`
  - the helper only stops this repo's matching `node.exe`, `electron.exe`, `horary_backend.exe`, or unpacked `Vox Stella.exe` processes
  - it no longer uses image-wide `taskkill` calls for `node.exe`, `electron.exe`, or `esbuild.exe`
  - the packaging script now passes a normalized workspace path into the helper so PowerShell does not receive a trailing-backslash argument that breaks `Resolve-Path`
- The script writes logs into:
  - `build-logs/`
- It may print:
  - `ERROR: Input redirection is not supported, exiting the process immediately.`
- In observed runs, that message appeared after a successful packaging completion and did not prevent output generation. Still verify the new files in `frontend/dist-electron/`.

What to upload to GitHub Releases
- Upload exactly these release assets from `frontend/dist-electron/`:
  - `builder-debug.yml`
  - `latest.yml`
  - `VoxStella-Setup-X.Y.Z.exe`
  - `VoxStella-Setup-X.Y.Z.exe.blockmap`
- Do not upload `win-unpacked/` as a folder.
- Do not upload generated `resources/` subfolders manually.

Manual GitHub UI flow
1. Open:
   - `https://github.com/aziz13-coder/VoxStella_1/releases`
2. Click `Draft a new release`.
3. Create tag `vX.Y.Z`.
4. Set release title `vX.Y.Z`.
5. Upload the four assets from `frontend/dist-electron/`.
6. Publish the release. Do not leave it as draft.

Preferred scripted GitHub flow
- If the machine already has GitHub credentials stored in Git credential manager, the release can be published via the GitHub REST API without `gh`.
- Practical sequence:
  - use `git credential fill` for `github.com`
  - create or fetch release `vX.Y.Z`
  - upload:
    - `builder-debug.yml`
    - `latest.yml`
    - `VoxStella-Setup-X.Y.Z.exe.blockmap`
    - `VoxStella-Setup-X.Y.Z.exe`
- If upload of the `.exe` times out, rerun the upload with a longer timeout; the installer is large and may take several minutes.

Verification after publishing
1. Confirm the release exists at:
   - `https://github.com/aziz13-coder/VoxStella_1/releases/tag/vX.Y.Z`
2. Confirm all four assets are present.
3. Confirm `latest.yml` on the release points at `VoxStella-Setup-X.Y.Z.exe`.
4. On an installed older build, use the app update check and confirm it detects the higher version.

Failure modes
- Bumping only `package.json` and forgetting `package-lock.json`
- Uploading only the `.exe` without `latest.yml`
- Uploading the wrong `.blockmap` for a different installer version
- Leaving the release as draft
- Assuming `frontend/dist-electron/` should be edited manually
- Timing out the `.exe` upload because the command timeout is too short
- Forcing packaging through after a backend copy or verification failure
- Reintroducing image-wide process kills that terminate unrelated Node or Electron work on the same machine

Important repo note
- This workspace has been operated as a source snapshot rather than a normal Git checkout.
- Bumping the local source version and packaging it does not automatically push those source changes to GitHub code.
- If the GitHub repository should also reflect the source bump in version-controlled files, push those source changes separately.

Backend startup status note
- Electron now owns backend lifecycle status for packaged startup.
- Root cause: packaged startup was slower and burstier than dev, and the status layer could show `API Offline` while the backend was still booting.
- The fixed model is:
  - main process marks backend state as `checking` during startup and restart grace windows
  - main process probes `/api/version` for reachability instead of using diagnostic health checks for liveness
  - packaged startup uses a longer boot grace window and requires multiple failed probes before reporting `offline`
  - preload exposes `backend:get-status`, `backend:refresh-status`, and `backend:status`
  - renderer subscribes to that lifecycle state instead of guessing from an unsynchronized first ping
- Result: packaged startup should stay in `Checking...` until the backend is actually reachable or genuinely offline.

When to turn this into a skill
- If this release workflow becomes routine across multiple sessions, a local Codex skill or a repo-local script is reasonable.
- For now, this document is the source of truth because the process is tightly coupled to this repo's packaging script, paths, and GitHub release target.
