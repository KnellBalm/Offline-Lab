# backend/services/problem_service.py
"""문제 관련 서비스"""
import json
import random
from pathlib import Path
from datetime import date
from typing import List, Optional, Dict, Any

from backend.schemas.problem import Problem, TableSchema, TableColumn
from backend.services.database import postgres_connection, duckdb_connection

PROBLEM_DIR = Path("problems/daily")
NUM_PROBLEM_SETS = 3


def get_user_set_index(user_id: Optional[str], target_date: date, data_type: str) -> int:
    """사용자에게 할당된 문제 세트 인덱스 조회 (없으면 랜덤 할당)"""
    if not user_id:
        # 로그인 안 된 사용자는 set_0 사용
        return 0
    
    try:
        with postgres_connection() as pg:
            # 기존 할당 확인
            df = pg.fetch_df("""
                SELECT set_index FROM user_problem_sets 
                WHERE user_id = %s AND session_date = %s AND data_type = %s
            """, [user_id, target_date.isoformat(), data_type])
            
            if len(df) > 0:
                return int(df.iloc[0]["set_index"])
            
            # 새 할당 (랜덤)
            set_index = random.randint(0, NUM_PROBLEM_SETS - 1)
            pg.execute("""
                INSERT INTO user_problem_sets (user_id, session_date, data_type, set_index)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, session_date, data_type) DO NOTHING
            """, [user_id, target_date.isoformat(), data_type, set_index])
            
            return set_index
    except Exception:
        return 0


def get_problems(
    data_type: str = "pa",
    target_date: Optional[date] = None,
    user_id: Optional[str] = None
) -> List[Problem]:
    """문제 목록 조회 (사용자별 세트 할당)"""
    if target_date is None:
        target_date = date.today()
    
    # 사용자 세트 인덱스 조회
    set_index = get_user_set_index(user_id, target_date, data_type)
    
    # 파일 경로 결정
    if data_type == "pa":
        # 먼저 세트 파일 시도
        path = PROBLEM_DIR / f"{target_date}_set{set_index}.json"
        if not path.exists():
            # 세트 파일 없으면 기본 파일 사용 (호환성)
            path = PROBLEM_DIR / f"{target_date}.json"
    else:
        # Stream 문제 (아직 세트 미지원)
        path = PROBLEM_DIR / f"stream_{target_date}.json"
    
    if not path.exists():
        return []
    
    with open(path, encoding="utf-8") as f:
        problems_data = json.load(f)
    
    # 완료 상태 조회
    completed_map = get_submission_status(target_date, user_id)
    
    problems = []
    for p in problems_data:
        problem = Problem(**p)
        if problem.problem_id in completed_map:
            problem.is_completed = True
            problem.is_correct = completed_map[problem.problem_id]
        else:
            problem.is_completed = False
        problems.append(problem)
    
    return problems


def get_problem_by_id(
    problem_id: str,
    data_type: str = "pa",
    target_date: Optional[date] = None,
    user_id: Optional[str] = None
) -> Optional[Problem]:
    """문제 상세 조회"""
    problems = get_problems(data_type, target_date, user_id)
    for p in problems:
        if p.problem_id == problem_id:
            return p
    return None


def get_submission_status(target_date: date, user_id: Optional[str] = None) -> Dict[str, bool]:
    """제출 상태 조회"""
    try:
        with postgres_connection() as pg:
            if user_id:
                df = pg.fetch_df("""
                    SELECT problem_id, is_correct FROM submissions 
                    WHERE session_date = %s AND user_id = %s
                """, [target_date.isoformat(), user_id])
            else:
                df = pg.fetch_df("""
                    SELECT problem_id, is_correct FROM submissions 
                    WHERE session_date = %s AND user_id IS NULL
                """, [target_date.isoformat()])
            
            return {row["problem_id"]: row["is_correct"] for _, row in df.iterrows()}
    except Exception:
        return {}


def get_table_schema(prefix: str = "pa_") -> List[TableSchema]:
    """테이블 스키마 조회"""
    tables = []
    
    try:
        with postgres_connection() as pg:
            # 테이블 목록
            table_df = pg.fetch_df(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '{prefix}%'
                ORDER BY table_name
            """)
            
            for _, row in table_df.iterrows():
                tbl_name = row["table_name"]
                
                # 컬럼 정보
                col_df = pg.fetch_df(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{tbl_name}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                
                columns = [
                    TableColumn(
                        column_name=c["column_name"],
                        data_type=c["data_type"]
                    )
                    for _, c in col_df.iterrows()
                ]
                
                # 행 수
                try:
                    count_df = pg.fetch_df(f"SELECT COUNT(*) as cnt FROM {tbl_name}")
                    row_count = int(count_df.iloc[0]["cnt"])
                except:
                    row_count = None
                
                tables.append(TableSchema(
                    table_name=tbl_name,
                    columns=columns,
                    row_count=row_count
                ))
    except Exception:
        pass
    
    return tables
