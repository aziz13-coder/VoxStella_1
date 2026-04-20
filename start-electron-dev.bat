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

REM Clear stale Vite listener on 5173
echo Checking for existing frontend listeners on port 5173...
set "FOUND_FRONTEND_PORT=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"127\.0\.0\.1:5173 .*LISTENING"') do (
    set "FOUND_FRONTEND_PORT=1"
    echo Stopping existing process on port 5173 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"\[::1\]:5173 .*LISTENING"') do (
    set "FOUND_FRONTEND_PORT=1"
    echo Stopping existing process on port 5173 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
if "%FOUND_FRONTEND_PORT%"=="1" (
    timeout /t 1 >nul
)

REM Clear stale packaged or previous Electron backend listener on 52525
echo Checking for stale Electron backend listeners on port 52525...
set "FOUND_ELECTRON_BACKEND_PORT=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"127\.0\.0\.1:52525 .*LISTENING"') do (
    set "FOUND_ELECTRON_BACKEND_PORT=1"
    echo Stopping existing process on port 52525 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"\[::1\]:52525 .*LISTENING"') do (
    set "FOUND_ELECTRON_BACKEND_PORT=1"
    echo Stopping existing process on port 52525 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
if "%FOUND_ELECTRON_BACKEND_PORT%"=="1" (
    timeout /t 1 >nul
)

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
