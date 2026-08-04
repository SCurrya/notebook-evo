# -*- coding: utf-8 -*-
"""Unit tests for the RAG evaluation service."""
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestMetricsFallback:
    @pytest.mark.asyncio
    async def test_heuristic_scoring(self):
        from api.eval_service import _metrics_fallback

        m = _metrics_fallback(
            question="AI Agent 的核心能力有哪些？",
            answer="核心能力包括任务规划、工具调用、记忆管理和自我反思。",
            contexts=["任务规划、工具调用、记忆管理、自我反思是 Agent 的核心能力"],
            reference="核心能力包括任务规划、工具调用、记忆管理和自我反思",
        )
        assert 0 <= m["faithfulness"] <= 1
        assert 0 <= m["answer_relevancy"] <= 1
        assert 0 <= m["context_precision"] <= 1
        assert 0 <= m["context_recall"] <= 1

    @pytest.mark.asyncio
    async def test_ragas_fallback_on_error(self):
        import api.eval_service as svc

        # Force the ragas branch to raise, and verify the heuristic fallback
        # is invoked and its result returned.
        captured = {}

        def fake_fallback(question, answer, contexts, reference):
            captured["called"] = True
            return {"faithfulness": 0.4, "answer_relevancy": 0.4,
                    "context_precision": 0.4, "context_recall": 0.4}

        with patch.object(svc, "_metrics_fallback", new=fake_fallback), \
             patch("builtins.__import__", side_effect=ImportError("ragas unavailable")):
            m = await svc._metrics_ragas(
                question="q", answer="a", contexts=["c"], reference="r"
            )
        assert captured.get("called") is True
        assert m["faithfulness"] == 0.4


class TestQuestionLoading:
    def test_default_questions_nonempty(self):
        from api.eval_service import DEFAULT_QUESTIONS

        assert len(DEFAULT_QUESTIONS) >= 5
        for q in DEFAULT_QUESTIONS:
            assert q["question"]
            assert q["reference"]

    def test_custom_questions_file(self, tmp_path, monkeypatch):
        from api.eval_service import _load_questions

        monkeypatch.setattr("api.eval_service.EVAL_DIR", tmp_path)
        (tmp_path / "questions.json").write_text(
            json.dumps([{"id": "x", "question": "自定义", "reference": "ref"}], ensure_ascii=False),
            encoding="utf-8",
        )
        questions = _load_questions()
        assert len(questions) == 1
        assert questions[0]["question"] == "自定义"


class TestReportPersistence:
    def test_save_and_list_reports(self, tmp_path, monkeypatch):
        import api.eval_service as svc

        monkeypatch.setattr(svc, "EVAL_DIR", tmp_path)
        report = {"id": "abc123", "created_at": "2026-08-04T00:00:00", "total_questions": 1, "aggregate": {}}
        svc._save_report(report)
        reports = svc.list_reports()
        assert len(reports) == 1
        assert reports[0]["id"] == "abc123"
        assert svc.get_report("abc123")["id"] == "abc123"
        assert svc.delete_report("abc123") is True
        assert svc.get_report("abc123") is None
        assert svc.delete_report("missing") is False


class TestRunSingleEval:
    @pytest.mark.asyncio
    async def test_run_single_eval_shape(self):
        import api.eval_service as svc

        with patch.object(svc, "hybrid_search", new=AsyncMock(return_value=[])), \
             patch.object(svc, "_generate_answer", new=AsyncMock(return_value="测试回答")), \
             patch.object(svc, "_metrics_ragas", new=AsyncMock(
                 return_value={"faithfulness": 1.0, "answer_relevancy": 0.5,
                               "context_precision": 0.8, "context_recall": 0.9}
             )):
            result = await svc.run_single_eval(
                question="什么是 AI Agent？", reference="参考", top_k=5
            )
        assert result["question"] == "什么是 AI Agent？"
        assert result["answer"] == "测试回答"
        assert result["metrics"]["faithfulness"] == 1.0
        assert "contexts" in result
