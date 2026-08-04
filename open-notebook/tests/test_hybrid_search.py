# -*- coding: utf-8 -*-
"""Unit tests for the hybrid search (RRF fusion + rerank fallback)."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_notebook.search.hybrid import (
    HybridSearchResult,
    _normalize_id,
    _rrf_fuse,
    hybrid_search,
    hybrid_search_with_details,
)


class TestNormalizeId:
    def test_dict_id(self):
        assert _normalize_id({"tb": "source", "id": "abc"}) == "source:abc"

    def test_str_id(self):
        assert _normalize_id("note:xyz") == "note:xyz"

    def test_none(self):
        assert _normalize_id(None) == ""


class TestRRFFuse:
    def _hits(self, items):
        out = []
        for i in items:
            out.append(
                {
                    "id": f"id_{i}",
                    "title": f"Title {i}",
                    "content": f"content {i}",
                    "parent_id": {"tb": "source", "id": i},
                    "similarity": 0.9 - i * 0.1,
                }
            )
        return out

    def test_fuses_and_sorts_by_rrf(self):
        vector = self._hits([1, 2, 3])
        text = [
            {"id": "id_2", "title": "T2", "content": "c2",
             "parent_id": {"tb": "source", "id": 2}, "relevance": 5.0},
            {"id": "id_9", "title": "T9", "content": "c9",
             "parent_id": {"tb": "source", "id": 9}, "relevance": 4.0},
        ]
        fused = _rrf_fuse(vector, text, top_k=10)
        assert len(fused) == 4
        ids = [r.id for r in fused]
        # id_2 appears in both lists -> highest RRF score -> first
        assert ids[0] == "id_2"
        assert fused[0].sources == ["vector", "text"]
        assert fused[0].result_type == "source"

    def test_limit(self):
        vector = self._hits([1, 2, 3, 4, 5])
        fused = _rrf_fuse(vector, [], top_k=3)
        assert len(fused) == 3

    def test_empty(self):
        assert _rrf_fuse([], [], top_k=10) == []


class TestHybridSearch:
    @pytest.mark.asyncio
    async def test_hybrid_search_returns_results(self):
        fake_vector = [
            {"id": "id_1", "title": "T1", "content": "c1",
             "parent_id": {"tb": "source", "id": 1}, "similarity": 0.8}
        ]
        fake_text = [
            {"id": "id_2", "title": "T2", "content": "c2",
             "parent_id": {"tb": "note", "id": 2}, "relevance": 3.0}
        ]
        with patch("open_notebook.search.hybrid.vector_search", new=AsyncMock(return_value=fake_vector)), \
             patch("open_notebook.search.hybrid.text_search", new=AsyncMock(return_value=fake_text)):
            results = await hybrid_search("test query", rerank=False)
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, HybridSearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_query(self):
        with patch("open_notebook.search.hybrid.vector_search", new=AsyncMock(return_value=[])), \
             patch("open_notebook.search.hybrid.text_search", new=AsyncMock(return_value=[])):
            assert await hybrid_search("") == []

    @pytest.mark.asyncio
    async def test_rerank_fallback_on_error(self):
        fake_vector = [
            {"id": "id_1", "title": "T1", "content": "c1",
             "parent_id": {"tb": "source", "id": 1}, "similarity": 0.8}
        ]
        with patch("open_notebook.search.hybrid.vector_search", new=AsyncMock(return_value=fake_vector)), \
             patch("open_notebook.search.hybrid.text_search", new=AsyncMock(return_value=[])), \
             patch("open_notebook.search.hybrid._call_rerank", new=AsyncMock(return_value=None)):
            results = await hybrid_search("test", rerank=True)
        assert len(results) == 1
        assert results[0].rerank_score is None

    @pytest.mark.asyncio
    async def test_details_output_shape(self):
        fake_vector = [
            {"id": "id_1", "title": "T1", "content": "c1",
             "parent_id": {"tb": "source", "id": 1}, "similarity": 0.8}
        ]
        with patch("open_notebook.search.hybrid.vector_search", new=AsyncMock(return_value=fake_vector)), \
             patch("open_notebook.search.hybrid.text_search", new=AsyncMock(return_value=[])):
            details = await hybrid_search_with_details("test", rerank=False)
        assert details["query"] == "test"
        assert details["vector_hits"] == 1
        assert details["text_hits"] == 0
        assert len(details["results"]) == 1
        assert "rrf_score" in details["results"][0]
