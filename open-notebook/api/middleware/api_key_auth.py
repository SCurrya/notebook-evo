"""
API Key 认证中间件。

支持通过 `X-API-Key` 请求头或 `Authorization: ApiKey <key>` 进行 API Key 认证。
- 仅当请求携带 API Key 时才进行校验，否则放行（由其他认证机制处理）
- 校验通过后，将 ApiKey 对象附加到 request.state.api_key
- 自动更新 last_used_at 字段

注意：API Key 仅存储 SHA-256 哈希，明文不落库。
"""

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from open_notebook.domain.api_key import ApiKey, hash_api_key
from open_notebook.utils.logger import Operation, Result, get_logger

# 请求头中 API Key 的字段名
API_KEY_HEADER = "X-API-Key"
# 备用：Authorization 头中的 scheme
API_KEY_AUTH_SCHEME = "ApiKey"


async def _extract_api_key(request: Request) -> Optional[str]:
    """从请求中提取 API Key。"""
    # 1. 优先从 X-API-Key 头获取
    key = request.headers.get(API_KEY_HEADER)
    if key:
        return key.strip()
    # 2. 从 Authorization: ApiKey <key> 获取
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            scheme, credentials = auth_header.split(" ", 1)
            if scheme.lower() == API_KEY_AUTH_SCHEME.lower():
                return credentials.strip()
        except ValueError:
            pass
    return None


async def _authenticate_api_key(request: Request) -> Optional[ApiKey]:
    """尝试用 API Key 认证请求，返回 ApiKey 对象或 None。"""
    raw_key = await _extract_api_key(request)
    if not raw_key:
        return None

    key_hash = hash_api_key(raw_key)
    api_key = await ApiKey.get_by_key_hash(key_hash)
    if api_key is None:
        return None

    # 更新最后使用时间（异步执行，不阻塞请求）
    try:
        await api_key.touch()
    except Exception as e:
        get_logger(
            "api_key_auth", Operation.UPDATE, "-", Result.FAILURE
        ).warning(f"更新 last_used_at 失败: {e}")

    return api_key


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件。

    - 当请求携带 API Key 时，校验并附加到 request.state.api_key
    - 当请求不携带 API Key 时，放行（由其他认证机制处理）
    - 校验失败时返回 401
    """

    async def dispatch(self, request: Request, call_next):
        # 仅当请求携带 API Key 时才进行校验
        raw_key = await _extract_api_key(request)
        if raw_key:
            key_hash = hash_api_key(raw_key)
            api_key = await ApiKey.get_by_key_hash(key_hash)
            if api_key is None:
                get_logger(
                    "api_key_auth", Operation.READ, "-", Result.FAILURE
                ).warning("API Key 认证失败：无效的 key")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "无效的 API Key"},
                )
            # 附加到 request.state 供后续使用
            request.state.api_key = api_key
            # 更新最后使用时间（不阻塞请求）
            try:
                await api_key.touch()
            except Exception as e:
                get_logger(
                    "api_key_auth", Operation.UPDATE, "-", Result.FAILURE
                ).warning(f"更新 last_used_at 失败: {e}")

        return await call_next(request)
