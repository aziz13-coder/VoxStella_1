@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

if not defined ADMIN_TOKEN_FILE if defined LOCALAPPDATA set "ADMIN_TOKEN_FILE=%LOCALAPPDATA%\VoxStella\licensing\admin_token.txt"

if exist .venv\Scripts\python.exe (
  call .venv\Scripts\python.exe show_admin_token.py
) else (
  py -3 show_admin_token.py
)
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%

