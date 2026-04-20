@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

if exist .venv\Scripts\python.exe (
  call .venv\Scripts\python.exe show_admin_token.py
) else (
  py -3 show_admin_token.py
)

endlocal

