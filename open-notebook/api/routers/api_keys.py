"""
API Key 管理路由器。

提供以下端点：
- POST   /api/api-keys        创建 API Key（返回明文，仅此一次）
- GET    /api/api-keys        列出所有 API Keys（不返回明文）
- DELETE /api/api-keys/{id}   撤销 API Key

安全说明：
- API Key 使用 SHA-256 哈希存储，明文仅在创建时返回一次
- 列表接口仅返回元数据（name, permissions, created, last_used_at 等）
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from open_notebook.domain.api_key import ApiKey, generate_api_key, hash_api_key
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _to_response(key: ApiKey) -> ApiKeyResponse:
    """将 ApiKey 域对象转换为响应模型（不含明文）。"""
    last_used = key.last_used_at
    if isinstance(last_used, datetime):
        last_used = last_used.isoformat()
    return ApiKeyResponse(
        id=key.id or "",
        name=key.name,
        permissions=key.permissions or [],
        created=str(key.created) if key.created else "",
        updated=str(key.updated) if key.updated else "",
        last_used_at=last_used,
    )


@router.post("", response_model=ApiKeyCreateResponse)
async def create_api_key(data: ApiKeyCreateRequest):
    """创建 API Key。返回明文 key，仅此一次，请妥善保存。"""
    log = get_logger("api_keys_api", Operation.CREATE, f"name={data.name}")
    log.debug("-> create_api_key()")
    try:
        raw_key = generate_api_key()
        api_key = ApiKey(
            name=data.name,
            key_hash=hash_api_key(raw_key),
            permissions=data.permissions or ["read"],
        )
        await api_key.save()
        log.bind(result=Result.SUCCESS).info(
            f"<- create_api_key() id={api_key.id}"
        )
        return ApiKeyCreateResponse(
            id=api_key.id or "",
            name=api_key.name,
            key=raw_key,
            permissions=api_key.permissions or [],
            created=str(api_key.created) if api_key.created else "",
            message="请妥善保存此 API Key，出于安全考虑不会再次显示",
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建 API Key 失败: {e}")
        get_logger(
            "api_keys_api",
            Operation.CREATE,
            f"name={data.name}",
            Result.FAILURE,
        ).error(f"create_api_key() failed: {e}")
        raise HTTPException(status_code=500, detail=f"创建 API Key 失败: {str(e)}")


@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys():
    """列出所有 API Keys（不返回明文）。"""
    log = get_logger("api_keys_api", Operation.READ)
    log.debug("-> list_api_keys()")
    try:
        keys = await ApiKey.get_all(order_by="created desc")
        log.bind(result=Result.SUCCESS).info(
            f"<- list_api_keys() count={len(keys)}"
        )
        return [_to_response(k) for k in keys]
    except Exception as e:
        logger.error(f"列出 API Keys 失败: {e}")
        get_logger(
            "api_keys_api", Operation.READ, "-", Result.FAILURE
        ).error(f"list_api_keys() failed: {e}")
        raise HTTPException(status_code=500, detail=f"列出 API Keys 失败: {str(e)}")


@router.delete("/{key_id}")
async def revoke_api_key(key_id: str):
    """撤销（删除）API Key。"""
    log = get_logger("api_keys_api", Operation.DELETE, f"key_id={key_id}")
    log.debug("-> revoke_api_key()")
    try:
        key = await ApiKey.get(key_id)
        await key.delete()
        log.bind(result=Result.SUCCESS).info("<- revoke_api_key() ok")
        return {"message": "API Key 已撤销"}
    except Exception as e:
        logger.error(f"撤销 API Key 失败: {e}")
        get_logger(
            "api_keys_api",
            Operation.DELETE,
            f"key_id={key_id}",
            Result.FAILURE,
        ).error(f"revoke_api_key() failed: {e}")
        raise HTTPException(status_code=500, detail=f"撤销 API Key 失败: {str(e)}")
