# ============================================================
# 获取当前 Cloudflare Tunnel 公网地址 + 所有访问方式汇总
# 用法：
#   powershell -File E:\notebook\scripts\get-tunnel-url.ps1
# ============================================================

$ErrorActionPreference = 'SilentlyContinue'

Write-Host ""
Write-Host "========== Open Notebook 访问方式 ==========" -ForegroundColor Cyan
Write-Host ""

# 1. Cloudflare Tunnel 公网地址
$tunnelLogs = @(
    'E:\notebook\downloads\tunnel.log',
    'E:\notebook\downloads\tunnel.err.log'
)
$tunnelUrl = $null
foreach ($log in $tunnelLogs) {
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1
        if ($m) { $tunnelUrl = $m.Matches[0].Value; break }
    }
}
if ($tunnelUrl) {
    Write-Host "  [公网] Cloudflare Tunnel: $tunnelUrl" -ForegroundColor Green
} else {
    Write-Host "  [公网] Cloudflare Tunnel: 未运行（无法公网访问）" -ForegroundColor Yellow
}

# 2. Tailscale
$ts = & 'C:\Program Files\Tailscale\tailscale.exe' status 2>&1 | Select-String -Pattern 'laptop-62burom0'
if ($ts) {
    $ip = ($ts.ToString() -split '\s+')[0]
    Write-Host "  [VPN]  Tailscale: http://${ip}:8889  (手机安装 Tailscale 后可随时随地访问)" -ForegroundColor Green
} else {
    Write-Host "  [VPN]  Tailscale: 未检测到 PC 节点" -ForegroundColor Yellow
}

# 3. 局域网
$wifi = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like '192.168.*' } | Select-Object -First 1
if ($wifi) {
    Write-Host "  [局域网] WiFi 网卡: http://$($wifi.IPAddress):8889  (手机连同一 WiFi)" -ForegroundColor Green
} else {
    Write-Host "  [局域网] WiFi 网卡: 未检测到 192.168.x.x 地址" -ForegroundColor Yellow
}

# 4. 本机
Write-Host "  [本机]   桌面: http://localhost:8889 或 http://127.0.0.1:8502" -ForegroundColor Gray

Write-Host ""
Write-Host "  统一访问密码: REPLACED_SEE_LOCAL_CREDENTIALS (见 E:\notebook\CREDENTIALS.md)" -ForegroundColor Magenta
Write-Host ""
Write-Host "  手机打开任意地址后，输入上面的密码即可登录使用。" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
