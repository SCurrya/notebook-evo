"""
Blog creation router.

Provides endpoints for blog post CRUD, publishing, export, and tag/category
aggregation. Posts are stored in-memory and persisted to ``outputs/blog/``.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query, Response
from loguru import logger

from api.blog_service import (
    BlogListResponse,
    BlogPostCreate,
    BlogPostResponse,
    BlogPostStatus,
    BlogPostUpdate,
    BlogService,
)

router = APIRouter()


def _service() -> BlogService:
    """获取 BlogService 单例。"""
    return BlogService.get_instance()


# === Specific routes (MUST come before /blog/posts/{post_id}) ===

@router.get("/blog/tags", response_model=List[str])
async def list_blog_tags():
    """列出所有文章中出现过的标签。"""
    return await _service().list_tags()


@router.get("/blog/categories", response_model=List[str])
async def list_blog_categories():
    """列出所有文章中出现过的分类。"""
    return await _service().list_categories()


@router.get("/blog/posts", response_model=BlogListResponse)
async def list_blog_posts(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    tag: str = Query(None, description="按标签过滤"),
    category: str = Query(None, description="按分类过滤"),
    status: BlogPostStatus = Query(None, description="按状态过滤"),
    search: str = Query(None, description="在标题和内容中搜索"),
):
    """列出博客文章，支持分页、过滤和搜索。"""
    return await _service().list_posts(
        page=page,
        page_size=page_size,
        tag=tag,
        category=category,
        status=status,
        search=search,
    )


@router.post("/blog/posts", response_model=BlogPostResponse, status_code=201)
async def create_blog_post(request: BlogPostCreate):
    """创建一篇新的博客文章。"""
    try:
        return await _service().create_post(request)
    except ValueError as e:
        logger.warning(f"创建博客文章参数无效: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


# === Parameterized routes ===

@router.get("/blog/posts/{post_id}", response_model=BlogPostResponse)
async def get_blog_post(post_id: str):
    """获取单篇博客文章。"""
    post = await _service().get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail=f"文章不存在: {post_id}")
    return post


@router.put("/blog/posts/{post_id}", response_model=BlogPostResponse)
async def update_blog_post(post_id: str, request: BlogPostUpdate):
    """更新博客文章。仅更新请求中提供的字段。"""
    post = await _service().update_post(post_id, request)
    if post is None:
        raise HTTPException(status_code=404, detail=f"文章不存在: {post_id}")
    return post


@router.delete("/blog/posts/{post_id}")
async def delete_blog_post(post_id: str):
    """删除博客文章。"""
    deleted = await _service().delete_post(post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"文章不存在: {post_id}")
    return {"deleted": True, "id": post_id}


@router.post("/blog/posts/{post_id}/publish", response_model=BlogPostResponse)
async def publish_blog_post(post_id: str):
    """发布博客文章。"""
    post = await _service().publish_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail=f"文章不存在: {post_id}")
    return post


@router.post("/blog/posts/{post_id}/unpublish", response_model=BlogPostResponse)
async def unpublish_blog_post(post_id: str):
    """取消发布博客文章（回到草稿状态）。"""
    post = await _service().unpublish_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail=f"文章不存在: {post_id}")
    return post


@router.get("/blog/posts/{post_id}/export")
async def export_blog_post(
    post_id: str,
    format: str = Query("md", description="导出格式: md 或 html"),
):
    """导出博客文章为 Markdown 或 HTML 文件。"""
    try:
        result = await _service().export_post(post_id, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if result is None:
        raise HTTPException(status_code=404, detail=f"文章不存在: {post_id}")

    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
        },
    )
