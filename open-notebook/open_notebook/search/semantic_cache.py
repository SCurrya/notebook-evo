# -*- coding: utf-8 -*-
"""
Semantic cache for RAG answers.

Stores recent (query -> answer) pairs and their query embeddings. When a new
query arrives, we embed it and compare against cached queries; if a cached
query is similar enough (cosine similarity >= threshold), we return the cached
answer instead of re-running the full pipeline.

This drastically reduces latency and cost for repeated / near-duplicate
questions — a standard production RAG optimization.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

CACHE_FILE = Path(os.getenv("SEMANTIC_CACHE_FILE", "data/semantic_cache.json"))
DEFAULT_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.90"))

_LOCK = threading.Lock()


class SemanticCache:
    """Embedding-based semantic cache backed by a JSON file."""

    def __init__(self, path: Path | str | None = None, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.path = Path(path) if path else CACHE_FILE
        self.threshold = threshold
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to load semantic cache: {e}")
            return []

    def _persist(self) -> None:
        with _LOCK:
            tmp = self.path.with_suffix(".json.tmp")
            try:
                tmp.write_text(
                    json.dumps(self._entries, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                tmp.replace(self.path)
            except Exception as e:
                logger.error(f"Failed to save semantic cache: {e}")

    # --- similarity helpers (avoid numpy dependency for the math) ---

    @staticmethod
    def _dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def _norm(v: List[float]) -> float:
        return (sum(x * x for x in v)) ** 0.5 or 1.0

    def _cosine(self, a: List[float], b: List[float]) -> float:
        return self._dot(a, b) / (self._norm(a) * self._norm(b))

    def get(self, query_embedding: List[float]) -> Optional[Dict[str, Any]]:
        """Return cached entry if a similar query exists, else None."""
        best: Optional[Tuple[float, Dict[str, Any]]] = None
        for entry in self._entries:
            emb = entry.get("query_embedding") or []
            if not emb or len(emb) != len(query_embedding):
                continue
            sim = self._cosine(query_embedding, emb)
            if sim >= self.threshold and (best is None or sim > best[0]):
                best = (sim, entry)
        if best:
            return best[1]
        return None

    def put(
        self,
        query: str,
        query_embedding: List[float],
        answer: str,
        sources: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a new (query, embedding, answer) entry. Evicts oldest beyond max."""
        max_entries = int(os.getenv("SEMANTIC_CACHE_MAX", "200"))
        self._entries.append(
            {
                "query": query,
                "query_embedding": query_embedding,
                "answer": answer,
                "sources": sources,
                "created_at": time.time(),
                "metadata": metadata or {},
            }
        )
        if len(self._entries) > max_entries:
            # Evict oldest by created_at
            self._entries.sort(key=lambda e: e.get("created_at", 0))
            self._entries = self._entries[-max_entries:]
        self._persist()

    def clear(self) -> int:
        """Clear the cache. Returns number of entries removed."""
        n = len(self._entries)
        self._entries = []
        self._persist()
        return n

    def stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "threshold": self.threshold, "max": int(os.getenv("SEMANTIC_CACHE_MAX", "200"))}


async def embed_query(query: str) -> Optional[List[float]]:
    """Embed a query using the default embedding model (best-effort)."""
    try:
        from open_notebook.ai.models import DefaultModels, model_manager

        defaults = await DefaultModels.get_instance()
        model_id = defaults.default_embedding_model
        if not model_id:
            return None
        model = await model_manager.get_model(model_id)
        if not model or not hasattr(model, "embed_query"):
            return None
        result = await model.embed_query(query)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "embedding" in result:
            return result["embedding"]
        return None
    except Exception as e:
        logger.warning(f"Query embedding failed: {e}")
        return None
