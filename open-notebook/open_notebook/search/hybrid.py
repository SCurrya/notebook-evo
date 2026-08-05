# -*- coding: utf-8 -*-
"""
Hybrid search: BM25 full-text + vector search with RRF fusion and optional rerank.

Pipeline:
  1. Recalls candidates from both BM25 (full-text) and vector (semantic) search
  2. Fuses the two ranked lists using Reciprocal Rank Fusion (RRF)
  3. Optionally reranks the fused top-k with a Cross-Encoder reranker
     (configurable via RERANK_PROVIDER; silently degrades to RRF-only)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from open_notebook.domain.notebook import text_search, vector_search

RRF_K = 60.0  # RRF smoothing constant
DEFAULT_RERANK_TOP_K = 10


@dataclass
class HybridSearchResult:
    id: str
    title: str
    content: str
    parent_id: str
    result_type: str
    score: float
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
    rerank_score: Optional[float] = None
    sources: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Guard: SurrealDB BM25 `matches` can surface as list content
        self.title = _to_text(self.title)
        self.content = _to_text(self.content)
        self.parent_id = _to_text(self.parent_id)


def _normalize_id(raw_id: Any) -> str:
    """Convert SurrealDB record id (dict or str) into 'table:id' string."""
    if raw_id is None:
        return ""
    if isinstance(raw_id, dict):
        tb = raw_id.get("tb", "")
        id_part = raw_id.get("id", "")
        return f"{tb}:{id_part}"
    return str(raw_id)


def _to_text(value: Any) -> str:
    """Coerce content fields to plain text.

    text_search can return `matches` as a list of dicts (SurrealDB BM25
    highlight matches) or content as a list. Normalize everything to a
    single string for downstream consumers.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p)
    return str(value)


def _build_rerank_payload(query: str, results: List[HybridSearchResult]) -> Dict[str, Any]:
    """Build a payload for an OpenAI-compatible rerank endpoint."""
    return {
        "model": os.getenv("RERANK_MODEL", "bge-reranker-v2-m3"),
        "query": query,
        "documents": [r.content[:2000] for r in results],
        "top_n": len(results),
    }


async def _call_rerank(query: str, results: List[HybridSearchResult]) -> Optional[List[float]]:
    """Call an OpenAI-compatible rerank API. Returns scores aligned with results."""
    url = os.getenv("RERANK_URL", "").strip()
    api_key = os.getenv("RERANK_API_KEY", "").strip()
    if not url or not results:
        return None

    import httpx

    payload = _build_rerank_payload(query, results)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        # Support both {results:[{index,relevance_score}]} and {data:[{index,score}]}
        raw = data.get("results") or data.get("data") or []
        ranked = sorted(raw, key=lambda x: float(x.get("relevance_score") or x.get("score") or 0), reverse=True)
        scores: List[float] = [0.0] * len(results)
        for item in ranked:
            idx = int(item.get("index", -1))
            if 0 <= idx < len(results):
                scores[idx] = float(item.get("relevance_score") or item.get("score") or 0.0)
        return scores
    except Exception as e:
        logger.warning(f"Rerank call failed, falling back to RRF-only: {e}")
        return None


def _rrf_fuse(
    vector_hits: List[Dict[str, Any]],
    text_hits: List[Dict[str, Any]],
    top_k: int,
) -> List[HybridSearchResult]:
    """Fuse two ranked lists with Reciprocal Rank Fusion."""
    rrf_scores: Dict[str, Dict[str, Any]] = {}

    def accumulate(hits: List[Dict[str, Any]], kind: str) -> None:
        for rank, hit in enumerate(hits):
            if not isinstance(hit, dict):
                continue
            rid = _normalize_id(hit.get("id") or hit.get("item_id") or hit.get("parent_id"))
            if not rid:
                continue
            entry = rrf_scores.setdefault(rid, {
                "id": rid,
                "title": _to_text(hit.get("title")),
                "content": _to_text(hit.get("content") or hit.get("matches")),
                "parent_id": _normalize_id(hit.get("parent_id") or hit.get("item_id") or hit.get("id")),
                "rrf": 0.0,
                "vector_score": None,
                "text_score": None,
                "sources": [],
            })
            entry["rrf"] += 1.0 / (RRF_K + rank + 1)
            entry["sources"].append(kind)
            if kind == "vector":
                s = hit.get("similarity") or hit.get("score") or hit.get("relevance")
                if s is not None:
                    try:
                        entry["vector_score"] = float(s)
                    except (TypeError, ValueError):
                        pass
                entry["title"] = _to_text(hit.get("title")) or entry["title"]
                entry["content"] = _to_text(hit.get("content")) or entry["content"]
                entry["parent_id"] = _normalize_id(hit.get("parent_id") or entry["parent_id"])
            else:
                s = hit.get("relevance") or hit.get("score") or hit.get("similarity")
                if s is not None:
                    try:
                        entry["text_score"] = float(s)
                    except (TypeError, ValueError):
                        pass
                if hit.get("title"):
                    entry["title"] = _to_text(hit["title"])
                if hit.get("content"):
                    entry["content"] = _to_text(hit["content"])
                if hit.get("parent_id"):
                    entry["parent_id"] = _normalize_id(hit["parent_id"])

    accumulate(vector_hits, "vector")
    accumulate(text_hits, "text")

    ranked = sorted(rrf_scores.values(), key=lambda x: x["rrf"], reverse=True)
    results: List[HybridSearchResult] = []
    for entry in ranked[:top_k]:
        parent = entry["parent_id"]
        result_type = parent.split(":", 1)[0] if ":" in parent else ""
        results.append(
            HybridSearchResult(
                id=entry["id"],
                title=entry["title"],
                content=entry["content"],
                parent_id=parent,
                result_type=result_type,
                score=entry["rrf"],
                vector_score=entry["vector_score"],
                text_score=entry["text_score"],
                sources=entry["sources"],
            )
        )
    return results


async def hybrid_search(
    query: str,
    limit: int = 10,
    search_sources: bool = True,
    search_notes: bool = True,
    minimum_score: float = 0.2,
    rerank: bool = True,
    vector_hits: int = 20,
    text_hits: int = 20,
) -> List[HybridSearchResult]:
    """Run hybrid search: vector + BM25, fused by RRF, optionally reranked."""
    if not query:
        return []

    vector_results: List[Dict[str, Any]] = []
    text_results: List[Dict[str, Any]] = []

    # Parallel dual-path recall
    try:
        vector_results = await vector_search(
            keyword=query,
            results=vector_hits,
            source=search_sources,
            note=search_notes,
            minimum_score=minimum_score,
        )
    except Exception as e:
        logger.warning(f"Vector search failed during hybrid search: {e}")

    try:
        text_results = await text_search(
            keyword=query,
            results=text_hits,
            source=search_sources,
            note=search_notes,
        )
    except Exception as e:
        logger.warning(f"Text search failed during hybrid search: {e}")

    if not vector_results and not text_results:
        return []

    fused = _rrf_fuse(vector_results or [], text_results or [], limit)

    if rerank and fused:
        scores = await _call_rerank(query, fused)
        if scores is not None:
            for r, s in zip(fused, scores):
                r.rerank_score = s
            fused.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)

    return fused


async def hybrid_search_with_details(
    query: str,
    limit: int = 10,
    search_sources: bool = True,
    search_notes: bool = True,
    minimum_score: float = 0.2,
    rerank: bool = True,
) -> Dict[str, Any]:
    """Run hybrid search and return results + diagnostic details (for the debug panel)."""
    vector_hits_count = max(limit * 2, 20)
    text_hits_count = max(limit * 2, 20)

    vector_results = []
    text_results = []
    try:
        vector_results = await vector_search(
            keyword=query,
            results=vector_hits_count,
            source=search_sources,
            note=search_notes,
            minimum_score=minimum_score,
        )
    except Exception as e:
        logger.warning(f"hybrid debug: vector failed: {e}")

    try:
        text_results = await text_search(
            keyword=query,
            results=text_hits_count,
            source=search_sources,
            note=search_notes,
        )
    except Exception as e:
        logger.warning(f"hybrid debug: text failed: {e}")

    fused = _rrf_fuse(vector_results or [], text_results or [], limit)
    rerank_used = False
    if rerank and fused:
        scores = await _call_rerank(query, fused)
        if scores is not None:
            rerank_used = True
            for r, s in zip(fused, scores):
                r.rerank_score = s
            fused.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)

    return {
        "query": query,
        "vector_hits": len(vector_results or []),
        "text_hits": len(text_results or []),
        "rerank_used": rerank_used,
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "content_preview": r.content[:500],
                "parent_id": r.parent_id,
                "result_type": r.result_type,
                "rrf_score": round(r.score, 6),
                "vector_score": round(r.vector_score, 6) if r.vector_score is not None else None,
                "text_score": round(r.text_score, 6) if r.text_score is not None else None,
                "rerank_score": round(r.rerank_score, 6) if r.rerank_score is not None else None,
                "sources": r.sources,
            }
            for r in fused
        ],
    }
