#requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [string]$Version,
  [switch]$NoUpload,
  [switch]$DryRun,
  [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Show-Usage {
  @"
Usage:
  docs\release-tools\release-build.bat [version] [options]

Examples:
  docs\release-tools\release-build.bat 3.0.1
    Bump package sources to 3.0.1, package, upload release v3.0.1.

  docs\release-tools\release-build.bat
    Package the current source version and publish it only when no public
    release exists.

  docs\release-tools\release-build.bat 3.0.1 -NoUpload
    Bump and package locally, but do not upload.

  docs\release-tools\release-build.bat 3.0.1 -DryRun
    Show the resolved plan without changing files, packaging, or uploading.

Options:
  -NoUpload     Package and verify locally, but skip GitHub upload.
  -DryRun       Print the planned actions and exit.
  -Help         Show this help.
"@ | Write-Host
}

function Assert-SemVer {
  param([Parameter(Mandatory = $true)][string]$Value)
  if ($Value -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version '$Value' must be a stable major.minor.patch version."
  }
}

function Assert-PatchIncrement {
  param(
    [Parameter(Mandatory = $true)][string]$Current,
    [Parameter(Mandatory = $true)][string]$Requested
  )
  $old = $Current.Split('.') | ForEach-Object { [int]$_ }
  $next = $Requested.Split('.') | ForEach-Object { [int]$_ }
  if ($next[0] -ne $old[0] -or $next[1] -ne $old[1] -or $next[2] -ne ($old[2] + 1)) {
    throw "Release version must increment exactly one patch: $Current -> $Requested is not allowed."
  }
}

function Invoke-GitText {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [switch]$AllowFailure
  )
  $output = & git -C $RepoRoot @Arguments 2>$null
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0 -and -not $AllowFailure) {
    throw "git $($Arguments -join ' ') failed with exit code $exitCode."
  }
  if ($exitCode -ne 0) {
    return $null
  }
  return (($output | Out-String).Trim())
}

function Assert-ReleaseSourceState {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$Tag
  )

  $status = Invoke-GitText $RepoRoot @('status', '--porcelain=v1', '--untracked-files=all')
  if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw 'Release source tree is dirty. Commit or remove every tracked and untracked source change before building.'
  }

  $branch = Invoke-GitText $RepoRoot @('branch', '--show-current')
  if ([string]::IsNullOrWhiteSpace($branch)) {
    throw 'Release builds require a named branch, not a detached HEAD.'
  }
  $head = Invoke-GitText $RepoRoot @('rev-parse', 'HEAD')
  $tree = Invoke-GitText $RepoRoot @('rev-parse', 'HEAD^{tree}')
  $upstream = Invoke-GitText $RepoRoot @('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}') -AllowFailure
  if ([string]::IsNullOrWhiteSpace($upstream)) {
    throw "Branch '$branch' has no upstream. Push it before releasing."
  }

  & git -C $RepoRoot fetch --quiet origin
  if ($LASTEXITCODE -ne 0) {
    throw 'Could not fetch origin to verify release provenance.'
  }
  $upstreamCommit = Invoke-GitText $RepoRoot @('rev-parse', '@{u}')
  if ($head -ne $upstreamCommit) {
    throw "Local HEAD $head does not exactly match pushed upstream $upstreamCommit."
  }

  $localTagCommit = Invoke-GitText $RepoRoot @('rev-list', '-n', '1', $Tag) -AllowFailure
  if ($localTagCommit -and $localTagCommit -ne $head) {
    throw "Existing local tag $Tag resolves to $localTagCommit, not release HEAD $head."
  }

  $remoteTagLines = Invoke-GitText $RepoRoot @(
    'ls-remote', '--tags', 'origin', "refs/tags/$Tag", "refs/tags/$Tag^{}"
  ) -AllowFailure
  if ($remoteTagLines) {
    $remoteCommit = $null
    foreach ($line in ($remoteTagLines -split "`r?`n")) {
      $parts = @($line -split '\s+' | Where-Object { $_ })
      if ($parts.Count -lt 2) { continue }
      if ($parts[1] -eq "refs/tags/$Tag^{}") {
        $remoteCommit = $parts[0]
        break
      }
      if ($parts[1] -eq "refs/tags/$Tag") {
        $remoteCommit = $parts[0]
      }
    }
    if (-not $remoteCommit) {
      throw "Could not resolve existing remote tag $Tag."
    }
    if ($remoteCommit -ne $head) {
      throw "Existing remote tag $Tag resolves to $remoteCommit, not release HEAD $head."
    }
  }

  return [pscustomobject]@{
    Branch = $branch
    Head = $head
    Tree = $tree
    Upstream = $upstream
  }
}

function Assert-ReleaseSourceStateUnchanged {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)]$ExpectedState,
    [Parameter(Mandatory = $true)][string]$Checkpoint
  )

  $status = Invoke-GitText $RepoRoot @('status', '--porcelain=v1', '--untracked-files=all')
  if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw "Release source tree became dirty $Checkpoint. Packaging/upload is aborted."
  }

  $head = Invoke-GitText $RepoRoot @('rev-parse', 'HEAD')
  if ($head -ne $ExpectedState.Head) {
    throw "Release HEAD changed $Checkpoint. Expected $($ExpectedState.Head), found $head."
  }

  $tree = Invoke-GitText $RepoRoot @('rev-parse', 'HEAD^{tree}')
  if ($tree -ne $ExpectedState.Tree) {
    throw "Release Git tree changed $Checkpoint. Expected $($ExpectedState.Tree), found $tree."
  }
}

function Invoke-NodeJsonScript {
  param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  $output = $Script | node - @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Node JSON helper failed with exit code $LASTEXITCODE."
  }
  return $output
}

function Get-SourceVersions {
  param(
    [Parameter(Mandatory = $true)][string]$PackageJsonPath,
    [Parameter(Mandatory = $true)][string]$PackageLockPath
  )

  $script = @'
const fs = require("fs");
const [packageJsonPath, packageLockPath] = process.argv.slice(2);
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
const packageLock = JSON.parse(fs.readFileSync(packageLockPath, "utf8"));
const lockRoot = packageLock.packages && packageLock.packages[""];
if (!lockRoot) {
  throw new Error('package-lock.json does not contain packages[""].');
}
const publish = packageJson.build && Array.isArray(packageJson.build.publish)
  ? packageJson.build.publish[0] || {}
  : {};
process.stdout.write(JSON.stringify({
  PackageVersion: String(packageJson.version || ""),
  BuildVersion: String((packageJson.build && packageJson.build.buildVersion) || ""),
  LockVersion: String(packageLock.version || ""),
  LockRootVersion: String(lockRoot.version || ""),
  Owner: String(publish.owner || ""),
  Repo: String(publish.repo || "")
}));
'@

  $output = Invoke-NodeJsonScript $script @($PackageJsonPath, $PackageLockPath)
  return $output | ConvertFrom-Json
}

function Set-SourceVersion {
  param(
    [Parameter(Mandatory = $true)][string]$PackageJsonPath,
    [Parameter(Mandatory = $true)][string]$PackageLockPath,
    [Parameter(Mandatory = $true)][string]$NewVersion
  )

  $script = @'
const fs = require("fs");
const [packageJsonPath, packageLockPath, version] = process.argv.slice(2);
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
const packageLock = JSON.parse(fs.readFileSync(packageLockPath, "utf8"));
if (!packageJson.build) {
  packageJson.build = {};
}
if (!packageLock.packages || !packageLock.packages[""]) {
  throw new Error('package-lock.json does not contain packages[""].');
}
packageJson.version = version;
packageJson.build.buildVersion = version;
packageLock.version = version;
packageLock.packages[""].version = version;
fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + "\n");
fs.writeFileSync(packageLockPath, JSON.stringify(packageLock, null, 2) + "\n");
'@

  Invoke-NodeJsonScript $script @($PackageJsonPath, $PackageLockPath, $NewVersion) | Out-Null

  $versions = Get-SourceVersions $PackageJsonPath $PackageLockPath
  if (
    $versions.PackageVersion -ne $NewVersion -or
    $versions.BuildVersion -ne $NewVersion -or
    $versions.LockVersion -ne $NewVersion -or
    $versions.LockRootVersion -ne $NewVersion
  ) {
    throw "Version update verification failed for $NewVersion."
  }
}

function Assert-SourceVersionAligned {
  param(
    [Parameter(Mandatory = $true)]$Versions,
    [Parameter(Mandatory = $true)][string]$ExpectedVersion
  )
  $actual = @(@(
    $Versions.PackageVersion,
    $Versions.BuildVersion,
    $Versions.LockVersion,
    $Versions.LockRootVersion
  ) | Select-Object -Unique)

  if ($actual.Count -ne 1 -or $actual[0] -ne $ExpectedVersion) {
    throw "Source versions are not aligned to $ExpectedVersion. Found: $($actual -join ', ')"
  }
}

function Clean-YamlValue {
  param([Parameter(Mandatory = $true)][string]$Value)
  $cleaned = $Value.Trim()
  if ($cleaned.Length -ge 2) {
    $first = $cleaned.Substring(0, 1)
    $last = $cleaned.Substring($cleaned.Length - 1, 1)
    if (($first -eq "'" -and $last -eq "'") -or ($first -eq '"' -and $last -eq '"')) {
      $cleaned = $cleaned.Substring(1, $cleaned.Length - 2)
    }
  }
  return $cleaned
}

function Read-LatestYml {
  param([Parameter(Mandatory = $true)][string]$Path)
  $text = Get-Content -LiteralPath $Path -Raw

  $versionMatch = [regex]::Match($text, '(?m)^version:\s*(.+?)\s*$')
  $pathMatch = [regex]::Match($text, '(?m)^path:\s*(.+?)\s*$')
  $shaMatch = [regex]::Match($text, '(?m)^\s*sha512:\s*(.+?)\s*$')
  $sizeMatch = [regex]::Match($text, '(?m)^\s*size:\s*(\d+)\s*$')

  if (-not $versionMatch.Success) { throw "Could not read version from $Path." }
  if (-not $pathMatch.Success) { throw "Could not read path from $Path." }
  if (-not $shaMatch.Success) { throw "Could not read sha512 from $Path." }
  if (-not $sizeMatch.Success) { throw "Could not read size from $Path." }

  return [pscustomobject]@{
    Version = Clean-YamlValue $versionMatch.Groups[1].Value
    Path = Clean-YamlValue $pathMatch.Groups[1].Value
    Sha512 = Clean-YamlValue $shaMatch.Groups[1].Value
    Size = [int64](Clean-YamlValue $sizeMatch.Groups[1].Value)
  }
}

function Get-FileSha512Base64 {
  param([Parameter(Mandatory = $true)][string]$Path)
  $hex = (Get-FileHash -LiteralPath $Path -Algorithm SHA512).Hash
  $bytes = [byte[]]::new($hex.Length / 2)
  for ($index = 0; $index -lt $bytes.Length; $index++) {
    $bytes[$index] = [Convert]::ToByte($hex.Substring($index * 2, 2), 16)
  }
  return [Convert]::ToBase64String($bytes)
}

function Assert-BlockmapValid {
  param([Parameter(Mandatory = $true)][string]$Path)
  $script = @'
const fs = require("fs");
const zlib = require("zlib");
const [blockmapPath] = process.argv.slice(2);
const compressed = fs.readFileSync(blockmapPath);
if (compressed.length < 64) throw new Error("blockmap is unexpectedly small");
const decoded = zlib.gunzipSync(compressed);
const payload = JSON.parse(decoded.toString("utf8"));
if (String(payload.version) !== "2") throw new Error("unsupported blockmap version");
if (!Array.isArray(payload.files) || payload.files.length === 0) throw new Error("blockmap has no files");
for (const file of payload.files) {
  if (!Array.isArray(file.checksums) || file.checksums.length === 0) {
    throw new Error("blockmap file has no checksums");
  }
  if (!Array.isArray(file.sizes) || file.sizes.length !== file.checksums.length) {
    throw new Error("blockmap checksum/size cardinality mismatch");
  }
}
process.stdout.write(JSON.stringify({ files: payload.files.length, bytes: compressed.length }));
'@
  $output = Invoke-NodeJsonScript $script @($Path)
  return $output | ConvertFrom-Json
}

function Assert-AuthenticodeValid {
  param([Parameter(Mandatory = $true)][string[]]$Paths)
  foreach ($path in $Paths) {
    $signature = Get-AuthenticodeSignature -LiteralPath $path
    if ($signature.Status -ne 'Valid') {
      throw "Authenticode signature is not valid for $path (status=$($signature.Status))."
    }
    Write-Host "Verified Authenticode signature: $path"
  }
}

function Assert-PackagedProvenance {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$ExpectedVersion,
    [Parameter(Mandatory = $true)]$SourceState
  )
  $metadataPath = Join-Path $RepoRoot 'frontend\dist-electron\win-unpacked\resources\backend\runtime\horary_backend\_internal\build_metadata.json'
  if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
    throw "Packaged provenance metadata is missing: $metadataPath"
  }
  $metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
  if ($metadata.app_version -ne $ExpectedVersion) {
    throw "Packaged app version '$($metadata.app_version)' does not match '$ExpectedVersion'."
  }
  if ($metadata.git.commit -ne $SourceState.Head -or $metadata.git.tree -ne $SourceState.Tree) {
    throw 'Packaged commit/tree provenance does not match the verified release source.'
  }
  if ($metadata.git.dirty -ne $false) {
    throw 'Packaged provenance metadata records a dirty source tree.'
  }
  return $metadata
}

function Invoke-Packaging {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)]$SourceState
  )
  Push-Location $RepoRoot
  try {
    $env:NO_OPEN_EXPLORER = '1'
    & cmd.exe /c package-app-new.bat
    if ($LASTEXITCODE -ne 0) {
      throw "package-app-new.bat failed with exit code $LASTEXITCODE."
    }
    Assert-ReleaseSourceStateUnchanged $RepoRoot $SourceState 'after package-app-new'
  } finally {
    Pop-Location
  }
}

function Test-ReleaseArtifacts {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$ExpectedVersion
  )

  $distDir = Join-Path $RepoRoot 'frontend\dist-electron'
  $installerName = "VoxStella-Setup-$ExpectedVersion.exe"
  $blockmapName = "$installerName.blockmap"
  # Updater metadata is deliberately last so it cannot point at an asset that
  # has not finished uploading.
  $assetPaths = @(
    (Join-Path $distDir $installerName),
    (Join-Path $distDir $blockmapName),
    (Join-Path $distDir 'latest.yml')
  )

  foreach ($path in $assetPaths) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      throw "Required release asset is missing: $path"
    }
  }

  $latest = Read-LatestYml (Join-Path $distDir 'latest.yml')
  if ($latest.Version -ne $ExpectedVersion) {
    throw "latest.yml version is '$($latest.Version)', expected '$ExpectedVersion'."
  }
  if ($latest.Path -ne $installerName) {
    throw "latest.yml path is '$($latest.Path)', expected '$installerName'."
  }

  $installer = Get-Item -LiteralPath (Join-Path $distDir $installerName)
  if ($latest.Size -ne $installer.Length) {
    throw "latest.yml size $($latest.Size) does not match installer size $($installer.Length)."
  }
  $actualSha512 = Get-FileSha512Base64 $installer.FullName
  if ($latest.Sha512 -ne $actualSha512) {
    throw 'latest.yml SHA-512 does not match the installer bytes.'
  }
  $blockmap = Assert-BlockmapValid (Join-Path $distDir $blockmapName)

  return [pscustomobject]@{
    AssetPaths = $assetPaths
    Latest = $latest
    Installer = $installer
    Blockmap = $blockmap
  }
}

function Get-GitHubHeaders {
  # Windows PowerShell 5.1 can corrupt embedded newlines when a single string is
  # piped to a native process. Feed Git an ASCII query file instead so the
  # credential protocol remains reliable without persisting the returned token.
  $credentialQueryPath = [IO.Path]::GetTempFileName()
  try {
    [IO.File]::WriteAllText(
      $credentialQueryPath,
      "protocol=https`r`nhost=github.com`r`n`r`n",
      [Text.Encoding]::ASCII
    )
    $credential = @(
      & cmd.exe /d /c "git credential fill < `"$credentialQueryPath`""
    )
    if ($LASTEXITCODE -ne 0) {
      throw "git credential fill failed with exit code $LASTEXITCODE."
    }
  } finally {
    Remove-Item -LiteralPath $credentialQueryPath -Force -ErrorAction SilentlyContinue
  }
  $passwordLine = $credential | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
  if (-not $passwordLine) {
    throw 'No GitHub credential password/token was returned by git credential fill.'
  }
  $token = $passwordLine.Substring('password='.Length)
  return [pscustomobject]@{
    Token = $token
    Headers = @{
      Authorization = "Bearer $token"
      Accept = 'application/vnd.github+json'
      'X-GitHub-Api-Version' = '2022-11-28'
      'User-Agent' = 'vox-stella-release-build-script'
    }
  }
}

function Get-OrCreateRelease {
  param(
    [Parameter(Mandatory = $true)][string]$ApiBase,
    [Parameter(Mandatory = $true)][hashtable]$Headers,
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Commit
  )

  try {
    $release = Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases/tags/$Tag" -Method Get
    if ($release.draft -eq $true) {
      if ([string]$release.target_commitish -ne $Commit) {
        throw "Existing draft $Tag targets '$($release.target_commitish)', not verified commit $Commit."
      }
      Write-Host "Found existing draft release $Tag id=$($release.id)"
      return $release
    }
    throw "Published release $Tag already exists. Releases are immutable; use a new patch version."
  } catch {
    if (
      $_.Exception.Message -like 'Published release*' -or
      $_.Exception.Message -like 'Existing draft*'
    ) {
      throw
    }
    $statusCode = $null
    if ($_.Exception.Response) {
      $statusCode = [int]$_.Exception.Response.StatusCode
    }
    if ($statusCode -ne 404) {
      throw
    }
  }

  $releases = @(
    Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases?per_page=100" -Method Get
  )
  $draft = $releases | Where-Object { $_.tag_name -eq $Tag -and $_.draft -eq $true } | Select-Object -First 1
  if ($draft) {
    if ([string]$draft.target_commitish -ne $Commit) {
      throw "Existing draft $Tag targets '$($draft.target_commitish)', not verified commit $Commit."
    }
    Write-Host "Found existing draft release $Tag id=$($draft.id)"
    return $draft
  }

  $body = @{
    tag_name = $Tag
    target_commitish = $Commit
    name = $Tag
    draft = $true
    prerelease = $false
    generate_release_notes = $false
  } | ConvertTo-Json

  $created = Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases" -Method Post -Body $body -ContentType 'application/json'
  Write-Host "Created draft release $Tag id=$($created.id), target=$Commit"
  return $created
}

function Publish-ReleaseAssets {
  param(
    [Parameter(Mandatory = $true)][string]$RepoFullName,
    [Parameter(Mandatory = $true)][string]$ApiBase,
    [Parameter(Mandatory = $true)][hashtable]$Headers,
    [Parameter(Mandatory = $true)][string]$Token,
    [Parameter(Mandatory = $true)]$Release,
    [Parameter(Mandatory = $true)][string[]]$AssetPaths,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)]$SourceState
  )

  if ($Release.draft -ne $true) {
    throw 'Assets may only be replaced on a draft release.'
  }
  $existingAssets = Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases/$($Release.id)/assets?per_page=100" -Method Get
  foreach ($assetPath in $AssetPaths) {
    $file = Get-Item -LiteralPath $assetPath
    $existing = $existingAssets | Where-Object { $_.name -eq $file.Name } | Select-Object -First 1
    if ($existing) {
      Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases/assets/$($existing.id)" -Method Delete | Out-Null
      Write-Host "Deleted existing asset $($file.Name)"
    }

    $uploadHeaders = @{
      Authorization = "Bearer $Token"
      Accept = 'application/vnd.github+json'
      'X-GitHub-Api-Version' = '2022-11-28'
      'User-Agent' = 'vox-stella-release-build-script'
    }
    $encodedName = [uri]::EscapeDataString($file.Name)
    $uploadUri = "https://uploads.github.com/repos/$RepoFullName/releases/$($Release.id)/assets?name=$encodedName"
    Assert-ReleaseSourceStateUnchanged $RepoRoot $SourceState "immediately before draft asset upload of $($file.Name)"
    $uploaded = Invoke-RestMethod -Headers $uploadHeaders -Uri $uploadUri -Method Post -InFile $file.FullName -ContentType 'application/octet-stream'
    Write-Host "Uploaded $($uploaded.name): $($uploaded.state), $($uploaded.size) bytes"
  }
}

function Assert-UploadedAssets {
  param(
    [Parameter(Mandatory = $true)][string]$ApiBase,
    [Parameter(Mandatory = $true)][hashtable]$Headers,
    [Parameter(Mandatory = $true)]$Release,
    [Parameter(Mandatory = $true)][string[]]$AssetPaths
  )

  $release = Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases/$($Release.id)" -Method Get
  if ($release.draft -ne $true) {
    throw 'Release became public before asset verification completed.'
  }
  $assets = @($release.assets)
  foreach ($assetPath in $AssetPaths) {
    $file = Get-Item -LiteralPath $assetPath
    $asset = $assets | Where-Object { $_.name -eq $file.Name } | Select-Object -First 1
    if (-not $asset) {
      throw "Release asset missing after upload: $($file.Name)"
    }
    if ($asset.state -ne 'uploaded') {
      throw "Release asset $($file.Name) state is '$($asset.state)', expected uploaded."
    }
    if ([int64]$asset.size -ne [int64]$file.Length) {
      throw "Release asset $($file.Name) size $($asset.size) does not match local size $($file.Length)."
    }
    $localSha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $digestProperty = $asset.PSObject.Properties['digest']
    $remoteDigest = if ($digestProperty) { [string]$digestProperty.Value } else { '' }
    if ($remoteDigest -and $remoteDigest.StartsWith('sha256:')) {
      $remoteSha256 = $remoteDigest.Substring('sha256:'.Length).ToLowerInvariant()
      if ($remoteSha256 -ne $localSha256) {
        throw "Release asset $($file.Name) SHA-256 does not match the local artifact."
      }
    } else {
      $downloadPath = Join-Path ([IO.Path]::GetTempPath()) "vox-stella-release-$($asset.id)-$([guid]::NewGuid().ToString('N'))"
      try {
        $downloadHeaders = @{} + $Headers
        $downloadHeaders.Accept = 'application/octet-stream'
        Invoke-WebRequest -Headers $downloadHeaders -Uri $asset.url -OutFile $downloadPath | Out-Null
        $downloadSha256 = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($downloadSha256 -ne $localSha256) {
          throw "Downloaded release asset $($file.Name) SHA-256 does not match the local artifact."
        }
      } finally {
        Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
      }
    }
    Write-Host "Verified $($asset.name): $($asset.state), $($asset.size) bytes"
  }
  return $release
}

function Publish-VerifiedDraft {
  param(
    [Parameter(Mandatory = $true)][string]$ApiBase,
    [Parameter(Mandatory = $true)][hashtable]$Headers,
    [Parameter(Mandatory = $true)]$Release
  )
  if ($Release.draft -ne $true) {
    throw 'Only a verified draft release may be published.'
  }
  $body = @{ draft = $false } | ConvertTo-Json
  $published = Invoke-RestMethod -Headers $Headers -Uri "$ApiBase/releases/$($Release.id)" -Method Patch -Body $body -ContentType 'application/json'
  if ($published.draft -ne $false) {
    throw 'GitHub did not publish the verified release.'
  }
  Write-Host "Published verified release: $($published.html_url)"
  return $published
}

if ($Help) {
  Show-Usage
  exit 0
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$packageJsonPath = Join-Path $repoRoot 'frontend\package.json'
$packageLockPath = Join-Path $repoRoot 'frontend\package-lock.json'
$packagingScript = Join-Path $repoRoot 'package-app-new.bat'

if (-not (Test-Path -LiteralPath $packagingScript -PathType Leaf)) {
  throw "Packaging script not found: $packagingScript"
}

$sourceVersions = Get-SourceVersions $packageJsonPath $packageLockPath
if ([string]::IsNullOrWhiteSpace($Version)) {
  $Version = $sourceVersions.PackageVersion
}
Assert-SemVer $Version

$tag = "v$Version"
$repoFullName = "$($sourceVersions.Owner)/$($sourceVersions.Repo)"
$apiBase = "https://api.github.com/repos/$repoFullName"

Write-Host "Repo root: $repoRoot"
Write-Host "Release target: $repoFullName"
Write-Host "Requested version: $Version"
Write-Host "GitHub tag: $tag"
Write-Host "No upload: $NoUpload"
Write-Host "Dry run: $DryRun"

if ($DryRun) {
  if ($sourceVersions.PackageVersion -ne $Version) {
    Assert-PatchIncrement $sourceVersions.PackageVersion $Version
  }
  Write-Host 'Dry run complete. No files were changed, packaged, or uploaded.'
  exit 0
}

$sourceState = Assert-ReleaseSourceState $repoRoot $tag

if (
  $sourceVersions.PackageVersion -ne $Version -or
  $sourceVersions.BuildVersion -ne $Version -or
  $sourceVersions.LockVersion -ne $Version -or
  $sourceVersions.LockRootVersion -ne $Version
) {
  Assert-PatchIncrement $sourceVersions.PackageVersion $Version
  Write-Host "Updating source version fields to $Version"
  Set-SourceVersion $packageJsonPath $packageLockPath $Version
  Write-Host 'Version sources were updated. Commit and push them, then rerun this command.'
  exit 3
}
Assert-SourceVersionAligned $sourceVersions $Version
Invoke-Packaging $repoRoot $sourceState

$artifactState = Test-ReleaseArtifacts $repoRoot $Version
$provenance = Assert-PackagedProvenance $repoRoot $Version $sourceState
Write-Host "Verified local latest.yml: version=$($artifactState.Latest.Version), path=$($artifactState.Latest.Path), size=$($artifactState.Latest.Size)"
Write-Host "Installer SHA512: $($artifactState.Latest.Sha512)"
Write-Host "Verified blockmap: files=$($artifactState.Blockmap.files), bytes=$($artifactState.Blockmap.bytes)"
Write-Host "Verified packaged provenance: commit=$($provenance.git.commit), tree=$($provenance.git.tree)"

$packagedSmokeScript = Join-Path $repoRoot 'scripts\test-packaged-app.ps1'
& $packagedSmokeScript -WorkspaceRoot $repoRoot -ExpectedVersion $Version -RequireCleanBuild

$appExe = Join-Path $repoRoot 'frontend\dist-electron\win-unpacked\Vox Stella.exe'
$backendExe = Join-Path $repoRoot 'frontend\dist-electron\win-unpacked\resources\backend\runtime\horary_backend\horary_backend.exe'
Assert-AuthenticodeValid @($artifactState.Installer.FullName, $appExe, $backendExe)

if ($NoUpload) {
  Write-Host 'Skipping GitHub upload because -NoUpload was provided.'
  exit 0
}

$github = Get-GitHubHeaders
$release = Get-OrCreateRelease $apiBase $github.Headers $tag $sourceState.Head
Assert-ReleaseSourceStateUnchanged $repoRoot $sourceState 'immediately before draft asset upload'
Publish-ReleaseAssets $repoFullName $apiBase $github.Headers $github.Token $release $artifactState.AssetPaths $repoRoot $sourceState
$verifiedDraft = Assert-UploadedAssets $apiBase $github.Headers $release $artifactState.AssetPaths
$publishedRelease = Publish-VerifiedDraft $apiBase $github.Headers $verifiedDraft

Write-Host "Release $tag completed from commit $($sourceState.Head): $($publishedRelease.html_url)"
