"""
知识图谱路由器。

提供以下端点：
- POST /api/knowledge-graph/extract        从笔记本内容提取实体和关系（调用 LLM）
- GET  /api/knowledge-graph/{notebook_id}  获取笔记本的知识图谱
- POST /api/knowledge-graph/entity          手动添加实体
- POST /api/knowledge-graph/relation        手动添加关系
- DELETE /api/knowledge-graph/entity/{id}   删除实体
- DELETE /api/knowledge-graph/relation/{id} 删除关系
"""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import (
    GraphEntityCreate,
    GraphEntityResponse,
    GraphExtractRequest,
    GraphExtractResponse,
    GraphRelationCreate,
    GraphRelationResponse,
)
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.knowledge_graph import GraphEntity, GraphRelation
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


# 提取实体和关系的 LLM 提示词
_EXTRACTION_SYSTEM_PROMPT = """你是一个知识图谱提取助手。从给定的笔记本内容中提取实体和关系。

输出严格的 JSON 格式，结构如下：
{
  "entities": [
    {"name": "实体名称", "type": "person|organization|concept|location|event|other", "properties": {}}
  ],
  "relations": [
    {"source": "源实体名称", "target": "目标实体名称", "type": "关系类型", "properties": {}}
  ]
}

要求：
1. 只输出 JSON，不要任何额外文字或解释
2. 实体名称应规范化、去重
3. 关系中的 source/target 必须对应已提取的实体名称
4. 关系类型使用 snake_case（如 works_for, located_in, created_by）
5. 最多提取 30 个实体和 50 个关系
"""


def _parse_llm_json(content: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON 内容，容错处理。"""
    text = content.strip()
    # 去除可能的 markdown 代码块包裹
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首尾的 ``` 行
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidInputError(f"LLM 返回的内容不是有效的 JSON: {e}")


async def _extract_with_llm(content: str) -> Dict[str, Any]:
    """调用 LLM 提取实体和关系。

    使用项目现有的模型管理系统，优先使用默认的 transformation 模型。
    """
    from open_notebook.ai.models import DefaultModels, model_manager

    defaults = await DefaultModels.get_instance()
    model_id = (
        defaults.default_transformation_model
        or defaults.default_chat_model
    )
    if not model_id:
        raise InvalidInputError(
            "未配置默认的 transformation 或 chat 模型，无法执行知识图谱提取"
        )
    model = await model_manager.get_model(model_id)
    if model is None:
        raise InvalidInputError(f"找不到模型 {model_id}")

    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"请从以下笔记本内容中提取知识图谱：\n\n{content}"},
    ]
    response = await model.achat_complete(messages)
    text = response.choices[0].message.content or ""
    return _parse_llm_json(text)


@router.post("/ask")
async def graph_ask(request: dict):
    """GraphRAG 问答：结合知识图谱实体关系 + 向量检索回答。

    请求体: {"question": str, "notebook_id": str, "top_k": int}
    """
    from open_notebook.graphrag import graph_rag_ask

    question = (request.get("question") or "").strip()
    notebook_id = request.get("notebook_id") or ""
    top_k = int(request.get("top_k") or 5)
    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")
    if not notebook_id:
        raise HTTPException(status_code=400, detail="notebook_id 不能为空")
    log = get_logger(
        "knowledge_graph_api",
        Operation.READ,
        f"graph_ask notebook_id={notebook_id} q={question[:40]}",
    )
    log.debug("-> graph_ask()")
    try:
        result = await graph_rag_ask(notebook_id, question, top_k)
        log.bind(result=Result.SUCCESS).info(
            f"<- graph_ask() entities={len(result['entities'])} "
            f"paths={len(result['graph_paths'])} retrieved={len(result['retrieved'])}"
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GraphRAG 问答失败: {e}")
        raise HTTPException(status_code=500, detail=f"GraphRAG 问答失败: {str(e)}")


@router.post("/extract", response_model=GraphExtractResponse)
async def extract_graph(request: GraphExtractRequest):
    """从笔记本内容提取实体和关系（调用 LLM）。"""
    log = get_logger(
        "knowledge_graph_api",
        Operation.CREATE,
        f"notebook_id={request.notebook_id}",
    )
    log.debug("-> extract_graph()")
    try:
        # 获取笔记本上下文
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="笔记本不存在")

        # 构建笔记本内容
        content = await notebook.get_context()
        if not content or len(content.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="笔记本内容为空，无法提取知识图谱",
            )

        # 调用 LLM 提取
        extracted = await _extract_with_llm(content)

        # 持久化实体（按名称去重）
        existing_entities = await GraphEntity.get_by_notebook(request.notebook_id)
        name_to_entity: Dict[str, GraphEntity] = {
            e.name.lower(): e for e in existing_entities
        }

        created_entities: List[GraphEntity] = []
        for ent in extracted.get("entities", []):
            name = (ent.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in name_to_entity:
                created_entities.append(name_to_entity[key])
                continue
            entity = GraphEntity(
                name=name,
                type=(ent.get("type") or "other").strip() or "other",
                properties=ent.get("properties") or {},
                notebook_id=request.notebook_id,
            )
            await entity.save()
            name_to_entity[key] = entity
            created_entities.append(entity)

        # 持久化关系
        created_relations: List[GraphRelation] = []
        for rel in extracted.get("relations", []):
            src_name = (rel.get("source") or "").strip()
            tgt_name = (rel.get("target") or "").strip()
            rel_type = (rel.get("type") or "").strip()
            if not src_name or not tgt_name or not rel_type:
                continue
            src = name_to_entity.get(src_name.lower())
            tgt = name_to_entity.get(tgt_name.lower())
            if not src or not tgt or not src.id or not tgt.id:
                continue
            relation = GraphRelation(
                source_id=src.id,
                target_id=tgt.id,
                type=rel_type,
                properties=rel.get("properties") or {},
            )
            await relation.save()
            created_relations.append(relation)

        log.bind(result=Result.SUCCESS).info(
            f"<- extract_graph() entities={len(created_entities)} relations={len(created_relations)}"
        )
        return GraphExtractResponse(
            entities=[
                GraphEntityResponse(
                    id=e.id or "",
                    name=e.name,
                    type=e.type,
                    properties=e.properties,
                    notebook_id=e.notebook_id,
                )
                for e in created_entities
            ],
            relations=[
                GraphRelationResponse(
                    id=r.id or "",
                    source_id=r.source_id,
                    target_id=r.target_id,
                    type=r.type,
                    properties=r.properties,
                )
                for r in created_relations
            ],
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提取知识图谱失败: {e}")
        get_logger(
            "knowledge_graph_api",
            Operation.CREATE,
            f"notebook_id={request.notebook_id}",
            Result.FAILURE,
        ).error(f"extract_graph() failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"提取知识图谱失败: {str(e)}"
        )


@router.get("/{notebook_id}", response_model=GraphExtractResponse)
async def get_graph(notebook_id: str):
    """获取笔记本的知识图谱。"""
    log = get_logger(
        "knowledge_graph_api", Operation.READ, f"notebook_id={notebook_id}"
    )
    log.debug("-> get_graph()")
    try:
        entities = await GraphEntity.get_by_notebook(notebook_id)
        relations = await GraphRelation.get_by_notebook(notebook_id)
        log.bind(result=Result.SUCCESS).info(
            f"<- get_graph() entities={len(entities)} relations={len(relations)}"
        )
        return GraphExtractResponse(
            entities=[
                GraphEntityResponse(
                    id=e.id or "",
                    name=e.name,
                    type=e.type,
                    properties=e.properties,
                    notebook_id=e.notebook_id,
                )
                for e in entities
            ],
            relations=[
                GraphRelationResponse(
                    id=r.id or "",
                    source_id=r.source_id,
                    target_id=r.target_id,
                    type=r.type,
                    properties=r.properties,
                )
                for r in relations
            ],
        )
    except Exception as e:
        logger.error(f"获取知识图谱失败: {e}")
        get_logger(
            "knowledge_graph_api",
            Operation.READ,
            f"notebook_id={notebook_id}",
            Result.FAILURE,
        ).error(f"get_graph() failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取知识图谱失败: {str(e)}"
        )


@router.post("/entity", response_model=GraphEntityResponse)
async def create_entity(data: GraphEntityCreate):
    """手动添加实体。"""
    log = get_logger(
        "knowledge_graph_api", Operation.CREATE, f"name={data.name}"
    )
    log.debug("-> create_entity()")
    try:
        entity = GraphEntity(
            name=data.name,
            type=data.type,
            properties=data.properties or {},
            notebook_id=data.notebook_id,
        )
        await entity.save()
        log.bind(result=Result.SUCCESS).info(f"<- create_entity() id={entity.id}")
        return GraphEntityResponse(
            id=entity.id or "",
            name=entity.name,
            type=entity.type,
            properties=entity.properties,
            notebook_id=entity.notebook_id,
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建实体失败: {e}")
        get_logger(
            "knowledge_graph_api",
            Operation.CREATE,
            f"name={data.name}",
            Result.FAILURE,
        ).error(f"create_entity() failed: {e}")
        raise HTTPException(status_code=500, detail=f"创建实体失败: {str(e)}")


@router.post("/relation", response_model=GraphRelationResponse)
async def create_relation(data: GraphRelationCreate):
    """手动添加关系。"""
    log = get_logger(
        "knowledge_graph_api",
        Operation.CREATE,
        f"source={data.source_id} target={data.target_id} type={data.type}",
    )
    log.debug("-> create_relation()")
    try:
        # 校验源/目标实体存在
        if not data.source_id or not data.target_id:
            raise HTTPException(status_code=400, detail="source_id 和 target_id 不能为空")
        try:
            await GraphEntity.get(data.source_id)
            await GraphEntity.get(data.target_id)
        except Exception:
            raise HTTPException(status_code=404, detail="源实体或目标实体不存在")

        relation = GraphRelation(
            source_id=data.source_id,
            target_id=data.target_id,
            type=data.type,
            properties=data.properties or {},
        )
        await relation.save()
        log.bind(result=Result.SUCCESS).info(f"<- create_relation() id={relation.id}")
        return GraphRelationResponse(
            id=relation.id or "",
            source_id=relation.source_id,
            target_id=relation.target_id,
            type=relation.type,
            properties=relation.properties,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建关系失败: {e}")
        get_logger(
            "knowledge_graph_api",
            Operation.CREATE,
            f"type={data.type}",
            Result.FAILURE,
        ).error(f"create_relation() failed: {e}")
        raise HTTPException(status_code=500, detail=f"创建关系失败: {str(e)}")


@router.delete("/entity/{entity_id}")
async def delete_entity(entity_id: str):
    """删除实体（同时删除相关关系）。"""
    log = get_logger(
        "knowledge_graph_api", Operation.DELETE, f"entity_id={entity_id}"
    )
    log.debug("-> delete_entity()")
    try:
        entity = await GraphEntity.get(entity_id)
        await entity.delete()
        # 删除关联的关系
        await repo_query(
            "DELETE FROM graph_relation WHERE source_id = $id OR target_id = $id",
            {"id": ensure_record_id(entity_id)},
        )
        log.bind(result=Result.SUCCESS).info("<- delete_entity() ok")
        return {"message": "实体删除成功"}
    except Exception as e:
        logger.error(f"删除实体失败: {e}")
        get_logger(
            "knowledge_graph_api",
            Operation.DELETE,
            f"entity_id={entity_id}",
            Result.FAILURE,
        ).error(f"delete_entity() failed: {e}")
        raise HTTPException(status_code=500, detail=f"删除实体失败: {str(e)}")


@router.delete("/relation/{relation_id}")
async def delete_relation(relation_id: str):
    """删除关系。"""
    log = get_logger(
        "knowledge_graph_api", Operation.DELETE, f"relation_id={relation_id}"
    )
    log.debug("-> delete_relation()")
    try:
        relation = await GraphRelation.get(relation_id)
        await relation.delete()
        log.bind(result=Result.SUCCESS).info("<- delete_relation() ok")
        return {"message": "关系删除成功"}
    except Exception as e:
        logger.error(f"删除关系失败: {e}")
        get_logger(
            "knowledge_graph_api",
            Operation.DELETE,
            f"relation_id={relation_id}",
            Result.FAILURE,
        ).error(f"delete_relation() failed: {e}")
        raise HTTPException(status_code=500, detail=f"删除关系失败: {str(e)}")
