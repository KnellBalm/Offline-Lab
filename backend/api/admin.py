# backend/api/admin.py
"""관리자 API"""
from datetime import date
import json
import os
from fastapi import APIRouter, HTTPException

from backend.schemas.admin import (
    SystemStatus, SchedulerStatus, DatabaseTable, TodayProblemsStatus,
    GenerateProblemsRequest, GenerateProblemsResponse,
    RefreshDataRequest, RefreshDataResponse
)
from backend.services.database import postgres_connection, duckdb_connection



router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """시스템 상태 조회"""
    # PostgreSQL 연결 확인
    postgres_connected = False
    tables = []
    
    try:
        with postgres_connection() as pg:
            postgres_connected = True
            
            table_df = pg.fetch_df("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            
            for _, row in table_df.iterrows():
                tbl = row["table_name"]
                try:
                    cnt = pg.fetch_df(f"SELECT COUNT(*) as cnt FROM {tbl}")
                    row_count = int(cnt.iloc[0]["cnt"])
                except:
                    row_count = 0
                
                col_cnt = pg.fetch_df(f"""
                    SELECT COUNT(*) as cnt FROM information_schema.columns
                    WHERE table_name = '{tbl}'
                """)
                
                tables.append(DatabaseTable(
                    table_name=tbl,
                    row_count=row_count,
                    column_count=int(col_cnt.iloc[0]["cnt"])
                ))
    except:
        pass
    
    # DuckDB 연결 확인
    duckdb_connected = False
    scheduler_sessions = []
    
    try:
        with duckdb_connection() as duck:
            duckdb_connected = True
            
            rows = duck.fetchall("""
                SELECT session_date, status, generated_at, problem_set_path
                FROM daily_sessions
                ORDER BY session_date DESC
                LIMIT 7
            """)
            
            scheduler_sessions = [
                SchedulerStatus(
                    session_date=r["session_date"],
                    status=r.get("status", "N/A"),
                    generated_at=r.get("generated_at"),
                    problem_set_path=r.get("problem_set_path")
                )
                for r in rows
            ]
    except:
        pass
    
    # 오늘의 문제 현황 확인
    today = date.today()
    problem_path = f"problems/daily/{today.isoformat()}.json"
    today_problems = None
    
    try:
        if os.path.exists(problem_path):
            with open(problem_path, encoding="utf-8") as f:
                problems = json.load(f)
            
            difficulties = {}
            for p in problems:
                diff = p.get("difficulty", "unknown")
                difficulties[diff] = difficulties.get(diff, 0) + 1
            
            today_problems = TodayProblemsStatus(
                exists=True,
                count=len(problems),
                difficulties=difficulties,
                path=problem_path
            )
        else:
            today_problems = TodayProblemsStatus(exists=False)
    except:
        today_problems = TodayProblemsStatus(exists=False)
    
    return SystemStatus(
        postgres_connected=postgres_connected,
        duckdb_connected=duckdb_connected,
        tables=tables,
        scheduler_sessions=scheduler_sessions,
        today_problems=today_problems
    )



@router.post("/generate-problems", response_model=GenerateProblemsResponse)
async def generate_problems(request: GenerateProblemsRequest):
    """문제 생성"""
    today = date.today()
    
    if request.data_type == "pa":
        try:
            from problems.generator import generate as gen_problems
            
            with postgres_connection() as pg:
                path = gen_problems(today, pg)
            
            # 생성된 문제 수 확인
            import json
            with open(path, encoding="utf-8") as f:
                problems = json.load(f)
            
            return GenerateProblemsResponse(
                success=True,
                message="PA 문제 생성 완료",
                path=path,
                problem_count=len(problems)
            )
        except Exception as e:
            return GenerateProblemsResponse(
                success=False,
                message=f"문제 생성 실패: {str(e)}"
            )
    else:
        return GenerateProblemsResponse(
            success=False,
            message="Stream 문제 생성은 준비 중입니다."
        )


@router.post("/refresh-data", response_model=RefreshDataResponse)
async def refresh_data(request: RefreshDataRequest):
    """데이터 갱신"""
    try:
        from generator.data_generator_advanced import generate_data
        
        if request.data_type == "pa":
            generate_data(modes=("pa",))
            return RefreshDataResponse(success=True, message="PA 데이터 갱신 완료")
        elif request.data_type == "stream":
            generate_data(modes=("stream",))
            return RefreshDataResponse(success=True, message="Stream 데이터 갱신 완료")
        else:
            return RefreshDataResponse(success=False, message="잘못된 data_type")
    except Exception as e:
        return RefreshDataResponse(success=False, message=f"데이터 갱신 실패: {str(e)}")


@router.post("/reset-submissions")
async def reset_submissions():
    """제출 기록 초기화"""
    try:
        with duckdb_connection() as duck:
            duck.execute("DELETE FROM pa_submissions")
        return {"success": True, "message": "제출 기록 초기화 완료"}
    except Exception as e:
        raise HTTPException(500, f"초기화 실패: {str(e)}")
