param(
  [Parameter(Mandatory=$true)] [string]$TunnelName,
  [string]$CloudflaredPath = "cloudflared.exe"
)

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$CloudflaredPath`" tunnel run $TunnelName"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings
Register-ScheduledTask -TaskName "Cloudflared Tunnel ($TunnelName)" -InputObject $task -Force | Out-Null

Write-Host "Registered Task Scheduler job: Cloudflared Tunnel ($TunnelName)" -ForegroundColor Green
Write-Host "Starts at logon, elevated, and restarts on failure." -ForegroundColor Yellow

