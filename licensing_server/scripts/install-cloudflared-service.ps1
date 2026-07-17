param(
  [Parameter(Mandatory=$true)] [string]$TunnelUUID,
  [string]$Hostname = "license.voxstella.app",
  [string]$OriginURL = "http://127.0.0.1:8787",
  [string]$CloudflaredPath = "cloudflared.exe",
  [string]$Protocol = "http2"
)

$systemProfileDir = "C:\\Windows\\System32\\config\\systemprofile\\.cloudflared"
if (-not (Test-Path $systemProfileDir)) { New-Item -ItemType Directory -Force -Path $systemProfileDir | Out-Null }

$cfgPath = Join-Path $systemProfileDir "config.yml"
$credPath = Join-Path $systemProfileDir ("{0}.json" -f $TunnelUUID)

# Copy user credentials JSON if found
$userCred = Join-Path $env:USERPROFILE ".cloudflared\$TunnelUUID.json"
if (Test-Path $userCred) {
  Copy-Item $userCred $credPath -Force
} else {
  Write-Host "WARNING: Could not find $userCred. Ensure you ran 'cloudflared tunnel login' and 'cloudflared tunnel create' first." -ForegroundColor Yellow
}

$cfg = @()
$cfg += "tunnel: $TunnelUUID"
$cfg += "credentials-file: $credPath"
$cfg += "protocol: $Protocol"
$cfg += "ingress:"
$cfg += "  - hostname: $Hostname"
$cfg += "    service: $OriginURL"
$cfg += "  - service: http_status:404"
$cfg -join "`n" | Set-Content -Encoding UTF8 -Path $cfgPath

Write-Host "Wrote systemprofile Cloudflared config: $cfgPath" -ForegroundColor Green

# Install and start service
& $CloudflaredPath service install | Out-Null
Start-Service -Name Cloudflared
Write-Host "Cloudflared Windows service installed and started." -ForegroundColor Green
