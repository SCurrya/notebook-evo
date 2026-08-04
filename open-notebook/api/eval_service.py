# -*- coding: utf-8 -*-
"""
RAG evaluation service.

Runs the full RAG pipeline (hybrid retrieval + answer generation) against a
built-in question set, then scores the quality with RAGAS metrics:
  - faithfulness        (is the answer grounded in retrieved context?)
  - answer_relevancy    (does the answer address the question?)
  - context_precision   (are retrieved chunks relevant to the question?)
  - context_recall      (was the required reference content retrieved?)

Results are persisted to JSON files under the data dir so the frontend
dashboard can list and render them.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from open_notebook.search.hybrid import hybrid_search

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
EVAL_DIR = DATA_DIR / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_QUESTIONS = [
    {
        "id": "q1",
        "question": "什么是 AI Agent？它和传统问答模型有什么区别？",
        "reference": "AI Agent 是能够自主感知环境、做出决策并执行行动以完成特定目标的人工智能系统，与传统单一问答模型不同，Agent 具备目标导向性、自主性和工具调用能力。",
    },
    {
        "id": "q2",
        "question": "AI Agent 的核心能力有哪些？",
        "reference": "核心能力包括任务规划、工具调用、记忆管理和自我反思。",
    },
    {
        "id": "q3",
        "question": "什么是 MCP（Model Context Protocol）？它由谁提出？",
        "reference": "MCP 由 Anthropic 于 2024 年底提出，2026 年已成为智能体与外部系统交互的事实标准。",
    },
    {
        "id": "q4",
        "question": "RAG 技术是什么？高级 RAG 架构包含哪些组件？",
        "reference": "RAG 通过从外部知识库检索相关文档增强大模型回答质量，高级架构包含混合检索（BM25+向量）、重排序（Rerank）和 RAG 评估。",
    },
    {
        "id": "q5",
        "question": "GraphRAG 相比传统 RAG 有什么优势？",
        "reference": "GraphRAG 将知识图谱与 RAG 结合，通过图谱路径检索辅助推理，适合多跳问题和跨文档推理场景。",
    },
    {
        "id": "q6",
        "question": "多智能体系统如何协作完成任务？",
        "reference": "多智能体通过多个各司其职的 Agent 协作，如规划、执行、审查 Agent，通过消息队列或 A2A 协议通信。",
    },
    {
        "id": "q7",
        "question": "2026 年 AI 产业的衡量标准有什么变化？",
        "reference": "AI 产业重心从参数规模竞赛转向 Agent 工程化落地，衡量标准不再是基准测试分数，而是自主规划、工具调用及闭环执行的成功率。",
    },
    {
        "id": "q8",
        "question": "AI Agent 有哪些典型应用场景？",
        "reference": "智能客服、代码助手、数据分析和自动化工作流。",
    },
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_questions() -> List[Dict[str, Any]]:
    custom_path = EVAL_DIR / "questions.json"
    if custom_path.exists():
        try:
            data = json.loads(custom_path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception as e:
            logger.warning(f"Failed to load custom questions, using defaults: {e}")
    return DEFAULT_QUESTIONS


def _build_prompt(question: str, context: str) -> str:
    return (
        "你是一个严谨的知识库问答助手。请仅基于提供的参考资料回答用户问题，"
        "不要编造信息。如果参考资料不足以回答，请明确说明。\n\n"
        f"参考资料：\n{context}\n\n"
        f"用户问题：{question}\n\n"
        "请用简洁准确的中文回答。"
    )


async def _generate_answer(question: str, context: str) -> str:
    """Generate an answer using the default text model (best-effort)."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from open_notebook.ai.provision import provision_langchain_model

        prompt = ChatPromptTemplate.from_messages(
            [("system", _build_prompt(question, context))]
        )
        model = await provision_langchain_model("default")
        chain = prompt | model
        response = await chain.ainvoke({"input": question})
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                str(c.get("text", "")) if isinstance(c, dict) else str(c) for c in content
            )
        return str(content).strip()
    except Exception as e:
        logger.warning(f"Answer generation failed, using fallback: {e}")
        return f"（无法生成回答：{e}）"


def _metrics_fallback(
    question: str, answer: str, contexts: List[str], reference: str
) -> Dict[str, float]:
    """Lightweight fallback scoring when ragas is unavailable."""
    import re

    def _fraction(src: str, tgt: str) -> float:
        if not tgt:
            return 0.0
        src = src.lower()
        key_terms = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", tgt.lower())
        if not key_terms:
            return 0.0
        hit = sum(1 for k in key_terms if k.lower() in src)
        return min(1.0, hit / len(key_terms))

    joined_ctx = " ".join(contexts)
    return {
        "faithfulness": _fraction(answer, joined_ctx),
        "answer_relevancy": _fraction(answer, question),
        "context_precision": _fraction(joined_ctx, question),
        "context_recall": _fraction(joined_ctx, reference),
    }


async def _metrics_ragas(
    question: str, answer: str, contexts: List[str], reference: str
) -> Dict[str, float]:
    """Score with RAGAS. Falls back to the heuristic scorer on any failure."""
    try:
        from ragas import EvaluationDataset, SingleTurnSample
        from ragas import evaluate
        from ragas.metrics import context_precision, context_recall, faithfulness, answer_relevancy

        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=reference,
        )
        dataset = EvaluationDataset(samples=[sample])
        scorer = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
        )
        result = scorer.to_pandas().iloc[0]
        return {
            "faithfulness": float(result.get("faithfulness", 0.0) or 0.0),
            "answer_relevancy": float(result.get("answer_relevancy", 0.0) or 0.0),
            "context_precision": float(result.get("context_precision", 0.0) or 0.0),
            "context_recall": float(result.get("context_recall", 0.0) or 0.0),
        }
    except Exception as e:
        logger.warning(f"RAGAS scoring failed, using heuristic fallback: {e}")
        return _metrics_fallback(question, answer, contexts, reference)


async def run_single_eval(
    question: str,
    reference: str,
    notebook_id: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Run one question through the RAG pipeline and score it."""
    from open_notebook.domain.notebook import Notebook

    context_texts: List[str] = []
    retrieved: List[Dict[str, Any]] = []
    if notebook_id:
        try:
            notebook = Notebook.get(notebook_id)
            if notebook:
                hybrid = await hybrid_search(
                    question,
                    limit=top_k,
                    search_sources=True,
                    search_notes=True,
                    rerank=False,
                )
                for r in hybrid:
                    context_texts.append(f"[{r.title}] {r.content[:800]}")
                    retrieved.append(
                        {
                            "id": r.id,
                            "title": r.title,
                            "score": r.score,
                            "sources": r.sources,
                        }
                    )
        except Exception as e:
            logger.warning(f"Eval retrieval failed for '{question}': {e}")

    answer = await _generate_answer(question, "\n".join(context_texts[:top_k]))
    metrics = await _metrics_ragas(question, answer, context_texts[:top_k], reference)

    return {
        "question": question,
        "reference": reference,
        "answer": answer,
        "contexts": context_texts[:top_k],
        "retrieved": retrieved,
        "metrics": metrics,
    }


async def run_full_eval(
    notebook_id: Optional[str] = None,
    top_k: int = 5,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the full question set through the pipeline. Returns a persisted report."""
    questions = _load_questions()
    if limit:
        questions = questions[:limit]

    report_id = uuid.uuid4().hex[:12]
    started = _utc_now_iso()
    items: List[Dict[str, Any]] = []
    for q in questions:
        logger.info(f"Eval [{report_id}] running: {q['question'][:40]}")
        item = await run_single_eval(
            question=q["question"],
            reference=q.get("reference", ""),
            notebook_id=notebook_id,
            top_k=top_k,
        )
        item["question_id"] = q.get("id", "")
        items.append(item)

    # Aggregate metrics
    keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    aggregate = {k: 0.0 for k in keys}
    for item in items:
        for k in keys:
            aggregate[k] += float(item["metrics"].get(k, 0.0))
    if items:
        aggregate = {k: round(v / len(items), 4) for k, v in aggregate.items()}

    report = {
        "id": report_id,
        "created_at": started,
        "notebook_id": notebook_id,
        "total_questions": len(items),
        "aggregate": aggregate,
        "items": items,
    }
    _save_report(report)
    return report


def _save_report(report: Dict[str, Any]) -> None:
    path = EVAL_DIR / f"report-{report['id']}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Eval report saved: {path}")


def list_reports() -> List[Dict[str, Any]]:
    reports = []
    for p in sorted(EVAL_DIR.glob("report-*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            reports.append(
                {
                    "id": data.get("id"),
                    "created_at": data.get("created_at"),
                    "total_questions": data.get("total_questions"),
                    "aggregate": data.get("aggregate", {}),
                }
            )
        except Exception:
            continue
    return reports


def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    path = EVAL_DIR / f"report-{report_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete_report(report_id: str) -> bool:
    path = EVAL_DIR / f"report-{report_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
