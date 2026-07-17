@echo off
setlocal
cd /d %~dp0
set "VENV_PY=.venv\Scripts\python.exe"
if exist "%VENV_PY%" goto :venv_ready

uv venv --python 3.12 .venv
if errorlevel 1 goto :error

:venv_ready
"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 goto :wrong_python

uv pip sync --python "%VENV_PY%" --require-hashes requirements-lock.txt >nul
if errorlevel 1 goto :error

"%VENV_PY%" keys\generate_keys.py
if errorlevel 1 goto :error

endlocal
pause
exit /b 0

:wrong_python
echo [ERROR] Existing .venv is not CPython 3.12.
echo [ERROR] Recreate it with: uv venv --python 3.12 .venv
goto :error

:error
echo [ERROR] Could not prepare the CPython 3.12 environment or generate keys.
endlocal
pause
exit /b 1
