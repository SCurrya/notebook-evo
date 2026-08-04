"""
Video generation router.

Integrates MoneyPrinterTurbo as an external microservice for end-to-end
short video generation (script → TTS → subtitle → material → video).

All requests are proxied to the MoneyPrinterTurbo service via HTTP.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from api.video_service import (
    VideoGenerationRequest,
    VideoService,
    VideoTaskResponse,
    VideoTaskStatus,
    VideoTemplate,
)

router = APIRouter()


class TemplateCreateRequest(BaseModel):
    """从模板创建视频任务的请求体。"""

    template_name: str = Field(
        ...,
        description="模板标识: marketing/tutorial/story/news/short",
    )
    subject: str = Field(..., description="视频主题/标题")
    custom_overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="覆盖模板预设参数，支持 VideoGenerationRequest 的任意字段",
    )


@router.get("/videos/health")
async def video_service_health() -> Dict[str, Any]:
    """Check if the MoneyPrinterTurbo video service is available."""
    return await VideoService.check_service_health()


@router.post("/videos/launch-mpt")
async def launch_moneyprinterturbo() -> Dict[str, Any]:
    """启动 MoneyPrinterTurbo 后端服务（自动定位项目目录并以子进程方式启动）。

    用于桌面端一键启动 MPT，避免用户手动打开终端。启动是异步非阻塞的，
    客户端可继续轮询 /videos/health 直到服务就绪。
    """
    return await VideoService.launch_moneyprinterturbo()


@router.get("/videos/templates", response_model=List[VideoTemplate])
async def list_video_templates() -> List[VideoTemplate]:
    """列出所有可用的视频模板。

    返回营销、教程、故事、新闻、短视频等预设模板，
    每个模板包含节奏、配音、BGM、字幕等预设参数。
    """
    return VideoService.list_templates()


@router.post("/videos", response_model=VideoTaskResponse)
async def create_video_task(request: VideoGenerationRequest):
    """Submit a new video generation task.

    The task runs asynchronously in the MoneyPrinterTurbo service.
    Returns immediately with a task ID for status polling.
    """
    try:
        return await VideoService.submit_video_task(request)
    except RuntimeError as e:
        logger.error(f"Video task submission failed: {e}")
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        logger.error(f"Invalid video request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/videos/from-template", response_model=VideoTaskResponse)
async def create_video_from_template(request: TemplateCreateRequest):
    """基于预设模板创建视频生成任务。

    根据模板名称加载预设参数，结合主题与可选覆盖项构建请求，
    然后提交到 MoneyPrinterTurbo 服务。
    """
    try:
        generation_request = VideoService.create_request_from_template(
            template_name=request.template_name,
            subject=request.subject,
            custom_overrides=request.custom_overrides,
        )
        return await VideoService.submit_video_task(generation_request)
    except ValueError as e:
        logger.error(f"Invalid template request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        logger.error(f"Template video task submission failed: {e}")
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/videos/{task_id}", response_model=VideoTaskStatus)
async def get_video_task(task_id: str):
    """Get the status of a video generation task."""
    try:
        return await VideoService.get_task_status(task_id)
    except RuntimeError as e:
        logger.error(f"Failed to get video task {task_id}: {e}")
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/videos")
async def list_video_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List video generation tasks (paginated)."""
    try:
        return await VideoService.list_tasks(page=page, page_size=page_size)
    except RuntimeError as e:
        logger.error(f"Failed to list video tasks: {e}")
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.delete("/videos/{task_id}")
async def delete_video_task(task_id: str):
    """Delete a video generation task and its artifacts."""
    try:
        return await VideoService.delete_task(task_id)
    except RuntimeError as e:
        logger.error(f"Failed to delete video task {task_id}: {e}")
        raise HTTPException(status_code=503, detail=str(e)) from e
