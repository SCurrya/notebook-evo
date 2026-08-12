# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Root `README.md` for the GitHub homepage (repo previously rendered blank)
- `MODEL_PROVIDER_PRIORITY` env — configurable cross-provider fallback ordering
  (`sensenova, openai_compatible, openrouter`)

### Fixed
- SenseNova compatible-mode base URL (`api.sensenova.cn` → `token.sensenova.cn`)
  — all SenseNova requests previously returned 403

## [1.2.0] - 2026-08-10

### Added
- **Notebook export center** — structured Markdown/JSON export (`GET
  /api/notebooks/{id}/export/json`, `open-notebook-json-v1` format)
- **Analytics dashboard** — `/` homepage now shows 8 stat cards + recent
  notebooks + quick links (`GET /api/analytics/summary`)
- **Knowledge graph in notebook detail** — new "graph" tab on mobile with
  entity/relation counts, one-click extraction, GraphView + EntityPanel
- **Share-link access tracking** — `access_count` + `last_accessed_at` on
  every shared view
- **Daily auto-backup** — Windows scheduled task (`OpenNotebook-AutoBackup`)
  keeps the last 5 snapshots
- **Search/ask history** — persistent localStorage chips for quick replay
- **System health panel** — `/api/system/status` now includes `db_stats`
  (record counts for notebooks/sources/notes/tasks/insights)

### Fixed
- **Source Chat read full text** — `ContextBuilder.build()` ignored
  `ContextConfig.sources`; chat prompts only contained source metadata
  (43 tokens) instead of the body (2305 tokens)
- **Share links were broken** — `token` is a SurrealDB protected variable;
  renamed the query param to `$share_token`
- **Async command registration** — `api/main.py` now imports command modules,
  so `embed_note` / `embed_source` / `process_source` work under uvicorn reload
- **Relationship direction** — `source->reference->notebook` queries in
  notebooks/sources routers used inverted `in`/`out` (source_count was
  always 0, notebook filtering in search was no-op)
- **Mobile build** — cleared IDE-injected `NODE_OPTIONS` (safe-delete shim
  caused `genie-trash ETIMEDOUT` during `.next` cleanup)

## [1.1.0] - 2026-08-08

### Added
- **Password authentication** — Bearer password middleware (constant-time
  compare) for all API routes; Swagger docs also protected
- **System health page** (`/system`) with 30s auto-refresh
- **Share QR codes** in the share dialog
- **PWA enhancements** — Chinese manifest, PNG icons (192/512 + maskable),
  drawer sidebar on phones (<768px)
- **Studio routes registered** — report/FAQ/timeline generators activated
- **Ops scripts** — `backup-data.ps1`, `get-tunnel-url.ps1`, `demo-mode.ps1`

### Fixed
- `start-all.bat` database mismatch (`open-notebook-data` vs `surreal_data`)
  — mobile/desktop now share one dataset
- Shared URL format bug (`/shared/token` → `/shared?token=`)
- Frontend connection-error overlay scroll

## [1.0.0] - 2026-08-05

### Added
- Cross-provider model fallback chain in the ask graph
- Chinese BM25 retrieval fallback (jieba + rank_bm25) for SurrealDB
  tokenizers that don't support CJK
- SSRF / DNS-rebinding protection (`url_validation.py`)
- SurrealQL injection hardening (parameter binding)
- Fixed Jinja2 template injection (fixed templates)

[Unreleased]: https://github.com/SCurrya/notebook-evo/compare/v1.2.0...master
[1.2.0]: https://github.com/SCurrya/notebook-evo/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/SCurrya/notebook-evo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/SCurrya/notebook-evo/releases/tag/v1.0.0
