# 系统架构

## 概览

Notebook-Evo 是一个隐私优先、多模型、可自托管的 AI 知识工作台。用户上传
资料（PDF/网页/文本），系统通过 RAG 流水线将资料向量化，提供 AI 问答、
混合检索、内容生成（播客/PPT/PDF/视频）、多智能体编排与知识图谱推理。

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 + React 19 + Tailwind + shadcn/ui)       │
│  ├─ 笔记本 / 来源 / 聊天 / 搜索 / 知识图谱 / Agent / Studio     │
│  ├─ RAG 评估中心 · Agent 编排 · 混合检索调试台（本增强版新增）  │
│  └─ i18n (14 语言) · 响应式 (Web / 移动端)                      │
└───────────────┬─────────────────────────────────────────────────┘
                │ REST + SSE (流式回答)
┌───────────────▼─────────────────────────────────────────────────┐
│  API 层 (FastAPI)                                               │
│  ├─ 认证 (PasswordAuthMiddleware) · 凭证加密存储                 │
│  ├─ 路由: notebooks / sources / chat / search / eval / agents   │
│  │        knowledge-graph / credentials / models / share        │
│  ├─ MCP Server (fastmcp) — 暴露知识库为 AI 客户端工具            │
│  └─ 后台调度器 (agent scheduler · 内容生成队列)                  │
└───────┬───────────────────────────────┬─────────────────────────┘
        │                               │
┌───────▼───────────────┐   ┌───────────▼─────────────────────────┐
│  SurrealDB (v2)       │   │  LangGraph 工作流                   │
│  ├─ 文档/来源/笔记存储 │   │  ├─ ask: 混合检索 → 回答            │
│  ├─ 向量索引 (vector) │   │  ├─ content: PDF/PPT/博客/播客生成   │
│  ├─ FULLTEXT 索引     │   │  └─ insight: 摘要/洞察提取           │
│  └─ 图存储 (实体/关系) │   │                                      │
└───────────────────────┘   └───────────┬─────────────────────────┘
                                        │
                            ┌───────────▼─────────────────────────┐
                            │  Esperanto 多模型抽象层              │
                            │  (20+ 提供商: OpenAI/Anthropic/      │
                            │   Gemini/DeepSeek/本地 Ollama 等)    │
                            └─────────────────────────────────────┘
```

## 核心数据流

### 1. 知识摄取流水线

```
上传来源 (PDF/URL/文本)
  → 文档解析 (PyMuPDF/BeautifulSoup)
  → 分块 (CHUNK_SIZE=400, OVERLAP=60)
  → 向量化 (Embedding 模型)
  → 写入 SurrealDB (vector index)
  → 可选: 实体/关系抽取 → 知识图谱
```

### 2. RAG 问答流水线（增强版混合检索）

```
用户问题
  → 双路并行召回:
      A. 向量检索 (语义相似, top-20)
      B. BM25 全文检索 (关键词匹配, top-20)
  → RRF 融合 (Reciprocal Rank Fusion, k=60)
  → 可选 Cross-Encoder Rerank
  → 上下文注入 → LLM 生成回答
  → 回答流式返回前端
```

### 3. RAG 评估流水线（本增强版新增）

```
内置/自定义测试集 (questions.json)
  → 对每题执行完整 RAG 链路（检索 + 回答）
  → RAGAS 四维评分:
      faithfulness / answer_relevancy
      context_precision / context_recall
  → 报告持久化 (data/eval/report-*.json)
  → 前端仪表盘可视化 + 导出
```

### 4. 多智能体编排（本增强版新增）

```
Agent 创建 → JSON 持久化 (agent_state.json)
  → 任务入队 (依赖 DAG)
  → 调度器分配 (能力匹配)
  → Agent 执行 (LLM + 工具)
  → 状态落库 → 重启恢复
```

### 5. MCP 集成（本增强版新增）

```
任意 AI 客户端 (Claude/Cursor/自研)
  → MCP 协议 (stdio/SSE)
  → api/mcp_server.py
  → 工具: hybrid_search / ask_knowledge_base / graph_ask ...
```

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 数据库 | SurrealDB v2 | 文档+向量+图三种模型一体，单库解决 |
| 多模型抽象 | Esperanto | 20+ 提供商统一接口，用户可自选 |
| 工作流编排 | LangGraph | 状态化图执行，支持流式与并行 |
| 混合检索 | BM25 + 向量 + RRF | 语义+关键词互补，RRF 无需训练 |
| RAG 评估 | RAGAS | 无参考自动评分，四维标准指标 |
| Agent 持久化 | JSON 文件 | 无表结构迁移成本，重启即恢复 |
| MCP | fastmcp | 标准协议，stdio/SSE 双传输 |

## 目录结构

```
api/                  # FastAPI 应用
  routers/            # 路由（每个资源一个文件）
  mcp_server.py       # MCP 服务端（增强）
  eval_service.py     # RAG 评估（增强）
  agent_service.py    # 多智能体调度（增强持久化）
  agent_persistence.py# Agent 状态持久化（增强）
open_notebook/
  domain/             # 领域模型 (notebook/source/note/graph)
  graphs/             # LangGraph 工作流
  ai/                 # 模型管理 (Esperanto)
  search/hybrid.py    # 混合检索（增强）
  graphrag.py         # 图谱问答（增强）
frontend/             # Next.js 应用
  src/app/(dashboard)/# 页面（eval 评估中心为增强新增）
docs/                 # 架构/使用文档
tests/                # 单元测试（增强新增 25+ 测试）
```
