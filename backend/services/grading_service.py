# backend/services/grading_service.py
"""채점 서비스 - 결과 비교 방식"""
import time
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import pandas as pd

from backend.services.database import postgres_connection, duckdb_connection
from backend.schemas.submission import SubmitResponse


def load_problem_with_answer(problem_id: str, data_type: str) -> Optional[dict]:
    """문제 및 정답 SQL 로드"""
    today = date.today().isoformat()
    if data_type == "stream":
        path = Path(f"problems/stream_daily/{today}.json")
    else:
        path = Path(f"problems/daily/{today}.json")
    
    if not path.exists():
        return None
    
    try:
        problems = json.loads(path.read_text(encoding="utf-8"))
        for p in problems:
            if p.get("problem_id") == problem_id:
                return p
        return None
    except Exception:
        return None


def compare_results(user_df: pd.DataFrame, answer_df: pd.DataFrame) -> tuple[bool, str]:
    """사용자 결과와 정답 결과 비교"""
    # 컬럼 수 확인
    if len(user_df.columns) != len(answer_df.columns):
        return False, f"컬럼 수가 다릅니다. (제출: {len(user_df.columns)}, 정답: {len(answer_df.columns)})"
    
    # 행 수 확인
    if len(user_df) != len(answer_df):
        return False, f"행 수가 다릅니다. (제출: {len(user_df)}, 정답: {len(answer_df)})"
    
    # 컬럼명 확인 (순서 무관)
    user_cols = set(c.lower() for c in user_df.columns)
    answer_cols = set(c.lower() for c in answer_df.columns)
    if user_cols != answer_cols:
        missing = answer_cols - user_cols
        extra = user_cols - answer_cols
        msg = "컬럼명이 다릅니다."
        if missing:
            msg += f" 누락: {missing}"
        if extra:
            msg += f" 추가: {extra}"
        return False, msg
    
    # 값 비교 (정렬 후)
    try:
        user_sorted = user_df.sort_values(by=list(user_df.columns)).reset_index(drop=True)
        answer_sorted = answer_df.sort_values(by=list(answer_df.columns)).reset_index(drop=True)
        
        # 컬럼 순서 맞추기
        user_sorted.columns = [c.lower() for c in user_sorted.columns]
        answer_sorted.columns = [c.lower() for c in answer_sorted.columns]
        user_sorted = user_sorted[sorted(user_sorted.columns)]
        answer_sorted = answer_sorted[sorted(answer_sorted.columns)]
        
        if user_sorted.equals(answer_sorted):
            return True, "정답입니다! 🎉"
        else:
            return False, "결과 값이 다릅니다."
    except Exception as e:
        return False, f"비교 오류: {str(e)}"


def grade_submission(
    problem_id: str,
    sql: str,
    data_type: str = "pa",
    note: Optional[str] = None
) -> SubmitResponse:
    """문제 제출 채점 - 결과 비교 방식"""
    start = time.time()
    session_date = date.today().isoformat()
    
    try:
        # 1. 문제 및 정답 SQL 로드
        problem = load_problem_with_answer(problem_id, data_type)
        answer_sql = problem.get("answer_sql") if problem else None
        
        # 2. 사용자 SQL 실행
        with postgres_connection() as pg:
            user_df = pg.fetch_df(sql.strip().rstrip(";"))
        
        # 3. 채점
        if answer_sql:
            # 정답이 있으면 결과 비교
            with postgres_connection() as pg:
                answer_df = pg.fetch_df(answer_sql.strip().rstrip(";"))
            is_correct, feedback = compare_results(user_df, answer_df)
        else:
            # 정답이 없으면 기본 검증 (결과가 있으면 일단 통과)
            is_correct = len(user_df) > 0
            feedback = "정답입니다! 🎉" if is_correct else "결과가 없습니다."
        
        # 4. 제출 기록 저장
        save_submission(
            session_date=session_date,
            problem_id=problem_id,
            data_type=data_type,
            sql_text=sql,
            is_correct=is_correct,
            feedback=feedback
        )
        
        elapsed = (time.time() - start) * 1000
        
        return SubmitResponse(
            is_correct=is_correct,
            feedback=feedback,
            execution_time_ms=elapsed,
            diff=None
        )
    
    except Exception as e:
        feedback = f"SQL 실행 오류: {str(e)}"
        
        save_submission(
            session_date=session_date,
            problem_id=problem_id,
            data_type=data_type,
            sql_text=sql,
            is_correct=False,
            feedback=feedback
        )
        
        return SubmitResponse(
            is_correct=False,
            feedback=feedback,
            execution_time_ms=0,
            diff=str(e)
        )


def get_hint(problem_id: str, sql: str, data_type: str = "pa") -> str:
    """AI 힌트 요청"""
    try:
        from problems.gemini import grade_pa_submission
        return grade_pa_submission(
            problem_id=problem_id,
            sql_text=sql,
            is_correct=False,
            diff=None,
            note="사용자가 도움을 요청했습니다. 틀린 부분을 친절하게 설명해주세요."
        )
    except Exception as e:
        return f"힌트 생성 실패: {str(e)}"


def save_submission(
    session_date: str,
    problem_id: str,
    data_type: str,
    sql_text: str,
    is_correct: bool,
    feedback: str
):
    """제출 기록 저장"""
    try:
        table = f"{data_type}_submissions"
        with duckdb_connection() as duck:
            duck.insert(table, {
                "session_date": session_date,
                "problem_id": problem_id,
                "sql_text": sql_text,
                "is_correct": is_correct,
                "feedback": feedback,
                "submitted_at": datetime.now()
            })
    except Exception:
        pass
