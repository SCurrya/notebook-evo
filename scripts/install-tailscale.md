# Tailscale Windows 客户端安装指引

> 本指引配套 `e:\notebook\downloads\tailscale-setup-latest-amd64.msi` 安装包使用，帮助你在 Windows PC 上完成 Tailscale 客户端的安装与首次登录，并与手机/其他电脑组成加密虚拟局域网。

---

## 一、安装包信息

| 项目 | 值 |
| --- | --- |
| 文件名 | `tailscale-setup-latest-amd64.msi` |
| 路径 | `e:\notebook\downloads\tailscale-setup-latest-amd64.msi` |
| 类型 | Windows MSI 安装包（amd64） |
| 来源 | https://pkgs.tailscale.com/stable/tailscale-setup-latest-amd64.msi |

> MSI 是图形化安装包，需要在桌面环境下双击运行；不要在无人值守的服务器/CI 环境中直接调用 `msiexec`（除非加 `/quiet` 等参数并明确知道后果）。

---

## 二、注册 / 登录账号

1. 在浏览器中打开：https://login.tailscale.com
2. 点击 **Log in**（或注册），选择一个已有的第三方账号登录即可，无需单独注册 Tailscale 账号：
   - Google 账号
   - GitHub 账号
   - Microsoft 账号
   - 其他（Apple、Email SSO 等）
3. 首次登录会自动创建一个属于你的 **Tailnet**（个人虚拟局域网），后续所有设备都加入到这个 Tailnet 中。

> 推荐使用长期可用的邮箱关联的账号，避免换号后无法找回 Tailnet。

---

## 三、PC 端安装步骤

### 1. 双击 MSI 完成安装

1. 打开 `e:\notebook\downloads\` 目录
2. 双击 `tailscale-setup-latest-amd64.msi`
3. 在弹出的安装向导中一路点击 **Next** → **Install** → **Finish**（默认配置即可）
4. 安装完成后会**自动启动 Tailscale 客户端**

### 2. 在系统托盘登录

1. 安装成功后，**Windows 系统托盘**（屏幕右下角时钟附近）会出现 Tailscale 的小图标
2. **右键**该图标 → 选择 **Log in...**
3. 浏览器会自动跳转到 https://login.tailscale.com，**使用与第二节相同的账号**完成授权
4. 授权成功后，浏览器会提示"You can close this window"，关闭即可
5. 回到系统托盘，Tailscale 图标会变为已连接状态（通常不再带红色叉号）

### 3. 验证本机已上线

打开 PowerShell 或命令提示符，执行：

```powershell
tailscale status
```

正常输出示例（会列出本机和 Tailnet 中的其他设备）：

```
100.64.10.20  your-pc-name   your-email@gmail.com   windows   -
```

记录下本机的 Tailscale 名称（`<机器名>.<tailnet>.ts.net`）和 IP（`100.x.x.x`），后面手机/其他电脑访问 PC 时要用到。

---

## 四、其他设备加入（手机 / 另一台电脑）

只要使用 **同一个 Tailscale 账号** 登录，它们就会自动出现在你的 Tailnet 中，相互之间可以直接通过 `100.x.x.x` 或 `<机器名>.ts.net` 通信。

### 手机端（Android / iOS）

1. 在应用商店搜索 **Tailscale** 并安装（或访问 https://tailscale.com/download）
2. 打开 App → 点击 **Sign in** → 用同一个账号登录
3. 首次会弹出"是否允许建立 VPN 连接"的系统提示，**点击允许**
4. 登录成功后，手机就拿到了一个 `100.x.x.x` 的 Tailscale IP

### 另一台电脑（Windows / macOS / Linux）

1. 同样从 https://tailscale.com/download 下载对应平台的客户端
2. 安装后通过系统托盘 / 应用菜单右键 **Log in**，用同一账号授权
3. 登录后即可在 `tailscale status` 中看到这台新设备

---

## 五、查询 Tailscale 域名 / 状态

在 PC 上执行：

```powershell
tailscale status
```

常用子命令：

| 命令 | 作用 |
| --- | --- |
| `tailscale status` | 查看 Tailnet 中所有设备及其在线状态 |
| `tailscale ip -4` | 查看本机的 IPv4 Tailscale 地址 |
| `tailscale ping <名称或IP>` | 测试到对端的连通性 |
| `tailscale netcheck` | 检查 NAT 穿透质量 |

完整域名格式为 `<机器名>.<tailnet名>.ts.net`，例如 `my-pc.tail1234.ts.net`，也可以在管理后台查看：https://login.tailscale.com/admin/machines

---

## 六、防火墙与端口配置提示

> **重要：5055 端口（Open Notebook API）无需对公网开放。**

| 端口 / 协议 | 用途 | 是否需要对外开放 |
| --- | --- | --- |
| **41641/UDP** | Tailscale 节点之间建立 WireGuard 直连（或经 DERP 中继） | ✅ 必须放行出站 UDP 41641（绝大多数家庭网络默认允许） |
| **5055/TCP** | Open Notebook API 监听端口（仅本机/Tailnet 内访问） | ❌ **不要**对公网开放，也不要做路由器端口映射 |
| 80/443（出站） | Tailscale 控制面登录、DERP 中继回退 | 默认出站即可 |

### 关键点

1. **5055 走 Tailscale 虚拟网卡即可**：手机/其他设备通过 Tailscale 通道访问 `http://<PC 的 100.x.x.x>:5055`，数据经过端到端加密，不需要走公网。
2. **不要在路由器上做 5055 端口映射**：把 5055 暴露到公网会带来安全风险，Tailscale 的目的就是**避免**这种暴露。
3. **Windows 防火墙**：默认情况下，Tailscale 安装时会自动添加放行规则；如果发现手机连不上 PC 的 5055，可以在 Windows Defender 防火墙中为 `tailscale.exe` 和 5055 端口添加入站规则（仅对 Tailscale 虚拟网卡 `Tailscale` 开放即可，不要对 `公用网络` 开放）。
4. **41641/UDP 出站**：Tailscale 用 41641/UDP 与其他节点协商（NAT 穿透），绝大多数家庭路由器默认放行；如果所在网络封禁了 UDP，需要联系网络管理员或改用 DERP 中继（Tailscale 会自动回退，速度稍慢但仍可用）。

---

## 七、卸载 Tailscale

如果需要卸载：

1. **控制面板** → **程序和功能** → 找到 **Tailscale** → **卸载**
2. 登录 https://login.tailscale.com/admin/machines，删除对应的设备记录

卸载后 Tailnet 仍保留，其他设备不受影响。

---

## 八、常见问题速查

| 现象 | 排查方向 |
| --- | --- |
| 托盘没有 Tailscale 图标 | 检查是否被杀毒软件拦截；或重启一次客户端 |
| `tailscale status` 命令找不到 | PowerShell 没识别 PATH，试试 `& "C:\Program Files\Tailscale\tailscale.exe" status` |
| 手机连不上 PC 的 5055 | 先在 PC 本机 `curl http://127.0.0.1:5055/health` 确认 API 启动；再检查 Windows 防火墙是否放行 Tailscale 虚拟网卡 |
| Tailscale 一直显示 `offline` | 检查网络是否能访问 `login.tailscale.com`（443 出站）；或重新 Log in |
| 速度很慢 | `tailscale status` 看是否走 `relay`（DERP 中继），可以尝试切换网络或开启路由器 UPnP 改善 NAT 穿透 |
