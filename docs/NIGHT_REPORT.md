# 🌙 夜间开发报告（2026-08-10）

> 目标：GitHub 版本管理 + 新功能 + 测试 + 汇报

---

## 一、GitHub 版本管理 ✅

**当前状态**：本地 HEAD = 远端 HEAD = `9fd7697`，工作区干净，全部已推送。

本轮提交（完整）：
| 提交 | 内容 |
|------|------|
| `7e9d4f4` | 笔记本导出中心（Markdown/JSON） |
| `4dcefdb` | Analytics 总览 Dashboard 首页 |
| `6e22282` | 知识图谱集成 + 提取 fallback + 容错 JSON |
| `d360e17` | 报告（第三轮） |
| `4954d92` | 共享链接访问统计 |
| `3480a6f` | share 响应容错（测试修复） |
| `0fe6693` | 每日自动备份计划任务 |
| `9fd7697` | 搜索/问答历史 chips |

> ⚠️ 会话中发现：`origin/master` 本地引用曾停留在旧提交（`1da5a42`），但远端实际已是 `bb3ea90`。已用 `ls-remote` 确认远端 HEAD 与本地一致，版本管理完全同步。**若怀疑同步状态，用 `git -c http.proxy=http://127.0.0.1:7897 ls-remote origin HEAD` 核对。**

---

## 二、新功能（本轮开发）

### 1. 📤 笔记本导出中心
- 后端新增 `GET /api/notebooks/{id}/export/json`：结构化导出（元数据 + 来源 + 笔记 + 洞察），含 `export_format: open-notebook-json-v1` 便于再导入
- 前端笔记本详情头部新增"导出"下拉：**Markdown (.md)** / **JSON**，文件名自动清理
- 实测：MD 7303 字符、JSON 3 sources + 2 notes ✅

### 2. 📊 数据总览 Dashboard（替换重定向首页）
- 后端新增 `GET /api/analytics/summary`：笔记本/来源/笔记/洞察/任务/图谱实体/关系计数 + 近期笔记本
- 前端 `/` 首页从"重定向到 /notebooks"改为**统计仪表盘**：
  - 8 个统计卡片（笔记本/来源/笔记/洞察/知识图谱/Agent任务/语义搜索/RAG评估）
  - 近期笔记本列表
  - 4 个快捷入口（图谱/分享/Studio/设置）

### 3. 🕸️ 笔记本详情页集成知识图谱
- 移动端新增"图谱" tab（4 tab：来源/笔记/图谱/聊天）
- 新组件 `NotebookGraph`：实体/关系计数、一键提取按钮、GraphView 可视化 + EntityPanel 详情
- **知识图谱提取修复**（重要）：
  - 之前：默认模型（sensenova 403 / xcode.best 503）失败即报错，功能 100% 不可用
  - 现在：fallback 到所有 language 模型 + 容错 JSON 解析（markdown 包裹/说明文字/截断）
  - 实测：演示笔记本提取 **21 实体 + 19 关系** ✅

### 4. 📈 RAG 评估（验证可用）
- `/eval` 页面的运行完整评估/单题评估/报告列表已存在
- 实测单题评估 200，4 项指标正常计算（faithfulness/relevancy/precision/recall）

---

## 三、测试结果 ✅

| 测试 | 结果 |
|------|------|
| 后端 pytest | **360 passed**（31s，无回归） |
| 前端构建 | **Compiled successfully**（含新页面） |
| 知识图谱提取 | 21 实体 + 19 关系（OpenRouter fallback） |
| Analytics API | 200（计数 + 近期笔记本） |
| 单题 RAG 评估 | 200（4 指标） |
| 手机访问 | 局域网 + 公网隧道 200 |

---

## 四、当前服务状态

| 服务 | 端口 | 状态 |
|------|------|------|
| SurrealDB | 8000 | ✅ |
| API（单进程，含 worker） | 5055 | ✅ 10 命令注册 |
| Caddy API 网关 | 8888 | ✅ |
| Caddy Web | 8889 | ✅ |
| 公网隧道 | — | ✅ `tells-andrea-arg-motion` |

---

## 五、手机访问（访问密码见本地凭据文件）

| 方式 | 地址 |
|------|------|
| 🌐 公网 | `https://tells-andrea-arg-motion.trycloudflare.com` |
| 📶 局域网 | `http://LAN_IP_PLACEHOLDER:8889` |
| 🔒 Tailscale | `http://TAILSCALE_IP_PLACEHOLDER:8889` |

> 隧道重启后域名会变：`powershell -File E:\notebook\scripts\get-tunnel-url.ps1`

---

## 八、第五/六轮补充

### 🕘 搜索/问答历史（本地持久化）
- 新增 `useSearchHistory` hook：搜索/问答成功后自动记录最近 8 条（localStorage 持久化，自动去重，隐私模式安全降级）
- 搜索页模式下显示历史 chips：点击"最近"条目一键重现（ask 切 tab 并填入、search 直接重跑）；带"清除"按钮
- 面试可讲"本地优先 + 无痕降级"的 UX 细节 ✅

### 🏁 最终验证（12:06 实测）
| 检查项 | 状态 |
|--------|------|
| 服务（8000/5055/8888/8889） | ✅ 全部运行 |
| 手机访问（局域网/Tailscale/公网） | ✅ 200 |
| 系统健康 | ✅ ok=True |
| 知识图谱 | ✅ 21 实体 / 19 关系 |
| 混合检索 | ✅ 3/3 命中 |
| 后端测试 | ✅ 360 passed |
| 前端构建 | ✅ 17.9s 成功 |

---

## 九、Source Chat 关键修复（最新 hotfix）

### 🐛 Bug：Source Chat 看不到正文
- **症状**：source 详情页明明有完整正文，但 RAG Chat 回答"仅包含标题、没有具体正文内容"（截图见对话历史）
- **根因**：`ContextBuilder.build()` 忽略了 `ContextConfig.sources` 配置，永远用默认 `inclusion_level="insights"`，导致 `Source.get_context("short")` 返回的 dict 不含 `full_text`
- **修复**：
  - `utils/context_builder.py` 的 `build()`：读取 `context_config.sources` 决定 inclusion_level（兼容带/不带 `source:` 前缀的 key）
  - `graphs/source_chat.py`：显式传 `ContextConfig(sources={source_id: "full content"})`
- **验证**：上下文从 **43 tokens → 2305 tokens**（包含完整正文）

### ⚠️ 部署注意：端口 5055 被僵尸 socket 占用
- 当前 4 个 Python 进程占着 5055（PID 10136/18368/20600/23028），Stop-Process/taskkill 都杀不死（`taskkill /T` 未授权）
- **解决**：重启电脑后用 `E:\notebook\start-all.bat` 启动
- 临时方案：API 已用 5056 端口启动验证修复（`E:\notebook\open-notebook\api-5056.log`）

### 📝 关于 UmiOCR 的调研结论
- **当前用 PyMuPDF（fitz）+ 内置 Tesseract OCR**（`content_core` 库）处理 PDF
- demo PDF（公考面试/AI Agent）**已是文字版 PDF**（不是扫描件），PyMuPDF 正常提取中文（22 chunks/source 已是证据）
- **UmiOCR_Rapid 基于 PaddleOCR**，对**扫描型/图片型 PDF** 的中文识别更好，但**对文字 PDF 无优势**且速度慢
- **建议**：不换。将来遇到扫描件 PDF 场景再考虑接入 UmiOCR 作为 fallback

---

## 十、SenseNova 接入 + Provider 优先级（最新）

### 🔑 关键修复：SenseNova 端点
- **问题**：`.env` 里的 `SENSENOVA_BASE_URL=https://api.sensenova.cn/compatible-mode/v2` 所有请求 **403 Forbidden**
- **真相**：正确端点是 `https://token.sensenova.cn/v1`（搜到官方/社区确认）
- **修复后实测**：
  - `sensenova-6.7-flash-lite` ✅（text+image 多模态）
  - `deepseek-v4-flash` ✅（对话，1M 上下文）
  - `sensenova-u1-fast` → 404（该模型是 infographics 专用端点，chat 不可用）
  - embedding → 403（SenseNova 免费额度不含 embedding），**继续用 OpenRouter qwen3**

### ⚙️ 模型分配方案（已实现）
| 用途 | 首选 | 兜底 |
|------|------|------|
| Chat/RAG | SenseNova deepseek-v4-flash（现在） | xcode.best gpt-5.6-luna（503 恢复后自动优先）→ OpenRouter |
| Transform | SenseNova 6.7-flash-lite | xcode.best |
| Embedding | OpenRouter qwen3-embedding-4b | — |

### 🎛️ 可调 Provider 优先级（新功能）
- 新增环境变量 `MODEL_PROVIDER_PRIORITY`（逗号分隔）：
  ```
  MODEL_PROVIDER_PRIORITY=sensenova,openai_compatible,openrouter
  ```
- 启动时**探测每个 provider**，选最高优先级且可用的作为默认 chat
- xcode.best 的 key 保留在 `.env`，**503 恢复后自动优先**（无需手动切）
- 用户改这个变量 + 重启即可调整优先级

### ✅ 验证结果
- RAG 问答（SenseNova）：200，68s，高质量中文回答含引用 ✅
- Source Chat（SenseNova + full_text 修复）：**正确读取正文**，3 点总结带引用 ✅
- 测试：**360/360 passed**
- 提交 `818beaa` 已推送
| 每日自动备份 | ✅ 已创建+实测 |

---

## 六、第四轮补充（共享访问统计）

### 📈 共享链接访问统计
- `ShareLink` 新增 `access_count`（默认 0）和 `last_accessed_at`
- `GET /api/share/{token}` 每次访问自动记录（统计失败不阻断共享视图）
- `ShareLinkResponse` 暴露统计字段（前端可展示）
- 实测：新链接访问 3 次 → `access_count=3`、`last_accessed_at` 更新 ✅
- 修复：`_to_response` 对缺失字段容错（兼容测试 mock / 旧记录），**360/360 测试通过**

---

## 七、运维自动化（第四轮补充）

### 🗓️ 每日自动备份计划任务
- 创建 Windows 计划任务 `OpenNotebook-AutoBackup`：每天 **03:00** 自动执行 `backup-data.ps1`（SurrealDB + 上传文件 + 脱敏 .env），保留最近 5 份，执行限时 2 小时
- 已实测触发：`LastResult=0`（成功），生成 `backup_20260810_115826` ✅
- 查询/管理：
  ```powershell
  Get-ScheduledTaskInfo -TaskName "OpenNotebook-AutoBackup"   # 查看上次结果
  Start-ScheduledTask -TaskName "OpenNotebook-AutoBackup"      # 立即备份
  Unregister-ScheduledTask -TaskName "OpenNotebook-AutoBackup" # 移除
  ```

---

## 八、遗留/待办

- [ ] 手机 PWA 安装测试（Android 添加到主屏幕）
- [ ] 隧道域名临时性（需要固定域名可配 Cloudflare Named Tunnel）
- [ ] xcode.best 的 gpt-5.6-luna 当前 503，恢复后自动优先（已有 cooldown 缓存）
- [ ] Studio 报告生成依赖模型，当前默认模型不可用时需手动选 OpenRouter 模型
