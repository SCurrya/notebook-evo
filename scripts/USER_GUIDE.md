# Open Notebook 移动版用户使用手册

> 本手册面向 Open Notebook 移动版用户，帮助你完成安装、配置和日常使用。所有步骤均经过实测，按顺序操作即可。

---

## 1. 概述

### Open Notebook 移动版是什么

Open Notebook 移动版是 Open Notebook 笔记本应用的 Android 客户端。它让你可以在手机上随时随地浏览、编辑自己的笔记本，与 PC 端共享同一份数据。

### 与 PC 网页版的关系

- **数据同步**：手机端和 PC 端连接的是同一个后端数据库（SurrealDB），任何一端的修改都会实时反映到另一端。
- **功能一致**：移动版保留了 PC 网页版的核心功能（浏览、搜索、编辑等），并针对小屏幕做了适配。
- **架构关系**：PC 端运行 Next.js 前端 + FastAPI + SurrealDB；移动端通过 Capacitor 把网页打包成 Android 应用，通过网络访问 PC 端的 API。

### 系统要求

| 项目 | 要求 |
| --- | --- |
| 手机系统 | Android 8.0（API 26）及以上 |
| PC 端 | 已安装并运行 Open Notebook |
| 网络 | 手机和 PC 处于同一 Tailscale 网络，或通过 Cloudflare Tunnel 连通 |

---

## 2. 首次安装

### 2.1 PC 端准备

在配置手机端之前，请先确保 PC 端服务正常。

1. **启动 Open Notebook**
   - 双击执行 `E:\notebook\start-open-notebook.bat`
   - 等待命令行窗口出现 "服务已启动" 之类的提示

2. **确认 API 可访问**
   - 打开浏览器，访问 `http://127.0.0.1:5055/health`
   - 正常情况下应返回：`{"status":"healthy"}`
   - 如果无法访问，请检查 PC 端是否启动成功

3. **确认认证密码已设置**
   - 打开 `E:\notebook\.env` 文件
   - 确认存在 `OPEN_NOTEBOOK_PASSWORD=你的密码` 这一行
   - 此密码将用于移动端登录认证，请记下来

### 2.2 安装 Tailscale（推荐）

Tailscale 是手机连接 PC 的首选通道，加密直连、速度快、不暴露公网端口。

1. **PC 端安装配置**
   - 参考 `scripts/setup-tailscale.md` 完成安装和登录

2. **手机端安装**
   - Google Play 搜索 "Tailscale" 下载安装
   - 或从 Tailscale 官网下载 APK：https://tailscale.com/download/android

3. **两端登录同一账号**
   - 手机端打开 Tailscale 应用
   - 使用与 PC 端相同的账号登录（支持 Google、Microsoft、GitHub 等）

4. **记录 PC 的 Tailscale IP**
   - 在 PC 上执行 `tailscale status`
   - 找到本机对应的 IP（形如 `100.x.x.x`）
   - 把这个 IP 记下来，后面配置手机端要用

### 2.3 安装 Android 应用

#### 方式一：通过 ADB 安装（推荐）

1. **构建 APK**
   - 在 PC 上执行 `scripts\build-android.bat`
   - 构建完成后，APK 文件位于 `e:\notebook\android\app\build\outputs\apk\release\app-release.apk`（具体路径以脚本输出为准）

2. **手机开启 USB 调试**
   - 进入手机 "设置 → 关于手机"
   - 连续点击 "版本号" 7 次，会提示 "您已处于开发者模式"
   - 返回 "设置"，找到 "开发者选项"（部分机型在 "系统" 或 "其他设置" 下）
   - 打开 "USB 调试" 开关

3. **USB 连接 PC**
   - 用数据线连接手机和 PC
   - 手机弹窗选择 "允许 USB 调试"

4. **安装 APK**
   - 在 PC 上执行：`adb install <APK路径>`
   - 例如：`adb install e:\notebook\android\app\build\outputs\apk\release\app-release.apk`
   - 看到 "Success" 字样即安装成功

#### 方式二：手动安装

1. 把构建好的 APK 文件传到手机（微信、QQ、U 盘均可）
2. 在手机文件管理器中找到该 APK，点击安装
3. 如果提示 "未知来源"，按引导允许安装即可

---

## 3. 配置移动应用

### 3.1 设置 API 地址

应用启动时会按以下优先级**自动尝试**连接 API：

1. `http://10.0.2.2:5055`（仅 Android 模拟器可用，对应宿主机）
2. `http://localhost:5055`（仅模拟器可用）
3. Tailscale 域名 / IP（需在应用设置中手动配置）
4. Cloudflare 域名（需在应用设置中手动配置）

> 真机使用时，前两个地址无法连通，必须配置 Tailscale 或 Cloudflare 通道。

### 3.2 设置认证密码

移动端访问 API 需要密码认证，密码即 PC 端 `.env` 中的 `OPEN_NOTEBOOK_PASSWORD`。

**两种设置方式：**

- **方式一（首次启动）**：应用首次启动会进入登录页，直接在输入框中填写密码即可。
- **方式二（应用设置）**：进入应用 "设置" 页面，找到 "API 密码" 项，填入密码并保存。

### 3.3 配置 Tailscale 域名

1. 在 PC 上打开命令行，执行：
   ```
   tailscale status
   ```
2. 在输出列表中找到 PC 这一行，记录其 Tailscale IP（形如 `100.x.x.x`）或 MagicDNS 域名（形如 `pc-name.tailnet-xxxx.ts.net`）。
3. 在手机上打开 Open Notebook 应用，进入 "设置" 页面。
4. 找到 "Tailscale 地址" 输入框，填入上一步获取的 IP 或域名（**不要带 `http://` 前缀**）。
5. 点击 "保存"，应用会自动通过 Tailscale 连接 PC 端 API。
6. 连接成功后，顶部状态栏会显示 "已连接"。

### 3.4 配置 Cloudflare 域名（可选）

Cloudflare Tunnel 作为 Tailscale 的备用通道，在 Tailscale 不可用时使用。

1. 在 PC 上参考 `scripts/setup-cloudflare-tunnel.md` 启动 Cloudflare Tunnel。
2. 启动后命令行会输出一个形如 `https://xxx-yyy-zzz.trycloudflare.com` 的临时域名，把它记下来。
3. 在手机上打开 Open Notebook 应用，进入 "设置" 页面。
4. 找到 "Cloudflare 地址" 输入框，填入上一步获取的域名（**不要带 `https://` 前缀**）。
5. 点击 "保存"。
6. 当 Tailscale 连接失败时，应用会自动切换到 Cloudflare 通道。

> 注意：临时隧道每次重启 `cloudflared` 域名都会变，需要重新配置。

---

## 4. 日常使用

### 4.1 浏览笔记本

- **打开应用**：启动后自动加载笔记本列表。
- **查看内容**：点击任意笔记本卡片即可进入详情页。
- **搜索**：在列表页顶部搜索框输入关键词，支持按标题和内容搜索。
- **筛选**：通过列表页的筛选按钮，可按标签、时间范围等条件筛选笔记本。

### 4.2 离线模式

当手机断网或无法连接 PC 端时，应用会自动进入离线模式。

- **可做的事**：浏览最近一次成功同步的笔记本内容（只读）。
- **不可做的事**：所有编辑按钮会置灰，无法新建、修改、删除笔记。
- **自动恢复**：网络恢复后，应用会自动重连并退出离线模式，无需手动操作。

> 离线缓存仅包含最近一次成功同步的数据，并非完整数据库。

### 4.3 数据同步

- 手机端和 PC 端**共享同一个数据库**，不存在 "上传/下载" 的概念。
- 任何一端创建、修改、删除数据，另一端**刷新后立即可见**。
- 通过 Tailscale 直连时，同步是**实时**的，延迟通常在毫秒级。
- 通过 Cloudflare Tunnel 时，同步会有少量额外延迟（经 Cloudflare 中转）。

---

## 5. 故障排查

### 问题：应用启动后显示 "无法连接"

按以下顺序排查：

1. **检查 PC 端服务**：在 PC 浏览器访问 `http://127.0.0.1:5055/health`，确认返回 `{"status":"healthy"}`。如果无法访问，重启 `start-open-notebook.bat`。
2. **检查 Tailscale 状态**：手机和 PC 两端的 Tailscale 应用都要显示 "已连接"。在 PC 上执行 `tailscale status` 确认手机出现在设备列表中。
3. **检查 API 密码**：进入应用 "设置" 页面，确认密码与 PC 端 `.env` 中的 `OPEN_NOTEBOOK_PASSWORD` 完全一致。
4. **切换通道**：如果 Tailscale 始终连不上，尝试在应用设置中启用 Cloudflare 通道。

### 问题：Tailscale 连接慢

1. **检查是否走了 DERP 中继**：登录 Tailscale 管理后台（https://login.tailscale.com/admin/machines），查看 PC 和手机之间的连接路径。如果显示 "DERP" 而不是 "direct"，说明走了中继，速度会变慢。
2. **确保网络支持 UDP**：Tailscale 直连依赖 UDP 协议。部分公司网络或公共 WiFi 会屏蔽 UDP，可尝试切换到家庭网络或 4G/5G 移动网络。
3. **切换网络**：从 WiFi 切到 4G，或反之，有时能建立直连。

### 问题：Cloudflare 域名变了

临时隧道每次重启 `cloudflared` 都会分配新域名。

1. 在 PC 上重新启动 cloudflared（参考 `scripts/setup-cloudflare-tunnel.md`）。
2. 从命令行输出中复制新的 `*.trycloudflare.com` 域名。
3. 在手机应用 "设置" 中更新 "Cloudflare 地址"。
4. 保存后重新连接。

### 问题：离线模式数据不完整

- 离线缓存只保存**最近一次成功同步**时的数据快照，并非完整数据库。
- 联网后下拉刷新笔记本列表，应用会拉取最新数据并更新本地缓存。
- 如果长期未联网，缓存可能过期，联网刷新一次即可恢复完整。

### 问题：APK 安装失败

1. **检查 "未知来源" 权限**：手机 "设置 → 应用管理 → 特殊访问权限 → 安装未知应用"，允许文件管理器或浏览器安装应用。
2. **检查 APK 完整性**：完整的 APK 文件大小应大于 5MB。如果文件明显偏小，可能是下载/传输中断，重新构建或传输一次。
3. **使用 ADB 重装**：USB 连接手机后执行 `adb install -r <APK路径>`，`-r` 参数表示覆盖安装。
4. **检查架构兼容性**：确认 APK 构建架构与手机 CPU 匹配（一般 arm64-v8a 适配绝大多数现代手机）。

---

## 6. 安全注意事项

- **不要分享密码**：`OPEN_NOTEBOOK_PASSWORD` 是访问你所有笔记本的钥匙，切勿告知他人或在公开场合记录。
- **不要公开 Cloudflare 域名**：临时隧道域名任何人知道都能访问你的 API，不要发到群里或社交平台。
- **定期检查 Tailscale 设备列表**：登录 https://login.tailscale.com/admin/machines 查看已接入设备，发现不认识的设备及时移除。
- **PC 必须开机**：这是自托管方案的固有限制——PC 不开机时，手机无法访问任何数据（除了离线缓存）。如需 7×24 访问，请考虑把 Open Notebook 部署到一台常开的家用服务器或 NAS 上。
- **及时退出账号**：在公共设备上登录 Tailscale 后，使用完毕记得退出。

---

## 附录：常用命令速查

| 命令 | 作用 |
| --- | --- |
| `E:\notebook\start-open-notebook.bat` | 启动 PC 端 Open Notebook |
| `scripts\build-android.bat` | 构建 Android APK |
| `tailscale status` | 查看 Tailscale 连接状态和设备 IP |
| `adb install <APK路径>` | 通过 USB 安装 APK 到手机 |
| `adb install -r <APK路径>` | 覆盖安装 APK |

如遇本手册未覆盖的问题，请先查看 `scripts/setup-tailscale.md` 和 `scripts/setup-cloudflare-tunnel.md`，或联系开发者。

---

## 附录 B：`build-android.bat` 一键构建脚本使用说明

### B.1 脚本作用

`scripts\build-android.bat` 是 Windows 平台下的一键构建脚本，按顺序完成 4 个步骤：

| 步骤 | 任务 | 关键命令 |
| --- | --- | --- |
| 1/4 | 环境检查 | 校验 Android SDK (`C:\Tools\android-sdk`) 与 JDK (`E:\C\Java\jdk-18.0.1.1`) 是否就位，并把它们加入 `PATH` |
| 2/4 | 构建 Next.js 静态导出 | 删除旧的 `.next` 与 `out`，执行 `npm run build:mobile` |
| 3/4 | 同步到 Android | 在 `mobile-app` 目录执行 `npx cap sync android` |
| 4/4 | 构建 APK | 进入 `mobile-app\android` 并执行 `gradlew.bat assembleDebug` |

### B.2 运行环境要求

| 项目 | 路径 / 版本 |
| --- | --- |
| JDK | `E:\C\Java\jdk-18.0.1.1`（脚本会校验 `bin\java.exe`） |
| Android SDK | `C:\Tools\android-sdk`，需包含 `platform-tools`、`platforms;android-34`、`build-tools;34.0.0` |
| Capacitor Android 工程 | `E:\notebook\mobile-app\android`（已执行过 `npx cap add android`） |
| Node.js | 任意可用的 LTS 版本，能跑 `npm run build:mobile` 即可 |
| 系统 | Windows 10 / 11 + PowerShell 或 cmd |

### B.3 使用方法

1. 确认上述依赖已安装并位于脚本默认路径。
2. 打开资源管理器，进入 `E:\notebook\scripts\`。
3. 双击 `build-android.bat`（或在该目录的 PowerShell / cmd 中执行 `.\build-android.bat`）。
4. 等待脚本自动跑完 4 步；每步成功会打印 `[OK]` 风格的提示，失败会跳到对应错误处理并 `pause`。
5. 全部成功后，APK 位于：
   ```
   E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk
   ```
6. 在手机上安装：
   ```
   adb install -r "E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk"
   ```

### B.4 输出与错误码

脚本退出码含义：

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部步骤成功，APK 已生成 |
| 1 | 任意步骤失败（脚本会先打印中文错误原因，再 `pause`） |

脚本内置的错误标签：

- `:error_sdk` — Android SDK 路径不存在
- `:error_jdk` — JDK 路径不存在
- `:error_build` — `npm run build:mobile` 失败
- `:error_sync` — `npx cap sync android` 失败
- `:error_gradle` — `gradlew.bat assembleDebug` 失败

### B.5 常见问题

- **“'gradlew.bat' is not recognized”**：脚本执行到第 4 步时所在的 `E:\notebook\mobile-app\android` 目录缺失，请先运行 `cd /d E:\notebook\mobile-app && npx cap add android`。
- **“'build:mobile' 不是 npm script”**：需要保证 `E:\notebook\open-notebook\frontend\package.json` 里有 `build:mobile` 脚本（设置 `BUILD_TARGET=mobile`）。
- **首次运行下载 Gradle 慢**：`gradlew.bat assembleDebug` 第一次会从 `services.gradle.org` 下载 Gradle 发行包（视网络 5–15 分钟），后续会复用本地缓存。
- **改动了脚本里的路径**：如果实际 JDK / SDK 不在默认位置，编辑脚本顶部的 `set ANDROID_HOME=`、`set JAVA_HOME=` 两行即可，其他逻辑无需修改。

