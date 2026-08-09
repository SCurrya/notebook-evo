"""
共享域模型。

定义笔记本共享链接（ShareLink），支持通过 token 访问笔记本。
权限级别：
- READ_ONLY：只读
- COMMENT：可评论
- EDIT：可编辑
"""

import secrets
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger

# 权限级别常量
PERMISSION_READ_ONLY = "READ_ONLY"
PERMISSION_COMMENT = "COMMENT"
PERMISSION_EDIT = "EDIT"
VALID_PERMISSIONS = {PERMISSION_READ_ONLY, PERMISSION_COMMENT, PERMISSION_EDIT}


def generate_share_token() -> str:
    """生成一个安全的随机共享 token。"""
    return secrets.token_urlsafe(24)


class ShareLink(ObjectModel):
    """笔记本共享链接。"""

    table_name: ClassVar[str] = "share_link"
    nullable_fields: ClassVar[set[str]] = {"expires_at", "created_by", "notebook_id"}

    notebook_id: str = Field(..., description="被共享的笔记本 ID")
    token: str = Field(..., description="访问 token")
    permissions: str = Field(
        PERMISSION_READ_ONLY, description="权限级别（READ_ONLY/COMMENT/EDIT）"
    )
    expires_at: Optional[datetime] = Field(
        None, description="过期时间（None 表示永不过期）"
    )
    created_by: Optional[str] = Field(
        None, description="创建者标识"
    )

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: str) -> str:
        if v not in VALID_PERMISSIONS:
            raise InvalidInputError(
                f"无效的权限级别: {v}，必须为 {', '.join(sorted(VALID_PERMISSIONS))}"
            )
        return v

    @field_validator("token")
    @classmethod
    def token_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidInputError("共享 token 不能为空")
        return v.strip()

    def _prepare_save_data(self) -> Dict[str, Any]:
        """准备保存数据，将 notebook_id 转换为 RecordID。"""
        data = super()._prepare_save_data()
        if data.get("notebook_id"):
            data["notebook_id"] = ensure_record_id(data["notebook_id"])
        return data

    def is_expired(self) -> bool:
        """检查共享链接是否已过期。"""
        if self.expires_at is None:
            return False
        # 处理可能为字符串的情况
        expires = self.expires_at
        if isinstance(expires, str):
            try:
                expires = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except ValueError:
                return True
        now = datetime.now(timezone.utc)
        # 确保 expires 带有时区信息
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    @classmethod
    async def get_by_token(cls, token: str) -> Optional["ShareLink"]:
        """通过 token 获取共享链接。"""
        get_logger(
            "share_domain", Operation.READ, f"token=***"
        ).debug("-> get_by_token()")
        results = await repo_query(
            "SELECT * FROM share_link WHERE token = $share_token LIMIT 1",
            {"share_token": token},
        )
        if not results:
            return None
        try:
            link = cls(**results[0])
            get_logger(
                "share_domain", Operation.READ, "-", Result.SUCCESS
            ).info("<- get_by_token() found")
            return link
        except Exception as e:
            get_logger(
                "share_domain", Operation.READ, "-", Result.FAILURE
            ).warning(f"跳过无效共享链接: {e}")
            return None

    @classmethod
    async def get_by_notebook(cls, notebook_id: str) -> List["ShareLink"]:
        """获取笔记本的所有共享链接。"""
        get_logger(
            "share_domain", Operation.READ, f"notebook_id={notebook_id}"
        ).debug("-> get_by_notebook()")
        results = await repo_query(
            "SELECT * FROM share_link WHERE notebook_id = $notebook_id ORDER BY created DESC",
            {"notebook_id": ensure_record_id(notebook_id)},
        )
        links = []
        for row in results:
            try:
                links.append(cls(**row))
            except Exception as e:
                get_logger(
                    "share_domain",
                    Operation.READ,
                    f"notebook_id={notebook_id}",
                    Result.FAILURE,
                ).warning(f"跳过无效共享链接: {e}")
        get_logger(
            "share_domain",
            Operation.READ,
            f"notebook_id={notebook_id}",
            Result.SUCCESS,
        ).info(f"<- get_by_notebook() count={len(links)}")
        return links
