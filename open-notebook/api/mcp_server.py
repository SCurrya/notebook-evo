# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) Server for the AI Knowledge Workbench.

Exposes platform capabilities as MCP tools so any AI client (Claude Desktop,
Cursor, VS Code, or any MCP-enabled agent) can operate the knowledge base.

Tools exposed:
  - list_notebooks       : list all notebooks
  - hybrid_search        : hybrid retrieval (BM25 + vector + RRF)
  - ask_knowledge_base   : RAG question answering
  - create_note          : create a note in a notebook
  - list_sources         : list sources in a notebook
  - graph_ask            : GraphRAG question answering

Transport:
  - stdio (default): `python -m api.mcp_server`
  - SSE:            `python -m api.mcp_server --sse --port 8765`
"""
from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any, Dict, List, Optional

from loguru import logger

from fastmcp import FastMCP

# Global MCP server (stdio)
mcp = FastMCP("notebook-evo")

# ---------------------------------------------------------------- helpers


def _notebook_id(nb: Any) -> str:
    return nb.id if hasattr(nb, "id") else str(getattr(nb, "id", ""))


def _notebook_name(nb: Any) -> str:
    return getattr(nb, "name", "") or ""


async def _get_default_chat_model():
    from open_notebook.ai.models import DefaultModels, model_manager

    defaults = await DefaultModels.get_instance()
    model_id = defaults.default_chat_model
    if not model_id:
        return None
    return await model_manager.get_model(model_id)


# ---------------------------------------------------------------- tools


@mcp.tool()
async def list_notebooks() -> List[Dict[str, str]]:
    """列出知识库中的所有笔记本。"""
    from open_notebook.domain.notebook import Notebook

    notebooks = await Notebook.list()
    return [
        {"id": _notebook_id(nb), "name": _notebook_name(nb)} for nb in notebooks
    ]


@mcp.tool()
async def hybrid_search(
    query: str, limit: int = 5, notebook_id: Optional[str] = None
) -> Dict[str, Any]:
    """混合检索（BM25 全文 + 向量 + RRF 融合）。

    Args:
        query: 检索关键词
        limit: 返回结果数量上限
        notebook_id: 可选，限定在某个笔记本内检索
    """
    from open_notebook.search.hybrid import hybrid_search as do_search

    results = await do_search(
        query,
        limit=limit,
        search_sources=True,
        search_notes=True,
        rerank=False,
    )
    items = [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content[:500],
            "score": r.score,
        }
        for r in results
    ]
    return {"query": query, "results": items, "total": len(items)}


@mcp.tool()
async def ask_knowledge_base(
    question: str, notebook_id: Optional[str] = None
) -> Dict[str, Any]:
    """对知识库进行 RAG 问答。

    Args:
        question: 用户问题
        notebook_id: 可选，限定笔记本
    """
    from langchain_core.prompts import ChatPromptTemplate
    from open_notebook.search.hybrid import hybrid_search

    results = await hybrid_search(
        question, limit=5, search_sources=True, search_notes=True, rerank=False
    )
    context = "\n\n".join(f"[{r.title}] {r.content[:500]}" for r in results)
    if not context:
        return {
            "answer": "知识库中没有检索到与问题相关的内容。",
            "retrieved_count": 0,
        }

    model = await _get_default_chat_model()
    if not model:
        return {
            "answer": "未配置默认聊天模型，无法生成回答。检索到以下上下文：\n\n" + context,
            "retrieved_count": len(results),
        }

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个严谨的知识库问答助手。请仅基于提供的参考资料回答，不要编造信息。",
            ),
            ("user", "参考资料：\n{context}\n\n用户问题：{question}"),
        ]
    )
    chain = prompt | model
    response = await chain.ainvoke({"context": context, "question": question})
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(str(c.get("text", "")) if isinstance(c, dict) else str(c) for c in content)
    return {
        "answer": str(content),
        "retrieved_count": len(results),
        "sources": [{"id": r.id, "title": r.title} for r in results],
    }


@mcp.tool()
async def create_note(notebook_id: str, title: str, content: str) -> Dict[str, str]:
    """在指定笔记本中创建一条笔记。

    Args:
        notebook_id: 笔记本 ID
        title: 笔记标题
        content: 笔记内容
    """
    from open_notebook.domain.notebook import Notebook, Note

    notebook = await Notebook.get(notebook_id)
    if not notebook:
        return {"status": "error", "message": f"笔记本不存在: {notebook_id}"}
    note = Note(title=title, content=content)
    await note.save()
    notebook.add_note(note)
    return {"status": "ok", "note_id": str(note.id), "title": title}


@mcp.tool()
async def list_sources(notebook_id: str) -> Dict[str, Any]:
    """列出笔记本中的所有来源（上传的文档）。

    Args:
        notebook_id: 笔记本 ID
    """
    from open_notebook.domain.notebook import Notebook

    notebook = await Notebook.get(notebook_id)
    if not notebook:
        return {"error": f"笔记本不存在: {notebook_id}"}
    sources = []
    for s in notebook.sources:
        sources.append(
            {
                "id": str(getattr(s, "id", "")),
                "title": getattr(s, "title", "") or getattr(s, "name", ""),
                "type": getattr(s, "content_type", "") or getattr(s, "type", ""),
            }
        )
    return {"notebook_id": notebook_id, "sources": sources}


@mcp.tool()
async def graph_ask(notebook_id: str, question: str) -> Dict[str, Any]:
    """结合知识图谱进行问答（GraphRAG）。

    Args:
        notebook_id: 笔记本 ID
        question: 用户问题
    """
    from open_notebook.graphrag import graph_rag_ask

    return await graph_rag_ask(notebook_id, question, top_k=5)


# ---------------------------------------------------------------- main


def run_stdio() -> None:
    """Run the MCP server over stdio transport."""
    logger.info("Starting MCP server (stdio transport)")
    mcp.run(transport="stdio")


def run_sse(host: str, port: int) -> None:
    """Run the MCP server over SSE transport."""
    logger.info(f"Starting MCP server (SSE transport) on {host}:{port}")
    mcp.run(transport="sse", host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Notebook-Evo MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--host", default="127.0.0.1", help="SSE bind host")
    parser.add_argument("--port", type=int, default=8765, help="SSE bind port")
    args = parser.parse_args()

    if args.sse:
        run_sse(args.host, args.port)
    else:
        run_stdio()


if __name__ == "__main__":
    main()
