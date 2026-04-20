param(
  [string]$InstallDir = "$env:LOCALAPPDATA\Cloudflared",
  [string]$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
)

$ErrorActionPreference = "Stop"

if (-not $env:LOCALAPPDATA) {
  throw "LOCALAPPDATA is not set."
}

if (-not (Test-Path $InstallDir)) {
  New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

$targetPath = Join-Path $InstallDir "cloudflared.exe"
$tempPath = Join-Path $InstallDir "cloudflared.exe.download"

Write-Host "Downloading cloudflared..." -ForegroundColor Cyan
Write-Host "Source: $DownloadUrl" -ForegroundColor DarkGray
Write-Host "Target: $targetPath" -ForegroundColor DarkGray

Invoke-WebRequest -Uri $DownloadUrl -OutFile $tempPath

if (Test-Path $targetPath) {
  Remove-Item -LiteralPath $targetPath -Force
}

Move-Item -LiteralPath $tempPath -Destination $targetPath -Force

$version = & $targetPath --version

Write-Host "" 
Write-Host "Installed cloudflared successfully." -ForegroundColor Green
Write-Host $version -ForegroundColor Green
Write-Host "Launcher path: $targetPath" -ForegroundColor Yellow
