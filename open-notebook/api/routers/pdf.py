"""
PDF generation router.

Provides REST endpoints for PDF template discovery, asynchronous task
submission, status polling, paginated task listing, file download, and
task deletion. PDF generation runs in a background thread via
asyncio.to_thread and uses reportlab directly (no browser printing).

Route ordering: specific routes (templates, tasks list) are registered
before parameterized routes (tasks/{task_id}) to avoid path conflicts.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from api.pdf_service import (
    PDFGenerationRequest,
    PDFService,
    PDFTaskListResponse,
    PDFTaskResponse,
    PDFTaskStatus,
    PDFTemplate,
)

router = APIRouter()


# === Specific routes (must come before parameterized routes) ===

@router.get("/pdf/templates", response_model=List[PDFTemplate])
async def list_pdf_templates():
    """列出所有可用的 PDF 模板。"""
    return PDFService.list_templates()


@router.post("/pdf/generate", response_model=PDFTaskResponse)
async def create_pdf_task(request: PDFGenerationRequest):
    """提交 PDF 生成任务。

    立即返回任务 ID，生成过程在后台异步执行。
    客户端可通过 GET /pdf/tasks/{task_id} 轮询状态。
    """
    try:
        return await PDFService.submit_task(request)
    except ValueError as e:
        logger.error(f"Invalid PDF request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to submit PDF task: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/pdf/tasks", response_model=PDFTaskListResponse)
async def list_pdf_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页列出 PDF 生成任务（按创建时间倒序）。"""
    return PDFService.list_tasks(page=page, page_size=page_size)


# === Parameterized routes ===

@router.get("/pdf/tasks/{task_id}", response_model=PDFTaskStatus)
async def get_pdf_task(task_id: str):
    """获取单个 PDF 任务的状态。"""
    task = PDFService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"PDF task not found: {task_id}")
    return task


@router.get("/pdf/tasks/{task_id}/download")
async def download_pdf_task(task_id: str):
    """下载已完成的 PDF 文件。

    仅当任务状态为 completed 时可下载。
    """
    task = PDFService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"PDF task not found: {task_id}")
    if task.state != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Task is not completed (current state: {task.state})",
        )

    file_path = PDFService.get_task_file_path(task_id)
    if file_path is None:
        raise HTTPException(
            status_code=404, detail=f"PDF file not found for task: {task_id}"
        )

    # 生成下载文件名
    safe_title = task.title or "document"
    download_name = f"{safe_title}.pdf"
    logger.info(f"Downloading PDF: task={task_id} file={file_path}")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=download_name,
    )


@router.delete("/pdf/tasks/{task_id}")
async def delete_pdf_task(task_id: str):
    """删除 PDF 任务及其生成的文件。"""
    deleted = PDFService.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"PDF task not found: {task_id}")
    return {"deleted": True, "task_id": task_id}
