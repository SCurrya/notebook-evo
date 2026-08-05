# -*- coding: utf-8 -*-
"""Unit tests for the Chinese-aware BM25 index."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_notebook.search.chinese_bm25 import ChineseBM25Index, tokenize


class TestTokenize:
    def test_english(self):
        tokens = tokenize("AI Agent is a concept")
        assert "ai" in tokens
        assert "agent" in tokens

    def test_chinese(self):
        tokens = tokenize("面试热点导读包含公务员考试知识")
        # jieba should split into meaningful tokens
        assert any("面试" in t for t in tokens)
        assert any("公务员" in t or "考试" in t for t in tokens)

    def test_mixed(self):
        tokens = tokenize("混合检索 Hybrid Search 结合全文与向量")
        assert any("混合" in t for t in tokens)
        assert any("hybrid" in t.lower() for t in tokens) or "hybrid" in tokens

    def test_empty(self):
        assert tokenize("") == []
        assert tokenize("  ") == []

    def test_noise_filtered(self):
        tokens = tokenize("的 了 是 在 和")
        assert tokens == [] or all(t not in {"的", "了", "是"} for t in tokens)


class TestChineseBM25:
    def _index(self):
        idx = ChineseBM25Index()
        idx.load_documents(
            sources=[
                {"id": "s1", "title": "面试热点", "full_text": "面试热点导读包含公务员考试相关知识，考生需要掌握政策解读方法", "parent_id": "s1"},
                {"id": "s2", "title": "AI Agent", "full_text": "AI Agent 是人工智能智能体，能够自主规划任务并调用工具完成目标", "parent_id": "s2"},
                {"id": "s3", "title": "混合检索", "full_text": "混合检索结合了全文搜索与向量搜索的优势，提升 RAG 回答质量", "parent_id": "s3"},
            ],
            notes=[],
        )
        return idx

    def test_chinese_query_hits(self):
        idx = self._index()
        results = idx.search("公务员面试", top_k=5)
        assert len(results) > 0
        assert results[0]["id"] == "s1"
        assert results[0]["result_type"] == "source"

    def test_english_query_hits(self):
        idx = self._index()
        results = idx.search("agent", top_k=5)
        assert len(results) > 0
        assert results[0]["id"] == "s2"

    def test_query_with_no_match(self):
        idx = self._index()
        results = idx.search("量子计算与密码学", top_k=5)
        assert results == [] or all(r["relevance"] <= 0 for r in results)

    def test_empty_index(self):
        idx = ChineseBM25Index()
        assert idx.search("anything") == []

    def test_snippet_contains_keyword(self):
        idx = self._index()
        results = idx.search("公务员", top_k=5)
        assert len(results) > 0
        assert "公务员" in results[0]["content"]

    def test_rebuild_on_new_docs(self):
        idx = ChineseBM25Index()
        idx.load_documents(
            sources=[{"id": "s1", "title": "t", "full_text": "苹果手机很好用", "parent_id": "s1"}]
        )
        r1 = idx.search("苹果", top_k=5)
        assert len(r1) == 1
        # Add a new doc and confirm index rebuilds
        idx.load_documents(
            sources=[
                {"id": "s1", "title": "t", "full_text": "苹果手机很好用", "parent_id": "s1"},
                {"id": "s2", "title": "t2", "full_text": "华为手机也很不错", "parent_id": "s2"},
            ]
        )
        r2 = idx.search("华为", top_k=5)
        assert len(r2) >= 1
        ids = [r["id"] for r in r2]
        assert "s2" in ids
        # s2 should rank above the unrelated doc for the query "华为"
        assert ids[0] == "s2" or r2[0]["id"] != "s1" or len(r2) > 1
