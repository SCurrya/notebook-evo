# ============================================================
# Open Notebook 健康检查 + 自动重启脚本
# 用法：
#   手动检查：  powershell -File E:\notebook\scripts\health-check.ps1
#   持续监控：  powershell -File E:\notebook\scripts\health-check.ps1 -Monitor
#   计划任务：  每 5 分钟自动运行一次（见 register-services.ps1）
# ============================================================

param(
    [switch]$Monitor,
    [int]$IntervalSeconds = 300  # 默认 5 分钟
)

$ErrorActionPreference = 'SilentlyContinue'
$LogFile = 'E:\notebook\scripts\health-check.log'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Test-Service {
    param([string]$Name, [string]$Url, [int]$Timeout = 5)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $Timeout
        return $true
    } catch {
        return $false
    }
}

function Start-SurrealDB {
    Write-Log "启动 SurrealDB..."
    Start-Process -FilePath 'C:\Tools\surreal\surreal.exe' `
        -ArgumentList 'start','--user','root','--pass','root','--bind','0.0.0.0:8000','rocksdb:E:\notebook\open-notebook-data\surrealdb\mydatabase.db' `
        -WorkingDirectory 'E:\notebook\open-notebook' -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

function Start-API {
    Write-Log "启动 API..."
    $env:DATA_FOLDER = 'E:\notebook\open-notebook-data'
    $env:PYTHONPATH = 'E:\notebook\open-notebook'
    $env:API_HOST = '0.0.0.0'
    $env:API_PORT = '5055'
    $env:API_RELOAD = 'false'
    Start-Process -FilePath 'E:\notebook\open-notebook\.venv\Scripts\python.exe' `
        -ArgumentList 'run_api.py' `
        -WorkingDirectory 'E:\notebook\open-notebook' -WindowStyle Hidden
    Start-Sleep -Seconds 15
}

function Start-Caddy {
    Write-Log "启动 Caddy..."
    Start-Process -FilePath 'E:\notebook\downloads\caddy\caddy.exe' `
        -ArgumentList 'run','--config','E:\notebook\downloads\caddy\Caddyfile' `
        -WorkingDirectory 'E:\notebook\downloads\caddy' -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

function Invoke-HealthCheck {
    Write-Log "========== 健康检查 =========="
    
    $allHealthy = $true
    
    # 1. SurrealDB
    if (Test-Service -Name 'SurrealDB' -Url 'http://127.0.0.1:8000/health') {
        Write-Log "✅ SurrealDB (8000): 正常"
    } else {
        Write-Log "❌ SurrealDB (8000): 异常，正在重启..." 'WARN'
        Start-SurrealDB
        if (Test-Service -Url 'http://127.0.0.1:8000/health') {
            Write-Log "✅ SurrealDB 重启成功"
        } else {
            Write-Log "❌ SurrealDB 重启失败" 'ERROR'
            $allHealthy = $false
        }
    }
    
    # 2. API
    if (Test-Service -Name 'API' -Url 'http://127.0.0.1:5055/health') {
        Write-Log "✅ API (5055): 正常"
    } else {
        Write-Log "❌ API (5055): 异常，正在重启..." 'WARN'
        Start-API
        if (Test-Service -Url 'http://127.0.0.1:5055/health') {
            Write-Log "✅ API 重启成功"
        } else {
            Write-Log "❌ API 重启失败" 'ERROR'
            $allHealthy = $false
        }
    }
    
    # 3. Caddy
    if (Test-Service -Name 'Caddy' -Url 'http://127.0.0.1:8889/') {
        Write-Log "✅ Caddy (8889): 正常"
    } else {
        Write-Log "❌ Caddy (8889): 异常，正在重启..." 'WARN'
        Start-Caddy
        if (Test-Service -Url 'http://127.0.0.1:8889/') {
            Write-Log "✅ Caddy 重启成功"
        } else {
            Write-Log "❌ Caddy 重启失败" 'ERROR'
            $allHealthy = $false
        }
    }
    
    # 4. Cloudflare Tunnel（检查进程是否存在）
    $cf = Get-Process cloudflared -ErrorAction SilentlyContinue
    if ($cf) {
        Write-Log "✅ Cloudflare Tunnel: 运行中 (PID: $($cf.Id -join ', '))"
    } else {
        Write-Log "⚠️ Cloudflare Tunnel: 未运行（手动启动: start-all.bat）" 'WARN'
    }
    
    # 5. Tailscale
    $ts = & 'C:\Program Files\Tailscale\tailscale.exe' status 2>&1
    if ($ts -match 'laptop-62burom0') {
        Write-Log "✅ Tailscale PC 节点: 在线"
    } else {
        Write-Log "⚠️ Tailscale PC 节点: 异常" 'WARN'
    }
    
    if ($allHealthy) {
        Write-Log "========== 全部正常 ✅ =========="
    } else {
        Write-Log "========== 部分异常 ❌ ==========" 'ERROR'
    }
    
    return $allHealthy
}

# ============================================================
# 主逻辑
# ============================================================

if ($Monitor) {
    Write-Log "持续监控模式，间隔 $IntervalSeconds 秒..."
    while ($true) {
        Invoke-HealthCheck
        Start-Sleep -Seconds $IntervalSeconds
    }
} else {
    Invoke-HealthCheck
}
