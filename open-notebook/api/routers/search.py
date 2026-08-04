import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from api.models import (
    AskRequest,
    AskResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResultItem,
    SearchRequest,
    SearchResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultItem,
)
from open_notebook.ai.models import Model, model_manager
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import Notebook, text_search, vector_search
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError
from open_notebook.graphs.ask import graph as ask_graph
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(search_request: SearchRequest):
    """Search the knowledge base using text or vector search."""
    log = get_logger("search_api", Operation.SEARCH, f"type={search_request.type} query={search_request.query[:50]}")
    log.debug("-> search_knowledge_base()")
    try:
        if search_request.type == "vector":
            # Check if embedding model is available for vector search
            if not await model_manager.get_embedding_model():
                raise HTTPException(
                    status_code=400,
                    detail="Vector search requires an embedding model. Please configure one in the Models section.",
                )

            results = await vector_search(
                keyword=search_request.query,
                results=search_request.limit,
                source=search_request.search_sources,
                note=search_request.search_notes,
                minimum_score=search_request.minimum_score,
            )
        else:
            # Text search
            results = await text_search(
                keyword=search_request.query,
                results=search_request.limit,
                source=search_request.search_sources,
                note=search_request.search_notes,
            )

        return SearchResponse(
            results=results or [],
            total_count=len(results) if results else 0,
            search_type=search_request.type,
        )

    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        logger.error(f"Database error during search: {str(e)}")
        get_logger("search_api", Operation.SEARCH, "-", Result.FAILURE).error(f"search_knowledge_base() db error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        get_logger("search_api", Operation.SEARCH, "-", Result.FAILURE).error(f"search_knowledge_base() failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


async def _filter_results_by_notebook(
    results: list, notebook_id: str
) -> list:
    """
    根据笔记本 ID 过滤搜索结果。

    通过查询笔记本关联的 source 和 note ID 集合，保留 parent_id 属于该笔记本的结果。
    过滤失败时回退为返回原始结果，避免因关联查询异常导致搜索不可用。
    """
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            return results

        # 收集笔记本关联的 source / note 记录 ID
        sources = await notebook.get_sources()
        notes = await notebook.get_notes()
        allowed_ids = set()
        for src in sources:
            if getattr(src, "id", None):
                allowed_ids.add(str(src.id))
        for note in notes:
            if getattr(note, "id", None):
                allowed_ids.add(str(note.id))

        # 仅保留 parent_id 指向笔记本内成员的结果
        filtered = []
        for item in results:
            parent_id = item.get("parent_id") if isinstance(item, dict) else None
            if parent_id and parent_id in allowed_ids:
                filtered.append(item)
        return filtered
    except Exception as e:
        logger.warning(f"Notebook filter failed, returning unfiltered results: {e}")
        return results


def _build_semantic_result(item: dict) -> SemanticSearchResultItem:
    """将原始向量搜索结果项转换为语义搜索结果项，提取相关性分数。"""
    parent_id = str(item.get("parent_id", "")) if item.get("parent_id") else ""
    result_type = None
    if parent_id and ":" in parent_id:
        result_type = parent_id.split(":", 1)[0]

    # 相关性分数：优先使用 final_score / score / similarity / relevance
    score = (
        item.get("final_score")
        or item.get("score")
        or item.get("similarity")
        or item.get("relevance")
        or 0.0
    )
    try:
        relevance = float(score)
    except (TypeError, ValueError):
        relevance = 0.0

    # 内容预览：从 matches 或 content 中提取
    preview = None
    matches = item.get("matches")
    if isinstance(matches, list) and matches:
        preview = str(matches[0])
    elif item.get("content"):
        preview = str(item["content"])

    return SemanticSearchResultItem(
        id=str(item.get("id", "")),
        title=str(item.get("title", "") or ""),
        parent_id=parent_id,
        relevance_score=relevance,
        content_preview=preview,
        result_type=result_type,
    )


@router.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索端点。

    使用嵌入模型将查询文本转为向量，执行向量相似度搜索，返回带相关性分数的结果。
    可通过 notebook_id 限定搜索范围到指定笔记本内的 source / note。
    """
    log = get_logger(
        "search_api",
        Operation.SEARCH,
        f"semantic query={request.query[:50]} notebook={request.notebook_id or '-'}",
    )
    log.debug("-> semantic_search()")
    try:
        # 校验嵌入模型可用
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="Semantic search requires an embedding model. Please configure one in the Models section.",
            )

        # 使用统一嵌入服务将查询转为向量并执行向量搜索
        raw_results = await vector_search(
            keyword=request.query,
            results=request.limit,
            source=True,
            note=True,
            minimum_score=request.minimum_score,
        )

        results = raw_results or []

        # 按笔记本过滤
        if request.notebook_id:
            results = await _filter_results_by_notebook(results, request.notebook_id)

        # 转换为语义搜索结果项并按相关性分数降序排序
        items = [_build_semantic_result(item) for item in results if isinstance(item, dict)]
        items.sort(key=lambda x: x.relevance_score, reverse=True)

        log.bind(result=Result.SUCCESS).info(
            f"<- semantic_search() ok count={len(items)}"
        )

        return SemanticSearchResponse(
            results=items,
            total_count=len(items),
            query=request.query,
            notebook_id=request.notebook_id,
        )

    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        logger.error(f"Database error during semantic search: {str(e)}")
        get_logger("search_api", Operation.SEARCH, "-", Result.FAILURE).error(
            f"semantic_search() db error: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during semantic search: {str(e)}")
        get_logger("search_api", Operation.SEARCH, "-", Result.FAILURE).error(
            f"semantic_search() failed: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


async def stream_ask_response(
    question: str, strategy_model: Model, answer_model: Model, final_answer_model: Model
) -> AsyncGenerator[str, None]:
    """Stream the ask response as Server-Sent Events."""
    try:
        final_answer = None

        async for chunk in ask_graph.astream(
            input=dict(question=question),  # type: ignore[arg-type]
            config=dict(
                configurable=dict(
                    strategy_model=strategy_model.id,
                    answer_model=answer_model.id,
                    final_answer_model=final_answer_model.id,
                )
            ),
            stream_mode="updates",
        ):
            if "agent" in chunk:
                strategy_data = {
                    "type": "strategy",
                    "reasoning": chunk["agent"]["strategy"].reasoning,
                    "searches": [
                        {"term": search.term, "instructions": search.instructions}
                        for search in chunk["agent"]["strategy"].searches
                    ],
                }
                yield f"data: {json.dumps(strategy_data)}\n\n"

            elif "provide_answer" in chunk:
                for answer in chunk["provide_answer"]["answers"]:
                    answer_data = {"type": "answer", "content": answer}
                    yield f"data: {json.dumps(answer_data)}\n\n"

            elif "write_final_answer" in chunk:
                final_answer = chunk["write_final_answer"]["final_answer"]
                final_data = {"type": "final_answer", "content": final_answer}
                yield f"data: {json.dumps(final_data)}\n\n"

        # Send completion signal
        completion_data = {"type": "complete", "final_answer": final_answer}
        yield f"data: {json.dumps(completion_data)}\n\n"

    except Exception as e:
        from open_notebook.utils.error_classifier import classify_error

        _, user_message = classify_error(e)
        logger.error(f"Error in ask streaming: {str(e)}")
        error_data = {"type": "error", "message": user_message}
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/search/hybrid", response_model=HybridSearchResponse)
async def hybrid_search_endpoint(request: HybridSearchRequest):
    """Hybrid search: BM25 + vector with RRF fusion and optional rerank."""
    from open_notebook.search.hybrid import hybrid_search_with_details

    log = get_logger("search_api", Operation.SEARCH, f"hybrid query={request.query[:50]}")
    log.debug("-> hybrid_search_endpoint()")
    try:
        details = await hybrid_search_with_details(
            query=request.query,
            limit=request.limit,
            search_sources=request.search_sources,
            search_notes=request.search_notes,
            minimum_score=request.minimum_score,
            rerank=request.rerank,
        )
        items = [
            HybridSearchResultItem(
                id=r["id"],
                title=r["title"],
                content_preview=r["content_preview"],
                parent_id=r["parent_id"],
                result_type=r["result_type"],
                rrf_score=r["rrf_score"],
                vector_score=r["vector_score"],
                text_score=r["text_score"],
                rerank_score=r["rerank_score"],
                sources=r["sources"],
            )
            for r in details["results"]
        ]
        log.bind(result=Result.SUCCESS).info(f"<- hybrid_search_endpoint() ok count={len(items)}")
        return HybridSearchResponse(
            query=request.query,
            results=items,
            total_count=len(items),
            vector_hits=details["vector_hits"],
            text_hits=details["text_hits"],
            rerank_used=details["rerank_used"],
        )
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        get_logger("search_api", Operation.SEARCH, "-", Result.FAILURE).error(f"hybrid_search_endpoint() failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@router.post("/search/ask")
async def ask_knowledge_base(ask_request: AskRequest):
    """Ask the knowledge base a question using AI models."""
    log = get_logger("search_api", Operation.CHAT, f"question={ask_request.question[:50]}")
    log.debug("-> ask_knowledge_base()")
    try:
        # Validate models exist
        strategy_model = await Model.get(ask_request.strategy_model)
        answer_model = await Model.get(ask_request.answer_model)
        final_answer_model = await Model.get(ask_request.final_answer_model)

        if not strategy_model:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy model {ask_request.strategy_model} not found",
            )
        if not answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Answer model {ask_request.answer_model} not found",
            )
        if not final_answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Final answer model {ask_request.final_answer_model} not found",
            )

        # Check if embedding model is available
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="Ask feature requires an embedding model. Please configure one in the Models section.",
            )

        # For streaming response
        return StreamingResponse(
            stream_ask_response(
                ask_request.question, strategy_model, answer_model, final_answer_model
            ),
            media_type="text/plain",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ask endpoint: {str(e)}")
        get_logger("search_api", Operation.CHAT, "-", Result.FAILURE).error(f"ask_knowledge_base() failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ask operation failed: {str(e)}")


@router.post("/search/ask/simple", response_model=AskResponse)
async def ask_knowledge_base_simple(ask_request: AskRequest):
    """Ask the knowledge base a question and return a simple response (non-streaming)."""
    log = get_logger("search_api", Operation.CHAT, f"question={ask_request.question[:50]}")
    log.debug("-> ask_knowledge_base_simple()")
    try:
        # Validate models exist
        strategy_model = await Model.get(ask_request.strategy_model)
        answer_model = await Model.get(ask_request.answer_model)
        final_answer_model = await Model.get(ask_request.final_answer_model)

        if not strategy_model:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy model {ask_request.strategy_model} not found",
            )
        if not answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Answer model {ask_request.answer_model} not found",
            )
        if not final_answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Final answer model {ask_request.final_answer_model} not found",
            )

        # Check if embedding model is available
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="Ask feature requires an embedding model. Please configure one in the Models section.",
            )

        # Run the ask graph and get final result
        final_answer = None
        async for chunk in ask_graph.astream(
            input=dict(question=ask_request.question),  # type: ignore[arg-type]
            config=dict(
                configurable=dict(
                    strategy_model=strategy_model.id,
                    answer_model=answer_model.id,
                    final_answer_model=final_answer_model.id,
                )
            ),
            stream_mode="updates",
        ):
            if "write_final_answer" in chunk:
                final_answer = chunk["write_final_answer"]["final_answer"]

        if not final_answer:
            raise HTTPException(status_code=500, detail="No answer generated")

        return AskResponse(answer=final_answer, question=ask_request.question)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ask simple endpoint: {str(e)}")
        get_logger("search_api", Operation.CHAT, "-", Result.FAILURE).error(f"ask_knowledge_base_simple() failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ask operation failed: {str(e)}")
