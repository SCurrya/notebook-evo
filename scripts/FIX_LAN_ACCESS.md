# 修复手机无法访问 http://192.168.5.22:3000

诊断时间：2026-06-17  
诊断人：Trae 自动诊断

---

## 一、诊断结果（粘贴步骤 1-4 的真实输出）

### 步骤 1：服务监听状态

```
Get-NetTCPConnection -LocalPort 3000
LocalAddress : 0.0.0.0
LocalPort    : 3000
State        : Listen
OwningProcess: 9580

Get-NetTCPConnection -LocalPort 5055（首次查询）
LocalAddress : 0.0.0.0
LocalPort    : 5055
State        : Listen
OwningProcess: 34652

（最新查询时 5055 已不再监听 — API 进程已退出）
```

✅ 3000 绑定 `0.0.0.0`（不是 127.0.0.1），服务监听到位  
⚠️ 5055 在诊断过程中已停止 — API 服务挂了

### 步骤 2：进程详情

```
PID 9580 (node.exe)
CommandLine  : E:\nodejs\node.exe E:\notebook\open-notebook\frontend\node_modules\next\dist\server\lib\start-server.js
ParentProcessId: 2660
Name         : node.exe
```

✅ 这是 Next.js 前端进程，启动方式正确  
⚠️ 5055 进程 PID 34652 已退出

### 步骤 3：防火墙规则

```
Get-NetFirewallRule | Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' }
匹配 LocalPort=3000 或 5055 的规则： 0 条

总入站规则数: 521
Get-NetFirewallProfile:
  Name  Enabled DefaultInboundAction DefaultOutboundAction
  Domain  True   NotConfigured         NotConfigured
  Private True   NotConfigured         NotConfigured
  Public  True   NotConfigured         NotConfigured
```

🚨 **没有任何针对 3000/5055 的入站 Allow 规则**  
Windows 默认入站行为是 Block，所以从手机流入的连接被静默丢弃

### 步骤 4：本机访问测试

```
Test 192.168.5.22:3000 (LAN IP)
  -> HTTP 500 内部服务器错误（能连上，但 SSR 报错）
Test 127.0.0.1:3000 (loopback)
  -> HTTP 500 内部服务器错误
Test-NetConnection 192.168.5.22 -Port 3000
  -> TcpTestSucceeded: True （TCP 握手成功）
Test 192.168.5.22:5055 (LAN IP)
  -> 无法连接到远程服务器
Test-NetConnection 192.168.5.22 -Port 5055
  -> TcpTestSucceeded: False（端口未监听）
```

| 地址 | 端口 | 结果 | 备注 |
|---|---|---|---|
| 192.168.5.22 | 3000 | HTTP 500 | 本机能连，有应用层错误 |
| 127.0.0.1 | 3000 | HTTP 500 | 本机能连，有应用层错误 |
| 192.168.5.22 | 5055 | 无法连接 | API 进程已停止 |
| localhost | 5055 | 无法连接 | 同上 |
| `[::1]` (IPv6) | 3000 | 无法连接 | 服务只绑 IPv4 |

---

## 二、问题根因（情况 C：防火墙拦截 + 附加问题）

### 主因：情况 C — 防火墙未放行 3000/5055

- PC 的 Windows 防火墙默认入站行为是 Block
- 没有任何针对 3000/5055 的入站 Allow 规则
- **本机访问 192.168.5.22:3000 之所以能拿到 500 错误**（而不是超时），是因为 PowerShell 的 `Test-NetConnection` / `Invoke-WebRequest` 走的是 loopback 优化路径，部分绕过了入站防火墙
- **手机从 WLAN 真实流入** → 没有放行规则 → 被默认规则拦截 → 手机浏览器显示"网页无法访问"（连接超时/被重置）

### 附加问题 1：API 服务（5055）当前未运行

- 最初查询时端口在监听（PID 34652），但后续查询时已不在
- 进程 `Get-Process -Id 34652` 返回空 → API 进程已退出
- 两个 `python.exe` 进程（PID 15308、38004）正在跑但都没监听 5055 — 可能是别的 Python 任务，不是这个项目的 API

### 附加问题 2：3000 端口 SSR 返回 500

- 192.168.5.22:3000 和 127.0.0.1:3000 都返回 500
- 服务能响应，但服务端渲染（SSR）时报错
- 即使防火墙放行、手机能连上，也会看到 500 错误页
- 需要查看 `e:\notebook\frontend.log` 或 Next.js 终端的错误堆栈

---

## 三、修复步骤

### 修复 1（核心）：放行 3000/5055 端口入站

⚠️ **请用户自己在 PowerShell（管理员）中执行下面命令，不要让 AI 自动跑**：

```powershell
# 放行前端 3000
New-NetFirewallRule -DisplayName "Open Notebook Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -Profile Private,Domain

# 放行 API 5055
New-NetFirewallRule -DisplayName "Open Notebook API" -Direction Inbound -LocalPort 5055 -Protocol TCP -Action Allow -Profile Private,Domain
```

如果命令报错 "MSFT_NetFirewallRule: ... 拒绝访问"，请：
1. 用"以管理员身份运行"打开 PowerShell
2. 或先执行 `Set-NetFirewallProfile -Profile Private,Domain -Enabled True`

### 修复 2：重启 API 服务（5055）

定位启动脚本/命令，然后重启。常见做法：

```powershell
# 查看项目根是否有启动脚本
Get-Content E:\notebook\start-open-notebook.bat

# 通常是：
cd E:\notebook\open-notebook
python run_api.py
# 或者：
uvicorn api.main:app --host 0.0.0.0 --port 5055
```

> 任务约束：不替用户执行重启。**只输出命令**，让用户决定。

### 修复 3（可选）：排查 3000 端口 500 错误

```powershell
# 查看最近的 Next.js 错误日志
Get-Content E:\notebook\frontend.log -Tail 100

# 或直接看控制台（PID 9580 启动时的那个终端）
Get-CimInstance Win32_Process -Filter "ProcessId = 9580" | Select-Object CommandLine
```

常见的 Next.js 500 原因：
- 数据库连接失败（SurrealDB 没起来）
- 缺少环境变量
- TypeScript 编译错误

### 修复 4（验证）：手机访问

手机连同一 WiFi（必须是 192.168.5.x 同一网段），浏览器打开：

- `http://192.168.5.22:3000`
- `http://192.168.5.22:5055/health`（应该返回 `{"status":"ok"}` 或类似 JSON）

如果手机能进 3000 但还是 500，**说明防火墙已经放行**，接下来排查应用层 500。

---

## 四、为什么本机测试能连、手机却不行？

这是 Windows 防火墙的常见迷惑行为：

| 测试方式 | 走的路径 | 是否过入站防火墙 |
|---|---|---|
| 本机 `Invoke-WebRequest http://127.0.0.1:3000` | loopback | ❌ 不走 |
| 本机 `Invoke-WebRequest http://192.168.5.22:3000` | 经本地协议栈转 loopback | ❌ 通常绕过 |
| 本机 `Test-NetConnection ... -Port 3000` | loopback | ❌ 不走 |
| 手机浏览器 `http://192.168.5.22:3000` | WLAN → 网卡 → 入站栈 | ✅ 走，**被默认 Block** |

所以**本机能访问 ≠ 手机能访问**。本机走 loopback 永远不受入站防火墙限制。

---

## 五、检查清单（按顺序）

- [ ] PC 和手机连同一 WiFi（手机查看 IP 应是 192.168.5.x）
- [ ] 用管理员 PowerShell 执行 2 条 `New-NetFirewallRule` 放行 3000、5055
- [ ] 重启 API 服务（python run_api.py 或对应命令）
- [ ] 手机浏览器访问 `http://192.168.5.22:3000`
- [ ] 如果还是 500，看 `frontend.log` 找应用层错误
- [ ] 手机访问 `http://192.168.5.22:5055/health` 验证 API 也通

---

## 六、相关文件路径

- 项目根：`E:\notebook\open-notebook\`
- 前端 package.json：`E:\notebook\open-notebook\frontend\package.json`
- API 入口：`E:\notebook\open-notebook\api\main.py`
- 启动脚本：`E:\notebook\start-open-notebook.bat`
- 前端日志：`E:\notebook\frontend.log`
- API 日志：`E:\notebook\api-err.log` / `E:\notebook\api-out.log`
- 已有 LAN 指南：`E:\notebook\scripts\LAN_GUIDE.md`（里面的防火墙命令和本文档一致）
