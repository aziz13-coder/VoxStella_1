@echo off
setlocal
title Vox Stella Backend - Debug

echo === Vox Stella Backend Debug Runner ===
pushd %~dp0
set "BACKEND_EXE=backend\dist\horary_backend\horary_backend.exe"
if not exist "%BACKEND_EXE%" (
  echo [ERROR] %BACKEND_EXE% not found. Build it first via:
  echo         cd backend ^&^& python build_backend.py
  pause
  exit /b 1
)

set HORARY_PORT=52525
set HORARY_LOG_DIR=%TEMP%\VoxStella\logs
if not exist "%HORARY_LOG_DIR%" mkdir "%HORARY_LOG_DIR%"
echo Logging to: %HORARY_LOG_DIR%

cd /d backend\dist\horary_backend
echo Starting backend on http://127.0.0.1:%HORARY_PORT%
"horary_backend.exe"
echo.
echo Backend exited with code %errorlevel%.
echo Logs (if any): %HORARY_LOG_DIR%\horary_api.log
pause
popd
exit /b 0

