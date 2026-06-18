# 📱 手机访问 PC Open Notebook 完全指南

> 写给完全没折腾过网络的人 —— 按步骤照做就能用

---

## 写在前面

你现在有 3 个手机访问 PC 上 Open Notebook 的方法，按推荐度排序：

| 方法 | 难度 | 是否需要 Tailscale | 是否需要 Nekobox 配合 | 推荐场景 |
|------|------|-------------------|---------------------|----------|
| 方法 A：Caddy + Tailscale | ⭐ 最简单 | ✅ 必开 | ❌ 关掉 | 同 WiFi 或有 Tailscale 时 |
| 方法 B：Cloudflare Tunnel | ⭐⭐ 中等 | ❌ 不需要 | ✅ 可共存 | 在外面、没 WiFi |
| 方法 C：局域网直连 | ⭐ 最简单 | ❌ 不需要 | ❌ 关掉 | 手机和 PC 同一 WiFi |

> 💡 **一句话总结**：在家用 **C**，最快；出门用 **B**，免 Tailscale；想稳用 **A**。

---

## 🔑 你的密码

无论用哪个方法，手机访问 PC 上的 Open Notebook 都需要输入密码：

```
密码位置：E:\notebook\open-notebook\.env 文件
密码字段：OPEN_NOTEBOOK_PASSWORD=...
当前值：mobile-notebook-2026-secure-key-change-me
```

**手机第一次访问时会要求输入这个密码**。记不住的话存在手机密码管理器里（推荐 1Password / 微信收藏）。

> ⚠️ 这串带 `change-me` 后缀是因为默认值是临时占位用的。建议你抽空改成自己好记的串，改完保存文件、重启 API 服务（执行 `E:\notebook\scripts\start-api.bat`）即可生效。

---

## 方法 A：Tailscale + Caddy（推荐，最稳）

### 适用场景
- 手机和 PC 都在 Tailscale 网络里
- 或者想用最稳定的方式访问
- 4G / 公共 WiFi / 公司网都能用，不挑网络

### 前提条件
- ✅ PC 端 Tailscale 已登录（你的 PC 节点名：`laptop-62burom0`）
- ✅ 手机端 Tailscale App 已装并登录**同一个账号**
- ✅ 手机已关掉 Nekobox（VPN slot 冲突）

### 步骤

#### A.1 PC 端（已完成，你不用动）
- ✅ Tailscale 已登录，节点名 `laptop-62burom0`
- ✅ Caddy 已启动，监听 `0.0.0.0:8888`（API）和 `0.0.0.0:8889`（前端）
- ✅ PC 防火墙已放行 8888/8889 端口

#### A.2 手机端（你要做的）

1. **打开 Tailscale App**（应用商店搜 "Tailscale" 下载）
2. **关掉 Nekobox**（设置 → VPN → 关掉 Nekobox，避免 VPN slot 冲突）
3. **开 Tailscale VPN**（在 Tailscale App 里点一下开关）
4. **等 5 秒**，看到节点列表里 `laptop-62burom0` 显示**绿色**对勾
5. **打开手机浏览器**（Safari / Chrome 都行）
6. **在地址栏输入下面任一 URL**：
   - 用 IP 访问：`http://100.108.217.19:8889`
   - 用域名访问：`http://laptop-62burom0.taile2bacf.ts.net:8889`
7. **第一次会跳到登录页**，输入密码 `mobile-notebook-2026-secure-key-change-me`
8. **登录后**就能看到 Open Notebook 了 🎉

### 测试同步
- PC 端：浏览器访问 `http://localhost:3000`，新建一个笔记本
- 手机端：**下拉刷新**页面，应该能看到刚建的那个笔记本
- 手机端：在笔记本里加个 source，PC 端刷新应该能看到

### 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 手机 Tailscale 节点显示灰色 | 节点离线 | 让 PC 端重新登录 Tailscale |
| `laptop-62burom0` 找不到 | MagicDNS 没生效 | 用 IP `100.108.217.19` 访问 |
| 打开 8889 端口白屏 | 前端 dev server 还在跑 | 正常，等 3-5 秒让 React 加载 |
| 提示密码错误 | .env 密码没复制全 | 重新复制，注意末尾没有空格 |
| 手机能用 Nekobox 但 Tailscale 灰了 | VPN slot 冲突 | 关 Nekobox，重开 Tailscale |
| 提示 "无法连接" | Tailscale 没开 | 打开 Tailscale VPN 开关 |

---

## 方法 B：Cloudflare Tunnel（无需 Tailscale 和 Nekobox）

### 适用场景
- 在外面，没有 Tailscale
- 想和 Nekobox 共存（不抢 VPN slot）
- 临时分享给朋友看（**注意：临时域名是公开的**）
- 4G / 公共 WiFi / 公司网都能用

### 前提条件
- ✅ PC 端 cloudflared 已启动（已为你跑好）
- ✅ 当前临时域名已就绪

### 当前临时域名（PC 重启后会变）

```
Web 隧道（前端，推荐用这个）：https://sellers-view-thoughts-hundreds.trycloudflare.com
API 隧道（后端）：             https://eyed-springs-replied-paintings.trycloudflare.com
```

> 💡 一般只用 **Web 隧道**就够了，前端会自动调用 API 隧道。

### 步骤

#### B.1 PC 端（已完成）
- ✅ cloudflared Web 隧道已启动：`https://sellers-view-thoughts-hundreds.trycloudflare.com` → `http://localhost:3000`
- ✅ cloudflared API 隧道已启动：`https://eyed-springs-replied-paintings.trycloudflare.com` → `http://localhost:5055`
- ✅ 协议：QUIC，Cloudflare 自动 HTTPS 加密

#### B.2 手机端（你要做的）

1. **手机开浏览器**（任何网络都行：4G / WiFi / 公司网，不挑）
2. **访问 URL**：
   ```
   https://sellers-view-thoughts-hundreds.trycloudflare.com
   ```
3. **第一次会跳到登录页**，输入密码 `mobile-notebook-2026-secure-key-change-me`
4. **登录后**就能用了 🎉

### 优势
- ✅ 不占 VPN slot（Nekobox 可继续用）
- ✅ 不需要 Tailscale
- ✅ 4G 网络也能用
- ✅ Cloudflare 自动 HTTPS 加密
- ✅ 一个 URL 搞定，不用记端口

### 注意事项
- ⚠️ **临时域名每次重启 PC 会变**（除非改用 named tunnel）
- ⚠️ 临时域名是公开的，**不要在朋友圈/微博分享**（别人知道域名 + 密码就能访问）
- ⚠️ 出现 `Cloudflare 530 错误` = 后端不通（PC 的 API 服务没起或 cloudflared 掉了，按下面步骤重启）
- ⚠️ 出现 `Cloudflare 502/504 错误` = 后端服务挂了（看 API 日志）

### 如何重启 Cloudflare Tunnel

如果 Cloudflare Tunnel 不可用（530 / 502 / 打不开）：

1. **打开 PowerShell**（开始菜单搜 "PowerShell"，右键用管理员跑）
2. **跑下面这条命令**：
   ```powershell
   E:\notebook\scripts\start-cloudflare-tunnel.bat
   ```
3. **等 15 秒**，新临时域名会打印在终端里
4. **去 `.err` 日志里看新域名**（`E:\notebook\cloudflared-web.log.err`）
5. **手机用新域名访问**

> 💡 提示：脚本会同时重启 Web 和 API 两个隧道，新域名是 `https://<随机串>.trycloudflare.com` 格式。

---

## 方法 C：局域网直连（最简单）

### 适用场景
- 手机和 PC 同一个 WiFi
- 完全不依赖 Tailscale
- 想速度最快、配置最少

### 步骤

#### C.1 PC 端（已完成）
- ✅ PC 内网 IP：`192.168.5.22`
- ✅ Open Notebook 监听 `0.0.0.0:3000`
- ✅ 防火墙已放行 3000 端口

#### C.2 手机端（你要做的）

1. **连上和 PC 同一个 WiFi**（注意是同一个 WiFi，不是隔壁的）
2. **打开手机浏览器**
3. **在地址栏输入**：
   ```
   http://192.168.5.22:3000
   ```
4. **第一次会跳到登录页**，输入密码 `mobile-notebook-2026-secure-key-change-me`
5. **登录后**就能用了 🎉

### 优势
- 最简单（不用记复杂域名）
- 速度最快（局域网传输）
- 不需要任何额外 App
- 不需要 Tailscale

### 限制
- ⚠️ 手机和 PC 必须同 WiFi
- ⚠️ 离开 WiFi 就不能用
- ⚠️ 换 WiFi 后 PC 的内网 IP 可能变（要看路由器是否固定 IP）

### 如果 IP 变了

1. PC 端按 `Win + R`，输入 `cmd`，回车
2. 输入 `ipconfig`，回车
3. 找"无线局域网适配器"或"以太网适配器"下的 `IPv4 地址`，例如 `192.168.5.22`
4. 手机用新 IP 访问

---

## 🎯 推荐使用组合

### 🏠 日常使用（PC 和手机同 WiFi）
**用方法 C**（局域网直连）—— 速度最快，零折腾

### 🚶 在外面（手机用 4G 或其他 WiFi）
**用方法 B**（Cloudflare Tunnel）—— 不需要 Tailscale，浏览器直接打开

### 🔧 想深度使用 + 多设备稳定
**用方法 A**（Tailscale）—— 最稳定，但要装 App

---

## 📞 遇到问题

### 通用排查清单

| 现象 | 优先排查 |
|------|---------|
| 三个方法都打不开 | PC 上的 Open Notebook 是不是没启动？看 `E:\notebook\frontend-dev.log.err` 和 `E:\notebook\api-startup.log.err` |
| 登录页能打开但密码错误 | 重新复制 `.env` 里的密码（注意首尾空格） |
| 登录后白屏 / 卡死 | 浏览器换无痕模式试一下；或换个浏览器（Chrome / Safari） |
| 数据没同步 | 刷新页面（Ctrl+F5 强制刷新）；检查是不是连了不同账号的 Tailscale |

### 各方法专属排查

- **方法 A 失败**：
  1. 手机 Tailscale 节点是绿色吗？不是 → 重新登录
  2. PC 端 `tailscaled` 进程在跑吗？打开 PowerShell 跑 `Get-Process tailscaled`
  3. 防火墙放行 8889 端口了吗？参考 `E:\notebook\scripts\FIX_LAN_ACCESS.md`

- **方法 B 失败**：
  1. 跑 `E:\notebook\scripts\start-cloudflare-tunnel.bat` 重启
  2. 看新域名是不是变了（`E:\notebook\cloudflared-web.log.err` 第一行）
  3. PC 上 API 服务在 5055 端口吗？`netstat -ano | findstr 5055`

- **方法 C 失败**：
  1. 手机和 PC 在同一 WiFi 吗？（不是隔壁 WiFi、不是访客网络）
  2. PC 防火墙放行 3000 端口了吗？参考 `E:\notebook\scripts\FIX_LAN_ACCESS.md`
  3. PC 内网 IP 是 `192.168.5.22` 吗？用 `ipconfig` 确认

### 详细日志位置

| 日志 | 路径 |
|------|------|
| 前端日志 | `E:\notebook\frontend-dev.log.err` |
| API 日志 | `E:\notebook\api-startup.log.err` |
| SurrealDB 日志 | `E:\notebook\surreal-startup.log.err` |
| Caddy 日志 | `E:\notebook\caddy-startup.log.err` |
| Cloudflare Web 日志 | `E:\notebook\cloudflared-web.log.err` |
| Cloudflare API 日志 | `E:\notebook\cloudflared-api.log.err` |
| Tailscale 状态 | PowerShell 跑 `tailscale status`（需安装 Tailscale CLI） |

---

## 📋 速查表（保存这一段就够日常用了）

```
╔══════════════════════════════════════════════════════════╗
║  密码：mobile-notebook-2026-secure-key-change-me          ║
╠══════════════════════════════════════════════════════════╣
║  方法 A (Tailscale)：                                    ║
║    http://100.108.217.19:8889                            ║
║    http://laptop-62burom0.taile2bacf.ts.net:8889         ║
║    前提：手机开 Tailscale，关 Nekobox                     ║
╠══════════════════════════════════════════════════════════╣
║  方法 B (Cloudflare)：                                   ║
║    https://sellers-view-thoughts-hundreds.trycloudflare.com║
║    前提：任何网络都行                                    ║
║    注意：PC 重启后域名会变                               ║
╠══════════════════════════════════════════════════════════╣
║  方法 C (局域网直连)：                                   ║
║    http://192.168.5.22:3000                              ║
║    前提：手机和 PC 同一 WiFi                             ║
╠══════════════════════════════════════════════════════════╣
║  出问题先看日志，重启用：                                ║
║    E:\notebook\scripts\start-cloudflare-tunnel.bat       ║
╚══════════════════════════════════════════════════════════╝
```

---

## 🆘 终极救命一招

如果三个方法都打不开，**99% 是 PC 端服务挂了**。按顺序重启：

1. 打开 PowerShell（管理员）
2. 跑：
   ```powershell
   E:\notebook\scripts\start-all.bat
   ```
3. 等 30 秒，看终端输出有没有报错
4. 重启后再用上面速查表的 URL 试一次

如果还不行，**把日志文件发给懂技术的朋友**：
- `E:\notebook\frontend-dev.log.err`
- `E:\notebook\api-startup.log.err`
- `E:\notebook\cloudflared-web.log.err`

---

> 📝 文档版本：2026-06-17
> 适用：Open Notebook + Tailscale + Cloudflare Tunnel + Caddy
> 目标用户：完全没折腾过网络的人
