# Notebook Evo 实施计划

> 日期：2026-08-04
> 基线：设计文档 `2026-08-04-ai-knowledge-workbench-design.md`（已冻结）
> 目标：两周内完成 P0+P1+P2，尽可能完成 H 系列

---

## 一、里程碑

| 里程碑 | 时间 | 内容 | 验收 |
|--------|------|------|------|
| M1 | D1-D2 | 仓库清理 + 基线稳定 | 干净仓库，API 可启动，测试全绿 |
| M2 | D3-D5 | P0.1 混合检索 + P0.2 RAG 评估 | 双功能 Agent 自验 PASS + 用户验收 |
| M3 | D6-D8 | P1.1 Agent 持久化 + 可视化编排 | Agent 重启不丢失 |
| M4 | D9-D10 | P1.2 GraphRAG + P1.3 MCP Server | 图谱问答可用 + MCP 客户端可调用 |
| M5 | D11-D12 | P1.4 CI/Docker/文档 + P2.1 演示模式 | CI 绿 + 一键演示 |
| M6 | D13-D14 | P2.2 双端同步 + P2.3 高级检索 + 总验收 | 手机可访问 + 简历素材 |

---

## 二、实施步骤（Task 分解）

### Phase 0：仓库清理（D1）

**T0.1 清理根目录临时文件**
- 删除：`_tmp_*`（10+ 个目录）、`backups/`、根目录 40+ 日志文件、`api-verify.log/.err.log`
- 保留：`docs/`、`scripts/`、`releases/`（审查后定）
- 检查 `.gitignore` 覆盖所有生成物

**T0.2 检查 open-notebook/ 内部清理**
- 删除：`*.log`、`exe_*.log`、`build/`、`dist/`、`surreal_data/`、`db/`、`data/`（确认 gitignore）
- 确认 `.env` / `.venv` / `node_modules` 不入库

**T0.3 基线验证**
- SurrealDB + API 启动 → `/health` 200
- `uv run pytest tests/` 全绿
- 前端 `npm run build` 通过

**T0.4 生成测试 PDF**
- 用 reportlab 生成 `data/demo/ai-agent-review.pdf`（技术主题，中文+英文混合）

### Phase 1：P0 功能（D2-D5）

**T1.1 混合检索服务**（`open_notebook/search/`）
- `hybrid.py`：`HybridSearchService`（双路召回 + RRF + Rerank 可选）
- `rerank.py`：Rerank 适配层（OpenAI-compatible / 本地模型 / 禁用降级）
- 恢复 `text_search` FULLTEXT 支持（查 SurrealDB schema，必要时加 BM25 内存实现）
- `ask.py` 接入混合检索
- 新增 `POST /api/search/hybrid` 调试端点

**T1.2 RAG 评估服务**（`api/eval_service.py` + `api/routers/eval.py`）
- 内置评估集 `tests/eval/questions.json`（20+ 中文题，覆盖公考 PDF + AI 综述 PDF）
- RAGAS 指标计算（faithfulness / answer_relevancy / context_precision / context_recall）
- 评估报告存储（SurrealDB 或 JSON）
- 前端 `eval/page.tsx`：仪表盘 + 雷达图 + 逐题明细
- 依赖：`ragas`（pip install）

**T1.3 Agent 自验 + 用户验收 M1/M2**

### Phase 2：P1 功能（D6-D10）

**T2.1 Agent 持久化**（`agent_service.py` 重构）
- Agent / AgentTask 模型持久化到 SurrealDB
- scheduler 从 DB 读任务 + 状态落库
- 前端 `agents/page.tsx` 升级为可视化编排（DAG 面板）

**T2.2 GraphRAG**（`api/routers/knowledge-graph.py` 扩展）
- 实体/关系 LLM 抽取 → 图谱存储
- 检索：图谱路径 + 向量双通道 → LLM 综合
- `POST /api/knowledge-graph/ask`

**T2.3 MCP Server**（`api/mcp_server.py`）
- FastMCP 暴露：list_notebooks / hybrid_search / ask_knowledge_base / create_note
- 独立进程 + 文档（MCP Inspector 验证步骤）
- 依赖：`fastmcp`

**T2.4 自验 + 用户验收 M3/M4**

### Phase 3：工程化 + 演示（D11-D12）

**T3.1 GitHub Actions**（`.github/workflows/ci.yml`）
- lint（ruff）→ test（pytest）→ build（frontend + docker）

**T3.2 Docker 一键部署**
- 完善 `docker-compose.yml`（SurrealDB + API + Frontend）
- 测试：`docker compose up -d` 全链路

**T3.3 一键演示模式**（`scripts/demo/`）
- `seed_demo_data.py`：导入公考 PDF + AI 综述 PDF → 笔记本 + 笔记 + 洞察
- `start-demo.bat`：一键启动
- README 更新（快速开始）

### Phase 4：P2 + 总验收（D13-D14）

**T4.1 双端同步**（Tailscale）
- 文档：Tailscale 安装 → 手机装 APK → 访问
- 复用 `TAILSCALE_DOMAIN` / `CLOUDFLARE_DOMAIN` 配置
- 实际验证（需用户手机配合）

**T4.2 高级检索**（HyDE + 语义缓存 + 自适应路由）
- `open_notebook/search/hyde.py`、`cache.py`、`router.py`
- 配置开关，默认开启缓存

**T4.3 H 系列（尽力）**
- 思维导图/闪卡/测验（Studio 扩展）
- A2A 消息协议

**T4.4 总验收 + 演示视频 + 简历素材**

---

## 三、并行策略

| 并行组 | 负责 | 依赖 |
|--------|------|------|
| 组 A：混合检索 + 评估（后端） | T1.1, T1.2 | 无 |
| 组 B：Agent + MCP + GraphRAG | T2.1, T2.2, T2.3 | 需 API 契约 |
| 组 C：前端页面（eval/agents/debug） | T1.2-frontend, T2.1-frontend | 需后端 OpenAPI |
| 组 D：工程化 + 文档 + 演示 | T0, T3, T4 | 无 |

**并行原则**：先定 Pydantic 契约（`api/models.py` 增 schema）→ 并行开发 → 集成测试收口。

---

## 四、依赖安装清单

```bash
cd open-notebook
uv add ragas fastmcp rank-bm25
```

---

## 五、验收流程（双验证）

每个 Task 完成 → **Agent 自验**（6 项检查，输出 PASS/FAIL 报告）→ **用户验收**（6 项打勾清单）。详见设计文档第七节。

---

## 六、风险清单

| 风险 | 对策 |
|------|------|
| ragas 安装失败/依赖重 | 降级：自实现 faithfulness 打分 |
| SurrealDB FULLTEXT 不兼容 | 降级：rank_bm25 内存 BM25 |
| 两周不够 | P2.3 / H 系列为尽力项 |
| 无 Claude Desktop | MCP Inspector + 自写客户端验证（已确认） |
