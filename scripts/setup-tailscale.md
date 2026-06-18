# Tailscale 安装配置指南

> 本指南面向零基础用户，帮助你在 PC（Windows）和手机（Android）之间建立加密直连，用于访问 Open Notebook API（端口 5055）。

---

## 一、前置说明

### Tailscale 是什么

Tailscale 是一款基于 WireGuard 协议的点对点加密组网工具。它可以把你的多台设备（PC、手机、服务器等）组成一个虚拟局域网，设备之间通过加密通道直接通信。

- **免费个人版**支持最多 100 台设备
- 官网：https://tailscale.com/

### 为什么用它

| 优势 | 说明 |
| --- | --- |
| 加密直连 | 手机和 PC 之间建立端到端加密通道，数据不经过第三方服务器（默认点对点） |
| 不暴露公网端口 | 不需要在路由器上做端口映射，家庭网络 IP 不会暴露在公网 |
| 家庭 IP 隐藏 | 所有通信走 Tailscale 虚拟网卡，对外不暴露真实 IP |
| NAT 穿透 | 支持大多数家庭网络和 4G 网络的 NAT 穿透，无需公网 IP |

---

## 二、PC 端安装（Windows）

### 步骤 1：下载安装

1. 访问下载地址：https://tailscale.com/download/windows
2. 下载 Windows 安装包（`.exe` 文件）
3. 双击安装包，按提示完成安装（一路"下一步"即可）

### 步骤 2：登录账号

1. 安装完成后，系统托盘（屏幕右下角）会出现 Tailscale 图标（一个蓝色的小方块）
2. 右键点击托盘图标 → 选择 `Log in`
3. 浏览器会自动打开登录页面，支持以下账号登录：
   - Google 账号
   - GitHub 账号
   - Microsoft 账号
   - 其他（如 Apple、Email 等）
4. 选择一个你已有的账号登录即可（无需单独注册 Tailscale 账号）

### 步骤 3：查看本机 Tailscale IP

打开 **PowerShell** 或 **命令提示符**，执行：

```powershell
tailscale ip -4
```

输出类似（一串 `100.x.x.x` 的地址）：

```
100.64.10.20
```

> 也可以右键系统托盘的 Tailscale 图标查看 IP。

### 步骤 4：查看本机 Tailscale 域名

执行：

```powershell
tailscale status
```

输出示例：

```
100.64.10.20  your-pc-name  your-email@gmail.com  windows  -
```

本机的 Tailscale 域名格式为 `<机器名>.<tailnet名>.ts.net`，也可以在管理后台 https://login.tailscale.com/admin/machines 看到。

### 步骤 5：记录关键信息

请把以下两个值记录下来，后续手机端验证要用：

```
Tailscale IP:   100.64.10.20      （替换为你的实际值）
Tailscale 域名: your-pc-name.ts.net （替换为你的实际值）
```

---

## 三、手机端安装（Android）

### 步骤 1：下载安装

二选一：

- **方式 A（推荐）**：在 Google Play 搜索 "Tailscale" 并安装
- **方式 B**：从官网下载 APK 直接安装：https://tailscale.com/download/android

### 步骤 2：登录同一账号

1. 打开手机上的 Tailscale 应用
2. 点击 `Sign in`
3. **使用与 PC 端相同的账号登录**（这是组网成功的关键）

### 步骤 3：开启 VPN 权限

1. 系统会弹出"是否允许 Tailscale 设置 VPN 连接"的提示
2. 点击 **允许 / 确定**
3. 此时手机顶部状态栏会出现一个 VPN 钥匙图标 🔑

### 步骤 4：确认手机获得 Tailscale IP

在 Tailscale 应用主界面，可以看到本机的 Tailscale IP（同样形如 `100.x.x.x`）。

也可以在 PC 端执行 `tailscale status`，应该能在列表中看到手机设备。

---

## 四、验证连接

### 步骤 1：手机访问 PC 的 API

确保 PC 上的 Open Notebook API 已经启动（监听 5055 端口）。

在手机浏览器中访问（把 IP 换成你 PC 的 Tailscale IP）：

```
http://100.64.10.20:5055/health
```

**预期返回**：

```json
{"status":"healthy"}
```

看到这个返回，说明 Tailscale 组网成功！

### 步骤 2：如果访问失败，按以下顺序排查

#### 排查 1：检查 PC 上 API 是否运行

在 PC 上执行：

```powershell
netstat -aon | findstr :5055
```

应该能看到类似下面的输出（表示有进程在监听 5055 端口）：

```
TCP    0.0.0.0:5055     0.0.0.0:0     LISTENING     12345
```

如果没有输出，说明 API 没启动，请先启动 Open Notebook API。

#### 排查 2：检查 PC 防火墙

Windows 防火墙可能阻止了 Tailscale 网卡访问 5055 端口。

临时关闭防火墙测试（仅用于排查，确认后请改用放行规则）：

1. 控制面板 → 系统和安全 → Windows Defender 防火墙 → 启用或关闭防火墙
2. 临时关闭专用网络防火墙，再试手机访问

如果关闭防火墙后能访问，说明是防火墙拦截。建议为 5055 端口添加入站规则放行（允许 Tailscale 网卡 `Tailscale` 访问）。

#### 排查 3：检查 Tailscale 是否在线

在 PC 和手机上分别执行 / 查看：

```powershell
tailscale status
```

- 确认两台设备都显示 `active` 或 `idle`（在线状态）
- 如果显示 `offline`，点击 Tailscale 应用中的连接按钮重新上线

---

## 五、配置 ACL（可选，增强安全）

Tailscale 默认 ACL 允许你的所有设备之间互通。为了更安全，可以限制为**仅允许手机访问 PC 的 5055 端口**，其他端口一律拒绝。

### 步骤 1：打开 ACL 管理页面

访问：https://login.tailscale.com/admin/acls

### 步骤 2：为设备打标签

在管理后台 https://login.tailscale.com/admin/machines：

- 找到你的 PC → 右侧 `⋮` → `Edit ACL tags` → 添加 `tag:pc`
- 找到你的手机 → 右侧 `⋮` → `Edit ACL tags` → 添加 `tag:phone`

> 注意：打标签需要先在 ACL 中声明 `tagOwners`（见下方配置）。

### 步骤 3：修改 ACL 规则

把 ACL 编辑器中的内容替换为（把"你的邮箱"换成你登录 Tailscale 的邮箱）：

```json
{
  "tagOwners": {
    "tag:phone": ["你的邮箱@gmail.com"],
    "tag:pc": ["你的邮箱@gmail.com"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:phone"],
      "dst": ["tag:pc:5055"]
    }
  ]
}
```

点击 **Save** 保存。

### 规则说明

- `tagOwners`：声明谁有权限给设备打这个标签（这里是你自己的邮箱）
- `acls`：只允许 `tag:phone`（手机）访问 `tag:pc`（PC）的 5055 端口
- 其他所有访问（如手机访问 PC 的其他端口）都会被拒绝

---

## 六、常见问题

### Q1：PC 重启后 Tailscale 没有自动启动？

**A**：设置 Tailscale 开机自启：

1. 右键系统托盘的 Tailscale 图标
2. 选择 `Preferences`
3. 勾选 `Run on startup`（开机自启）

### Q2：手机在 4G 网络下连不上 PC？

**A**：Tailscale 支持 NAT 穿透，4G 网络理论上可用。请检查：

1. 手机系统是否限制了 Tailscale VPN 的后台运行（部分国产手机有"省电"策略会杀后台 VPN）
   - 在手机设置 → 电池 → 找到 Tailscale → 允许后台运行
2. 手机 Tailscale 应用是否处于连接状态（顶部应有 VPN 钥匙图标）
3. 信号是否正常，尝试切换 4G/Wi-Fi 再试

### Q3：访问速度很慢？

**A**：Tailscale 默认尝试点对点（P2P）直连，速度最快。如果 NAT 穿透失败，会走中继服务器（DERP），速度较慢。

排查方法：

1. 在 PC 执行 `tailscale status`，查看连接类型
2. 或访问管理后台 https://login.tailscale.com/admin/machines 查看连接详情
3. 如果显示 `relay "xxx"`，说明走的是中继，可以尝试：
   - 在路由器上开启 UPnP（有助于 NAT 穿透）
   - 换一个网络环境再试

### Q4：手机访问返回 403 或连接被拒绝？

**A**：通常是 ACL 规则或 API 本身的鉴权问题：

1. 检查 ACL 是否配置过严（参考第五节）
2. 检查 Open Notebook API 是否设置了访问密码（`OPEN_NOTEBOOK_PASSWORD`），手机端请求时需要带上

### Q5：如何卸载 Tailscale？

**A**：

1. 控制面板 → 程序和功能 → 找到 Tailscale → 卸载
2. 在管理后台 https://login.tailscale.com/admin/machines 删除对应设备
