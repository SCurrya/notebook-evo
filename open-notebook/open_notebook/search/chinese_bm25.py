# -*- coding: utf-8 -*-
"""
Chinese-aware BM25 retrieval (enhancement).

SurrealDB's built-in FULLTEXT search uses blank/camel/class tokenizers which
treat contiguous Chinese text as a single token, so `fn::text_search` returns
nothing for Chinese queries. This module provides a Python-side BM25 index
using jieba segmentation + rank_bm25 so hybrid retrieval actually works for
Chinese content.

Design:
- Loads source/note text from SurrealDB (lazy, cached)
- Tokenizes with jieba (handles CJK + English)
- Builds a rank_bm25 corpus on demand, rebuilds when data changes
- Returns results in the same shape as fn::text_search so hybrid.py can fuse
"""
from __future__ import annotations

import hashlib
import os
import re
import threading
from typing import Any, Dict, List, Optional

from loguru import logger
from rank_bm25 import BM25Okapi

try:
    import jieba
except Exception:  # pragma: no cover - jieba optional but recommended
    jieba = None  # type: ignore

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]{2,}|[\u4e00-\u9fff]")

_lock = threading.Lock()


def tokenize(text: str) -> List[str]:
    """Tokenize mixed Chinese/English text."""
    if not text:
        return []
    if jieba is not None:
        # jieba works on the whole string, keeps English words as tokens too
        tokens = [t.strip().lower() for t in jieba.cut(text) if t.strip()]
    else:
        tokens = _WORD_RE.findall(text.lower())
    # Filter: drop pure punctuation / single noise tokens
    return [t for t in tokens if t and not _is_noise(t)]


def _is_noise(token: str) -> bool:
    if token in {"的", "了", "是", "在", "和", "与", "及", "或", "等"}:
        return True
    if len(token) == 1 and not token.isalnum():
        return True
    return False


class ChineseBM25Index:
    """Python BM25 index over sources/notes for Chinese hybrid search."""

    def __init__(self, max_docs: int = 5000) -> None:
        self._max_docs = max_docs
        self._docs: List[Dict[str, Any]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._fingerprint: Optional[str] = None
        self._lock = threading.Lock()

    def _corpus_fingerprint(self, docs: List[Dict[str, Any]]) -> str:
        h = hashlib.md5()
        for d in docs[:500]:
            h.update(f"{d.get('id')}|{d.get('updated') or ''}".encode())
        return h.hexdigest()

    def load_documents(self, sources: List[Dict[str, Any]], notes: List[Dict[str, Any]] = None) -> None:
        """Load docs (with text) and (re)build the index when data changed."""
        docs: List[Dict[str, Any]] = []
        for s in sources:
            text = s.get("full_text") or s.get("content") or ""
            if not text:
                continue
            docs.append(
                {
                    "id": s.get("id"),
                    "title": s.get("title") or "",
                    "content": text,
                    "parent_id": s.get("parent_id") or s.get("id"),
                    "result_type": "source",
                }
            )
        for n in notes or []:
            text = n.get("content") or ""
            if not text:
                continue
            docs.append(
                {
                    "id": n.get("id"),
                    "title": n.get("title") or "",
                    "content": text,
                    "parent_id": n.get("parent_id") or n.get("id"),
                    "result_type": "note",
                }
            )

        fp = self._corpus_fingerprint(docs)
        with self._lock:
            if fp == self._fingerprint and self._bm25 is not None:
                return
            self._docs = docs[: self._max_docs]
            if self._docs:
                tokenized = [tokenize(d["content"]) for d in self._docs]
                self._bm25 = BM25Okapi(tokenized)
            else:
                self._bm25 = None
            self._fingerprint = fp
            logger.debug(f"ChineseBM25Index rebuilt: {len(self._docs)} docs")

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Return BM25 results in text_search-like shape.

        rank_bm25 can return negative scores on tiny corpora; we normalize
        scores to [0,1] via min-max so hybrid fusion remains stable.
        """
        if not query or self._bm25 is None:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scores = self._bm25.get_scores(q_tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        # Min-max normalize (handle the all-negative tiny-corpus case)
        pos = [s for s in scores if s > 0]
        if pos:
            s_min, s_max = min(pos), max(pos)
            denom = (s_max - s_min) or 1.0
        else:
            s_min, s_max = min(scores), max(scores)
            denom = (s_max - s_min) or 1.0

        out = []
        for idx in ranked:
            score = scores[idx]
            if score <= 0 and pos:
                break
            norm = (score - s_min) / denom
            doc = self._docs[idx]
            # Extract a snippet around the best matching span
            snippet = _snippet(doc["content"], q_tokens)
            out.append(
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": snippet,
                    "parent_id": doc["parent_id"],
                    "result_type": doc["result_type"],
                    "relevance": round(float(norm), 6),
                }
            )
            if len(out) >= top_k:
                break
        return out


def _snippet(content: str, tokens: List[str], max_len: int = 300) -> str:
    """Extract a snippet around the first occurrence of any query token."""
    low = content.lower()
    for tok in tokens:
        if len(tok) >= 2:
            pos = low.find(tok)
            if pos >= 0:
                start = max(0, pos - 60)
                end = min(len(content), pos + 160)
                prefix = "…" if start > 0 else ""
                suffix = "…" if end < len(content) else ""
                return prefix + content[start:end].replace("\n", " ") + suffix
    return content[:max_len].replace("\n", " ") + ("…" if len(content) > max_len else "")


_instance: Optional[ChineseBM25Index] = None


def get_chinese_bm25() -> ChineseBM25Index:
    global _instance
    if _instance is None:
        _instance = ChineseBM25Index()
    return _instance


def reset_chinese_bm25() -> None:
    """Clear the cached index (e.g. after new sources uploaded)."""
    global _instance
    _instance = None
