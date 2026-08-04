# -*- coding: utf-8 -*-
"""RAG evaluation endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from api.eval_service import (
    delete_report,
    get_report,
    list_reports,
    run_full_eval,
)
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter()


class EvalRunRequest(BaseModel):
    notebook_id: Optional[str] = Field(None, description="Scope evaluation to a notebook")
    top_k: int = Field(5, description="Number of retrieved chunks per question", ge=1, le=20)
    limit: Optional[int] = Field(None, description="Limit the number of questions", ge=1, le=50)


class EvalQuestionRequest(BaseModel):
    question: str = Field(..., description="Question to evaluate", min_length=1)
    reference: str = Field("", description="Reference/expected answer for context_recall")
    notebook_id: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)


@router.post("/eval/run")
async def run_eval(request: EvalRunRequest):
    """Run the full evaluation set and return the report."""
    log = get_logger("eval_api", Operation.EVAL, f"run notebook={request.notebook_id or 'all'}")
    log.debug("-> run_eval()")
    try:
        report = await run_full_eval(
            notebook_id=request.notebook_id,
            top_k=request.top_k,
            limit=request.limit,
        )
        log.bind(result=Result.SUCCESS).info(f"<- run_eval() ok questions={report['total_questions']}")
        return report
    except Exception as e:
        logger.error(f"Eval run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/eval/run-single")
async def run_single_eval_endpoint(request: EvalQuestionRequest):
    """Run evaluation for a single custom question."""
    from api.eval_service import run_single_eval

    log = get_logger("eval_api", Operation.EVAL, f"single q={request.question[:40]}")
    try:
        result = await run_single_eval(
            question=request.question,
            reference=request.reference,
            notebook_id=request.notebook_id,
            top_k=request.top_k,
        )
        log.bind(result=Result.SUCCESS).info("<- run_single_eval_endpoint() ok")
        return result
    except Exception as e:
        logger.error(f"Single eval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/eval/reports")
async def get_reports():
    """List all persisted evaluation reports (summary only)."""
    try:
        return {"reports": list_reports()}
    except Exception as e:
        logger.error(f"List reports failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eval/reports/{report_id}")
async def get_report_endpoint(report_id: str):
    """Get a full evaluation report by id."""
    try:
        report = get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/eval/reports/{report_id}")
async def delete_report_endpoint(report_id: str):
    """Delete an evaluation report."""
    try:
        deleted = delete_report(report_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"status": "deleted", "id": report_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
