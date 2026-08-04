# -*- coding: utf-8 -*-
"""
Agent & Task persistence layer.

Persists agents, tasks, and messages to a JSON file so the multi-agent
system survives API restarts. Atomic writes protect against corruption.

Design:
- Single JSON file per deployment (AGENT_STATE_FILE env override)
- Load on manager init, save after every mutation
- Kept intentionally simple (no DB schema migration needed)
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

DEFAULT_STATE_FILE = Path(os.getenv("AGENT_STATE_FILE", "data/agent_state.json"))

_SAVE_LOCK = threading.Lock()


class AgentStateStore:
    """JSON-file backed store for agent system state."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_STATE_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load persisted state. Returns empty structure if missing/corrupt."""
        if not self.path.exists():
            return {"agents": [], "tasks": [], "messages": []}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("state file root is not a dict")
            return data
        except Exception as e:
            logger.warning(f"Failed to load agent state from {self.path}: {e}")
            # Rename corrupt file so it doesn't keep failing
            try:
                corrupt = self.path.with_suffix(".json.corrupt")
                self.path.rename(corrupt)
                logger.warning(f"Corrupt state moved to {corrupt}")
            except Exception:
                pass
            return {"agents": [], "tasks": [], "messages": []}

    def save(self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]],
             messages: List[Dict[str, Any]]) -> None:
        """Atomically persist the full state."""
        with _SAVE_LOCK:
            tmp = self.path.with_suffix(".json.tmp")
            try:
                tmp.write_text(
                    json.dumps(
                        {"agents": agents, "tasks": tasks, "messages": messages},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                tmp.replace(self.path)
            except Exception as e:
                logger.error(f"Failed to save agent state: {e}")
