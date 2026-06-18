# 📱 手机 Tailscale 访问 PC Open Notebook 故障排查

## 现状
- ✅ PC 端 `http://100.108.217.19:8889` 已经能访问 Open Notebook
- ❌ 手机访问同地址失败

## 排查流程（按顺序尝试）

### 第 1 步：检查手机 Tailscale 状态

**手机端**操作：

1. 打开 Tailscale App
2. 看节点列表里 `laptop-62burom0` 是什么颜色：
   - 🟢 绿色 = 在线，可以访问
   - ⚪ 灰色 = 离线，需要重新连接
   - 🟡 黄色 = 正在连接，等几秒

如果是灰色/黄色：
- 关掉 Tailscale VPN 开关
- 等 3 秒
- 再开 Tailscale VPN
- 等 10 秒看是否变绿

**如果 30 秒还没变绿**：
- 切换网络（WiFi ↔ 4G）
- 重启 Tailscale App
- 重启手机（最后手段）

### 第 2 步：检查 Tailscale VPN 是否开启

1. 打开手机**设置** → **网络和互联网** → **VPN**
2. 看是否有 "Tailscale" 正在运行
3. 如果没有：回 Tailscale App 开启

### 第 3 步：检查 Nekobox 是否冲突

Android 同时只允许**一个 VPN 进程**：
- 如果 Nekobox VPN 开着，**Tailscale VPN 会被禁用**
- 反之亦然

**解决**：
1. 暂时**关掉 Nekobox**
2. Tailscale App 里**确认 VPN 是开的**
3. 访问 PC

### 第 4 步：测试手机到 PC 的连接

**手机浏览器**访问：
```
http://100.108.217.19:8889
```

期望：看到 Open Notebook 登录页

**如果打不开**：
- 看到 "无法访问此网站" → 网络层问题（Tailscale 没通）
- 看到 "ERR_CONNECTION_TIMED_OUT" → 端口被防火墙拦了
- 看到 Open Notebook 但密码错误 → 密码错（看第 5 步）
- 看到 Open Notebook 完整界面 = 成功！✅

### 第 5 步：密码错误

如果登录页提示密码错：
1. 在 PC 上查看实际密码：
   ```powershell
   Select-String -Path 'E:\notebook\open-notebook\.env' -Pattern 'OPEN_NOTEBOOK_PASSWORD'
   ```
2. 复制 `=` 后面**完整**的内容（可能包含特殊字符）
3. 手机端完整粘贴

**常见错误**：
- 多复制了空格
- 把 `=` 号也算进去了
- 复制了 `OPEN_NOTEBOOK_PASSWORD=` 前缀

### 第 6 步：手机能看到 PC 但 UI 没渲染（白屏）

**PC 端操作**：
1. 打开 PC Chrome
2. 访问 `http://100.108.217.19:8889`
3. 按 F12 打开开发者工具
4. 看 Console 有什么错误

**如果 PC 端 OK 但手机端空白**：
- 手机浏览器问题
- 试 Chrome for Android 或 Firefox
- 试**无痕模式**（避免缓存干扰）

### 第 7 步：仍然访问不了

打开手机 Tailscale App，复制**手机 Tailscale IP**：
- 一般是 `100.x.x.x` 形式
- 把这个 IP 告诉我

打开 PC PowerShell 跑：
```powershell
tailscale ping <手机 Tailscale IP>
```

如果超时：
- 手机节点离线
- Tailscale 中继服务器没工作
- 让手机切换到另一个网络

如果 pong：
- PC → 手机方向通
- 反向（手机 → PC）不通，说明是 PC 防火墙或端口问题
- 检查防火墙规则：
  ```powershell
  Get-NetFirewallRule | Where-Object { $_.DisplayName -match 'Open Notebook' }
  ```

## 快速对照表

| 现象 | 原因 | 解决 |
|------|------|------|
| 手机 Tailscale 节点灰 | 节点离线 | 重启 Tailscale |
| Nekobox 开着，Tailscale 灰 | VPN slot 冲突 | 关 Nekobox |
| 手机 Tailscale 绿但打不开 8889 | PC 防火墙/端口 | 检查防火墙规则 |
| 打开 8889 看到登录页但密码错 | 密码复制错 | 重新复制 |
| 打开 8889 看到完整 UI | 成功！| 登录用 |
| 打开 8889 看到白屏 | 静态资源加载失败 | PC Chrome F12 看错误 |

## 切换方案

如果 Tailscale 始终不通，**换 Cloudflare Tunnel**：

1. 临时域名：`https://eyed-springs-replied-paintings.trycloudflare.com`
2. 这个域名**不依赖 Tailscale**，**不依赖 VPN slot**
3. 4G/WiFi/任何网络都行
4. 但 Mihomo 代理会拦截，需要在 Merge.yaml 加 `trycloudflare.com` DIRECT 规则（已加，需要重启 Clash Verge）
5. 或者直接用 IP 而不是域名：
   - 走 Tailscale IP：`100.108.217.19:8889`（已验证通）
   - 走局域网 IP：`192.168.5.22:3000`（同 WiFi 时）

## 一键收集诊断信息

手机端无法访问时，跑这个 PC 端命令收集所有信息：

```powershell
# Tailscale 状态
tailscale status
# Tailscale ping
tailscale ping 100.115.184.63
# 防火墙规则
Get-NetFirewallRule | Where-Object { $_.DisplayName -match 'Open Notebook' } | Format-Table
# 端口监听
Get-NetTCPConnection -LocalPort 3000,5055,8000,8888,8889 -ErrorAction SilentlyContinue | Format-Table
# Caddy 健康
Invoke-WebRequest http://localhost:8889/api/config -UseBasicParsing | ConvertFrom-Json
```
