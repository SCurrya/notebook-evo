# Open Notebook 远程访问完整配置指南（Tailscale + Cloudflare）

> 本指南把 Tailscale（首选）和 Cloudflare Tunnel（备用）两条远程访问通道整合起来，
> 覆盖从"PC 端服务开机自启"到"手机端验证"的完整流程。配套详细文档：
> - `E:\notebook\scripts\setup-tailscale.md`（Tailscale 详细单点指南）
> - `E:\notebook\scripts\setup-cloudflare-tunnel.md`（Cloudflare 详细单点指南）
> - `E:\notebook\scripts\LAN_GUIDE.md`（局域网访问）
> - `E:\notebook\scripts\USER_GUIDE.md`（Open Notebook 使用说明）

---

## 0. 前置条件

| 项 | 状态 | 说明 |
| --- | --- | --- |
| Open Notebook 后端（5055） | 需保证运行 | `python` / `uvicorn` 进程监听 `0.0.0.0:5055`（**不要** `127.0.0.1`） |
| Open Notebook 前端（3000） | 需保证运行 | `next start` 监听 `0.0.0.0:3000` |
| PC 内网 IP | `192.168.5.22` | 仅在同一 Wi-Fi 下需要 |
| Tailscale Windows 客户端 | **已通过 MSI 静默安装** | 路径 `C:\Program Files\Tailscale\tailscale.exe`，版本 1.98.4，**服务已设为 Automatic（开机自启）** |
| Tailscale 账号 | **已登录** `scurry413a@` | Tailscale IP `100.108.217.19`，tailnet 域名 `laptop-62burom0.taile2bacf.ts.net` |
| cloudflared.exe | 已下载到 `E:\notebook\downloads\cloudflared.exe` | 备用通道才需要 |
| Android SDK | 已安装 | 仅打包 APK 时需要 |

> **Tailscale 域名构成**：`{机器名}.{tailnet-suffix}.ts.net`
> 例如本机：`laptop-62burom0.taile2bacf.ts.net`

---

## A. Tailscale 远程访问（首选方案）

### A.1 PC 端登录（已完成）

Tailscale 已通过 MSI 静默安装到 `C:\Program Files\Tailscale\`，并已登录账号 `scurry413a@`。

如果需要重新登录（例如换了账号）：

1. 找到系统托盘的 Tailscale 图标（蓝白色方块）
2. 右键 → `Log in`
3. 浏览器自动打开 https://login.tailscale.com
4. 用 Google / GitHub / 微软账号登录（首次需注册，免费）
5. 登录后回到 PC，Tailscale 自动连接

> **不要在自动化脚本里模拟登录**——Tailscale 登录是 OAuth 流程，必须用户手动完成。

### A.2 查询 PC 的 Tailscale 域名（已获取）

打开 PowerShell 执行：

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" status
```

本机当前输出：

```
100.108.217.19  laptop-62burom0  scurry413a@  windows  -
```

执行下面这条命令拿到 **完整 tailnet 域名**（包含 `.ts.net` 后缀）：

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" status --json | Select-String '"MagicDNSSuffix"'
```

本机结果：

```
"taile2bacf.ts.net"
```

**完整 Tailscale 域名 = `laptop-62burom0.taile2bacf.ts.net`**

### A.3 把域名配置到 `.env`

打开 `e:\notebook\open-notebook\.env`，找到 `TAILSCALE_DOMAIN=` 一行，填入域名（**不含端口和协议**）：

```ini
TAILSCALE_DOMAIN=laptop-62burom0.taile2bacf.ts.net
CLOUDFLARE_DOMAIN=
```

> `.env` 里这两行就是给前端 `api-discovery.ts` 用的占位符。
> 注意：当前 `.env` 的 `CORS_ORIGINS` 是 `http://...` 形式，
> Tailscale 走的是 `http://<域名>:5055`，CORS 默认同源放行（前端端口 3000 → 后端 5055 是跨端口，
> 浏览器会发 CORS 预检），如果手机端跨域失败，需要在 `CORS_ORIGINS` 里追加
> `http://laptop-62burom0.taile2bacf.ts.net:3000`。

### A.4 重启 Open Notebook 服务

让 API 域名发现模块读到新配置：

```powershell
# 后端：找到 open-notebook 的 python 进程并重启
Get-Process python -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowTitle -match 'open-notebook|uvicorn' } |
  Stop-Process -Force

# 或者用你平常的启动脚本重启
```

> 前端的 `NEXT_PUBLIC_TAILSCALE_DOMAIN` 在 Next.js 编译时被 bake-in，
> **修改 `.env` 之后需要 `npm run build` + `npm start` 才生效**（如果走 production 模式）。
> 走 `npm run dev` 则可以热重载。

### A.5 手机端安装 Tailscale（需用户操作）

1. 打开 Google Play（Android）或 App Store（iOS）
2. 搜索 "Tailscale" 安装（免费）
3. 打开 Tailscale App，用**同一个账号** `scurry413a@` 登录
4. 授予 VPN 权限
5. 手机会获得一个 `100.x.x.x` 的 Tailscale IP

### A.6 手机端测试

手机浏览器访问（替换成你的实际域名）：

```
http://laptop-62burom0.taile2bacf.ts.net:3000
```

应该能看到 Open Notebook 前端。API 也走 Tailscale 域名 + 5055 端口。

也可以直接用 Tailscale IP（不依赖 DNS）：

```
http://100.108.217.19:3000
http://100.108.217.19:5055/health
```

### A.7 故障排查

| 问题 | 解决 |
| --- | --- |
| Tailscale 显示 `disconnected` | 检查系统托盘图标，右键 `Reconnect` |
| 手机能登 Tailscale 但访问不到 PC | 确认 PC 和手机登录**同一账号**（看 tailscale 管理后台 https://login.tailscale.com/admin/machines） |
| 访问超慢 / 断断续续 | Tailscale NAT 穿透失败走 DERP 中继；本机 DERP 是 Tokyo（367ms），可以开启 "Allow Direct Connections" 优化 |
| 5055 端口被拒 | 确认后端监听 `0.0.0.0:5055`（**不是** `127.0.0.1`），用 `netstat -aon \| findstr :5055` 看 LocalAddress 列 |
| 前端看不到 Tailscale 域名 | 浏览器 DevTools → Network → 看请求 URL；如果还是 `localhost:5055` 说明 `NEXT_PUBLIC_TAILSCALE_DOMAIN` 没读到，需要重新 build 前端 |
| DNS health: "Access is denied" | 当前会话未以管理员身份跑 `tailscale up`；**不影响** 100.x IP 直连，路由和加密隧道都正常 |

### A.8 开机自启（已配置）

| 组件 | 启动方式 | 当前状态 |
| --- | --- | --- |
| Tailscale 服务 | Windows Service `Tailscale`，StartType = `Automatic` | ✅ 已启用 |
| Open Notebook 后端 | 需用任务计划程序 / NSSM / 自启脚本注册 | 需用户按需配置 |
| Open Notebook 前端 | 同上 | 需用户按需配置 |

**Tailscale 已自动开机自启**。如需验证：

```powershell
Get-Service Tailscale | Format-List Name, Status, StartType
```

应看到 `StartType : Automatic`、`Status : Running`。

> Tailscale MSI 安装时已自动注册为 Windows 服务并设为自动启动，不需要手动配置。

---

## B. Cloudflare Tunnel 备用外网通道

> 适合**没有 Tailscale 但需要公网访问**的场景（例如临时借给别人用、出国出差等）。
> 详细步骤见 `E:\notebook\scripts\setup-cloudflare-tunnel.md`。

### B.1 临时隧道（无需 Cloudflare 账号）

打开 PowerShell：

```powershell
E:\notebook\downloads\cloudflared.exe tunnel --url http://localhost:5055
```

会输出形如：

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://xxxx-xxxx.trycloudflare.com                                                       |
+--------------------------------------------------------------------------------------------+
```

把这个 `https://xxxx-xxxx.trycloudflare.com` 填入 `.env`：

```ini
CLOUDFLARE_DOMAIN=https://xxxx-xxxx.trycloudflare.com
```

> **注意 `.env` 字段格式**：必须带 `https://` 前缀，不带尾部斜杠。
> （和 `TAILSCALE_DOMAIN` 写法不同——后者**不要**带协议头，因为前端是 `http://` 拼端口 5055。）

### B.2 开机自启（固定域名 + 服务模式）

需要 Cloudflare 账号 + 一个域名（NS 改到 Cloudflare）。流程：

```powershell
# 1. 下载 NSSM（用于把任意 exe 注册为 Windows 服务）
Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'E:\notebook\downloads\nssm.zip'
Expand-Archive -Path 'E:\notebook\downloads\nssm.zip' -DestinationPath 'E:\notebook\downloads\nssm'

# 2. cloudflared 自己的 service install（推荐）
E:\notebook\downloads\cloudflared.exe service install
```

> 推荐用 `cloudflared service install`，它会自动建 Windows 服务 `Cloudflared`、开机自启。
> 服务模式下 `config.yml` 必须放在 `C:\Windows\System32\config\systemprofile\.cloudflared\config.yml`。
> 详细步骤见 `setup-cloudflare-tunnel.md` 第三节。

---

## C. 数据同步验证清单

完成 A/B 后逐项验证：

- [ ] PC 浏览器打开 `http://localhost:3000`，看到 Open Notebook
- [ ] 手机浏览器打开 Tailscale 域名 `http://laptop-62burom0.taile2bacf.ts.net:3000`，看到同一界面
- [ ] 手机浏览器打开 Tailscale IP `http://100.108.217.19:3000`，看到同一界面
- [ ] PC 端创建新笔记本 `test-sync`
- [ ] 手机端刷新，看到 `test-sync`
- [ ] 手机端尝试创建笔记本（如果 Tailscale 通了，可以写）
- [ ] PC 端刷新，看到手机创建的
- [ ] 关闭 Open Notebook 服务，手机端会进入"离线模式"（用本地 IndexedDB 缓存）
- [ ] 重新启动服务，手机端自动重连
- [ ] PC 重启 → Tailscale 服务自动拉起 → Open Notebook 启动后手机端继续可用

---

## D. 进阶：手机端 APK 安装

等 APK 打包完成（`E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk`）：

1. USB 连手机到 PC
2. 启用手机 USB 调试
3. PC 端执行：
   ```powershell
   adb install -r E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk
   ```
4. 手机应用列表出现 "Open Notebook"
5. 打开应用，**首次启动**会弹出"配置 API 域名"对话框，填入：
   ```
   Tailscale 域名: laptop-62burom0.taile2bacf.ts.net
   Cloudflare 域名: （留空，或填你 B.1 拿到的 https://xxxx.trycloudflare.com）
   ```
   应用会把域名存到 `localStorage`，之后 `api-discovery.ts` 会按
   `localhost → Tailscale → Cloudflare` 顺序自动选第一个能连通的端点。

> **不需要**每次启动都重新填域名（除非换账号或换 PC）。

---

## E. 安全注意事项

1. **Tailscale 通道**：默认 ACL 允许你账号下所有设备互通，已经有 Tailscale 账号认证，**比公网暴露安全得多**。
2. **Cloudflare 临时隧道**：域名公开可猜，**必须**在 `.env` 设置 `OPEN_NOTEBOOK_PASSWORD=...` 让后端开启 Bearer 鉴权（`e:\notebook\open-notebook\.env` 里已有默认值 `mobile-notebook-2026-secure-key-change-me`，**生产环境请修改**）。
3. **OPEN_NOTEBOOK_ENCRYPTION_KEY**（`.env`）：存 API 凭证加密用，**必须**改成 32 字符以上的随机串。
4. **Tailscale ACL 收紧**（可选）：参考 `setup-tailscale.md` 第五节，把 ACL 改成"只允许 `tag:phone` 访问 `tag:pc:5055`"。

---

## F. 关键路径速查

| 用途 | 路径 |
| --- | --- |
| Tailscale 可执行文件 | `C:\Program Files\Tailscale\tailscale.exe` |
| Tailscale 安装日志 | `E:\notebook\downloads\tailscale-install.log` |
| Tailscale MSI 安装包 | `E:\notebook\downloads\tailscale-setup-latest-amd64.msi` |
| cloudflared 可执行文件 | `E:\notebook\downloads\cloudflared.exe` |
| Open Notebook 配置 | `e:\notebook\open-notebook\.env` |
| 前端 API 发现 | `E:\notebook\open-notebook\frontend\src\lib\api-discovery.ts` |
| APK 输出 | `E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk` |

---

## G. 当前 PC Tailscale 实际状态（agent 已记录）

```
版本: 1.98.4 (tailscale commit 9e69045b291a7cb1edc714442d68e83b95d05e6b)
服务: Tailscale  Running  Automatic
账号: scurry413a@  (已登录)
Tailscale IPv4: 100.108.217.19
Tailscale IPv6: fd7a:115c:a1e0::c401:d9a9
节点名: laptop-62burom0
完整域名: laptop-62burom0.taile2bacf.ts.net
DERP: Tokyo (最近，367ms)
DNS 状态: "Access is denied"（非阻塞，仅 MagicDNS 后缀未设，路由和隧道均正常）
```

> DNS 状态的"Access is denied"是因为 agent 当前会话未以管理员身份跑 `tailscale up`，
> 不会影响 100.x IP 直连和加密隧道。**用户无需处理**。
> 如需消除这个警告，可以右键托盘 → `Reconnect`（自动以管理员身份重置 DNS 设置）。
