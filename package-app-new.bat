@echo off
setlocal enabledelayedexpansion
title Vox Stella - Package NSIS Installer

echo === Vox Stella - Package NSIS Installer ===
set "PUSHD_DEPTH=0"
pushd "%~dp0" || exit /b 1
set "PUSHD_DEPTH=1"
set "WORKSPACE_ROOT=%CD%"

REM Create timestamped log file
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$d=(Get-Date).ToString('yyyyMMdd_HHmmss'); Write-Output $d"`) do set TS=%%i
set "LOGDIR=%~dp0build-logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "LOG=%LOGDIR%\package-app-new_%TS%.log"
echo [LOG] Output will also be saved to %LOG%
echo [START] %DATE% %TIME% >"%LOG%"

REM Used only by the deterministic failure-propagation test.
if /I "%VOX_STELLA_PACKAGE_FAIL_FAST_PROBE%"=="1" goto :intentional_failure_probe

REM Prefer the verified workspace-local Node release used by the canonical
REM release workflow. This keeps a manually launched package build independent
REM of an older system-wide Node/npm installation.
set "LOCAL_NODE_DIR=%WORKSPACE_ROOT%\build-logs\toolchains\node-v22.23.1-win-x64"
if exist "%LOCAL_NODE_DIR%\node.exe" if exist "%LOCAL_NODE_DIR%\npm.cmd" (
  set "PATH=%LOCAL_NODE_DIR%;%PATH%"
  echo [INFO] Using workspace Node toolchain: %LOCAL_NODE_DIR%
  >>"%LOG%" echo [INFO] Using workspace Node toolchain: %LOCAL_NODE_DIR%
)

REM Verify the exact release Node/npm toolchain before any build work.
where node >nul 2>&1 || goto :node_missing
where npm >nul 2>&1 || goto :npm_missing
call :run_logged "npm --prefix frontend run verify:release-runtime"
if errorlevel 1 goto :release_runtime_error
call :run_logged "npm --prefix frontend run verify:license-trust-root"
if errorlevel 1 goto :license_trust_root_error
for /f %%v in ('node -v') do set NODEV=%%v
for /f %%v in ('npm -v') do set NPMV=%%v
echo Using Node %NODEV%, npm %NPMV%
>>"%LOG%" echo Using Node %NODEV%, npm %NPMV%

REM 1) Create a deterministic Python 3.12 release environment.
echo.
echo [1/11] Preparing locked Python release environment
echo.>>"%LOG%"
echo [1/11] Preparing locked Python release environment>>"%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\prepare-release-python.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%\." >>"%LOG%" 2>&1
if errorlevel 1 goto :release_python_error
set "_PY=backend\.release-venv\Scripts\python.exe"
for /f "usebackq delims=" %%v in (`node -p "require('./frontend/package.json').version"`) do set "VOX_STELLA_BUILD_VERSION=%%v"

REM 2) Audit the locked dependencies and scan shipped Python source.
echo.
echo [2/11] Auditing release dependencies and Python source
echo.>>"%LOG%"
echo [2/11] Auditing release dependencies and Python source>>"%LOG%"
call :run_logged "%_PY% -m pip_audit -r backend/requirements-lock.txt" || goto :error
call :run_logged "%_PY% -m pip_audit -r licensing_server/requirements-lock.txt" || goto :error
call :run_logged "%_PY% -m bandit -q -r backend licensing_server -x backend/build,backend/dist,backend/venv,backend/.venv,backend/.release-venv,licensing_server/venv,licensing_server/.venv,frontend/backend -lll" || goto :error

REM 3) Run the same backend correctness gate used by CI.
echo.
echo [3/11] Running backend tests
echo.>>"%LOG%"
echo [3/11] Running backend tests>>"%LOG%"
call :run_logged "%_PY% -m pytest -q tests backend --ignore=backend/test_api_request.py --ignore=backend/test_engine.py --ignore=backend/test_simple.py --ignore=tests/test_election_route_contracts.py --ignore=tests/test_election_model_invariants.py --ignore=tests/test_election_rank_stress.py --ignore=tests/test_election_fuzz_matrix.py" || goto :error
call :run_logged "%_PY% -m pytest -q tests/test_election_route_contracts.py tests/test_election_model_invariants.py" || goto :error

REM 4) Build backend executable from the locked environment.
echo.
echo [4/11] Building backend executable with PyInstaller
echo.>>"%LOG%"
echo [4/11] Building backend executable with PyInstaller>>"%LOG%"
pushd backend
set /a "PUSHD_DEPTH+=1" >nul
call :run_logged ".release-venv\Scripts\python.exe build_backend.py" || goto :error
popd
set /a "PUSHD_DEPTH-=1" >nul

echo.>>"%LOG%"
echo.
echo [5/11] Stopping workspace packaging processes to avoid npm file locks
echo [5/11] Stopping workspace packaging processes to avoid npm file locks>>"%LOG%"
echo [INFO] powershell cleanup helper>>"%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-workspace-packaging-processes.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%\." >>"%LOG%" 2>&1
if errorlevel 1 goto :workspace_cleanup_error
timeout /t 2 >nul

REM 6) Build frontend
pushd frontend
set /a "PUSHD_DEPTH+=1" >nul
echo.
echo [6/11] Installing npm dependencies
echo.>>"%LOG%"
echo [6/11] Installing npm dependencies>>"%LOG%"
call :run_logged "npm ci" || goto :error

echo.
echo [7/11] Linting, testing, and building frontend
echo.>>"%LOG%"
echo [7/11] Linting, testing, and building frontend>>"%LOG%"
call :run_logged "npm run lint" || goto :error
call :run_logged "npm test" || goto :error
call :run_logged "npm run build" || goto :error

echo.
echo [8/11] Preparing compiled backend resources
echo.>>"%LOG%"
echo [8/11] Preparing compiled backend resources>>"%LOG%"
call :run_logged "npm run prepare-backend" || goto :error

echo.
echo [9/11] Creating unpacked Electron app
echo.>>"%LOG%"
echo [9/11] Creating unpacked Electron app first>>"%LOG%"
rem Stop workspace-scoped app/dev processes again before writing the unpacked build.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-workspace-packaging-processes.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%\." >>"%LOG%" 2>&1
if errorlevel 1 goto :pre_unpack_cleanup_error
call :run_logged "npx electron-builder --dir" || goto :error

REM Verify unpacked app was created
set "UNPACKED_DIR=%cd%\dist-electron\win-unpacked"
set "APP_EXE=%UNPACKED_DIR%\Vox Stella.exe"
if not exist "%APP_EXE%" goto :unpacked_app_missing
echo [SUCCESS] Unpacked app created.
echo [SUCCESS] Unpacked app created: "%APP_EXE%" >>"%LOG%"

echo.
echo [10/11] Creating NSIS installer
echo.>>"%LOG%"
echo [10/11] Creating NSIS installer (full build to embed auto-update config)>>"%LOG%"
rem Build installer directly so electron-builder generates app-update.yml in resources
call :run_logged "npx electron-builder --win nsis --publish never" || goto :error

set "OUT_DIR=%cd%\dist-electron"
set "SETUP_EXE=%OUT_DIR%\VoxStella-Setup-%VOX_STELLA_BUILD_VERSION%.exe"

echo.>>"%LOG%"
if not exist "%SETUP_EXE%" goto :installer_missing

echo.
echo [11/11] Running packaged runtime smoke test
echo.>>"%LOG%"
echo [11/11] Running packaged runtime smoke test against the final updater-enabled layout>>"%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%WORKSPACE_ROOT%\scripts\test-packaged-app.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%\." -ExpectedVersion "%VOX_STELLA_BUILD_VERSION%" >>"%LOG%" 2>&1
if errorlevel 1 goto :packaged_smoke_error

echo [SUCCESS] Package complete: "%SETUP_EXE%" >>"%LOG%"
echo === Packaging complete ===
echo Created: %SETUP_EXE%
if /I not "%NO_OPEN_EXPLORER%"=="1" start "" explorer.exe "%OUT_DIR%" >nul 2>&1

popd
set /a "PUSHD_DEPTH-=1" >nul
popd
set /a "PUSHD_DEPTH-=1" >nul
exit /b 0

:intentional_failure_probe
echo [ERROR] Intentional package failure-propagation probe.>>"%LOG%"
call :run_logged "cmd /d /c exit 9"
if errorlevel 1 goto :error
echo [ERROR] Failure probe command unexpectedly succeeded.>>"%LOG%"
goto :error

:node_missing
echo [ERROR] node not found in PATH. Install Node.js 22.23.1 and try again.>>"%LOG%"
goto :error

:npm_missing
echo [ERROR] npm not found in PATH. Install the npm 10.9.8 bundled with Node.js 22.23.1.>>"%LOG%"
goto :error

:release_runtime_error
echo [ERROR] Packaging requires exactly Node 22.23.1 with bundled npm 10.9.8.
echo [ERROR] Packaging requires exactly Node 22.23.1 with bundled npm 10.9.8.>>"%LOG%"
goto :error

:license_trust_root_error
echo [ERROR] Production licensing origin or Ed25519 trust root verification failed.
echo [ERROR] Production licensing origin or Ed25519 trust root verification failed.>>"%LOG%"
goto :error

:release_python_error
echo [ERROR] Release Python environment preparation failed>>"%LOG%"
goto :error

:workspace_cleanup_error
echo [ERROR] Workspace packaging cleanup failed>>"%LOG%"
goto :error

:pre_unpack_cleanup_error
echo [ERROR] Workspace cleanup before unpacked build failed>>"%LOG%"
goto :error

:unpacked_app_missing
echo [ERROR] Unpacked app not created: "%APP_EXE%">>"%LOG%"
goto :error

:packaged_smoke_error
echo [ERROR] Packaged runtime smoke test failed>>"%LOG%"
goto :error

:installer_missing
echo [ERROR] Expected NSIS setup exe not found: "%SETUP_EXE%">>"%LOG%"
goto :error

:run_logged
set "RUN_CMD=%~1"
echo [CMD] %RUN_CMD%
>>"%LOG%" echo [CMD] %RUN_CMD%
cmd /c "%RUN_CMD%" >>"%LOG%" 2>&1
set "RUN_CODE=%ERRORLEVEL%"
if not "%RUN_CODE%"=="0" (
  >>"%LOG%" echo [ERROR] Command failed with exit code %RUN_CODE%: %RUN_CMD%
)
exit /b %RUN_CODE%

:error
echo.
echo Packaging failed. See log: %LOG%
if /I not "%NO_OPEN_EXPLORER%"=="1" if exist "%LOG%" start notepad "%LOG%"
for /l %%d in (1,1,!PUSHD_DEPTH!) do popd
exit /b 1
