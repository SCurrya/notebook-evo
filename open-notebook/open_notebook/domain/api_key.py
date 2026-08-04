"""
API Key 域模型。

存储用于 API 访问认证的 API Key。出于安全考虑，只存储 key 的 SHA-256 哈希值，
绝不存储明文。创建时返回明文一次，之后无法恢复。

permissions 字段存储权限列表（如 ["read", "write"]），用于细粒度访问控制。
"""

import hashlib
import secrets
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger

# API Key 前缀，便于识别
API_KEY_PREFIX = "on_"


def generate_api_key() -> str:
    """生成一个新的随机 API Key（明文，仅在创建时返回）。"""
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """计算 API Key 的 SHA-256 哈希值（用于存储和校验）。"""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


class ApiKey(ObjectModel):
    """API Key 域模型。"""

    table_name: ClassVar[str] = "api_key"
    nullable_fields: ClassVar[set[str]] = {"last_used_at", "permissions"}

    name: str = Field(..., description="API Key 名称（便于识别）")
    key_hash: str = Field(..., description="API Key 的 SHA-256 哈希值")
    permissions: List[str] = Field(
        default_factory=lambda: ["read"],
        description="权限列表（如 read/write）",
    )
    last_used_at: Optional[datetime] = Field(
        None, description="最后使用时间"
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidInputError("API Key 名称不能为空")
        return v.strip()

    @field_validator("key_hash")
    @classmethod
    def key_hash_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidInputError("key_hash 不能为空")
        return v.strip()

    @classmethod
    async def get_by_key_hash(cls, key_hash: str) -> Optional["ApiKey"]:
        """通过 key 哈希查找 API Key（用于认证）。"""
        get_logger(
            "api_key_domain", Operation.READ, "key_hash=***"
        ).debug("-> get_by_key_hash()")
        results = await repo_query(
            "SELECT * FROM api_key WHERE key_hash = $key_hash LIMIT 1",
            {"key_hash": key_hash},
        )
        if not results:
            return None
        try:
            key = cls(**results[0])
            get_logger(
                "api_key_domain", Operation.READ, "-", Result.SUCCESS
            ).info("<- get_by_key_hash() found")
            return key
        except Exception as e:
            get_logger(
                "api_key_domain", Operation.READ, "-", Result.FAILURE
            ).warning(f"跳过无效 API Key: {e}")
            return None

    @classmethod
    async def get_all(cls, order_by: Optional[str] = None) -> List["ApiKey"]:
        """获取所有 API Key（重写以处理权限字段）。"""
        order_clause = f" ORDER BY {order_by}" if order_by else ""
        results = await repo_query(
            f"SELECT * FROM api_key{order_clause}",
            {},
        )
        keys = []
        for row in results:
            try:
                keys.append(cls(**row))
            except Exception as e:
                get_logger(
                    "api_key_domain", Operation.READ, "-", Result.FAILURE
                ).warning(f"跳过无效 API Key 记录: {e}")
        return keys

    async def touch(self) -> None:
        """更新最后使用时间为当前时间。"""
        self.last_used_at = datetime.now()
        # 仅更新 last_used_at 字段
        await repo_query(
            "UPDATE $id SET last_used_at = $now",
            {"id": ensure_record_id(self.id or ""), "now": self.last_used_at},
        )
