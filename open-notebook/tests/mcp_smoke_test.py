# -*- coding: utf-8 -*-
"""
MCP Server smoke test.

Spawns the MCP server as a subprocess (stdio transport) and verifies the
tools are advertised and callable through the official mcp client library.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "api.mcp_server"],
        cwd=str(Path(__file__).resolve().parent.parent),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. List tools
            tools = await session.list_tools()
            tool_names = sorted(t.name for t in tools.tools)
            print(f"[PASS] tools advertised: {tool_names}")
            expected = {
                "list_notebooks",
                "hybrid_search",
                "ask_knowledge_base",
                "create_note",
                "list_sources",
                "graph_ask",
            }
            assert expected.issubset(set(tool_names)), f"missing tools: {expected - set(tool_names)}"

            # 2. Call list_notebooks (safe, no DB required to return list)
            result = await session.call_tool("list_notebooks", {})
            print(f"[INFO] list_notebooks -> {result.content[0].text[:120] if result.content else 'empty'}")
            assert not result.isError

            # 3. Call hybrid_search with empty db (should return empty results, not error)
            result = await session.call_tool(
                "hybrid_search", {"query": "AI Agent", "limit": 3}
            )
            print(f"[INFO] hybrid_search -> {result.content[0].text[:150] if result.content else 'empty'}")
            assert not result.isError

            # 4. list_sources with bogus id should return error object but not tool error
            result = await session.call_tool(
                "list_sources", {"notebook_id": "nonexistent-xyz"}
            )
            print(f"[INFO] list_sources(bogus) -> {result.content[0].text[:150] if result.content else 'empty'}")
            assert not result.isError

            # 5. create_note with bogus id -> graceful error message
            result = await session.call_tool(
                "create_note",
                {
                    "notebook_id": "nonexistent-xyz",
                    "title": "test",
                    "content": "content",
                },
            )
            print(f"[INFO] create_note(bogus) -> {result.content[0].text[:150] if result.content else 'empty'}")
            assert not result.isError

            print("[PASS] MCP smoke test completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
