@echo off
setlocal enabledelayedexpansion
title Vox Stella - Package NSIS Installer

echo === Vox Stella - Package NSIS Installer ===
pushd %~dp0
set "WORKSPACE_ROOT=%CD%"

REM Create timestamped log file
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$d=(Get-Date).ToString('yyyyMMdd_HHmmss'); Write-Output $d"`) do set TS=%%i
set "LOGDIR=%~dp0build-logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "LOG=%LOGDIR%\package-app-new_%TS%.log"
echo [LOG] Output will also be saved to %LOG%
echo [START] %DATE% %TIME% >"%LOG%"

REM Verify Node/npm
where npm >nul 2>&1 || (
  echo [ERROR] npm not found in PATH. Please install Node.js and try again.>>"%LOG%"
  goto :error
)
for /f %%v in ('node -v') do set NODEV=%%v
for /f %%v in ('npm -v') do set NPMV=%%v
echo Using Node %NODEV%, npm %NPMV%
echo Using Node %NODEV%, npm %NPMV%>>"%LOG%"

REM 1) Build backend executable first
echo.
echo [1/7] Building backend executable with PyInstaller
echo.>>"%LOG%"
echo [1/7] Building backend executable with PyInstaller>>"%LOG%"
set "_PY="
py -3 -c "import sys;print(sys.version)" >nul 2>&1 && set "_PY=py -3"
if not defined _PY (
  python -c "import sys;print(sys.version)" >nul 2>&1 && set "_PY=python"
)
if defined _PY (
  pushd backend
  call :run_logged "%_PY% build_backend.py" || (
    popd
    goto :error
  )
  popd
) else (
  echo [ERROR] Python not found>>"%LOG%"
  goto :error
)

echo.>>"%LOG%"
echo.
echo [2/7] Stopping workspace packaging processes to avoid npm file locks
echo [2/7] Stopping workspace packaging processes to avoid npm file locks>>"%LOG%"
echo [INFO] powershell cleanup helper>>"%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-workspace-packaging-processes.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%\." >>"%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] Workspace packaging cleanup failed>>"%LOG%"
  goto :error
)
timeout /t 2 >nul

REM 2) Build frontend
pushd frontend
echo.
echo [3/7] Installing npm dependencies
echo.>>"%LOG%"
echo [3/7] Installing npm dependencies>>"%LOG%"
call :run_logged "npm ci" || goto :error

echo.
echo [4/7] Building frontend (Vite)
echo.>>"%LOG%"
echo [4/7] Building frontend (Vite)>>"%LOG%"
call :run_logged "npm run build" || goto :error

echo.
echo [5/7] Preparing backend resources
echo.>>"%LOG%"
echo [5/7] Preparing backend resources>>"%LOG%"
call :run_logged "npm run prepare-backend" || goto :error

echo.
echo [6/7] Creating unpacked Electron app
echo.>>"%LOG%"
echo [6/7] Creating unpacked Electron app first>>"%LOG%"
rem Stop workspace-scoped app/dev processes again before writing the unpacked build.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-workspace-packaging-processes.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%\." >>"%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] Workspace cleanup before unpacked build failed>>"%LOG%"
  goto :error
)
call :run_logged "npx electron-builder --dir" || goto :error

REM Verify unpacked app was created
set "UNPACKED_DIR=%cd%\dist-electron\win-unpacked"
set "APP_EXE=%UNPACKED_DIR%\Vox Stella.exe"
if not exist "%APP_EXE%" (
  echo [ERROR] Unpacked app not created: "%APP_EXE%" >>"%LOG%"
  goto :error
)
echo [SUCCESS] Unpacked app created.
echo [SUCCESS] Unpacked app created: "%APP_EXE%" >>"%LOG%"

echo.
echo [7/7] Creating NSIS installer
echo.>>"%LOG%"
echo [7/7] Creating NSIS installer (full build to embed auto-update config)>>"%LOG%"
rem Build installer directly so electron-builder generates app-update.yml in resources
call :run_logged "npx electron-builder --win nsis --publish never" || goto :error

set "OUT_DIR=%cd%\dist-electron"
set "SETUP_EXE="
for /f "delims=" %%f in ('dir /b "%OUT_DIR%\VoxStella-Setup*.exe" 2^>nul') do set "SETUP_EXE=%OUT_DIR%\%%f"
if not defined SETUP_EXE for /f "delims=" %%f in ('dir /b "%OUT_DIR%\Vox Stella Setup*.exe" 2^>nul') do set "SETUP_EXE=%OUT_DIR%\%%f"
if not defined SETUP_EXE for /f "delims=" %%f in ('dir /b /o:d "%OUT_DIR%\*.exe" 2^>nul') do set "SETUP_EXE=%OUT_DIR%\%%f"

echo.>>"%LOG%"
if defined SETUP_EXE (
  echo [SUCCESS] Package complete: "%SETUP_EXE%" >>"%LOG%"
  echo === Packaging complete ===
  echo Created: %SETUP_EXE%
  if /I not "%NO_OPEN_EXPLORER%"=="1" (
    start "" explorer.exe "%OUT_DIR%" >nul 2>&1
  )
) else (
  echo [ERROR] NSIS setup exe not found in %OUT_DIR%.>>"%LOG%"
  goto :error
)

popd
popd
exit /b 0

:run_logged
set "RUN_CMD=%~1"
echo [CMD] %RUN_CMD%
echo [CMD] %RUN_CMD%>>"%LOG%"
cmd /c "%RUN_CMD%" >>"%LOG%" 2>&1
set "RUN_CODE=%ERRORLEVEL%"
if not "%RUN_CODE%"=="0" (
  echo [ERROR] Command failed with exit code %RUN_CODE%: %RUN_CMD%>>"%LOG%"
)
exit /b %RUN_CODE%

:error
echo.
echo Packaging failed. See log: %LOG%
if exist "%LOG%" start notepad "%LOG%"
popd
exit /b 1
