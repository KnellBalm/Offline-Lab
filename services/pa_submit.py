# services/pa_submit.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

import pandas as pd

from engine.postgres_engine import PostgresEngine
from engine.duckdb_engine import DuckDBEngine
from problems.gemini import grade_pa_submission
from common.logging import get_logger
from config.db import PostgresEnv, get_duckdb_path

logger = get_logger(__name__)


def _get_pg():
    """PostgreSQL 연결 생성"""
    return PostgresEngine(PostgresEnv().dsn())


def _get_duck():
    """DuckDB 연결 생성 (동시 접근 문제 방지)"""
    return DuckDBEngine(get_duckdb_path())


# ============================
# 내부 헬퍼
# ============================
def _run_user_sql(sql_text: str) -> pd.DataFrame:
    """
    사용자 SQL 실행
    """
    logger.info("running user sql")
    pg = _get_pg()
    try:
        return pg.fetch_df(sql_text)
    finally:
        pg.close()


def _run_answer_sql(problem_id: str) -> pd.DataFrame:
    """
    문제별 정답 SQL 실행
    """
    duck = _get_duck()
    try:
        result = duck.fetchone(
            """
            SELECT answer_sql
            FROM pa_answers
            WHERE problem_id = ?
            """,
            [problem_id],
        )
    finally:
        duck.close()
    
    if result is None:
        raise ValueError(f"problem_id={problem_id}의 정답 SQL을 찾을 수 없습니다")
    
    logger.info(f"running answer sql for {problem_id}")
    pg = _get_pg()
    try:
        return pg.fetch_df(result["answer_sql"])
    finally:
        pg.close()


def _compare_df(user_df: pd.DataFrame, answer_df: pd.DataFrame) -> Dict[str, Any]:
    """
    결과 비교 (엄격)
    """
    if list(user_df.columns) != list(answer_df.columns):
        return {
            "is_correct": False,
            "reason": "컬럼 구성이 다릅니다",
        }

    if len(user_df) != len(answer_df):
        return {
            "is_correct": False,
            "reason": "row 수가 다릅니다",
        }

    diff = (user_df != answer_df).any(axis=1)
    if diff.any():
        idx = diff.idxmax()
        col = (user_df.iloc[idx] != answer_df.iloc[idx]).idxmax()
        return {
            "is_correct": False,
            "reason": f"{idx+1}번째 row, {col} 컬럼 값이 다릅니다",
        }

    return {"is_correct": True}


# ============================
# 외부 진입점 (Streamlit / CLI 공용)
# ============================
def submit_pa(
    *,
    problem_id: str,
    sql_text: str,
    note: str | None = None,
    session_date: str,
) -> Dict[str, Any]:
    """
    PA 문제 제출 엔진
    """

    submitted_at = datetime.utcnow()
    logger.info(f"PA submit start problem_id={problem_id}")

    # ----------------------------
    # 1. 사용자 SQL 실행
    # ----------------------------
    try:
        user_df = _run_user_sql(sql_text)
    except Exception as e:
        logger.exception("user sql execution failed")
        feedback = grade_pa_submission(
            problem_id=problem_id,
            sql_text=sql_text,
            error=str(e),
            is_correct=False,
            diff=None,
            note=note,
        )
        _save_submission(
            problem_id,
            sql_text,
            False,
            feedback,
            session_date,
            submitted_at,
        )
        return {
            "is_correct": False,
            "feedback": feedback,
        }

    # ----------------------------
    # 2. 정답 SQL 실행
    # ----------------------------
    answer_df = _run_answer_sql(problem_id)

    # ----------------------------
    # 3. 결과 비교
    # ----------------------------
    cmp = _compare_df(user_df, answer_df)
    is_correct = cmp.get("is_correct", False)
    diff_reason = cmp.get("reason")

    # ----------------------------
    # 4. Gemini 채점
    # ----------------------------
    feedback = grade_pa_submission(
        problem_id=problem_id,
        sql_text=sql_text,
        is_correct=is_correct,
        diff=diff_reason,
        note=note,
    )

    # ----------------------------
    # 5. 저장
    # ----------------------------
    _save_submission(
        problem_id,
        sql_text,
        is_correct,
        feedback,
        session_date,
        submitted_at,
    )

    logger.info(f"PA submit done problem_id={problem_id} correct={is_correct}")

    return {
        "is_correct": is_correct,
        "feedback": feedback,
    }


# ============================
# DB 저장
# ============================
def _save_submission(
    problem_id: str,
    sql_text: str,
    is_correct: bool,
    feedback: str,
    session_date: str,
    submitted_at: datetime,
):
    duck = _get_duck()
    try:
        duck.insert("pa_submissions", {
            "session_date": session_date,
            "problem_id": problem_id,
            "sql_text": sql_text,
            "is_correct": is_correct,
            "feedback": feedback,
            "submitted_at": submitted_at,
        })
    finally:
        duck.close()
