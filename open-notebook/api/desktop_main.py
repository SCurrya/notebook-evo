"""
桌面 EXE 模式专用的 FastAPI 主程序（精简版）
- 启动后端核心 API
- 挂载前端静态文件
- 排除重型可选模块（podcast/transformations/advanced）以减小 EXE 体积
- 内嵌启动 surreal-commands worker（处理 PDF 源、播客等异步任务）
"""

import os
import sys
import pathlib
import threading
import asyncio
import importlib
import time
from urllib.parse import quote
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# 强制加载 .env（如果存在）
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

# === 统一日志 ===
from open_notebook.utils.logger import LOG_FORMAT

# === 日志目录（用户数据目录） ===
_data_dir = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home())) / "OpenNotebook"
_data_dir.mkdir(parents=True, exist_ok=True)
_log_dir = _data_dir / "logs"
_log_dir.mkdir(exist_ok=True)
logger.add(
    str(_log_dir / "open-notebook-{time:YYYY-MM-DD}.log"),
    rotation="50 MB",
    retention="10 days",
    compression="zip",
    level="INFO",
    encoding="utf-8",
    format=LOG_FORMAT,
)

api_prefix = "/api"


def _include_router_module(module_name: str, required: bool = True) -> bool:
    started = time.perf_counter()
    logger.info(f"Desktop API: importing router module {module_name}...")
    try:
        module = importlib.import_module(f"api.routers.{module_name}")
        router = getattr(module, "router", None)
        if router is None:
            logger.warning(f"Desktop API: router {module_name} has no router attr")
            return False
        app.include_router(router, prefix=api_prefix)
        logger.info(
            f"Desktop API: router {module_name} registered in "
            f"{time.perf_counter() - started:.2f}s"
        )
        return True
    except Exception as e:
        log = logger.error if required else logger.warning
        log(
            f"Desktop API: failed to import router {module_name} after "
            f"{time.perf_counter() - started:.2f}s: {e}"
        )
        if required:
            raise
        return False


def _load_optional_routers() -> None:
    for module_name in [
        "commands",
        "context",
        "embedding",
        "embedding_rebuild",
        "insights",
        "languages",
        "speaker_profiles",
        "episode_profiles",
    ]:
        try:
            _include_router_module(module_name, required=False)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Open Notebook Desktop starting up...")
    try:
        from open_notebook.ai.provider_defaults import ensure_preferred_provider_setup

        await ensure_preferred_provider_setup()
    except Exception as e:
        logger.warning(f"Preferred AI provider setup encountered errors: {e}")

    # Start the multi-agent task scheduler
    try:
        from api.agent_service import AgentManager

        await AgentManager.get_instance().start_scheduler()
        logger.info("Multi-agent scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start agent scheduler: {e}")

    # 启动 surreal-commands worker（线程方式）以处理 PDF/播客等异步任务
    # 这是桌面版最关键的修复：之前命令入队成功但永远停在 'new' 状态，
    # 因为没有任何进程在监听 SurrealDB 的 command live query
    _start_surreal_commands_worker()
    threading.Thread(
        target=_load_optional_routers,
        name="optional-router-loader",
        daemon=True,
    ).start()

    yield

    # Stop scheduler on shutdown
    try:
        from api.agent_service import AgentManager

        await AgentManager.get_instance().stop_scheduler()
    except Exception:
        pass
    logger.info("Open Notebook Desktop shutting down...")


def _start_surreal_commands_worker():
    """在后台线程中启动 surreal-commands worker 以处理异步命令队列。

    桌面 EXE 中没有 supervisord/CLI worker 进程，因此必须在主进程内嵌一个 worker。
    这确保上传的 PDF/链接能真正进入处理流程，而不是一直停在 'new' 状态。
    """
    def _worker_main():
        try:
            logger.info("Starting in-process surreal-commands worker...")
            # 1. 导入所有命令模块以注册到全局 registry
            import commands  # noqa: F401  # triggers commands/__init__.py
            try:
                import commands.podcast_commands  # noqa: F401
            except Exception as e:
                logger.warning(f"podcast commands unavailable: {e}")
            try:
                import commands.source_commands  # noqa: F401
            except Exception as e:
                logger.warning(f"source commands unavailable: {e}")
            try:
                import commands.embedding_commands  # noqa: F401
            except Exception as e:
                logger.warning(f"embedding commands unavailable: {e}")

            from surreal_commands.core.worker import listen_for_commands
            from surreal_commands.core.registry import registry

            registered = registry.get_all_commands()
            logger.info(
                f"Surreal-commands worker registered: "
                f"{[f'{c.app_id}.{c.name}' for c in registered]}"
            )
            if not registered:
                logger.warning(
                    "No commands registered! Async processing will not work."
                )

            # 2. 在新事件循环中跑 worker
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(listen_for_commands(max_tasks=5))
            finally:
                loop.close()
        except Exception as e:
            logger.exception(f"Surreal-commands worker crashed: {e}")

    t = threading.Thread(target=_worker_main, name="surreal-cmds-worker", daemon=True)
    t.start()
    logger.info("surreal-commands worker thread spawned")


# 创建 FastAPI 应用
app = FastAPI(
    title="Open Notebook",
    description="Open Notebook Desktop Edition",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS（桌面版允许所有来源，因为只本地访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === 通用异常处理：让 4xx/5xx 响应包含 detail 字段 ===
@app.exception_handler(StarletteHTTPException)
async def _desktop_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers or {},
    )


# 兜底：捕获所有未处理的异常，避免 500 只返回 "Internal Server Error"
from fastapi.exceptions import RequestValidationError


@app.exception_handler(Exception)
async def _desktop_generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(f"Unhandled exception in {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )

# 轻量健康检查，给桌面入口和冷启动探针使用。
@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0-desktop"}

# === API 路由（核心模块，确保 EXE 内可用） ===
for _required_mod in [
    "auth",
    "chat",
    "config",
    "credentials",
    "models",
    "notebooks",
    "notes",
    "search",
    "settings",
    "share",
    "source_chat",
    "sources",
    "api_keys",
    "podcasts",
    "transformations",
    "ppt",
    "blog",
    "pdf",
    "image",
    "video",
    "logs",
    "agents",
    "studio",
    "knowledge_graph",
]:
    _include_router_module(_required_mod, required=True)

# === 静态文件服务（前端 Next.js 构建） ===
def get_frontend_dir() -> pathlib.Path:
    """获取前端静态文件目录"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后：_MEIPASS/frontend/index.html
        candidate = pathlib.Path(sys._MEIPASS) / "frontend"
        if candidate.exists():
            return candidate
    # 开发模式：从 api/ 上溯到项目根，再到 frontend/out
    project_root = pathlib.Path(__file__).parent.parent
    for rel in ("frontend/out", "frontend"):
        candidate = project_root / rel
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
    return project_root / "frontend"  # 返回默认（即使不存在）


frontend_dir = get_frontend_dir()


def _dynamic_route_redirect(path: str) -> str | None:
    """Redirect exported dynamic routes to static detail pages with query ids."""
    normalized = path.strip("/")
    if not normalized:
        return None

    parts = normalized.split("/")
    if len(parts) < 2:
        return None

    section = parts[0]
    if section not in {"notebooks", "sources"}:
        return None

    # Keep Next.js route data files and generated static routes intact.
    if parts[1].startswith("__next") or parts[1] in {"_placeholder", "detail"}:
        return None

    param_name = "notebookId" if section == "notebooks" else "sourceId"
    return f"/{section}/detail?{param_name}={quote(parts[1], safe='')}"


def _reflect_cors(request: Request) -> dict[str, str]:
    """为错误响应反射 CORS 头（与 allow_credentials=True 兼容）。"""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,HEAD,POST,PUT,DELETE,PATCH,OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }


def _resolve_frontend_file(path: str) -> pathlib.Path | None:
    """Resolve Next static export routes such as /notebooks/detail/."""
    file_path = frontend_dir / path
    candidates = [
        file_path,
        file_path / "index.html",
    ]

    if file_path.suffix == "":
        candidates.append(file_path.with_suffix(".html"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


# 挂载静态资源（_next, assets 等）
if frontend_dir.exists():
    # 静态资源目录
    for sub in ["_next", "assets", "static", "icons"]:
        sub_path = frontend_dir / sub
        if sub_path.exists() and sub_path.is_dir():
            app.mount(f"/{sub}", StaticFiles(directory=str(sub_path)), name=sub)

    # 根路径返回 index.html
    @app.get("/")
    async def serve_index():
        index = frontend_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"error": "Frontend not built"}, status_code=500)

    # SPA fallback：所有非 /api 路径返回 index.html
    # 注册所有 HTTP 方法，避免非 GET 请求命中 catch-all 时返回 405
    @app.api_route(
        "/{path:path}",
        methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )
    async def serve_spa(path: str, request: Request):
        # API 已在前面挂载，这里只处理前端路由
        if path.startswith("api/") or path.startswith("_next/") or path.startswith("static/"):
            return JSONResponse(
                {"error": "Not found", "path": path},
                status_code=404,
                headers=_reflect_cors(request),
            )

        # 非 GET/HEAD 请求到前端路由路径：返回 404（避免 405 误导）
        if request.method not in ("GET", "HEAD"):
            return JSONResponse(
                {"error": "Method not allowed on frontend route", "path": path},
                status_code=404,
                headers=_reflect_cors(request),
            )

        # 尝试返回具体文件或 Next 静态导出的目录 index.html。
        resolved_file = _resolve_frontend_file(path)
        if resolved_file is not None:
            return FileResponse(str(resolved_file))

        dynamic_redirect = _dynamic_route_redirect(path)
        if dynamic_redirect is not None:
            return RedirectResponse(dynamic_redirect, status_code=307)

        # 否则返回 index.html（SPA 路由）
        index = frontend_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse(
            {"error": "Not found"},
            status_code=404,
            headers=_reflect_cors(request),
        )

    logger.info(f"Frontend served from: {frontend_dir}")
else:
    logger.warning(f"Frontend dir not found: {frontend_dir}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8502)
