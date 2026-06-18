# 个人 PC + 手机 数据同步 / 远程访问 方案对比

> 调研对象：可用于「家庭 PC 自托管服务 + 手机远程访问」的开源 / 免费方案
> 项目背景：Open Notebook 远程访问 API（FastAPI + SurrealDB，监听 5055）
> 核心约束：个人开发者、零月费、数据自托管、最好端到端加密
> 调研日期：2026-06-17

---

## 一、对比总表

> 说明：
> - 「设备数限制」按各方案**免费层**的官方说明。
> - 「流量是否中转」：P2P 直连 = 不经第三方；Relay = 经官方/自有中转；服务端转发 = 经用户自建服务器。
> - 「端到端加密」= 数据在「客户端 ↔ 客户端 / 客户端 ↔ 自建服务端」之间是否被方案自身加密（与 HTTPS/TLS 含义不同）。
> - 「需公网 IP」= 是否依赖用户自己拥有公网 IPv4（IPv6-only / CGNAT 不算）。
> - 「配置难度」按 1-5 星打分，1 = 一键，5 = 需要写配置文件 + 维护证书。

| # | 方案 | 类型 | 需公网 IP | 需公网 VPS/服务器 | 需自有域名 | 需装客户端 | 需登录账号 | 流量是否中转 | 端到端加密 | 免费设备数 | 配置难度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Tailscale**（基线） | P2P Mesh VPN | ❌ | ❌ | ❌ | ✅ PC+手机 | ✅（Google/GitHub/微软 SSO） | 默认 P2P，失败走 DERP 中继 | ✅ WireGuard | 100 | ⭐ |
| 2 | **ZeroTier** | P2P Mesh VPN（自研协议） | ❌ | ❌ | ❌ | ✅ PC+手机 | ✅（ZeroTier 账号） | 默认 P2P，失败走 planet 中继 | ✅ 自研协议 | 25（旧版）/10（新版） | ⭐⭐ |
| 3 | **WireGuard（裸用）** | 内核级 VPN | ✅ 至少一端 | ❌ | ❌ | ✅ 系统客户端 / App | ❌ | P2P 直连 | ✅ WireGuard | 无限制（自管） | ⭐⭐⭐⭐⭐ |
| 4 | **Nebula** | Overlay 网络（Noise） | ❌（推荐 1 个 lighthouse 在公网） | ✅ 至少 1 个 lighthouse VPS | ❌ | ✅ PC+手机 | ❌（自建 PKI/CA） | P2P，失败可中继 | ✅ Noise + X.509 | 无限制（自管） | ⭐⭐⭐⭐ |
| 5 | **frp / rathole** | 内网穿透 | ✅ 服务端 | ✅ 自购 VPS | ❌ | ✅ PC 端 + 服务端 | ❌ | 经 VPS 中转 | ⚠️ 可选 TLS/Noise | 无限制（自管） | ⭐⭐⭐ |
| 6 | **ngrok** | 商业内网穿透 | ❌ | ❌ | ❌ | ✅ PC 端 | ✅ | 经 ngrok 云 | ⚠️ TLS（ngrok 可看元数据） | 免费 1 GB/月、3 endpoint、20k req | ⭐ |
| 7 | **Cloudflare Tunnel**（基线） | 反向代理隧道 | ❌ | ❌ | 固定域名要，临时不要 | ✅ PC 端（cloudflared） | ✅（Cloudflare 账号） | 经 Cloudflare 边缘 | ⚠️ Cloudflare 可解密 HTTPS（可加 Access） | 无限制 | ⭐⭐ |
| 8 | **Bore / SSH 反向隧道** | 极简 TCP 隧道 | ✅ 至少 1 端公网 | 可有可无 | ❌ | ✅ PC 端 | ❌ | 经中转 | ⚠️ SSH 加密 | 无限制 | ⭐⭐⭐ |
| 9 | **RustDesk / 自建 ToDesk** | 远程桌面 | ❌ | ✅ 自建 hbbs+hbbr | ❌ | ✅ PC+手机 | ❌（自建 key） | P2P，失败走 hbbr | ✅ 端到端加密 | 无限制（自管） | ⭐⭐⭐ |
| 10 | **Syncthing** | P2P 文件同步 | ❌ | ❌ | ❌ | ✅ PC+手机 | ❌ | 默认 P2P，失败走 relay | ✅ TLS + PFS | 无限制（自管） | ⭐⭐ |
| 11 | **直接端口暴露 + 防火墙 + DDNS** | 传统方式 | ✅ | ❌ | ✅（DDNS 必备） | ❌（浏览器/API 直接连） | ❌ | 直连 | ⚠️ 取决于应用层 HTTPS | 无限制 | ⭐⭐⭐⭐ |
| 12 | **Pangolin / Netmaker** | 自托管反向代理 + WireGuard | ❌ | ✅ 自建服务端 | ✅ | ✅ PC 端（Newt/netclient），手机可用浏览器 | ❌（自建鉴权） | 经自建服务端 | ✅ WireGuard | 无限制（自管） | ⭐⭐⭐⭐ |
| 13 | **Pomerium / Cloudflare Access + Zero Trust** | 零信任身份网关 | ❌ | ❌（CF）/ ✅（Pomerium 自建） | ✅ | ❌（浏览器代理） | ✅（CF）/ ✅（OIDC） | 经网关中转 | ⚠️ 网关可解密 | 无限制 | ⭐⭐⭐ |

---

## 二、各方案优缺点简述

### 1. Tailscale（基线方案）
✅ 优点：
- 零配置：装客户端 + 同账号登录即可组网，5 分钟上手
- 基于 WireGuard，性能与安全兼得
- 100 台设备免费，足够家用
- 支持 MagicDNS、ACL、SSH、Subnet Router、Funnel
- Android/iOS 客户端成熟

❌ 缺点：
- 依赖 Tailscale 控制服务器（控制面不开源），元数据可见
- 中国大陆 NAT 穿透率较低，常需走 DERP 中继
- ACL/精细管控是付费特性

🎯 适合：个人开发者首选、手机直连 PC API 的标准方案

---

### 2. ZeroTier
✅ 优点：
- 协议自研 + Layer 2，支持复杂网络拓扑
- Android/iOS/Windows/macOS/Linux 全平台
- 可以自建 `moon` 节点提升国内穿透率

❌ 缺点：
- **2025 年改版后新版免费层只允许 10 设备**（旧版 legacy 25 设备），对家庭用户变抠门
- 没有原生 SSO，权限管理偏弱
- 国内 UDP 仍受 QoS 影响

🎯 适合：不愿依赖 Tailscale、想用自研协议、且能接受 10 设备限制的人

---

### 3. WireGuard（裸用）
✅ 优点：
- 内核级性能，最快最省电
- 完全自管，零月费、零依赖
- 加密强度行业标杆

❌ 缺点：
- **必须有一端是公网 IP**（家庭宽带大多拿不到）
- 配置纯文本，IP 变了要手动改
- 没有设备发现、没有 ACL 中心管理
- iOS 客户端需要重启应用才能切节点

🎯 适合：有一台公网 VPS 的人，把 VPS 当 hub，PC/手机当 spoke

---

### 4. Nebula（Slack 开源 overlay）
✅ 优点：
- 完全开源、零费用、零设备数限制
- 自建 PKI/CA，证书可分组
- Android/iOS 都有官方客户端
- P2P 失败可走中继

❌ 缺点：
- **至少要 1 个 lighthouse 节点在公网**（即一台便宜 VPS，~$6/月）
- 需要自建 CA、签发证书、配置防火墙规则，维护成本高
- iOS 客户端功能阉割（不能自定义 DNS、防火墙规则缺失）
- 文档偏企业级，个人家庭场景「杀鸡用牛刀」

🎯 适合：技术宅、想完全脱离 SaaS 控制面、能折腾 Linux 的人

---

### 5. frp / rathole
✅ 优点：
- 完全自管，零月费（除 VPS 本身）
- frp 是国内最成熟方案，中文文档丰富
- rathole（Rust 写）性能更好、内存更小
- 支持 TCP/UDP/HTTP/HTTPS/STCP/XTCP（P2P 模式）

❌ 缺点：
- **必须有一台公网 VPS**（这是固定开销，5-10 USD/月）
- frpc/rathole 客户端要在 PC 常驻
- frp 流量**全部经过 VPS**，VPS 带宽成瓶颈
- 默认不开端到端加密（可加 TLS，但 VPS 仍可看元数据）

🎯 适合：已有便宜 VPS、想最大化可控、且不在意经 VPS 中转的人

---

### 6. ngrok
✅ 优点：
- 客户端最简单：`ngrok http 5055` 一行命令
- 自动 HTTPS、内置 Web Inspector
- 全球边缘节点

❌ 缺点：
- **免费版限制多**：1 GB/月流量、20k 请求、3 endpoint、域名不可选、HTML 流量有警告页
- 免费域名每次重启都变，手机端配置得跟着改
- 商业版 $8/月起，个人用不划算
- 隐私：ngrok 能看到元数据

🎯 适合：临时调试、demo 给别人看，**不适合长期个人自托管**

---

### 7. Cloudflare Tunnel（基线方案）
✅ 优点：
- 零月费、无限流量
- 自动 HTTPS、自动续证书
- 临时隧道（`trycloudflare.com`）5 分钟搞定
- 固定域名 + 开机自启后体验接近商业 CDN
- 可叠加 Cloudflare Access 做零信任

❌ 缺点：
- 流量**全部经过 Cloudflare**，CF 可解密 HTTPS（虽说不看内容，但理论上可看）
- 固定域名需要 NS 改到 Cloudflare + 拥有域名（域名年费 ~$10）
- 国内访问 Cloudflare 边缘节点速度有时不稳
- DERP/临时域名会变，需重启 cloudflared 或重配手机

🎯 适合：不想暴露家庭 IP、需要一个稳定 HTTPS 入口、又接受 Cloudflare 作为信任方的用户

---

### 8. Bore / SSH 反向隧道
✅ 优点：
- **极简**：bore 一个二进制，SSH 是系统自带
- 零额外依赖、零月费
- 适合临时调试、转发单个端口

❌ 缺点：
- Bore/SSH 反向隧道**要求中转端有公网 IP**（一台便宜 VPS 或朋友的服务器）
- 速度慢、稳定性差、容易被运营商 QoS
- 缺少 ACL、认证、监控
- 不适合作为「家庭 PC 主力远程访问方案」

🎯 适合：临时用一下 SSH 进家庭 PC，或在内网环境做应急穿透

---

### 9. RustDesk（自建远程桌面）
✅ 优点：
- 完全开源、自建 hbbs+hbbr 服务器，零月费
- 端到端加密（End-to-End Encrypted）
- Android/iOS/Windows/macOS/Linux 全平台
- 替代 TeamViewer/AnyDesk，支持文件传输、剪贴板、TCP 隧道
- 自建 server 体验可媲美 AnyDesk

❌ 缺点：
- 远程桌面**不是 API 调用**——手机端要的是数据不是「看屏幕」
- **必须自建 hbbs+hbbr 服务器**（VPS，最低配 1c1g 即可）
- 自建后还需在两端配 key、IP，体验偏运维
- 客户端启动要手动选「自建服务器」，对家人不友好

🎯 适合：需要「远程控制 PC」（如远程修电脑、应急），**不是本项目（API 访问）的最优解**

---

### 10. Syncthing
✅ 优点：
- P2P 文件同步，端到端加密 + PFS（完美前向保密）
- 无中心服务器、无限设备数
- Android 客户端（Syncthing-Fork）成熟
- 适合**离线副本、增量同步**

❌ 缺点：
- **同步的是文件，不是 API 请求**——你无法在手机上"调用 PC 的 FastAPI"
- 同步需要两端都在线（PC 关机时手机不能写入）
- 大量小文件性能差
- 不能替代远程访问 API，只能作为"数据快照备份"补充

🎯 适合：笔记本资料的多设备离线副本备份；**不适合本项目（API 远程访问）**

---

### 11. 直接暴露端口 + 防火墙 + DDNS
✅ 优点：
- 最原始、最直接，无中间层
- 速度最快、延迟最低
- 零月费（除域名年费）

❌ 缺点：
- **必须有公网 IP**（运营商已极少主动给）
- 路由器防火墙、端口转发、IP 白名单全要自己配
- IP 暴露在公网，扫描/爆破风险高（必须自建 fail2ban/WAF）
- 家用宽带上行带宽小（30-50 Mbps 常见）
- DDNS 偶尔抽风、运营商回收 IP 麻烦
- 关电脑 = 断网

🎯 适合：能拿到公网 IP、有运维能力、不嫌麻烦的极客

---

### 12. Pangolin / Netmaker（新兴方案）
✅ 优点：
- **Pangolin = 自托管版 Cloudflare Tunnel + Zero Trust**：反向代理 + SSO 鉴权 + WireGuard 隧道
- Netmaker = 自托管版 Tailscale：管理控制台 + WireGuard
- 完全开源、零月费、无限设备
- Pangolin 可用浏览器无客户端访问（手机不装 VPN 也能用）

❌ 缺点：
- **必须自建服务端**（公网 VPS，最低 1c1g）
- Netmaker 自建管理控制面有学习曲线
- Pangolin 自建需 Docker + 反代 + 域名 + 证书
- 客户端需装 Newt（PC）和 Pangolin Client（手机），生态比 Tailscale 弱
- 国内访问自建 VPS 速度看线路

🎯 适合：不愿用 Tailscale/CF SaaS、愿意用一台 VPS 换完全可控的人

---

### 13. Pomerium / Cloudflare Access + Zero Trust
✅ 优点：
- 在**任何反向代理前面加一层身份认证**
- 支持 OIDC、SSO、MFA、设备指纹
- Cloudflare Access 免费层 50 用户足够个人用
- 不暴露任何服务端口，攻击面归零

❌ 缺点：
- 本身**不是隧道**，必须和 Cloudflare Tunnel / Pangolin / Caddy 等配合
- Cloudflare Access 仍是 SaaS，依赖 CF 账号
- 自建 Pomerium 需要懂 OIDC、IdP 概念
- 对个人项目来说"过度设计"

🎯 适合：在「Cloudflare Tunnel」或「Pangolin」基础上加一层邮箱 OTP/MFA 验证

---

## 三、关键场景适配性分析

### 场景 A：PC 关电脑时还能访问？
> **没有任何一个方案能做到**——所有方案都依赖「PC 上的 Open Notebook API 在运行」。PC 关机 = API 停 = 无法访问。
> 唯一例外：Syncthing 可在 PC 关机后让手机保留**只读离线副本**（最近一次同步内容）。
> 真正 7×24 访问需要把服务迁到 NAS / 旧笔记本 / 树莓派等「常开小主机」。

### 场景 B：必须装手机客户端？
| 方案 | 是否必须装客户端 |
|---|---|
| Cloudflare Tunnel | ❌ 浏览器/API 直接访问，零客户端 |
| Tailscale / ZeroTier / Nebula / Syncthing | ✅ 需装 App（VPN/Sync 客户端） |
| ngrok / frp | ❌（但需 PC 装客户端） |
| RustDesk | ✅ 需装 App（远程桌面） |
| Pangolin | ⚠️ 选配：可浏览器访问，也可装 App |

### 场景 C：是否端到端加密？
| 方案 | 端到端加密？ | 说明 |
|---|---|---|
| Tailscale | ✅ | WireGuard 客户端↔客户端 |
| ZeroTier | ✅ | 自研协议 |
| Nebula | ✅ | Noise + X.509 |
| WireGuard | ✅ | 原生 |
| Syncthing | ✅ | TLS + PFS |
| RustDesk | ✅ | E2EE |
| **Cloudflare Tunnel** | ⚠️ | CF 可解密 HTTPS 流量（TLS termination） |
| **ngrok** | ⚠️ | 同上 |
| frp / rathole | ⚠️ | 可选 TLS，但 VPS 可见 |
| Cloudflare Access | ⚠️ | 网关可解密 |
| DDNS 直接暴露 | ❌ | 取决于应用层是否 HTTPS |

### 场景 D：每月固定开销？
| 方案 | 固定开销 |
|---|---|
| Tailscale / ZeroTier / WireGuard / Cloudflare Tunnel / Syncthing / RustDesk（仅 PC 端） | **$0** |
| Cloudflare Tunnel 固定域名 | **$0** + 域名年费（~¥70） |
| ngrok 免费版 | $0（功能受限） |
| ngrok 付费版 | $8/月 |
| frp / rathole / Nebula / Pangolin / Netmaker / 自建 RustDesk | VPS $5-10/月（最低配） |
| 自建 Pomerium | VPS $5/月 + OIDC IdP 复杂度 |

---

## 四、针对本项目（Open Notebook 远程访问 API）的最终推荐

### 推荐组合 1：Tailscale 主 + Cloudflare Tunnel 备（最省心，零月费）

**适合人群：**
- 不想买 VPS、想零月费
- 愿意用 Google/GitHub/微软账号登录 Tailscale
- 接受 Cloudflare 作为信任方

**组合方式：**
- **主力通道**：Tailscale（手机装 App，PC 装客户端，组网后 `http://100.x.x.x:5055` 直连）
- **备用通道**：Cloudflare Tunnel 临时域名（4G 环境下、Tailscale 不通时，手机应用自动切换）
- **兜底**：PC 上 Open Notebook 设访问密码 + Tailscale ACL 限制只允许手机设备访问 5055 端口

**优点：** 0 月费、配置门槛最低、端到端加密（主通道）、开箱即用
**缺点：** 关电脑 = 断网；依赖 Tailscale 控制服务器

---

### 推荐组合 2：Cloudflare Tunnel 固定域名（仅需一个域名，零月费、零客户端）

**适合人群：**
- 不想在手机上装 VPN 类 App
- 已经有一个域名（或愿意花 ¥70 买个域名）
- 接受 Cloudflare 作为中间人

**组合方式：**
- 在 PC 跑 cloudflared 服务，指向 `notebook.你的域名.com` → `http://localhost:5055`
- 手机浏览器或 App 直接 `https://notebook.你的域名.com` 访问
- 加 Cloudflare Access 做邮箱 OTP 二次验证
- 固定域名 + 开机自启，一次配置长期使用

**优点：** 手机端零 VPN 客户端；HTTPS 自动签发；可叠加 Access 鉴权
**缺点：** 流量经 Cloudflare 中转；关电脑 = 断网；域名年费 ¥70

---

### 推荐组合 3：Tailscale + frp（VPS 用户的双保险）

**适合人群：**
- 已有便宜 VPS（$5/月级别）
- 既要端到端加密、又要公网稳定访问
- 愿意双通道冗余

**组合方式：**
- **主通道**：Tailscale（手机 ↔ PC 直连，零延迟）
- **应急通道**：frp 把 PC:5055 映射到 VPS，手机用 `https://你的VPS域名:port` 访问
- VPS 上用 frp 的 `xtcp` 模式还能做 P2P 进一步降延迟
- 双重保险：Tailscale 抽风时切 frp

**优点：** 一台 VPS 解决「公网稳定 + 端到端加密 + 自托管」三件套
**缺点：** VPS 月费；frp 流量经 VPS（VPS 可见元数据但应用层仍 HTTPS）

---

### 三组合速查表

| 组合 | 月费 | 手机装客户端？ | 关电脑能用？ | 端到端加密 | 配置难度 | 推荐度 |
|---|---|---|---|---|---|---|
| **Tailscale + Cloudflare 备** | $0 | ✅（Tailscale） | ❌ | ✅（主）/ ⚠️（备） | ⭐ | ⭐⭐⭐⭐⭐ |
| **Cloudflare Tunnel 固定域名** | $0 + 域名 ¥70 | ❌ | ❌ | ⚠️ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Tailscale + frp（VPS）** | $5-10 | ✅ | ❌ | ✅ | ⭐⭐⭐ | ⭐⭐⭐ |

### 不推荐用于本项目的方案
- ❌ **ngrok 免费版**：流量限制 + 域名变化，不适合长期自托管
- ❌ **Syncthing**：同步文件而非 API，本项目用不上
- ❌ **RustDesk**：远程桌面不是 API 调用，偏离需求
- ❌ **DDNS + 端口暴露**：家庭无公网 IP 已是常态
- ❌ **Pomerium / Cloudflare Access 单用**：必须搭配 Tunnel 才有意义

### 关于"PC 关电脑时还能访问"
- **所有方案都做不到**，除非把 Open Notebook 迁到：
  - NAS（如群晖、威联通）
  - 旧笔记本当小服务器
  - 树莓派 4B/5（功耗 < 10W）
  - 云厂商小 VPS（最低 $3.5/月）
- 推荐把 SurrealDB 数据目录挂 NAS，开机自动起 docker-compose

---

## 五、参考资料

- Tailscale 官方：[https://tailscale.com/](https://tailscale.com/)
- ZeroTier 官网改版说明（V2EX 2025-12）：[https://global.v2ex.co/t/1178126](https://global.v2ex.co/t/1178126)
- Nebula GitHub：[https://github.com/slackhq/nebula](https://github.com/slackhq/nebula)
- frp GitHub：[https://github.com/fatedier/frp](https://github.com/fatedier/frp)
- rathole GitHub：[https://github.com/rapiz1/rathole](https://github.com/rapiz1/rathole)
- ngrok 定价：[https://ngrok.com/pricing](https://ngrok.com/pricing)
- Cloudflare Tunnel 文档：[https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- Pangolin 官网：[https://pangolin.net/](https://pangolin.net/)
- Netmaker 文档：[https://docs.netmaker.org/](https://docs.netmaker.org/)
- RustDesk Server：[https://github.com/rustdesk/rustdesk-server](https://github.com/rustdesk/rustdesk-server)
- Syncthing 官网：[https://syncthing.net/](https://syncthing.net/)
- Pomerium 官网：[https://www.pomerium.com/](https://www.pomerium.com/)
