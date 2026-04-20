param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-WorkspaceRootPath {
    param([string]$RawPath)

    $candidate = if ($null -eq $RawPath) { '' } else { $RawPath.Trim() }
    $candidate = $candidate.Trim('"')

    if (-not $candidate) {
        throw 'WorkspaceRoot cannot be empty.'
    }

    $resolvedPath = [string](Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
    $pathRoot = [System.IO.Path]::GetPathRoot($resolvedPath)

    if ($resolvedPath.Length -gt $pathRoot.Length) {
        return $resolvedPath.TrimEnd('\')
    }

    return $resolvedPath
}

$resolvedWorkspace = Resolve-WorkspaceRootPath -RawPath $WorkspaceRoot
$frontendRoot = (Join-Path $resolvedWorkspace 'frontend').TrimEnd('\')
$projectAppRoot = (Join-Path $frontendRoot 'dist-electron\win-unpacked').TrimEnd('\')
$projectAppExe = Join-Path $projectAppRoot 'Vox Stella.exe'
$workspaceNeedles = @($resolvedWorkspace, $frontendRoot, $projectAppRoot, $projectAppExe) |
    Where-Object { $_ -and $_.Trim() } |
    Select-Object -Unique
$targetPorts = @(5173, 52525)
$targetNames = @('node.exe', 'electron.exe', 'horary_backend.exe', 'Vox Stella.exe')
$stoppedProcessIds = [System.Collections.Generic.HashSet[int]]::new()
$stoppedCount = 0

function Write-Status {
    param([string]$Message)

    Write-Output $Message
}

function Test-WorkspaceMatch {
    param([string]$Value)

    if (-not $Value) {
        return $false
    }

    foreach ($needle in $workspaceNeedles) {
        if ($Value.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }

    return $false
}

function Is-WorkspaceProcess {
    param($ProcessInfo)

    $name = [string]$ProcessInfo.Name
    $commandLine = [string]$ProcessInfo.CommandLine
    $executablePath = [string]$ProcessInfo.ExecutablePath

    if ($name -eq 'Vox Stella.exe') {
        if ($executablePath) {
            return $executablePath.IndexOf($projectAppRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        }
        return (Test-WorkspaceMatch -Value $commandLine)
    }

    if ($targetNames -notcontains $name) {
        return $false
    }

    return (Test-WorkspaceMatch -Value $commandLine) -or (Test-WorkspaceMatch -Value $executablePath)
}

function Stop-WorkspaceProcess {
    param(
        $ProcessInfo,
        [string]$Reason
    )

    $processId = [int]$ProcessInfo.ProcessId
    if ($processId -eq $PID) {
        return $false
    }
    if ($stoppedProcessIds.Contains($processId)) {
        return $false
    }
    if (-not (Is-WorkspaceProcess -ProcessInfo $ProcessInfo)) {
        return $false
    }

    $name = [string]$ProcessInfo.Name
    $commandLine = [string]$ProcessInfo.CommandLine
    $summary = if ($commandLine) { $commandLine } else { [string]$ProcessInfo.ExecutablePath }
    $handled = $false

    if ($DryRun) {
        Write-Status "[DRYRUN] Would stop PID $processId ($name) because $Reason"
        $script:stoppedCount += 1
        $handled = $true
    } else {
        $liveProcess = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if (-not $liveProcess) {
            Write-Status "[INFO] PID $processId ($name) already exited before cleanup could stop it"
            $handled = $true
        } else {
            Write-Status "[STOP] PID $processId ($name) because $Reason"
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                $script:stoppedCount += 1
                $handled = $true
            } catch {
                $fullyQualifiedErrorId = [string]$_.FullyQualifiedErrorId
                if ($fullyQualifiedErrorId -like 'NoProcessFoundForGivenId*') {
                    Write-Status "[INFO] PID $processId ($name) exited during cleanup before Stop-Process completed"
                    $handled = $true
                } else {
                    throw
                }
            }
        }
    }

    if ($summary) {
        Write-Status "        $summary"
    }

    $stoppedProcessIds.Add($processId) | Out-Null
    return $handled
}

function Get-ListeningProcessIds {
    param([int]$Port)

    $processIds = [System.Collections.Generic.HashSet[int]]::new()
    $pattern = '^\s*TCP\s+\S+:' + [regex]::Escape([string]$Port) + '\s+\S+\s+LISTENING\s+(\d+)\s*$'
    foreach ($line in @(netstat -ano -p tcp 2>$null)) {
        if ($line -match $pattern) {
            $processIds.Add([int]$matches[1]) | Out-Null
        }
    }

    return @($processIds)
}

Write-Status "Workspace packaging cleanup root: $resolvedWorkspace"

foreach ($port in $targetPorts) {
    $portMatched = $false
    foreach ($processId in Get-ListeningProcessIds -Port $port) {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if (-not $processInfo) {
            continue
        }
        $portMatched = $true
        if (-not (Stop-WorkspaceProcess -ProcessInfo $processInfo -Reason "it owns workspace listener port $port")) {
            Write-Status "[SKIP] Leaving PID $processId on port $port because it is not a workspace process"
        }
    }
    if (-not $portMatched) {
        Write-Status "[INFO] No workspace listener found on port $port"
    }
}

$workspaceProcesses = Get-CimInstance Win32_Process |
    Where-Object { $targetNames -contains [string]$_.Name }

foreach ($processInfo in $workspaceProcesses) {
    Stop-WorkspaceProcess -ProcessInfo $processInfo -Reason 'it belongs to this workspace packaging flow' | Out-Null
}

if ($stoppedCount -eq 0) {
    Write-Status 'Workspace packaging cleanup found no matching processes to stop.'
} else {
    Write-Status "Workspace packaging cleanup stopped $stoppedCount process(es)."
}
