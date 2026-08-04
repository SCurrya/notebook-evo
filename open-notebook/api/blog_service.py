"""
Blog creation service.

Provides blog post CRUD with in-memory storage and file persistence to
``outputs/blog/``. Markdown content is rendered to HTML using the ``markdown``
library.

Design:
- All post state is held in-memory (process-local) for fast access.
- Each post is also persisted as a JSON file under ``outputs/blog/`` so that
  content survives process restarts.
- Markdown -> HTML conversion runs in a worker thread via ``asyncio.to_thread``
  to avoid blocking the event loop on large documents.

Configuration:
    BLOG_OUTPUT_DIR - Directory for persisted post files
                      (default: <project_root>/outputs/blog)
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown
from loguru import logger
from pydantic import BaseModel, Field


# === Configuration ===
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
BLOG_OUTPUT_DIR = Path(_PROJECT_ROOT / "outputs" / "blog")


# === Enums ===

class BlogPostStatus(str, Enum):
    """Blog post lifecycle status."""
    DRAFT = "draft"
    PUBLISHED = "published"


# === Models ===

class BlogPostCreate(BaseModel):
    """Request model for creating a blog post."""
    title: str = Field(..., min_length=1, description="Post title")
    content: str = Field(default="", description="Post content in Markdown")
    tags: List[str] = Field(default_factory=list, description="Post tags")
    category: Optional[str] = Field(default=None, description="Post category")
    author: Optional[str] = Field(default=None, description="Author name")


class BlogPostUpdate(BaseModel):
    """Request model for updating a blog post.

    All fields are optional; only provided fields are applied.
    """
    title: Optional[str] = Field(default=None, min_length=1)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    author: Optional[str] = None
    status: Optional[BlogPostStatus] = None


class BlogPost(BaseModel):
    """Internal blog post model (full state)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str = ""
    html: str = ""
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    status: BlogPostStatus = BlogPostStatus.DRAFT
    author: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class BlogPostResponse(BaseModel):
    """Response model for a single blog post."""
    id: str
    title: str
    content: str
    html: str
    tags: List[str]
    category: Optional[str]
    status: BlogPostStatus
    author: Optional[str]
    created_at: str
    updated_at: str


class BlogListResponse(BaseModel):
    """Paginated blog post list response."""
    items: List[BlogPostResponse]
    total: int
    page: int
    page_size: int


# === Helpers ===

def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug.

    用于生成导出文件名，移除非法字符并将空白替换为连字符。
    """
    # 移除文件系统非法字符
    slug = re.sub(r'[\\/:*?"<>|]', "", text)
    # 空白转连字符
    slug = re.sub(r"\s+", "-", slug.strip())
    # 折叠连续连字符
    slug = re.sub(r"-+", "-", slug)
    return slug or "untitled"


def _render_markdown(content: str) -> str:
    """Render Markdown content to HTML.

    启用常用扩展：代码高亮、表格、自动链接、目录。
    """
    md = markdown.Markdown(
        extensions=["extra", "codehilite", "tables", "toc", "sane_lists"],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight"},
        },
    )
    return md.convert(content)


def _build_html_document(title: str, html_body: str) -> str:
    """Wrap rendered HTML body in a styled full HTML document.

    用于导出为独立的 .html 文件，包含基础排版样式。
    """
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      "Helvetica Neue", Arial, sans-serif;
    line-height: 1.7;
    max-width: 760px;
    margin: 2rem auto;
    padding: 0 1rem;
    color: #1f2937;
    background: #ffffff;
  }}
  h1, h2, h3, h4, h5, h6 {{
    line-height: 1.25;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
  }}
  code {{
    background: #f3f4f6;
    padding: 0.15em 0.35em;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  pre {{
    background: #f9fafb;
    padding: 1em;
    border-radius: 6px;
    overflow-x: auto;
  }}
  pre code {{
    background: transparent;
    padding: 0;
  }}
  blockquote {{
    border-left: 4px solid #e5e7eb;
    margin: 0;
    padding-left: 1em;
    color: #6b7280;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
  }}
  th, td {{
    border: 1px solid #e5e7eb;
    padding: 0.5em 0.75em;
    text-align: left;
  }}
  img {{
    max-width: 100%;
  }}
</style>
</head>
<body>
<article>
{html_body}
</article>
</body>
</html>"""


# === Service ===

class BlogService:
    """Blog post service with in-memory storage and file persistence.

    Singleton: use ``BlogService.get_instance()`` to access. State is held
    in-memory for fast reads and mirrored to ``outputs/blog/`` as JSON files
    so content survives restarts.
    """

    _instance: Optional["BlogService"] = None

    def __init__(self) -> None:
        self._posts: Dict[str, BlogPost] = {}
        self._lock = asyncio.Lock()
        self._output_dir = BLOG_OUTPUT_DIR
        self._ensure_output_dir()
        # 启动时从磁盘加载已有文章
        self._load_from_disk()

    @classmethod
    def get_instance(cls) -> "BlogService":
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_output_dir(self) -> None:
        """确保输出目录存在。"""
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"无法创建博客输出目录 {self._output_dir}: {e}")

    def _post_file_path(self, post_id: str) -> Path:
        """返回单篇文章的持久化文件路径。"""
        return self._output_dir / f"{post_id}.json"

    def _load_from_disk(self) -> None:
        """从输出目录加载所有已持久化的文章。

        在构造时调用一次，用于进程重启后恢复状态。
        """
        if not self._output_dir.exists():
            return
        loaded = 0
        for json_file in self._output_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                post = BlogPost(**data)
                self._posts[post.id] = post
                loaded += 1
            except Exception as e:
                logger.warning(f"加载博客文章失败 {json_file}: {e}")
        if loaded:
            logger.info(f"从磁盘加载了 {loaded} 篇博客文章")

    def _persist_post(self, post: BlogPost) -> None:
        """将单篇文章持久化为 JSON 文件。"""
        file_path = self._post_file_path(post.id)
        try:
            file_path.write_text(
                post.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"持久化博客文章失败 {post.id}: {e}")

    def _delete_persisted_post(self, post_id: str) -> None:
        """删除持久化的文章文件。"""
        file_path = self._post_file_path(post_id)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as e:
            logger.warning(f"删除持久化文章失败 {post_id}: {e}")

    def _to_response(self, post: BlogPost) -> BlogPostResponse:
        """将内部模型转换为响应模型。"""
        return BlogPostResponse(
            id=post.id,
            title=post.title,
            content=post.content,
            html=post.html,
            tags=list(post.tags),
            category=post.category,
            status=post.status,
            author=post.author,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )

    # --- CRUD ---

    async def create_post(self, request: BlogPostCreate) -> BlogPostResponse:
        """创建一篇新的博客文章。

        Markdown 内容会被渲染为 HTML 并一并存储。
        """
        async with self._lock:
            # 在线程中渲染 Markdown，避免阻塞事件循环
            html = await asyncio.to_thread(_render_markdown, request.content)
            now = datetime.now(timezone.utc).isoformat()
            post = BlogPost(
                title=request.title,
                content=request.content,
                html=html,
                tags=list(request.tags),
                category=request.category,
                author=request.author,
                status=BlogPostStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            self._posts[post.id] = post
            self._persist_post(post)
            logger.info(f"博客文章已创建: id={post.id} title={post.title!r}")
            return self._to_response(post)

    async def get_post(self, post_id: str) -> Optional[BlogPostResponse]:
        """获取单篇文章。"""
        async with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                return None
            return self._to_response(post)

    async def update_post(
        self, post_id: str, request: BlogPostUpdate
    ) -> Optional[BlogPostResponse]:
        """更新文章。仅更新请求中提供的字段。

        若 ``content`` 发生变化，会重新渲染 HTML。
        """
        async with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                return None

            changed = False
            if request.title is not None and request.title != post.title:
                post.title = request.title
                changed = True
            if request.tags is not None and request.tags != post.tags:
                post.tags = list(request.tags)
                changed = True
            if request.category is not None and request.category != post.category:
                post.category = request.category
                changed = True
            if request.author is not None and request.author != post.author:
                post.author = request.author
                changed = True
            if request.status is not None and request.status != post.status:
                post.status = request.status
                changed = True
            if request.content is not None and request.content != post.content:
                post.content = request.content
                # 内容变化时重新渲染 HTML
                post.html = await asyncio.to_thread(_render_markdown, request.content)
                changed = True

            if changed:
                post.updated_at = datetime.now(timezone.utc).isoformat()
                self._persist_post(post)
                logger.info(f"博客文章已更新: id={post_id}")

            return self._to_response(post)

    async def delete_post(self, post_id: str) -> bool:
        """删除文章。"""
        async with self._lock:
            post = self._posts.pop(post_id, None)
            if post is None:
                return False
            self._delete_persisted_post(post_id)
            logger.info(f"博客文章已删除: id={post_id}")
            return True

    async def list_posts(
        self,
        page: int = 1,
        page_size: int = 20,
        tag: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[BlogPostStatus] = None,
        search: Optional[str] = None,
    ) -> BlogListResponse:
        """列出文章，支持分页、过滤和搜索。

        - ``tag``: 仅返回包含该标签的文章
        - ``category``: 仅返回该分类的文章
        - ``status``: 仅返回该状态的文章
        - ``search``: 在标题和内容中搜索（大小写不敏感）
        """
        async with self._lock:
            posts = list(self._posts.values())

            # 按标签过滤
            if tag:
                posts = [p for p in posts if tag in p.tags]
            # 按分类过滤
            if category:
                posts = [p for p in posts if p.category == category]
            # 按状态过滤
            if status:
                posts = [p for p in posts if p.status == status]
            # 搜索标题和内容
            if search:
                needle = search.lower()
                posts = [
                    p
                    for p in posts
                    if needle in p.title.lower()
                    or needle in p.content.lower()
                ]

            # 按更新时间倒序排列
            posts.sort(key=lambda p: p.updated_at, reverse=True)

            total = len(posts)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = posts[start:end]

            return BlogListResponse(
                items=[self._to_response(p) for p in page_items],
                total=total,
                page=page,
                page_size=page_size,
            )

    async def set_status(
        self, post_id: str, status: BlogPostStatus
    ) -> Optional[BlogPostResponse]:
        """设置文章状态（发布/取消发布）。"""
        async with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                return None
            if post.status == status:
                return self._to_response(post)
            post.status = status
            post.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_post(post)
            logger.info(f"博客文章状态变更: id={post_id} status={status}")
            return self._to_response(post)

    async def publish_post(self, post_id: str) -> Optional[BlogPostResponse]:
        """发布文章。"""
        return await self.set_status(post_id, BlogPostStatus.PUBLISHED)

    async def unpublish_post(self, post_id: str) -> Optional[BlogPostResponse]:
        """取消发布文章（回到草稿状态）。"""
        return await self.set_status(post_id, BlogPostStatus.DRAFT)

    # --- Aggregations ---

    async def list_tags(self) -> List[str]:
        """列出所有文章中出现过的标签（去重、排序）。"""
        async with self._lock:
            tags: set[str] = set()
            for post in self._posts.values():
                tags.update(post.tags)
            return sorted(tags)

    async def list_categories(self) -> List[str]:
        """列出所有文章中出现过的分类（去重、排序）。"""
        async with self._lock:
            categories: set[str] = set()
            for post in self._posts.values():
                if post.category:
                    categories.add(post.category)
            return sorted(categories)

    # --- Export ---

    async def export_post(
        self, post_id: str, fmt: str
    ) -> Optional[Dict[str, Any]]:
        """导出文章为 ``md`` 或 ``html`` 格式。

        返回字典包含 ``filename``、``content``、``media_type``。
        """
        async with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                return None

        slug = _slugify(post.title)
        fmt_lower = fmt.lower()

        if fmt_lower == "md":
            # Markdown 导出：在内容前附加标题元数据
            header_lines = [f"# {post.title}", ""]
            if post.tags:
                header_lines.append(
                    "Tags: " + ", ".join(post.tags)
                )
            if post.category:
                header_lines.append(f"Category: {post.category}")
            if post.author:
                header_lines.append(f"Author: {post.author}")
            header_lines.append(
                f"Created: {post.created_at}  Updated: {post.updated_at}"
            )
            header_lines.extend(["", "---", ""])
            content = "\n".join(header_lines) + post.content
            return {
                "filename": f"{slug}.md",
                "content": content,
                "media_type": "text/markdown; charset=utf-8",
            }

        if fmt_lower == "html":
            # HTML 导出：渲染完整的独立 HTML 文档
            html_body = post.html or await asyncio.to_thread(
                _render_markdown, post.content
            )
            full_html = _build_html_document(post.title, html_body)
            return {
                "filename": f"{slug}.html",
                "content": full_html,
                "media_type": "text/html; charset=utf-8",
            }

        raise ValueError(f"不支持的导出格式: {fmt}（仅支持 md 或 html）")
