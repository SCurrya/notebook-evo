"""
Log management service.

Provides read/filter/search/clear operations on application log files.
Supports both the dev mode logs (./logs/) and desktop EXE logs
(%APPDATA%/OpenNotebook/logs/).
"""

import os
import pathlib
import re
from datetime import datetime
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel


def get_log_dir() -> pathlib.Path:
    """Get the active log directory.

    Priority:
    1. OPEN_NOTEBOOK_LOG_DIR env var (explicit override)
    2. Desktop EXE: %APPDATA%/OpenNotebook/logs/
    3. Dev mode: ./logs/ (project root)
    """
    explicit = os.environ.get("OPEN_NOTEBOOK_LOG_DIR")
    if explicit:
        path = pathlib.Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path

    appdata = os.environ.get("APPDATA")
    if appdata:
        desktop_logs = pathlib.Path(appdata) / "OpenNotebook" / "logs"
        if desktop_logs.exists():
            return desktop_logs

    project_root = pathlib.Path(__file__).parent.parent
    dev_logs = project_root / "logs"
    dev_logs.mkdir(parents=True, exist_ok=True)
    return dev_logs


class LogEntry(BaseModel):
    """A single log line with parsed metadata."""
    timestamp: Optional[str] = None
    level: Optional[str] = None
    message: str
    raw: str
    line_number: int


class LogFile(BaseModel):
    """Metadata for a log file."""
    name: str
    size: int
    modified: Optional[str] = None
    line_count: Optional[int] = None


class LogService:
    """Service for reading and managing application logs."""

    # Log level regex (matches loguru default format)
    _LEVEL_PATTERN = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
        r"\s*\|\s*(?P<level>TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)"
        r"\s*\|\s*(?P<module>[^|]+?)\s*\|\s*(?P<function>[^|]+?)\s*\|\s*(?P<line>\d+)\s*\|\s*(?P<message>.+)",
        re.IGNORECASE,
    )
    # Simpler format (HH:mm:ss | LEVEL | message)
    _SIMPLE_PATTERN = re.compile(
        r"(?P<timestamp>\d{2}:\d{2}:\d{2})"
        r"\s*\|\s*(?P<level>TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)"
        r"\s*\|\s*(?P<message>.+)",
        re.IGNORECASE,
    )

    @staticmethod
    def list_log_files() -> List[LogFile]:
        """List all log files in the log directory."""
        log_dir = get_log_dir()
        files: List[LogFile] = []
        if not log_dir.exists():
            return files
        for entry in sorted(log_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if entry.is_file():
                stat = entry.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                files.append(
                    LogFile(
                        name=entry.name,
                        size=stat.st_size,
                        modified=modified,
                    )
                )
        return files

    @staticmethod
    def read_log(
        filename: str,
        max_lines: int = 1000,
        level_filter: Optional[str] = None,
        search: Optional[str] = None,
        reverse: bool = True,
    ) -> List[LogEntry]:
        """Read a log file with optional filtering and search.

        Args:
            filename: Log file name (basename only, no path)
            max_lines: Maximum number of lines to return
            level_filter: Filter by log level (INFO, WARNING, ERROR, etc.)
            search: Case-insensitive search string
            reverse: If True, return newest lines first
        """
        log_dir = get_log_dir()
        # Security: only allow basename, no path traversal
        safe_name = pathlib.Path(filename).name
        log_path = log_dir / safe_name
        if not log_path.is_file():
            raise FileNotFoundError(f"Log file not found: {filename}")

        entries: List[LogEntry] = []
        level_upper = level_filter.upper() if level_filter else None
        search_lower = search.lower() if search else None

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, raw_line in enumerate(f, 1):
                    line = raw_line.rstrip("\n\r")
                    if not line:
                        continue

                    # Parse log line
                    entry = LogService._parse_line(line, line_num)

                    # Apply level filter
                    if level_upper and entry.level:
                        if entry.level.upper() != level_upper:
                            continue
                    elif level_upper and not entry.level:
                        continue

                    # Apply search filter
                    if search_lower and search_lower not in line.lower():
                        continue

                    entries.append(entry)

                    if len(entries) >= max_lines:
                        break
        except OSError as e:
            logger.error(f"Failed to read log file {filename}: {e}")
            raise

        if reverse:
            entries.reverse()
        return entries

    @staticmethod
    def _parse_line(line: str, line_num: int) -> LogEntry:
        """Parse a log line into a LogEntry."""
        # Try full loguru format first
        match = LogService._LEVEL_PATTERN.match(line)
        if match:
            return LogEntry(
                timestamp=match.group("timestamp"),
                level=match.group("level").upper(),
                message=match.group("message"),
                raw=line,
                line_number=line_num,
            )
        # Try simple format
        match = LogService._SIMPLE_PATTERN.match(line)
        if match:
            return LogEntry(
                timestamp=match.group("timestamp"),
                level=match.group("level").upper(),
                message=match.group("message"),
                raw=line,
                line_number=line_num,
            )
        # Unparseable line
        return LogEntry(
            message=line,
            raw=line,
            line_number=line_num,
        )

    @staticmethod
    def clear_log(filename: str) -> dict:
        """Clear (truncate) a log file."""
        log_dir = get_log_dir()
        safe_name = pathlib.Path(filename).name
        log_path = log_dir / safe_name
        if not log_path.is_file():
            raise FileNotFoundError(f"Log file not found: {filename}")
        size_before = log_path.stat().st_size
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("")
        logger.info(f"Cleared log file: {filename} ({size_before} bytes)")
        return {
            "filename": filename,
            "cleared": True,
            "bytes_freed": size_before,
        }

    @staticmethod
    def clear_all_logs() -> dict:
        """Clear all log files in the log directory."""
        log_dir = get_log_dir()
        cleared = []
        total_freed = 0
        if log_dir.exists():
            for entry in log_dir.iterdir():
                if entry.is_file() and entry.suffix in (".log", ".txt"):
                    size = entry.stat().st_size
                    with open(entry, "w", encoding="utf-8") as f:
                        f.write("")
                    cleared.append(entry.name)
                    total_freed += size
        logger.info(
            f"Cleared {len(cleared)} log files, freed {total_freed} bytes"
        )
        return {
            "cleared_files": cleared,
            "count": len(cleared),
            "bytes_freed": total_freed,
        }

    @staticmethod
    def get_log_path(filename: str) -> pathlib.Path:
        """Get the full path for a log file (for download)."""
        log_dir = get_log_dir()
        safe_name = pathlib.Path(filename).name
        return log_dir / safe_name
