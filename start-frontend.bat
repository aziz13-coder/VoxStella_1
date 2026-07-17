@echo off
title Vox Stella - Frontend Development Server
color 0A

echo =====================================
echo  Vox Stella Frontend Development Server
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
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\assert-port-available.ps1" -Port 5173 -Purpose "Vite browser development server"
if errorlevel 1 exit /b 1

echo Starting frontend development server...
echo The application will open in your browser at http://localhost:5173
echo NOTE: Backend API must also be running at http://127.0.0.1:52525 (use start-backend.bat)
echo NOTE: start-backend.bat enables local dev license bypass by default; use --strict-license to disable it.
echo NOTE: This script runs the browser dev server only.
echo NOTE: For Electron desktop dev mode, use start-electron-dev.bat instead.
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the development server
set "VITE_API_BASE_URL=http://127.0.0.1:52525"
npm run dev

REM If we reach here, the server was stopped
echo.
echo Frontend development server stopped.
pause
