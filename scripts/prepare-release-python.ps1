#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$lockPath = Join-Path $root 'backend\requirements-lock.txt'
$venvPath = Join-Path $root 'backend\.release-venv'
$pythonPath = Join-Path $venvPath 'Scripts\python.exe'
$expectedUvVersion = '0.11.15'
$expectedPythonVersion = '3.12.13'

if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
    throw "Pinned backend lock file is missing: $lockPath"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required for deterministic release environments. Install it from https://docs.astral.sh/uv/.'
}
$uvVersionOutput = (& uv --version).Trim()
if ($LASTEXITCODE -ne 0 -or $uvVersionOutput -notmatch "^uv $([regex]::Escape($expectedUvVersion))(?:\s|$)") {
    throw "Release uv must be $expectedUvVersion, found '$uvVersionOutput'."
}

Write-Host "[release-python] Ensuring CPython $expectedPythonVersion is available through uv $expectedUvVersion"
& uv python install $expectedPythonVersion
if ($LASTEXITCODE -ne 0) {
    throw "uv python install failed with exit code $LASTEXITCODE."
}

Write-Host "[release-python] Recreating clean environment at $venvPath"
& uv venv --clear --managed-python --python $expectedPythonVersion $venvPath
if ($LASTEXITCODE -ne 0) {
    throw "uv venv failed with exit code $LASTEXITCODE."
}

Write-Host '[release-python] Synchronizing exact locked dependencies with hash verification'
& uv pip sync --python $pythonPath --require-hashes $lockPath
if ($LASTEXITCODE -ne 0) {
    throw "uv pip sync failed with exit code $LASTEXITCODE."
}

$probe = & $pythonPath -c "import importlib.metadata as m, json, sys; print(json.dumps({'python': list(sys.version_info[:3]), 'pyinstaller': m.version('pyinstaller')}))"
if ($LASTEXITCODE -ne 0) {
    throw "Release Python verification failed with exit code $LASTEXITCODE."
}
$state = $probe | ConvertFrom-Json
if (($state.python -join '.') -ne $expectedPythonVersion) {
    throw "Release Python must be $expectedPythonVersion, found $($state.python -join '.')."
}
if ($state.pyinstaller -ne '6.21.0') {
    throw "Release PyInstaller must be 6.21.0, found $($state.pyinstaller)."
}

Write-Host "[release-python] Ready: Python $($state.python -join '.'), PyInstaller $($state.pyinstaller)"
