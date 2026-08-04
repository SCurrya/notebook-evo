"""
Studio API 端点测试套件。

测试覆盖：
- 模板 CRUD 操作（创建、读取、更新、删除）
- 报告生成端点
- FAQ 生成端点
- 时间线生成端点

使用 unittest.mock 模拟数据库操作和 LLM 调用，
确保测试不依赖真实数据库和外部服务。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端，环境变量已由 conftest.py 清理。"""
    from api.main import app

    return TestClient(app)


def _make_template_mock(template_id="studio_template:abc123", name="测试模板"):
    """创建模拟的 StudioTemplate 对象。"""
    template = AsyncMock()
    template.id = template_id
    template.name = name
    template.description = "测试描述"
    template.prompt = "测试提示词"
    template.output_format = "markdown"
    template.created = datetime(2026, 1, 1, 0, 0, 0)
    template.updated = datetime(2026, 1, 1, 0, 0, 0)
    template.save = AsyncMock()
    template.delete = AsyncMock(return_value=True)
    return template


class TestTemplateCRUD:
    """Studio 模板 CRUD 操作测试。"""

    @patch("api.routers.studio.StudioTemplate")
    def test_list_templates(self, mock_template_cls, client):
        """测试获取模板列表。"""
        mock_templates = [_make_template_mock(), _make_template_mock("studio_template:def456", "模板2")]
        mock_template_cls.get_all = AsyncMock(return_value=mock_templates)

        response = client.get("/api/v1/studio/templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "测试模板"
        assert data[0]["output_format"] == "markdown"
        assert "created_at" in data[0]
        assert "updated_at" in data[0]

    @patch("api.routers.studio.StudioTemplate")
    def test_create_template(self, mock_template_cls, client):
        """测试创建模板。"""
        mock_template = _make_template_mock()
        mock_template_cls.return_value = mock_template

        response = client.post(
            "/api/v1/studio/templates",
            json={
                "name": "新模板",
                "description": "新描述",
                "prompt": "新提示词",
                "output_format": "json",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # mock 对象返回预设的名称和格式
        assert data["name"] == "测试模板"
        assert data["output_format"] == "markdown"
        assert data["id"] == "studio_template:abc123"
        mock_template.save.assert_called_once()

    @patch("api.routers.studio.StudioTemplate")
    def test_get_template(self, mock_template_cls, client):
        """测试获取单个模板。"""
        mock_template = _make_template_mock()
        mock_template_cls.get = AsyncMock(return_value=mock_template)

        response = client.get("/api/v1/studio/templates/studio_template:abc123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "studio_template:abc123"
        assert data["name"] == "测试模板"

    @patch("api.routers.studio.StudioTemplate")
    def test_get_template_not_found(self, mock_template_cls, client):
        """测试获取不存在的模板返回 404。"""
        mock_template_cls.get = AsyncMock(return_value=None)

        response = client.get("/api/v1/studio/templates/studio_template:nonexistent")

        assert response.status_code == 404

    @patch("api.routers.studio.StudioTemplate")
    def test_update_template(self, mock_template_cls, client):
        """测试更新模板。"""
        mock_template = _make_template_mock()
        mock_template_cls.get = AsyncMock(return_value=mock_template)

        response = client.put(
            "/api/v1/studio/templates/studio_template:abc123",
            json={"name": "更新后的名称", "prompt": "更新后的提示词"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的名称"
        assert data["prompt"] == "更新后的提示词"
        mock_template.save.assert_called_once()

    @patch("api.routers.studio.StudioTemplate")
    def test_delete_template(self, mock_template_cls, client):
        """测试删除模板。"""
        mock_template = _make_template_mock()
        mock_template_cls.get = AsyncMock(return_value=mock_template)

        response = client.delete("/api/v1/studio/templates/studio_template:abc123")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        mock_template.delete.assert_called_once()


class TestReportGeneration:
    """报告生成端点测试。"""

    @patch("api.routers.studio.transformation_graph")
    @patch("api.routers.studio.DefaultModels")
    @patch("api.routers.studio.Notebook")
    def test_generate_report_academic(
        self, mock_notebook_cls, mock_default_models, mock_graph, client
    ):
        """测试生成学术报告。"""
        # 模拟笔记本
        mock_notebook = AsyncMock()
        mock_notebook.get_context = AsyncMock(return_value="笔记本内容...")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        # 模拟默认模型
        mock_defaults = AsyncMock()
        mock_defaults.default_transformation_model = "model:test"
        mock_default_models.get_instance = AsyncMock(return_value=mock_defaults)

        # 模拟转换引擎
        mock_graph.ainvoke = AsyncMock(
            return_value={"output": "# 学术报告\n\n这是报告内容。"}
        )

        response = client.post(
            "/api/v1/studio/report/generate",
            json={"notebook_id": "notebook:test", "report_type": "academic"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "report" in data
        assert data["report_type"] == "academic"
        assert data["notebook_id"] == "notebook:test"
        assert "学术报告" in data["report"]

    @patch("api.routers.studio.transformation_graph")
    @patch("api.routers.studio.DefaultModels")
    @patch("api.routers.studio.Notebook")
    def test_generate_report_business(
        self, mock_notebook_cls, mock_default_models, mock_graph, client
    ):
        """测试生成商业报告。"""
        mock_notebook = AsyncMock()
        mock_notebook.get_context = AsyncMock(return_value="商业内容...")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        mock_defaults = AsyncMock()
        mock_defaults.default_transformation_model = None
        mock_default_models.get_instance = AsyncMock(return_value=mock_defaults)

        mock_graph.ainvoke = AsyncMock(
            return_value={"output": "# 商业报告\n\n这是商业报告内容。"}
        )

        response = client.post(
            "/api/v1/studio/report/generate",
            json={"notebook_id": "notebook:test", "report_type": "business"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "business"

    @patch("api.routers.studio.Notebook")
    def test_generate_report_notebook_not_found(self, mock_notebook_cls, client):
        """测试笔记本不存在时返回 404。"""
        mock_notebook_cls.get = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/studio/report/generate",
            json={"notebook_id": "notebook:nonexistent", "report_type": "academic"},
        )

        assert response.status_code == 404


class TestFAQGeneration:
    """FAQ 生成端点测试。"""

    @patch("api.routers.studio.transformation_graph")
    @patch("api.routers.studio.DefaultModels")
    @patch("api.routers.studio.Notebook")
    def test_generate_faq(
        self, mock_notebook_cls, mock_default_models, mock_graph, client
    ):
        """测试生成 FAQ。"""
        mock_notebook = AsyncMock()
        mock_notebook.get_context = AsyncMock(return_value="FAQ 内容...")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        mock_defaults = AsyncMock()
        mock_defaults.default_transformation_model = "model:test"
        mock_default_models.get_instance = AsyncMock(return_value=mock_defaults)

        # 模拟 LLM 返回 JSON 格式的 FAQ
        faq_json = '[{"question": "问题1", "answer": "回答1"}, {"question": "问题2", "answer": "回答2"}]'
        mock_graph.ainvoke = AsyncMock(return_value={"output": faq_json})

        response = client.post(
            "/api/v1/studio/faq/generate",
            json={"notebook_id": "notebook:test", "num_questions": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["faqs"]) == 2
        assert data["faqs"][0]["question"] == "问题1"
        assert data["faqs"][0]["answer"] == "回答1"

    @patch("api.routers.studio.transformation_graph")
    @patch("api.routers.studio.DefaultModels")
    @patch("api.routers.studio.Notebook")
    def test_generate_faq_with_markdown_code_block(
        self, mock_notebook_cls, mock_default_models, mock_graph, client
    ):
        """测试 LLM 返回 Markdown 代码块包裹的 JSON 时也能正确解析。"""
        mock_notebook = AsyncMock()
        mock_notebook.get_context = AsyncMock(return_value="内容...")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        mock_defaults = AsyncMock()
        mock_defaults.default_transformation_model = None
        mock_default_models.get_instance = AsyncMock(return_value=mock_defaults)

        faq_with_codeblock = '```json\n[{"question": "问题", "answer": "回答"}]\n```'
        mock_graph.ainvoke = AsyncMock(return_value={"output": faq_with_codeblock})

        response = client.post(
            "/api/v1/studio/faq/generate",
            json={"notebook_id": "notebook:test", "num_questions": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["faqs"]) == 1
        assert data["faqs"][0]["question"] == "问题"


class TestTimelineGeneration:
    """时间线生成端点测试。"""

    @patch("api.routers.studio.transformation_graph")
    @patch("api.routers.studio.DefaultModels")
    @patch("api.routers.studio.Notebook")
    def test_generate_timeline(
        self, mock_notebook_cls, mock_default_models, mock_graph, client
    ):
        """测试生成时间线。"""
        mock_notebook = AsyncMock()
        mock_notebook.get_context = AsyncMock(return_value="时间线内容...")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        mock_defaults = AsyncMock()
        mock_defaults.default_transformation_model = "model:test"
        mock_default_models.get_instance = AsyncMock(return_value=mock_defaults)

        timeline_json = '[{"date": "2024-01-15", "event": "事件1"}, {"date": "2024-03-01", "event": "事件2"}]'
        mock_graph.ainvoke = AsyncMock(return_value={"output": timeline_json})

        response = client.post(
            "/api/v1/studio/timeline/generate",
            json={"notebook_id": "notebook:test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        assert data["events"][0]["date"] == "2024-01-15"
        assert data["events"][0]["event"] == "事件1"

    @patch("api.routers.studio.Notebook")
    def test_generate_timeline_empty_notebook(self, mock_notebook_cls, client):
        """测试笔记本内容为空时返回 400。"""
        mock_notebook = AsyncMock()
        mock_notebook.get_context = AsyncMock(return_value="")
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        response = client.post(
            "/api/v1/studio/timeline/generate",
            json={"notebook_id": "notebook:empty"},
        )

        assert response.status_code == 400
