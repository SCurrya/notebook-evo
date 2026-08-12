# 技术决策说明（Tech Decisions）

> 面试参考：本文档解释每个关键架构选择背后的"为什么"，以及我们考虑的替代方案。
> 这不是"哪个更好"的争论记录，而是**为什么这个项目选这个**的工程决策说明。

## 1. 数据库：SurrealDB（而非 PostgreSQL + pgvector）

**选择**：SurrealDB（文档+图+向量+全文，一体化）

**原因**：
- **一体化**：笔记本/来源/笔记/洞察/图谱关系都在一个库里，省去多数据库同步复杂度
- **图查询原生支持**：`RELATE source->reference->notebook` 直接表达知识图谱关系，比 join 表清晰
- **BM25 内置**：`SEARCH ANALYZER ... BM25` 直接做全文检索
- **嵌入式部署**：单二进制 rocksdb 后端，零运维，适合本地优先场景
- **多语言 SDK**：Python 异步驱动天然适配 FastAPI

**替代方案**：
- PostgreSQL + pgvector：成熟但需要搭 pgvector + tsvector + 图插件（AGE），配置复杂
- Qdrant + Postgres：向量检索最佳但图关系弱
- MongoDB + Atlas Search：商业化、文档友好但向量弱

**代价**：SurrealDB 2.x 较新，生产案例少，部分高级查询语法与 SQL 差异大。

## 2. 中文检索：jieba + rank_bm25 fallback

**选择**：原生 BM25 失败时切到 jieba + rank_bm25 的 Python 内存索引

**问题**：SurrealDB 2.3.7 的内置 token analyzer 对中文（CJK）支持弱——单字或无意义的二元组，混合检索几乎召回不到

**解决**：双层 fallback
1. 检测 query 是否含 CJK（`[\u4e00-\u9fff]` 正则）
2. 是 → 用 `rank_bm25.BM25Okapi` 在 Python 进程内构建索引
3. 仍 RRF 融合向量和 BM25 分数

**替代方案**：
- 装 jieba SDK 给 SurrealDB（侵入式、需要自编译）
- 切换到 ElasticSearch / Meilisearch（重、额外服务）
- 调用外部 API（如腾讯云 ES）（外部依赖）

**理由**：零外部依赖、几行代码、面试可讲清楚权衡。

## 3. 跨 Provider 模型降级（而非单一 Provider 重试）

**选择**：探测每个 Provider → 自动降级链（xcode.best → SenseNova → OpenRouter）

**问题**：单一 Provider 频繁 503/限流（面试场景常见的"模型挂了"问题）

**设计**：
- **启动探测**：`ensure_preferred_provider_setup()` 用 chat completion 试探每个 Provider
- **优先级可配**：`MODEL_PROVIDER_PRIORITY` 环境变量一行调整顺序
- **运行期降级**：`ask.py` 的 `_fallback_chain` 同 provider hints → 同 provider → 跨 provider
- **冷却缓存**：进程内 5 分钟内已知 503 模型直接跳过

**替代方案**：
- 单一 Provider + retry + backoff：碰到持续故障无效
- 智能路由（按 query 类型选模型）：复杂度高、效果不稳定
- 永远用最贵的 Provider：成本失控

**代价**：fallback 链首次慢（要试 3-4 个 Provider）。

## 4. LangGraph（而非直接调 LLM API）

**选择**：用 LangGraph 状态图编排 RAG/Source Chat/Agent

**原因**：
- **可中断**：人类可在中间节点确认/修改
- **可持久化**：SqliteSaver checkpointing，跨重启恢复
- **可观察**：每步状态可见，调试容易
- **可组合**：子图复用（Source Chat 和 Ask 都用同一 retrieval node）

**替代方案**：
- 直接 LLM API + 手动状态管理：灵活但 50+ 行 boilerplate
- AutoGen / CrewAI：多智能体合适但单智能体场景过度
- LlamaIndex：偏数据框架，对话流不如 LangGraph 灵活

## 5. Next.js 16 App Router（而非 Pages Router）

**选择**：Next.js 16 + React 19 + Server Components

**原因**：
- 服务端组件减少 JS bundle（首屏快）
- 内置 i18n、metadata API
- static export（`next export`）支持离线/单页部署
- 移动端 PWA（service worker、manifest）

**替代方案**：
- Vite + React Router：更轻但失去 RSC
- Astro：内容站优秀但交互性弱

## 6. 密码认证 + Bearer（而非 OAuth/JWT）

**选择**：单一密码（`OPEN_NOTEBOOK_PASSWORD`）→ Bearer token + 恒时比较

**原因**：
- **场景简单**：本地部署、单一用户、信任客户端
- **零依赖**：不用架设 OAuth 服务
- **恒时比较**：`secrets.compare_digest` 防时序攻击
- **可演进**：留好接口，未来加 JWT/OAuth 只需替换 middleware

**替代方案**：
- JWT：本地场景无意义，且密钥管理复杂
- OAuth：需要外部 IdP，本地部署不可行

## 7. self-hosted 优先（而非 SaaS）

**选择**：所有数据本地（SurrealDB rocksdb 文件、上传文件本地、模型 key 用户自配）

**原因**：
- **隐私**：研究资料/笔记可能含敏感内容
- **成本**：自托管零边际成本
- **可控**：不被厂商策略变化影响
- **面试亮点**：体现隐私意识，符合当下 AI 产品的核心价值

**代价**：部署门槛（用户自己起 SurrealDB/API/前端）—— 我们提供 Docker Compose + 一键脚本降低门槛。

---

**总结**：每个选择都遵循"在隐私/简单/可控优先"的项目价值观。面试时如果被问，可以直接引用本文档作为回答。