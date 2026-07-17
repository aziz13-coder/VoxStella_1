#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedVersion,
    [int]$TimeoutSeconds = 90,
    [switch]$RequireCleanBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$unpackedRoot = Join-Path $root 'frontend\dist-electron\win-unpacked'
$appExe = Join-Path $unpackedRoot 'Vox Stella.exe'
$runtimeRoot = Join-Path $unpackedRoot 'resources\backend\runtime\horary_backend'
$backendExe = Join-Path $runtimeRoot 'horary_backend.exe'
$metadataPath = Join-Path $runtimeRoot '_internal\build_metadata.json'
$updateConfigPath = Join-Path $unpackedRoot 'resources\app-update.yml'
$licenseConfigPath = Join-Path $root 'frontend\license.config.json'

foreach ($required in @($appExe, $backendExe, $metadataPath, $updateConfigPath, $licenseConfigPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Packaged smoke-test prerequisite is missing: $required"
    }
}

$head = (& git -C $root rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -notmatch '^[0-9a-f]{40}$') {
    throw 'Could not determine the expected Git commit.'
}
$tree = (& git -C $root rev-parse 'HEAD^{tree}').Trim()
if ($LASTEXITCODE -ne 0 -or $tree -notmatch '^[0-9a-f]{40}$') {
    throw 'Could not determine the expected Git tree.'
}

$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
if ($metadata.app_version -ne $ExpectedVersion) {
    throw "Packaged metadata version '$($metadata.app_version)' does not match '$ExpectedVersion'."
}
if ($metadata.git.commit -ne $head -or $metadata.git.tree -ne $tree) {
    throw 'Packaged backend provenance does not match the current Git commit/tree.'
}
if ($RequireCleanBuild -and $metadata.git.dirty -ne $false) {
    throw 'Packaged backend metadata says the release source tree was dirty.'
}

$updateConfig = Get-Content -LiteralPath $updateConfigPath -Raw
if ($updateConfig -notmatch '(?m)^provider:\s*github\s*$') {
    throw 'Packaged app-update.yml is missing the GitHub provider.'
}
if ($updateConfig -notmatch '(?m)^owner:\s*aziz13-coder\s*$') {
    throw 'Packaged app-update.yml has an unexpected GitHub owner.'
}
if ($updateConfig -notmatch '(?m)^repo:\s*VoxStella_1\s*$') {
    throw 'Packaged app-update.yml has an unexpected GitHub repository.'
}

$licenseConfig = Get-Content -LiteralPath $licenseConfigPath -Raw | ConvertFrom-Json
if ([string]$licenseConfig.serverUrl -ne 'https://license.voxstella.app') {
    throw 'Packaged smoke test requires the fixed production licensing origin.'
}
$licenseKeyText = [string]$licenseConfig.publicKeyB64
try {
    $licenseKeyBytes = [Convert]::FromBase64String($licenseKeyText)
} catch {
    throw 'Packaged smoke test requires a valid base64 Ed25519 public key.'
}
if ($licenseKeyBytes.Length -ne 32 -or [Convert]::ToBase64String($licenseKeyBytes) -ne $licenseKeyText) {
    throw 'Packaged smoke test requires an exact 32-byte Ed25519 public key.'
}
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $expectedLicenseKeyFingerprint = (
        [BitConverter]::ToString($sha256.ComputeHash($licenseKeyBytes))
    ).Replace('-', '').ToLowerInvariant()
} finally {
    $sha256.Dispose()
}

$timeoutMs = [Math]::Min([Math]::Max($TimeoutSeconds * 1000, 5000), 180000)
$resultPath = Join-Path ([IO.Path]::GetTempPath()) "vox-stella-electron-smoke-$PID.result.json"
$smokeEnvironment = @{
    VOX_STELLA_SMOKE_TEST = '1'
    VOX_STELLA_SMOKE_TIMEOUT_MS = [string]$timeoutMs
    VOX_STELLA_EXPECTED_COMMIT = $head
    VOX_STELLA_SMOKE_REQUIRE_CLEAN_BUILD = if ($RequireCleanBuild) { '1' } else { '0' }
    VOX_STELLA_SMOKE_RESULT_PATH = $resultPath
}

$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $appExe
$startInfo.Arguments = '--smoke-test'
$startInfo.WorkingDirectory = $unpackedRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
foreach ($entry in $smokeEnvironment.GetEnumerator()) {
    $startInfo.EnvironmentVariables[$entry.Key] = $entry.Value
}

$processStarted = $false
$process = $null
try {
    Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw 'Packaged Electron smoke process could not be started.'
    }
    $processStarted = $true
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()

    $deadline = [DateTime]::UtcNow.AddMilliseconds($timeoutMs + 15000)
    while (-not $process.WaitForExit(250)) {
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "Packaged Electron smoke test timed out after $TimeoutSeconds seconds."
        }
    }
    $process.WaitForExit()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) {
        throw "Packaged Electron smoke test exited with code $($process.ExitCode).`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
    }
    if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
        throw "Packaged Electron exited without a smoke result file.`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
    }
    $smokeResult = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    if ($smokeResult.schemaVersion -ne 1 -or $smokeResult.ok -ne $true) {
        throw "Packaged Electron smoke result was not successful: $($smokeResult | ConvertTo-Json -Compress)"
    }
    if (
        $smokeResult.result.appVersion -ne $ExpectedVersion -or
        $smokeResult.result.commit -ne $head -or
        $smokeResult.result.licensePublicKeySha256 -ne $expectedLicenseKeyFingerprint
    ) {
        throw "Packaged Electron smoke result has unexpected version/provenance/trust root: $($smokeResult | ConvertTo-Json -Compress)"
    }

    Write-Host "[smoke] Packaged Electron started its bundled backend and reached authoritative readiness"
    Write-Host "[smoke] Version $ExpectedVersion, commit $head, tree $tree, clean-required=$([bool]$RequireCleanBuild)"
} finally {
    if ($process) {
        try {
            if ($processStarted -and -not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                $process.WaitForExit(5000) | Out-Null
            }
        } finally {
            $process.Dispose()
        }
    }
    Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
}
