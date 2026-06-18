# Tailscale 与系统代理（VPN/代理软件）的冲突问题及解决方案

> 适用场景：用户用 Tailscale 访问 PC 上的 Open Notebook，同时手机开着代理软件（Clash / V2RayN / Shadowrocket / Netch 等），发现两者不能同时工作。本文档解释原因并给出可落地的 5 个方案。

---

## 一、为什么会冲突（核心原理）

### Android 系统的 VPN 槽位是互斥的

Android 系统（包括 iOS、macOS 的旧版本）只允许 **一个 VPN 应用** 占用系统的 VPN 通道（业内称为 "VPN slot"）。这不是 Tailscale 的 bug，而是操作系统层面的安全设计：

- Tailscale 在 Android 上**必须**以 VPN 模式运行（因为它底层用 WireGuard，没有 VPN 权限就拿不到虚拟网卡）
- Clash / V2RayN / Shadowrocket 在 Android 上**也**必须以 VPN 模式运行（同样的原因）
- 两者抢同一个 VPN slot，**后启动的会挤掉前一个**

所以你看到的现象是：开了 Tailscale VPN 后，代理软件就退出了；反之亦然。

### 为什么"分应用 VPN"也救不了

Android 8+ 支持 per-app VPN（让某个 VPN 只对指定应用生效），但 Tailscale 官方客户端**目前没有提供"分应用 VPN"开关**——它对所有应用都生效。Tailscale 团队虽然在路线图上提过，但截至 2025 年仍未在 Android 客户端正式发布。

> Windows / Linux 不存在此问题。Windows 允许多个 VPN 客户端共存，Tailscale 与 Clash TUN 模式可以同时跑。

---

## 二、5 个方案对比

| 方案 | 操作难度 | 代理保留 | Tailscale 保留 | 推荐度 |
|------|---------|---------|---------------|--------|
| **A. 手动切换** | ⭐ | 需要切换 | 需要切换 | ⭐⭐⭐ |
| **B. PC 端加 Tailscale 域名白名单** | ⭐⭐ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **C. 用 ZeroTier 替代 Tailscale** | ⭐⭐⭐ | ✅ | ✅（换 ZeroTier） | ⭐⭐⭐ |
| **D. Tailscale Subnet Router** | ⭐⭐⭐ | ✅ | ✅ | ⭐⭐⭐ |
| **E. frp 暴露到公网 VPS** | ⭐⭐ | ✅ | ❌ 换 frp | ⭐⭐⭐⭐ |

---

## 三、方案 B 详细步骤（⭐ 最推荐）

### 原理

- Tailscale 分配的 IP 是 `100.64.0.0/10` 这个私有地址段
- Clash / V2RayN 默认配置里**对私有 IP 是 DIRECT 规则**（即不走代理）
- 关键问题：100.x 流量默认走 **Tailscale VPN 通道**（抓系统 VPN slot），而代理软件也想用 VPN slot → 冲突
- 解法：让 Tailscale 走**应用层 DNS / 路由**，不要占系统 VPN slot

### 步骤 1：手机上关闭 Tailscale 的"使用 VPN 模式"

在 Tailscale Android 应用里：

1. 右上角菜单 → `Settings` → `Connection`
2. 关闭 **`Use Tailscale subnet routes`**（如果只用了 100.x 内网访问）
3. 关闭 **`Run as exit node`**（不要让 Tailscale 接管全局流量）

> 这样 Tailscale 仍然在线、仍然能 ping 通 PC，但不会独占 VPN slot。

### 步骤 2：手机用 Tailscale 的应用层访问

- 浏览器输入 PC 的 Tailscale IP（`http://100.64.x.x:5055`）即可直连
- Tailscale 走的是应用层 socket，不占系统 VPN slot

### 步骤 3：Clash 规则白名单（确保 100.x 不走代理）

Clash 配置文件（`config.yaml`）的 `rules` 部分加上：

```yaml
rules:
  # Tailscale 私有 IP 走 DIRECT（不走代理）
  - IP-CIDR,100.64.0.0/10,DIRECT,no-resolve
  # 局域网
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  # 其它规则...
```

### 步骤 4：V2RayN 路由规则

V2RayN 的 `routing.json`：

```json
{
  "domain": ["*.ts.net"],
  "ip": ["100.64.0.0/10"],
  "outboundTag": "direct"
}
```

### 步骤 5：PC 端的 Clash / V2RayN 也加同样规则

PC 上如果也跑代理（推荐），同样在配置里加 Tailscale 域名/IP 的 DIRECT 规则，否则 PC 端访问 Tailscale 协调服务器会绕一圈。

---

## 四、方案 A 详细步骤（最简单）

适合：用户**只是偶尔**用 Tailscale 访问 PC，平时 90% 时间在用代理刷外网。

### 步骤

1. **Tailscale 改为按需连接**：
   - 打开 Tailscale 应用 → 右上角 `⋮` → `Settings` → 关掉 `Always on`
   - Android 12+ 系统设置：`设置 → 网络和互联网 → VPN → Tailscale → 设为"按需"`（不要选"始终开启"）
2. **访问 Open Notebook** 时：手动打开 Tailscale 连接，访问完再关
3. **访问外网** 时：关 Tailscale，开代理软件

### 缺点

- 每次都要手动切换，比较烦
- 后台可能会被系统杀进程，需要把 Tailscale 加电池白名单

---

## 五、方案 E 详细步骤（适合有 VPS 的用户）

完全不用 Tailscale，**PC 通过 frp 暴露到公网**，手机直接用公网 IP 访问。

### 步骤 1：准备一台便宜 VPS

- 推荐：Vultr / RackNerd / 搬瓦工，$5/月起
- 系统：Ubuntu 22.04
- 需要**公网 IPv4**（重要）

### 步骤 2：VPS 上安装 frps（服务端）

```bash
wget https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz
tar xzf frp_0.61.1_linux_amd64.tar.gz
cd frp_0.61.1_linux_amd64
./frps -c frps.ini
```

`frps.ini`：

```ini
[common]
bind_port = 7000
token = 改成复杂密码
```

> 把 frps 配成 systemd 服务，开机自启（略，可参考 frp 官方文档）。

### 步骤 3：PC 上安装 frpc（客户端）

Windows 下载：https://github.com/fatedier/frp/releases

`frpc.ini`：

```ini
[common]
server_addr = VPS_IP
server_port = 7000
token = 改成复杂密码

[open-notebook-api]
type = tcp
local_ip = 127.0.0.1
local_port = 5055
remote_port = 6000
```

跑起来：

```powershell
.\frpc.exe -c frpc.ini
```

### 步骤 4：手机访问

浏览器输入 `http://VPS_IP:6000/...`，完全不走 VPN slot。

### 配套

- VPS 上**同时**跑一个代理服务（如 xray / hysteria2）和 frp，互不冲突
- 手机上用代理软件连 VPS 代理 → VPS 反代回 PC 的 frp 端口 → 访问 Open Notebook

---

## 六、其他平台提示

| 平台 | 冲突情况 | 备注 |
|------|---------|------|
| **Windows** | ❌ 无冲突 | Windows 允许多个 VPN，Tailscale + Clash TUN 可同时跑 |
| **macOS** | ⚠️ 部分冲突 | 可在 Tailscale 设置里 "Exclude from VPN" 排除某些应用 |
| **iOS** | ✅ 同样冲突 | iOS 也只允许一个 VPN，方案 A/B 同样适用 |
| **Linux** | ❌ 无冲突 | WireGuard 走 netns，不冲突 |

---

## 七、我的建议

针对**当前用户**（已经用代理软件 + Tailscale）的优先级：

1. **首选方案 B**：不动现有架构，加几条 Clash 规则就能共存。一劳永逸。
2. **临时方案 A**：如果只是临时用 Tailscale 调试一两次，手动切换最快。
3. **长期方案 E**：如果将来 Tailscale 用得越来越频繁，建议租个 VPS 走 frp，不再依赖 VPN slot。

---

## 八、快速决策树

```
Q1: 你用 Tailscale 访问 PC 的频率是？
   ├─ 每天都要用 ────────────→ 选 B（加 Clash 规则）
   ├─ 每周用一两次 ──────────→ 选 A（手动切换）
   └─ 几乎不用 / 想长期方案 ──→ 选 E（frp + VPS）

Q2: 你愿意花钱租 VPS 吗？
   ├─ 愿意 + 想彻底解决 ──→ 选 E
   └─ 不愿意 / 不想折腾 ──→ 选 B

Q3: 你是 PC / macOS 用户吗？
   ├─ 是 Windows ──→ 无此问题，无需解决
   ├─ 是 macOS ──→ Tailscale 设置里 Exclude 代理应用
   └─ 是 Android/iOS ──→ 回到 Q1
```

---

## 九、相关文档

- `setup-tailscale.md`：Tailscale 安装配置指南
- `setup-cloudflare-tunnel.md`：Cloudflare Tunnel 公网暴露方案（也属于方案 E 的替代）
- `install-tailscale.md`：Tailscale 快速安装脚本
