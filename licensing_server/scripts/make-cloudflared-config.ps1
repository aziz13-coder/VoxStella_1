param(
  [Parameter(Mandatory=$true)] [string]$TunnelUUID,
  [string]$Hostname = "license.voxstella.app",
  [string]$OriginURL = "http://127.0.0.1:8787"
)

$userProfile = $env:USERPROFILE
if (-not $userProfile) { throw "USERPROFILE not set. Run in a normal user PowerShell." }

$cfDir = Join-Path $userProfile ".cloudflared"
if (-not (Test-Path $cfDir)) {
  New-Item -ItemType Directory -Force -Path $cfDir | Out-Null
}

$credFile = Join-Path $cfDir ("{0}.json" -f $TunnelUUID)
$cfgPath  = Join-Path $cfDir "config.yml"

$cfg = @()
$cfg += "tunnel: $TunnelUUID"
$cfg += "credentials-file: $credFile"
$cfg += "ingress:"
$cfg += "  - hostname: $Hostname"
$cfg += "    service: $OriginURL"
$cfg += "  - service: http_status:404"

$cfg -join "`n" | Set-Content -Encoding UTF8 -Path $cfgPath

Write-Host "Wrote Cloudflared config: $cfgPath" -ForegroundColor Green
Write-Host "Expect credentials JSON at: $credFile" -ForegroundColor Yellow
Write-Host "If you haven't logged in/created the tunnel: 'cloudflared tunnel login' then 'cloudflared tunnel create <name>'" -ForegroundColor Yellow

