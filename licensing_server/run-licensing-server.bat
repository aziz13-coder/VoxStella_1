@echo off
setlocal enabledelayedexpansion
title Vox Stella - Licensing Server

cd /d %~dp0
echo === Vox Stella - Licensing Server ===

set "SERVER_HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8787"
if "%LICENSE_VERIFY_INTERVAL_SECONDS%"=="" set "LICENSE_VERIFY_INTERVAL_SECONDS=604800"
if "%LICENSE_SUBS_GRACE_SECONDS%"=="" set "LICENSE_SUBS_GRACE_SECONDS=172800"
if "%LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%"=="" set "LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS=1814400"
if "%LICENSE_PERPETUAL_GRACE_SECONDS%"=="" set "LICENSE_PERPETUAL_GRACE_SECONDS=259200"

set "VENV_PY=.venv\Scripts\python.exe"
set "PRIVATE_KEY_FILE=%cd%\keys\ed25519_private.key"
set "PUBLIC_KEY_FILE=%cd%\keys\ed25519_public.key"
set "TOKEN_DIR=%LOCALAPPDATA%\VoxStella\licensing"
set "TOKEN_FILE=%TOKEN_DIR%\admin_token.txt"
set "RUNNER_CMD=%TEMP%\voxstella_licensing_run.cmd"

REM 1) Ensure Python venv exists
if not exist "%VENV_PY%" (
  echo [SETUP] Creating virtual environment...
  py -3 -m venv .venv || (
    echo [ERROR] Could not create venv. Ensure Python 3 is installed and py is in PATH.
    goto :end
  )
)

REM 2) Install requirements
echo [SETUP] Installing dependencies...
call "%VENV_PY%" -m pip install --upgrade pip >nul 2>&1
call "%VENV_PY%" -m pip install -r requirements.txt || (
  echo [ERROR] Failed installing Python requirements.
  goto :end
)

REM 3) Generate signing keys only when missing
if not exist "%PRIVATE_KEY_FILE%" (
  echo [SETUP] Generating Ed25519 signing keys...
  call "%VENV_PY%" keys\generate_keys.py || (
    echo [ERROR] Failed generating keys.
    goto :end
  )
)

if not exist "%PUBLIC_KEY_FILE%" (
  echo [ERROR] Public key file missing: %PUBLIC_KEY_FILE%
  goto :end
)

REM 4) Read public key as base64 and persist app runtime env
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$bytes=[System.IO.File]::ReadAllBytes('%PUBLIC_KEY_FILE%'); [Convert]::ToBase64String($bytes)"`) do set "PUBLIC_KEY_B64=%%i"
if not defined PUBLIC_KEY_B64 (
  echo [ERROR] Could not read public key.
  goto :end
)
setx LICENSE_SERVER_URL "http://%SERVER_HOST%:%PORT%" >nul
setx LICENSE_PUBLIC_KEY_B64 "!PUBLIC_KEY_B64!" >nul
echo [INFO] Updated user environment:
echo        LICENSE_SERVER_URL=http://%SERVER_HOST%:%PORT%
echo        LICENSE_PUBLIC_KEY_B64=!PUBLIC_KEY_B64!

REM 5) Admin token: use env if present, else token file, else generate once
if "%ADMIN_TOKEN%"=="" (
  if not exist "%TOKEN_DIR%" mkdir "%TOKEN_DIR%" >nul 2>&1
  if exist "%TOKEN_FILE%" (
    set /p ADMIN_TOKEN=<"%TOKEN_FILE%"
  )
)
if /I "%ADMIN_TOKEN%"=="ECHO is off." set "ADMIN_TOKEN="
if "%ADMIN_TOKEN%"=="" (
  for /f %%i in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')"') do set "ADMIN_TOKEN=%%i"
  >"%TOKEN_FILE%" echo !ADMIN_TOKEN!
)
if "%ADMIN_TOKEN%"=="" (
  echo [ERROR] Failed to determine ADMIN_TOKEN.
  goto :end
)

echo [INFO] Admin token: %ADMIN_TOKEN%
echo [INFO] Admin token file: %TOKEN_FILE%
echo [INFO] Server port: %PORT%
echo [INFO] Subscription verify interval (seconds): %LICENSE_VERIFY_INTERVAL_SECONDS%
echo [INFO] Subscription grace (seconds): %LICENSE_SUBS_GRACE_SECONDS%
echo [INFO] Perpetual verify interval (seconds): %LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%
echo [INFO] Perpetual grace (seconds): %LICENSE_PERPETUAL_GRACE_SECONDS%

REM 6) Launch server in separate window
(
  echo @echo off
  echo cd /d "%~dp0"
  echo set "PORT=%PORT%"
  echo set "LICENSE_VERIFY_INTERVAL_SECONDS=%LICENSE_VERIFY_INTERVAL_SECONDS%"
  echo set "LICENSE_SUBS_GRACE_SECONDS=%LICENSE_SUBS_GRACE_SECONDS%"
  echo set "LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS=%LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%"
  echo set "LICENSE_PERPETUAL_GRACE_SECONDS=%LICENSE_PERPETUAL_GRACE_SECONDS%"
  echo set "ADMIN_TOKEN=%ADMIN_TOKEN%"
  echo set "ADMIN_TOKEN_FILE=%TOKEN_FILE%"
  echo set "LICENSE_PRIVATE_KEY_FILE=%PRIVATE_KEY_FILE%"
  echo echo [INFO] ADMIN_TOKEN=%ADMIN_TOKEN%
  echo echo [INFO] ADMIN_TOKEN_FILE=%TOKEN_FILE%
  echo "%VENV_PY%" app.py
) > "%RUNNER_CMD%"

echo [RUN] Starting licensing server in a new window...
start "Vox Stella Licensing" cmd /k "%RUNNER_CMD%"

REM 7) Wait until server is reachable then open admin login
set "_TRIES=0"
:wait_loop
set /a _TRIES+=1
powershell -NoProfile -Command "try { iwr http://%SERVER_HOST%:%PORT%/admin/login -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
  if %_TRIES% GEQ 20 (
    echo [WARN] Could not reach server after %_TRIES% tries.
    echo [WARN] Check the window titled: Vox Stella Licensing
    goto :end
  )
  timeout /t 1 >nul
  goto wait_loop
)

start "" "http://%SERVER_HOST%:%PORT%/admin/login"
start "" "%~dp0show-admin-token.bat"
echo [DONE] Licensing server is running.
echo [DONE] Opened admin login in browser.
echo [DONE] Use token: %ADMIN_TOKEN%

:end
endlocal
