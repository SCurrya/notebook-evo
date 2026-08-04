"""认证与命令服务的定向测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.auth import PasswordAuthMiddleware, check_api_password
from api.command_service import CommandService


class _FakeRequest:
    def __init__(self, path="/api/test", method="GET", headers=None):
        self.url = SimpleNamespace(path=path)
        self.method = method
        self.headers = headers or {}


class _FakeApiKey:
    def __init__(self):
        self.touched = False

    async def touch(self):
        self.touched = True


class _FakeCommandRow:
    def __init__(self, status):
        self.status = status


@pytest.mark.asyncio
async def test_password_middleware_skips_when_password_missing():
    """未配置密码时，密码中间件不应拦截请求。"""

    middleware = PasswordAuthMiddleware(app=object())
    middleware.password = None
    called = False

    async def call_next(_request):
        nonlocal called
        called = True
        return "ok"

    result = await middleware.dispatch(_FakeRequest(), call_next)

    assert called is True
    assert result == "ok"


@pytest.mark.asyncio
async def test_password_middleware_rejects_wrong_password():
    """配置密码后，错误的 Bearer 值应返回 401。"""

    middleware = PasswordAuthMiddleware(app=object())
    middleware.password = "correct-password"

    response = await middleware.dispatch(
        _FakeRequest(headers={"Authorization": "Bearer wrong-password"}),
        lambda _request: "ok",
    )

    assert response.status_code == 401
    assert response.body


@pytest.mark.asyncio
async def test_check_api_password_skips_without_password():
    """没有配置密码时，check_api_password 应直接放行。"""

    with patch("api.auth.get_secret_from_env", return_value=None):
        assert check_api_password(credentials=None) is True


@pytest.mark.asyncio
async def test_check_api_password_uses_constant_time_compare():
    """配置密码时，应校验 Bearer 令牌并通过恒定时间比较。"""

    credentials = SimpleNamespace(credentials="secret")

    with (
        patch("api.auth.get_secret_from_env", return_value="secret"),
        patch("api.auth.secrets.compare_digest", return_value=True) as mock_compare,
    ):
        assert check_api_password(credentials=credentials) is True
        mock_compare.assert_called_once_with("secret", "secret")


@pytest.mark.asyncio
async def test_cancel_command_job_rejects_running_job():
    """运行中的命令任务不应被伪造为已取消。"""

    with (
        patch("api.command_service.RecordID.parse", return_value="command:123"),
        patch("api.command_service.repo_query", new=AsyncMock()) as mock_query,
    ):
        mock_query.side_effect = [
            [{"id": "command:123", "status": "running"}],
        ]

        cancelled = await CommandService.cancel_command_job("command:123")

    assert cancelled is False
    mock_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_command_job_marks_new_job_canceled():
    """排队中的任务可被真实标记为 canceled。"""

    with (
        patch("api.command_service.RecordID.parse", return_value="command:123"),
        patch("api.command_service.repo_query", new=AsyncMock()) as mock_query,
    ):
        mock_query.side_effect = [
            [{"id": "command:123", "status": "new"}],
            [],
        ]

        cancelled = await CommandService.cancel_command_job("command:123")

    assert cancelled is True
    assert mock_query.await_count == 2
