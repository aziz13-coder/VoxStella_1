[CmdletBinding()]
param(
  [string]$WorkspaceRoot
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  $WorkspaceRoot = Split-Path -Parent $PSScriptRoot
}
$workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$batchFile = Join-Path $workspace 'package-app-new.bat'

if (-not (Test-Path -LiteralPath $batchFile -PathType Leaf)) {
  throw "Packaging script not found: $batchFile"
}

$previousProbe = $env:VOX_STELLA_PACKAGE_FAIL_FAST_PROBE
$previousNoExplorer = $env:NO_OPEN_EXPLORER

try {
  $env:VOX_STELLA_PACKAGE_FAIL_FAST_PROBE = '1'
  $env:NO_OPEN_EXPLORER = '1'

  Push-Location $workspace
  try {
    $probeOutput = @(& cmd.exe /d /c package-app-new.bat 2>&1)
    $exitCode = $LASTEXITCODE
  } finally {
    Pop-Location
  }
} finally {
  if ($null -eq $previousProbe) {
    Remove-Item Env:VOX_STELLA_PACKAGE_FAIL_FAST_PROBE -ErrorAction SilentlyContinue
  } else {
    $env:VOX_STELLA_PACKAGE_FAIL_FAST_PROBE = $previousProbe
  }

  if ($null -eq $previousNoExplorer) {
    Remove-Item Env:NO_OPEN_EXPLORER -ErrorAction SilentlyContinue
  } else {
    $env:NO_OPEN_EXPLORER = $previousNoExplorer
  }
}

$probeText = ($probeOutput | Out-String)
Write-Host $probeText.TrimEnd()
if ($exitCode -ne 1) {
  throw "Package failure probe returned exit code $exitCode; expected 1."
}
if (
  $probeText -notmatch '\[CMD\]\s+cmd /d /c exit 9' -or
  $probeText -match 'cannot find the batch label'
) {
  throw 'Package failure probe did not execute the intended failing subcommand.'
}

Write-Host 'Package failure propagation verified (exit code 1).'
