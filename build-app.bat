@echo off
setlocal enabledelayedexpansion
title Vox Stella - Build (Unpacked)

echo === Vox Stella Build (Unpacked) ===
echo Working directory: %~dp0
pushd %~dp0

REM Choose Python launcher
set "_PY="
py -3 -c "import sys;print(sys.version)" >nul 2>&1 && set "_PY=py -3"
if not defined _PY (
  python -c "import sys;print(sys.version)" >nul 2>&1 && set "_PY=python"
)
if not defined _PY (
  echo [ERROR] Python not found. Please install Python 3.x and try again.
  goto :error
)

echo.
echo [1/4] Building backend executable with PyInstaller...
%_PY% backend\build_backend.py || goto :error

echo.
echo [2/4] Preparing backend resources for Electron bundle...
pushd frontend
call npm run prepare-backend || goto :error

echo.
echo [3/4] Building frontend (Vite)...
call npm run build || goto :error

echo.
echo [4/4] Creating unpacked Electron app (win-unpacked)...
call npm run electron:pack || goto :error
popd

echo.
echo === Build complete ===
echo Unpacked app: frontend\dist-electron\win-unpacked\Vox Stella.exe
echo Backend port (runtime): 52525
popd
exit /b 0

:error
echo.
echo Build failed. See messages above.
popd
exit /b 1

