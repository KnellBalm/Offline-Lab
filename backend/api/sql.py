# backend/api/sql.py
"""SQL 실행 API"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.schemas.submission import (
    SQLExecuteRequest, SQLExecuteResponse,
    SubmitRequest, SubmitResponse
)
from backend.services.sql_service import execute_sql
from backend.services.grading_service import grade_submission, get_hint
from backend.api.auth import get_session


router = APIRouter(prefix="/sql", tags=["sql"])


class HintRequest(BaseModel):
    problem_id: str
    sql: str
    data_type: str = "pa"


class HintResponse(BaseModel):
    hint: str


@router.post("/execute", response_model=SQLExecuteResponse)
async def execute_query(request: SQLExecuteRequest):
    """SQL 쿼리 실행 (테스트용)"""
    data, columns, error, elapsed = execute_sql(request.sql, request.limit)
    
    if error:
        return SQLExecuteResponse(
            success=False,
            error=error,
            execution_time_ms=elapsed
        )
    
    return SQLExecuteResponse(
        success=True,
        columns=columns,
        data=data,
        row_count=len(data) if data else 0,
        execution_time_ms=elapsed
    )


@router.post("/submit", response_model=SubmitResponse)
async def submit_answer(request: SubmitRequest, req: Request):
    """문제 제출 및 채점"""
    # 세션에서 user_id 추출
    user_id = None
    session_id = req.cookies.get("session_id")
    if session_id:
        session = get_session(session_id)
        if session and session.get("user"):
            user_id = session["user"].get("id")
    
    return grade_submission(
        problem_id=request.problem_id,
        sql=request.sql,
        data_type=getattr(request, 'data_type', 'pa'),
        note=request.note,
        user_id=user_id
    )


@router.post("/hint", response_model=HintResponse)
async def request_hint(request: HintRequest):
    """AI 힌트 요청"""
    hint = get_hint(
        problem_id=request.problem_id,
        sql=request.sql,
        data_type=request.data_type
    )
    return HintResponse(hint=hint)
