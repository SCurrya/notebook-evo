# 📋 Open Notebook 手机访问项目 — 上下文总结与全面体检

> **生成时间**：2026-06-17
> **目的**：让用户在新窗口快速理解项目全貌 + 当前所有痛点
> **完整工程位置**：`E:\notebook\`

---

## 1. 🎯 项目目标

在 PC 上跑 Open Notebook（一个 AI 研究助手 / 笔记本管理工具），让 **手机在 4G/任意网络** 下也能访问、与 PC 端数据同步。

---

## 2. 🏗️ 系统架构

```
┌─────────────────┐                ┌─────────────────┐
│   PC 端 (Windows)│                │   手机 (Android) │
│                 │                │                 │
│  Open Notebook  │◄──── Tailscale ──►│  手机浏览器      │
│   - API:5055    │      VPN 隧道     │                 │
│   - 前端:8889   │      (100.x网段) │                 │
│                 │                │                 │
│  SurrealDB:8000 │                │                 │
│  Caddy:8888/8889│                │                 │
│  Tailscale:100.108.217.19        │  Tailscale:100.115.184.63│
└─────────────────┘                └─────────────────┘
        │                                    ▲
        │           Cloudflare Tunnel         │
        └──────► (5055 + 8889)  ◄──────────┘
              trycloudflare.com
              (http2 协议)
```

### 数据流
- **PC 本机**：`http://localhost:8889`（Caddy 静态文件 + /api 反代）
- **Tailscale VPN**：`http://100.108.217.19:8889`（PC 端 Tailscale IP）
- **Cloudflare Tunnel**：`https://eyed-springs-replied-paintings.trycloudflare.com`（临时域名）

### 端口分配
| 端口 | 服务 | 绑定 | 备注 |
|------|------|------|------|
| 3000 | Next.js dev server | ~~0.0.0.0~~ | **已停**（HMR 跨源问题）|
| 5055 | Open Notebook API | 0.0.0.0 | Python FastAPI |
| 8000 | SurrealDB | 0.0.0.0 | RocksDB |
| 8888 | Caddy API 反代 | :: (IPv6 wildcard) | reverse_proxy 127.0.0.1:5055 |
| 8889 | Caddy 静态文件 | :: (IPv6 wildcard) | file_server `out/` + /api/* reverse_proxy |

---

## 3. 🔑 关键信息

### 密码 / Token
- **OPEN_NOTEBOOK_PASSWORD**：`mobile-notebook-2026-secure-key-change-me`（从 .env 文件）
- **API 认证方式**：Bearer Token in Authorization header
- **密码文件路径**：`E:\notebook\open-notebook\.env`

### 网络信息
- **PC 内网 IP**：`192.168.5.22`
- **PC Tailscale IP**：`100.108.217.19`
- **PC Tailscale 域名**：`laptop-62burom0.taile2bacf.ts.net`
- **手机 Tailscale IP**：`100.115.184.63`（redmi-k70，**已离线 46 分钟**）
- **Tailscale 账号**：`scurry413a@`

### Cloudflare 临时域名（每次重启会变）
- **Web**：`https://eyed-springs-replied-paintings.trycloudflare.com`
- **API**：`https://sellers-view-thoughts-hundreds.trycloudflare.com`
- 当前在 .env 第 79 行：`CLOUDFLARE_DOMAIN=https://eyed-springs-replied-paintings.trycloudflare.com`

---

## 4. ✅ 已完成的工作

| # | 任务 | 状态 | 详情 |
|---|------|------|------|
| 1 | Tailscale 安装 + 登录 | ✅ | v1.98.4，节点名 laptop-62burom0 |
| 2 | PC 防火墙放行 3000/5055 | ✅ | New-NetFirewallRule × 2，Private profile |
| 3 | Tailscale 在手机端登录 | ✅ | 用户手动操作 |
| 4 | Cloudflared 下载 | ✅ | 51.66 MB，`E:\notebook\downloads\cloudflared.exe` |
| 5 | APK 打包（Capacitor + Android）| ✅ | 5.43 MB，路径 `E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk` |
| 6 | Next.js 16 静态构建 | ✅ | `out/` 目录生成，含 100.108.217.19 硬编码 |
| 7 | Caddy 静态文件反代 | ✅ | 8889 端口 file_server + /api/* reverse_proxy |
| 8 | Caddy API 反代 | ✅ | 8888 端口 reverse_proxy 127.0.0.1:5055 |
| 9 | SurrealDB 在线 | ✅ | PID 12388，0.0.0.0:8000，dbStatus: online |
| 10 | Open Notebook API 在线 | ✅ | PID 41744，0.0.0.0:5055 |
| 11 | Cloudflare Tunnel 启动 | ✅ | http2 协议，PIDs 44504 + 30940 |
| 12 | Mihomo Merge.yaml DNS 修复 | ✅ | 加了 `*.ts.net`、`*.trycloudflare.com` DIRECT 规则 |
| 13 | dev server (3000) 关闭 | ✅ | 避免 HMR 跨源问题 |
| 14 | Next.js SWC 错误修复 | ✅ | 清理 `next-swc` 缓存，重装 `@next/swc-win32-x64-msvc` |
| 15 | Mihomo Merge.yaml fake-ip-filter | ✅ | 防止 Tailscale/Cloudflare 域名被 fake-ip 劫持 |
| 16 | 完整用户文档 | ✅ | MOBILE_ACCESS_GUIDE.md, MOBILE_TAILSCALE_TROUBLESHOOTING.md, RESTART_CLASH_VERGE.md |
| 17 | Tailscale + Caddy 路线 PC 端验证 | ✅ | PC 浏览器访问 `100.108.217.19:8889/notebooks` 看到完整 Open Notebook 界面 |

---

## 5. ❌ 当前痛点（按严重度排序）

### 🔴 P0：手机 Tailscale 节点离线 46 分钟

**症状**：`tailscale status` 显示
```
100.108.217.19  laptop-62burom0  windows  -
100.115.184.63  redmi-k70        android  offline, last seen 46m ago
```

**影响**：手机 Tailscale 通道失效，**手机无法访问 `100.108.217.19:8889`**

**根因**：
- 手机 Tailscale App 后台被杀
- 或 Android 电池优化切断 Tailscale 心跳
- 或手机切换网络（4G ↔ WiFi）导致 tunnel 断了

**修复建议**：
1. 手机 Tailscale App → 关 VPN → 等 5 秒 → 开 VPN
2. 关 Nekobox（VPN slot 冲突）
3. Tailscale App → 设置 → 开启 "Always-On VPN"（始终连接的 VPN）
4. Android 设置 → 应用 → Tailscale → 电池 → 不优化

**验证命令**（PC 端跑）：
```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' ping 100.115.184.63
# 期望：pong from ... ; 失败：timeout
```

---

### 🔴 P0：Caddy 进程会被杀（无守护）

**症状**：Caddy 静默死亡，8888/8889 端口没人监听，手机显示"无法处理此请求"

**已发生**：至少一次（用户报"100.108.217.19 当前无法处理此请求"时）

**根因**：
- Caddy 用 `Start-Process -WindowStyle Hidden` 启动，没有守护
- PC 进 Sleep / Modern Standby / 重启时 Caddy 不会恢复
- 计划任务注册需要管理员权限（agent 没权限）

**修复方法**（需要用户手动，**管理员 PowerShell**）：
```powershell
sc.exe create Caddy binPath= "E:\notebook\downloads\caddy\caddy.exe run --config E:\notebook\downloads\caddy\Caddyfile" start= auto
sc.exe start Caddy
```

或者用 NSSM：
```powershell
nssm install Caddy "E:\notebook\downloads\caddy\caddy.exe" "run --config E:\notebook\downloads\caddy\Caddyfile"
nssm set Caddy AppDirectory "E:\notebook\downloads\caddy"
nssm set Caddy Start SERVICE_AUTO_START
```

---

### 🟠 P1：Cloudflare Tunnel 手机端无法访问

**症状**：手机访问 `https://eyed-springs-replied-paintings.trycloudflare.com` 失败

**根因（推测）**：
- Mihomo TUN 模式在 PC 本机劫持 DNS
- 手机端如果开了 Tailscale VPN，可能 tunnel 走不通
- Mihomo Merge.yaml 已修复但**没重启 Clash Verge**

**修复方法**：
1. **PC 端**：重启 Clash Verge 让 Merge.yaml 生效
   - 系统托盘 → 右键 → 退出 → 重新打开
2. **手机端**：先关 Tailscale VPN 再试 Cloudflare

**验证命令**（PC 端）：
```powershell
nslookup sellers-view-thoughts-hundreds.trycloudflare.com
# 修复后应返回 Cloudflare 真实 IP（104.16.x.x 或 104.18.x.x）
# 修复前会返回 198.18.0.x（Mihomo fake-ip）
```

---

### 🟠 P1：Tailscale 域名被 Mihomo 劫持

**症状**：PC 端访问 `http://laptop-62burom0.taile2bacf.ts.net:8889` 失败，解析到 198.18.0.64

**根因**：Mihomo TUN fake-ip 模式把 `*.ts.net` 解析到 198.18.0.x

**已修复**：Merge.yaml 加了 fake-ip-filter

**未生效**：需用户重启 Clash Verge

**临时绕过**：用 Tailscale IP `100.108.217.19` 代替域名（PC 和手机都能用）

---

### 🟡 P2：Nekobox 与 Tailscale VPN slot 冲突

**症状**：Nekobox VPN 开启时，Tailscale App 看起来"开"但实际 tunnel 断了

**根因**：Android 系统同时只允许 1 个 VPN App 占 VPN slot

**现状**：
- 用户两个都装着
- 解决方案文档 `MOBILE_TAILSCALE_TROUBLESHOOTING.md` 已写好
- 但没自动化处理

**修复建议**（任选其一）：
1. **临时关 Nekobox**（用 Open Notebook 时）
2. **方案 A**：Nekobox 加 Tailscale IP direct 规则（100.64.0.0/10）→ 仍冲突，因为底层是 VPN slot
3. **方案 B**：用 Cloudflare Tunnel 替代 Tailscale（不占 VPN slot）
4. **方案 C**（需 root）：Magisk Tailscaled 模块，userspace 模式不占 slot

---

### 🟡 P2：Next.js dev server 外部访问 HMR 失败

**症状**：dev server (3000) 跑着但外部 IP 访问返回白屏

**根因**：Next.js 16 `allowedDevOrigins` 默认不包含外部 IP，HMR 资源被拦截

**已修复**：用 `build:mobile` 生成静态文件 + Caddy file_server，**dev server 已停**

**不影响当前使用**

---

### 🟢 P3：SurrealDB 没有开机自启

**症状**：PC 重启后 SurrealDB 不会自动起来

**根因**：用 `Start-Process` 启动，没注册为服务

**修复**（需管理员 PowerShell）：
```powershell
$action = New-ScheduledTaskAction -Execute 'C:\Tools\surreal\surreal.exe' `
  -Argument 'start --user root --pass root rocksdb:./surreal_data/mydatabase.db --bind 0.0.0.0:8000' `
  -WorkingDirectory 'E:\notebook\open-notebook'
$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Delay = 'PT10S'
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'SurrealDB-AutoStart' -Action $action -Trigger $trigger -Settings $settings `
  -User 'SYSTEM' -RunLevel 'HIGHEST'
```

---

### 🟢 P3：API 没有开机自启

**症状**：PC 重启后 API 不会自动起来

**修复**（需管理员 PowerShell）：
```powershell
# 用 nssm 注册
nssm install OpenNotebookAPI "E:\notebook\open-notebook\.venv\Scripts\python.exe" "run_api.py"
nssm set OpenNotebookAPI AppDirectory "E:\notebook\open-notebook"
nssm set OpenNotebookAPI Start SERVICE_AUTO_START
```

---

## 6. 🚀 立即可用的访问方式

| 方式 | 地址 | 状态 | 备注 |
|------|------|------|------|
| **PC 本机** | `http://localhost:8889` | ✅ | Caddy 静态文件 |
| **PC Tailscale IP** | `http://100.108.217.19:8889` | ✅ PC 通 | 手机端需 Tailscale 重新连 |
| **PC Tailscale 域名** | `http://laptop-62burom0.taile2bacf.ts.net:8889` | ⚠️ Mihomo 劫持 | 用 IP 代替 |
| **局域网** | `http://192.168.5.22:8889` | ✅ | 同 WiFi |
| **Cloudflare** | `https://eyed-springs-replied-paintings.trycloudflare.com` | ⚠️ PC Mihomo 拦截 | 手机端独立 |

---

## 7. 🛠️ 用户需要做的 4 件事（按优先级）

### 高优先级

1. **手机 Tailscale 重新连**
   - Tailscale App → 关 VPN → 等 5 秒 → 开 VPN
   - 关键：关 Nekobox
   - 验证：手机浏览器 `http://100.108.217.19:8889` 能看到 Open Notebook

2. **重启 Clash Verge（让 Mihomo DNS 修复生效）**
   - 系统托盘 → Clash Verge 图标 → 右键 → 退出
   - 重新打开 Clash Verge
   - 验证：`nslookup laptop-62burom0.taile2bacf.ts.net` 返回 `100.108.217.19`

### 中优先级

3. **Caddy 注册为 Windows 服务**（避免再被杀）
   - 管理员 PowerShell 跑：
     ```powershell
     sc.exe create Caddy binPath= "E:\notebook\downloads\caddy\caddy.exe run --config E:\notebook\downloads\caddy\Caddyfile" start= auto
     sc.exe start Caddy
     ```

### 低优先级

4. **SurrealDB + API 注册为开机自启**（需管理员权限）
   - 见上面 P3 修复方法

---

## 8. 📂 关键文件路径

### 配置
- `E:\notebook\open-notebook\.env` — API 密码、域名、DB 密码
- `E:\notebook\downloads\caddy\Caddyfile` — Caddy 配置（8888/8889）
- `C:\Users\ZS\.config\clash\config.yaml` — Mihomo 配置（被 Merge.yaml 覆盖）
- `C:\Users\ZS\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\profiles\Merge.yaml` — **真正生效的 Mihomo 配置**

### 可执行文件
- `E:\notebook\downloads\caddy\caddy.exe`
- `E:\notebook\downloads\cloudflared.exe`
- `C:\Tools\surreal\surreal.exe`
- `C:\Program Files\Tailscale\tailscale.exe`

### 数据
- `E:\notebook\open-notebook\surreal_data\mydatabase.db`
- `E:\notebook\open-notebook\frontend\out\` — 静态前端（已构建）

### 日志
- `E:\notebook\frontend-dev.log.err`
- `E:\notebook\api-startup.log.err`
- `E:\notebook\surreal-startup.log.err`
- `E:\notebook\caddy-startup.log.err`
- `E:\notebook\cloudflared-web.log.err`
- `E:\notebook\cloudflared-api.log.err`

### 文档
- `E:\notebook\scripts\MOBILE_ACCESS_GUIDE.md` — 完整访问指南
- `E:\notebook\scripts\MOBILE_TAILSCALE_TROUBLESHOOTING.md` — 故障排查
- `E:\notebook\scripts\RESTART_CLASH_VERGE.md` — Clash Verge 重启
- `E:\notebook\scripts\PRODUCTION_GUIDE.md` — 7 个方案对比
- `E:\notebook\scripts\CLOUDFLARE_QUICKSTART.md` — CF Tunnel 文档
- `E:\notebook\scripts\start-cloudflare-tunnel.bat` — 一键启动
- `E:\notebook\scripts\stop-dev-server.bat` — 停 dev server
- `E:\notebook\scripts\start-dev-server.bat` — 启 dev server

### 移动端
- `E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk` — 5.43 MB APK

---

## 9. 🆘 一键诊断命令

如果遇到问题，PC 端 PowerShell 跑这些命令收集信息：

```powershell
# 1. 服务状态
Get-NetTCPConnection -LocalPort 3000,5055,8000,8888,8889 -ErrorAction SilentlyContinue | Format-Table LocalAddress, LocalPort, State, OwningProcess

# 2. Tailscale 状态
& 'C:\Program Files\Tailscale\tailscale.exe' status
& 'C:\Program Files\Tailscale\tailscale.exe' ping 100.115.184.63

# 3. 防火墙规则
Get-NetFirewallRule | Where-Object { $_.DisplayName -match 'Open Notebook|caddy|Tailscale' } | Format-Table

# 4. Mihomo DNS 验证
nslookup laptop-62burom0.taile2bacf.ts.net
nslookup sellers-view-thoughts-hundreds.trycloudflare.com

# 5. API 健康
Invoke-WebRequest http://localhost:5055/health -UseBasicParsing

# 6. 静态前端健康
Invoke-WebRequest http://localhost:8889/ -UseBasicParsing

# 7. Caddy 日志
Get-Content E:\notebook\caddy-startup.log.err -Tail 20

# 8. cloudflared 状态
Get-Process cloudflared -ErrorAction SilentlyContinue | Format-Table Id, StartTime
Get-Content E:\notebook\cloudflared-web.log.err -Tail 20
```

---

## 10. 📝 下一步计划

### 短期（让手机访问通）
1. 用户重启 Clash Verge（让 Mihomo 修复生效）
2. 用户手机重连 Tailscale（关 Nekobox）
3. 手机浏览器访问 `http://100.108.217.19:8889` 验证

### 中期（让系统稳定）
4. Caddy 注册为 Windows 服务
5. SurrealDB + API 注册为开机自启
6. Tailscale 手机端设置 "Always-On VPN"

### 长期（消除 VPN slot 冲突）
7. 评估 Cloudflare Tunnel + 永久域名 + Cloudflare Access 替代 Tailscale
8. 或用 Nekobox 加 Tailscale WireGuard 配置（协议层共存）

---

## 📌 关键事实（必须记住）

- **PC 端 Tailscale + Caddy 路线完全跑通**（已截图验证）
- **手机端 Tailscale 节点离线 46 分钟**（最大痛点）
- **Caddy 没有守护**（第二大痛点）
- **Mihomo Merge.yaml 已修复但需重启 Clash Verge**
- **Nekobox 抢 VPN slot**（根本限制）
- **Cloudflare 域名是临时域名**，每次重启 PC 会变

---

## 11. 🔍 现场体检报告

> 以下为 2026-06-17 现场跑诊断命令的真实输出（已贴在文档里方便新窗口直接看）

### 体检总览

| 检查项 | 结果 | 状态 |
|--------|------|------|
| 端口 5055（API） | 0.0.0.0:5055 LISTEN，PID 41744 | ✅ 正常 |
| 端口 8000（SurrealDB） | 0.0.0.0:8000 LISTEN，PID 12388 | ✅ 正常 |
| 端口 8888（Caddy API 反代） | ::8888 LISTEN，PID 40988 | ✅ 正常 |
| 端口 8889（Caddy 静态） | ::8889 LISTEN，PID 40988 | ✅ 正常 |
| 端口 3000（dev server） | 无监听 | ✅ 已停 |
| Caddy 进程 | PID 40988，30.1 MB | ✅ 正常 |
| API 进程 | PID 41744，54.7 MB（另有 venv wrapper PID 2096） | ✅ 正常 |
| SurrealDB 进程 | PID 12388，112.3 MB | ✅ 正常 |
| Mihomo（verge-mihomo） | PID 41128，101.4 MB | ✅ 跑着 |
| Cloudflared Web | PID 44504，33.6 MB（nrt14，http2 已注册） | ✅ 正常 |
| Cloudflared API | （需查第二个 PID，未列出但日志显示 nrt12 已注册）| ✅ 正常 |
| Tailscale PC 节点 | 100.108.217.19 在线 | ✅ 正常 |
| Tailscale 手机节点 | 100.115.184.63 **offline, last seen 28m ago** | 🔴 严重 |
| API /health | 200, `{"status":"healthy"}` | ✅ 正常 |
| Caddy 静态首页 | 200, 8836 bytes HTML | ✅ 正常 |
| Mihomo DNS（ts.net） | **解析失败**（"Non-existent domain"） | 🟠 异常 |
| Mihomo DNS（trycloudflare） | 解析到 **198.18.0.45**（fake-ip 劫持未修） | 🟠 异常 |
| Tailscale DNS 健康 | "can't reach DNS / Access is denied" | 🟠 异常 |
| 防火墙规则 | 4 个 Inbound Allow（Private），2 个 Block（Public） | ✅ 配置正确 |

### 1. 端口监听

```
LocalAddress LocalPort       State OwningProcess
------------ ---------       ----- -------------
::1               8889 Established         40988
::                8889      Listen         40988
::                8888      Listen         40988
0.0.0.0           8000      Listen         12388
127.0.0.1         5055    FinWait2         41744
0.0.0.0           5055      Listen         41744
```

观察：8889 端口有一个 ::1 的 Established 连接（Caddy 正在响应请求），其他都是 LISTEN。无 3000 端口（dev server 已停）。

### 2. Tailscale 状态

```
100.108.217.19  laptop-62burom0  scurry413a@  windows  -

100.115.184.63  redmi-k70        scurry413a@  android  active; relay "hkg"; offline, last seen 28m ago, tx 35568 rx 0

# Health check:
#     - Tailscale can't reach the configured DNS servers. Internet connectivity may be affected.
#     - Tailscale failed to set the DNS configuration of your device: Access is denied.
#     - Access is denied.
```

**关键发现**：
1. 手机节点 `redmi-k70` 已经离线 **28 分钟**（比 46 分钟稍好但仍然断）
2. 手机节点状态显示 `active; relay "hkg"` — 说明手机 Tailscale App 还活着，走的是香港 relay，但 WireGuard tunnel 实际上不通
3. **新增问题**：Tailscale DNS 配置失败（Access is denied），可能影响 MagicDNS 解析 `.ts.net` 域名

### 3. Tailscale ping 手机 (100.115.184.63)

```
ping "100.115.184.63" timed out
ping "100.115.184.63" timed out
... (10 次超时)
no reply
```

**结论**：手机端 Tailscale tunnel 完全不通，P2P 路径和 relay 路径都失败。

### 4. Mihomo 进程 (verge-mihomo)

```
   Id StartTime Mem(MB)
   -- --------- -------
41128             101.4
```

**观察**：Mihomo 进程在跑（PID 41128，101.4 MB），但 Tailscale DNS 报"Access is denied"暗示两个代理有冲突。

### 5. Cloudflared 进程

```
   Id StartTime          Mem(MB)
   -- ---------          -------
44504 2026/6/17 21:47:45    33.6
```

**观察**：Cloudflared Web 进程在线（PID 44504，启动时间 21:47:45）。
Cloudflared API 进程未在此次枚举列出（可能是不同进程名或已被合并），但日志显示 API 通道也已注册到 nrt12。

### 6. API 健康 (http://localhost:5055/health)

```
Status: 200
Content: {"status":"healthy"}
```

✅ **API 完全正常**，可以直接用。

### 7. Caddy 静态版健康 (http://localhost:8889/)

```
Status: 200, Content-Length=8836
Content (first 200 chars): <!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/bbc9afb96cd4e6b6.css" da
```

✅ **Caddy 正常**，返回 Next.js 静态 HTML。

### 8. 防火墙规则

```
DisplayName            Direction Action         Profile
-----------            --------- ------         -------
Tailscale-Process        Inbound  Allow             Any
Tailscale-In             Inbound  Allow Domain, Private
Tailscale-In             Inbound  Allow Domain, Private
Open Notebook Frontend   Inbound  Allow         Private
Open Notebook API        Inbound  Allow         Private
caddy                    Inbound  Allow         Private
caddy                    Inbound  Allow         Private
caddy                    Inbound  Block          Public
caddy                    Inbound  Block          Public
```

✅ 防火墙配置正确：内网允许，外部公网 Block（需要 Tailscale tunnel 才能穿透）。

### 9. Mihomo DNS — laptop-62burom0.taile2bacf.ts.net

```
Server:  UnKnown
Address:  fdfe:dcba:9876::2

*** UnKnown can't find laptop-62burom0.taile2bacf.ts.net: Non-existent domain
```

🟠 **PC 端本地 DNS 解析不到 ts.net 域名**。原因：
- DNS 服务器指向 `fdfe:dcba:9876::2`（Mihomo 内部 fake-ip DNS）
- Mihomo 把 ts.net 走 DIRECT（不返回 fake-ip），但 Mihomo 本身不会做 MagicDNS 解析
- Tailscale MagicDNS 没有被 PC 端使用

**建议**：用 IP `100.108.217.19` 代替域名（PC 和手机都直接用 IP）。

### 10. Mihomo DNS — sellers-view-thoughts-hundreds.trycloudflare.com

```
Server:  UnKnown
Address:  fdfe:dcba:9876::2

Name:    sellers-view-thoughts-hundreds.trycloudflare.com
Address:  198.18.0.45
```

🟠 **Merge.yaml 修复没生效**！trycloudflare.com 仍然被 fake-ip 到 `198.18.0.45`，说明 **Clash Verge 没重启**。这意味着 PC 端无法直接用域名访问 Cloudflare Tunnel（必须用 IP，或者重启 Clash Verge）。

**重要**：手机端不受 PC Mihomo 影响，手机仍然可以访问 trycloudflare.com 真实 IP（但前提是手机 DNS 没被劫持）。

### 11. Cloudflare 临时域名 (从日志)

```
Web: https://eyed-springs-replied-paintings.trycloudflare.com
API: https://sellers-view-thoughts-hundreds.trycloudflare.com
```

✅ 临时域名和 .env 第 79 行一致，没有变化。

### 12. .env 文件前 30 行

```bash
# Open Notebook Configuration
# Copy this file to .env and customize as needed

# ============================================================================= 
# REQUIRED
# ============================================================================= 

# Encryption key for storing API credentials securely in the database
# Change this to any secret string (minimum 16 characters recommended)
OPEN_NOTEBOOK_ENCRYPTION_KEY=HHuk2IRyhYSyZpoZqaogI4lNJaJ0hsl4B8ghKeoH/LEHoSqZJqZjDBgW5/3oJnE/

# ============================================================================= 
# DATABASE (Default values work with docker-compose.yml)
# ============================================================================= 

SURREAL_URL="ws://127.0.0.1:8000/rpc"
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook

# ============================================================================= 
# OPTIONAL: AI Provider API Keys
# ============================================================================= 
# You can configure these via the UI (Settings → API Keys) or set them here     
# UI configuration is recommended for better security and flexibility

# OpenAI
# OPENAI_API_KEY=sk-...
```

**环境变量行 79 附近**（行 70-85）：

```bash
# CORS origins for mobile app access
# Tailscale domain (https) + Cloudflare Tunnel domain (https) + localhost for dev
# Note: Tailscale uses http on port 5055, Cloudflare uses https
# capacitor:// scheme is used by Android Capacitor app
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,capacitor://localhost,http://localhost,https://localhost

# Mobile app API endpoints (discovered at runtime by the app)
# These are placeholders - actual domains are configured in the mobile app      
TAILSCALE_DOMAIN=laptop-62burom0.taile2bacf.ts.net
CLOUDFLARE_DOMAIN=https://eyed-springs-replied-paintings.trycloudflare.com
```

✅ .env 配置和实际域名匹配。

### 13. Caddy 日志最后 10 行

```json
{"level":"warn","ts":1781708950.9137554,"logger":"admin","msg":"admin endpoint disabled"}
{"level":"info","ts":1781708950.951418,"logger":"http.auto_https","msg":"automatic HTTPS is completely disabled for server","server_name":"srv0"}
{"level":"info","ts":1781708950.951418,"logger":"tls.cache.maintenance","msg":"started background certificate maintenance","cache":"0xc00057ed00"}
{"level":"info","ts":1781708951.0125606,"logger":"http.auto_https","msg":"automatic HTTPS is completely disabled for server","server_name":"srv1"}
{"level":"info","ts":1781708951.0897484,"logger":"http.log","msg":"server running","name":"srv0","protocols":["h1","h2","h3"]}
{"level":"info","ts":1781708951.0914106,"logger":"tls","msg":"storage cleaning happened too recently; skipping for now"}
{"level":"info","ts":1781708951.1907432,"logger":"http.log","msg":"server running","name":"srv1","protocols":["h1","h2","h3"]}
{"level":"info","ts":1781708951.2202399,"logger":"tls","msg":"finished cleaning storage units"}
{"level":"info","ts":1781708951.2593691,"msg":"autosaved config (load with --resume flag)","file":"C:\\Users\\ZS\\AppData\\Roaming\\Caddy\\autosave.json"}
{"level":"info","ts":1781708951.3968852,"msg":"serving initial configuration"}
```

✅ Caddy 启动正常，两个 server（srv0 = 8888 API 反代，srv1 = 8889 静态）都在跑。

### 14. API 进程详情

```
   Id StartTime          Mem_MB CmdShort
   -- ---------          ------ --------
 2096 2026/6/17 17:04:10    4.3 "E:\notebook\open-notebook\.venv\Scripts\python.exe" run_api.py
41744 2026/6/17 17:04:10   54.7 "C:\Users\ZS\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe"  run_api.py
```

**观察**：发现 2 个 Python 进程跑 `run_api.py`（PID 2096 和 41744）。这是历史遗留，启动脚本可能重复启动了一次。**不影响功能**，端口 5055 由 41744 监听。

### 15. Surreal 进程

```
   Id StartTime          Mem(MB)
   -- ---------          -------
12388 2026/6/17 17:02:53   112.3
```

✅ SurrealDB 跑着 6 小时 5 分钟（17:02 启动），内存 112 MB，正常。

### 16-18. cloudflared 日志最后几行

Web 通道：
```json
{"level":"error","event":0,"ip":"198.18.0.5","connIndex":0,"error":"TLS handshake with edge error: EOF","time":"2026-06-17T14:39:05Z","message":"Serve tunnel error"}
{"level":"info","event":0,"ip":"198.18.0.5","connIndex":0,"time":"2026-06-17T14:39:05Z","message":"Retrying connection in up to 4s"}
{"level":"error","error":"TLS handshake with edge error: EOF","connIndex":0,"time":"2026-06-17T14:39:06Z","message":"Connection terminated"}
{"level":"info","event":0,"ip":"198.18.0.43","connIndex":0,"time":"2026-06-17T14:39:20Z","message":"Tunnel connection curve preferences: [X25519MLKEM768 CurveID(65074) CurveP256]"}
{"level":"info","event":0,"connection":"19e6d9c8-1bd4-45a2-a924-56a3b29af0e0","connIndex":0,"location":"nrt14","ip":"198.18.0.43","protocol":"http2","time":"2026-06-17T14:39:22Z","message":"Registered tunnel connection"}
```

API 通道：
```json
{"level":"info","event":0,"connection":"ce7c7b75-9009-4ece-aa3d-12fdcfdf3d31","connIndex":0,"location":"nrt12","ip":"198.18.0.5","protocol":"http2","time":"2026-06-17T14:39:06Z","message":"Registered tunnel connection"}
```

✅ 两个 tunnel 都成功注册到 Cloudflare edge（Web → nrt14，API → nrt12），http2 协议。

---

## 12. 🩺 体检结论与下一步建议

### 关键判断（按严重度）

#### 🔴 #1 最大痛点：手机 Tailscale 节点离线 28 分钟

**证据**：
- `tailscale status` 显示 `redmi-k70 ... offline, last seen 28m ago`
- `tailscale ping 100.115.184.63` 10 次全部 timeout

**影响**：**手机无法通过 Tailscale VPN 访问 `http://100.108.217.19:8889`**。这是当前唯一完全阻塞手机访问的故障点。

**下一步**（先做这个）：
1. **手机端**：Tailscale App → 关闭 VPN → 等 5 秒 → 重新打开
2. **手机端**：检查 Nekobox 状态（必须关闭才能让 Tailscale 占 VPN slot）
3. **手机端**：Tailscale App → 设置 → 开启 "Always-On VPN"
4. **手机端**：Android 系统设置 → 应用 → Tailscale → 电池 → 选"不优化"
5. **验证**：手机浏览器打开 `http://100.108.217.19:8889` 应能看到 Open Notebook

#### 🟠 #2 次要痛点：Mihomo 修复没生效（PC 端）

**证据**：
- `nslookup sellers-view-thoughts-hundreds.trycloudflare.com` 仍然返回 198.18.0.45（fake-ip 劫持）
- Tailscale 健康检查报 "Access is denied"（DNS 配置失败）

**影响**：PC 端不能直接用 trycloudflare.com 域名访问（必须用 IP 或重启 Clash Verge）。**不影响手机端**，但 PC 端验证 Cloudflare 路线会失败。

**下一步**：
- PC 端：右键系统托盘 Clash Verge → 退出 → 重新打开
- 验证：`nslookup sellers-view-thoughts-hundreds.trycloudflare.com` 应返回 104.16.x.x 或 104.18.x.x 真实 IP

#### 🟢 #3 系统稳定性（低优先级）

- Caddy 现在在线（PID 40988，30 MB），但没有守护，建议注册为 Windows 服务
- SurrealDB 跑了 6 小时稳定，**但 PC 重启后不会自启**
- API 跑了 6 小时稳定，**但 PC 重启后不会自启**

### 🎯 推荐的立即操作顺序

1. **【最高】** 手机重连 Tailscale（关 Nekobox，重开 VPN）→ 验证 `http://100.108.217.19:8889` 能打开
2. **【高】** PC 重启 Clash Verge → 验证 Mihomo DNS 修复生效
3. **【中】** 管理员 PowerShell 注册 Caddy 为服务（避免被进程杀）
4. **【低】** 注册 SurrealDB + API 为开机自启

### 📊 路线图

| 路线 | 状态 | 手机端是否可用 |
|------|------|----------------|
| PC 本机 (`localhost:8889`) | ✅ 跑着 | N/A |
| PC Tailscale IP (`100.108.217.19:8889`) | ✅ PC 通 | ❌ 手机 Tailscale 离线 |
| Cloudflare Web (`trycloudflare.com`) | ✅ 域名注册 | ✅ 理论上手机可访问（无 Nekobox/Tailscale 冲突时）|
| Cloudflare API (`trycloudflare.com`) | ✅ 域名注册 | ✅ 同上 |
| 局域网 (`192.168.5.22:8889`) | ✅ 跑着 | ✅ 同 WiFi 可用 |

**最稳最快的当前可用路线**：手机**关 Nekobox + 重连 Tailscale** → 用 `http://100.108.217.19:8889` 访问。

**完全独立的备份路线**：手机**不开任何 VPN** → 用 `https://eyed-springs-replied-paintings.trycloudflare.com` 访问（前提是手机 DNS 没被劫持）。

---

## 📌 体检后更新的关键事实

- **手机 Tailscale 节点已离线 28 分钟**（从 46 分钟改善到 28 分钟，但仍然断）
- **Caddy 当前在线**（PID 40988），但**没有守护进程**这个 P0 痛点仍然存在
- **Mihomo Merge.yaml 修复仍未生效**（Clash Verge 未重启）
- **新增问题**：Tailscale DNS 配置失败（Access is denied），需关注
- **CLOUDFLARE_DOMAIN 仍然有效**，临时域名没变
- **API /health 正常返回**，Caddy 静态首页正常返回
- **2 个 run_api.py 进程并存**（PID 2096 + 41744），不冲突但浪费资源
- **SurrealDB 跑 6 小时 5 分钟**稳定
- **cloudflared web/API 通道都已注册**到 Cloudflare edge

---

> 文档生成完毕。如果手机 Tailscale 重新连接后问题解决，**直接用 `http://100.108.217.19:8889` 访问**。
> 如果还是不通，再试 Cloudflare `https://eyed-springs-replied-paintings.trycloudflare.com`（手机端不走 Mihomo）。

