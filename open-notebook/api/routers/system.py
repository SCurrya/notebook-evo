# -*- coding: utf-8 -*-
"""
System health status endpoint.
Provides a single-pane-of-glass view of the whole application stack:
database connectivity, model/provider configuration, worker status and version.
"""
import os
import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from open_notebook.ai.models import Model
from open_notebook.database.repository import db_connection
from open_notebook.utils.version_utils import get_installed_version

router = APIRouter(prefix="/system", tags=["system"])

# Time when the API process started (module import time)
_PROCESS_START = time.time()


def _uptime() -> int:
    """Seconds since the API process started."""
    return int(time.time() - _PROCESS_START)


async def _db_status() -> Dict[str, Any]:
    """Check SurrealDB connectivity."""
    result: Dict[str, Any] = {"connected": False}
    try:
        async with db_connection() as connection:
            await connection.query("RETURN 1;")
            result["connected"] = True
    except Exception as e:  # pragma: no cover - depends on runtime env
        result["error"] = str(e)[:200]
    return result


async def _model_overview() -> Dict[str, Any]:
    """Summarize registered models grouped by provider and type."""
    result: Dict[str, Any] = {"count": 0, "by_provider": {}, "default_chat": None}
    try:
        models = await Model.get_all()
        result["count"] = len(models)
        by_provider: Dict[str, int] = {}
        for m in models:
            provider = m.provider or "unknown"
            by_provider[provider] = by_provider.get(provider, 0) + 1
        result["by_provider"] = by_provider
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


async def _db_stats() -> Dict[str, Any]:
    """Count records in key tables for a quick data-at-a-glance metric."""
    result: Dict[str, Any] = {}
    tables = ("notebook", "source", "note", "task", "insight")
    try:
        async with db_connection() as connection:
            for table in tables:
                rows = await connection.query(
                    f"SELECT count() AS total FROM {table} GROUP ALL;"
                )
                # connection.query returns the list of result rows directly
                if rows and isinstance(rows[0], dict):
                    result[table] = rows[0].get("total", 0)
    except Exception as e:  # pragma: no cover - depends on runtime env
        result["error"] = str(e)[:200]
    return result


async def _worker_status() -> Dict[str, Any]:
    """Check whether the background command worker loop is running.

    ``run_api.py`` sets the ``OPEN_NOTEBOOK_WORKER_RUNNING`` env var when it
    spawns the in-process surreal-commands worker thread. If it is missing we
    report the worker as not running with a hint to start with the worker.
    """
    result: Dict[str, Any] = {"running": False, "max_tasks": None}
    try:
        result["running"] = (
            os.environ.get("OPEN_NOTEBOOK_WORKER_RUNNING") == "1"
        )
        result["max_tasks"] = os.environ.get(
            "OPEN_NOTEBOOK_WORKER_MAX_TASKS", "5"
        )
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


@router.get("/status")
async def system_status() -> Dict[str, Any]:
    """Full system health overview."""
    payload: Dict[str, Any] = {
        "ok": True,
        "version": get_installed_version("open-notebook"),
        "uptime_seconds": _uptime(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "db": await _db_status(),
        "db_stats": await _db_stats(),
        "models": await _model_overview(),
        "worker": await _worker_status(),
    }
    # Overall status: DB + worker must be healthy
    payload["ok"] = bool(payload["db"].get("connected")) and bool(
        payload["worker"].get("running")
    )
    return payload


@router.get("/healthz")
async def healthz() -> Dict[str, Any]:
    """Liveness probe - always answers 200 when the API process is alive."""
    return {"status": "ok", "uptime_seconds": _uptime()}
