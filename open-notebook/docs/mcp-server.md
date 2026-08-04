# MCP Server 接入指南

本项目实现了 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务端，
将知识库的核心能力暴露为标准 MCP 工具，任何支持 MCP 的 AI 客户端
（Claude Desktop、Cursor、VS Code、各类 Agent 框架）都能直接操作知识库。

## 暴露的工具

| 工具 | 说明 |
|------|------|
| `list_notebooks` | 列出所有笔记本 |
| `hybrid_search` | 混合检索（BM25 全文 + 向量 + RRF 融合） |
| `ask_knowledge_base` | RAG 问答 |
| `create_note` | 在笔记本中创建笔记 |
| `list_sources` | 列出笔记本来源文档 |
| `graph_ask` | GraphRAG 图谱问答 |

## 启动方式

### 1. stdio 传输（默认，推荐用于本地客户端）

```bash
python -m api.mcp_server
```

### 2. SSE 传输（远程访问）

```bash
python -m api.mcp_server --sse --port 8765
```

## 接入 Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "notebook-evo": {
      "command": "python",
      "args": ["-m", "api.mcp_server"],
      "cwd": "E:/notebook/open-notebook"
    }
  }
}
```

## 接入 Cursor

Cursor Settings → MCP → Add new MCP server：

```json
{
  "mcpServers": {
    "notebook-evo": {
      "command": "python",
      "args": ["-m", "api.mcp_server"],
      "cwd": "E:/notebook/open-notebook"
    }
  }
}
```

## 自写测试客户端（无图形客户端时）

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "api.mcp_server"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("可用工具:", [t.name for t in tools.tools])
            result = await session.call_tool("hybrid_search", {"query": "AI Agent", "limit": 5})
            print(result.content[0].text)

asyncio.run(main())
```

## 用 MCP Inspector 调试

```bash
npx @modelcontextprotocol/inspector python -m api.mcp_server
```
