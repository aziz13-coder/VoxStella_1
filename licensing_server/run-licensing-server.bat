@echo off
setlocal enabledelayedexpansion
title Vox Stella - Licensing Server

cd /d %~dp0
echo === Vox Stella - Licensing Server ===
set "EXIT_CODE=1"

set "SERVER_HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8787"
if "%LICENSE_VERIFY_INTERVAL_SECONDS%"=="" set "LICENSE_VERIFY_INTERVAL_SECONDS=604800"
if "%LICENSE_SUBS_GRACE_SECONDS%"=="" set "LICENSE_SUBS_GRACE_SECONDS=172800"
if "%LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%"=="" set "LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS=0"
if "%LICENSE_PERPETUAL_GRACE_SECONDS%"=="" set "LICENSE_PERPETUAL_GRACE_SECONDS=259200"

REM Refuse duplicate or conflicting launches before setup work or opening a new window.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\assert-port-available.ps1" -Port "%PORT%" -Purpose "Vox Stella licensing server"
if errorlevel 1 goto :port_in_use

set "VENV_PY=.venv\Scripts\python.exe"
set "PRIVATE_KEY_FILE=%cd%\keys\ed25519_private.key"
set "PUBLIC_KEY_FILE=%cd%\keys\ed25519_public.key"
set "TOKEN_DIR=%LOCALAPPDATA%\VoxStella\licensing"
set "TOKEN_FILE=%TOKEN_DIR%\admin_token.txt"
set "PAYPAL_ENV_FILE=%cd%\paypal.env"
set "RUNNER_CMD=%TEMP%\voxstella_licensing_run.cmd"

REM 1) Ensure Python venv exists
if exist "%VENV_PY%" goto :venv_ready

echo [SETUP] Creating CPython 3.12 virtual environment...
uv venv --python 3.12 .venv
if errorlevel 1 goto :venv_setup_error

:venv_ready
call "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 goto :wrong_python

REM 2) Install hash-locked requirements
echo [SETUP] Installing hash-locked dependencies...
uv pip sync --python "%VENV_PY%" --require-hashes requirements-lock.txt
if errorlevel 1 goto :dependency_error

REM 3) Generate signing keys only when missing
if exist "%PRIVATE_KEY_FILE%" goto :private_key_ready

echo [SETUP] Generating Ed25519 signing keys...
call "%VENV_PY%" keys\generate_keys.py
if errorlevel 1 goto :key_generation_error

:private_key_ready
if not exist "%PUBLIC_KEY_FILE%" goto :public_key_error

REM 4) Read public key as base64 and persist app runtime env
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$bytes=[System.IO.File]::ReadAllBytes('%PUBLIC_KEY_FILE%'); [Convert]::ToBase64String($bytes)"`) do set "PUBLIC_KEY_B64=%%i"
if not defined PUBLIC_KEY_B64 goto :public_key_read_error
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
if "%ADMIN_TOKEN%"=="" goto :admin_token_error

REM 6) Optional PayPal automation environment
set "PAYPAL_CLIENT_ID_CONFIGURED="
set "PAYPAL_CLIENT_SECRET_CONFIGURED="
set "PAYPAL_WEBHOOK_ID_CONFIGURED="
if not "%PAYPAL_CLIENT_ID%"=="" set "PAYPAL_CLIENT_ID_CONFIGURED=1"
if not "%PAYPAL_CLIENT_SECRET%"=="" set "PAYPAL_CLIENT_SECRET_CONFIGURED=1"
if not "%PAYPAL_WEBHOOK_ID%"=="" set "PAYPAL_WEBHOOK_ID_CONFIGURED=1"
if exist "%PAYPAL_ENV_FILE%" (
  echo [SETUP] PayPal configuration file found:
  echo         %PAYPAL_ENV_FILE%
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%PAYPAL_ENV_FILE%") do (
    if /I "%%A"=="PAYPAL_CLIENT_ID" if not "%%B"=="" set "PAYPAL_CLIENT_ID_CONFIGURED=1"
    if /I "%%A"=="PAYPAL_CLIENT_SECRET" if not "%%B"=="" set "PAYPAL_CLIENT_SECRET_CONFIGURED=1"
    if /I "%%A"=="PAYPAL_WEBHOOK_ID" if not "%%B"=="" set "PAYPAL_WEBHOOK_ID_CONFIGURED=1"
  )
  echo [INFO] app.py will load PayPal settings directly from paypal.env.
) else (
  echo [INFO] Optional PayPal configuration not found:
  echo        %PAYPAL_ENV_FILE%
  echo        Copy paypal.env.example to paypal.env when you are ready to enable PayPal automation.
)

echo [INFO] Admin token: %ADMIN_TOKEN%
echo [INFO] Admin token file: %TOKEN_FILE%
echo [INFO] Server port: %PORT%
echo [INFO] Subscription verify interval (seconds): %LICENSE_VERIFY_INTERVAL_SECONDS%
echo [INFO] Subscription grace (seconds): %LICENSE_SUBS_GRACE_SECONDS%
echo [INFO] Perpetual verify interval (seconds): %LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%
echo [INFO] Perpetual grace (seconds): %LICENSE_PERPETUAL_GRACE_SECONDS%
echo [INFO] PayPal allowed subscription plans include the Vox Stella in-app and website plans.
echo [INFO] PayPal one-time amount defaults to 250.00 USD unless overridden in paypal.env.
if "%PAYPAL_CLIENT_ID_CONFIGURED%"=="" (
  echo [WARN] PAYPAL_CLIENT_ID is not configured. PayPal activation endpoints will return paypal-not-configured.
) else (
  echo [INFO] PAYPAL_CLIENT_ID is configured.
)
if "%PAYPAL_CLIENT_SECRET_CONFIGURED%"=="" (
  echo [WARN] PAYPAL_CLIENT_SECRET is not configured. PayPal activation endpoints will return paypal-not-configured.
) else (
  echo [INFO] PAYPAL_CLIENT_SECRET is configured.
)
if "%PAYPAL_WEBHOOK_ID_CONFIGURED%"=="" (
  echo [WARN] PAYPAL_WEBHOOK_ID is not configured. PayPal webhooks will return paypal-webhook-not-configured.
) else (
  echo [INFO] PAYPAL_WEBHOOK_ID is configured.
)

REM 7) Launch server in separate window
(
  echo @echo off
  echo cd /d "%~dp0"
  echo set "PORT=%PORT%"
  echo set "LICENSE_VERIFY_INTERVAL_SECONDS=%LICENSE_VERIFY_INTERVAL_SECONDS%"
  echo set "LICENSE_SUBS_GRACE_SECONDS=%LICENSE_SUBS_GRACE_SECONDS%"
  echo set "LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS=%LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%"
  echo set "LICENSE_PERPETUAL_GRACE_SECONDS=%LICENSE_PERPETUAL_GRACE_SECONDS%"
  echo set "ADMIN_TOKEN_FILE=%TOKEN_FILE%"
  echo set "LICENSE_PRIVATE_KEY_FILE=%PRIVATE_KEY_FILE%"
  echo set "PAYPAL_CLIENT_ID_CONFIGURED=%PAYPAL_CLIENT_ID_CONFIGURED%"
  echo set "PAYPAL_CLIENT_SECRET_CONFIGURED=%PAYPAL_CLIENT_SECRET_CONFIGURED%"
  echo set "PAYPAL_WEBHOOK_ID_CONFIGURED=%PAYPAL_WEBHOOK_ID_CONFIGURED%"
  echo REM PayPal secret values are loaded directly by app.py from paypal.env, not written into this runner.
  echo echo [INFO] ADMIN_TOKEN_FILE=%TOKEN_FILE%
  echo if "%%PAYPAL_CLIENT_ID_CONFIGURED%%"=="" echo [WARN] PAYPAL_CLIENT_ID is not configured.
  echo if "%%PAYPAL_CLIENT_SECRET_CONFIGURED%%"=="" echo [WARN] PAYPAL_CLIENT_SECRET is not configured.
  echo if "%%PAYPAL_WEBHOOK_ID_CONFIGURED%%"=="" echo [WARN] PAYPAL_WEBHOOK_ID is not configured.
  echo "%VENV_PY%" app.py
) > "%RUNNER_CMD%"

echo [RUN] Starting licensing server in a new window...
start "Vox Stella Licensing" cmd /k "%RUNNER_CMD%"

REM 8) Wait until server is reachable then open admin login
set "_TRIES=0"
:wait_loop
set /a _TRIES+=1
powershell -NoProfile -Command "try { iwr http://%SERVER_HOST%:%PORT%/admin/login -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% EQU 0 goto :server_ready
if %_TRIES% GEQ 20 goto :server_unreachable
timeout /t 1 >nul
goto :wait_loop

:server_ready
start "" "http://%SERVER_HOST%:%PORT%/admin/login"
start "" "%~dp0show-admin-token.bat"
echo [DONE] Licensing server is running.
echo [DONE] Opened admin login in browser.
echo [DONE] Use token: %ADMIN_TOKEN%
set "EXIT_CODE=0"
goto :end

:venv_setup_error
echo [ERROR] Could not create venv. Ensure uv is installed and CPython 3.12 is available.
goto :end

:wrong_python
echo [ERROR] Existing .venv is not CPython 3.12.
echo [ERROR] Recreate it with: uv venv --python 3.12 .venv
goto :end

:dependency_error
echo [ERROR] Failed installing hash-locked Python requirements.
goto :end

:port_in_use
echo [ERROR] Licensing server port %PORT% is already in use.
echo [ERROR] Refusing to start a duplicate server process.
goto :end

:key_generation_error
echo [ERROR] Failed generating keys.
goto :end

:public_key_error
echo [ERROR] Public key file missing: %PUBLIC_KEY_FILE%
goto :end

:public_key_read_error
echo [ERROR] Could not read public key.
goto :end

:admin_token_error
echo [ERROR] Failed to determine ADMIN_TOKEN.
goto :end

:server_unreachable
echo [ERROR] Could not reach server after %_TRIES% tries.
echo [ERROR] Check the window titled: Vox Stella Licensing

:end
endlocal & exit /b %EXIT_CODE%
