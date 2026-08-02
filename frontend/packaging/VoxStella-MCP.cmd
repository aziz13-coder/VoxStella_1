@echo off
setlocal
set "ELECTRON_RUN_AS_NODE=1"
"%~dp0Vox Stella.exe" "%~dp0resources\app.asar.unpacked\main\mcp\stdio-bridge.js"
exit /b %ERRORLEVEL%
