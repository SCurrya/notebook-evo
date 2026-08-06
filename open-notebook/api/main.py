# Load environment variables
from dotenv import load_dotenv

load_dotenv()

import os
import sys
import importlib
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

# === 统一日志系统配置 ===
# 导入统一日志模块，自动配置结构化格式和默认 extra 字段
from open_notebook.utils.logger import LOG_FORMAT, Operation, Result, get_logger

# === 日志轮转配置：50MB 轮转，保留 10 天 ===
import pathlib
_log_dir = pathlib.Path(__file__).parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)
logger.add(
    str(_log_dir / "api_{time:YYYY-MM-DD}.log"),
    rotation="50 MB",
    retention="10 days",
    compression="zip",
    level="INFO",
    encoding="utf-8",
    format=LOG_FORMAT,
)

from api.auth import PasswordAuthMiddleware
from api.middleware.api_key_auth import ApiKeyAuthMiddleware
from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ExternalServiceError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
    OpenNotebookError,
    RateLimitError,
)
from open_notebook.utils.encryption import get_secret_from_env


def _parse_cors_origins(raw: str) -> list[str]:
    """Parse CORS_ORIGINS env value into a list of origins."""
    value = raw.strip()
    if value == "*":
        return ["*"]
    return [origin.strip() for origin in value.split(",") if origin.strip()]


# Parsed once at module load; CORS_ORIGINS changes require a restart.
_cors_origins_raw = os.getenv("CORS_ORIGINS")
CORS_ALLOWED_ORIGINS = _parse_cors_origins(_cors_origins_raw or "*")
CORS_IS_DEFAULT_WILDCARD = _cors_origins_raw is None

api_prefix = "/api"


def _include_router_module(module_name: str, required: bool = True) -> bool:
    started = time.perf_counter()
    logger.info(f"API: importing router module {module_name}...")
    try:
        module = importlib.import_module(f"api.routers.{module_name}")
        router = getattr(module, "router", None)
        if router is None:
            logger.warning(f"API: router {module_name} has no router attr")
            return False
        app.include_router(router, prefix=api_prefix, tags=[module_name])
        logger.info(
            f"API: router {module_name} registered in "
            f"{time.perf_counter() - started:.2f}s"
        )
        return True
    except Exception as e:
        log = logger.error if required else logger.warning
        log(
            f"API: failed to import router {module_name} after "
            f"{time.perf_counter() - started:.2f}s: {e}"
        )
        if required:
            raise
        return False


def _load_optional_routers() -> None:
    for module_name in [
        "context",
        "embedding",
        "embedding_rebuild",
        "insights",
        "languages",
        "episode_profiles",
        "speaker_profiles",
        "podcasts",
        "transformations",
        "video",
        "logs",
        "ppt",
        "blog",
        "pdf",
        "image",
    ]:
        try:
            _include_router_module(module_name, required=False)
        except Exception:
            pass


def _cors_headers(request: Request) -> dict[str, str]:
    """
    Build CORS headers for error responses.

    Mirrors Starlette CORSMiddleware behavior: reflects the request Origin
    when the origin is allowed (or when wildcard is configured, since
    browsers reject `Access-Control-Allow-Origin: *` combined with
    credentials). Omits `Access-Control-Allow-Origin` for disallowed
    origins so the browser blocks the error body from leaking cross-origin.
    """
    origin = request.headers.get("origin")
    headers: dict[str, str] = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }

    if origin and ("*" in CORS_ALLOWED_ORIGINS or origin in CORS_ALLOWED_ORIGINS):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"

    return headers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for the FastAPI application.
    Runs database migrations automatically on startup.
    """
    # Startup: Security checks
    logger.info("Starting API initialization...")

    # Security check: Encryption key
    if not get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY"):
        logger.warning(
            "OPEN_NOTEBOOK_ENCRYPTION_KEY not set. "
            "API key encryption will fail until this is configured. "
            "Set OPEN_NOTEBOOK_ENCRYPTION_KEY to any secret string."
        )

    # Run database migrations

    try:
        migration_manager = AsyncMigrationManager()
        current_version = await migration_manager.get_current_version()
        logger.info(f"Current database version: {current_version}")

        if await migration_manager.needs_migration():
            logger.warning("Database migrations are pending. Running migrations...")
            await migration_manager.run_migration_up()
            new_version = await migration_manager.get_current_version()
            logger.success(
                f"Migrations completed successfully. Database is now at version {new_version}"
            )
        else:
            logger.info(
                "Database is already at the latest version. No migrations needed."
            )
    except Exception as e:
        logger.error(f"CRITICAL: Database migration failed: {str(e)}")
        logger.exception(e)
        # Fail fast - don't start the API with an outdated database schema
        raise RuntimeError(f"Failed to run database migrations: {str(e)}") from e

    # Run podcast profile data migration (legacy strings -> Model registry)
    try:
        from open_notebook.podcasts.migration import migrate_podcast_profiles

        await migrate_podcast_profiles()
    except Exception as e:
        logger.warning(f"Podcast profile migration encountered errors: {e}")
        # Non-fatal: profiles can be migrated manually via UI

    try:
        from open_notebook.ai.provider_defaults import ensure_preferred_provider_setup

        await ensure_preferred_provider_setup()
    except Exception as e:
        logger.warning(f"Preferred AI provider setup encountered errors: {e}")

    logger.success("API initialization completed successfully")

    # Start the multi-agent task scheduler
    try:
        from api.agent_service import AgentManager

        await AgentManager.get_instance().start_scheduler()
        logger.info("Multi-agent scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start agent scheduler: {e}")

    threading.Thread(
        target=_load_optional_routers,
        name="optional-router-loader",
        daemon=True,
    ).start()

    # Yield control to the application
    yield

    # Shutdown: stop agent scheduler and cleanup
    try:
        from api.agent_service import AgentManager

        await AgentManager.get_instance().stop_scheduler()
    except Exception:
        pass
    logger.info("API shutdown complete")


app = FastAPI(
    title="Open Notebook API",
    description=(
        "API for Open Notebook - Research Assistant\n\n"
        "## 认证方式\n\n"
        "支持以下两种认证方式：\n\n"
        "1. **Bearer 认证**：在 `Authorization` 头中传入 `Bearer <password>`\n"
        "2. **API Key 认证**：在 `X-API-Key` 头中传入 API Key，或在 "
        "`Authorization` 头中传入 `ApiKey <key>`\n\n"
        "API Key 可通过 `/api/api-keys` 接口创建（仅返回明文一次）。\n"
    ),
    lifespan=lifespan,
)

if CORS_IS_DEFAULT_WILDCARD:
    logger.warning(
        "CORS_ORIGINS is not set — API accepts cross-origin requests from any "
        "origin (default: '*'). For production deployments, set CORS_ORIGINS to "
        "your frontend origin(s), e.g. "
        "CORS_ORIGINS=https://notebook.example.com"
    )
else:
    logger.info(f"CORS allowed origins: {CORS_ALLOWED_ORIGINS}")

# Add password authentication middleware first
# Exclude /api/auth/status and /api/config from authentication
app.add_middleware(
    PasswordAuthMiddleware,
    excluded_paths=[
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/status",
        "/api/config",
    ],
)

# Add API Key authentication middleware
# 仅当请求携带 API Key 时才进行校验，否则放行（由其他认证机制处理）
app.add_middleware(ApiKeyAuthMiddleware)

# Add CORS middleware last (so it processes first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handler to ensure CORS headers are included in error responses
# This helps when errors occur before the CORS middleware can process them
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Custom exception handler that ensures CORS headers are included in error responses.
    This is particularly important for 413 (Payload Too Large) errors during file uploads.

    Note: If a reverse proxy (nginx, traefik) returns 413 before the request reaches
    FastAPI, this handler won't be called. In that case, configure your reverse proxy
    to add CORS headers to error responses.
    """
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path} method={request.method}",
        Result.FAILURE,
    ).warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={**(exc.headers or {}), **_cors_headers(request)},
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).warning(f"Not found: {exc}")
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_error_handler(request: Request, exc: InvalidInputError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).warning(f"Invalid input: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).warning(f"Authentication error: {exc}")
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).warning(f"Rate limited: {exc}")
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).error(f"Configuration error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(NetworkError)
async def network_error_handler(request: Request, exc: NetworkError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).error(f"Network error: {exc}")
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).error(f"External service error: {exc}")
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(OpenNotebookError)
async def open_notebook_error_handler(request: Request, exc: OpenNotebookError):
    get_logger(
        "api_main", Operation.READ, f"path={request.url.path}", Result.FAILURE,
    ).error(f"Unhandled OpenNotebookError: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


# Include routers
for _required_mod in [
    "auth",
    "notebooks",
    "credentials",
    "search",
    "models",
    "notes",
    "settings",
    "sources",
    "chat",
    "source_chat",
    "share",
    "api_keys",
    "eval",
    "agents",
    "knowledge_graph",
    "config",
]:
    _include_router_module(_required_mod, required=True)


@app.get("/")
async def root():
    """返回前端 index.html（如可用），否则返回 API 健康消息"""
    frontend_dir = _get_frontend_dir()
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Open Notebook API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# === 静态文件服务（前端 Next.js 构建） ===
def _get_frontend_dir() -> pathlib.Path:
    """获取前端静态文件目录（兼容 PyInstaller 打包）"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后：_MEIPASS/frontend/index.html
        candidate = pathlib.Path(sys._MEIPASS) / "frontend"
        if candidate.exists():
            return candidate
    # 开发模式：从 api/main.py 上溯到项目根，再到 frontend/out
    project_root = pathlib.Path(__file__).parent.parent
    for rel in ("frontend/out", "frontend"):
        candidate = project_root / rel
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
    return project_root / "frontend"  # 返回默认（即使不存在）


# 在所有 API 路由注册之后再挂载静态文件（API 路由优先级更高）
_frontend_dir = _get_frontend_dir()
if _frontend_dir.exists() and (_frontend_dir / "index.html").exists():
    # 1. 挂载 /_next/、/static/、/assets/ 等子目录
    for sub in ("_next", "static", "assets", "icons"):
        sub_path = _frontend_dir / sub
        if sub_path.exists() and sub_path.is_dir():
            app.mount(f"/{sub}", StaticFiles(directory=str(sub_path)), name=sub)

    # 2. /favicon.ico 路由
    @app.get("/favicon.ico")
    async def favicon():
        fav = _frontend_dir / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav))
        # 返回 1x1 透明 ICO 避免 404
        return Response(
            content=b"\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x30\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            media_type="image/x-icon",
        )

    # 3. SPA 路由 fallback（/notebooks/123 等深链接）
    # 注册所有 HTTP 方法，避免非 GET 请求命中 catch-all 时返回 405
    # （非 GET 请求到非 API 路径应返回 404，而非 405）
    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )
    async def spa_fallback(full_path: str, request: Request):
        # API 路径已在前面注册；这里只处理前端资源/路由
        if full_path.startswith(("api/", "_next/", "static/", "assets/", "icons/")):
            return JSONResponse(
                {"detail": "Not found", "path": full_path},
                status_code=404,
                headers=_cors_headers(request),
            )
        # 非 GET/HEAD 请求到前端路由路径：返回 404（避免 405 误导）
        if request.method not in ("GET", "HEAD"):
            return JSONResponse(
                {"detail": "Method not allowed on frontend route", "path": full_path},
                status_code=404,
                headers=_cors_headers(request),
            )
        # 尝试返回具体静态文件
        file_path = _frontend_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # 否则返回 index.html（SPA 由前端路由处理）
        index = _frontend_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse(
            {"detail": "Frontend index not found"},
            status_code=404,
            headers=_cors_headers(request),
        )

    logger.info(f"Frontend served from: {_frontend_dir}")
else:
    logger.warning(f"Frontend dir not found or no index.html: {_frontend_dir}")

