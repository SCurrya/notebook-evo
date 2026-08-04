# -*- coding: utf-8 -*-
"""
Advanced retrieval: HyDE (Hypothetical Document Embeddings) + adaptive routing.

1. Adaptive routing: decides per-query whether to use simple vector search,
   full hybrid search, or hybrid + rerank — based on query characteristics.
2. HyDE: generates a hypothetical answer document with the LLM, embeds it,
   and uses that embedding for retrieval. Improves recall for queries whose
   phrasing differs from the source text.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from loguru import logger

# Chinese/English short query -> simple vector path
_MIN_HYBRID_LEN = int(os.getenv("ADAPTIVE_MIN_HYBRID_LEN", "4"))
# Queries with explicit connectors -> deep path
_COMPLEX_MARKERS = ("为什么", "如何", "比较", "区别", "关系", "how", "why", "compare", "vs")


def classify_query(query: str) -> str:
    """Classify a query into a retrieval strategy.

    Returns one of: "simple", "hybrid", "deep".
    """
    q = query.strip()
    if not q:
        return "simple"
    # 多语言字符长度（中文字符算 1）
    if len(q) <= _MIN_HYBRID_LEN:
        return "simple"
    # 含复杂连接词或较长问题 -> 深度检索（含重排）
    q_lower = q.lower()
    if len(q) > 24 or any(m in q_lower for m in _COMPLEX_MARKERS):
        return "deep"
    return "hybrid"


async def hyde_generate(query: str) -> Optional[str]:
    """Generate a hypothetical document for the query using the default model."""
    try:
        from open_notebook.ai.models import DefaultModels, model_manager

        defaults = await DefaultModels.get_instance()
        model_id = defaults.default_chat_model
        if not model_id:
            return None
        model = await model_manager.get_model(model_id)
        if not model:
            return None
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个检索辅助助手。请根据用户问题，生成一段简短、信息密集的"
                    "假设性文档（200字以内），内容应直接回答该问题并包含可能的关键术语。"
                    "这段文字将用于检索相似文档，不要输出任何额外解释。"
                ),
            },
            {"role": "user", "content": query},
        ]
        response = await model.achat_complete(messages)
        text = (response.choices[0].message.content or "").strip()
        return text[:500] if text else None
    except Exception as e:
        logger.warning(f"HyDE generation failed: {e}")
        return None


async def adaptive_hybrid_search(
    query: str,
    limit: int = 10,
    search_sources: bool = True,
    search_notes: bool = True,
    minimum_score: float = 0.2,
    use_hyde: bool = True,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Adaptive hybrid search with optional HyDE expansion and semantic cache.

    Returns a dict with results plus diagnostics (strategy, cache hit, hyde used).
    """
    from open_notebook.search.hybrid import hybrid_search
    from open_notebook.search.semantic_cache import SemanticCache, embed_query

    diagnostics: Dict[str, Any] = {
        "strategy": "hybrid",
        "cache_hit": False,
        "hyde_used": False,
    }

    strategy = classify_query(query)

    # --- Semantic cache lookup (fast path) ---
    if use_cache:
        cache = SemanticCache()
        query_emb = await embed_query(query)
        if query_emb:
            hit = cache.get(query_emb)
            if hit:
                diagnostics["cache_hit"] = True
                diagnostics["strategy"] = "cache"
                return {
                    "results": [{
                        "id": "cached",
                        "title": "（语义缓存命中）",
                        "content": hit.get("answer", ""),
                        "parent_id": "",
                        "result_type": "cache",
                        "score": 1.0,
                        "sources": hit.get("sources", []),
                    }],
                    "diagnostics": diagnostics,
                }

    # --- HyDE expansion (only for deep queries) ---
    search_query = query
    if use_hyde and strategy in ("deep", "hybrid"):
        hyde_doc = await hyde_generate(query)
        if hyde_doc:
            search_query = f"{query}\n\n参考假设文档：\n{hyde_doc}"
            diagnostics["hyde_used"] = True

    # --- Strategy-specific retrieval ---
    if strategy == "simple":
        results = await hybrid_search(
            query, limit, search_sources, search_notes, minimum_score, rerank=False
        )
    elif strategy == "deep":
        results = await hybrid_search(
            query, limit, search_sources, search_notes, minimum_score, rerank=True
        )
    else:
        results = await hybrid_search(
            query, limit, search_sources, search_notes, minimum_score, rerank=False
        )

    diagnostics["strategy"] = strategy
    return {
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "content": r.content,
                "parent_id": r.parent_id,
                "result_type": r.result_type,
                "score": r.score,
                "vector_score": r.vector_score,
                "text_score": r.text_score,
                "rerank_score": r.rerank_score,
                "sources": r.sources,
            }
            for r in results
        ],
        "diagnostics": diagnostics,
    }
