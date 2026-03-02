# backend/main.py
"""
QueryCraft - FastAPI Backend
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.middleware import PathRewriteMiddleware, ExceptionHandlingMiddleware, CORSLoggingMiddleware
from backend.api.problems import router as problems_router
from backend.api.sql import router as sql_router
from backend.api.stats import router as stats_router
from backend.api.admin import router as admin_router
from backend.api.auth import router as auth_router
from backend.api.practice import router as practice_router
from backend.api.health import router as health_router
from backend.api.daily import router as daily_router  # Daily Challenge (NEW)

# 초기화 상태 기록
init_status = {"initialized": False, "error": None}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명 주기 관리 - DB 초기화 및 스케줄러 시작/중지"""
    import threading
    
    # DB 초기화 (백그라운드에서 실행 - 서버 시작 블로킹 방지)
    def init_background():
        global init_status
        try:
            from backend.services.db_init import init_database
            success, error_msg = init_database()
            if success:
                init_status["initialized"] = True
                print("[INFO] Database initialized successfully")
            else:
                init_status["error"] = error_msg or "Unknown error during initialization"
        except Exception as e:
            error_msg = f"Critical failure in init thread: {str(e)}"
            init_status["error"] = error_msg
            print(f"[WARNING] {error_msg}")
    
    threading.Thread(target=init_background, daemon=True).start()
    
    # 스케줄러 시작 (ENABLE_SCHEDULER=true일 때만)
    # GCP Cloud Run에서는 APScheduler 대신 Cloud Scheduler 사용
    # APScheduler는 로컬 환경 또는 stateful 서버에서만 사용
    scheduler_started = False
    should_start_scheduler = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"
    
    if should_start_scheduler:
        try:
            from backend.scheduler import start_scheduler
            
            def start_scheduler_background():
                import time
                time.sleep(5)  # DB 초기화 및 테이블 생성이 완료될 때까지 대기
                try:
                    start_scheduler()
                    print("[INFO] Scheduler started in background")
                except Exception as e:
                    print(f"[WARNING] Scheduler start failed: {e}")
            
            threading.Thread(target=start_scheduler_background, daemon=True).start()
            scheduler_started = True
        except Exception as e:
            print(f"[WARNING] Scheduler module import failed: {e}")

    # Log CORS Configuration
    print(f"[INFO] CORS Config - ENV: {os.getenv('ENV', 'development')}")
    print(f"[INFO] CORS Config - Allowed Origins: {cloud_origins}")
    print(f"[INFO] CORS Config - Origin Regex: {cloud_origin_regex}")
    
    yield
    
    if scheduler_started:
        try:
            from backend.scheduler import stop_scheduler
            stop_scheduler()
        except:
            pass


app = FastAPI(
    title="QueryCraft API",
    description="AI 기반 SQL 학습 플랫폼 API",
    version="1.0.0",
    lifespan=lifespan
)

# PathRewriteMiddleware 등록 (CORS보다 먼저 등록하여 안쪽에 위치하게 함 -> CORS가 바깥쪽에서 먼저 실행됨)
# 순서: Request -> CORS -> PathRewrite -> Router
app.add_middleware(PathRewriteMiddleware)

# Exception handling middleware - catch exceptions before they crash the server,
# ensuring CORS headers are added by the outer CORS middleware.
app.add_middleware(ExceptionHandlingMiddleware)

# CORS 설정 - 환경별 분리
# Cloud Run 도메인 및 Regex 정의 (환경 무관하게 참조 가능하도록)
cloud_origins = [
    "https://query-craft-frontend-53ngedkhia-uc.a.run.app",
    "https://query-craft-frontend-758178119666.us-central1.run.app",
    "https://query-craft-frontend-758178119666.a.run.app", # 추가
    "https://querycraft.run.app",  # 커스텀 도메인 예비
]
# 좀 더 유연한 regex: query-craft-frontend로 시작하는 모든 .run.app 도메인 허용
cloud_origin_regex = r"https?://query-craft-frontend.*\.run\.app"

if os.getenv("ENV") == "production":
    # 프로덕션: Cloud Run 도메인 허용 (여러 형식 지원)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cloud_origins,
        allow_origin_regex=cloud_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

else:
    # 개발: localhost 및 개발서버 IP 허용 + Cloud Run 도메인 (설정 실수 대비)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:15173", 
            "http://127.0.0.1:15173", 
            "http://localhost:3000",
            "http://192.168.101.224:15173",  # 개발서버 IP
        ] + cloud_origins,
        allow_origin_regex=cloud_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# CORS Logging Middleware (wraps CORSMiddleware to verify headers)
app.add_middleware(CORSLoggingMiddleware)
    
# 404 및 기타 에러 로깅 미들웨어
@app.middleware("http")
async def log_errors_middleware(request, call_next):
    from fastapi import Request
    from starlette.responses import Response
    
    response = await call_next(request)
    
    if response.status_code == 404:
        from backend.common.logging import get_logger
        logger = get_logger("backend.main.404")
        full_url = str(request.url)
        logger.warning(f"404 Not Found: {request.method} {full_url} (Referer: {request.headers.get('referer', 'N/A')})")
        
    return response

# 라우터 등록 (순서 중요: /problems/recommend 보다 먼저 등록)
app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(daily_router, prefix="/api")  # Daily Challenge (NEW)
app.include_router(sql_router, prefix="/api")
app.include_router(problems_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(practice_router, prefix="/api")

@app.get("/")
async def root():
    """기본 루트 - 서비스 상태 및 DB 정보 요약"""
    db_status = "unknown"
    tables = []
    try:
        from backend.services.database import postgres_connection
        with postgres_connection() as pg:
            db_status = "connected"
            df = pg.fetch_df("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = df["table_name"].tolist()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "service": "QueryCraft API",
        "version": "1.0.0",
        "init": init_status,
        "db": {
            "status": db_status,
            "table_count": len(tables),
            "tables": tables[:10]
        }
    }


@app.get("/health")
async def health():
    """상세 헬스 체크"""
    try:
        from backend.services.database import postgres_connection
        with postgres_connection() as pg:
            pg.execute("SELECT 1")
        return {
            "status": "healthy", 
            "db": "connected",
            "init": init_status
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "db": str(e),
            "init": init_status
        }
