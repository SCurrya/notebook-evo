# 手机 / 电脑 双端访问指南

本项目支持通过 Tailscale（内网穿透 VPN）实现手机与电脑访问同一份知识库。
手机端使用 Capacitor 构建的 Android APK 或直接浏览器访问。

## 架构

```
┌─────────────┐     Tailscale 加密隧道      ┌──────────────────┐
│  手机 (APK) │ ───────────────────────────► │  电脑 (服务端)    │
│  或浏览器   │   tailscale-ip:8502          │  SurrealDB + API  │
└─────────────┘                              │  + Web UI         │
                                             └──────────────────┘
```

原理：Tailscale 把手机和电脑加入同一个虚拟局域网（ZeroTier 类 Mesh VPN），
手机通过 Tailscale 分配的 IP 直连电脑上的服务，无需公网端口映射。

## 前提条件

- Windows 电脑：安装 [Tailscale](https://tailscale.com/download)
- Android 手机：安装 [Tailscale](https://play.google.com/store/apps/details?id=com.tailscale.ipn) + 本项目 APK
- 手机与电脑登录**同一个 Tailscale 账号**

## 步骤

### 1. 电脑端

```powershell
# 安装并登录 Tailscale 后，获取 Tailscale IP
tailscale ip -4
# 例如输出: 100.64.0.5
```

编辑 `.env`，把 `TAILSCALE_DOMAIN` 设为该 IP：

```env
TAILSCALE_DOMAIN=100.64.0.5
```

### 2. 启动服务

```powershell
# 启动 SurrealDB + API（Tailscale 只穿透 API 和 Web UI）
.\surreal.exe start --log info --user root --pass root --bind 0.0.0.0:8000 rocksdb:./surreal_data/db
$env:API_RELOAD="false"
.\.venv\Scripts\python.exe run_api.py
```

注意：SurrealDB 需要绑定 `0.0.0.0`（默认 `127.0.0.1` 手机访问不到）。

### 3. 手机端

1. 打开 Tailscale 应用，确认已连接（显示电脑的 Tailscale IP）
2. 浏览器访问 `http://<电脑TailscaleIP>:8502` 或打开 APK
3. 在 APK 设置里把 API URL 设为 `http://<电脑TailscaleIP>:5055`

### 4. 防火墙

Windows 防火墙需放行 8000/8502/5055 端口的入站连接：

```powershell
New-NetFirewallRule -DisplayName "Notebook-Evo API" -Direction Inbound -Protocol TCP -LocalPort 5055 -Action Allow
New-NetFirewallRule -DisplayName "Notebook-Evo UI" -Direction Inbound -Protocol TCP -LocalPort 8502 -Action Allow
```

## 安全说明

- 所有流量经 Tailscale 端到端加密，不暴露公网
- 只有加入你 Tailscale 网络的设备能访问
- 推荐在 API 设置中开启密码认证（Settings → 安全）
- 如需公网访问（不用 Tailscale），可用 Cloudflare Tunnel（见 `.env` 的 `CLOUDFLARE_DOMAIN`）

## 备选：公网域名（Cloudflare Tunnel）

```powershell
# 安装 cloudflared 后
cloudflared tunnel --url http://127.0.0.1:8502
# 得到 https://xxx.trycloudflare.com 临时域名
```

然后在 `.env` 设置 `CLOUDFLARE_DOMAIN` 并用该域名访问，无需手机装 Tailscale。
