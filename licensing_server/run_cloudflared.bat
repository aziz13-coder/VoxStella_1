@echo off
setlocal

REM === Path resolution order ===
REM 1) CLOUDFLARED_EXE env var
REM 2) managed user install under %%LOCALAPPDATA%%
REM 3) cloudflared on PATH
REM 4) legacy Downloads copy
set "CF_EXE="
set "CF_MANAGED=%LOCALAPPDATA%\Cloudflared\cloudflared.exe"
set "CF_LEGACY=%USERPROFILE%\Downloads\cloudflared-windows-amd64.exe"
set "CF_CFG=%USERPROFILE%\.cloudflared\config.yml"
set "TUNNEL_NAME=voxstella-license"
if "%PORT%"=="" set "PORT=8787"
if "%TUNNEL_TRANSPORT_PROTOCOL%"=="" set "TUNNEL_TRANSPORT_PROTOCOL=http2"
set "CF_PROTOCOL=%TUNNEL_TRANSPORT_PROTOCOL%"
set "LOCAL_LICENSE_URL=http://127.0.0.1:%PORT%/admin/login"

echo === Vox Stella - Cloudflare Tunnel ===

if defined CLOUDFLARED_EXE if exist "%CLOUDFLARED_EXE%" set "CF_EXE=%CLOUDFLARED_EXE%"
if not defined CF_EXE if exist "%CF_MANAGED%" set "CF_EXE=%CF_MANAGED%"
if not defined CF_EXE (
  for /f "delims=" %%I in ('where cloudflared 2^>nul') do (
    set "CF_EXE=%%I"
    goto :have_cf_exe
  )
)
if not defined CF_EXE if exist "%CF_LEGACY%" set "CF_EXE=%CF_LEGACY%"

:have_cf_exe
if not exist "%CF_EXE%" (
  echo [ERROR] cloudflared executable not found:
  echo         expected one of:
  echo           %CF_MANAGED%
  echo           cloudflared on PATH
  echo           %CF_LEGACY%
  echo [INFO] Install or update it with:
  echo        powershell -ExecutionPolicy Bypass -File "%~dp0scripts\install-cloudflared.ps1"
  exit /b 1
)

echo [INFO] Using cloudflared:
echo        %CF_EXE%
echo [INFO] Expected local licensing server:
echo        %LOCAL_LICENSE_URL%
echo [INFO] Cloudflare tunnel transport:
echo        %CF_PROTOCOL%

powershell -NoProfile -Command "try { iwr '%LOCAL_LICENSE_URL%' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
  echo [WARN] Local licensing server is not reachable yet.
  echo [WARN] Start run-licensing-server.bat first, or keep this tunnel window open and start the server next.
)

set "PS_SCRIPT=%TEMP%\run_cloudflared_window.ps1"
(
  echo $cfExe = '%CF_EXE%'
  echo $cfCfg = '%CF_CFG%'
  echo $tunnel = '%TUNNEL_NAME%'
  echo $protocol = '%CF_PROTOCOL%'
  echo $localUrl = '%LOCAL_LICENSE_URL%'
  echo Write-Host "Listing tunnels..." -ForegroundColor Cyan
  echo ^& $cfExe tunnel list
  echo Write-Host ""
  echo Write-Host "Expected local service: $localUrl" -ForegroundColor Cyan
  echo Write-Host "Tunnel transport: $protocol" -ForegroundColor Cyan
  echo if (Test-Path $cfCfg^) {
  echo ^  Write-Host "Starting tunnel from config: $cfCfg" -ForegroundColor Green
  echo ^  Write-Host "(This must stay running.)" -ForegroundColor DarkGray
  echo ^  ^& $cfExe tunnel --protocol $protocol --config $cfCfg run
  echo ^} else {
  echo ^  Write-Host "Config not found. Starting named tunnel: $tunnel" -ForegroundColor Yellow
  echo ^  Write-Host "(This must stay running.)" -ForegroundColor DarkGray
  echo ^  ^& $cfExe tunnel --protocol $protocol run $tunnel
  echo ^}
  echo $code = $LASTEXITCODE
  echo if ($code -eq $null^) { $code = 0 }
  echo Write-Host ""
  echo Write-Host ("cloudflared exited with code {0}" -f $code^) -ForegroundColor Yellow
  echo Write-Host "Press Enter to close..." -ForegroundColor Green
  echo [void](Read-Host^)
) > "%PS_SCRIPT%"

start "Cloudflare Tunnel - Vox Stella" powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%PS_SCRIPT%"

endlocal
