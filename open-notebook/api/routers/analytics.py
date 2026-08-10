# -*- coding: utf-8 -*-
"""
Analytics summary endpoint.

Aggregates counts and simple distributions across the main data types
(notebooks, sources, notes, insights, knowledge-graph entities) plus
recent activity, so the frontend can render a data-at-a-glance dashboard.
"""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from open_notebook.database.repository import db_connection

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _count_table(connection, table: str) -> int:
    """Count rows in a table, tolerating missing tables."""
    try:
        rows = await connection.query(
            f"SELECT count() AS total FROM {table} GROUP ALL;"
        )
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("total", 0))
    except Exception:
        return 0
    return 0


@router.get("/summary")
async def analytics_summary() -> Dict[str, Any]:
    """Return aggregate stats for the dashboard overview page."""
    result: Dict[str, Any] = {
        "counts": {},
        "recent_notebooks": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        async with db_connection() as connection:
            # Core counts
            for table in ("notebook", "source", "note", "insight", "task"):
                result["counts"][table] = await _count_table(connection, table)

            # Knowledge-graph entities / relations
            result["counts"]["entity"] = await _count_table(connection, "entity")
            result["counts"]["relation"] = await _count_table(connection, "relation")

            # Recent notebooks (most recently updated, top 5)
            try:
                rows = await connection.query(
                    "SELECT id, name, updated FROM notebook "
                    "ORDER BY updated DESC LIMIT 5;"
                )
                recent = []
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    recent.append(
                        {
                            "id": str(item.get("id", "")),
                            "name": item.get("name", ""),
                            "updated": item.get("updated"),
                        }
                    )
                result["recent_notebooks"] = recent
            except Exception:
                result["recent_notebooks"] = []
    except Exception as e:  # pragma: no cover - depends on runtime env
        result["error"] = str(e)[:200]
    return result
