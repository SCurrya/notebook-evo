"""共享 API 测试。

测试覆盖：
- POST   /api/share/notebook/{notebook_id}            创建共享链接
- GET    /api/share/{token}                            通过 token 访问共享笔记本
- DELETE /api/share/{id}                               撤销共享链接
- GET    /api/share/notebook/{notebook_id}/links       列出笔记本的所有共享链接
"""

from datetime import datetime, timezone
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
    notebook.get_sources = AsyncMock(return_value=[])
    notebook.get_notes = AsyncMock(return_value=[])
    return notebook


@pytest.fixture
def mock_share_link():
    """模拟 ShareLink 对象。"""
    link = MagicMock()
    link.id = "share_link:abc123"
    link.notebook_id = "notebook:test123"
    link.token = "test_token_xyz"
    link.permissions = "READ_ONLY"
    link.expires_at = None
    link.created_by = None
    link.created = datetime.now(timezone.utc)
    link.updated = datetime.now(timezone.utc)
    link.is_expired = MagicMock(return_value=False)
    link.save = AsyncMock()
    link.delete = AsyncMock()
    return link


class TestCreateShareLink:
    """创建共享链接测试。"""

    @patch("api.routers.share.Notebook")
    @patch("api.routers.share.ShareLink")
    @patch("api.routers.share.generate_share_token")
    def test_create_share_link_success(
        self, mock_gen_token, mock_share_link_cls, mock_notebook_cls, client, mock_notebook, mock_share_link
    ):
        """测试成功创建共享链接。"""
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)
        mock_gen_token.return_value = "generated_token"
        mock_share_link_cls.return_value = mock_share_link

        response = client.post(
            "/api/share/notebook/notebook:test123",
            json={"permissions": "READ_ONLY"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notebook_id"] == "notebook:test123"
        assert data["permissions"] == "READ_ONLY"
        assert data["token"] == "test_token_xyz"
        mock_share_link.save.assert_awaited_once()

    @patch("api.routers.share.Notebook")
    def test_create_share_link_notebook_not_found(self, mock_notebook_cls, client):
        """测试笔记本不存在时创建共享链接失败。"""
        mock_notebook_cls.get = AsyncMock(return_value=None)

        response = client.post(
            "/api/share/notebook/notebook:nonexistent",
            json={"permissions": "READ_ONLY"},
        )

        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    @patch("api.routers.share.Notebook")
    @patch("api.routers.share.ShareLink")
    @patch("api.routers.share.generate_share_token")
    def test_create_share_link_with_edit_permission(
        self, mock_gen_token, mock_share_link_cls, mock_notebook_cls, client, mock_notebook, mock_share_link
    ):
        """测试创建可编辑权限的共享链接。"""
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)
        mock_gen_token.return_value = "edit_token"
        mock_share_link.permissions = "EDIT"
        mock_share_link_cls.return_value = mock_share_link

        response = client.post(
            "/api/share/notebook/notebook:test123",
            json={"permissions": "EDIT"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == "EDIT"


class TestGetSharedNotebook:
    """通过 token 访问共享笔记本测试。"""

    @patch("api.routers.share.Notebook")
    @patch("api.routers.share.ShareLink")
    def test_get_shared_notebook_success(
        self, mock_share_link_cls, mock_notebook_cls, client, mock_notebook, mock_share_link
    ):
        """测试成功通过 token 访问共享笔记本。"""
        mock_share_link_cls.get_by_token = AsyncMock(return_value=mock_share_link)
        mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)

        response = client.get("/api/share/test_token_xyz")

        assert response.status_code == 200
        data = response.json()
        assert data["notebook_id"] == "notebook:test123"
        assert data["notebook_name"] == "测试笔记本"
        assert data["permissions"] == "READ_ONLY"

    @patch("api.routers.share.ShareLink")
    def test_get_shared_notebook_token_not_found(self, mock_share_link_cls, client):
        """测试 token 不存在时访问失败。"""
        mock_share_link_cls.get_by_token = AsyncMock(return_value=None)

        response = client.get("/api/share/nonexistent_token")

        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    @patch("api.routers.share.ShareLink")
    def test_get_shared_notebook_expired(self, mock_share_link_cls, client, mock_share_link):
        """测试共享链接过期时访问失败。"""
        mock_share_link.is_expired = MagicMock(return_value=True)
        mock_share_link_cls.get_by_token = AsyncMock(return_value=mock_share_link)

        response = client.get("/api/share/expired_token")

        assert response.status_code == 410
        assert "过期" in response.json()["detail"]


class TestListShareLinks:
    """列出共享链接测试。"""

    @patch("api.routers.share.ShareLink")
    def test_list_share_links_success(self, mock_share_link_cls, client, mock_share_link):
        """测试成功列出笔记本的共享链接。"""
        mock_share_link_cls.get_by_notebook = AsyncMock(
            return_value=[mock_share_link]
        )

        response = client.get("/api/share/notebook/notebook:test123/links")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["token"] == "test_token_xyz"


class TestRevokeShareLink:
    """撤销共享链接测试。"""

    @patch("api.routers.share.ShareLink")
    def test_revoke_share_link_success(self, mock_share_link_cls, client, mock_share_link):
        """测试成功撤销共享链接。"""
        mock_share_link_cls.get = AsyncMock(return_value=mock_share_link)

        response = client.delete("/api/share/share_link:abc123")

        assert response.status_code == 200
        mock_share_link.delete.assert_awaited_once()
