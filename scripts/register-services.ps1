# ============================================================
# Register Caddy as Windows Service (requires Admin PowerShell)
# Run: Right-click PowerShell -> Run as Administrator -> paste this script
# ============================================================

$ErrorActionPreference = 'Stop'

Write-Host "=== Registering Caddy as Windows Service ===" -ForegroundColor Cyan

# Remove existing service if present
$existing = Get-Service -Name 'Caddy' -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing Caddy service..."
    if ($existing.Status -eq 'Running') {
        Stop-Service -Name 'Caddy' -Force
        Start-Sleep -Seconds 2
    }
    sc.exe delete Caddy | Out-Null
    Start-Sleep -Seconds 2
}

# Register Caddy as a service
$caddyExe = 'E:\notebook\downloads\caddy\caddy.exe'
$caddyConfig = 'E:\notebook\downloads\caddy\Caddyfile'
$binPath = "`"$caddyExe`" run --config `"$caddyConfig`""

Write-Host "Creating service with binPath: $binPath"
sc.exe create Caddy binPath= $binPath start= auto | Out-Null

# Set description and recovery
sc.exe description Caddy "Caddy web server for Open Notebook (ports 8888/8889)" | Out-Null
sc.exe failure Caddy reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

# Start the service
Write-Host "Starting Caddy service..."
sc.exe start Caddy | Out-Null
Start-Sleep -Seconds 3

# Verify
$svc = Get-Service -Name 'Caddy' -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq 'Running') {
    Write-Host "`n✅ Caddy service registered and running!" -ForegroundColor Green
    Write-Host "   Service will auto-start on boot and auto-restart on crash."
} else {
    Write-Host "`n⚠️ Caddy service created but not running. Check:" -ForegroundColor Yellow
    Write-Host "   Get-Service Caddy"
    Write-Host "   Get-EventLog -LogName Application -Source Caddy -Newest 5"
}

# Also register SurrealDB and API as scheduled tasks (auto-start on login)
Write-Host "`n=== Registering SurrealDB auto-start ===" -ForegroundColor Cyan
$surrealAction = New-ScheduledTaskAction -Execute 'C:\Tools\surreal\surreal.exe' `
    -Argument 'start --user root --pass root --bind 0.0.0.0:8000 rocksdb:E:\notebook\open-notebook\surreal_data\db' `
    -WorkingDirectory 'E:\notebook\open-notebook'
$surrealTrigger = New-ScheduledTaskTrigger -AtLogOn
$surrealTrigger.Delay = 'PT5S'
$surrealSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'SurrealDB-AutoStart' -Action $surrealAction -Trigger $surrealTrigger -Settings $surrealSettings -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
Write-Host "✅ SurrealDB auto-start registered" -ForegroundColor Green

Write-Host "`n=== Registering Open Notebook API auto-start ===" -ForegroundColor Cyan
$apiAction = New-ScheduledTaskAction -Execute 'E:\notebook\open-notebook\.venv\Scripts\python.exe' `
    -Argument 'run_api.py' `
    -WorkingDirectory 'E:\notebook\open-notebook'
$apiTrigger = New-ScheduledTaskTrigger -AtLogOn
$apiTrigger.Delay = 'PT15S'
$apiSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$apiEnv = New-ScheduledTaskAction -Execute 'cmd.exe' `
    -Argument '/c set DATA_FOLDER=E:\notebook\open-notebook\data && set PYTHONPATH=E:\notebook\open-notebook && set API_HOST=0.0.0.0 && set API_PORT=5055 && set API_RELOAD=false && E:\notebook\open-notebook\.venv\Scripts\python.exe run_api.py' `
    -WorkingDirectory 'E:\notebook\open-notebook'
Register-ScheduledTask -TaskName 'OpenNotebook-API-AutoStart' -Action $apiEnv -Trigger $apiTrigger -Settings $apiSettings -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
Write-Host "✅ Open Notebook API auto-start registered" -ForegroundColor Green

Write-Host "`n=== Done! ===" -ForegroundColor Cyan
Write-Host "All services will now auto-start on boot/login."
Write-Host "Caddy will auto-restart on crash (via service recovery)."
