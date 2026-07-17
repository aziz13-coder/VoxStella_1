#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int]$Port,
    [string]$Purpose = 'development service'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$listeners = @(
    Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
)
if ($listeners.Count -eq 0) {
    Write-Host "[port-check] Port $Port is available for $Purpose."
    exit 0
}

Write-Error "Port $Port is already in use; refusing to terminate an unrelated process."
foreach ($listener in $listeners) {
    $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    $name = if ($process) { $process.ProcessName } else { 'unknown' }
    $path = if ($process) {
        try { $process.Path } catch { $null }
    } else {
        $null
    }
    Write-Host "  PID $($listener.OwningProcess), process=$name, address=$($listener.LocalAddress)"
    if ($path) {
        Write-Host "  executable=$path"
    }
}
Write-Host "Stop the intended process yourself or select another port, then retry."
exit 1
