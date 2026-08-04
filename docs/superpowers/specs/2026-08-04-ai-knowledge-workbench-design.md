# AI 知识工作台（Open Notebook Enhanced）设计文档

> 日期：2026-08-04
> 状态：已确认
> 目标：两周内打造一个可用于求职展示（AI 应用开发 / AI 产品方向）的完整、可演示、有深度、可落地的 AI 知识工作台

---

## 一、项目定位

**一句话定位**：一个隐私优先、多模型、可自托管的 AI 知识工作台——管理你的研究资料，用 AI 问答、检索、生成内容（播客/PPT/PDF/视频），支持 Agent 工作流与多端访问。

**差异化声明**：基于开源项目 [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook)（MIT，2.5w+ star）深度增强。fork 声明 + 明确的增强清单，突出增量贡献。

**求职叙事**：
- **AI 应用开发能力**：RAG 全链路（摄取→分块→嵌入→混合检索→重排→评估）、LangGraph 工作流、多模型抽象、Agent 编排、MCP 集成
- **产品/架构能力**：完整的产品功能矩阵、Docker 一键部署、多端分发（Web/Desktop/Android）、CI/CD、架构文档
- **工程素养**：单元/集成/E2E 测试、双验证验收流程、代码规范

---

## 二、功能全景（P0/P1/P2 + 高级功能）

### P0 - 核心必做（第 1-2 周前半）

| # | 功能 | 技术方案 | 验收标准 |
|---|------|---------|---------|
| P0.1 | **混合检索升级** | BM25 全文 + 向量双路召回 → RRF 融合 → Cross-Encoder Rerank（可选 BGE-Reranker） | 检索接口返回融合+重排结果，指标可测 |
| P0.2 | **RAG 评估仪表盘** | RAGAS 指标（faithfulness / answer_relevancy / context_precision / context_recall），内置测试集，可视化报告 | 一键跑评估，生成可导出报告 |
| P0.3 | **仓库清理 + GitHub 上线** | 删除临时文件/日志/备份，重建 git 历史，README 重写 | 干净仓库，可 clone 后一键启动 |

### P1 - 重要（第 1-2 周后半）

| # | 功能 | 技术方案 | 验收标准 |
|---|------|---------|---------|
| P1.1 | **Agent 可视化工作流** | 现有 4 种 Agent 持久化到 SurrealDB + 前端可视化编排面板（拖拽式 DAG） | Agent/任务重启不丢失，可编排并执行 |
| P1.2 | **知识图谱问答** | 现有图谱可视化 → GraphRAG：实体/关系抽取 + 图谱检索 + 推理问答 | 图谱问答能给出基于实体关系的回答 |
| P1.3 | **MCP Server** | 用 FastMCP 暴露平台能力（检索/笔记/来源管理）为 MCP 工具 | 可用 Claude Desktop / 任意 MCP 客户端调用 |
| P1.4 | **GitHub 工程化** | CI（GitHub Actions：lint + test + build）、Docker Compose 一键部署、架构文档、演示视频 | CI 绿、Docker 一键起、文档完整 |

### P2 - 加分（第 2 周收尾）

| # | 功能 | 技术方案 | 验收标准 |
|---|------|---------|---------|
| P2.1 | **一键演示模式** | 内置示例数据（示例 PDF/笔记本）+ 一键启动脚本 | 5 分钟内跑起来并看到数据 |
| P2.2 | **双端同步** | Tailscale 内网穿透（复用已有 TAILSCALE/CLOUDFLARE 配置）+ Android APK | 手机通过 Tailscale 访问桌面实例 |
| P2.3 | **高级检索能力** | HyDE（假设文档嵌入）+ 语义缓存（相似问题直接命中）+ 自适应路由 | 检索速度提升 & 缓存命中率指标 |

### 高级功能（技术亮点展示，能力叠加）

| # | 功能 | 说明 |
|---|------|------|
| H1 | **多智能体 A2A 协作** | 现有 Agent 消息队列升级为 A2A 协议风格（Agent Card + 任务委派） |
| H2 | **思维导图/闪卡/测验生成** | Studio 模式扩展（NotebookLM 2026 同款能力） |
| H3 | **多模态 RAG** | 图片/表格内容理解（VLM 抽取 + 向量化） |
| H4 | **Agentic RAG** | 检索策略由 Agent 自适应决定（多跳检索、查询改写） |

---

## 三、技术架构

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 + React 19 + shadcn/ui + Zustand)     │
│  - 30+ 页面：笔记本/来源/聊天/搜索/图谱/Agent/Studio/生成    │
│  - 新增：RAG 评估仪表盘、Agent 编排面板、检索调试台         │
└────────────────────────┬────────────────────────────────────┘
                         │ REST + SSE (流式)
┌────────────────────────▼────────────────────────────────────┐
│  API (FastAPI) + LangGraph                                  │
│  - 混合检索服务 (BM25+向量+RRF+Rerank)                      │
│  - 评估服务 (RAGAS) + 缓存服务 (语义缓存)                   │
│  - Agent 服务 (持久化 + 可视化编排)                         │
│  - MCP Server (FastMCP)                                     │
│  - 知识图谱服务 (GraphRAG)                                  │
└────────────┬───────────────────────────────┬────────────────┘
             │ SurrealQL                     │
┌────────────▼─────────────┐    ┌────────────▼────────────────┐
│  SurrealDB (图谱+向量+DB)│    │  Esperanto (20+ 模型商抽象) │
│  - 混合索引: 全文+向量    │    │  外部服务: MPT/视频/PPT/PDF │
└──────────────────────────┘    └─────────────────────────────┘
```

**核心复用**（已有基础，不重写）：
- `text_search` / `vector_search`（已有，ask.py 已注释全文检索 → 恢复 + 融合）
- 现有 Agent 系统（内存 → 持久化）
- 现有知识图谱可视化（补 GraphRAG 检索）
- 现有 Capacitor 移动端 + Tailscale 配置

---

## 四、P0 详细设计

### P0.1 混合检索升级

**现状**：`ask.py` 只调用 `vector_search`，`text_search` 存在但未接入。

**设计**：
```
用户查询
  → 并行双路召回:
      A. 向量检索 (vector_search, top 20)
      B. BM25 全文检索 (text_search, top 20)  [恢复 SurrealDB FULLTEXT 索引]
  → RRF 融合 (Reciprocal Rank Fusion, k=60)
  → 可选 Rerank (Cross-Encoder, top 10)
      - 有 rerank 模型配置时启用（如 BGE-Reranker via API/本地）
      - 未配置时跳过，直接返回 RRF 结果
  → 返回带 score/source 的检索结果
```

**改动点**：
- `open_notebook/domain/notebook.py`：恢复/完善 `text_search`（确认 FULLTEXT 索引 schema）
- 新增 `open_notebook/search/hybrid.py`：`HybridSearchService`（双路召回 + RRF + Rerank）
- `open_notebook/graphs/ask.py`：`provide_answer` 改用混合检索
- 新增 `open_notebook/search/rerank.py`：Rerank 适配层（OpenAI-compatible rerank API 或本地模型）
- `api/routers/search.py`：新增 `POST /api/search/hybrid` 调试端点
- 前端：搜索页/检索调试台显示"双路命中 + 融合"详情

**依赖**：`rank_bm25`（纯 Python，无重型依赖）或复用 SurrealDB FULLTEXT；Rerank 走 OpenAI-compatible 端点（可用现有 provider 体系）。

### P0.2 RAG 评估仪表盘

**设计**：
```
内置评估集 (tests/eval/questions.json): 20+ 个"问题-期望要点"对
  → 对每个问题执行 RAG 全链路（检索+生成）
  → RAGAS 指标计算:
      - faithfulness (忠实度): 答案是否基于检索上下文
      - answer_relevancy (答案相关性)
      - context_precision (上下文精确度)
      - context_recall (召回率)
  → 前端仪表盘: 总分 + 四维雷达图 + 逐题明细
  → 导出 JSON/Markdown 报告
```

**改动点**：
- 新增 `api/eval_service.py`：评估流水线
- 新增 `api/routers/eval.py`：`POST /api/eval/run`、`GET /api/eval/reports`、`GET /api/eval/reports/{id}`
- 新增 `frontend/src/app/(dashboard)/eval/page.tsx`：评估仪表盘
- 依赖：`ragas`（pip 安装，纯调用 LLM 评分）

### P0.3 仓库清理 + GitHub 上线

**清理清单**：
- 删除：所有 `_tmp_*` 目录、`backups/`、根目录 40+ 日志文件、`open-notebook` 下 `*.log`/`exe_*.log`
- 确认 `.gitignore` 覆盖：`.env`、`.venv`、`node_modules`、`dist/`、`build/`、`data/`、`db/`、`surreal_data/`、日志
- 重建 git 历史（或 squash 为清晰提交）
- 重写 README：定位、功能矩阵、截图、快速开始、增强清单、架构图

---

## 五、P1 详细设计

### P1.1 Agent 可视化工作流

**现状**：`agent_service.py` 纯内存，进程重启丢失。

**设计**：
- Agent/Task 持久化到 SurrealDB（新增 `Agent`、`AgentTask` 表 + repo）
- 前端新增"Agent 编排"页面：节点（Agent）+ 连线（依赖）的 DAG 可视化
- 调度器：现有 scheduler 逻辑改造为从 DB 读取 + 状态落库
- API：`GET/POST /api/agents/workflows`、`POST /api/agents/workflows/{id}/run`

### P1.2 知识图谱问答（GraphRAG）

**设计**：
- 现有图谱可视化保留
- 新增：实体/关系 LLM 抽取 → 存入图谱 → 检索时"图谱路径 + 向量"双通道
- 问答节点：先图谱查询（实体匹配 + 一跳/两跳邻居）→ 结合向量检索 → LLM 综合回答
- API：`POST /api/knowledge-graph/ask`

### P1.3 MCP Server

**设计**：
- 用 `fastmcp` 暴露工具：`list_notebooks`、`search_sources`、`hybrid_search`、`create_note`、`ask_knowledge_base`
- 单独进程 `python -m api.mcp_server`（或并入 API 进程，`/mcp` SSE 端点）
- 文档：Claude Desktop / Cursor / 任意 MCP 客户端接入步骤
- 依赖：`fastmcp`（pip）

### P1.4 GitHub 工程化

- `.github/workflows/ci.yml`：lint（ruff/mypy）→ test（pytest）→ build（frontend + docker）
- Docker Compose 完善：`docker-compose.yml` 一键起 SurrealDB + API + Frontend
- `docs/architecture.md`：架构图 + 数据流 + 模块说明
- 演示视频脚本：`docs/demo/` 录制大纲（3-5 分钟）

---

## 六、P2 详细设计

### P2.1 一键演示模式
- `scripts/demo/seed_demo_data.py`：创建示例笔记本 + 上传示例 PDF + 生成示例笔记/洞察
- `start-demo.bat`：起 SurrealDB + API + 种子数据 + 打开浏览器
- 示例数据放 `data/demo/`（一个公开中文 PDF，如政府工作报告节选）

### P2.2 双端同步
- 复用已有 `TAILSCALE_DOMAIN` / `CLOUDFLARE_DOMAIN` 配置
- 文档：Tailscale 安装 → 手机装 APK → 输入 Tailscale IP → 访问
- APK 用 `frontend/android/`（消除双重 Capacitor 项目）

### P2.3 高级检索（HyDE + 语义缓存 + 自适应路由）
- HyDE：查询 → LLM 生成假设文档 → 用其向量检索（可选开关）
- 语义缓存：`(query_embedding, 阈值)` → 命中返回缓存答案；基于向量表 `CacheEntry`
- 自适应路由：简单问题走纯向量，复杂问题走混合+重排（基于 query 长度/关键词）

---

## 七、测试与验收方案（双验证流程）

### 7.1 验收原则

> **Agent 先验证 → 用户后验收**。每个功能模块由 AI Agent 完成自动化验证（测试+检查清单），全部通过后再提交用户做人工确认。减少用户工作量：用户只需核对验收单，无需逐项深查。

### 7.2 三层测试体系

| 层 | 工具 | 内容 | 触发 |
|---|------|------|------|
| 单元测试 | pytest | 服务层/工具函数/检索逻辑 | CI + Agent 自测 |
| 集成测试 | pytest + httpx | API 端点 + 数据库 + 图执行 | Agent 自测 |
| E2E 验收 | 脚本 + 手动 | 全链路（上传→检索→问答→评估） | Agent 预跑 + 用户复核 |

### 7.3 Agent 自动验证清单（每功能完成时必须通过）

每个功能提交时，Agent 必须运行并输出：

```
[模块名] Agent 自验报告
1. 单元测试:  全部通过 (N tests) / 失败列表
2. API 冒烟:  POST/GET 各端点 200 / 异常
3. 数据验证:  数据库记录正确 / 无脏数据
4. 回归检查:  既有测试未破坏 (N tests)
5. 边界检查:  空输入/超大输入/并发 处理正确
6. 日志检查:  无 ERROR 级日志泄漏
结论: PASS / FAIL (附原因)
```

### 7.4 用户验收单（每个功能，用户只需打勾）

```
验收单 - [功能名]
□ 我能用 5 分钟内在本地跑起来看到这个功能
□ 功能行为符合设计文档描述
□ 界面是中文且无报错
□ 数据操作正确（增删改查无异常）
□ Agent 自验报告已附上且 PASS
□ 如发现问题: 描述 → 返回 Agent 修复 → 复验
```

### 7.5 验收边界（明确"什么不算缺陷"）

| 边界 | 说明 |
|------|------|
| 模型质量波动 | LLM 输出非确定性，允许语义等价的不同措辞；不接受事实错误 |
| 外部服务 | MoneyPrinterTurbo/播客 TTS 需要外部服务，未启动时显示明确提示而非崩溃 |
| 性能 | P2 前不做基准测试；交互响应 < 10s 即可 |
| 兼容 | 仅保证 Chrome/Edge 最新版 + Android 12+ |
| 数据安全 | `.env` 永不入库；demo 数据不含真实 API key |

---

## 八、两周排期

### 第 1 周：地基 + P0

| 天 | 任务 | 交付物 |
|----|------|--------|
| D1 | 仓库清理 + git 历史重建 + README 框架 | 干净仓库 |
| D2-3 | P0.1 混合检索（BM25+向量+RRF+Rerank） | 混合检索服务 + 调试台 |
| D4-5 | P0.2 RAG 评估仪表盘（RAGAS） | 评估服务 + 前端页面 |
| D6 | P0 双验证 + 用户验收 | 验收单完成 |

### 第 2 周：P1 + P2

| 天 | 任务 | 交付物 |
|----|------|--------|
| D7-8 | P1.1 Agent 持久化 + 可视化编排 | Agent 工作流页面 |
| D9 | P1.2 GraphRAG 问答 | 图谱问答 |
| D10 | P1.3 MCP Server | MCP 接入文档 + 可用 |
| D11 | P1.4 CI + Docker + 架构文档 | GitHub 工程化 |
| D12 | P2.1 演示模式 + P2.2 Tailscale 文档 | 一键演示 |
| D13 | P2.3 HyDE + 缓存 + 高级功能（尽力） | 检索增强 |
| D14 | 总验收 + 演示视频 + 简历素材 | 可投简历 |

### 多 Agent 并行策略

| 并行组 | 说明 |
|--------|------|
| 组 A：后端 AI 能力（混合检索+评估+缓存） | 独立服务层，互不依赖 |
| 组 B：Agent + MCP + GraphRAG | 独立模块 |
| 组 C：前端页面（评估台/编排台/调试台） | 依赖 API 契约（先定 OpenAPI） |
| 组 D：GitHub 工程化 + 文档 + 演示 | 全程并行 |

并行原则：先定 API 契约（Pydantic schema）→ 各组按契约并行开发 → 集成测试收口。

---

## 九、风险与对策

| 风险 | 对策 |
|------|------|
| RAGAS 依赖重/装不上 | 备选：自实现 faithfulness（LLM 打分），不依赖 ragas |
| SurrealDB FULLTEXT 索引兼容问题 | 备选：BM25 用 `rank_bm25` 内存实现（数据量小，可接受） |
| Rerank 无可用模型 | 设计为可选链路，未配置自动降级为 RRF-only |
| 两周时间紧 | P2.3/H 系列为"尽力项"，P0+P1 必保 |
| 原版上游更新冲突 | 本地 fork 固定基线，不盲目 merge 上游 |

---

## 十、GitHub 展示方案

- 仓库名：`ai-knowledge-workbench`（或用户定）
- README 结构：Hero 图 → 一句话定位 → 功能矩阵（表）→ 快速开始（Docker/源码）→ 截图 → 增强清单（vs 上游）→ 技术架构图 → 测试 → 路线图
- 主分支：`main`，工作流：PR → CI 绿 → merge
- 演示视频链接（README 顶部 + 简历）
- 完整 API 文档（FastAPI 自带 `/docs`）+ 截图

---

## 附：需要用户确认的开放项

1. GitHub 仓库名（建议 `ai-knowledge-workbench`）
2. 示例 PDF 素材（用户提供一份真实 PDF 或我生成测试 PDF）
3. MCP Server 是否需要接入 Claude Desktop 实测（需用户本机有 Claude Desktop）
4. Tailscale 是否需要实测（需用户手机装 APK + Tailscale）
