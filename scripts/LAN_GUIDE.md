# 局域网体验指南（无需 Tailscale/Cloudflare）

## 适用场景
- 手机和 PC 连接到同一个 WiFi
- 想先体验同步效果再决定是否装 Tailscale
- 测试用，5 分钟搞定

## PC 端准备

### 1. 确认 PC 内网 IP
PC 的内网 IP 是：**192.168.5.22**（WLAN 接口）

如果 IP 经常变，可在路由器上给 PC 设置静态 IP，或在 Windows 设置 → 网络 → 当前连接 → IP 分配改为"手动"。

### 2. 防火墙放行
确保 3000（前端）和 5055（API）端口对局域网开放：

打开 PowerShell（管理员）执行：
```powershell
New-NetFirewallRule -DisplayName "Open Notebook Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "Open Notebook API" -Direction Inbound -LocalPort 5055 -Protocol TCP -Action Allow -Profile Private
```

如果上面命令报错，先执行 `Set-NetFirewallProfile -Profile Private -Enabled True`。

### 3. 确认服务在跑
浏览器在 PC 上访问：
- http://localhost:3000（前端）
- http://localhost:5055/docs（API 文档）

两者都能开就 OK。

## 手机端体验

### 1. 确保手机连同一 WiFi

### 2. 手机浏览器访问
- 前端：http://192.168.5.22:3000
- API 测试：http://192.168.5.22:5055/health（应该返回 {"status":"ok"}）

### 3. 测试同步
- 在 PC 端网页里新建一个笔记本
- 手机浏览器刷新 http://192.168.5.22:3000
- 应该能看到刚才创建的笔记本

### 4. 测试创建 API Key
- 进入 Settings → API Keys → 创建一个新 Key
- 在手机端用某个 API 调用验证（参考 API 文档 http://192.168.5.22:5055/docs）

## 限制
- ❌ 手机离开这个 WiFi 就连不上
- ❌ PC 内网 IP 变化后手机要重新填
- ❌ 真实场景建议改用 Tailscale（参见 setup-tailscale.md）

## 完成后建议
局域网跑通后，下一步可以装 Tailscale（云安装包已下好）：
- 双击 `e:\notebook\downloads\tailscale-setup-latest-amd64.msi`
- 系统托盘右键 → Log in → 用 Google/GitHub 账号
- 详见 `e:\notebook\scripts\install-tailscale.md`

## 常见问题
| 问题 | 解决 |
|------|------|
| 手机连不上 | 确认手机和 PC 同一 WiFi，PC 防火墙未拦截 |
| 显示连接被拒 | 防火墙未放行，执行上面的 New-NetFirewallRule 命令 |
| 内网 IP 不对 | Win+R → cmd → 输入 ipconfig，看 IPv4 地址 |
| 前端开 3000 但手机看到 404 | 可能 PC 端服务在跑但绑定到 127.0.0.1，需要确认服务监听 0.0.0.0 |
