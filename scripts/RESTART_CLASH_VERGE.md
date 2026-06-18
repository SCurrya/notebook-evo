# 重启 Clash Verge 步骤（已配置好 Mihomo DNS 规则）

## 背景
Mihomo (Clash Meta) 之前会把 `*.ts.net` 和 `*.trycloudflare.com` 解析到假 IP（198.18.0.x）。
已修复配置，需要**重启 Clash Verge** 让配置生效。

## 步骤

### 方法 1：托盘右键（最稳）
1. 找系统托盘（屏幕右下角，时钟旁边）的 Clash Verge 图标
2. **右键点击** → **退出**
3. 等 5 秒
4. 重新打开 Clash Verge（开始菜单搜 "Clash Verge"）
5. 等 10 秒让 Mihomo 重新加载配置

### 方法 2：任务管理器（备用）
1. Ctrl+Shift+Esc 打开任务管理器
2. 找到 "Clash Verge" 和 "verge-mihomo" 进程
3. 选中 → 右键 → 结束任务
4. 重新打开 Clash Verge

### 方法 3：PowerShell（如果上面不行）
```powershell
# 杀进程
Get-Process verge-mihomo,clash-verge -ErrorAction SilentlyContinue | Stop-Process -Force
# 重新启动（路径可能不同，自己找）
Start-Process 'C:\Users\ZS\AppData\Local\Programs\clash-verge\Clash Verge.exe' -ErrorAction SilentlyContinue
```

## 验证修复
重启后，PowerShell 里跑：
```powershell
nslookup laptop-62burom0.taile2bacf.ts.net
# 期望：Address: 100.108.217.19（不是 198.18.0.x）

nslookup sellers-view-thoughts-hundreds.trycloudflare.com
# 期望：返回 Cloudflare 真实 IP（104.16.x.x 或 104.18.x.x）
```

## 如果还是假 IP
1. 确认 Merge.yaml 修改了
2. 看看 Mihomo 的 `dns.enhanced-mode` 是否是 `fake-ip`，是的话需要改 `redir-host`
3. 考虑彻底关闭 Tailscale 的 "Use Tailscale Subnets" 选项
