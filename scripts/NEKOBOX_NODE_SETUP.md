# 手机 Nekobox 通过 Tailscale 访问 PC 的 Open Notebook

> 本文档说明：如何让手机 **Nekobox（仅作 SOCKS5/HTTP 客户端）**通过 Tailscale 加密隧道访问 PC 上的 Open Notebook（端口 5055/3000），
> 同时解决 Nekobox VPN 和 Tailscale VPN 的 slot 冲突。

## 1. 当前 PC 端反代部署状态

| 组件 | 状态 | 说明 |
| --- | --- | --- |
| Open Notebook API | 运行中 | `127.0.0.1:5055`（python 进程） |
| Open Notebook 前端 | 运行中 | `127.0.0.1:3000`（node 进程） |
| SurrealDB | 运行中 | `0.0.0.0:8000` |
| Clash Verge (verge-mihomo) | 运行中 | 7897 (HTTP), 198.18.0.1:14710 (SOCKS) — **仅 127.0.0.1 / 198.18.0.1**，手机不可达 |
| Tailscale | 已登录 | 100.108.217.19，节点名 `laptop-62burom0` |
| **Caddy 反代（本次部署）** | **已启动** | **0.0.0.0:8888 → 127.0.0.1:5055** |

## 2. 已部署的 Caddy 反向代理

### 2.1 部署位置

- Caddy 可执行文件：`E:\notebook\downloads\caddy\caddy.exe`
- Caddyfile：`E:\notebook\downloads\caddy\Caddyfile`
- API 访问日志：`E:\notebook\downloads\caddy\access-api.log`
- 前端访问日志：`E:\notebook\downloads\caddy\access-web.log`
- 启动日志：`E:\notebook\caddy-startup.log` / `E:\notebook\caddy-startup.err.log`
- Caddy 进程 PID：`27380`（重启后会变）

### 2.2 监听端口

| 端口 | 转发目标 | 用途 |
| --- | --- | --- |
| `0.0.0.0:8888` | `127.0.0.1:5055` | Open Notebook API |
| `0.0.0.0:8889` | `127.0.0.1:3000` | Open Notebook 前端（目前上游 500，可修复） |

### 2.3 验证结果

```
localhost:8888/health               → 200 {"status":"healthy"}
localhost:8888/                     → 200 {"message":"Open Notebook API is running"}
100.108.217.19:8888/health          → 200  (走 Tailscale IP)
100.108.217.19:8888/                → 200  (走 Tailscale IP)
```

### 2.4 启动 / 停止 / 重启

```powershell
# 启动（隐藏窗口，日志重定向）
Set-Location 'E:\notebook\downloads\caddy'
$proc = Start-Process -FilePath '.\caddy.exe' `
  -ArgumentList 'run','--config','Caddyfile' `
  -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput 'E:\notebook\caddy-startup.log' `
  -RedirectStandardError 'E:\notebook\caddy-startup.err.log'

# 停止（通过 PID 或进程名）
Get-Process -Name caddy | Stop-Process -Force

# 重启
Get-Process -Name caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
Set-Location 'E:\notebook\downloads\caddy'
Start-Process -FilePath '.\caddy.exe' `
  -ArgumentList 'run','--config','Caddyfile' `
  -WindowStyle Hidden `
  -RedirectStandardOutput 'E:\notebook\caddy-startup.log' `
  -RedirectStandardError 'E:\notebook\caddy-startup.err.log'
```

### 2.5 开机自启（可选）

把 Caddy 注册成 Windows 服务，方法二选一：

**方法 A：nssm（推荐）**

```powershell
# 下载 nssm 后
nssm install Caddy 'E:\notebook\downloads\caddy\caddy.exe' 'run --config E:\notebook\downloads\caddy\Caddyfile'
nssm set Caddy AppDirectory 'E:\notebook\downloads\caddy'
nssm set Caddy AppStdout 'E:\notebook\caddy-startup.log'
nssm set Caddy AppStderr 'E:\notebook\caddy-startup.err.log'
nssm set Caddy Start SERVICE_AUTO_START
nssm start Caddy
```

**方法 B：计划任务**

```powershell
$action  = New-ScheduledTaskAction -Execute 'E:\notebook\downloads\caddy\caddy.exe' `
           -Argument 'run --config E:\notebook\downloads\caddy\Caddyfile' `
           -WorkingDirectory 'E:\notebook\downloads\caddy'
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName 'CaddyOpenNotebook' -Action $action -Trigger $trigger `
            -RunLevel Highest -Description 'Caddy reverse proxy for Open Notebook'
```

## 3. Nekobox 客户端配置

### 3.1 重要认知

> ⚠️ **Nekobox 是 SOCKS5 / HTTP 代理客户端，不是 HTTP 浏览器。**
> - Nekobox 的"VPN 模式"在 Android 上是基于 VpnService 的全局 TCP 代理
> - 它**不能**用来"代理访问一个网站"——它代理的是手机应用发出的 TCP 流量
> - 因此 Nekobox 真正能做的，是让手机 app **走 Tailscale 隧道 + PC 上其他代理出口**访问外网

> ⚠️ **Android VPN slot 只有一个。** 不能同时开 Tailscale VPN + Nekobox VPN。

### 3.2 走 Tailscale 隧道访问 PC 资源（Nekobox 无需参与）

如果你**只是想从手机访问 PC 的 Open Notebook**：

1. 手机装 Tailscale App，登录同一账号（**账号不是 Nekobox 用的那个**）
2. 关闭 Nekobox
3. 打开 Tailscale VPN
4. 浏览器直接访问：
   - API：`http://100.108.217.19:8888/`
   - 前端：`http://laptop-62burom0.taile2bacf.ts.net:3000`
5. 流量经 Tailscale WireGuard 加密 → 直达 PC

**这是最简单、最稳定的方案。**

### 3.3 用 Nekobox 走 Tailscale 隧道 + 复用 PC 上 Clash Verge 出口

如果要让手机 app **先** 走 Tailscale 到 PC **再** 走 PC 本地的 Clash Verge 出去访问外网：

> 这才是 Nekobox 真正的用武之地（把 PC 当作一个加密跳板 + 代理出口）。

**步骤：**

1. **PC 端**：在 Clash Verge / verge-mihomo 配置里把外部控制端口**绑定到 0.0.0.0**（默认 127.0.0.1 外部不可达）。
   - 找到 `C:\Users\ZS\AppData\Roaming\verge-mihomo\config.yaml` 或 verge 设置
   - 修改 `mixed-port` 或 `external-controller` 监听 `0.0.0.0`
   - 重启 Clash Verge

2. **PC 端**：因为 Caddy 已经在跑 0.0.0.0:8888，可以**直接**让 Nekobox 把它当 HTTP 代理用：
   - 实际上**不需要** Caddy，Caddy 是为 HTTP 流量（浏览器）准备的
   - Nekobox 想要的是 **SOCKS5 出口**

3. **改造方案**：让 Caddy 同时暴露 SOCKS5 端口给 Nekobox
   - Caddy 不支持 SOCKS5，需额外加一个轻量 SOCKS5 桥（如 `microsocks`、`3proxy`、`gost`）
   - 推荐 `gost`（单文件，支持很多协议）

**用 gost 暴露 SOCKS5（推荐）：**

```powershell
# 下载 gost
$url = 'https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-windows-amd64.zip'
Invoke-WebRequest -Uri $url -OutFile 'E:\notebook\downloads\gost.zip' -UseBasicParsing
Expand-Archive -LiteralPath 'E:\notebook\downloads\gost.zip' `
  -DestinationPath 'E:\notebook\downloads\gost' -Force

# 启动 gost：在 0.0.0.0:1080 暴露 SOCKS5
Start-Process -FilePath 'E:\notebook\downloads\gost\gost-windows-amd64.exe' `
  -ArgumentList '-L','socks5://:1080' `
  -WindowStyle Hidden `
  -RedirectStandardOutput 'E:\notebook\gost.log' `
  -RedirectStandardError 'E:\notebook\gost.err.log'
```

**Nekobox 端配置：**

| 字段 | 值 |
| --- | --- |
| 服务器 | `100.108.217.19` |
| 端口 | `1080` |
| 协议 | `SOCKS5` |
| 加密 | `none`（Tailscale 已经加密） |
| 路由 | 走全局 |
| VPN 模式 | 打开（仅 Nekobox 的 VPN） |

**手机开 Nekobox 时必须先关 Tailscale VPN**（VPN slot 冲突）。

⚠️ 这种用法**不会**经过 PC 的 Clash Verge——Nekobox 走 SOCKS5 后到 PC，PC 上没人代理这台手机发起的请求。
要"经过 PC 上的 Clash Verge 出去"，需要：
- 把 Nekobox 的出站流量重定向到 `127.0.0.1:7897`（Clash Verge HTTP 端口）
- 在 PC 上用 `gost` 做链式代理：`<-socks5://:1080` → `forward=http://127.0.0.1:7897`

```powershell
# gost 链式代理：手机 SOCKS5 → gost → Clash Verge HTTP 出口
Start-Process -FilePath 'E:\notebook\downloads\gost\gost-windows-amd64.exe' `
  -ArgumentList '-L','socks5://:1080','-F','http://127.0.0.1:7897' `
  -WindowStyle Hidden `
  -RedirectStandardOutput 'E:\notebook\gost.log' `
  -RedirectStandardError 'E:\notebook\gost.err.log'
```

**Nekobox 配置**（同上面，但意义是手机流量 → Tailscale → PC → Clash Verge → 外网）。

### 3.4 不在方案 3.3 这条路上

如果你的真实需求是"手机上跑 Nekobox 同时访问 PC 的 Open Notebook"，请直接看 §3.2：
- **Nekobox 和 Tailscale 不能同时开 VPN**
- 所以要么：
  - ① 访问 Open Notebook 时只开 Tailscale（最稳）
  - ② 走 Cloudflare Tunnel 完全绕开 VPN（详见 `E:\notebook\scripts\PRODUCTION_GUIDE.md` B 节）
  - ③ 用 Cloudflare WARP（1.1.1.1 App）替代 Nekobox 走"另一条 VPN 通道"和 Tailscale 共存

## 4. 总结：用户怎么用

| 你的需求 | 推荐方案 |
| --- | --- |
| 手机浏览器访问 PC 的 Open Notebook | **方案 3.2**：只开 Tailscale，访问 `http://100.108.217.19:3000` 或 `http://100.108.217.19:8888/`（API） |
| 手机 app 通过 PC 的 Clash Verge 出口上网 | **方案 3.3**：关 Tailscale，开 Nekobox（SOCKS5→gost→Clash Verge） |
| 两个都要，且都要在手机端 | **方案 3.3 + §3.2 二选一使用**（因为 VPN slot 唯一） |
| 想完全绕开手机端 VPN slot 问题 | 用 **Cloudflare Tunnel** 把 Open Notebook 暴露到公网域名，详见 PRODUCTION_GUIDE.md |

## 5. 故障排查

| 症状 | 检查点 |
| --- | --- |
| 手机访问 `100.108.217.19:8888` 无响应 | ① 手机 Tailscale 是否登录同一账号 ② `Get-NetTCPConnection -LocalPort 8888` 看 PC 上是否还在监听 ③ PC 防火墙是否允许 8888 入站（家用网络一般自动放行 Tailscale 接口） |
| localhost:8888 健康，本地 0.0.0.0:8888 不通 | 防火墙入站规则 `New-NetFirewallRule -DisplayName "Caddy8888" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow` |
| Caddy 启动后立即退出 | 看 `E:\notebook\caddy-startup.err.log`，通常是 Caddyfile 语法问题 |
| 端口被占用 | `Get-NetTCPConnection -LocalPort 8888,8889` 看 OwningProcess |
