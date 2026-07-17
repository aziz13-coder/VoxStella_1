# Agent Guidelines for This Repository

This repo contains both source code and packaged build artifacts (Electron bundles, compiled backends). To avoid bugs and confusion, all code changes MUST be made in source files only.

Do not edit packaged artifacts

- Never modify files under these paths (read-only/output only):
  - `backend/build/**`
  - `backend/dist/**`
  - `backend/*.spec`
  - `frontend/dist-electron/**`
  - `frontend/backend/build/**`
  - `frontend/backend/dist/**`
  - `frontend/backend/runtime/**`
  - `frontend/dist/**`
  - `website/**` (generated site content)
  - Any `win-unpacked/**` or `resources/**` subfolders
  - Any `venv/**` or `node_modules/**` folders

Edit sources instead

- Backend source lives under:
  - `backend/**` (canonical desktop backend source)
  - `frontend/backend/**` (legacy/source utilities; packaging never rewrites it)
- Frontend source lives under:
  - `frontend/src/**`

Verification

- If you see a file in `frontend/dist-electron/win-unpacked/resources/backend/…`, find and edit its source twin in `backend/**` or `frontend/backend/**`.
- You can verify the running backend build by hitting a health/version endpoint when available; packaged builds should embed a version/commit.

Packaging

- Use `package-app-new.bat` to produce packaged builds; it must always consume source files from the directories listed above and never expect manual edits inside `dist-electron`.
- Packaging stages only the PyInstaller runtime under `frontend/backend/runtime/**`; it never ships the Python source/test mirror.
- `frontend/backend/runtime/**` is generated staging output: build it through the packaging workflow and never edit or commit it.
- For the desktop release workflow that bumps the version, repackages, and uploads GitHub release assets, follow `docs/electron_updates.md`.

CI/Pre-commit

- CI blocks changes to the disallowed paths above.
- Run `powershell -ExecutionPolicy Bypass -File scripts/install-git-hooks.ps1`
  once per clone to install the same guard as an executable local pre-commit
  hook.
