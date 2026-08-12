# ============================================================
# 一键演示模式 - 面试/展示用
# 1. 备份当前数据（防止意外丢失）
# 2. 重置数据库（删除 notebook/source/note 数据）
# 3. 注入演示数据（3 个 PDF）
# 4. 启动 SurrealDB + API + Caddy
# 5. 打印所有访问地址
#
# 用法：
#   powershell -File E:\notebook\scripts\demo-mode.ps1
#   powershell -File E:\notebook\scripts\demo-mode.ps1 -SkipReset   # 保留数据只启动
# ============================================================

param(
    [switch]$SkipReset   # 跳过重置，只启动服务
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\notebook\open-notebook'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'HH:mm:ss'
    Write-Host "[$ts] [$Level] $Message"
}

Write-Log "========== 一键演示模式 =========="

# 1. 备份
if (-not $SkipReset) {
    Write-Log "备份当前数据..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\notebook\scripts\backup-data.ps1'
}

# 2. 重置数据库（通过 API 完成，避免直接操作 RocksDB）
if (-not $SkipReset) {
    Write-Log "重置数据库（清空笔记本和来源）..."
    try {
        # 从 .env 读取密码（不硬编码到脚本里）
        $envPass = (Select-String -Path 'E:\notebook\open-notebook\.env' -Pattern '^OPEN_NOTEBOOK_PASSWORD=' | Select-Object -First 1).Line -replace '^OPEN_NOTEBOOK_PASSWORD=', ''
        if (-not $envPass) { throw 'OPEN_NOTEBOOK_PASSWORD 未在 .env 中配置' }
        $h = @{ Authorization = "Bearer $($envPass.Trim())" }
        # 删除所有笔记本（级联删除来源/笔记）
        $nbs = (Invoke-RestMethod -Uri 'http://127.0.0.1:5055/api/notebooks' -Headers $h -TimeoutSec 10)
        foreach ($nb in $nbs) {
            Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:5055/api/notebooks/$($nb.id)" -Headers $h -TimeoutSec 20 | Out-Null
            Write-Log "  已删除笔记本: $($nb.name)"
        }
        Write-Log "数据库已重置"
    } catch {
        Write-Log "⚠️ 重置失败（API 可能未启动，继续尝试注入演示数据）: $($_.Exception.Message)" 'WARN'
    }
}

# 3. 启动服务（若未运行）
function Test-Port { param([int]$Port) return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) }

if (-not (Test-Port 8000)) {
    Write-Log "启动 SurrealDB..."
    Start-Process -FilePath 'C:\Tools\surreal\surreal.exe' -ArgumentList 'start','--user','root','--pass','root','--bind','0.0.0.0:8000','rocksdb:E:\notebook\open-notebook\surreal_data\db' -WorkingDirectory $ROOT -WindowStyle Hidden
    Start-Sleep 5
} else { Write-Log "SurrealDB 已在运行" }

if (-not (Test-Port 5055)) {
    Write-Log "启动 API..."
    $env:DATA_FOLDER = "$ROOT\data"
    $env:PYTHONPATH = $ROOT
    $env:API_HOST = '0.0.0.0'
    $env:API_PORT = '5055'
    $env:API_RELOAD = 'false'
    Start-Process -FilePath "$ROOT\.venv\Scripts\python.exe" -ArgumentList 'run_api.py' -WorkingDirectory $ROOT -WindowStyle Hidden
    Start-Sleep 25
} else { Write-Log "API 已在运行" }

# 4. 注入演示数据
if (-not $SkipReset) {
    Write-Log "注入演示数据..."
    Push-Location $ROOT
    & "$ROOT\.venv\Scripts\python.exe" scripts\seed_demo_data.py
    Pop-Location
    Write-Log "演示数据注入完成"
}

# 5. 启动 Caddy
if (-not (Test-Port 8889)) {
    Write-Log "启动 Caddy..."
    Start-Process -FilePath 'E:\notebook\downloads\caddy\caddy.exe' -ArgumentList 'run','--config','E:\notebook\downloads\caddy\Caddyfile' -WorkingDirectory 'E:\notebook\downloads\caddy' -WindowStyle Hidden
    Start-Sleep 3
} else { Write-Log "Caddy 已在运行" }

# 6. 打印访问地址
Write-Log "启动完成，访问方式："
& powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\notebook\scripts\get-tunnel-url.ps1'
Write-Log "========== 演示模式就绪 ✅ =========="
