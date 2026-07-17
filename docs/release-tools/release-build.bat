@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
:check_args
if "%~1"=="" goto :run
if /I "%~1"=="-UploadOnly" goto :upload_only_removed
shift
goto :check_args

:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%release-build.ps1" %*
exit /b %ERRORLEVEL%

:upload_only_removed
echo [ERROR] -UploadOnly has been removed. Every upload must package and verify the current clean source tree.
exit /b 2
