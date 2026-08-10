"""
共享路由器。

提供以下端点：
- POST   /api/share/notebook/{notebook_id}            创建共享链接
- GET    /api/share/{token}                            通过 token 访问共享笔记本
- DELETE /api/share/{id}                               撤销共享链接
- GET    /api/share/notebook/{notebook_id}/links       列出笔记本的所有共享链接
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

from api.models import (
    SharedNotebookResponse,
    ShareLinkCreateRequest,
    ShareLinkResponse,
)
from open_notebook.domain.notebook import Notebook
from open_notebook.domain.share import (
    PERMISSION_COMMENT,
    PERMISSION_EDIT,
    PERMISSION_READ_ONLY,
    ShareLink,
    generate_share_token,
)
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter(prefix="/share", tags=["share"])


def _to_response(link: ShareLink) -> ShareLinkResponse:
    """将 ShareLink 域对象转换为响应模型。"""
    expires_at = link.expires_at
    if isinstance(expires_at, datetime):
        expires_at = expires_at.isoformat()
    # 兼容旧记录/测试 mock：字段可能缺失
    access_count = getattr(link, "access_count", 0) or 0
    last_accessed = getattr(link, "last_accessed_at", None)
    if isinstance(last_accessed, datetime):
        last_accessed = last_accessed.isoformat()
    elif last_accessed is not None and not isinstance(last_accessed, str):
        last_accessed = None
    return ShareLinkResponse(
        id=link.id or "",
        notebook_id=link.notebook_id,
        token=link.token,
        permissions=link.permissions,
        expires_at=expires_at,
        created_by=link.created_by,
        created=str(link.created) if link.created else "",
        updated=str(link.updated) if link.updated else "",
        access_count=access_count,
        last_accessed_at=last_accessed,
    )


@router.post("/notebook/{notebook_id}", response_model=ShareLinkResponse)
async def create_share_link(notebook_id: str, data: ShareLinkCreateRequest):
    """为笔记本创建共享链接。"""
    log = get_logger(
        "share_api", Operation.CREATE, f"notebook_id={notebook_id}"
    )
    log.debug("-> create_share_link()")
    try:
        # 校验笔记本存在
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="笔记本不存在")

        link = ShareLink(
            notebook_id=notebook_id,
            token=generate_share_token(),
            permissions=data.permissions,
            expires_at=data.expires_at,
            created_by=data.created_by,
        )
        await link.save()
        log.bind(result=Result.SUCCESS).info(f"<- create_share_link() id={link.id}")
        return _to_response(link)
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建共享链接失败: {e}")
        get_logger(
            "share_api",
            Operation.CREATE,
            f"notebook_id={notebook_id}",
            Result.FAILURE,
        ).error(f"create_share_link() failed: {e}")
        raise HTTPException(status_code=500, detail=f"创建共享链接失败: {str(e)}")


@router.get("/notebook/{notebook_id}/links", response_model=List[ShareLinkResponse])
async def list_share_links(notebook_id: str):
    """列出笔记本的所有共享链接。"""
    log = get_logger(
        "share_api", Operation.READ, f"notebook_id={notebook_id}"
    )
    log.debug("-> list_share_links()")
    try:
        links = await ShareLink.get_by_notebook(notebook_id)
        log.bind(result=Result.SUCCESS).info(
            f"<- list_share_links() count={len(links)}"
        )
        return [_to_response(link) for link in links]
    except Exception as e:
        logger.error(f"列出共享链接失败: {e}")
        get_logger(
            "share_api",
            Operation.READ,
            f"notebook_id={notebook_id}",
            Result.FAILURE,
        ).error(f"list_share_links() failed: {e}")
        raise HTTPException(status_code=500, detail=f"列出共享链接失败: {str(e)}")


@router.get("/{token}", response_model=SharedNotebookResponse)
async def get_shared_notebook(token: str):
    """通过 token 访问共享笔记本（只读视图）。"""
    log = get_logger("share_api", Operation.READ, "token=***")
    log.debug("-> get_shared_notebook()")
    try:
        link = await ShareLink.get_by_token(token)
        if not link:
            raise HTTPException(status_code=404, detail="共享链接不存在")
        if link.is_expired():
            raise HTTPException(status_code=410, detail="共享链接已过期")

        # 记录访问统计
        try:
            await link.record_access()
        except Exception:
            # 统计失败不应阻断共享访问
            pass

        notebook = await Notebook.get(link.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="笔记本不存在")

        # 获取笔记本的源和笔记（精简视图）
        sources = await notebook.get_sources(include_full_text=False)
        notes = await notebook.get_notes(include_content=False)

        log.bind(result=Result.SUCCESS).info("<- get_shared_notebook() ok")
        return SharedNotebookResponse(
            notebook_id=str(notebook.id or ""),
            notebook_name=notebook.name,
            notebook_description=notebook.description,
            permissions=link.permissions,
            sources=[
                {
                    "id": str(s.id or ""),
                    "title": getattr(s, "title", None),
                    "created": str(getattr(s, "created", "")),
                    "updated": str(getattr(s, "updated", "")),
                }
                for s in sources
            ],
            notes=[
                {
                    "id": str(n.id or ""),
                    "title": getattr(n, "title", None),
                    "created": str(getattr(n, "created", "")),
                    "updated": str(getattr(n, "updated", "")),
                }
                for n in notes
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"访问共享笔记本失败: {e}")
        get_logger(
            "share_api", Operation.READ, "token=***", Result.FAILURE
        ).error(f"get_shared_notebook() failed: {e}")
        raise HTTPException(status_code=500, detail=f"访问共享笔记本失败: {str(e)}")


@router.delete("/{link_id}")
async def revoke_share_link(link_id: str):
    """撤销共享链接。"""
    log = get_logger("share_api", Operation.DELETE, f"link_id={link_id}")
    log.debug("-> revoke_share_link()")
    try:
        link = await ShareLink.get(link_id)
        await link.delete()
        log.bind(result=Result.SUCCESS).info("<- revoke_share_link() ok")
        return {"message": "共享链接已撤销"}
    except Exception as e:
        logger.error(f"撤销共享链接失败: {e}")
        get_logger(
            "share_api",
            Operation.DELETE,
            f"link_id={link_id}",
            Result.FAILURE,
        ).error(f"revoke_share_link() failed: {e}")
        raise HTTPException(status_code=500, detail=f"撤销共享链接失败: {str(e)}")
