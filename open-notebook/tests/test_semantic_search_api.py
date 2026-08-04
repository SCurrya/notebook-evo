"""语义搜索 API 端点测试。

测试覆盖：
1. 无嵌入模型时返回 400
2. 成功执行语义搜索并返回相关性分数
3. 空查询返回 422 校验错误
4. 带 notebook_id 时按笔记本过滤结果
5. 向量搜索抛出数据库错误时返回 500
6. 结果按相关性分数降序排序
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端（环境变量已由 conftest 清理）。"""
    from api.main import app

    return TestClient(app)


class TestSemanticSearch:
    """语义搜索 API 测试套件。"""

    @patch("api.routers.search.model_manager")
    def test_semantic_search_no_embedding_model_returns_400(
        self, mock_manager, client
    ):
        """无嵌入模型配置时应返回 400 错误。"""
        mock_manager.get_embedding_model = AsyncMock(return_value=None)

        response = client.post(
            "/api/search/semantic",
            json={"query": "machine learning"},
        )

        assert response.status_code == 400
        assert "embedding model" in response.json()["detail"].lower()

    @patch("api.routers.search._filter_results_by_notebook", new_callable=AsyncMock)
    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager")
    def test_semantic_search_returns_results_with_relevance(
        self, mock_manager, mock_vector_search, mock_filter, client
    ):
        """成功执行语义搜索并返回带相关性分数的结果。"""
        mock_manager.get_embedding_model = AsyncMock(return_value=True)
        mock_vector_search.return_value = [
            {
                "id": "source:abc",
                "title": "机器学习入门",
                "parent_id": "source:abc",
                "final_score": 0.85,
                "matches": ["机器学习是人工智能的一个分支"],
            }
        ]
        mock_filter.return_value = mock_vector_search.return_value

        response = client.post(
            "/api/search/semantic",
            json={"query": "machine learning", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["query"] == "machine learning"
        assert data["results"][0]["relevance_score"] == 0.85
        assert data["results"][0]["parent_id"] == "source:abc"
        assert data["results"][0]["result_type"] == "source"

    def test_semantic_search_empty_query_returns_422(self, client):
        """空查询应触发 Pydantic 校验错误（422）。"""
        response = client.post(
            "/api/search/semantic",
            json={"query": ""},
        )

        assert response.status_code == 422

    @patch("api.routers.search._filter_results_by_notebook", new_callable=AsyncMock)
    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager")
    def test_semantic_search_with_notebook_id_filters_results(
        self, mock_manager, mock_vector_search, mock_filter, client
    ):
        """提供 notebook_id 时应调用笔记本过滤函数。"""
        mock_manager.get_embedding_model = AsyncMock(return_value=True)
        mock_vector_search.return_value = [
            {
                "id": "source:abc",
                "title": "源 A",
                "parent_id": "source:abc",
                "final_score": 0.9,
            },
            {
                "id": "source:xyz",
                "title": "源 B（不属于笔记本）",
                "parent_id": "source:xyz",
                "final_score": 0.5,
            },
        ]
        # 模拟过滤后仅保留属于笔记本的结果
        mock_filter.return_value = [mock_vector_search.return_value[0]]

        response = client.post(
            "/api/search/semantic",
            json={
                "query": "test",
                "notebook_id": "notebook:123",
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["results"][0]["parent_id"] == "source:abc"
        assert data["notebook_id"] == "notebook:123"
        # 验证过滤函数被调用
        mock_filter.assert_called_once()

    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager")
    def test_semantic_search_database_error_returns_500(
        self, mock_manager, mock_vector_search, client
    ):
        """向量搜索抛出 DatabaseOperationError 时应返回 500。"""
        from open_notebook.exceptions import DatabaseOperationError

        mock_manager.get_embedding_model = AsyncMock(return_value=True)
        mock_vector_search.side_effect = DatabaseOperationError("DB down")

        response = client.post(
            "/api/search/semantic",
            json={"query": "test"},
        )

        assert response.status_code == 500
        assert "Semantic search failed" in response.json()["detail"]

    @patch("api.routers.search._filter_results_by_notebook", new_callable=AsyncMock)
    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager")
    def test_semantic_search_results_sorted_by_relevance_desc(
        self, mock_manager, mock_vector_search, mock_filter, client
    ):
        """结果应按相关性分数降序排序。"""
        mock_manager.get_embedding_model = AsyncMock(return_value=True)
        mock_vector_search.return_value = [
            {
                "id": "source:low",
                "title": "低相关",
                "parent_id": "source:low",
                "final_score": 0.3,
            },
            {
                "id": "source:high",
                "title": "高相关",
                "parent_id": "source:high",
                "final_score": 0.95,
            },
            {
                "id": "source:mid",
                "title": "中相关",
                "parent_id": "source:mid",
                "final_score": 0.6,
            },
        ]
        mock_filter.return_value = mock_vector_search.return_value

        response = client.post(
            "/api/search/semantic",
            json={"query": "test"},
        )

        assert response.status_code == 200
        data = response.json()
        scores = [r["relevance_score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)
        assert scores[0] == 0.95
        assert scores[-1] == 0.3
