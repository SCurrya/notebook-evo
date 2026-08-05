$ErrorActionPreference = "Continue"
$db = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $db) {
    Start-Process -FilePath ".\surreal.exe" -ArgumentList @("start","--log","info","--user","root","--pass","root","--bind","127.0.0.1:8000","rocksdb:./surreal_data/db") -WindowStyle Hidden
    Start-Sleep 10
}
$env:API_RELOAD = "false"
Start-Process -FilePath "E:\notebook\open-notebook\.venv\Scripts\python.exe" -ArgumentList @("E:\notebook\open-notebook\run_api.py") -WorkingDirectory "E:\notebook\open-notebook" -RedirectStandardOutput "E:\notebook\open-notebook\api-verify.log" -RedirectStandardError "E:\notebook\open-notebook\api-verify.err.log" -WindowStyle Hidden
Start-Sleep 35
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5055/api/notebooks" -UseBasicParsing -TimeoutSec 10
    Write-Output "API up: $($r.StatusCode)"
} catch {
    Write-Output "API FAILED: $($_.Exception.Message)"
}
