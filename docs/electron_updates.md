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

Pinned release runtime
- Packaging and CI use exactly Node.js `22.23.1` with its bundled npm `10.9.8`.
- Python packaging uses exactly `uv 0.11.15`, uv-managed CPython `3.12.13`,
  and PyInstaller `6.21.0`.
- The Node pin is recorded in `.node-version`; npm is pinned by
  `frontend/package.json` through `packageManager` and exact `engines` values.
- `package-app-new.bat` runs `npm run verify:release-runtime` before any build
  work and fails if either executable has a different version.
- Do not upgrade Node or npm independently for a release. Update the pins,
  lockfile, workflows, assertion script, and this playbook together, then rerun
  the complete packaging gate.

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
1. Start from a completely clean named branch whose `HEAD` exactly matches its
   fetched upstream.
2. Run `docs\release-tools\release-build.bat X.Y.Z`. When a patch bump is
   needed, the helper updates the four version fields and exits before building.
3. Review, commit, and push that version-only change.
4. Rerun the same command. The helper now verifies clean/pushed provenance,
   runs the full package gates, creates a GitHub draft tied to the exact commit,
   verifies all uploaded bytes, then publishes it.
5. Verify these files exist under `frontend/dist-electron/` for the new version:
   - `latest.yml`
   - `VoxStella-Setup-X.Y.Z.exe`
   - `VoxStella-Setup-X.Y.Z.exe.blockmap`
6. Open `frontend/dist-electron/latest.yml` and confirm:
   - `version: X.Y.Z`
   - `path: VoxStella-Setup-X.Y.Z.exe`
   - file size and sha512 refer to the new installer
7. Confirm the installer, unpacked Electron executable, and packaged backend
   executable all have valid Authenticode signatures.
8. Verify the release page shows all three assets in state `uploaded`.

Packaging notes
- `package-app-new.bat` does the right repo-specific sequence:
  - verifies exactly Node.js 22.23.1 and bundled npm 10.9.8
  - verifies the tracked production licensing origin and Ed25519 trust root
  - recreates a Python 3.12 environment from the hash-locked requirements
  - audits both Python lockfiles and runs the high-severity Bandit source gate
  - runs backend tests
  - builds the backend runtime with exactly PyInstaller 6.21.0
  - installs frontend dependencies, lints, tests, and builds the frontend
  - stages only the compiled backend runtime
  - creates the unpacked Electron app
  - creates the NSIS installer
  - launches and probes the final updater-enabled packaged runtime, checking
    version, commit, Git tree, and licensing trust-root fingerprint
- The packaged backend is intentionally built as a PyInstaller `onedir` bundle:
  - source builder: `backend/build_backend.py`
  - packaged runtime location before Electron build: `frontend/backend/runtime/horary_backend/`
  - packaged runtime location after Electron build: `resources/backend/runtime/horary_backend/`
  - rationale: avoid the cold-start extraction penalty from PyInstaller `onefile`, which caused build-only API status lag and false offline flashes
- Backend preparation is fail-fast:
  - `frontend/scripts/prepare-backend.js` treats any runtime copy error as fatal
  - it never deletes or rewrites the tracked `frontend/backend/` source mirror
  - it stages only `frontend/backend/runtime/horary_backend/`
  - it verifies every copied runtime file by size and SHA-256
  - the optional trait corpus is embedded by PyInstaller under the compact
    `_internal/tc` root, where the frozen resolver can find it without pushing
    descriptive corpus filenames past Windows install-path limits
  - before NSIS runs, `scripts/check_windows_install_paths.py` projects every
    unpacked file and directory below a conservative default per-user install
    root and enforces 247 characters, preserving 12 characters of headroom below
    Windows' 259-visible-character ceiling
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
  - `latest.yml`
  - `VoxStella-Setup-X.Y.Z.exe`
  - `VoxStella-Setup-X.Y.Z.exe.blockmap`
- Keep `builder-debug.yml` local; it can contain absolute builder paths and is
  diagnostics, not updater input.
- Do not upload `win-unpacked/` as a folder.
- Do not upload generated `resources/` subfolders manually.

Manual GitHub UI flow
1. Open:
   - `https://github.com/aziz13-coder/VoxStella_1/releases`
2. Click `Draft a new release`.
3. Create tag `vX.Y.Z`.
4. Set release title `vX.Y.Z`.
5. Upload the three public assets from `frontend/dist-electron/`.
6. Publish the release. Do not leave it as draft.

Preferred scripted GitHub flow
- If the machine already has GitHub credentials stored in Git credential manager, the release can be published via the GitHub REST API without `gh`.
- Practical sequence:
  - use `git credential fill` for `github.com`
  - create a draft release `vX.Y.Z` targeting the verified commit
  - upload:
    - `VoxStella-Setup-X.Y.Z.exe`
    - `VoxStella-Setup-X.Y.Z.exe.blockmap`
    - `latest.yml` last
  - verify remote SHA-256 for every asset
  - publish the draft only after all checks pass
- Published versions are immutable. A failed upload remains a draft and must
  never replace assets on an already public release.

Repo helper script
- The repeatable local helper lives at:
  - `docs/release-tools/release-build.bat`
- Common commands:
  - `docs\release-tools\release-build.bat 3.0.1`
    - first invocation updates version sources and stops; after commit/push, the
      second packages and publishes release `v3.0.1`
  - `docs\release-tools\release-build.bat`
    - package the current source version only when no public release exists
  - `docs\release-tools\release-build.bat 3.0.1 -NoUpload`
    - bump and package locally, but do not upload
- `-UploadOnly` is deliberately rejected. Every upload must be preceded in the
  same helper invocation by a fresh package build, packaged-runtime smoke test,
  provenance verification, and signature verification.
- The helper validates:
  - exact one-patch version increments
  - clean source, named branch, fetched upstream equality, and tag provenance
  - source version alignment
  - unchanged clean `HEAD` and Git tree immediately after packaging and again
    immediately before any draft asset upload
  - required `frontend/dist-electron/` assets
  - `latest.yml` version, path, size, and recomputed SHA-512
  - gzip/JSON blockmap structure and checksum cardinality
  - embedded build version, commit, Git tree, and clean-build marker
  - Authenticode on all three shipped executables
  - GitHub release asset state, size, and SHA-256 after upload

Verification after publishing
1. Confirm the release exists at:
   - `https://github.com/aziz13-coder/VoxStella_1/releases/tag/vX.Y.Z`
2. Confirm all three public assets are present.
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

Release provenance invariant
- Every public release tag, source commit, embedded backend metadata, and
  installer must describe the same clean, pushed Git tree.
- The helper refuses dirty builds, unpushed commits, stale prebuilt-artifact
  uploads, unsigned executables, tag reuse, and public asset replacement.

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
