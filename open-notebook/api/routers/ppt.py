"""
PPT 生成路由。

提供模板列表、任务提交、状态查询、文件下载和删除等端点。

IMPORTANT: Specific 路由（如 /ppt/templates, /ppt/tasks）MUST 在参数化路由
（如 /ppt/tasks/{task_id}）之前定义，以避免路由遮蔽。
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from api.ppt_service import (
    PPTGenerationRequest,
    PPTService,
    PPTTaskListResponse,
    PPTTaskResponse,
    PPTTaskStatus,
    PPTTemplate,
)

router = APIRouter()


def _get_service() -> PPTService:
    return PPTService.get_instance()


# === Specific 路由（必须在参数化路由之前） ===

@router.get("/ppt/templates", response_model=list[PPTTemplate])
async def list_templates():
    """列出所有可用的 PPT 模板。"""
    return PPTService.list_templates()


@router.post("/ppt/generate", response_model=PPTTaskResponse)
async def generate_ppt(request: PPTGenerationRequest):
    """提交 PPT 生成任务。

    立即返回 task_id，生成在后台异步执行。
    通过 GET /ppt/tasks/{task_id} 轮询状态。
    """
    try:
        return await _get_service().create_task(request)
    except Exception as e:
        logger.error(f"PPT generation submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ppt/tasks", response_model=PPTTaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页列出 PPT 生成任务。"""
    return _get_service().list_tasks(page=page, page_size=page_size)


# === 参数化路由 ===

@router.get("/ppt/tasks/{task_id}", response_model=PPTTaskStatus)
async def get_task(task_id: str):
    """获取 PPT 生成任务状态。"""
    task = _get_service().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"PPT task not found: {task_id}")
    return task


@router.get("/ppt/tasks/{task_id}/download")
async def download_task(task_id: str):
    """下载生成的 PPTX 文件。"""
    task = _get_service().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"PPT task not found: {task_id}")

    if task.state != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Task not completed (state={task.state})",
        )

    file_path = _get_service().get_file_path(task_id)
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=404, detail="Generated file not found"
        )

    # 文件名使用标题（清理非法字符）
    safe_title = "".join(
        c for c in (task.title or task_id) if c.isalnum() or c in (" ", "-", "_")
    ).strip() or task_id
    filename = f"{safe_title}.pptx"

    logger.info(f"Downloading PPT: task={task_id} file={filename}")
    return FileResponse(
        path=str(file_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml."
            "presentation"
        ),
        filename=filename,
    )


@router.delete("/ppt/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除 PPT 生成任务及其文件。"""
    if not _get_service().delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"PPT task not found: {task_id}")
    return {"deleted": True, "task_id": task_id}
