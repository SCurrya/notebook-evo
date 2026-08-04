# -*- coding: utf-8 -*-
"""Unit tests for semantic cache and advanced retrieval."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestSemanticCache:
    def test_get_put_roundtrip(self, tmp_path):
        from open_notebook.search.semantic_cache import SemanticCache

        cache = SemanticCache(tmp_path / "cache.json", threshold=0.9)
        emb = [1.0, 0.0, 0.0, 0.0]
        cache.put("什么是MCP", emb, "MCP 由 Anthropic 提出", ["s1"])
        hit = cache.get(emb)
        assert hit is not None
        assert hit["answer"] == "MCP 由 Anthropic 提出"

    def test_similar_query_hit(self, tmp_path):
        from open_notebook.search.semantic_cache import SemanticCache

        cache = SemanticCache(tmp_path / "cache.json", threshold=0.95)
        cache.put("什么是MCP协议", [1.0, 0.0, 0.0, 0.0], "答案A", [])
        # 近似的查询向量 -> 命中
        hit = cache.get([0.97, 0.05, 0.01, 0.0])
        assert hit is not None

    def test_dissimilar_query_miss(self, tmp_path):
        from open_notebook.search.semantic_cache import SemanticCache

        cache = SemanticCache(tmp_path / "cache.json", threshold=0.95)
        cache.put("什么是MCP", [1.0, 0.0, 0.0, 0.0], "答案A", [])
        # 完全不同的查询向量 -> 未命中
        hit = cache.get([0.0, 1.0, 0.0, 0.0])
        assert hit is None

    def test_clear(self, tmp_path):
        from open_notebook.search.semantic_cache import SemanticCache

        cache = SemanticCache(tmp_path / "cache.json")
        cache.put("q", [1.0, 0.0], "a", [])
        assert cache.clear() == 1
        assert cache.stats()["entries"] == 0


class TestClassifyQuery:
    def test_simple_short(self):
        from open_notebook.search.advanced_retrieval import classify_query

        assert classify_query("MCP") == "simple"

    def test_hybrid_mid(self):
        from open_notebook.search.advanced_retrieval import classify_query

        assert classify_query("什么是向量数据库") == "hybrid"

    def test_deep_complex(self):
        from open_notebook.search.advanced_retrieval import classify_query

        assert classify_query("为什么 GraphRAG 比传统 RAG 更适合多跳推理？") == "deep"
        assert classify_query("how to deploy a RAG system with reranking") == "deep"


class TestAdaptiveHybridSearch:
    @pytest.mark.asyncio
    async def test_cache_hit_fast_path(self, tmp_path, monkeypatch):
        import open_notebook.search.advanced_retrieval as adv

        # 预置缓存命中
        from open_notebook.search.semantic_cache import SemanticCache

        cache_path = tmp_path / "cache.json"
        cache = SemanticCache(cache_path)
        cache.put("什么是MCP", [1.0, 0.0, 0.0, 0.0], "缓存答案", [])

        monkeypatch.setattr("open_notebook.search.semantic_cache.CACHE_FILE", cache_path)
        with patch("open_notebook.search.semantic_cache.embed_query", new=AsyncMock(return_value=[1.0, 0.0, 0.0, 0.0])):
            result = await adv.adaptive_hybrid_search("什么是MCP", use_hyde=False)
        assert result["diagnostics"]["cache_hit"] is True
        assert result["results"][0]["id"] == "cached"

    @pytest.mark.asyncio
    async def test_deep_strategy_uses_rerank(self, tmp_path, monkeypatch):
        import open_notebook.search.advanced_retrieval as adv

        monkeypatch.setattr("open_notebook.search.semantic_cache.CACHE_FILE", tmp_path / "cache.json")
        captured = {}

        async def fake_hybrid(query, limit, ss, sn, ms, rerank):
            captured["rerank"] = rerank
            from open_notebook.search.hybrid import HybridSearchResult

            return [
                HybridSearchResult(
                    id="x", title="T", content="C", parent_id="source:1",
                    result_type="source", score=0.5,
                )
            ]

        with patch("open_notebook.search.semantic_cache.embed_query", new=AsyncMock(return_value=None)), \
             patch("open_notebook.search.hybrid.hybrid_search", new=fake_hybrid):
            result = await adv.adaptive_hybrid_search(
                "为什么 GraphRAG 比传统 RAG 更适合多跳推理？", use_hyde=False, use_cache=True
            )
        assert captured["rerank"] is True
        assert result["diagnostics"]["strategy"] == "deep"

    @pytest.mark.asyncio
    async def test_hyde_generation_used_for_deep(self, tmp_path, monkeypatch):
        import open_notebook.search.advanced_retrieval as adv

        monkeypatch.setattr("open_notebook.search.semantic_cache.CACHE_FILE", tmp_path / "cache.json")

        async def fake_hybrid(query, limit, ss, sn, ms, rerank):
            from open_notebook.search.hybrid import HybridSearchResult

            return [HybridSearchResult(id="y", title="T", content="C", parent_id="note:2", result_type="note", score=0.5)]

        with patch("open_notebook.search.semantic_cache.embed_query", new=AsyncMock(return_value=None)), \
             patch.object(adv, "hyde_generate", new=AsyncMock(return_value="假设文档内容")), \
             patch("open_notebook.search.hybrid.hybrid_search", new=fake_hybrid):
            result = await adv.adaptive_hybrid_search("如何部署 RAG 系统", use_hyde=True, use_cache=True)
        assert result["diagnostics"]["hyde_used"] is True
