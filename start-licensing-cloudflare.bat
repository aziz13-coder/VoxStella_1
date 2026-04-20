@echo off
setlocal
cd /d %~dp0

echo === Start Licensing + Cloudflare Tunnel ===
call start-licensing-server.bat
call licensing_server\run_cloudflared.bat
setx LICENSE_SERVER_URL "https://license.voxstella.app" >nul
echo [INFO] Updated user environment: LICENSE_SERVER_URL=https://license.voxstella.app

echo [DONE] Started licensing server launcher and Cloudflare tunnel launcher.
echo Keep both opened windows running.
endlocal
