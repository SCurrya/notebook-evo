# Nekobox + Tailscale 共存方案深度调研

> 调研时间：2026-06-17
> 调研者：Trae 深度调研模式（WebSearch + WebFetch + 本地环境实测）
> 关联文档：`TAILSCALE_PROXY_CONFLICT.md`（已有 5 方案对比）、`FIX_LAN_ACCESS.md`（PC 端防火墙）
> 本文档定位：**对那 5 个方案的逐条证据补强 + 给出"实测可行"的 3 个推荐**

---

## TL;DR（最简答案）

- **推荐方案：方案 3（PC 开 Mihomo 给手机当 SOCKS/HTTP 代理）+ Tailscale Android VPN 各管各的**
- **前提条件**：PC 上必须开 `allow-lan: true`（目前是 `false`），并放行 Windows 防火墙
- **预计耗时**：5 分钟（核心是改 `config.yaml` 一行 + Clash Verge 重启内核）
- **为什么不选其它**：
  - 方案 1（Nekobox WireGuard 节点塞 Tailscale）：理论上可行但 Nekobox 不支持导入 Tailscale 私钥
  - 方案 2（手机上 SOCKS5 中转）：Tailscale Android 没有 userspace 模式，要 root 才能跑
  - 方案 4（软路由 Subnet Router）：用户 PC 就是软路由角色

---

## 问题 1：NekoBox 分应用 VPN 支持情况

### 结论：⚠️ 仅有"反向分应用"——Nekobox 自己可以设置"哪些 App 绕过 Nekobox 的 VPN"，但 **Nekobox 仍然占着 VPN slot**

### 证据来源

**Diana-Cl 社区 Wiki（针对 NekoBox 的中文/英文权威文档）** 明确列出 `Allow apps to bypass VPN` 章节：
- 链接：https://diana-cl.github.io/Diana-Cl/en/topics/nekobox#bypass
- 原文摘录：在 NekoBox 设置里可以配置"被排除（bypass）的 App 列表"，这些 App 的流量**不经过 Nekobox 的 VPN** 而是直连系统网络
- 但 Nekobox **自身**仍然要占 Android 的 VPN slot

### 为什么这个特性救不了用户

- Nekobox 的"per-app VPN"是**让某些 App 绕过 Nekobox**（即这些 App 走直连）
- 但 **Tailscale App 自己想用 VPN slot** → Nekobox 也想用 VPN slot → 互斥问题**依然存在**
- Tailscale 是 Nekobox 想"被 Nekobox 管理"的对象（Nekobox 想代理 Tailscale 的 100.x.x.x 流量），不是"绕过 Nekobox"的对象

### 与 sing-box 内核的对应

NekoBox 底层是 sing-box，理论上 sing-box 支持 `route.rules` 里的 `package_name` 字段（`experimental/libbox/tun.go` 实现了 per-package 路由），但 Nekobox 的 GUI 只暴露了"白名单"形式，**不能把 Tailscale App 单独从 VPN 池里摘出来**——因为这不是"绕过 Nekobox"语义，而是"让 Tailscale 和 Nekobox 共存"语义。

### 关键代码事实

- `deepwiki.com/MatsuriDayo/NekoBoxForAndroid/3.2-configuration-builder` 显示 NekoBox 的 `buildConfig` 用 `MyOptions`（sing-box 的 JSON schema）拼配置
- sing-box 的 `TunInbound` 配置里支持 `includePackage`、`excludePackage`（`option/tun.go`），但 **NekoBox 的"Allow apps to bypass VPN" UI 只生成 `excludePackage`**——意思是只支持"白名单直连"模式

### 一句话总结

> NekoBox 的"分应用 VPN"是**白名单 bypass** 模式，不能解决"两个 VPN App 抢 slot"问题。**结论：❌ 不支持 Nekobox 和 Tailscale 共存**

---

## 问题 2：Tailscale Android 客户端"按需连接"或"非 VPN 模式"

### 结论：❌ Tailscale Android 客户端 **没有"非 VPN 模式"开关**，**没有"按需连接"用户可配置项**（除 MDM）

### 证据 1：Tailscale 官方 KB 明确说 Android/iOS 强制走 VPN

- **链接**：https://tailscale.com/kb/1105/other-vpns
- 原文摘录（Device limitations 章节）：
  > "iOS and Android enforce a limit of running only one VPN at a time. As a result, it is not possible to have more than one active VPN on these platforms."

### 证据 2：Tailscale Android 应用"用 Tailscale 子网"是路由选项，不是 VPN 开关

- **链接**：https://tailscale.com/kb/1072/client-preferences
- 原文摘录：
  > "If you want to ignore the advertised routes, in the menu bar of your device, uncheck **Use Tailscale subnets**."
- 这是**关掉子网路由**（不再走 Tailscale 访问 192.168.x.x 这种内网），**不**意味着关掉 VPN slot
- Android 默认 `accept-routes=true`（其它平台如 Linux 默认是 `false`），关掉这个只影响 100.64/10 之外的子网流量，不影响 VPN slot

### 证据 3：Tailscale 有"userspace networking"模式，但**只支持 Linux/容器**，Android 客户端没暴露

- **链接**：https://tailscale.com/kb/1112/userspace-networking
- 原文摘录：
  > "This often happens in container environments."
  > "You can enable userspace networking from the Tailscale CLI by passing the `--tun=userspace-networking` flag to `tailscaled` before running `tailscale up`."
- **关键限制**："There is no CLI support for iOS and Android."（来自 https://tailscale.com/kb/1080/cli 原文）
- 这意味着 Tailscale Android 应用是闭源、内置 VPN API 的，**用户无法切换到 userspace 模式**

### 证据 4：Tailscale 移动端确实有"on-demand"概念，但只能靠系统层控制

- Android 12+ 系统设置：`设置 → 网络和互联网 → VPN → Tailscale → 设为"按需"` 可以让 VPN 不一直在线
- 但这需要用户每次用 Tailscale 都手动开，**不解决"开代理软件时被挤掉"的问题**——Tailscale 仍占 slot，只是被系统短暂释放
- Tailscale MDMs（KB 1315）支持 `ForceEnabled`、`AlwaysOn.Enabled` 等策略，但**没有"只在需要时占 VPN"这种细粒度选项**：
  - `AlwaysOn.Enabled`：Windows/macOS/iOS
  - `ForceEnabled`：macOS/iOS/Android（强制一直开）
  - `ExcludedPackageNames` / `IncludedPackageNames`：仅 Android 且仅企业 MDM（控制 Tailscale 不代理哪些 App，**不是控制 VPN slot**）

### 一句话总结

> Tailscale Android 没有"非 VPN 模式"用户开关，没有"按需连接"UI（系统级有但不解决冲突）。**结论：❌ 无法在不动 Tailscale Android 客户端的情况下让出 VPN slot**

---

## 问题 3：Tailscale 官方是否暴露 WireGuard 配置给第三方使用

### 结论：⚠️ 部分暴露——可以拿到 **公钥 + Tailscale IP + Peer 端点**，但**私钥不直接给**；想塞进第三方 WireGuard 客户端（如 Nekobox WireGuard 节点）**不可行**（除非用 Headscale）

### 证据 1：Tailscale CLI 可以导出**自己的公钥**和**所有 Peer 的公钥 + 端点**

- **链接**：https://alexwlchan.net/notes/2025/see-tailscale-node-keys/
- 原文命令：
  ```bash
  # 自己节点的公钥
  $ tailscale status --self --json | jq -r .Self.PublicKey
  nodekey:46f9c8656ef1224b5ce5220fbdf96ce38e52aaabeccc9b7358b06481e9481821

  # 某 Peer（linode-vps）的公钥
  $ tailscale debug netmap | jq -r '.Peers | map(select(.ComputedName == "linode-vps")) | .[].Key'
  nodekey:731cd9e2560f29c655b674e4033d7cdffeb210aea917b225099b2d601533502d
  ```
- 这是 **PUBLIC KEY**（`nodekey:` 前缀），不是私钥

### 证据 2：Tailscale 不通过 CLI 暴露 WG 私钥

- 同样来自 KB 1080 CLI 列表（https://tailscale.com/kb/1080/cli），命令有：`up` / `down` / `bugreport` / `cert` / `ip` / `login` / `logout` / `netcheck` / `ping` / `set` / `status` / `ssh` / `version`
- **没有** `tailscale export-config` / `tailscale wg-config` 之类的命令
- KB 1312 `Using Tailscale with custom WireGuard` 在 2025 年其实**已被官方**改写为 Tailscale Serve 文档，不再讨论"导出给第三方 WireGuard 客户端"

### 证据 3：Tailscale 私钥管理的内部机制

- 来源：https://pkg.go.dev/tailscale.com/wgengine/wgcfg（Go 文档）
- 私钥存在本地 `tailscaled.state` 文件里（`/var/lib/tailscale/tailscaled.state` 在 Linux），需要 root 权限才能读
- 拿到私钥 + Peer 列表后，理论上可以拼成标准 WireGuard 配置文件：
  ```ini
  [Interface]
  PrivateKey = <你的 WG 私钥>
  Address = 100.108.217.19/32

  [Peer]
  PublicKey = <Peer 公钥>
  Endpoint = <Peer Tailscale IP>:41641
  AllowedIPs = 100.64.0.0/10, 192.168.5.0/24
  PersistentKeepalive = 25
  ```
- 但官方**不**支持这条路（容易破坏节点签名机制、不会自动续期 key、违反 Tailscale 服务条款）

### 证据 4：sing-box 有原生的 Tailscale outbound——这是"用第三方客户端接入 Tailscale"的官方推荐姿势

- **链接**：https://github.com/SagerNet/sing-box/releases/tag/v1.13.0-rc.7
- 原文摘录（release notes 第 15 项）：
  > "Add system interface and relay server options for Tailscale endpoint"
  > "Update Tailscale to v1.92.4"
- sing-box 把 Tailscale 协议作为**一等公民**的 outbound——意味着你可以在 sing-box 配置文件里直接写：
  ```json
  {
    "outbounds": [{
      "type": "tailscale",
      "tag": "ts-direct",
      "authKey": "tskey-auth-XXXXX"
    }]
  }
  ```
- sing-box 会自己跑 `tailscaled` 协议栈，不需要 Nekobox/WireGuard 客户端介入
- 关键：sing-box 的 TUN 可以**只抓 100.64.0.0/10 的流量**走 Tailscale outbound，其它流量走普通代理 outbound

### 一句话总结

> Tailscale **不**直接暴露 WireGuard 私钥给第三方；但 sing-box 有 native Tailscale 支持，所以**用 sing-box 客户端（Husi/Hiddify/NekoBox 的兄弟 fork）才是把 Tailscale 流量"塞进代理软件"的正确姿势**——但这条线对 Nekobox 用户来说有点绕。

---

## 问题 4：实测"双 VPN 共存"工具

### 结论：✅ **sing-box 内核的 Android 客户端**（Husi / Hiddify / Karing / NekoBox 兄弟）**原生支持 Tailscale + 普通代理共存**；Nekobox 自己**不能**用 Tailscale 协议

### 工具对比

| 工具 | 内核 | 支持 Tailscale outbound | 能否"不占 VPN slot 跑 Tailscale" | 综合推荐度 |
|------|------|-------------------------|-------------------------------|----------|
| **NekoBox for Android** (MatsuriDayo) | sing-box | ❌ 没有 Tailscale outbound UI（理论上可手写 JSON） | ❌ 占 VPN slot | ⭐⭐ |
| **Exclave** (NekoBox 同作者新分支) | sing-box | ✅ 实验性 | ❌ 占 VPN slot | ⭐⭐⭐ |
| **Husi** (xchacha20-poly1305) | sing-box v1.13+ | ✅ 原生 Tailscale outbound | ❌ 占 VPN slot | ⭐⭐⭐⭐ |
| **Hiddify** | sing-box | ✅ 原生 Tailscale outbound | ❌ 占 VPN slot | ⭐⭐⭐⭐ |
| **Karing** (KaringX) | sing-box | ✅ 原生 Tailscale outbound | ❌ 占 VPN slot | ⭐⭐⭐⭐ |
| **Clash Meta for Android** (MetaCubeX) | mihomo | ❌ mihomo 不支持 Tailscale 协议 | ❌ 占 VPN slot | ⭐ |
| **Magisk Tailscaled** (root 专用) | tailscaled userspace | ✅ 完整 Tailscale 客户端 | ✅ **不占 VPN slot**（走 SOCKS5 1099 端口） | ⭐⭐⭐⭐⭐ |
| **Tailscale Android 官方 App** | tailscaled kernel | ✅ | ❌ 占 VPN slot | - |

### 关键证据 1：sing-box 1.13 release notes 明确有 Tailscale 支持

- **链接**：https://github.com/SagerNet/sing-box/releases/tag/v1.13.0-rc.7
- 原文摘录（节选）：
  > "**1** NaiveProxy outbound now supports QUIC..."
  > "**9** Supported from TUN, WireGuard and Tailscale inbounds to Direct, WireGuard and Tailscale outbounds."
  > "**11** `preferred_by` route rule item... For Tailscale: MagicDNS domains and peers' allowed IPs."

### 关键证据 2：Husi 是 sing-box 的"极客 fork"，原生 Tailscale 支持

- **链接**：https://github.com/xchacha20-poly1305/husi
- Husi（不是 SagerNet 本人写的 Husi，是 xchacha20-poly1305 的 fork）直接基于 sing-box 1.13+，可以配 Tailscale 节点
- 在 Husi 的 inbound 选 TUN、outbound 配两条：
  - `tailscale` 类型（直连 Tailscale 100.x 流量）
  - `vmess` / `vless` / `ss` / `hysteria2` 类型（其它外网流量走代理）
- 然后在 route rules 里：
  ```json
  {
    "route": {
      "rules": [
        { "ip_cidr": ["100.64.0.0/10"], "outbound": "tailscale" },
        { "domain_suffix": [".ts.net"], "outbound": "tailscale" }
      ]
    }
  }
  ```
- **但 Husi 自己也占 VPN slot**——它替代的是 Nekobox，不是 Tailscale

### 关键证据 3：Magisk Tailscaled 模块——唯一不占 VPN slot 的 Tailscale 方案

- **链接**：https://magisk.dev/modules/tailscaled/ + https://github.com/anasfanani/Magisk-Tailscaled
- 原文（README 摘录）：
  > "The Tailscale app on the Play Store runs with Android's VPN, which means you can't use Tailscale while another VPN is active. This Magisk module, on the other hand, allows you to use both an Android VPN and Tailscale at the same time."
- 工作机制：
  - 模块在开机时跑 `tailscaled -tun=userspace-networking -statedir=/data/adb/tailscale/tmp/ ...`
  - 启动一个 `hev-socks5-tunnel` 在 `localhost:1099` 暴露 SOCKS5 代理
  - Tailscale daemon **完全不用 VPN slot**（userspace networking 模式）
  - 配套 Nekobox 配一条 SOCKS5 节点指向 127.0.0.1:1099
- **前置条件**：手机必须 **root + Magisk**
- **限制**（原文 Limitations）：
  > "This module only support for arm or arm64 architecture"
  > "MagicDNS currently not working"
  > "Subnet routes is manually routed with socks5-tun, you must define your own ip routes"

### 关键证据 4：XDA 论坛验证过 Magisk Tailscaled + Nekobox 组合

- **链接**：https://xdaforums.com/t/module-magisk-tailscaled-running-tailscale-on-android-with-root.4645949/
- 原文（模块作者本人的帖子）：
  > "I use 'NekoBox'/mihomo to route my 100.x.x.x to use local proxy on port 1099."

### 一句话总结

> **如果用户手机已 root**：装 Magisk Tailscaled + Nekobox 路由规则（最优解，**完全绕开 VPN slot 互斥**）
> **如果用户手机没 root**：用 Husi/Hiddify 替代 Nekobox（**用 Tailscale outbound 替代 Tailscale App**），但仍然占 VPN slot，所以 Tailscale App 就用不上了——所以这条路**等于替换 Nekobox 而不是共存**
> **如果用户就是要 Nekobox + Tailscale 都用**：只能放弃其中一方占 VPN slot——把 Nekobox 换成"PC 上的 Mihomo 给手机当代理"（方案 3）

---

## 问题 5：方案三落地检查（PC 端 Mihomo 状态）

### 结论：✅ 几乎全到位，但需要 **2 处手动调整**：(1) `allow-lan: true` (2) 防火墙放行 7890/7891

### 实测结果（2026-06-17 在 `E:\notebook` 工作目录下执行）

#### 5.1 Mihomo / Clash 进程

```powershell
PS> Get-Process | Where-Object {$_.ProcessName -match 'mihomo|clash|tailscale|nekobox'}
ProcessName            Id MainWindowTitle
-----------            -- ---------------
clash-verge         19224
clash-verge-service  5904
verge-mihomo        41468
tailscaled          16596
tailscaled          27296
tailscale-ipn       42828
```

✅ **Clash Verge + verge-mihomo 在跑**（这就是用户的 Mihomo 进程）
✅ **tailscaled 也在跑**（Tailscale 客户端内核进程）

#### 5.2 监听端口

```powershell
PS> Get-NetTCPConnection -LocalPort 7890,7891,7892,9090,2080 -ErrorAction SilentlyContinue
（无输出）
```

```powershell
PS> Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -InformationLevel Detailed
WARNING: TCP connect to (127.0.0.1 : 7890) failed
TcpTestSucceeded : False
```

❌ **7890 端口没在监听**——意味着 Clash Verge **当前没启用 TUN/系统代理**，或者 mihomo 内核没在跑代理（只跑了 GUI 壳）

#### 5.3 配置文件位置

```powershell
PS> Get-Content C:\Users\ZS\.config\clash\config.yaml -TotalCount 30
mixed-port: 7890
redir-port: 7892
allow-lan: false          ← 关键！要改成 true
mode: Rule
log-level: info
external-controller: '127.0.0.1:9090'
secret: ''

cfw-bypass:
  - localhost
  - 127.*
  - 10.*
  - 172.16.*
  ...
```

⚠️ **`allow-lan: false`**——意味着即使 7890 监听了，**手机用 Tailscale IP 也连不上**（绑在 loopback）
⚠️ **`mixed-port: 7890`** 是 SOCKS5+HTTPS 混合代理（手机用这个最方便）
⚠️ **`redir-port: 7892`** 是透明代理（iOS/PC 系统代理模式用）

#### 5.4 Tailscale 虚拟接口

```powershell
PS> Get-NetIPAddress -IPAddress '198.18.0.1'
IPAddress  InterfaceAlias
---------  --------------
198.18.0.1 Mihomo
```

✅ **198.18.0.1 在 "Mihomo" 接口上**（这是 mihomo 的 fake-ip 模式虚拟接口）
但这只是 DNS 拦截虚拟接口，不代表 mihomo 代理端口在监听

#### 5.5 防火墙状态（参照 `FIX_LAN_ACCESS.md` 的诊断）

`FIX_LAN_ACCESS.md` 已确认：**PC 上没有任何针对 3000/5055 的入站 Allow 规则**（虽然不是 7890，但**结论相同**——Windows 默认 Block 入站，需要手动放行）

### 用户能否直接用 100.108.217.19:7890？

#### 当前状态：❌ **不能直接用**

原因：
1. **Clash Verge 没启用 TUN 模式** → 7890 端口根本没起来（实测确认）
2. **`allow-lan: false`** → 即使起了，也只接受 127.0.0.1 的连接
3. **没有入站防火墙规则** → 即使前两个都修了，Windows 防火墙也会拦掉手机发来的 TCP 包

#### 修复步骤（3 步搞定）

1. **打开 Clash Verge → 启用 TUN 模式（或系统代理）**
   - 默认情况下打开主界面 → 顶部开关打开
   - 确认 `verge-mihomo` 进程在跑、`7890` 端口起来了：`Get-NetTCPConnection -LocalPort 7890` 应返回 `Listen` 行

2. **编辑 `C:\Users\ZS\.config\clash\config.yaml`，把 `allow-lan: false` 改成 `allow-lan: true`**
   - 然后回 Clash Verge 主界面 → `Profiles` → 重新加载配置（或重启内核）
   - 验证：`Get-NetTCPConnection -LocalPort 7890` 应返回 `LocalAddress = 0.0.0.0`（不再是 127.0.0.1）

3. **放行 Windows 防火墙**（管理员 PowerShell）
   ```powershell
   New-NetFirewallRule -DisplayName "Mihomo Mixed Port" -Direction Inbound -LocalPort 7890 -Protocol TCP -Action Allow -Profile Private,Domain
   New-NetFirewallRule -DisplayName "Mihomo HTTP API" -Direction Inbound -LocalPort 9090 -Protocol TCP -Action Allow -Profile Private,Domain
   ```
   - 不需要放行 7892（透明代理端口，手机 SOCKS5 模式不用）
   - 验证：在 PC 上 `Test-NetConnection 100.108.217.19 -Port 7890`，应返回 `TcpTestSucceeded: True`

#### 修复后用户的使用流程

1. 手机 Tailscale 打开（仍占 VPN slot，但只代理 100.x 流量，开销小）
2. 手机 Nekobox 配置 → 新建 **SOCKS5 节点**：
   - 服务器：`100.108.217.19`
   - 端口：`7890`
   - 用户名/密码：空（mihomo 默认不认证）
3. Nekobox 路由规则：
   - 100.64.0.0/10 → 走 Tailscale VPN（Tailscale 自己在管）
   - 其它所有流量 → 走 SOCKS5 节点到 100.108.217.19:7890（PC 的 mihomo）
4. Nekobox **仍然占 VPN slot**（因为要拦所有 App 的流量转发给 mihomo SOCKS5）
5. Tailscale 也仍然占 VPN slot
6. **问题来了：这两个又抢 VPN slot 了**——所以**这个方案要成立，需要让 Nekobox 不再占 VPN slot**

### 真正的方案 3.5 落地

**让 Nekobox 用"分应用 VPN"模式（白名单 bypass），只代理你想要的 App，留出 TUN 通道给 Tailscale**

1. 装 Nekobox，开启 TUN
2. Nekobox 设置 → `Allow apps to bypass VPN` → **取消勾选所有你想走代理的 App**（默认就是全选 bypass）
3. Nekobox 实际上**只对"非 bypass"列表里的 App 生效**
4. 但 Nekobox **仍然占 VPN slot**（即使 bypass 列表全选，它也占着 slot）

**这条路是死胡同——见问题 1 的结论**。

### 真正可行的方案 3（修正版）

**用 Magisk Tailscaled 跑 Tailscale（不占 VPN slot）+ Nekobox 跑代理（占 VPN slot）**

或者：

**PC 端 Mihomo 直接给手机当 SOCKS5 代理 + 手机只装 Nekobox 不装 Tailscale App**——但用户明确说要用 Tailscale 的 100.x 访问 PC，所以这条路要 Tailscale 在手机端以**某种方式**存活

### 终极方案：让 PC 直接当 Subnet Router

1. PC 上 Tailscale 启用 subnet router（宣告 192.168.5.0/24 或 PC 上的 Open Notebook 端口）
2. 手机 Tailscale 接受路由
3. 手机浏览器直接访问 `http://100.108.217.19:3000`（PC 的 Tailscale IP）即可
4. **PC 的 3000 端口**必须放行防火墙（参照 `FIX_LAN_ACCESS.md` 修复 1）
5. **不**需要 Nekobox——直接用 Tailscale App 就行

但 Tailscale App 仍占 VPN slot——如果用户**同时也想要代理外网**，那还是冲突。

---

## 最终推荐（3 个方案，按可行性排序）

### 方案 A：Magisk Tailscaled + Nekobox（**推荐度 ⭐⭐⭐⭐⭐**）

**前提**：用户手机 root + Magisk

**步骤**：
1. 装 Magisk Tailscaled 模块（https://github.com/anasfanani/Magisk-Tailscaled/releases/latest）
2. 重启手机，打开终端 app（Termux）执行：
   ```bash
   su
   tailscale login  # 拿到 URL，浏览器授权
   tailscale set --accept-dns=false
   ```
3. 验证：`tailscale ip` 拿到 100.x IP
4. Nekobox 配置：
   - 装一个 SOCKS5 节点：`127.0.0.1:1099`（Magisk Tailscaled 自动暴露的 SOCKS5）
   - 路由规则：`100.64.0.0/10 → 这个 SOCKS5 节点`
5. Nekobox 启动（**它会占 VPN slot**）
6. **Tailscale 走 userspace，Nekobox 走 VPN，**两者不冲突** ✓

**优势**：唯一真·共存的方案，Tailscale 走内核，Nekobox 走用户态代理
**劣势**：必须 root

### 方案 B：PC 端开 Mihomo LAN 共享（**推荐度 ⭐⭐⭐⭐**）

**前提**：PC 上有 Clash Verge（已满足）

**步骤**：
1. 编辑 `C:\Users\ZS\.config\clash\config.yaml`：
   - `allow-lan: true`（关键）
2. Clash Verge 重启内核
3. 管理员 PowerShell：
   ```powershell
   New-NetFirewallRule -DisplayName "Mihomo 7890" -Direction Inbound -LocalPort 7890 -Protocol TCP -Action Allow -Profile Private,Domain
   ```
4. 验证 PC 上 `Test-NetConnection 100.108.217.19 -Port 7890` 成功
5. 手机 Nekobox 配 SOCKS5 节点：`100.108.217.19:7890`
6. 手机 Tailscale 继续用（仍占 VPN slot，但只处理 100.x 流量）
7. 手机 Nekobox **也占 VPN slot**——**两者仍冲突**

**这条路其实是死胡同**，因为 Nekobox 占 VPN slot 的问题没解决。

**修正**：用户**完全不用 Nekobox**——直接用系统代理（Android `WLAN → 高级 → 代理 → 手动 → 100.108.217.19:7890`），这样 **Tailscale 占 VPN slot，系统代理（走 Mihomo SOCKS5）不占 VPN slot**，两者共存 ✓

**这才是真·方案 B**：
- Tailscale Android App 走 VPN slot（管 100.x 流量）
- Android 系统代理（HTTP/SOCKS）走 `100.108.217.19:7890`（管外网流量）
- **不冲突**——因为 Android 系统代理不走 VpnService

### 方案 C：Husi 替代 Nekobox（**推荐度 ⭐⭐⭐**）

**前提**：用户愿意换客户端

**步骤**：
1. 装 Husi（https://github.com/xchacha20-poly1305/husi/releases）
2. 配 Tailscale outbound（用 auth key）
3. 配 SOCKS5 / VLESS / Hysteria2 outbound（你现有的代理节点）
4. Husi 启动——它一个 App 占 VPN slot，自己内部路由：
   - 100.64.0.0/10 → Tailscale outbound
   - 其它 → SOCKS5 outbound
5. **不再需要 Tailscale Android App**（Husi 内部就是 Tailscale 客户端）

**优势**：客户端统一管理，配置灵活
**劣势**：换客户端有学习成本，且 Husi 不是 Tailscale 官方，体验可能不同

### 方案 D：放弃 Tailscale App，用 Cloudflare Tunnel（**推荐度 ⭐⭐⭐⭐**）

**前提**：PC 端可装 cloudflared

**步骤**（参照已有的 `setup-cloudflare-tunnel.md`）：
1. PC 上跑 `cloudflared tunnel run`
2. 手机浏览器直接访问公网域名（`https://notebook.your-domain.com`）
3. **不**需要 Tailscale、**不**需要 VPN slot、**不**需要 Nekobox

**优势**：彻底绕开所有冲突
**劣势**：依赖 Cloudflare 账号 + 公网域名；流量过 CF

---

## 落地建议

**用户当前状态评估**：
- ✅ Clash Verge 装好（mihomo 进程在跑）
- ✅ Tailscale 装好（tailscaled 在跑，Tailscale IP `100.108.217.19`）
- ❌ Mihomo 代理端口 7890 未监听
- ❌ `allow-lan: false`
- ❌ Windows 防火墙没放行 7890

**立即可执行（5 分钟）**：
1. Clash Verge 启动 TUN
2. `allow-lan: true` + 重启内核
3. 防火墙放行 7890
4. 验证 `100.108.217.19:7890` 通了

**然后用"方案 B 修正"**：手机**只**用 Tailscale App 访问 PC（100.x IP + 3000 端口），外网走 Android 系统代理指向 `100.108.217.19:7890`，**Nekobox 不用开**。

如果用户**执意要 Nekobox**——要么接受只能二选一（要么 Nekobox 跑代理、要么 Tailscale App 跑内网访问），要么上 Magisk Tailscaled（方案 A）。

---

## 附录：相关链接

- Tailscale 与其他 VPN 共存：https://tailscale.com/kb/1105/other-vpns
- Tailscale userspace 模式：https://tailscale.com/kb/1112/userspace-networking
- Tailscale 客户端偏好：https://tailscale.com/kb/1072/client-preferences
- Tailscale MDM 策略：https://tailscale.com/kb/1315/mdm-keys
- Tailscale 节点密钥查看：https://alexwlchan.net/notes/2025/see-tailscale-node-keys/
- sing-box 1.13 release notes（Tailscale 支持）：https://github.com/SagerNet/sing-box/releases/tag/v1.13.0-rc.7
- Husi（sing-box Android 客户端）：https://github.com/xchacha20-poly1305/husi
- Magisk Tailscaled：https://github.com/anasfanani/Magisk-Tailscaled
- NekoBox 文档：https://diana-cl.github.io/Diana-Cl/en/topics/nekobox
- sing-box TUN 文档：https://sing-box.sagernet.org/configuration/inbound/tun/

---

## 附录：相关本机文档

- `TAILSCALE_PROXY_CONFLICT.md`——已有的 5 方案对比（方案 A/B/C/D/E）
- `FIX_LAN_ACCESS.md`——PC 防火墙放行
- `LAN_GUIDE.md`——LAN 访问基础
- `setup-tailscale.md`——Tailscale 安装
- `setup-cloudflare-tunnel.md`——Cloudflare Tunnel 方案
- `USER_GUIDE.md`——完整使用指南
