"""
知识图谱域模型。

定义知识图谱中的实体（GraphEntity）和关系（GraphRelation）。
- GraphEntity：表示笔记本中提取出的实体（人物、组织、概念等）
- GraphRelation：表示两个实体之间的关系，使用 SurrealDB 的 RELATE 语句存储为图边

实体通过 notebook_id 字段关联到笔记本，关系通过 source_id/target_id 引用实体。
"""

from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger


class GraphEntity(ObjectModel):
    """知识图谱实体。"""

    table_name: ClassVar[str] = "graph_entity"
    nullable_fields: ClassVar[set[str]] = {"properties", "notebook_id"}

    name: str = Field(..., description="实体名称")
    type: str = Field(..., description="实体类型（如 person/organization/concept）")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="实体附加属性"
    )
    notebook_id: Optional[str] = Field(
        None, description="所属笔记本 ID"
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidInputError("实体名称不能为空")
        return v.strip()

    @field_validator("type")
    @classmethod
    def type_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidInputError("实体类型不能为空")
        return v.strip()

    def _prepare_save_data(self) -> Dict[str, Any]:
        """准备保存数据，将 notebook_id 转换为 RecordID。"""
        data = super()._prepare_save_data()
        if data.get("notebook_id"):
            data["notebook_id"] = ensure_record_id(data["notebook_id"])
        return data

    @classmethod
    async def get_by_notebook(cls, notebook_id: str) -> List["GraphEntity"]:
        """获取指定笔记本的所有实体。"""
        get_logger(
            "knowledge_graph_domain", Operation.READ, f"notebook_id={notebook_id}"
        ).debug("-> get_by_notebook()")
        results = await repo_query(
            "SELECT * FROM graph_entity WHERE notebook_id = $notebook_id ORDER BY name ASC",
            {"notebook_id": ensure_record_id(notebook_id)},
        )
        entities = []
        for row in results:
            try:
                entities.append(cls(**row))
            except Exception as e:
                get_logger(
                    "knowledge_graph_domain",
                    Operation.READ,
                    f"notebook_id={notebook_id}",
                    Result.FAILURE,
                ).warning(f"跳过无效实体记录: {e}")
        get_logger(
            "knowledge_graph_domain",
            Operation.READ,
            f"notebook_id={notebook_id}",
            Result.SUCCESS,
        ).info(f"<- get_by_notebook() count={len(entities)}")
        return entities


class GraphRelation(ObjectModel):
    """知识图谱关系（实体之间的边）。"""

    table_name: ClassVar[str] = "graph_relation"
    nullable_fields: ClassVar[set[str]] = {"properties"}

    source_id: str = Field(..., description="起始实体 ID")
    target_id: str = Field(..., description="目标实体 ID")
    type: str = Field(..., description="关系类型（如 works_for/located_in）")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="关系附加属性"
    )

    @field_validator("type")
    @classmethod
    def type_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidInputError("关系类型不能为空")
        return v.strip()

    def _prepare_save_data(self) -> Dict[str, Any]:
        """准备保存数据，将 source_id/target_id 转换为 RecordID。"""
        data = super()._prepare_save_data()
        if data.get("source_id"):
            data["source_id"] = ensure_record_id(data["source_id"])
        if data.get("target_id"):
            data["target_id"] = ensure_record_id(data["target_id"])
        return data

    @classmethod
    async def get_by_notebook(cls, notebook_id: str) -> List["GraphRelation"]:
        """获取指定笔记本的所有关系（通过实体关联）。"""
        get_logger(
            "knowledge_graph_domain", Operation.READ, f"notebook_id={notebook_id}"
        ).debug("-> get_relations_by_notebook()")
        results = await repo_query(
            """
            SELECT * FROM graph_relation
            WHERE source_id.notebook_id = $notebook_id
               OR target_id.notebook_id = $notebook_id
            """,
            {"notebook_id": ensure_record_id(notebook_id)},
        )
        relations = []
        for row in results:
            try:
                relations.append(cls(**row))
            except Exception as e:
                get_logger(
                    "knowledge_graph_domain",
                    Operation.READ,
                    f"notebook_id={notebook_id}",
                    Result.FAILURE,
                ).warning(f"跳过无效关系记录: {e}")
        get_logger(
            "knowledge_graph_domain",
            Operation.READ,
            f"notebook_id={notebook_id}",
            Result.SUCCESS,
        ).info(f"<- get_relations_by_notebook() count={len(relations)}")
        return relations
