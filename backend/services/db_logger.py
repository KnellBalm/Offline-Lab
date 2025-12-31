# backend/services/db_logger.py
"""중앙 집중식 로깅 서비스 - DB에 로그 저장"""
from datetime import datetime
from typing import Optional
from backend.services.database import postgres_connection
from common.logging import get_logger

logger = get_logger(__name__)

# 로그 카테고리
class LogCategory:
    PROBLEM_GENERATION = "problem_generation"  # 문제 생성/적재
    USER_ACTION = "user_action"                # 사용자 행동
    SCHEDULER = "scheduler"                    # 스케줄러 동작
    SYSTEM = "system"                          # 시스템 상태/에러
    API = "api"                                # API 요청


# 로그 레벨
class LogLevel:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


def ensure_logs_table():
    """logs 테이블 생성"""
    try:
        with postgres_connection() as pg:
            pg.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id SERIAL PRIMARY KEY,
                    category VARCHAR(50) NOT NULL,
                    level VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    source VARCHAR(100),
                    user_id VARCHAR(100),
                    extra_data TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # 인덱스 생성
            pg.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(category)
            """)
            pg.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at DESC)
            """)
    except Exception as e:
        logger.error(f"Failed to create logs table: {e}")


def db_log(
    category: str,
    message: str,
    level: str = LogLevel.INFO,
    source: str = None,
    user_id: str = None,
    extra_data: str = None
):
    """DB에 로그 저장"""
    try:
        with postgres_connection() as pg:
            pg.execute("""
                INSERT INTO logs (category, level, message, source, user_id, extra_data)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (category, level, message, source, user_id, extra_data))
        
        # 콘솔에도 출력
        log_msg = f"[{category}/{level}] {message}"
        if level == LogLevel.ERROR:
            logger.error(log_msg)
        elif level == LogLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    except Exception as e:
        logger.error(f"Failed to save log to DB: {e}")


def get_logs(
    category: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100
) -> list:
    """로그 조회"""
    try:
        with postgres_connection() as pg:
            conditions = []
            params = []
            
            if category:
                conditions.append("category = %s")
                params.append(category)
            if level:
                conditions.append("level = %s")
                params.append(level)
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            params.append(limit)
            
            df = pg.fetch_df(f"""
                SELECT id, category, level, message, source, user_id, extra_data, created_at
                FROM logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """, params)
            
            logs = []
            for _, row in df.iterrows():
                logs.append({
                    "id": int(row["id"]),
                    "category": row["category"],
                    "level": row["level"],
                    "message": row["message"],
                    "source": row["source"],
                    "user_id": row["user_id"],
                    "extra_data": row["extra_data"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            return logs
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        return []


# 시작 시 테이블 생성
ensure_logs_table()
