# -*- coding: utf-8 -*-
"""
GraphRAG 问答服务。

结合知识图谱（实体/关系）与向量检索，对问题做多跳推理回答：
1. 实体匹配：从问题中提取关键词，匹配图谱实体
2. 图谱展开：BFS 获取匹配实体的一跳/两跳邻居（实体 + 关系）
3. 上下文融合：图谱路径 + 向量检索结果共同组成上下文
4. LLM 综合：基于图谱上下文 + 向量上下文生成回答
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.knowledge_graph import GraphEntity, GraphRelation


def _entity_name_from_record(rec: Dict[str, Any]) -> Optional[str]:
    """从 SurrealDB 查询结果中提取实体名称（兼容嵌套 RecordID）。"""
    name = rec.get("name")
    if name:
        return str(name)
    # 可能是嵌套的对象（如 source.name）
    for k in ("source", "target"):
        v = rec.get(k)
        if isinstance(v, dict) and v.get("name"):
            return str(v["name"])
    return None


def _extract_question_terms(question: str) -> List[str]:
    """从问题中提取候选实体关键词。

    简单实现：中文按 2-6 字滑窗 + 英文按单词。图谱实体名做模糊匹配。
    """
    terms: List[str] = []
    # 中文词组滑窗
    cn_chars = [c for c in question if "\u4e00" <= c <= "\u9fff"]
    if len(cn_chars) >= 2:
        for start in range(0, len(cn_chars)):
            for length in (2, 3, 4):
                if start + length <= len(cn_chars):
                    terms.append("".join(cn_chars[start : start + length]))
    # 英文单词
    import re

    terms.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", question))
    # 去重保持顺序
    seen: Set[str] = set()
    out: List[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


async def match_entities(
    notebook_id: Optional[str], question: str, max_entities: int = 5
) -> List[GraphEntity]:
    """匹配问题关键词到图谱实体（名称包含匹配）。"""
    entities = await GraphEntity.get_by_notebook(notebook_id) if notebook_id else []
    if not entities:
        return []
    terms = _extract_question_terms(question)
    q_lower = question.lower()
    matched: List[GraphEntity] = []
    for ent in entities:
        name = ent.name.lower()
        # 精确包含：问题包含实体名，或实体名包含某个术语
        if name and (name in q_lower or any(t in name for t in terms)):
            matched.append(ent)
    # 去重，限制数量
    seen_ids: Set[str] = set()
    out: List[GraphEntity] = []
    for e in matched:
        if e.id and e.id not in seen_ids:
            seen_ids.add(e.id)
            out.append(e)
    return out[:max_entities]


async def get_entity_neighbors(
    entity_ids: List[str], depth: int = 2
) -> Tuple[Set[str], List[Dict[str, str]]]:
    """BFS 获取实体邻居，返回 (实体ID集合, 路径描述列表)。"""
    visited: Set[str] = set(entity_ids)
    frontier: List[str] = list(entity_ids)
    paths: List[Dict[str, str]] = []

    for _ in range(depth):
        if not frontier:
            break
        next_frontier: List[str] = []
        for eid in frontier:
            # 查询以 eid 为 source 或 target 的关系
            results = await repo_query(
                """
                SELECT source.id AS sid, source.name AS sname,
                       target.id AS tid, target.name AS tname,
                       type
                FROM graph_relation
                WHERE source.id = $eid OR target.id = $eid
                """,
                {"eid": ensure_record_id(eid)},
            )
            for row in results:
                sid = str(row.get("sid") or "").split(":")[-1] if row.get("sid") else None
                tid = str(row.get("tid") or "").split(":")[-1] if row.get("tid") else None
                rel_type = row.get("type")
                sname = _entity_name_from_record(row) or (row.get("sname") or "?")
                tname = row.get("tname") or "?"
                if not sid or not tid or not rel_type:
                    continue
                paths.append({"source": sname, "target": tname, "type": str(rel_type)})
                for nid in (sid, tid):
                    if nid and nid not in visited:
                        visited.add(nid)
                        next_frontier.append(nid)
        frontier = next_frontier
    return visited, paths


def format_graph_context(paths: List[Dict[str, str]], entities: List[GraphEntity]) -> str:
    """把图谱路径格式化为 LLM 上下文文本。"""
    lines: List[str] = []
    if entities:
        names = "、".join(e.name for e in entities)
        lines.append(f"图谱中匹配到的核心实体：{names}")
    for p in paths[:40]:
        lines.append(f"- {p['source']} --[{p['type']}]--> {p['target']}")
    if not paths:
        lines.append("（图谱中暂无与问题相关的实体关系）")
    return "\n".join(lines)


async def graph_rag_ask(
    notebook_id: str,
    question: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    """GraphRAG 问答主入口。

    流程：实体匹配 → 图谱展开 → 向量检索 → 上下文融合 → LLM 回答。
    """
    from open_notebook.ai.models import DefaultModels, model_manager
    from open_notebook.domain.notebook import Notebook
    from open_notebook.search.hybrid import hybrid_search

    # 1. 实体匹配
    entities = await match_entities(notebook_id, question)
    entity_ids = [e.id for e in entities if e.id]

    # 2. 图谱展开
    graph_paths: List[Dict[str, str]] = []
    if entity_ids:
        _, graph_paths = await get_entity_neighbors(entity_ids, depth=2)

    # 3. 向量检索
    retrieved: List[Dict[str, Any]] = []
    try:
        hybrid = await hybrid_search(
            question,
            limit=top_k,
            search_sources=True,
            search_notes=True,
            rerank=False,
        )
        retrieved = [
            {
                "id": r.id,
                "title": r.title,
                "content": r.content[:600],
                "score": r.score,
            }
            for r in hybrid
        ]
    except Exception as e:
        logger.warning(f"GraphRAG vector retrieval failed: {e}")

    # 4. 上下文融合
    graph_context = format_graph_context(graph_paths, entities)
    vector_context = "\n\n".join(
        f"[{r['title']}] {r['content']}" for r in retrieved[:top_k]
    )
    combined_context = (
        f"【知识图谱上下文】\n{graph_context}\n\n"
        f"【检索文档上下文】\n{vector_context or '（无检索结果）'}"
    )

    # 5. LLM 回答
    system_prompt = (
        "你是一个结合知识图谱与检索增强的知识问答助手。请综合【知识图谱上下文】"
        "中的实体关系信息和【检索文档上下文】中的文档内容来回答用户问题。\n"
        "回答要求：\n"
        "1. 优先利用图谱中的实体关系进行推理，说明实体之间的关系\n"
        "2. 结合检索到的文档细节，给出有依据的回答\n"
        "3. 如果图谱和文档都无法回答，请明确说明\n"
        "4. 使用简洁准确的中文回答"
    )
    answer = ""
    model_source = "graph"
    try:
        defaults = await DefaultModels.get_instance()
        model_id = defaults.default_chat_model
        if model_id:
            model = await model_manager.get_model(model_id)
            if model:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"用户问题：{question}\n\n{combined_context}",
                    },
                ]
                response = await model.achat_complete(messages)
                answer = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"GraphRAG LLM generation failed: {e}")
        answer = "（模型回答生成失败）"

    return {
        "question": question,
        "answer": answer,
        "entities": [
            {"id": e.id or "", "name": e.name, "type": e.type} for e in entities
        ],
        "graph_paths": graph_paths,
        "retrieved": retrieved,
        "context": combined_context,
        "model_source": model_source,
    }
