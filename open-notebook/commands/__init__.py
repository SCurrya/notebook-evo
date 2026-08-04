"""Surreal-commands integration for Open Notebook"""

from loguru import logger

from .embedding_commands import (
    embed_insight_command,
    embed_note_command,
    embed_source_command,
    rebuild_embeddings_command,
)
from .example_commands import analyze_data_command, process_text_command
from .source_commands import process_source_command

# podcast_commands 依赖重型可选库（podcast_creator -> moviepy -> imageio），
# 在 PyInstaller 打包的桌面 EXE 中可能不可用，因此改为可选导入。
try:
    from .podcast_commands import generate_podcast_command
    _PODCAST_AVAILABLE = True
except Exception as _podcast_err:  # noqa: BLE001
    logger.warning(
        f"podcast_commands not available, podcast features disabled: {_podcast_err}"
    )
    generate_podcast_command = None  # type: ignore[assignment]
    _PODCAST_AVAILABLE = False

__all__ = [
    # Embedding commands
    "embed_note_command",
    "embed_insight_command",
    "embed_source_command",
    "rebuild_embeddings_command",
    # Other commands
    "process_source_command",
    "process_text_command",
    "analyze_data_command",
]
if _PODCAST_AVAILABLE:
    __all__.append("generate_podcast_command")
