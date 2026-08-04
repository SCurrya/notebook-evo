"""
Log management router.

Provides endpoints for viewing, filtering, searching, and clearing
application logs. Used by the startup log viewer UI.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from api.log_service import LogEntry, LogFile, LogService

router = APIRouter()


@router.get("/logs/files", response_model=List[LogFile])
async def list_log_files():
    """List all available log files."""
    return LogService.list_log_files()


@router.get("/logs/{filename}", response_model=List[LogEntry])
async def read_log(
    filename: str,
    max_lines: int = Query(1000, ge=1, le=10000),
    level: Optional[str] = Query(None, description="Filter by level (INFO/WARNING/ERROR)"),
    search: Optional[str] = Query(None, description="Case-insensitive search"),
    reverse: bool = Query(True, description="Newest first"),
):
    """Read a log file with optional filtering and search."""
    try:
        return LogService.read_log(
            filename=filename,
            max_lines=max_lines,
            level_filter=level,
            search=search,
            reverse=reverse,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OSError as e:
        logger.error(f"Failed to read log {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/logs/{filename}/download")
async def download_log(filename: str):
    """Download a raw log file."""
    try:
        path = LogService.get_log_path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"Log file not found: {filename}")
        return FileResponse(
            str(path),
            media_type="text/plain",
            filename=filename,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/logs/{filename}")
async def clear_log(filename: str):
    """Clear (truncate) a specific log file."""
    try:
        return LogService.clear_log(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/logs")
async def clear_all_logs():
    """Clear all log files."""
    return LogService.clear_all_logs()
