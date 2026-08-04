"""API Key 管理 API 测试。

测试覆盖：
- POST   /api/api-keys        创建 API Key（返回明文，仅此一次）
- GET    /api/api-keys        列出所有 API Keys（不返回明文）
- DELETE /api/api-keys/{id}   撤销 API Key

安全验证：
- API Key 使用 SHA-256 哈希存储，不存储明文
- 列表接口不返回明文 key
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
def mock_api_key():
    """模拟 ApiKey 对象。"""
    key = MagicMock()
    key.id = "api_key:abc123"
    key.name = "测试 Key"
    key.key_hash = "a" * 64  # 模拟 SHA-256 哈希值
    key.permissions = ["read", "write"]
    key.created = datetime.now(timezone.utc)
    key.updated = datetime.now(timezone.utc)
    key.last_used_at = None
    key.save = AsyncMock()
    key.delete = AsyncMock()
    return key


class TestCreateApiKey:
    """创建 API Key 测试。"""

    @patch("api.routers.api_keys.ApiKey")
    @patch("api.routers.api_keys.generate_api_key")
    @patch("api.routers.api_keys.hash_api_key")
    def test_create_api_key_success(
        self, mock_hash, mock_gen_key, mock_api_key_cls, client, mock_api_key
    ):
        """测试成功创建 API Key，返回明文。"""
        mock_gen_key.return_value = "on_test_key_12345"
        mock_hash.return_value = "hashed_value"
        mock_api_key_cls.return_value = mock_api_key

        response = client.post(
            "/api/api-keys",
            json={"name": "测试 Key", "permissions": ["read", "write"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试 Key"
        assert data["key"] == "on_test_key_12345"  # 明文 key 返回
        assert "read" in data["permissions"]
        assert "write" in data["permissions"]
        assert "保存" in data["message"]
        mock_api_key.save.assert_awaited_once()

    @patch("api.routers.api_keys.ApiKey")
    @patch("api.routers.api_keys.generate_api_key")
    @patch("api.routers.api_keys.hash_api_key")
    def test_create_api_key_default_permissions(
        self, mock_hash, mock_gen_key, mock_api_key_cls, client, mock_api_key
    ):
        """测试创建 API Key 时使用默认权限。"""
        mock_gen_key.return_value = "on_default_key"
        mock_hash.return_value = "hashed_value"
        mock_api_key.permissions = ["read"]
        mock_api_key_cls.return_value = mock_api_key

        response = client.post(
            "/api/api-keys",
            json={"name": "默认权限 Key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == ["read"]

    @patch("api.routers.api_keys.ApiKey")
    @patch("api.routers.api_keys.generate_api_key")
    @patch("api.routers.api_keys.hash_api_key")
    def test_create_api_key_hash_not_stored_as_plaintext(
        self, mock_hash, mock_gen_key, mock_api_key_cls, client, mock_api_key
    ):
        """测试 API Key 的哈希值被存储，明文不被存储。"""
        plaintext_key = "on_secret_key_67890"
        hashed_value = "sha256_hashed_value_xxx"
        mock_gen_key.return_value = plaintext_key
        mock_hash.return_value = hashed_value
        mock_api_key_cls.return_value = mock_api_key

        response = client.post(
            "/api/api-keys",
            json={"name": "安全测试 Key", "permissions": ["read"]},
        )

        assert response.status_code == 200
        # 验证 ApiKey 对象使用的是哈希值，不是明文
        mock_api_key_cls.assert_called_once()
        _, kwargs = mock_api_key_cls.call_args
        assert kwargs["key_hash"] == hashed_value
        assert kwargs["key_hash"] != plaintext_key


class TestListApiKeys:
    """列出 API Keys 测试。"""

    @patch("api.routers.api_keys.ApiKey")
    def test_list_api_keys_success(self, mock_api_key_cls, client, mock_api_key):
        """测试成功列出所有 API Keys，不返回明文。"""
        mock_api_key_cls.get_all = AsyncMock(return_value=[mock_api_key])

        response = client.get("/api/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "测试 Key"
        assert "key" not in data[0]  # 列表接口不返回明文 key
        assert "key_hash" not in data[0]  # 也不返回哈希值
        assert "permissions" in data[0]

    @patch("api.routers.api_keys.ApiKey")
    def test_list_api_keys_empty(self, mock_api_key_cls, client):
        """测试列出空 API Key 列表。"""
        mock_api_key_cls.get_all = AsyncMock(return_value=[])

        response = client.get("/api/api-keys")

        assert response.status_code == 200
        assert response.json() == []


class TestRevokeApiKey:
    """撤销 API Key 测试。"""

    @patch("api.routers.api_keys.ApiKey")
    def test_revoke_api_key_success(self, mock_api_key_cls, client, mock_api_key):
        """测试成功撤销 API Key。"""
        mock_api_key_cls.get = AsyncMock(return_value=mock_api_key)

        response = client.delete("/api/api-keys/api_key:abc123")

        assert response.status_code == 200
        assert "撤销" in response.json()["message"]
        mock_api_key.delete.assert_awaited_once()
