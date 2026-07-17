#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gitDir = (& git -C $repoRoot rev-parse --git-dir).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'This command must run inside the Vox Stella Git checkout.'
}
if (-not [IO.Path]::IsPathRooted($gitDir)) {
    $gitDir = Join-Path $repoRoot $gitDir
}

$source = Join-Path $repoRoot '.githooks\pre-commit'
$hookDirectory = Join-Path $gitDir 'hooks'
$destination = Join-Path $hookDirectory 'pre-commit'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw "Hook source is missing: $source"
}

New-Item -ItemType Directory -Path $hookDirectory -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $destination -Force
if (Get-Command chmod -ErrorAction SilentlyContinue) {
    & chmod +x $destination
    if ($LASTEXITCODE -ne 0) {
        throw 'chmod failed while making the pre-commit hook executable.'
    }
}

# Use Git's default .git/hooks location so the copied executable is portable
# even when the tracked source file lacks a Unix executable bit.
& git -C $repoRoot config --local --unset-all core.hooksPath 2>$null
if ($LASTEXITCODE -notin @(0, 1, 5)) {
    throw 'Could not restore Git default hooks path.'
}

Write-Host "Installed source-path guard at $destination"
