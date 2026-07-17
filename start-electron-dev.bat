@echo off
title Vox Stella - Electron Development Server
color 0D

echo =====================================
echo  Vox Stella Electron Development Server
echo =====================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org/
    pause
    exit /b 1
)

REM Navigate to frontend directory
cd /d "%~dp0frontend"
if errorlevel 1 (
    echo ERROR: Could not navigate to frontend directory
    pause
    exit /b 1
)

echo Current directory: %CD%
echo.

REM Check if node_modules exists, if not install dependencies
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    echo This may take a few minutes...
    echo.
    npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully!
    echo.
)

REM If node_modules exists but vite is missing, dependencies are incomplete
if not exist "node_modules\\.bin\\vite.cmd" (
    echo Detected incomplete frontend dependencies ^(vite missing^).
    echo Reinstalling Node.js dependencies...
    echo.
    npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
    echo Dependencies repaired successfully!
    echo.
)

REM Never kill an arbitrary listener. Refuse startup and identify the owner.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\assert-port-available.ps1" -Port 5173 -Purpose "Vite development server"
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\assert-port-available.ps1" -Port 52525 -Purpose "Electron development backend"
if errorlevel 1 exit /b 1

echo Starting Electron desktop development mode...
echo This launcher starts Vite and Electron together.
echo Use start-backend.bat + start-frontend.bat only for browser dev mode.
echo.
echo Press Ctrl+C to stop Electron dev mode
echo.

npm run electron:dev

echo.
echo Electron development server stopped.
pause
