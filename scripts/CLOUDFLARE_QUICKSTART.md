# Cloudflare Tunnel 临时公网访问 - 快速指南

> 目标：让手机（Android / iOS）无需任何 VPN 即可访问家/公司 PC 上的 Open Notebook。
> 完全绕开 Tailscale + Nekobox 冲突。
> 当前使用 **http2 协议**（绕开 Mihomo 对 QUIC/UDP 的拦截），Web 隧道指向 **Caddy 8889 统一入口**。

---

## 1. 临时域名（本次会话）

| 用途 | 临时域名 | 后端 | 状态 |
| --- | --- | --- | --- |
| **API**（FastAPI :5055） | `https://sellers-view-thoughts-hundreds.trycloudflare.com` | Caddy/直接 | ✅ 已注册（http2） |
| **Web**（Caddy :8889 统一入口） | `https://eyed-springs-replied-paintings.trycloudflare.com` | Caddy 8889 | ✅ 已注册（http2） |

> ⚠️ 注意：每次重启 `cloudflared`，trycloudflare.com 都会分配**新的随机域名**。需要把新域名同步给手机 app。

> 💡 **关键变化（2026-06-17）**：
> 1. 协议从 QUIC 切到 **http2**（解决 Mihomo 代理拦截 QUIC/UDP 的 530 错误）
> 2. Web 隧道从 Next.js :3000 切到 **Caddy :8889**（Caddy 内部 `/api/*` 反代到 :5055，手机**一个 URL** 即可同时访问前端 + API）

---

## 2. 手机访问步骤（无需任何 VPN）

### Android（Capacitor App）

1. 打开手机上的 **Open Notebook** app
2. 进入 **Settings → API Endpoint**
3. 填入（推荐用 **Web 域名**，Caddy 内部反代 API）：
   ```
   https://eyed-springs-replied-paintings.trycloudflare.com
   ```
   或直接用 API 域名：
   ```
   https://sellers-view-thoughts-hundreds.trycloudflare.com
   ```
4. 密码（Bearer Token）填 `open-notebook/.env` 里的 `OPEN_NOTEBOOK_PASSWORD`（即 `mobile-notebook-2026-secure-key-change-me`）
5. 保存 → 重启 app → 即可使用

### iOS Safari / 任意浏览器

直接打开（推荐 Web 域名）：
- 前端（含 API 反代）：<https://eyed-springs-replied-paintings.trycloudflare.com>
- API 健康检查：<https://sellers-view-thoughts-hundreds.trycloudflare.com/health>

### 关键：完全不需要 VPN

- **Nekobox / Clash / 任何代理都不用开**
- 走的是 Cloudflare 全球边缘节点，国内/国外都通
- 临时域名是公开的，理论上任何人知道 URL 都能访问 → 因此**强烈建议修改默认密码**（见第 4 节）

---

## 3. 工作原理

```
[手机 App] ──HTTPS──> [Cloudflare Edge] ──HTTP/2 (TCP 443)──> [cloudflared.exe on PC] ──HTTP──> [Caddy :8889 / FastAPI :5055]
                       (trycloudflare.com)                       (后台常驻进程)                        (Open Notebook)
```

- `cloudflared.exe` 在 PC 上跑两个进程（PID 见 `cloudflared-api.log.err` / `cloudflared-web.log.err`）
- 反向隧道：Cloudflare 主动连出，**无需 PC 公网 IP，无需端口转发**
- 协议：**HTTP/2 over TCP 443**（不依赖 QUIC/UDP，能穿透企业代理/Mihomo）
- Web 隧道 → Caddy :8889（Caddy 内部把 `/api/*` 反代到 FastAPI :5055，静态文件直接服务）

### 三个进程协作

```
手机 ──> Cloudflare Edge ──HTTP/2──> cloudflared-web ──> Caddy :8889 ──┬──> 静态文件 (Next.js build)
                                                                       └──> /api/* ──> FastAPI :5055
手机 ──> Cloudflare Edge ──HTTP/2──> cloudflared-api ──> FastAPI :5055 (直连备用)
```

---

## 4. 安全性说明

| 风险 | 缓解措施 |
| --- | --- |
| 临时域名是公开的（拿到链接就能访问） | ✅ 已开启 Bearer Token 鉴权（`OPEN_NOTEBOOK_PASSWORD`） |
| 密码太弱被爆破 | ⚠️ **建议立即改密码**：`open-notebook/.env` 里的 `OPEN_NOTEBOOK_PASSWORD=...` → 改成长随机串 |
| 日志泄露 URL | ✅ 临时域名仅在 `.err` 日志里；用完即关 |
| 隧道长时间挂 | ⚠️ 临时隧道不保证 SLA；用完手动关闭（见第 5 节） |

### 修改默认密码

编辑 `E:\notebook\open-notebook\.env`：

```bash
OPEN_NOTEBOOK_PASSWORD=改成你自己的强密码-32位以上
```

然后重启 API：

```powershell
# 在 open-notebook 目录下
uvicorn api.main:app --host 0.0.0.0 --port 5055
```

---

## 5. 关闭命令

### 方法 A：一键关闭所有 cloudflared 进程

```powershell
Get-Process cloudflared | Stop-Process -Force
```

### 方法 B：按 PID 关闭

```powershell
# 查看 PID
Get-Process cloudflared

# 关闭指定 PID
Stop-Process -Id <PID> -Force
```

### 方法 C：任务管理器

Ctrl+Shift+Esc → 详细信息 → 找 `cloudflared.exe` → 右键结束任务

---

## 6. 重启 / 重新获取新域名

```powershell
# 1. 关闭旧隧道
Get-Process cloudflared | Stop-Process -Force

# 2. 重新启动（域名会变！必须用 --protocol http2）
& 'E:\notebook\downloads\cloudflared.exe' tunnel --url http://localhost:5055 --no-autoupdate --protocol http2
& 'E:\notebook\downloads\cloudflared.exe' tunnel --url http://localhost:8889 --no-autoupdate --protocol http2
```

或者双击 `E:\notebook\scripts\start-cloudflare-tunnel.bat`，等待 15 秒后日志里会自动打印新域名。

---

## 7. 文件清单

| 路径 | 用途 |
| --- | --- |
| `E:\notebook\downloads\cloudflared.exe` | Cloudflare Tunnel 客户端（51.66 MB） |
| `E:\notebook\cloudflared-api.log.err` | API 隧道日志（最新一次启动） |
| `E:\notebook\cloudflared-web.log.err` | Web 隧道日志（最新一次启动） |
| `E:\notebook\scripts\start-cloudflare-tunnel.bat` | 一键启动脚本（已带 `--protocol http2`） |
| `E:\notebook\scripts\CLOUDFLARE_QUICKSTART.md` | 本文档 |
| `E:\notebook\open-notebook\.env` | 含 `CLOUDFLARE_DOMAIN` 和 `OPEN_NOTEBOOK_PASSWORD` |

---

## 8. 故障排查

| 症状 | 解决 |
| --- | --- |
| 手机连不上 API | ① 域名是否复制完整（带 `https://`）② `OPEN_NOTEBOOK_PASSWORD` 是否和手机一致 ③ PC 上 `curl http://localhost:5055/health` 是否通 |
| 530 错误（QUIC 超时） | ✅ 已修复：改用 `--protocol http2`（TCP 443），所有 cloudflared 命令必须带这个参数 |
| 域名变成 `https://0.0.0.0:5055` 之类 | 重新跑启动脚本，日志会刷新 |
| `cloudflared.exe` 启动后立即退出 | 必须带 `--protocol http2` 参数（QUIC 协议被 Mihomo 拦截） |
| 手机浏览器提示"连接不安全" | 不会发生——Cloudflare 颁发的是正式证书 |
| Mihomo 仍在 hijack 本地 DNS | 这是预期行为——本机 `curl https://*.trycloudflare.com` 会失败（TUN 拦截），但**外部客户端（手机）正常** |

---

## 9. 与 Tailscale 方案的对比

| 维度 | Tailscale + Nekobox | Cloudflare 临时隧道（**当前方案**） |
| --- | --- | --- |
| 手机安装 | Tailscale App + Nekobox 配置文件 | **无需任何 App**（用浏览器/Capacitor app 直连） |
| Nekobox 占用 slot | 占 1 个代理 slot | 0 |
| 国内直连 | ❌ 需要 Nekobox 中转 | ✅ 直连 Cloudflare 节点 |
| 鉴权 | Tailscale 账号 | Bearer Token（`.env`） |
| 域名稳定性 | 稳定（`.ts.net`） | 每次重启变 |
| 协议 | 取决于 Tailscale | **HTTP/2 (TCP 443)**，绕开 QUIC 拦截 |
| 适用场景 | 长期部署 | 临时分享 / 调试 / 跨网络访问 |

---

*最后更新：2026-06-17 21:50 (Asia/Shanghai) — 协议升级到 http2，Web 入口改为 Caddy :8889*
