# -*- coding: utf-8 -*-
"""Unit tests for the GraphRAG service."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_notebook.graphrag import (
    _extract_question_terms,
    format_graph_context,
    match_entities,
)


class TestExtractTerms:
    def test_chinese_terms(self):
        terms = _extract_question_terms("什么是MCP协议")
        assert any(t == "MCP" for t in terms)
        assert any(t == "协议" for t in terms)

    def test_english_terms(self):
        terms = _extract_question_terms("What is RAG and Agent?")
        assert any(t == "RAG" for t in terms)
        assert any(t == "Agent" for t in terms)


class TestFormatGraphContext:
    def test_with_paths(self):
        ctx = format_graph_context(
            [{"source": "Anthropic", "target": "MCP", "type": "proposed_by"}],
            [],
        )
        assert "Anthropic" in ctx
        assert "proposed_by" in ctx
        assert "MCP" in ctx

    def test_empty_paths_message(self):
        ctx = format_graph_context([], [])
        assert "暂无" in ctx

    def test_with_entities(self):
        class FakeEntity:
            name = "AI Agent"

        ctx = format_graph_context([], [FakeEntity()])
        assert "AI Agent" in ctx


class TestMatchEntities:
    @pytest.mark.asyncio
    async def test_match_by_question_containment(self):
        class FakeEntity:
            def __init__(self, name, eid):
                self.name = name
                self.id = eid

        entities = [FakeEntity("MCP协议", "e1"), FakeEntity("RAG", "e2")]
        with patch(
            "open_notebook.graphrag.GraphEntity.get_by_notebook",
            new=AsyncMock(return_value=entities),
        ):
            matched = await match_entities("nb1", "什么是MCP协议", max_entities=2)
        assert len(matched) == 1
        assert matched[0].name == "MCP协议"

    @pytest.mark.asyncio
    async def test_empty_notebook(self):
        with patch(
            "open_notebook.graphrag.GraphEntity.get_by_notebook",
            new=AsyncMock(return_value=[]),
        ):
            assert await match_entities(None, "anything") == []
