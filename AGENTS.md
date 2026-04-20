# Agent Guidelines for This Repository

This repo contains both source code and packaged build artifacts (Electron bundles, compiled backends). To avoid bugs and confusion, all code changes MUST be made in source files only.

Do not edit packaged artifacts

- Never modify files under these paths (read-only/output only):
  - `frontend/dist-electron/**`
  - `frontend/backend/build/**`
  - `frontend/dist/**`
  - `website/**` (generated site content)
  - Any `win-unpacked/**` or `resources/**` subfolders
  - Any `venv/**` or `node_modules/**` folders

Edit sources instead

- Backend source lives under:
  - `backend/**`
  - `frontend/backend/**` (Python utilities packaged with the app)
- Frontend source lives under:
  - `frontend/src/**`

Verification

- If you see a file in `frontend/dist-electron/win-unpacked/resources/backend/…`, find and edit its source twin in `backend/**` or `frontend/backend/**`.
- You can verify the running backend build by hitting a health/version endpoint when available; packaged builds should embed a version/commit.

Packaging

- Use `package-app-new.bat` to produce packaged builds; it must always consume source files from the directories listed above and never expect manual edits inside `dist-electron`.
- For the desktop release workflow that bumps the version, repackages, and uploads GitHub release assets, follow `docs/electron_updates.md`.

CI/Pre-commit (recommended)

- Add a pre-commit hook or CI check to block changes to the disallowed paths above. See `.githooks/pre-commit` for a sample script.
