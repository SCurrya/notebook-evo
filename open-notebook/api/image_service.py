"""
Image generation service.

Supports multiple providers:
  - openai: DALL-E 3 and DALL-E 2 via the openai library
  - stable_diffusion: Stability AI REST API
  - placeholder: local gradient image generation via Pillow (offline)

Configuration:
    OPENAI_API_KEY - OpenAI API key for DALL-E models
    STABILITY_API_KEY - Stability AI API key for Stable Diffusion

Generated images are saved to outputs/images/ and served via the
image router's download endpoint.

Tasks are tracked in-memory (process-local). Restarting the API
process clears the task registry but leaves generated files on disk.
"""

import asyncio
import base64
import hashlib
import io
import os
import textwrap
import uuid
from colorsys import hls_to_rgb
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field


# === Configuration ===
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_OUTPUT_DIR = os.environ.get(
    "IMAGE_OUTPUT_DIR",
    os.path.join(_PROJECT_ROOT, "outputs", "images"),
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
STABILITY_API_KEY = os.environ.get("STABILITY_API_KEY", "")
STABILITY_API_URL = (
    "https://api.stability.ai/v2beta/stable-image/generate/core"
)
STABILITY_TIMEOUT = float(os.environ.get("STABILITY_TIMEOUT", "120"))
OPENAI_IMAGE_TIMEOUT = float(os.environ.get("OPENAI_IMAGE_TIMEOUT", "120"))

# Supported sizes per provider/model
OPENAI_DALLE3_SIZES = {"1024x1024", "1792x1024", "1024x1792"}
OPENAI_DALLE2_SIZES = {"256x256", "512x512", "1024x1024"}
PLACEHOLDER_SIZES = {
    "256x256", "512x512", "1024x1024", "1792x1024", "1024x1792",
}
# Stability AI uses aspect ratios rather than pixel dimensions
STABILITY_ASPECT_RATIOS: Dict[str, str] = {
    "1024x1024": "1:1",
    "1792x1024": "16:9",
    "1024x1792": "9:16",
}

# Thumbnail max dimension (pixels) for base64 previews
THUMBNAIL_MAX_SIZE = 256


# === Pydantic Models ===
class ImageProvider(str, Enum):
    """Supported image generation providers."""

    OPENAI = "openai"
    STABLE_DIFFUSION = "stable_diffusion"
    PLACEHOLDER = "placeholder"


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(
        ..., min_length=1, description="Text prompt describing the image"
    )
    negative_prompt: Optional[str] = Field(
        default=None,
        description="What to exclude from the image (stable_diffusion only)",
    )
    size: str = Field(
        default="1024x1024",
        description="Image size: 256x256, 512x512, 1024x1024, 1792x1024, 1024x1792",
    )
    quality: str = Field(
        default="standard",
        description="Image quality: standard, hd (DALL-E 3 only)",
    )
    style: str = Field(
        default="vivid",
        description="Image style: vivid, natural (DALL-E 3 only)",
    )
    n: int = Field(
        default=1, ge=1, le=4, description="Number of images to generate"
    )
    provider: ImageProvider = Field(
        default=ImageProvider.PLACEHOLDER,
        description="Image generation provider",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model name: dall-e-3, dall-e-2 (openai provider only)",
    )


class GeneratedImage(BaseModel):
    """A single generated image within a task."""

    index: int
    filename: str
    url: str
    thumbnail_base64: str
    width: int
    height: int


class ImageGenerationResponse(BaseModel):
    """Immediate response from a generation request."""

    task_id: str
    status: str = "pending"
    message: str = ""


class ImageTaskStatus(BaseModel):
    """Full status of an image generation task."""

    id: str
    state: str = "pending"
    progress: int = 0
    message: str = ""
    prompt: str = ""
    provider: str = ""
    model: Optional[str] = None
    size: str = ""
    n: int = 1
    images: List[GeneratedImage] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    error: Optional[str] = None


class ImageProviderInfo(BaseModel):
    """Information about an available image provider."""

    id: str
    name: str
    available: bool
    models: List[str] = Field(default_factory=list)
    description: str = ""
    requires_api_key: bool = True


class ImageTaskListResponse(BaseModel):
    """Paginated list of image tasks."""

    items: List[ImageTaskStatus]
    total: int
    page: int
    page_size: int


# === Helpers ===
def _now_iso() -> str:
    """Current UTC timestamp in ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


def _parse_size(size: str) -> Tuple[int, int]:
    """Parse 'WxH' into (width, height). Raises ValueError on bad format."""
    try:
        w_str, h_str = size.lower().split("x")
        w, h = int(w_str), int(h_str)
        if w <= 0 or h <= 0:
            raise ValueError
        return w, h
    except Exception as e:
        raise ValueError(f"Invalid size '{size}'. Expected format: WxH") from e


def _load_font(size: int) -> ImageFont.ImageFont:
    """Load a TrueType font, falling back to PIL's default bitmap font."""
    # 常见字体路径，按平台覆盖
    candidates = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _create_thumbnail(image_bytes: bytes, max_size: int = THUMBNAIL_MAX_SIZE) -> str:
    """Generate a base64-encoded JPEG thumbnail from raw image bytes."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((max_size, max_size))
    # 转为 RGB 以兼容 JPEG 编码
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _generate_placeholder_image(prompt: str, size: str) -> bytes:
    """Generate a placeholder gradient image with the prompt text.

    Uses Pillow only — no network or API key required. Useful for demos
    and offline development.
    """
    width, height = _parse_size(size)

    # 基于提示词哈希生成确定性颜色，保证同一 prompt 产出一致的视觉
    hash_val = int(hashlib.md5(prompt.encode("utf-8")).hexdigest(), 16)
    hue1 = (hash_val % 360) / 360.0
    hue2 = ((hash_val // 360) % 360) / 360.0
    r1, g1, b1 = hls_to_rgb(hue1, 0.35, 0.7)
    r2, g2, b2 = hls_to_rgb(hue2, 0.55, 0.7)
    color1 = (int(r1 * 255), int(g1 * 255), int(b1 * 255))
    color2 = (int(r2 * 255), int(g2 * 255), int(b2 * 255))

    # 先构建 1x256 渐变条再缩放，避免逐像素填充大图带来的性能问题
    gradient = Image.new("RGB", (1, 256))
    for y in range(256):
        ratio = y / 255
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        gradient.putpixel((0, y), (r, g, b))
    img = gradient.resize((width, height), Image.BILINEAR)

    # 在半透明遮罩上绘制提示词文本
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(max(16, min(width, height) // 18))

    wrapped = textwrap.wrap(prompt, width=32)
    text = "\n".join(wrapped[:12])
    if len(wrapped) > 12:
        text += "\n..."

    bbox = draw.multiline_textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2

    padding = 24
    draw.rectangle(
        [
            x - padding,
            y - padding,
            x + text_w + padding,
            y + text_h + padding,
        ],
        fill=(0, 0, 0, 150),
    )
    draw.multiline_text(
        (x, y), text, fill=(255, 255, 255, 255), font=font, align="center"
    )

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# === Service ===
class ImageService:
    """Service for generating images via multiple providers.

    Tasks are tracked in an in-memory dict keyed by task_id. Generation
    runs as a background asyncio task that updates the task status as
    it progresses.
    """

    # 进程内任务存储（重启后清空，但磁盘文件保留）
    _tasks: Dict[str, ImageTaskStatus] = {}
    _tasks_lock: asyncio.Lock = asyncio.Lock()

    # ---- Task registry helpers ----
    @classmethod
    async def _update_task(cls, task_id: str, **updates: Any) -> None:
        """Update task fields under the lock."""
        async with cls._tasks_lock:
            task = cls._tasks.get(task_id)
            if task is None:
                return
            for key, value in updates.items():
                setattr(task, key, value)
            task.updated_at = _now_iso()

    @classmethod
    async def get_task(cls, task_id: str) -> Optional[ImageTaskStatus]:
        """Retrieve a task by ID (returns a copy)."""
        async with cls._tasks_lock:
            task = cls._tasks.get(task_id)
            return task.model_copy(deep=True) if task else None

    @classmethod
    async def list_tasks(
        cls, page: int = 1, page_size: int = 20
    ) -> ImageTaskListResponse:
        """List tasks newest-first with pagination."""
        async with cls._tasks_lock:
            all_tasks = sorted(
                cls._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )
            total = len(all_tasks)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = all_tasks[start:end]
        return ImageTaskListResponse(
            items=[t.model_copy(deep=True) for t in page_items],
            total=total,
            page=page,
            page_size=page_size,
        )

    @classmethod
    async def delete_task(cls, task_id: str) -> bool:
        """Remove a task and delete its image files from disk."""
        async with cls._tasks_lock:
            task = cls._tasks.pop(task_id, None)
        if task is None:
            return False
        # 清理磁盘上的图片文件
        for img in task.images:
            try:
                file_path = os.path.join(IMAGES_OUTPUT_DIR, img.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError as e:
                logger.warning(f"Failed to delete {img.filename}: {e}")
        return True

    # ---- Provider listing ----
    @staticmethod
    def list_providers() -> List[ImageProviderInfo]:
        """List all providers with their current availability."""
        return [
            ImageProviderInfo(
                id=ImageProvider.OPENAI.value,
                name="OpenAI DALL-E",
                available=bool(OPENAI_API_KEY),
                models=["dall-e-3", "dall-e-2"],
                description="DALL-E 3 (HD, vivid/natural) and DALL-E 2.",
                requires_api_key=True,
            ),
            ImageProviderInfo(
                id=ImageProvider.STABLE_DIFFUSION.value,
                name="Stability AI (Stable Diffusion)",
                available=bool(STABILITY_API_KEY),
                models=["stable-image-core"],
                description="Stable Image Core via Stability AI API.",
                requires_api_key=True,
            ),
            ImageProviderInfo(
                id=ImageProvider.PLACEHOLDER.value,
                name="Placeholder (offline)",
                available=True,
                models=["gradient"],
                description="Local gradient images via Pillow. No API key needed.",
                requires_api_key=False,
            ),
        ]

    # ---- Validation ----
    @staticmethod
    def _validate_request(request: ImageGenerationRequest) -> None:
        """Validate provider-specific constraints. Raises ValueError on failure."""
        provider = request.provider
        size = request.size

        if provider == ImageProvider.OPENAI:
            model = request.model or "dall-e-3"
            if model not in ("dall-e-3", "dall-e-2"):
                raise ValueError(
                    f"Unsupported OpenAI model '{model}'. Use 'dall-e-3' or 'dall-e-2'."
                )
            allowed = (
                OPENAI_DALLE3_SIZES if model == "dall-e-3" else OPENAI_DALLE2_SIZES
            )
            if size not in allowed:
                raise ValueError(
                    f"Size '{size}' not supported by {model}. "
                    f"Allowed: {sorted(allowed)}"
                )
            if model == "dall-e-3" and request.n > 1:
                # DALL-E 3 only supports n=1 per call; we generate sequentially
                logger.info(
                    "DALL-E 3 does not support n>1 in a single call; "
                    f"will generate {request.n} images sequentially."
                )
            if not OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY is not configured. Set it in the environment "
                    "or use the 'placeholder' provider for offline demos."
                )
        elif provider == ImageProvider.STABLE_DIFFUSION:
            if size not in STABILITY_ASPECT_RATIOS:
                raise ValueError(
                    f"Size '{size}' not supported by stable_diffusion. "
                    f"Allowed: {sorted(STABILITY_ASPECT_RATIOS.keys())}"
                )
            if not STABILITY_API_KEY:
                raise ValueError(
                    "STABILITY_API_KEY is not configured. Set it in the environment "
                    "or use the 'placeholder' provider for offline demos."
                )
        elif provider == ImageProvider.PLACEHOLDER:
            if size not in PLACEHOLDER_SIZES:
                raise ValueError(
                    f"Size '{size}' not supported by placeholder. "
                    f"Allowed: {sorted(PLACEHOLDER_SIZES)}"
                )

    # ---- Generation entry point ----
    @classmethod
    async def submit_task(
        cls, request: ImageGenerationRequest
    ) -> ImageGenerationResponse:
        """Create a task and start background generation.

        Returns immediately with a task_id; the actual generation runs
        asynchronously and updates the task status.
        """
        cls._validate_request(request)

        task_id = uuid.uuid4().hex
        now = _now_iso()
        task = ImageTaskStatus(
            id=task_id,
            state="pending",
            progress=0,
            message="Task queued",
            prompt=request.prompt,
            provider=request.provider.value,
            model=request.model,
            size=request.size,
            n=request.n,
            created_at=now,
            updated_at=now,
        )
        async with cls._tasks_lock:
            cls._tasks[task_id] = task

        # 启动后台生成（不等待完成）
        asyncio.create_task(cls._run_generation(task_id, request))

        logger.info(
            f"Image task {task_id} submitted: provider={request.provider.value} "
            f"size={request.size} n={request.n}"
        )
        return ImageGenerationResponse(
            task_id=task_id,
            status="pending",
            message="Image generation task submitted",
        )

    @classmethod
    async def _run_generation(
        cls, task_id: str, request: ImageGenerationRequest
    ) -> None:
        """Background generation coroutine. Updates task status throughout."""
        try:
            await cls._update_task(
                task_id, state="processing", progress=10, message="Generating..."
            )

            images: List[GeneratedImage] = []
            n = request.n
            for i in range(n):
                img = await cls._generate_single(task_id, request, i, n)
                images.append(img)
                progress = 10 + int(80 * (i + 1) / n)
                await cls._update_task(
                    task_id,
                    progress=progress,
                    message=f"Generated {i + 1}/{n} images",
                )

            await cls._update_task(
                task_id,
                state="completed",
                progress=100,
                message=f"Generated {len(images)} image(s)",
                images=images,
            )
            logger.info(f"Image task {task_id} completed: {len(images)} image(s)")
        except Exception as e:
            logger.error(f"Image task {task_id} failed: {e}")
            await cls._update_task(
                task_id,
                state="failed",
                progress=0,
                error=str(e),
                message="Generation failed",
            )

    @classmethod
    async def _generate_single(
        cls,
        task_id: str,
        request: ImageGenerationRequest,
        index: int,
        total: int,
    ) -> GeneratedImage:
        """Generate a single image via the selected provider."""
        provider = request.provider

        if provider == ImageProvider.OPENAI:
            image_bytes, w, h = await cls._generate_openai(request, index)
        elif provider == ImageProvider.STABLE_DIFFUSION:
            image_bytes, w, h = await cls._generate_stability(request)
        elif provider == ImageProvider.PLACEHOLDER:
            image_bytes, w, h = await cls._generate_placeholder(request)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # 保存到磁盘
        os.makedirs(IMAGES_OUTPUT_DIR, exist_ok=True)
        filename = f"{task_id}_{index}.png"
        file_path = os.path.join(IMAGES_OUTPUT_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        thumbnail = _create_thumbnail(image_bytes)
        return GeneratedImage(
            index=index,
            filename=filename,
            url=f"/api/images/tasks/{task_id}/download?index={index}",
            thumbnail_base64=thumbnail,
            width=w,
            height=h,
        )

    # ---- Provider: OpenAI DALL-E ----
    @staticmethod
    async def _generate_openai(
        request: ImageGenerationRequest, index: int
    ) -> Tuple[bytes, int, int]:
        """Generate an image via OpenAI DALL-E."""
        # 延迟导入以避免在未安装时影响模块加载
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        model = request.model or "dall-e-3"

        kwargs: Dict[str, Any] = {
            "model": model,
            "prompt": request.prompt,
            "size": request.size,
            "n": 1,  # DALL-E 3 限制 n=1，多图通过循环实现
        }
        if model == "dall-e-3":
            kwargs["quality"] = request.quality
            kwargs["style"] = request.style

        logger.info(
            f"OpenAI image request: model={model} size={request.size} "
            f"prompt='{request.prompt[:60]}...'"
        )
        try:
            response = await client.images.generate(**kwargs)
        except Exception as e:
            raise RuntimeError(f"OpenAI image generation failed: {e}") from e

        if not response.data:
            raise RuntimeError("OpenAI returned no image data")

        item = response.data[0]
        # 优先使用 b64_json，避免额外的 HTTP 下载
        if getattr(item, "b64_json", None):
            image_bytes = base64.b64decode(item.b64_json)
        elif getattr(item, "url", None):
            async with httpx.AsyncClient(timeout=OPENAI_IMAGE_TIMEOUT) as http:
                img_resp = await http.get(item.url)
                img_resp.raise_for_status()
                image_bytes = img_resp.content
        else:
            raise RuntimeError("OpenAI returned neither b64_json nor url")

        w, h = _parse_size(request.size)
        return image_bytes, w, h

    # ---- Provider: Stability AI ----
    @staticmethod
    async def _generate_stability(
        request: ImageGenerationRequest,
    ) -> Tuple[bytes, int, int]:
        """Generate an image via Stability AI Stable Image Core."""
        aspect_ratio = STABILITY_ASPECT_RATIOS[request.size]

        # Stability API 要求 multipart/form-data；用 (None, value) 表示表单字段
        form_fields: List[Tuple[str, str]] = [
            ("prompt", request.prompt),
            ("aspect_ratio", aspect_ratio),
            ("output_format", "png"),
        ]
        if request.negative_prompt:
            form_fields.append(("negative_prompt", request.negative_prompt))

        files = [(key, (None, value)) for key, value in form_fields]

        logger.info(
            f"Stability AI request: aspect={aspect_ratio} "
            f"prompt='{request.prompt[:60]}...'"
        )
        try:
            async with httpx.AsyncClient(timeout=STABILITY_TIMEOUT) as client:
                response = await client.post(
                    STABILITY_API_URL,
                    headers={
                        "Authorization": f"Bearer {STABILITY_API_KEY}",
                        "Accept": "image/*",
                    },
                    files=files,
                )
        except httpx.RequestError as e:
            raise RuntimeError(f"Stability AI request failed: {e}") from e

        if response.status_code != 200:
            detail = response.text[:500]
            raise RuntimeError(
                f"Stability AI returned HTTP {response.status_code}: {detail}"
            )

        image_bytes = response.content
        w, h = _parse_size(request.size)
        return image_bytes, w, h

    # ---- Provider: Placeholder (Pillow) ----
    @staticmethod
    async def _generate_placeholder(
        request: ImageGenerationRequest,
    ) -> Tuple[bytes, int, int]:
        """Generate a placeholder image locally via Pillow."""
        # Pillow 是同步库，放到默认执行器中避免阻塞事件循环
        loop = asyncio.get_running_loop()
        image_bytes = await loop.run_in_executor(
            None, _generate_placeholder_image, request.prompt, request.size
        )
        w, h = _parse_size(request.size)
        return image_bytes, w, h

    # ---- File serving ----
    @classmethod
    async def get_image_path(cls, task_id: str, index: int) -> Optional[str]:
        """Return the on-disk path of a generated image, or None if missing."""
        task = await cls.get_task(task_id)
        if task is None:
            return None
        for img in task.images:
            if img.index == index:
                path = os.path.join(IMAGES_OUTPUT_DIR, img.filename)
                return path if os.path.exists(path) else None
        return None
