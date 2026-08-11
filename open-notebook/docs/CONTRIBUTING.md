# Contributing to Notebook-Evo

Thanks for your interest! This project is a deep enhancement of
[Open Notebook](https://github.com/lfnovo/open-notebook). Contributions are
welcome — features, bug fixes, docs, and tests.

## Development Setup

```bash
# Requires Python 3.12+ and Node 22+
cd open-notebook
uv sync

# Start SurrealDB
./surreal.exe start --user root --pass root --bind 127.0.0.1:8000 rocksdb:./surreal_data/db

# Start API
.\.venv\Scripts\python.exe run_api.py

# Start frontend (dev)
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
# Backend (360+ tests)
uv run pytest tests/ -v

# Frontend
cd frontend && npm test

# Lint
uv run ruff check api/ open_notebook/ tests/
cd frontend && npm run lint
```

## Code Style

- Python: ruff (line length 100)
- TypeScript/React: ESLint + Prettier
- Write tests for new logic — the project aims to keep the suite green

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): description
fix(scope): description
docs: description
perf(scope): description
```

## Pull Request Process

1. Fork the repo and create a branch from `master`
2. Add tests for any new behavior
3. Ensure `pytest` and `npm run lint` pass locally
4. Open a PR with a clear description

## Areas to Explore

- `open_notebook/search/` — hybrid retrieval, Chinese BM25, HyDE
- `open_notebook/graphs/` — LangGraph agents, source chat, ask graph
- `api/` — FastAPI routers, eval service, agent persistence
- `frontend/` — Next.js 16 app, i18n (14 languages)

Questions? Open an issue with the `question` label.
