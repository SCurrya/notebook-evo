# Open Notebook 项目全面总结与痛点分析报告

> 生成时间：2026-06-22  
> 目标读者：AI 代码助手（Codex / Claude / Cursor 等）  
> 用途：后续开发优化的上下文输入

---

## 一、项目背景与目标

### 1.1 项目定位

**Open Notebook**（v2.1.0，MIT 许可）是一个 **开源、隐私优先的 Google NotebookLM 替代品**，由 Luis Novo 开发。核心价值主张：

- **自托管**：数据完全由用户控制，无云端依赖
- **多模型 AI**：通过 Esperanto 库支持 18+ AI 提供商（OpenAI / Anthropic / Google / Ollama / Groq / Mistral / DeepSeek / xAI / OpenRouter 等）
- **多模态内容组织**：PDF、视频、音频、网页、Office 文档
- **专业播客生成**：1-4 说话人，自定义 Episode/Speaker Profile
- **全平台分发**：Docker / 源码 / Windows EXE / Android APK

### 1.2 当前分支的定制化目标

在原版基础上，当前工作分支额外实现了：
- **Windows 桌面 EXE 一键启动**（PyInstaller 单文件，内嵌 SurrealDB + FastAPI + 前端静态文件）
- **MoneyPrinterTurbo 视频生成集成**（一键启动 + 健康检查 + 任务轮询）
- **多智能体系统**（并行任务调度，build/test/research/coder/reviewer 类型）
- **内容生成矩阵**（PDF / PPT / 图片 / 博客 / 视频 5 大生成器）
- **全中文 UI**（14 种语言 i18n 基础设施 + 硬编码中文覆盖）
- **详细日志埋点**（`[PDF/PROCESS]` `[VIDEO/GEN]` `[AGENT/EXEC]` 等前缀）

---

## 二、核心功能模块

### 2.1 后端模块清单

#### 路由层（api/routers/，32 个路由文件）

| 分类 | 路由 | 功能 |
|------|------|------|
| **核心** | notebooks, sources, notes, chat, source_chat, search | 笔记本 CRUD、源上传/处理、AI 对话、语义搜索 |
| **AI 模型** | models, credentials, api_keys, settings, config | 模型配置、18+ 提供商凭据管理（Fernet 加密）、API Key |
| **内容生成** | video, ppt, pdf, image, blog | 视频(MoneyPrinterTurbo)、PPT(python-pptx)、PDF(reportlab)、图片(DALL-E/SD)、博客 |
| **播客** | podcasts, episode_profiles, speaker_profiles, languages | 播客生成、剧集/说话人配置、语言列表 |
| **高级** | agents, knowledge_graph, studio, transformations, insights | 多智能体、知识图谱、Studio(报告/FAQ/时间线/模板)、转换规则、洞察 |
| **系统** | logs, commands, embedding, embedding_rebuild, auth, share, context | 日志查看、命令状态、嵌入操作、认证、分享 |

#### 异步命令层（commands/，基于 surreal-commands 队列）

| 命令 | 重试 | 功能 |
|------|------|------|
| `process_source` | 15次 | 源处理核心：提取→保存→转换→嵌入(fire-and-forget) |
| `run_transformation` | 5次 | 对已存在源运行转换生成洞察 |
| `generate_podcast` | 1次 | 播客生成（桌面 EXE 中为 stub） |
| `embed_note/insight/source` | 5次 | 单条嵌入（自动分块 + 平均池化） |
| `create_insight` | 5次 | 创建洞察 + 触发 embed_insight |
| `rebuild_embeddings` | 无 | 批量重建嵌入协调器 |

#### 领域模型层（open_notebook/domain/，10 个文件）

- `ObjectModel`（基类）：自动嵌入、多态 get、关系管理
- `Notebook` → `Source` → `SourceInsight` / `SourceEmbedding`
- `Note`（自动触发 embed_note）
- `ChatSession`、`Asset`、`Transformation`、`Credential`、`ApiKey`
- 搜索：`text_search()` + `vector_search()`

#### LangGraph 图层（open_notebook/graphs/，7 个图）

| 图 | 功能 |
|----|------|
| `source_graph` | 内容摄取管道：提取(content-core)→保存→转换(并行) |
| `chat_graph` | 笔记本对话（带历史 + 上下文 + SqliteSaver 检查点） |
| `source_chat_graph` | 源聚焦对话（ContextBuilder 注入洞察/内容） |
| `ask_graph` | 多搜索策略 Agent（生成搜索词→检索→综合） |
| `transform_graph` | 单节点转换执行器（Jinja2 模板） |

### 2.2 前端页面清单（27 个页面）

| 分类 | 页面 | 技术要点 |
|------|------|----------|
| **核心** | notebooks, notebooks/[id], sources, sources/[id], search | 三栏布局、键盘导航、滚动加载、流式回答 |
| **内容生成** | video, ppt, pdf, image, blog | 模板选择、任务轮询、Markdown 编辑器 |
| **播客** | podcasts | Episodes + Templates 双 Tab |
| **高级** | agents, knowledge-graph, studio(4 子页), transformations | 多 Agent 管理、图谱可视化、Playground |
| **系统** | settings, settings/api-keys, settings/api-access, advanced, logs, shared | 凭据管理(900+行)、API Key、系统信息、日志查看器 |

### 2.3 桌面版架构

```
OpenNotebook.exe (145 MB, PyInstaller 单文件)
├── entry_point.py          # EXE 入口
│   ├── PyInstaller 兼容修补  # tomli/moviepy/podcast_creator stub
│   ├── SurrealDB 启动       # 子进程, 端口 8500, root/root
│   ├── FastAPI 启动         # 线程, 端口 8502, desktop_main.app
│   ├── surreal-commands worker  # daemon 线程, listen_for_commands
│   └── UI 打开              # webbrowser → pywebview → 打印 URL
├── api/desktop_main.py      # 精简 FastAPI
│   ├── 无密码认证
│   ├── CORS allow_origins=["*"]
│   ├── 静态文件挂载 (frontend/out)
│   ├── SPA fallback
│   ├── AgentManager 调度器
│   └── 异常处理器
├── frontend/out/            # Next.js 静态导出
├── surreal.exe              # 嵌入式数据库
└── content_core/*.yaml      # 内容提取配置
```

---

## 三、技术架构与实现方案

### 3.1 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 后端框架 | FastAPI + uvicorn | 0.104+ / 0.24+ |
| AI 编排 | LangChain + LangGraph | 1.2+ / 1.0.5+ |
| 多模型抽象 | Esperanto | 2.20+ |
| 数据库 | SurrealDB | 1.0.4+ |
| 异步队列 | surreal-commands | 1.3.1+ |
| 前端框架 | Next.js + React | 16.2.6 / 19.2.3 |
| UI 组件 | Radix UI + shadcn/ui | - |
| 状态管理 | Zustand + TanStack Query | 5.0 / 5.83 |
| i18n | i18next + react-i18next | 25.7 / 16.5 |
| 桌面打包 | PyInstaller + Inno Setup | - |
| 移动打包 | Capacitor | 8.4 |
| 日志 | Loguru | 0.7.2+ |

### 3.2 数据流

```
用户上传 PDF
  → POST /api/sources (multipart)
  → 创建 Source 记录 + 保存文件
  → CommandService.submit_command_job("open_notebook", "process_source", payload)
  → SurrealDB command 表插入记录
  → surreal-commands worker (daemon 线程) 监听到新命令
  → process_source 命令执行:
      → 加载 Transformation 列表
      → source_graph.ainvoke():
          → content-core 提取全文
          → 保存 full_text 到 Source
          → 并行执行转换生成 Insight
          → fire-and-forget embed_source 命令
  → 前端轮询 GET /api/commands/jobs/{id}
  → status: new → assigned → completed
  → GET /api/sources/{id} 返回 full_text
```

### 3.3 桌面版启动流程

```
双击 OpenNotebook.exe
  → PyInstaller 解压到 _MEIPASS 临时目录
  → entry_point.py main()
  → 注入 moviepy/podcast_creator stub 到 sys.modules
  → 修补 surrealdb AsyncWsSurrealConnection
  → 复制 surreal.exe 到 %APPDATA%/OpenNotebook/bin/
  → 启动 SurrealDB 子进程 (端口 8500)
  → 启动 uvicorn 线程 (端口 8502, desktop_main.app)
  → desktop_main lifespan:
      → 启动 AgentManager 调度器
      → 启动 surreal-commands worker 线程
  → webbrowser.open("http://127.0.0.1:8502")
  → while True: sleep(1)  # 维持进程
```

---

## 四、已完成的开发进度

### 4.1 已完成 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| 笔记本/源/笔记 CRUD | ✅ 完整 | 含三栏布局、搜索、标签 |
| PDF 上传 + 处理 | ✅ 已修复 | full_text 提取 2679 字符中文，命令队列正常 |
| AI 对话 | ✅ 完整 | chat_graph + source_chat_graph，流式回答 |
| 语义搜索 | ✅ 完整 | vector_search + text_search |
| 18+ AI 提供商凭据 | ✅ 完整 | Fernet 加密，凭据发现/迁移 |
| 视频生成 | ✅ 已修复 | MPT 一键启动 + 健康检查 + 任务提交/轮询 |
| PDF/PPT/图片/博客生成 | ✅ 完整 | 5 种模板 each |
| 多智能体系统 | ✅ 基础可用 | 4 种 agent 类型，并行调度 |
| 知识图谱 | ✅ 完整 | 实体/关系可视化 |
| Windows EXE 打包 | ✅ 已修复 | 145 MB，webbrowser 优先打开 UI |
| Android APK 打包 | ✅ 可用 | 6 MB debug APK |
| 全中文 UI | ✅ ~90% | 4 个页面有英文残留 |
| 日志埋点 | ✅ 已添加 | PDF/VIDEO/AGENT 前缀 |
| i18n 基础设施 | ✅ 完整 | 14 种语言 |

### 4.2 部分完成 ⚠️

| 模块 | 状态 | 缺失 |
|------|------|------|
| 播客生成 | ⚠️ 桌面 stub | 桌面 EXE 中 podcast_creator 为占位 stub，需完整 Python 环境运行 |
| 命令列表/取消 | ⚠️ 桩函数 | `list_command_jobs` 返回空数组，`cancel_command_job` 假装成功 |
| 多智能体持久化 | ⚠️ 纯内存 | 进程重启后 agent/task 全部丢失 |
| MPT config.toml | ⚠️ 缺失 | 仅有 config.example.toml，未创建实际配置 |

### 4.3 未开始 ❌

| 模块 | 状态 |
|------|------|
| EXE 签名 | ❌ 未签名（SmartScreen 警告） |
| APK 签名 | ❌ 未签名（无法上架） |
| 自动更新 | ❌ 无 |
| 集成测试 / E2E 测试 | ❌ 全是单元测试 |
| Prometheus metrics | ❌ 无 |
| Sentry 错误聚合 | ❌ 无 |

---

## 五、关键数据指标

### 5.1 代码规模

| 维度 | 数量 |
|------|------|
| 后端路由文件 | 32 个 |
| 异步命令 | 10 个 |
| 领域模型 | 10 个文件 |
| LangGraph 图 | 7 个 |
| 前端页面 | 27 个 |
| 前端组件 | 80+ 个（31 UI + 15 通用 + 35 业务） |
| 测试文件 | 17 个，263 个测试函数 |
| `# type: ignore` | 25 处（2026-06-22 复核，原报告 66 处已偏高） |
| `except Exception` | 114 处 / 20 文件（api/ 目录，2026-06-22 复核） |
| `except Exception: pass` | 20 处（静默吞异常） |
| `open-notebook.spec` | **缺失**（Makefile 仍引用 → `make build-exe` 当前已损坏） |

### 5.2 构建产物

| 产物 | 路径 | 大小 |
|------|------|------|
| Windows EXE | `e:\notebook\releases\OpenNotebook-v1.0.exe` | 145 MB |
| Android APK | `e:\notebook\releases\OpenNotebook-v1.0-debug.apk` | 6 MB |
| Inno Setup 安装包 | `e:\notebook\open-notebook\installer_output\open-notebook-setup-2.1.0.exe` | ~145 MB |

### 5.3 运行时端口

| 服务 | 端口 |
|------|------|
| SurrealDB | 8500 |
| FastAPI | 8502 |
| MoneyPrinterTurbo | 8080 |

### 5.4 端到端测试结果（2026-06-22）

```
[0] GET /api/notebooks                    200  count=1         ✅
[1] POST /api/sources (PDF)               200  cmd=command:... ✅
[2] poll commands/jobs/{id}               → completed           ✅
[3] GET /api/sources/{id}                 200  full_text=2679ch ✅
[4] GET /api/videos/health (前)            available=false       ✅
[5] POST /api/videos/launch-mpt           200  pid=7116        ✅
[6] wait 40s → health                     available=true        ✅
[7] GET /api/videos/templates             5 模板                ✅
[8] POST /api/videos/from-template        200  task_id=...      ✅
[9] POST /api/agents/setup-defaults       200  4 agent          ✅
[10] 3 并发 build 任务                    3/3 completed         ✅
[12] i18n JS 12/12 中文标记               全部命中              ✅
```

---

## 六、用户反馈情况

### 6.1 已报告并修复的问题

| # | 用户反馈 | 根因 | 修复 |
|---|----------|------|------|
| 1 | PDF 上传 500 错误 | podcast_creator 导入失败阻塞 CommandService | stub 模块 + 静默导入 |
| 2 | PDF 处理队列停滞 | 桌面版未启动 surreal-commands worker | desktop_main 内嵌 worker 线程 |
| 3 | PDF full_text=0 | moviepy stub 缺 AudioFileClip → source_graph 加载失败 | 补全 moviepy stub 类 |
| 4 | 视频服务不可用 | sys.executable 指向 EXE 自身 → 启动了另一个 OpenNotebook | _resolve_python_executable 找 venv python |
| 5 | MPT health 永远 false | MPT 无 /ping 路由 | 多端点探测 (/docs, /api/v1/videos) |
| 6 | EXE 双击空白窗口 | pywebview 卡在 webview.start()，无兜底 | webbrowser 优先 + pywebview 备选 |
| 7 | UI 英文残留 | 部分页面未中文化 | 逐页替换（4 页面仍有残留） |

### 6.2 用户情绪与期望

用户多次表达不满（"你做什么了？啥也没做啊！全是501！"），核心期望：
- **零配置开箱即用**：双击 EXE 即可看到完整界面
- **PDF 上传必须能用**：这是核心功能
- **全中文界面**：不能有任何英文
- **视频生成可一键启动**：不需要手动 cd 命令
- **笔记本列表必须展示**：不能空白

---

## 七、主要痛点分析

### 7.1 功能缺陷（按严重程度排序）

#### P0 - 严重

| # | 缺陷 | 位置 | 影响 |
|---|------|------|------|
| 1 | **`command_service.py` 的 `list_command_jobs` 返回空数组** | `api/command_service.py:91-100` | 前端命令列表永远空白，用户无法查看历史任务 |
| 2 | **`cancel_command_job` 假装成功** | `api/command_service.py:102-111` | 用户点取消无效果，任务继续执行 |
| 3 | **`command_service.py` 静默吞掉命令模块导入失败** | `api/command_service.py:31-38` | 若 source_commands/embedding_commands 加载失败，任务入队后永远停滞，无任何日志 |
| 4 | **Build Agent 命令注入漏洞** | `api/agent_service.py:201-207` | `subprocess.create_subprocess_shell(task.payload["command"])` 无白名单，RCE 风险 |
| 5 | **SurrealDB 硬编码 root/root + `--allow-guests`** | `entry_point.py:291-293` | 同机任何进程可直连数据库读写全部数据 |
| 6 | **密码明文比较 + 未设置时跳过认证** | `api/auth.py:32-33,66,94-96` | 时序攻击；生产部署遗漏密码则完全无认证 |
| 7 | **`open-notebook.spec` 文件缺失**（2026-06-22 复核新增） | `open-notebook/` 根目录 | `make build-exe` / `make build-installer` / `make build-all` 全部失效，无法重建 EXE；releases/OpenNotebook-v1.0.exe 为旧产物 |

#### P1 - 高

| # | 缺陷 | 位置 | 影响 |
|---|------|------|------|
| 7 | **agent_service 纯内存状态** | `api/agent_service.py:16-17` | 进程重启 agent/task 全丢失，无超时无重试无 dead-letter |
| 8 | **video_service 日志文件句柄泄漏** | `api/video_service.py:781` | `open(log_path)` 传给 Popen 后从不 close |
| 9 | **video_service MPT 进程死亡无监控** | `api/video_service.py:794-802` | `_mpt_process` 死后无重启，用户需手动重新启动 |
| 10 | **video_service 健康检查误判** | `api/video_service.py:625` | `status_code < 500` 把 404/405 也当健康 |
| 11 | **prompts/ 目录打包配置** | `open-notebook.spec`（待重建） | spec 缺失，重建时必须包含 prompts/ datas，否则 EXE 中 LangGraph Jinja2 模板丢失，AI 对话/源处理失效 |
| 12 | **console=True 未改为 windowed** | `open-notebook.spec`（待重建） | 重建 spec 时应设 `console=False`，避免用户看到黑色控制台窗口 |

#### P2 - 中

| # | 缺陷 | 位置 | 影响 |
|---|------|------|------|
| 13 | 4 个页面有英文残留 | image/agents/logs/settings-api-keys | 国际化不完整 |
| 14 | MPT config.toml 缺失 | MoneyPrinterTurbo/ | 视频生成功能无法直接使用 |
| 15 | CORS 默认通配符 + allow_credentials=True | `api/main.py:95,248` | 跨域安全风险 |
| 16 | 6 处资源清理 `except Exception: pass` | `api/routers/sources.py` | 磁盘泄漏无法追踪 |
| 17 | EXE/APK 均未签名 | releases/ | SmartScreen 警告，无法上架 |
| 18 | 双重 Capacitor 项目 | mobile-app/ vs frontend/android/ | appId 不一致，混乱 |
| 19 | `next.config.ts` ignoreBuildErrors: true | frontend/ | 掩盖 TypeScript 错误 |

### 7.2 性能瓶颈

| # | 瓶颈 | 位置 | 影响 |
|---|------|------|------|
| 1 | **SurrealDB 事务冲突需 15 次重试** | `commands/source_commands.py:56` | `max_attempts: 15` 绕开 DB 事务冲突，高并发下处理延迟 |
| 2 | **source_graph 同步节点 + asyncio 桥接** | `open_notebook/graphs/source.py` | LangGraph 节点同步但 provision 异步，用 `asyncio.new_event_loop()` 绕过，性能差 |
| 3 | **嵌入 fire-and-forget 无限积压** | `commands/embedding_commands.py` | 大量上传时 embed 命令积压，无限流 |
| 4 | **前端 27 个页面全量加载** | `frontend/src/app/` | 无路由级代码分割（Next.js standalone 模式） |
| 5 | **EXE 145 MB 启动慢** | `dist/OpenNotebook.exe` | PyInstaller 单文件解压 + SurrealDB 启动 + API 启动 = 20-30s |

### 7.3 用户体验问题

| # | 问题 | 影响 |
|---|------|------|
| 1 | **EXE 启动后弹出黑色控制台窗口** | 用户困惑，不像正经应用 |
| 2 | **EXE 启动需 20-30 秒** | 用户以为卡死，多次双击导致多进程 |
| 3 | **MPT 启动需 30-45 秒** | 用户以为视频功能坏了 |
| 4 | **无启动进度指示** | 用户看不到启动状态 |
| 5 | **关闭浏览器 ≠ 关闭服务** | 后台进程残留，端口占用 |
| 6 | **4 个页面英文残留** | 中文化不完整 |
| 7 | **侧边栏 20+ 项过于臃肿** | 功能多但学习成本高 |
| 8 | **播客功能在桌面版不可用** | 无明确提示，用户困惑 |

### 7.4 技术债务

#### 债务 1：`sys.modules` stub hack 污染（严重）
- **位置**：`entry_point.py:47-127`
- **问题**：注入 10 个假模块（moviepy/podcast_creator/imageio），`import` 成功但调用失败，`isinstance` 检查错误，6 处 `# type: ignore`
- **修复方向**：用 `importlib.util.LazyLoader` 或拆分桌面版/完整版代码路径

#### 债务 2：25 处 `# type: ignore`（已改善，原报告 66 处）
- **2026-06-22 复核**：全项目已降至 25 处 / 10 文件，最大热点为 `entry_point.py`（7 处，多为 PyInstaller 兼容修补）
- **修复方向**：继续逐步消除，重点排查 `entry_point.py` 和 `commands/source_commands.py`（3 处）

#### 债务 3：`command_service.py` 未实现桩（高）
- **位置**：`api/command_service.py:91-111`
- **修复方向**：实现 SurrealDB 查询或返回 501

#### 债务 4：硬编码 Windows 绝对路径（高）
- **位置**：`api/video_service.py:670,712,761`
- **修复方向**：环境变量 + 平台检测

#### 债务 5：114 处 `except Exception` / 20 文件（中）
- **2026-06-22 复核**：实际 114 处，热点为 `api/routers/sources.py`（28 处）、`api/routers/chat.py`（12 处）、`api/desktop_main.py`（8 处）
- **修复方向**：用具体异常类型替换，优先处理 sources.py

#### 债务 6：无集成测试（中）
- **修复方向**：补 `command_service` / `agent_service` / `auth.py` 单元测试 + E2E

#### 债务 7：双重 Capacitor 项目（低）
- **修复方向**：删除 `mobile-app/`，统一用 `frontend/android/`

### 7.5 开发效率障碍

| # | 障碍 | 影响 |
|---|------|------|
| 1 | **EXE 重建需 5-6 分钟** | 迭代慢，每次改后端代码都要全量重建 |
| 2 | **前端构建需 1-2 分钟** | Next.js 16 静态导出慢 |
| 3 | **无热重载** | 桌面版改代码 = 重建 EXE = 5 分钟 |
| 4 | **测试覆盖不足** | 改代码无测试保护，容易引入回归 |
| 5 | **日志分散** | startup.log / surreal.log / console_err.log / open_notebook_mpt.log 四处 |
| 6 | **无 CI 覆盖率门槛** | 测试通过但不知道覆盖了多少 |
| 7 | **mypy.ini 存在但 66 处 type: ignore** | 类型检查形同虚设 |

---

## 八、给 AI 代码助手的优化建议（按优先级）

### P0 - 立即修复

1. **实现 `list_command_jobs` 和 `cancel_command_job`**（`api/command_service.py:91-111`）
2. **修复 `command_service.py:31-38` 静默吞异常** → 至少 `logger.warning`
3. **修复 Build Agent 命令注入**（`api/agent_service.py:201-207`）→ `create_subprocess_exec` + 白名单
4. **SurrealDB 随机密码**（`entry_point.py:291-293`）→ 启动时生成，写入仅用户可读文件
5. **密码用 `secrets.compare_digest`**（`api/auth.py:66,107`）
6. **重建 `open-notebook.spec`**（当前缺失，Makefile 第 224 行引用）→ 恢复 EXE 构建能力，datas 必须包含 `prompts/`、`frontend/out/`、`surreal.exe`、`content_core/*.yaml`，`console=False`

### P1 - 短期改进

7. **修复 4 个页面英文残留**（image/agents/logs/settings-api-keys）
8. **video_service 日志文件句柄用 contextlib 管理**
9. **video_service MPT 进程监控 + 自动重启**
10. **video_service 健康检查修正** → 404 不应判为健康
11. **agent_service 持久化到 SurrealDB**
12. **创建 MPT config.toml**（从 config.example.toml 复制并配置）

### P2 - 中期优化

13. **消除 `sys.modules` stub hack** → 用可选依赖模式
14. **修复 `api/routers/models.py` type: ignore** → 修复 ContentSettings 类型（2026-06-22 复核：全项目 type: ignore 已降至 25 处，models.py 不再是最大热点，需重新定位）
15. **补测试**：command_service / agent_service / auth / video_service
16. **EXE 签名**（自签名证书）
17. **APK 签名**（release keystore）
18. **启动进度窗口**（splash screen + 进度条）
19. **统一日志输出**（合并 startup.log + console_err.log）

### P3 - 长期演进

20. **路由级代码分割**（减少前端包体积）
21. **Prometheus metrics 导出**
22. **Sentry 错误聚合**
23. **自动更新机制**
24. **SurrealDB 事务冲突根本修复**（减少 max_attempts）
25. **嵌入限流**（令牌桶或信号量）

---

## 九、关键文件索引

| 用途 | 路径 |
|------|------|
| EXE 入口 | `e:\notebook\open-notebook\entry_point.py` |
| 桌面 API | `e:\notebook\open-notebook\api\desktop_main.py` |
| 命令服务（未实现桩） | `e:\notebook\open-notebook\api\command_service.py` |
| 多 Agent 服务（内存状态） | `e:\notebook\open-notebook\api\agent_service.py` |
| 视频服务（MPT 集成） | `e:\notebook\open-notebook\api\video_service.py` |
| 源处理命令 | `e:\notebook\open-notebook\commands\source_commands.py` |
| 播客命令（stub） | `e:\notebook\open-notebook\commands\podcast_commands.py` |
| 认证（密码明文比较） | `e:\notebook\open-notebook\api\auth.py` |
| 源路由（28 处 except Exception） | `e:\notebook\open-notebook\api\routers\sources.py` |
| PyInstaller 配置 | `e:\notebook\open-notebook\open-notebook.spec` **（当前缺失，需重建）** |
| 备份目录 | `e:\notebook\open-notebook-backup-20260621_050052\`（2026-06-21 快照，**不含 spec 文件**，含旧版 entry_point/api/frontend 等，可用于对比回归） |
| 前端设计系统 | `e:\notebook\open-notebook\frontend\src\app\globals.css` |
| 前端 i18n 配置 | `e:\notebook\open-notebook\frontend\src\lib\i18n.ts` |
| 中文翻译 | `e:\notebook\open-notebook\frontend\src\lib\locales\zh-CN\index.ts` |
| 英文残留页面 | image/page.tsx, agents/page.tsx, logs/page.tsx, settings/api-keys/page.tsx |
| 测试目录 | `e:\notebook\open-notebook\tests\`（17 文件，263 测试） |
| 构建产物 | `e:\notebook\releases\` |
| MPT 项目 | `e:\notebook\MoneyPrinterTurbo\` |

---

*报告结束。可直接将此文档提供给 AI 代码助手作为开发优化的上下文输入。*
