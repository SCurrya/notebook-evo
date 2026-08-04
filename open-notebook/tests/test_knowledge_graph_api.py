"""知识图谱 API 测试。

测试覆盖：
- POST /api/knowledge-graph/extract        从笔记本提取实体和关系
- GET  /api/knowledge-graph/{notebook_id}  获取笔记本的知识图谱
- POST /api/knowledge-graph/entity          手动添加实体
- POST /api/knowledge-graph/relation        手动添加关系
- DELETE /api/knowledge-graph/entity/{id}   删除实体
- DELETE /api/knowledge-graph/relation/{id} 删除关系
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端。"""
    from api.main import app

    return TestClient(app)


@pytest.fixture
def mock_notebook():
    """模拟 Notebook 对象。"""
    notebook = AsyncMock()
    notebook.id = "notebook:test123"
    notebook.name = "测试笔记本"
    notebook.description = "测试描述"
    notebook.get_context = AsyncMock(return_value="这是一段测试内容，包含张三和李四的信息。")
    return notebook


@pytest.fixture
def mock_entity():
    """模拟 GraphEntity 对象。"""
    entity = MagicMock()
    entity.id = "graph_entity:abc123"
    entity.name = "张三"
    entity.type = "person"
    entity.properties = {"age": 30}
    entity.notebook_id = "notebook:test123"
    entity.save = AsyncMock()
    entity.delete = AsyncMock()
    return entity


@pytest.fixture
def mock_relation():
    """模拟 GraphRelation 对象。"""
    relation = MagicMock()
    relation.id = "graph_relation:xyz789"
    relation.source_id = "graph_entity:abc123"
    relation.target_id = "graph_entity:def456"
    relation.type = "works_for"
    relation.properties = {}
    relation.save = AsyncMock()
    relation.delete = AsyncMock()
    return relation


class TestGraphExtraction:
    """知识图谱提取测试。"""

    @patch("api.routers.knowledge_graph.Notebook")
    @patch("api.routers.knowledge_graph._extract_with_llm")
    @patch("api.routers.knowledge_graph.GraphEntity")
    @patch("api.routers.knowledge_graph.GraphRelation")
    def test_extract_graph_success(
        self,
        mock_relation_cls,
        mock_entity_cls,
        mock_extract_llm,
        mock_notebook_cls,
        client,
        mock_notebook,
        mock_entity,
    ):
        """测试成功提取知识图谱。"""
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)
        mock_entity_cls.get_by_notebook = AsyncMock(return_value=[])
        mock_extract_llm.return_value = {
            "entities": [
                {"name": "张三", "type": "person", "properties": {}},
                {"name": "Acme公司", "type": "organization", "properties": {}},
            ],
            "relations": [
                {
                    "source": "张三",
                    "target": "Acme公司",
                    "type": "works_for",
                    "properties": {},
                }
            ],
        }

        # 模拟创建实体
        created_entities = []
        for i, name in enumerate(["张三", "Acme公司"]):
            ent = MagicMock()
            ent.id = f"graph_entity:{i}"
            ent.name = name
            ent.type = "person" if i == 0 else "organization"
            ent.properties = {}
            ent.notebook_id = "notebook:test123"
            ent.save = AsyncMock()
            created_entities.append(ent)

        # 让 GraphEntity 构造函数返回模拟对象
        mock_entity_cls.side_effect = created_entities

        # 模拟创建关系
        created_relation = MagicMock()
        created_relation.id = "graph_relation:0"
        created_relation.source_id = "graph_entity:0"
        created_relation.target_id = "graph_entity:1"
        created_relation.type = "works_for"
        created_relation.properties = {}
        created_relation.save = AsyncMock()
        mock_relation_cls.side_effect = [created_relation]

        response = client.post(
            "/api/knowledge-graph/extract",
            json={"notebook_id": "notebook:test123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 2
        assert len(data["relations"]) == 1
        assert data["entities"][0]["name"] == "张三"
        assert data["relations"][0]["type"] == "works_for"

    @patch("api.routers.knowledge_graph.Notebook")
    def test_extract_graph_notebook_not_found(self, mock_notebook_cls, client):
        """测试笔记本不存在时提取失败。"""
        mock_notebook_cls.get = AsyncMock(return_value=None)

        response = client.post(
            "/api/knowledge-graph/extract",
            json={"notebook_id": "notebook:nonexistent"},
        )

        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    @patch("api.routers.knowledge_graph.Notebook")
    def test_extract_graph_empty_content(self, mock_notebook_cls, client, mock_notebook):
        """测试笔记本内容为空时提取失败。"""
        mock_notebook.get_context = AsyncMock(return_value="")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        response = client.post(
            "/api/knowledge-graph/extract",
            json={"notebook_id": "notebook:test123"},
        )

        assert response.status_code == 400
        assert "为空" in response.json()["detail"]


class TestGraphRetrieval:
    """知识图谱获取测试。"""

    @patch("api.routers.knowledge_graph.GraphEntity")
    @patch("api.routers.knowledge_graph.GraphRelation")
    def test_get_graph_success(
        self, mock_relation_cls, mock_entity_cls, client, mock_entity, mock_relation
    ):
        """测试成功获取知识图谱。"""
        mock_entity_cls.get_by_notebook = AsyncMock(return_value=[mock_entity])
        mock_relation_cls.get_by_notebook = AsyncMock(return_value=[mock_relation])

        response = client.get("/api/knowledge-graph/notebook:test123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 1
        assert data["entities"][0]["name"] == "张三"
        assert len(data["relations"]) == 1
        assert data["relations"][0]["type"] == "works_for"

    @patch("api.routers.knowledge_graph.GraphEntity")
    @patch("api.routers.knowledge_graph.GraphRelation")
    def test_get_graph_empty(self, mock_relation_cls, mock_entity_cls, client):
        """测试获取空知识图谱。"""
        mock_entity_cls.get_by_notebook = AsyncMock(return_value=[])
        mock_relation_cls.get_by_notebook = AsyncMock(return_value=[])

        response = client.get("/api/knowledge-graph/notebook:empty")

        assert response.status_code == 200
        data = response.json()
        assert data["entities"] == []
        assert data["relations"] == []


class TestEntityManagement:
    """实体管理测试。"""

    @patch("api.routers.knowledge_graph.GraphEntity")
    def test_create_entity_success(self, mock_entity_cls, client, mock_entity):
        """测试成功创建实体。"""
        mock_entity_cls.return_value = mock_entity

        response = client.post(
            "/api/knowledge-graph/entity",
            json={
                "name": "张三",
                "type": "person",
                "properties": {"age": 30},
                "notebook_id": "notebook:test123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "张三"
        assert data["type"] == "person"
        mock_entity.save.assert_awaited_once()

    @patch("api.routers.knowledge_graph.GraphEntity")
    def test_delete_entity_success(self, mock_entity_cls, client, mock_entity):
        """测试成功删除实体。"""
        mock_entity_cls.get = AsyncMock(return_value=mock_entity)

        with patch(
            "api.routers.knowledge_graph.repo_query", new=AsyncMock()
        ) as mock_repo:
            response = client.delete(
                "/api/knowledge-graph/entity/graph_entity:abc123"
            )

        assert response.status_code == 200
        mock_entity.delete.assert_awaited_once()
        # 验证删除了关联关系
        assert mock_repo.await_count >= 1


class TestRelationManagement:
    """关系管理测试。"""

    @patch("api.routers.knowledge_graph.GraphEntity")
    @patch("api.routers.knowledge_graph.GraphRelation")
    def test_create_relation_success(
        self, mock_relation_cls, mock_entity_cls, client, mock_relation, mock_entity
    ):
        """测试成功创建关系。"""
        # 模拟源和目标实体都存在
        mock_entity_cls.get = AsyncMock(return_value=mock_entity)
        mock_relation_cls.return_value = mock_relation

        response = client.post(
            "/api/knowledge-graph/relation",
            json={
                "source_id": "graph_entity:abc123",
                "target_id": "graph_entity:def456",
                "type": "works_for",
                "properties": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "works_for"
        mock_relation.save.assert_awaited_once()

    @patch("api.routers.knowledge_graph.GraphEntity")
    @patch("api.routers.knowledge_graph.GraphRelation")
    def test_create_relation_entity_not_found(
        self, mock_relation_cls, mock_entity_cls, client
    ):
        """测试源/目标实体不存在时创建关系失败。"""
        mock_entity_cls.get = AsyncMock(side_effect=Exception("not found"))

        response = client.post(
            "/api/knowledge-graph/relation",
            json={
                "source_id": "graph_entity:nonexistent",
                "target_id": "graph_entity:nonexistent2",
                "type": "works_for",
            },
        )

        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    @patch("api.routers.knowledge_graph.GraphRelation")
    def test_delete_relation_success(self, mock_relation_cls, client, mock_relation):
        """测试成功删除关系。"""
        mock_relation_cls.get = AsyncMock(return_value=mock_relation)

        response = client.delete(
            "/api/knowledge-graph/relation/graph_relation:xyz789"
        )

        assert response.status_code == 200
        mock_relation.delete.assert_awaited_once()
