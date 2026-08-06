<div align="center">

# Notebook-Evo · AI 知识工作台

**隐私优先 · 多模型 · 可自托管的 AI 知识工作台**

基于开源项目 [Open Notebook](https://github.com/lfnovo/open-notebook)（MIT）深度增强的个人知识库与 AI 内容生产平台。

上传你的研究资料，用 AI 问答、混合检索、图谱推理与内容生成，构建属于你的知识工作流。

</div>

---

## ✨ 本增强版亮点（vs 上游）

| 能力 | 说明 | 技术要点 |
|------|------|---------|
| 🔍 **混合检索** | BM25 全文 + 向量语义双路召回，RRF 融合 + 可选 Rerank | `open_notebook/search/hybrid.py` |
| 🀄 **中文检索** | jieba 分词 + rank_bm25 兜底（SurrealDB 英文 analyzer 无法处理中文） | `open_notebook/search/chinese_bm25.py` |
| 📊 **RAG 评估中心** | RAGAS 四维指标自动评估回答质量，可视化报告 | `api/eval_service.py` + 前端仪表盘 |
| 🤖 **Agent 持久化** | 多智能体状态跨重启恢复，任务依赖 DAG 可视化编排 | `api/agent_persistence.py` |
| 🕸️ **GraphRAG 问答** | 实体关系图谱推理 + 向量检索融合问答 | `open_notebook/graphrag.py` |
| 🔌 **MCP Server** | 知识库能力暴露为标准 MCP 工具，AI 客户端可直接操作 | `api/mcp_server.py` |
| 🧠 **高级检索** | HyDE 假设文档嵌入 + 语义缓存 + 自适应路由 | `open_notebook/search/advanced_retrieval.py` |
| 🚀 **一键演示** | 内置示例数据 + 一键启动脚本，5 分钟跑起来 | `start-demo.bat` |
| 📱 **双端同步** | Tailscale 内网穿透，手机电脑访问同一知识库 | `docs/mobile-sync.md` |
| ✅ **工程化** | CI（lint + test）、Docker 一键部署、架构文档 | `.github/workflows/` |
| 🔐 **安全加固** | SSRF/DNS 重绑定防护、SurrealQL 注入修复、Jinja2 模板注入修复、跨 provider 模型降级 | 移植原版 v1.12-1.14 安全修复 |

## 🧱 技术栈

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![SurrealDB](https://img.shields.io/badge/SurrealDB-FF5E00?style=for-the-badge&logo=databricks&logoColor=white)](https://surrealdb.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-3A3A3A?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain.com)
[![MCP](https://img.shields.io/badge/MCP-000000?style=for-the-badge&logo=modelcontextprotocol&logoColor=white)](https://modelcontextprotocol.io)

## 📐 系统架构

```
前端 (Next.js 16 + React 19)  ← REST + SSE →  API 层 (FastAPI + LangGraph)
                                                │
                                    ┌───────────┴───────────┐
                                    │ SurrealDB (文档+向量+图)│
                                    │ Esperanto (20+ 模型商) │
                                    │ MCP Server (fastmcp)   │
                                    └───────────────────────┘
```

完整架构见 [docs/architecture.md](docs/architecture.md)

## 🚀 快速开始

### 方式一：Docker 一键部署（2 分钟）

```bash
# 构建并使用本增强版镜像
docker compose -f docker-compose.self.yml up -d
# 打开 http://localhost:8502
```

### 方式二：源码运行

```bash
# 1. 安装依赖 (需要 Python 3.12+ / uv)
uv sync

# 2. 启动 SurrealDB
./surreal.exe start --log info --user root --pass root --bind 127.0.0.1:8000 rocksdb:./surreal_data/db

# 3. 启动 API
.\.venv\Scripts\python.exe run_api.py
```

### 方式三：一键演示模式（Windows）

```bat
start-demo.bat
```

自动启动数据库 → 初始化演示数据 → 打开浏览器，5 分钟体验全部功能。

## ⚙️ 配置 AI 模型

1. 打开 Web UI → **Models**
2. 添加配置（OpenAI / Anthropic / DeepSeek / 本地 Ollama 等 20+ 提供商）
3. 填入 API Key → **Test** 测试 → **Sync Models**
4. **Auto-Assign Defaults** 分配默认模型

## 🛠️ 功能总览

### 知识管理
- **笔记本**：多项目组织研究资料
- **来源**：PDF / 网页 / 视频 / 音频 / Office 文档
- **笔记**：AI 辅助洞察生成

### AI 能力
- **RAG 问答**：混合检索增强回答，带引用
- **混合检索**：全文 + 语义 + 重排（本增强版）
- **知识图谱**：实体关系提取 + GraphRAG 推理问答（本增强版）
- **RAG 评估**：四维指标自动评估（本增强版）
- **多智能体**：并行任务 + 持久化 + DAG 编排（本增强版）

### 内容生产
- **播客**：多 Speaker 播客生成
- **PPT / PDF / 博客 / 图片**：一键内容转化
- **视频**：MoneyPrinterTurbo 集成

### 集成与部署
- **MCP Server**：AI 客户端直接操作知识库（本增强版）
- **REST API**：完整程序化访问
- **桌面版**：Windows EXE / Android APK
- **多语言**：14 种语言 UI

## 📚 文档

| 文档 | 说明 |
|------|------|
| [架构文档](docs/architecture.md) | 系统架构、数据流、技术决策 |
| [MCP 接入指南](docs/mcp-server.md) | 将知识库接入 Claude/Cursor |
| [双端同步指南](docs/mobile-sync.md) | Tailscale 手机电脑访问 |
| [测试与验收方案](docs/qa.md) | 三层测试体系与验收标准 |

## 🧪 测试

```bash
# 后端单元测试
uv run pytest tests/ -v

# 前端测试
cd frontend && npm test

# Lint
uv run ruff check api/ open_notebook/ tests/
cd frontend && npm run lint
```

本增强版新增 51 个单元测试（混合检索 / 中文 BM25 / RAG 评估 / GraphRAG / MCP / Agent 持久化 / 高级检索）。

## 🗺️ Roadmap

- [x] P0.1 混合检索（BM25 + 向量 + RRF + Rerank）
- [x] P0.2 RAG 评估仪表盘（RAGAS）
- [x] P1.1 Agent 持久化 + 可视化编排
- [x] P1.2 GraphRAG 图谱问答
- [x] P1.3 MCP Server
- [x] P1.4 CI + Docker + 架构文档
- [x] P2.1 一键演示模式
- [x] P2.2 双端同步（Tailscale）
- [x] P2.3 高级检索（HyDE + 语义缓存 + 自适应路由）
- [ ] H1 多智能体 A2A 协作
- [ ] H2 思维导图 / 闪卡 / 测验生成
- [ ] H3 多模态 RAG（图片 / 表格理解）
- [ ] H4 Agentic RAG（自适应多跳检索）

## 📄 License

MIT License. 基于 [Open Notebook](https://github.com/lfnovo/open-notebook)（MIT）增强，诚实的 fork 声明与增量贡献。

## 🙏 致谢

- [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook) — 上游开源项目
- [Esperanto](https://github.com/lfnovo/esperanto) — 多模型抽象层
- [RAGAS](https://github.com/explodinggradients/ragas) — RAG 评估框架
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP 服务端
