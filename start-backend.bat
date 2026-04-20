@echo off
title Vox Stella - Backend Development Server
color 0B

echo =====================================
echo  Vox Stella Backend Development Server
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org/
    pause
    exit /b 1
)

REM Navigate to backend directory
cd /d "%~dp0backend"
if errorlevel 1 (
    echo ERROR: Could not navigate to backend directory
    pause
    exit /b 1
)

echo Current directory: %CD%
echo.

REM Ensure stale packaged backend listeners on Electron port are cleared too
echo Checking for stale packaged backend listeners on port 52525...
set "FOUND_PACKAGED_BACKEND_PORT=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"127\.0\.0\.1:52525 .*LISTENING"') do (
    set "FOUND_PACKAGED_BACKEND_PORT=1"
    echo Stopping packaged backend process on port 52525 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"\[::1\]:52525 .*LISTENING"') do (
    set "FOUND_PACKAGED_BACKEND_PORT=1"
    echo Stopping packaged backend process on port 52525 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
if "%FOUND_PACKAGED_BACKEND_PORT%"=="1" (
    timeout /t 1 >nul
)

REM Ensure stale backend listeners on dev port are cleared first
echo Checking for existing backend listeners on port 5000...
set "FOUND_BACKEND_PORT=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"127\.0\.0\.1:5000 .*LISTENING"') do (
    set "FOUND_BACKEND_PORT=1"
    echo Stopping existing process on port 5000 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"\[::1\]:5000 .*LISTENING"') do (
    set "FOUND_BACKEND_PORT=1"
    echo Stopping existing process on port 5000 ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
)
if "%FOUND_BACKEND_PORT%"=="1" (
    timeout /t 1 >nul
)

REM Check Python version
echo Checking Python version...
python --version
echo.

REM Install dependencies directly (simplified approach)
echo Installing Python dependencies...
echo This may take a few minutes on first run...
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo Trying core dependencies only...
    pip install Flask==2.3.3 Flask-CORS==4.0.0 pyswisseph==2.10.3.2 geopy==2.4.1 pytz==2023.3 requests==2.31.0 python-dateutil==2.8.2 PyYAML==6.0.2 python-dotenv==1.0.0
    if errorlevel 1 (
        echo ERROR: Failed to install core dependencies
        pause
        exit /b 1
    )
)

echo.
echo Dependencies installed successfully!
echo.

echo Starting backend development server...
echo The API will be available at http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the Flask development server
set "HORARY_PORT=5000"
set "FLASK_ENV=development"
set "ALLOW_DEV_LICENSE_BYPASS=1"
if /I "%~1"=="--strict-license" (
    set "ALLOW_DEV_LICENSE_BYPASS=0"
    echo INFO: Development license bypass disabled for this session.
) else (
    echo INFO: Development license bypass enabled for local source runtime.
)
python app.py

REM If we reach here, the server was stopped
echo.
echo Backend development server stopped.
pause
