# backend/main.py
"""
SQL Analytics Lab - FastAPI Backend
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.problems import router as problems_router
from backend.api.sql import router as sql_router
from backend.api.stats import router as stats_router
from backend.api.admin import router as admin_router
from backend.api.auth import router as auth_router
from backend.api.practice import router as practice_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명 주기 관리 - 스케줄러 시작/중지"""
    # 스케줄러 시작 (환경변수로 활성화)
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        from backend.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
        yield
        stop_scheduler()
    else:
        yield


app = FastAPI(
    title="SQL Analytics Lab API",
    description="AI 기반 SQL 학습 플랫폼 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 - 모든 origin 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(problems_router)
app.include_router(sql_router)
app.include_router(stats_router)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(practice_router)


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "status": "ok",
        "service": "SQL Analytics Lab API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy"}
