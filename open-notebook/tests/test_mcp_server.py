# -*- coding: utf-8 -*-
"""Unit tests for MCP server tool registration."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestMCPToolsRegistered:
    @pytest.mark.asyncio
    async def test_tools_advertised(self):
        from api.mcp_server import mcp

        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        expected = {
            "list_notebooks",
            "hybrid_search",
            "ask_knowledge_base",
            "create_note",
            "list_sources",
            "graph_ask",
        }
        assert expected.issubset(names), f"missing: {expected - names}"

    @pytest.mark.asyncio
    async def test_tool_signatures(self):
        from api.mcp_server import mcp

        tools = {t.name: t for t in await mcp.list_tools()}
        # hybrid_search should declare query + limit + notebook_id params
        props = tools["hybrid_search"].parameters["properties"]
        assert "query" in props
        assert "limit" in props
        assert "notebook_id" in props
        assert "question" in tools["ask_knowledge_base"].parameters["properties"]
        assert "notebook_id" in tools["create_note"].parameters["properties"]
