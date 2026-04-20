@echo off
setlocal enabledelayedexpansion
title Vox Stella - Make Unpacked GUI

echo === Vox Stella - Build Unpacked GUI ===
pushd %~dp0

REM Create timestamped log file (without relying on WMIC)
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$d=(Get-Date).ToString('yyyyMMdd_HHmmss'); Write-Output $d"`) do set TS=%%i
set "LOGDIR=%~dp0build-logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "LOG=%LOGDIR%\make-unpacked-gui_%TS%.log"
echo [LOG] Output will also be saved to %LOG%
echo [START] %DATE% %TIME% >"%LOG%"

REM 1) Verify Node/npm
where npm >nul 2>&1 || (
  echo [ERROR] npm not found in PATH. Please install Node.js and try again.>>"%LOG%"
  goto :error
)
for /f %%v in ('node -v') do set NODEV=%%v
for /f %%v in ('npm -v') do set NPMV=%%v
echo Using Node %NODEV%, npm %NPMV%>>"%LOG%"

REM 1a) Build backend executable first (so prepare-backend can bundle it)
echo.>>"%LOG%"
echo [0/3] Building backend executable with PyInstaller>>"%LOG%"
set "_PY="
py -3 -c "import sys;print(sys.version)" >nul 2>&1 && set "_PY=py -3"
if not defined _PY (
  python -c "import sys;print(sys.version)" >nul 2>&1 && set "_PY=python"
)
if defined _PY (
  pushd backend
  powershell -NoProfile -Command "Start-Transcript -Path '%LOG%' -Append | Out-Null; %_PY% build_backend.py; $code=$LASTEXITCODE; Stop-Transcript | Out-Null; exit $code" || echo [WARN] Backend exe build failed; will fall back to python app.py>>"%LOG%"
  popd
 ) else (
  echo [WARN] Python not found; will fall back to python app.py at runtime>>"%LOG%"
 )

REM 2) Build frontend and pack Electron app (PowerShell Tee captures output to log)
pushd frontend
echo.>>"%LOG%"
echo [0.5/3] Installing npm dependencies>>"%LOG%"
powershell -NoProfile -Command "Start-Transcript -Path '%LOG%' -Append | Out-Null; (npm ci) -or (npm install); $code=$LASTEXITCODE; Stop-Transcript | Out-Null; exit $code" || goto :error

echo.>>"%LOG%"
echo [1/3] Building frontend (Vite)>>"%LOG%"
powershell -NoProfile -Command "Start-Transcript -Path '%LOG%' -Append | Out-Null; npm run build; $code=$LASTEXITCODE; Stop-Transcript | Out-Null; exit $code" || goto :error

echo.>>"%LOG%"
echo [2/3] Preparing backend resources>>"%LOG%"
powershell -NoProfile -Command "Start-Transcript -Path '%LOG%' -Append | Out-Null; npm run prepare-backend; $code=$LASTEXITCODE; Stop-Transcript | Out-Null; exit $code" || goto :error

echo.>>"%LOG%"
echo [3/3] Creating unpacked Electron app (win-unpacked)>>"%LOG%"
rem Ensure previous app instance is not locking the exe
tasklist /fi "imagename eq Vox Stella.exe" | find /i "Vox Stella.exe" >nul 2>&1 && (
  echo [INFO] Stopping running app instance before packaging>>"%LOG%"
  taskkill /f /im "Vox Stella.exe" >>"%LOG%" 2>&1
  timeout /t 1 >nul
)
powershell -NoProfile -Command "Start-Transcript -Path '%LOG%' -Append | Out-Null; npm run electron:pack; $code=$LASTEXITCODE; Stop-Transcript | Out-Null; exit $code" || goto :error

set "UNPACKED_DIR=%cd%\dist-electron\win-unpacked"
set "APP_EXE=%UNPACKED_DIR%\Vox Stella.exe"
popd

if not exist "%APP_EXE%" (
  echo [ERROR] Expected executable not found: "%APP_EXE%" >>"%LOG%"
  echo         Please open %LOG% for full details. >>"%LOG%"
  goto :error
)

echo.>>"%LOG%"
echo === Success ===>>"%LOG%"
echo Unpacked app: "%APP_EXE%" >>"%LOG%"
echo Opening folder...>>"%LOG%"
start "" explorer.exe "%UNPACKED_DIR%"
echo Launching app...>>"%LOG%"
start "Vox Stella" "%APP_EXE%"
popd
echo.
echo Done. Log: %LOG%
pause
exit /b 0

:error
echo.
echo Build failed. See log: %LOG%
if exist "%LOG%" start notepad "%LOG%"
popd
echo.
pause
exit /b 1
