# Backend Source Ownership

## Authoritative source

`backend/**` is the only authoritative Python backend source tree for Vox
Stella. Development commands, tests, PyInstaller, and release packaging must
build or import Python modules from that directory.

The release path is:

1. `backend/build_backend.py` builds `backend/app.py` with PyInstaller.
2. The compiled onedir bundle is written to
   `backend/dist/horary_backend/`.
3. `frontend/scripts/prepare-backend.js` copies that compiled bundle to the
   generated staging path `frontend/backend/runtime/horary_backend/`.
4. Electron Builder packages only that generated runtime at
   `resources/backend/runtime/horary_backend/`.
5. The Electron main process launches the packaged executable from that
   runtime directory. Its development fallback resolves `backend/app.py`.

## Legacy mirror

`frontend/backend/**`, except for its generated `runtime/**` child, is a
non-authoritative historical mirror. It is retained temporarily because old
tests, audit records, and source references still point to it. Its Python
files are not PyInstaller inputs, Electron resources, or development backend
entrypoints. Drift from `backend/**` therefore does not describe the released
application.

Do not implement fixes in the mirror and do not manually copy canonical
backend changes into it. New tests should target `backend/**`; old mirror tests
should be migrated or removed as their dependencies are retired.

## Executable guard

Run:

```powershell
python scripts/check_backend_source_ownership.py
```

The guard verifies the package scripts, PyInstaller entrypoint, Electron
resource configuration, application launch paths, isolated Python import
origins, and the ownership marker. It also hashes matching astrocartography
files in both trees and reports them as synchronized, diverged, or legacy-only
without treating the mirror as a release input.

`tests/test_backend_source_ownership.py` runs the same invariant in the normal
backend test gate used by CI and `package-app-new.bat`. It also proves that an
Electron configuration attempting to package the legacy source tree is
rejected.
