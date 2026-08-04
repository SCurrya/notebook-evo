"""
Image generation router.

Exposes endpoints for listing providers, submitting generation tasks,
polling task status, downloading generated images, and deleting tasks.

Route ordering note: FastAPI matches routes in declaration order, so
static paths (e.g. /images/providers, /images/tasks) are declared before
parameterized paths (e.g. /images/tasks/{task_id}) to avoid ambiguity.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from api.image_service import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageProviderInfo,
    ImageService,
    ImageTaskListResponse,
    ImageTaskStatus,
)

router = APIRouter()


@router.get("/images/providers", response_model=List[ImageProviderInfo])
async def list_image_providers():
    """List available image providers and their configuration status."""
    return ImageService.list_providers()


@router.post("/images/generate", response_model=ImageGenerationResponse)
async def create_image_task(request: ImageGenerationRequest):
    """Submit a new image generation task.

    The task runs asynchronously; this endpoint returns immediately with
    a task_id for status polling.
    """
    try:
        return await ImageService.submit_task(request)
    except ValueError as e:
        logger.warning(f"Invalid image request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to submit image task: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Static path declared before parameterized path to ensure correct matching
@router.get("/images/tasks", response_model=ImageTaskListResponse)
async def list_image_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List image generation tasks (paginated, newest-first)."""
    return await ImageService.list_tasks(page=page, page_size=page_size)


@router.get("/images/tasks/{task_id}", response_model=ImageTaskStatus)
async def get_image_task(task_id: str):
    """Get the status of a single image generation task."""
    task = await ImageService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Image task not found: {task_id}")
    return task


@router.get("/images/tasks/{task_id}/download")
async def download_image(task_id: str, index: int = Query(0, ge=0)):
    """Download a generated image file.

    The `index` query parameter selects which image to download when a
    task produced multiple images.
    """
    path = await ImageService.get_image_path(task_id, index)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Image not found for task {task_id} at index {index}",
        )
    return FileResponse(path, media_type="image/png", filename=f"{task_id}_{index}.png")


@router.delete("/images/tasks/{task_id}")
async def delete_image_task(task_id: str):
    """Delete an image task and its generated files."""
    deleted = await ImageService.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Image task not found: {task_id}")
    return {"deleted": True, "task_id": task_id}
