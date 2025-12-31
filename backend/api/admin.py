# backend/api/admin.py
"""관리자 API"""
from datetime import date
import json
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Query

from backend.schemas.admin import (
    SystemStatus, SchedulerStatus, DatabaseTable, TodayProblemsStatus,
    GenerateProblemsRequest, GenerateProblemsResponse,
    RefreshDataRequest, RefreshDataResponse
)
from backend.services.database import postgres_connection, duckdb_connection
from backend.api.auth import get_session
from backend.services.db_logger import get_logs, db_log, LogCategory, LogLevel


async def require_admin(request: Request):
    """관리자 권한 체크"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(403, "관리자 권한이 필요합니다")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(403, "관리자 권한이 필요합니다")
    
    user_email = session.get("user", {}).get("email", "")
    
    # DB에서 is_admin 확인
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df("SELECT is_admin FROM users WHERE email = %s", [user_email])
            if len(df) == 0 or not df.iloc[0].get('is_admin', False):
                raise HTTPException(403, "관리자 권한이 필요합니다")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(403, "관리자 권한이 필요합니다")
    
    return session


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status", response_model=SystemStatus)
async def get_system_status(admin=Depends(require_admin)):
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
    """문제 생성 (PA 또는 Stream)"""
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
                message=f"PA 문제 생성 실패: {str(e)}"
            )
    
    elif request.data_type == "stream":
        try:
            from problems.generator_stream import generate_stream_problems
            
            with postgres_connection() as pg:
                path = generate_stream_problems(today, pg)
            
            import json
            with open(path, encoding="utf-8") as f:
                problems = json.load(f)
            
            return GenerateProblemsResponse(
                success=True,
                message="Stream 문제 생성 완료",
                path=path,
                problem_count=len(problems)
            )
        except Exception as e:
            return GenerateProblemsResponse(
                success=False,
                message=f"Stream 문제 생성 실패: {str(e)}"
            )
    
    else:
        return GenerateProblemsResponse(
            success=False,
            message="지원하지 않는 data_type입니다."
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


@router.get("/dataset-versions")
async def get_dataset_versions():
    """데이터셋 버전 이력 조회"""
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df("""
                SELECT 
                    version_id,
                    created_at,
                    generator_type,
                    start_date,
                    end_date,
                    n_users,
                    n_events
                FROM dataset_versions
                ORDER BY created_at DESC
                LIMIT 20
            """)
            versions = df.to_dict(orient="records")
            return {"success": True, "versions": versions}
    except Exception as e:
        return {"success": False, "message": str(e), "versions": []}


@router.get("/scheduler-logs")
async def get_scheduler_logs(lines: int = 50):
    """스케줄러 로그 조회 (docker logs)"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "scheduler", "--tail", str(lines)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/app"  # docker compose가 실행되는 위치
        )
        logs = result.stdout or result.stderr
        
        # 로그를 줄 단위로 파싱
        log_lines = []
        for line in logs.split('\n'):
            if 'scheduler-1' in line:
                # "scheduler-1  | " 제거
                clean_line = line.split('|', 1)[-1].strip() if '|' in line else line
                log_lines.append(clean_line)
        
        return {
            "success": True, 
            "logs": log_lines[-lines:],  # 최근 N줄
            "total_lines": len(log_lines)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "로그 조회 타임아웃", "logs": []}
    except Exception as e:
        return {"success": False, "message": str(e), "logs": []}


@router.get("/scheduler-status")
async def get_scheduler_status():
    """스케줄러 상태 조회"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "scheduler", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/app"
        )
        
        import json as json_lib
        if result.stdout:
            try:
                status_data = json_lib.loads(result.stdout)
                return {
                    "success": True,
                    "running": True,
                    "status": status_data
                }
            except:
                return {"success": True, "running": "scheduler" in result.stdout, "status": result.stdout}
        
        return {"success": True, "running": False, "status": None}
    except Exception as e:
        return {"success": False, "message": str(e), "running": False}


@router.post("/reset-submissions")
async def reset_submissions(admin=Depends(require_admin)):
    """제출 기록 초기화 및 XP 리셋"""
    try:
        with postgres_connection() as pg:
            pg.execute("TRUNCATE TABLE submissions RESTART IDENTITY")
            pg.execute("UPDATE users SET xp = 0, level = 1")
        
        return {
            "success": True,
            "message": "모든 제출 기록이 초기화되었습니다."
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"초기화 실패: {str(e)}"
        }

@router.get("/logs")
async def get_system_logs(
    admin=Depends(require_admin),
    category: Optional[str] = Query(None, description="로그 카테고리"),
    level: Optional[str] = Query(None, description="로그 레벨"),
    limit: int = Query(100, description="조회 개수")
):
    """시스템 로그 조회"""
    logs = get_logs(category=category, level=level, limit=limit)
    return {
        "success": True,
        "logs": logs,
        "count": len(logs)
    }


@router.get("/log-categories")
async def get_log_categories(admin=Depends(require_admin)):
    """로그 카테고리 목록"""
    return {
        "categories": [
            {"id": "problem_generation", "name": "문제 생성", "icon": "🤖"},
            {"id": "user_action", "name": "사용자 액션", "icon": "👤"},
            {"id": "scheduler", "name": "스케줄러", "icon": "⏰"},
            {"id": "system", "name": "시스템", "icon": "🖥️"},
            {"id": "api", "name": "API", "icon": "🔌"}
        ]
    }


@router.get("/users")
async def get_all_users(admin=Depends(require_admin)):
    """전체 사용자 목록 조회"""
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df("""
                SELECT id, email, name, nickname, xp, level, is_admin, created_at
                FROM users
                ORDER BY created_at DESC
            """)
            users = []
            for _, row in df.iterrows():
                users.append({
                    "id": row["id"],
                    "email": row["email"],
                    "name": row["name"],
                    "nickname": row["nickname"],
                    "xp": int(row.get("xp", 0)),
                    "level": int(row.get("level", 1)),
                    "is_admin": bool(row.get("is_admin", False)),
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            return {"success": True, "users": users, "count": len(users)}
    except Exception as e:
        return {"success": False, "message": str(e), "users": []}


@router.patch("/users/{user_id}/admin")
async def toggle_user_admin(user_id: str, admin=Depends(require_admin)):
    """사용자 관리자 권한 토글"""
    try:
        with postgres_connection() as pg:
            # 현재 상태 조회
            df = pg.fetch_df("SELECT is_admin FROM users WHERE id = %s", [user_id])
            if len(df) == 0:
                return {"success": False, "message": "사용자를 찾을 수 없습니다"}
            
            current_admin = bool(df.iloc[0].get("is_admin", False))
            new_admin = not current_admin
            
            pg.execute("UPDATE users SET is_admin = %s WHERE id = %s", [new_admin, user_id])
            
            db_log(
                category=LogCategory.SYSTEM,
                message=f"사용자 관리자 권한 변경: {user_id} -> {'관리자' if new_admin else '일반'}",
                level=LogLevel.INFO,
                source="admin_api"
            )
            
            return {"success": True, "is_admin": new_admin}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin=Depends(require_admin)):
    """사용자 삭제"""
    try:
        with postgres_connection() as pg:
            pg.execute("DELETE FROM submissions WHERE user_id = %s", [user_id])
            pg.execute("DELETE FROM user_problem_sets WHERE user_id = %s", [user_id])
            pg.execute("DELETE FROM users WHERE id = %s", [user_id])
            
            db_log(
                category=LogCategory.SYSTEM,
                message=f"사용자 삭제: {user_id}",
                level=LogLevel.WARNING,
                source="admin_api"
            )
            
            return {"success": True, "message": "사용자가 삭제되었습니다"}
    except Exception as e:
        return {"success": False, "message": str(e)}
