@echo off
setlocal
cd /d %~dp0
call licensing_server\run-licensing-server.bat
endlocal
