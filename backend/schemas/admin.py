# backend/schemas/admin.py
"""관리자 관련 스키마"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SchedulerStatus(BaseModel):
    """스케줄러 상태"""
    session_date: str
    status: str
    generated_at: Optional[datetime] = None
    problem_set_path: Optional[str] = None


class DatabaseTable(BaseModel):
    """데이터베이스 테이블 정보"""
    table_name: str
    row_count: int
    column_count: int


class TodayProblemsStatus(BaseModel):
    """오늘의 문제 현황"""
    exists: bool
    count: int = 0
    difficulties: Optional[Dict[str, int]] = None
    path: Optional[str] = None


class SystemStatus(BaseModel):
    """시스템 상태"""
    postgres_connected: bool
    duckdb_connected: bool
    tables: List[DatabaseTable]
    scheduler_sessions: List[SchedulerStatus]
    today_problems: Optional[TodayProblemsStatus] = None



class GenerateProblemsRequest(BaseModel):
    """문제 생성 요청"""
    data_type: str = "pa"  # pa | stream
    force: bool = False


class GenerateProblemsResponse(BaseModel):
    """문제 생성 응답"""
    success: bool
    message: str
    path: Optional[str] = None
    problem_count: Optional[int] = None


class RefreshDataRequest(BaseModel):
    """데이터 갱신 요청"""
    data_type: str = "pa"  # pa | stream


class RefreshDataResponse(BaseModel):
    """데이터 갱신 응답"""
    success: bool
    message: str
