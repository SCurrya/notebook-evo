# Cloudflare Tunnel 配置指南

> 本指南面向零基础用户，帮助你在没有公网 IP、不开放路由器端口的情况下，通过 Cloudflare Tunnel 把 PC 上的 Open Notebook API（端口 5055）暴露到公网，作为 Tailscale 不可用时的备用外网通道。

---

## 一、前置说明

### Cloudflare Tunnel 是什么

Cloudflare Tunnel（原名 Argo Tunnel）是 Cloudflare 提供的反向代理隧道服务。你在 PC 上运行一个 `cloudflared` 客户端，它会主动连接 Cloudflare 边缘节点，把外部请求反向转发到你本地的服务。

### 为什么用它

| 优势 | 说明 |
| --- | --- |
| 无需公网 IP | 家庭宽带没有公网 IP 也能用 |
| 无需开放路由器端口 | 不做端口映射，家庭网络更安全 |
| 自动 HTTPS | Cloudflare 自动签发并续期 SSL 证书 |
| 备用通道 | 作为 Tailscale 的备用方案，当 Tailscale 不可用时使用 |

### 限制（重要）

- **临时隧道**：域名每次重启 `cloudflared` 都会变，适合临时测试
- **固定域名**：需要注册 Cloudflare 账号，并且拥有一个域名（需把域名 NS 改到 Cloudflare）

### 本指南约定的 cloudflared 路径

本项目已经把 `cloudflared.exe` 下载并放在：

```
e:\notebook\downloads\cloudflared.exe
```

所有命令默认使用此路径。**无需**放到 `C:\Tools\`、`C:\Windows\System32\` 等系统目录，避免权限问题。

---

## 二、方式一：临时隧道（最快，无需账号）

适合快速测试，**不需要注册任何 Cloudflare 账号**。每次重启 `cloudflared` 域名都会变（形如 `https://xxxx.trycloudflare.com`），但开箱即用，最快验证通路。

### 步骤 1：确认 cloudflared.exe 已就位

文件路径：

```
e:\notebook\downloads\cloudflared.exe
```

可以用以下命令验证可执行性：

```powershell
e:\notebook\downloads\cloudflared.exe --version
```

应输出类似：

```
cloudflared version 2026.6.0 (built 2026-06-08T11:16 UTC)
```

### 步骤 2：启动临时隧道

打开 **PowerShell** 或 **命令提示符（cmd）**，执行：

```powershell
e:\notebook\downloads\cloudflared.exe tunnel --url http://localhost:5055
```

> 注意：
> - `http://localhost:5055` 是 Open Notebook API 的本地监听地址，请按你的实际端口修改
> - **必须先启动 Open Notebook API**，否则 cloudflared 连不上本地服务

### 步骤 3：获取临时域名

命令执行后，终端会输出一段日志，找到类似下面这一行（有一根 `|` 框）：

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://xxxx-yyy-zzz.trycloudflare.com                                                     |
+--------------------------------------------------------------------------------------------+
```

其中 `https://xxxx-yyy-zzz.trycloudflare.com` 就是你的临时公网访问地址（每次启动都不一样）。

### 步骤 4：把临时域名写入 `.env`（推荐）

把这个 `https://xxxx-yyy-zzz.trycloudflare.com` 域名填到 Open Notebook 的环境变量里，让 API 自动启用 Cloudflare 端点。

编辑 `e:\notebook\open-notebook\.env`：

```ini
CLOUDFLARE_DOMAIN=https://xxxx-yyy-zzz.trycloudflare.com
```

> 说明：
> - `CLOUDFLARE_DOMAIN` 带 `https://` 前缀（Open Notebook 内部直接拼到 API 基址）
> - 留空表示未启用 Cloudflare 端点
> - 临时域名会变，**每次重启 cloudflared 都要回来改这一行**；如果不想频繁改，请改用方式二的固定域名

### 步骤 5：测试访问

在手机上**关闭 Tailscale**、切换到 4G 移动网络，浏览器访问：

```
https://xxxx-yyy-zzz.trycloudflare.com/health
```

应返回：

```json
{"status":"healthy"}
```

### 注意事项

- **关闭终端 = 隧道停止**：这个命令是前台运行的，关闭终端窗口隧道就断了
- **重启后域名会变**：每次重新执行命令，都会分配一个新的临时域名，需要重新填到 `.env` 和手机里
- 适合临时调试或短期使用，长期使用建议用方式二

---

## 三、方式二：固定域名（需 Cloudflare 账号 + 域名）

适合长期使用，域名固定不变，可设为开机自启。

### 步骤 1：注册 Cloudflare 账号（免费）

访问：https://dash.cloudflare.com/sign-up

用邮箱注册一个账号即可，完全免费。

### 步骤 2：添加一个域名到 Cloudflare

1. 登录 Cloudflare 控制台
2. 点击 `Add a Site`（添加站点）
3. 输入你拥有的域名（例如 `example.com`）
4. 选择 **Free** 免费套餐
5. Cloudflare 会给你两个 NS 服务器地址，例如：
   ```
   ns1.cloudflare.com
   ns2.cloudflare.com
   ```
6. 去你的**域名注册商**（如阿里云、GoDaddy、Namecheap 等）后台，把域名的 NS 记录改成 Cloudflare 提供的这两个
7. 等待 NS 生效（通常几分钟到几小时，最长 24 小时），Cloudflare 控制台会显示域名状态为 `Active`

### 步骤 3：登录 cloudflared

在 PC 上执行：

```powershell
e:\notebook\downloads\cloudflared.exe tunnel login
```

1. 命令会自动打开浏览器
2. 选择你刚才添加到 Cloudflare 的域名
3. 点击 `Authorize`
4. 授权成功后，PC 上会生成一个 `cert.pem` 文件，路径通常在：
   ```
   C:\Users\<你的用户名>\.cloudflared\cert.pem
   ```

### 步骤 4：创建隧道

执行：

```powershell
e:\notebook\downloads\cloudflared.exe tunnel create open-notebook
```

输出示例：

```
Created tunnel open-notebook with id 12345678-90ab-cdef-1234-567890abcdef
```

**记下这个隧道 ID**（`12345678-90ab-cdef-1234-567890abcdef`），下一步要用。

同时会在 `C:\Users\<你的用户名>\.cloudflared\` 目录下生成一个凭据文件：

```
<隧道ID>.json
```

例如：`12345678-90ab-cdef-1234-567890abcdef.json`

### 步骤 5：配置隧道

在 `C:\Users\<你的用户名>\.cloudflared\` 目录下，新建一个文本文件，命名为 `config.yml`，内容如下（把 `<隧道ID>` 和 `<你的用户名>` 和域名替换成你的实际值）：

```yaml
tunnel: <隧道ID>
credentials-file: C:\Users\<你的用户名>\.cloudflared\<隧道ID>.json

ingress:
  - hostname: notebook.你的域名.com
    service: http://localhost:5055
  - service: http_status:404
```

**示例**（假设隧道 ID 是 `12345678-90ab-cdef-1234-567890abcdef`，用户名是 `zhangsan`，域名是 `example.com`）：

```yaml
tunnel: 12345678-90ab-cdef-1234-567890abcdef
credentials-file: C:\Users\zhangsan\.cloudflared\12345678-90ab-cdef-1234-567890abcdef.json

ingress:
  - hostname: notebook.example.com
    service: http://localhost:5055
  - service: http_status:404
```

> 说明：
> - `tunnel`：隧道 ID
> - `credentials-file`：上一步生成的凭据文件路径
> - `ingress`：路由规则，把 `notebook.example.com` 的请求转发到本地 5055 端口；其他请求返回 404

### 步骤 6：添加 DNS 记录

执行（把 `open-notebook` 换成你的隧道名，`notebook.你的域名.com` 换成你的实际域名）：

```powershell
e:\notebook\downloads\cloudflared.exe tunnel route dns open-notebook notebook.你的域名.com
```

这条命令会自动在 Cloudflare DNS 中为 `notebook.你的域名.com` 添加一条 CNAME 记录，指向你的隧道。

### 步骤 7：测试隧道

执行：

```powershell
e:\notebook\downloads\cloudflared.exe tunnel run open-notebook
```

看到类似下面的日志，说明隧道已启动：

```
INF Tunnel tunnel started
INF Connection registered
```

此时用任意设备访问 `https://notebook.你的域名.com/health`，应返回：

```json
{"status":"healthy"}
```

### 步骤 8：把固定域名写入 `.env`

编辑 `e:\notebook\open-notebook\.env`：

```ini
CLOUDFLARE_DOMAIN=https://notebook.example.com
```

> 注意要带 `https://` 前缀。重启 Open Notebook API 后，Cloudflare 端点会作为可选访问源生效。

### 步骤 9：设为开机自启（需管理员权限）

为了不用每次开机都手动启动，可以把 cloudflared 注册为 Windows 服务：

1. **以管理员身份**打开 PowerShell 或命令提示符（开始菜单搜索 → 右键 → 以管理员身份运行）
2. 执行：

```powershell
e:\notebook\downloads\cloudflared.exe service install
```

3. 安装后，服务名为 `Cloudflared`，启动类型默认为自动（开机自启）
4. 可以在 `services.msc`（服务管理器）中查看和管理这个服务

> 注意：注册为服务后，`config.yml` 必须放在 `C:\Windows\System32\config\systemprofile\.cloudflared\config.yml`，或者用绝对路径指定。如果服务启动失败，请检查路径问题。

---

## 四、加入系统 PATH（可选）

如果你不想每次都打 `e:\notebook\downloads\cloudflared.exe` 这一长串路径，可以把 cloudflared 所在目录加入系统 PATH。

### 方式 A：手动设置（推荐）

1. `Win + R` → 输入 `sysdm.cpl` → 回车
2. 切到 **高级** 选项卡 → 点击 **环境变量**
3. 在 **系统变量** 里找到 `Path`，双击打开
4. 点 **新建**，输入：
   ```
   e:\notebook\downloads
   ```
5. 一路 **确定** 保存
6. **重开一个** PowerShell/cmd 窗口（环境变量要新进程才生效）
7. 验证：

```powershell
cloudflared.exe --version
```

应直接输出版本号（无需带路径）。

### 方式 B：PowerShell 临时会话设置（仅当前窗口生效）

```powershell
$env:Path += ";e:\notebook\downloads"
cloudflared.exe --version
```

这种方式只对当前终端有效，关掉就失效，仅适合临时测试。

### 方式 C：复制到已有 PATH 目录（不推荐）

```powershell
# 把 cloudflared.exe 复制到已经在 PATH 里的目录，例如 C:\Windows
# 注意：写到 C:\Windows 需要管理员权限，而且混进系统目录不便管理，不推荐
```

> **不推荐**把 `cloudflared.exe` 复制到 `C:\Windows\`、`C:\Windows\System32\` 等系统目录。保留在 `e:\notebook\downloads\` 既方便管理，也能跟随项目一起备份。

---

## 五、验证

1. 在手机上**关闭 Tailscale**（断开 Tailscale VPN）
2. 切换到 **4G 移动网络**（确保不走家庭 Wi-Fi）
3. 用手机浏览器访问：

```
https://<你的隧道域名>/health
```

例如：

```
https://notebook.example.com/health
```

**预期返回**：

```json
{"status":"healthy"}
```

看到这个返回，说明 Cloudflare Tunnel 配置成功，可以作为 Tailscale 的备用外网通道使用了！

---

## 六、安全建议

### 临时隧道

- 临时隧道域名是**公开可猜到的**，任何人知道这个域名都能访问你的 API
- **务必**在 Open Notebook 中设置访问密码：环境变量 `OPEN_NOTEBOOK_PASSWORD`
- 不要把临时域名分享到公开场合

### 固定域名

- 固定域名同样公开，知道域名的人都能访问
- 强烈建议启用 **Cloudflare Access**（零信任认证）做额外保护：
  1. 在 Cloudflare 控制台进入 `Zero Trust` → `Access` → `Applications`
  2. 添加一个 Application，域名填 `notebook.你的域名.com`
  3. 配置策略：只允许你的邮箱访问
  4. 之后访问该域名会先跳转到 Cloudflare 登录页，验证邮箱后才能访问 API
- 同时仍建议设置 `OPEN_NOTEBOOK_PASSWORD` 作为第二层防护

---

## 七、常见问题

### Q1：临时隧道域名变了怎么办？

**A**：临时隧道每次重启 `cloudflared` 都会分配新域名。解决方法：

1. 重新执行启动命令：
   ```powershell
   e:\notebook\downloads\cloudflared.exe tunnel --url http://localhost:5055
   ```
2. 从终端输出中复制新的 `https://xxxx-yyy-zzz.trycloudflare.com` 域名
3. 更新 `e:\notebook\open-notebook\.env` 的 `CLOUDFLARE_DOMAIN=https://xxxx-yyy-zzz.trycloudflare.com`
4. 重启 Open Notebook API

> 如果不想频繁更换域名，请使用**方式二：固定域名**。

### Q2：隧道连不上 / 访问报错 502？

**A**：按以下顺序排查：

1. **检查 PC 上 API 是否运行**：
   ```powershell
   netstat -aon | findstr :5055
   ```
   应有 `LISTENING` 输出。如果没有，先启动 Open Notebook API。

2. **检查 cloudflared 是否在运行**：
   - 临时隧道：检查命令提示符窗口是否还开着
   - 固定域名（服务模式）：在 `services.msc` 中查看 `Cloudflared` 服务状态是否为"正在运行"

3. **检查 config.yml 配置**：
   - 隧道 ID 是否正确
   - `credentials-file` 路径是否正确（注意用户名和文件名）
   - `hostname` 是否和 DNS 记录一致

4. **检查 DNS 记录**：在 Cloudflare 控制台 → DNS 中，确认 `notebook.你的域名.com` 的 CNAME 记录存在且指向 `<隧道ID>.cfargotunnel.com`

### Q3：访问速度慢？

**A**：Cloudflare 免费版没有速度限制，慢通常是以下原因：

1. **PC 上行带宽不足**：家庭宽带上行通常比下行小很多（如 100M 下行 / 30M 上行），上传大文件时会慢
2. **API 处理慢**：如果 API 本身响应慢（如加载大模型），与隧道无关，请优化 API 性能
3. **网络抖动**：尝试切换网络或稍后再试

### Q4：cloudflared 提示"command not found"？

**A**：说明 `cloudflared.exe` 不在系统 PATH 中。两种解决方法：

- **方法 A（推荐）**：用完整路径调用，例如 `e:\notebook\downloads\cloudflared.exe tunnel ...`
- **方法 B**：把 `e:\notebook\downloads\` 加入系统 PATH 环境变量（参见第四节），然后重开终端

### Q5：服务模式启动失败？

**A**：常见原因：

1. **没有用管理员权限**：必须以管理员身份运行 PowerShell/命令提示符
2. **config.yml 路径问题**：服务模式下，cloudflared 以 SYSTEM 账户运行，默认读取路径是：
   ```
   C:\Windows\System32\config\systemprofile\.cloudflared\config.yml
   ```
   把 `config.yml` 和 `<隧道ID>.json` 复制到这个目录下即可。
3. **凭据文件路径错误**：服务模式下 `credentials-file` 路径要改成 SYSTEM 账户能访问的路径，例如：
   ```yaml
   credentials-file: C:\Windows\System32\config\systemprofile\.cloudflared\<隧道ID>.json
   ```

### Q6：如何卸载 cloudflared 服务？

**A**：以管理员身份执行：

```powershell
e:\notebook\downloads\cloudflared.exe service uninstall
```

### Q7：.env 里的 CLOUDFLARE_DOMAIN 怎么填才对？

**A**：

- 临时隧道（`https://xxxx-yyy-zzz.trycloudflare.com`）：
  ```ini
  CLOUDFLARE_DOMAIN=https://xxxx-yyy-zzz.trycloudflare.com
  ```
- 固定域名（`notebook.example.com`）：
  ```ini
  CLOUDFLARE_DOMAIN=https://notebook.example.com
  ```
- 不使用时留空：
  ```ini
  CLOUDFLARE_DOMAIN=
  ```

注意：
- 必须带 `https://` 前缀（不要只写域名）
- 不要带尾部斜杠
- 改完 `.env` 要重启 Open Notebook API 才生效
