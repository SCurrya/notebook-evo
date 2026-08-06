# -*- coding: utf-8 -*-
"""Unit tests for the model fallback logic in ask.py."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestModelFallback:
    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self):
        from open_notebook.graphs.ask import _model_call_with_fallback

        async def call_fn(model):
            return "result"

        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(return_value=MagicMock()),
        ) as mock:
            result = await _model_call_with_fallback(
                "prompt", "model:primary", "tools", 500, call_fn
            )
        assert result == "result"
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_primary_failure_falls_back(self):
        from open_notebook.graphs.ask import _model_call_with_fallback

        async def call_fn(model):
            return "ok"

        fallback = MagicMock()
        fallback.provider = "openai_compatible"
        fallback.name = "gpt-5.4-mini"
        fallback.id = "model:fallback"

        # provision_langchain_model: first call raises (simulating 503),
        # second call returns a usable model
        async def fake_provision(prompt, mid, provider, max_tokens=2000):
            if mid == "model:primary":
                raise RuntimeError("503 provider error")
            return MagicMock()

        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=fake_provision,
        ) as mock, \
             patch(
                 "open_notebook.ai.models.model_manager.get_model",
                 new=AsyncMock(return_value=MagicMock(provider="openai_compatible")),
             ), \
             patch(
                 "open_notebook.ai.models.Model.get_models_by_type",
                 new=AsyncMock(return_value=[fallback]),
             ):
            result = await _model_call_with_fallback(
                "prompt", "model:primary", "tools", 500, call_fn
            )
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_primary_failure_no_candidates_raises(self):
        from open_notebook.graphs.ask import _model_call_with_fallback

        async def call_fn(model):
            return "never"

        async def fake_provision(prompt, mid, provider, max_tokens=2000):
            raise RuntimeError("boom")

        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=fake_provision,
        ), \
             patch(
                 "open_notebook.ai.models.Model.get_models_by_type",
                 new=AsyncMock(return_value=[]),
             ):
            with pytest.raises(RuntimeError):
                await _model_call_with_fallback(
                    "prompt", "model:primary", "tools", 500, call_fn
                )

    @pytest.mark.asyncio
    async def test_no_model_id_raises_immediately(self):
        from open_notebook.graphs.ask import _model_call_with_fallback

        async def call_fn(model):
            return "never"

        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ) as mock:
            with pytest.raises(RuntimeError):
                await _model_call_with_fallback(
                    "prompt", None, "tools", 500, call_fn
                )
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_ainvoke_failure_falls_back(self):
        """The call_fn (ainvoke) failing should also trigger fallback."""
        from open_notebook.graphs.ask import _model_call_with_fallback

        calls = []

        async def call_fn(model):
            # 模拟 ainvoke：第一个模型抛错，fallback 模型返回内容
            if len(calls) == 0:
                calls.append(model)
                raise RuntimeError("ainvoke failed on primary")
            return "fallback ok"

        fallback = MagicMock()
        fallback.provider = "openai_compatible"
        fallback.name = "gpt-5.4-mini"
        fallback.id = "model:fallback"

        # First provision returns a model whose ainvoke raises; second returns ok
        primary_model = MagicMock()
        primary_model.ainvoke = AsyncMock(side_effect=RuntimeError("503"))
        fallback_model = MagicMock()
        fallback_model.ainvoke = AsyncMock(return_value=MagicMock(content="fallback ok"))

        async def fake_provision(prompt, mid, provider, max_tokens=2000):
            if mid == "model:primary":
                return primary_model
            return fallback_model

        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=fake_provision,
        ), \
             patch(
                 "open_notebook.ai.models.model_manager.get_model",
                 new=AsyncMock(return_value=MagicMock(provider="openai_compatible")),
             ), \
             patch(
                 "open_notebook.ai.models.Model.get_models_by_type",
                 new=AsyncMock(return_value=[fallback]),
             ):
            result = await _model_call_with_fallback(
                "prompt", "model:primary", "tools", 500, call_fn
            )
        assert result == "fallback ok"
