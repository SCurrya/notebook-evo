"""
Video generation service that integrates with MoneyPrinterTurbo.

This service acts as a proxy/adapter to the MoneyPrinterTurbo microservice,
which provides end-to-end short video generation:
  script generation → TTS → subtitle → material download → video synthesis

Architecture: MoneyPrinterTurbo runs as an independent service (default
http://localhost:8080) and this service forwards requests via HTTP.

Configuration:
    MONEYPRINTER_URL - Base URL of the MoneyPrinterTurbo service
                       (default: http://localhost:8080)
    MONEYPRINTER_API_PREFIX - API prefix (default: /api/v1)
    MONEYPRINTER_TIMEOUT - Request timeout in seconds (default: 600)
    MPT_PROJECT_DIR - Path to MoneyPrinterTurbo project (default: e:/notebook/MoneyPrinterTurbo)
"""

import contextlib
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel, Field


# === Configuration ===
MPT_BASE_URL = os.environ.get("MONEYPRINTER_URL", "http://localhost:8080")
MPT_API_PREFIX = os.environ.get("MONEYPRINTER_API_PREFIX", "/api/v1")
MPT_TIMEOUT = float(os.environ.get("MONEYPRINTER_TIMEOUT", "600"))


# === Video Templates ===
# 视频模板预设：每个模板针对特定场景预设了节奏、配音、BGM、字幕等参数
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "marketing": {
        "name": "营销宣传",
        "description": "适合产品宣传，节奏快，BGM 欢快",
        "paragraph_number": 4,
        "voice_name": "zh-CN-XiaoxiaoNeural-Female",
        "bgm_type": "random",
        "video_aspect": "16:9",
        "subtitle_font_size": 60,
        "video_concat_mode": "sequential",
        "max_clip_duration": 3,
    },
    "tutorial": {
        "name": "教学教程",
        "description": "适合教学，节奏慢，字幕大",
        "paragraph_number": 6,
        "voice_name": "zh-CN-YunxiNeural-Male",
        "bgm_type": "none",
        "video_aspect": "16:9",
        "subtitle_font_size": 72,
        "video_concat_mode": "sequential",
        "max_clip_duration": 8,
    },
    "story": {
        "name": "故事叙事",
        "description": "适合叙事，有起承转合",
        "paragraph_number": 8,
        "voice_name": "zh-CN-YunyangNeural-Male",
        "bgm_type": "random",
        "video_aspect": "16:9",
        "subtitle_font_size": 56,
        "video_concat_mode": "sequential_desc",
        "max_clip_duration": 5,
    },
    "news": {
        "name": "新闻资讯",
        "description": "适合资讯，正式风格",
        "paragraph_number": 5,
        "voice_name": "zh-CN-YunxiNeural-Male",
        "bgm_type": "none",
        "video_aspect": "16:9",
        "subtitle_font_size": 64,
        "video_concat_mode": "sequential",
        "max_clip_duration": 4,
    },
    "short": {
        "name": "短视频",
        "description": "15-30秒，适合 TikTok/Shorts",
        "paragraph_number": 2,
        "voice_name": "zh-CN-XiaoxiaoNeural-Female",
        "bgm_type": "random",
        "video_aspect": "9:16",
        "subtitle_font_size": 80,
        "video_concat_mode": "random",
        "max_clip_duration": 2,
    },
}


# === Request/Response Models ===
class VideoAspect(str):
    """Video aspect ratio."""
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


class VideoVoiceConfig(BaseModel):
    """TTS voice configuration."""
    voice_name: str = Field(
        default="zh-CN-XiaoxiaoNeural-Female",
        description="Azure TTS voice name (e.g., zh-CN-XiaoxiaoNeural-Female)",
    )
    voice_rate: float = Field(default=1.0, description="Speech rate (0.5-2.0)")
    voice_volume: float = Field(default=1.0, description="Volume (0.0-1.0)")


class VideoSubtitleConfig(BaseModel):
    """Subtitle configuration."""
    enabled: bool = Field(default=True, description="Generate subtitles")
    font_name: str = Field(default="STHeitiMedium.ttc", description="Font file name")
    font_size: int = Field(default=60, ge=10, le=200)
    text_color: str = Field(default="#FFFFFF", description="Text color (hex)")
    stroke_color: str = Field(default="#000000", description="Stroke color (hex)")
    stroke_width: float = Field(default=1.5, ge=0, le=10)
    position: str = Field(
        default="bottom",
        description="Subtitle position: top/center/bottom/custom",
    )
    custom_position: float = Field(default=70.0, ge=0, le=100)


class VideoGenerationRequest(BaseModel):
    """Request model for video generation.

    Maps to MoneyPrinterTurbo's VideoConcatMode/VideoParams.
    """
    # Content
    video_subject: str = Field(
        ..., description="Topic/subject of the video (used for script generation)",
    )
    video_script: Optional[str] = Field(
        default=None,
        description="Pre-written script. If provided, skips LLM script generation.",
    )
    # Language
    language: str = Field(default="zh-CN", description="Script language code")
    # Format
    video_aspect: str = Field(
        default=VideoAspect.LANDSCAPE,
        description="Aspect ratio: 16:9 (landscape), 9:16 (portrait), 1:1 (square)",
    )
    # Script
    paragraph_number: int = Field(default=3, ge=1, le=20, description="Script paragraphs")
    custom_system_prompt: Optional[str] = Field(
        default=None, description="Custom LLM system prompt for script generation"
    )
    # Voice
    voice: VideoVoiceConfig = Field(default_factory=VideoVoiceConfig)
    # Subtitle
    subtitle: VideoSubtitleConfig = Field(default_factory=VideoSubtitleConfig)
    # Materials
    video_source: str = Field(
        default="pexels",
        description="Material source: pexels/pixabay/local",
    )
    max_clip_duration: int = Field(default=5, ge=1, le=60, description="Max clip duration (s)")
    video_concat_mode: str = Field(
        default="sequential",
        description="Concat mode: sequential/random/sequential_desc",
    )
    # BGM
    bgm_type: str = Field(
        default="random",
        description="BGM selection: random/none/<filename>",
    )
    # Advanced
    max_concurrent_tasks: Optional[int] = Field(
        default=None, ge=1, le=10, description="Max concurrent tasks"
    )


class VideoTaskResponse(BaseModel):
    """Response from video generation request."""
    task_id: str
    status: str = "pending"
    message: str = ""


class VideoTaskStatus(BaseModel):
    """Video task status."""
    id: str
    state: str
    progress: int = 0
    message: str = ""
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    script: Optional[str] = None
    terms: Optional[List[str]] = None
    audio_url: Optional[str] = None
    subtitle_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


class VideoTemplate(BaseModel):
    """视频模板预设配置。

    每个模板针对特定场景预设了节奏、配音、BGM、字幕等参数，
    用户可基于模板快速创建视频任务并按需覆盖部分参数。
    """
    key: str = Field(..., description="模板唯一标识 (marketing/tutorial/story/news/short)")
    name: str = Field(..., description="模板展示名称")
    description: str = Field(..., description="模板适用场景描述")
    paragraph_number: int = Field(..., ge=1, le=20, description="脚本段落数")
    voice_name: str = Field(..., description="Azure TTS 语音名称")
    bgm_type: str = Field(..., description="BGM 选择: random/none/<filename>")
    video_aspect: str = Field(..., description="视频宽高比: 16:9/9:16/1:1")
    subtitle_font_size: int = Field(..., ge=10, le=200, description="字幕字体大小")
    video_concat_mode: str = Field(
        ..., description="拼接模式: sequential/random/sequential_desc"
    )
    max_clip_duration: int = Field(..., ge=1, le=60, description="单段素材最大时长 (秒)")


class VideoService:
    """Service that proxies video generation requests to MoneyPrinterTurbo."""

    @staticmethod
    def _endpoint(path: str) -> str:
        """Build full URL for MoneyPrinterTurbo endpoint."""
        return f"{MPT_BASE_URL}{MPT_API_PREFIX}{path}"

    @staticmethod
    def list_templates() -> List[VideoTemplate]:
        """返回所有可用的视频模板列表。

        模板按 TEMPLATES 字典定义顺序返回，供前端展示和选择。
        """
        templates: List[VideoTemplate] = []
        for key, config in TEMPLATES.items():
            templates.append(
                VideoTemplate(
                    key=key,
                    name=config["name"],
                    description=config["description"],
                    paragraph_number=config["paragraph_number"],
                    voice_name=config["voice_name"],
                    bgm_type=config["bgm_type"],
                    video_aspect=config["video_aspect"],
                    subtitle_font_size=config["subtitle_font_size"],
                    video_concat_mode=config["video_concat_mode"],
                    max_clip_duration=config["max_clip_duration"],
                )
            )
        logger.debug(f"Listed {len(templates)} video templates")
        return templates

    @staticmethod
    def get_template(template_name: str) -> Optional[VideoTemplate]:
        """根据模板名称获取单个视频模板。

        Args:
            template_name: 模板标识 (marketing/tutorial/story/news/short)

        Returns:
            匹配的 VideoTemplate，未找到时返回 None
        """
        config = TEMPLATES.get(template_name)
        if config is None:
            logger.warning(f"Video template not found: {template_name}")
            return None
        return VideoTemplate(
            key=template_name,
            name=config["name"],
            description=config["description"],
            paragraph_number=config["paragraph_number"],
            voice_name=config["voice_name"],
            bgm_type=config["bgm_type"],
            video_aspect=config["video_aspect"],
            subtitle_font_size=config["subtitle_font_size"],
            video_concat_mode=config["video_concat_mode"],
            max_clip_duration=config["max_clip_duration"],
        )

    @staticmethod
    def create_request_from_template(
        template_name: str,
        subject: str,
        custom_overrides: Optional[Dict[str, Any]] = None,
    ) -> VideoGenerationRequest:
        """基于模板创建视频生成请求。

        将模板预设参数映射为 VideoGenerationRequest，并允许通过
        custom_overrides 覆盖任意字段（如 video_script、language 等）。

        Args:
            template_name: 模板标识 (marketing/tutorial/story/news/short)
            subject: 视频主题/标题
            custom_overrides: 覆盖参数字典，支持 VideoGenerationRequest 的任意字段

        Returns:
            填充了模板预设值的 VideoGenerationRequest

        Raises:
            ValueError: 模板不存在时抛出
        """
        template = VideoService.get_template(template_name)
        if template is None:
            raise ValueError(f"Unknown video template: {template_name}")

        overrides = custom_overrides or {}

        # 构建基础请求参数：模板预设 + 主题
        request_kwargs: Dict[str, Any] = {
            "video_subject": subject,
            "paragraph_number": template.paragraph_number,
            "video_aspect": template.video_aspect,
            "video_concat_mode": template.video_concat_mode,
            "bgm_type": template.bgm_type,
            "max_clip_duration": template.max_clip_duration,
            "voice": VideoVoiceConfig(voice_name=template.voice_name),
            "subtitle": VideoSubtitleConfig(font_size=template.subtitle_font_size),
        }

        # 应用用户覆盖参数
        for override_key, override_value in overrides.items():
            if override_value is None:
                continue
            # 处理嵌套对象：voice / subtitle
            if override_key == "voice" and isinstance(override_value, dict):
                base_voice = request_kwargs["voice"].model_dump()
                base_voice.update(override_value)
                request_kwargs["voice"] = VideoVoiceConfig(**base_voice)
            elif override_key == "subtitle" and isinstance(override_value, dict):
                base_subtitle = request_kwargs["subtitle"].model_dump()
                base_subtitle.update(override_value)
                request_kwargs["subtitle"] = VideoSubtitleConfig(**base_subtitle)
            else:
                request_kwargs[override_key] = override_value

        logger.info(
            f"Created video request from template '{template_name}' "
            f"for subject='{subject}' (overrides: {list(overrides.keys())})"
        )
        return VideoGenerationRequest(**request_kwargs)

    @staticmethod
    def _build_mpt_payload(request: VideoGenerationRequest) -> Dict[str, Any]:
        """Translate open-notebook request to MoneyPrinterTurbo payload.

        MoneyPrinterTurbo expects a flat VideoParams object.
        """
        payload: Dict[str, Any] = {
            "video_subject": request.video_subject,
            "video_aspect": request.video_aspect,
            "language": request.language,
            "paragraph_number": request.paragraph_number,
            "voice_name": request.voice.voice_name,
            "voice_rate": request.voice.voice_rate,
            "voice_volume": request.voice.voice_volume,
            "video_source": request.video_source,
            "max_clip_duration": request.max_clip_duration,
            "video_concat_mode": request.video_concat_mode,
            "bgm_type": request.bgm_type,
            "subtitle_enabled": request.subtitle.enabled,
            "subtitle_font_name": request.subtitle.font_name,
            "subtitle_font_size": request.subtitle.font_size,
            "text_fore_color": request.subtitle.text_color,
            "stroke_color": request.subtitle.stroke_color,
            "stroke_width": request.subtitle.stroke_width,
            "subtitle_position": request.subtitle.position,
            "custom_position": request.subtitle.custom_position,
        }
        if request.video_script:
            payload["video_script"] = request.video_script
        if request.custom_system_prompt:
            payload["custom_system_prompt"] = request.custom_system_prompt
        if request.max_concurrent_tasks:
            payload["max_concurrent_tasks"] = request.max_concurrent_tasks
        return payload

    @staticmethod
    async def submit_video_task(
        request: VideoGenerationRequest,
    ) -> VideoTaskResponse:
        """Submit a new video generation task.

        Returns task ID immediately; generation runs asynchronously
        in the MoneyPrinterTurbo service.
        """
        payload = VideoService._build_mpt_payload(request)
        logger.info(
            f"[VIDEO/GEN] ▸ SUBMIT subject={request.video_subject!r} "
            f"aspect={request.video_aspect} lang={request.language} "
            f"paragraphs={request.paragraph_number} voice={request.voice.voice_name} "
            f"bgm={request.bgm_type} concat={request.video_concat_mode} "
            f"clip_dur={request.max_clip_duration}s"
        )
        logger.debug(f"[VIDEO/GEN]   payload keys={list(payload.keys())}")
        try:
            async with httpx.AsyncClient(timeout=MPT_TIMEOUT) as client:
                endpoint = VideoService._endpoint("/videos")
                logger.info(f"[VIDEO/GEN]   POST {endpoint} timeout={MPT_TIMEOUT}s")
                response = await client.post(
                    endpoint,
                    json=payload,
                )
                logger.info(
                    f"[VIDEO/GEN]   HTTP {response.status_code} "
                    f"content-type={response.headers.get('content-type')}"
                )
                response.raise_for_status()
                data = response.json()
                # MPT response shape may be:
                #   {id: ...}              (flat)
                #   {task_id: ...}         (flat)
                #   {data: {task_id: ...}} (nested, MPT v1 envelope)
                #   {data: {id: ...}}      (nested alternative)
                def _extract_task_id(payload: Any) -> str:
                    if not isinstance(payload, dict):
                        return ""
                    if payload.get("id"):
                        return str(payload["id"])
                    if payload.get("task_id"):
                        return str(payload["task_id"])
                    inner = payload.get("data")
                    if isinstance(inner, dict):
                        if inner.get("task_id"):
                            return str(inner["task_id"])
                        if inner.get("id"):
                            return str(inner["id"])
                    return ""

                task_id = _extract_task_id(data)
                if not task_id:
                    logger.error(f"[VIDEO/GEN] ✗ MPT did not return task_id. body={data}")
                    raise ValueError(
                        f"MoneyPrinterTurbo did not return a task ID: {data}"
                    )
                logger.info(
                    f"[VIDEO/GEN] ◂ SUBMIT OK task_id={task_id} "
                    f"subject={request.video_subject!r}"
                )
                return VideoTaskResponse(
                    task_id=task_id,
                    status="pending",
                    message="Video generation task submitted",
                )
        except httpx.ConnectError as e:
            logger.error(
                f"[VIDEO/GEN] ✗ CONNECT FAIL {MPT_BASE_URL}: {type(e).__name__}: {e}"
            )
            raise RuntimeError(
                f"MoneyPrinterTurbo service unavailable at {MPT_BASE_URL}. "
                "Ensure the service is running (default: http://localhost:8080)."
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[VIDEO/GEN] ✗ HTTP {e.response.status_code} body="
                f"{e.response.text[:500]!r}"
            )
            raise RuntimeError(
                f"MoneyPrinterTurbo error: {e.response.status_code} - "
                f"{e.response.text}"
            ) from e
        except Exception as e:
            logger.exception(f"[VIDEO/GEN] ✗ UNEXPECTED: {type(e).__name__}: {e}")
            raise

    @staticmethod
    async def get_task_status(task_id: str) -> VideoTaskStatus:
        """Get the status of a video generation task.

        MPT v1 routes: ``GET /api/v1/tasks/{task_id}``
        (not ``/videos/{task_id}`` — that path does not exist).
        """
        logger.info(f"[VIDEO/STATUS] ▸ query task_id={task_id}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # MPT uses /tasks/{id} for status lookups
                endpoint = VideoService._endpoint(f"/tasks/{task_id}")
                response = await client.get(endpoint)
                logger.info(
                    f"[VIDEO/STATUS]   HTTP {response.status_code} for {task_id}"
                )
                response.raise_for_status()
                # MPT v1 wraps body in {status, message, data}
                raw = response.json()
                payload = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
                if not isinstance(payload, dict):
                    payload = {}
                state = str(payload.get("state", "unknown"))
                # MPT may report percent via "progress" or "percentage"
                progress = int(payload.get("progress", payload.get("percentage", 0)) or 0)
                status = VideoTaskStatus(
                    id=str(payload.get("id") or payload.get("task_id") or task_id),
                    state=state,
                    progress=progress,
                    message=str(payload.get("message", "")),
                    video_url=(payload.get("videos", [None])[0] if isinstance(payload.get("videos"), list) and payload.get("videos") else payload.get("video_url")),
                    video_path=payload.get("video_path"),
                    script=payload.get("script"),
                    terms=payload.get("terms"),
                    audio_url=payload.get("audio_url"),
                    subtitle_url=payload.get("subtitle_url"),
                    created_at=payload.get("created_at"),
                    updated_at=payload.get("updated_at"),
                    error=payload.get("error"),
                )
                logger.info(
                    f"[VIDEO/STATUS] ◂ task_id={task_id} state={status.state} "
                    f"progress={status.progress}%"
                )
                return status
        except httpx.ConnectError as e:
            logger.error(f"[VIDEO/STATUS] ✗ CONNECT FAIL: {e}")
            raise RuntimeError(
                f"MoneyPrinterTurbo service unavailable: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"[VIDEO/STATUS] ✗ 404 not found task_id={task_id}")
                raise ValueError(f"Video task not found: {task_id}") from e
            logger.error(f"[VIDEO/STATUS] ✗ HTTP {e.response.status_code}: {e}")
            raise RuntimeError(
                f"MoneyPrinterTurbo error: {e.response.status_code}"
            ) from e

    @staticmethod
    async def list_tasks(
        page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """List video generation tasks (paginated).

        MPT v1 route is ``GET /api/v1/tasks`` (with pagination query).
        """
        logger.info(f"[VIDEO/LIST] ▸ page={page} page_size={page_size}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                endpoint = VideoService._endpoint("/tasks")
                response = await client.get(
                    endpoint,
                    params={"page": page, "page_size": page_size},
                )
                logger.info(f"[VIDEO/LIST]   HTTP {response.status_code}")
                response.raise_for_status()
                raw = response.json()
                # Unwrap MPT v1 envelope {status, message, data: {items, total, ...}}
                if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], dict):
                    data = raw["data"]
                else:
                    data = raw
                if isinstance(data, dict) and "items" in data:
                    logger.info(
                        f"[VIDEO/LIST] ◂ {len(data.get('items', []))} items "
                        f"total={data.get('total', '?')}"
                    )
                else:
                    logger.info(f"[VIDEO/LIST] ◂ {type(data).__name__} payload")
                return data
        except httpx.ConnectError as e:
            logger.error(f"[VIDEO/LIST] ✗ CONNECT FAIL: {e}")
            raise RuntimeError(
                f"MoneyPrinterTurbo service unavailable: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"[VIDEO/LIST] ✗ HTTP {e.response.status_code}: {e}")
            raise RuntimeError(
                f"MoneyPrinterTurbo error: {e.response.status_code}"
            ) from e

    @staticmethod
    async def delete_task(task_id: str) -> Dict[str, Any]:
        """Delete a video generation task and its artifacts.

        MPT v1 uses ``DELETE /api/v1/tasks/{task_id}``.
        """
        logger.info(f"[VIDEO/DELETE] ▸ task_id={task_id}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                endpoint = VideoService._endpoint(f"/tasks/{task_id}")
                response = await client.delete(endpoint)
                logger.info(f"[VIDEO/DELETE]   HTTP {response.status_code}")
                response.raise_for_status()
                return response.json() if response.content else {"deleted": True}
        except httpx.ConnectError as e:
            logger.error(f"[VIDEO/DELETE] ✗ CONNECT FAIL: {e}")
            raise RuntimeError(
                f"MoneyPrinterTurbo service unavailable: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"[VIDEO/DELETE] ✗ HTTP {e.response.status_code}: {e}")
            raise RuntimeError(
                f"MoneyPrinterTurbo error: {e.response.status_code}"
            ) from e

    @staticmethod
    async def check_service_health() -> Dict[str, Any]:
        """Check if MoneyPrinterTurbo service is reachable.

        Tries multiple probe endpoints in priority order:
        1. ``{MPT_BASE_URL}/api/v1/videos`` HEAD — exists in MPT v1+ API
        2. ``{MPT_BASE_URL}/docs`` — FastAPI docs (always available)
        3. ``{MPT_BASE_URL}/`` — root index

        MPT v1 may not register a ``/ping`` route (it lives in
        ``app/controllers/ping.py`` but is not always included in
        ``root_api_router``), so we avoid relying on it.
        """
        probes = (
            f"{MPT_BASE_URL}/api/v1/videos",
            f"{MPT_BASE_URL}/docs",
            f"{MPT_BASE_URL}/",
        )
        last_error: Optional[str] = None
        logger.info(f"[VIDEO/HEALTH] ▸ probing MPT at {MPT_BASE_URL} ({len(probes)} probes)")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for url in probes:
                    try:
                        # GET 一次判断；FastAPI /docs/ 永远存在且为 200
                        # 即使其他端点 404/405，只要能 connect 就说明服务在跑
                        response = await client.get(url)
                        logger.debug(
                            f"[VIDEO/HEALTH]   probe {url} → HTTP {response.status_code}"
                        )
                        if response.status_code in {200, 204, 301, 302, 307, 308}:
                            logger.info(
                                f"[VIDEO/HEALTH] ◂ UP probed={url} "
                                f"status={response.status_code}"
                            )
                            return {
                                "available": True,
                                "url": MPT_BASE_URL,
                                "status": "healthy",
                                "probed": url,
                                "http_status": response.status_code,
                            }
                        last_error = f"HTTP {response.status_code} on {url}"
                    except Exception as e:
                        logger.debug(
                            f"[VIDEO/HEALTH]   probe {url} → "
                            f"{type(e).__name__}: {e}"
                        )
                        last_error = f"{type(e).__name__}: {e} ({url})"
                        continue
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
        logger.warning(f"[VIDEO/HEALTH] ✗ DOWN url={MPT_BASE_URL} error={last_error}")
        return {
            "available": False,
            "url": MPT_BASE_URL,
            "status": "unavailable",
            "error": last_error or "All probes failed",
        }

    _mpt_process: Optional[subprocess.Popen] = None

    @staticmethod
    def _resolve_python_executable() -> Optional[str]:
        """解析要启动 MPT 的 Python 解释器。

        在 PyInstaller 打包后的桌面 EXE 中，``sys.executable`` 指向 OpenNotebook.exe
        自身，不能用于启动子进程，否则会以自身为解释器启动 OpenNotebook 而不是 MPT。

        解析优先级：
        1. MPT_PROJECT_DIR/.venv/Scripts/python.exe（项目自带虚拟环境）
        2. 同目录的 ../open-notebook/.venv/Scripts/python.exe（开发环境）
        3. PATH 上的 python.exe（通过 shutil.which）
        4. 注册表中的 Windows 默认 Python
        """
        mpt_dir = os.environ.get("MPT_PROJECT_DIR", r"e:\notebook\MoneyPrinterTurbo")

        # 1. MPT 自带 venv
        candidate = os.path.join(mpt_dir, ".venv", "Scripts", "python.exe")
        if os.path.isfile(candidate):
            return candidate

        # 2. 当前项目的 venv（开发模式或桌面 EXE 共享同一项目时）
        #    _MEIPASS 不可直接拼项目根，所以这里用 mpt_dir 上一级兜底
        for parent in (os.path.dirname(mpt_dir), os.path.dirname(os.path.dirname(mpt_dir))):
            if not parent:
                continue
            candidate = os.path.join(parent, "open-notebook", ".venv", "Scripts", "python.exe")
            if os.path.isfile(candidate):
                return candidate
            candidate = os.path.join(parent, ".venv", "Scripts", "python.exe")
            if os.path.isfile(candidate):
                return candidate

        # 3. PATH 上的 python
        import shutil
        for name in ("python.exe", "python", "python3.exe", "python3"):
            which = shutil.which(name)
            if which:
                return which

        # 4. 如果是开发模式（非 EXE），回退到 sys.executable
        if not getattr(sys, "frozen", False):
            return sys.executable

        # 5. 兜底：返回 None，让调用方报错
        return None

    @staticmethod
    async def launch_moneyprinterturbo() -> Dict[str, Any]:
        """启动 MoneyPrinterTurbo 服务。

        在后台以子进程方式运行 `python main.py`（位于 MPT_PROJECT_DIR 目录）。
        不会阻塞当前请求；启动后前端可轮询 /videos/health 验证是否就绪。
        """
        mpt_dir = os.environ.get(
            "MPT_PROJECT_DIR",
            r"e:\notebook\MoneyPrinterTurbo",
        )
        logger.info(f"[VIDEO/LAUNCH] ▸ requested mpt_dir={mpt_dir}")
        if not os.path.isdir(mpt_dir):
            logger.error(f"[VIDEO/LAUNCH] ✗ mpt_dir not found: {mpt_dir}")
            return {
                "success": False,
                "message": f"未找到 MoneyPrinterTurbo 项目目录: {mpt_dir}",
            }

        # If we already think the service is up, just return success
        if VideoService._mpt_process and VideoService._mpt_process.poll() is None:
            logger.info(
                f"[VIDEO/LAUNCH]   _mpt_process alive pid="
                f"{VideoService._mpt_process.pid}, rechecking health"
            )
            health = await VideoService.check_service_health()
            if health.get("available"):
                logger.info("[VIDEO/LAUNCH] ◂ already healthy, returning early")
                return {
                    "success": True,
                    "message": "MoneyPrinterTurbo 服务已在运行",
                    "url": MPT_BASE_URL,
                }
            logger.warning(
                f"[VIDEO/LAUNCH]   tracked process is alive but MPT not reachable, "
                f"will restart. health={health}"
            )

        main_py = os.path.join(mpt_dir, "main.py")
        if not os.path.isfile(main_py):
            logger.error(f"[VIDEO/LAUNCH] ✗ main.py not found: {main_py}")
            return {
                "success": False,
                "message": f"未找到 main.py: {main_py}",
            }

        # 解析真正的 Python 解释器（EXE 模式下 sys.executable 是 OpenNotebook.exe 自身）
        python_exe = VideoService._resolve_python_executable()
        logger.info(f"[VIDEO/LAUNCH]   resolved python: {python_exe}")
        if not python_exe or not os.path.isfile(python_exe):
            logger.error(
                f"[VIDEO/LAUNCH] ✗ no Python interpreter found "
                f"(frozen={getattr(sys, 'frozen', False)})"
            )
            return {
                "success": False,
                "message": (
                    "无法定位 Python 解释器。请先在系统安装 Python 3.11+，"
                    "或运行 `cd e:\\notebook\\MoneyPrinterTurbo; uv sync` 创建虚拟环境。"
                ),
                "url": MPT_BASE_URL,
            }

        # Build environment for MPT
        env = os.environ.copy()
        env["PYTHONPATH"] = mpt_dir
        # 把 MPT 自己的 Scripts 加到 PATH，确保它在 PATH 中能找到
        mpt_scripts = os.path.join(mpt_dir, ".venv", "Scripts")
        if os.path.isdir(mpt_scripts):
            env["PATH"] = mpt_scripts + os.pathsep + env.get("PATH", "")

        # Windows: use CREATE_NO_WINDOW to avoid spawning a console window
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            log_path = os.path.join(mpt_dir, "open_notebook_mpt.log")
            with open(log_path, "a", encoding="utf-8") as log_file:
                # 同时输出启动命令本身到日志，便于诊断
                log_file.write(
                    f"\n[{_now_str()}] Launching MoneyPrinterTurbo:\n"
                    f"  python: {python_exe}\n"
                    f"  cwd:    {mpt_dir}\n"
                    f"  script: main.py\n"
                )
                log_file.flush()
                logger.info(
                    f"[VIDEO/LAUNCH]   spawn: '{python_exe} main.py' cwd={mpt_dir} "
                    f"log={log_path}"
                )
                proc = subprocess.Popen(
                    [python_exe, "main.py"],
                    cwd=mpt_dir,
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                )
            VideoService._mpt_process = proc
            logger.info(
                f"[VIDEO/LAUNCH] ◂ SPAWN OK pid={proc.pid} python={python_exe} "
                f"cwd={mpt_dir} log={log_path} (MP服务需 30-45s 启动完成)"
            )
            return {
                "success": True,
                "message": (
                    f"已在后台启动 MoneyPrinterTurbo (pid={proc.pid})，"
                    "首次启动需 30-45 秒完成模块加载，请稍候后刷新页面。"
                ),
                "pid": proc.pid,
                "python": python_exe,
                "log_path": log_path,
                "url": MPT_BASE_URL,
            }
        except Exception as e:
            logger.exception(f"[VIDEO/LAUNCH] ✗ spawn failed: {type(e).__name__}: {e}")
            return {
                "success": False,
                "message": f"启动失败: {e}",
            }


def _now_str() -> str:
    """Return current time as ISO-like string for log prefixing."""
    import datetime as _dt
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
