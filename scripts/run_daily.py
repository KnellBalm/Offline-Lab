# scripts/run_daily.py
"""
일일 데이터 생성 및 문제 출제 스케줄러
- Docker 컨테이너에서 상시 실행
- 매일 자정에 데이터 생성
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
import os

from dotenv import load_dotenv
load_dotenv()

from engine.postgres_engine import PostgresEngine
from engine.duckdb_engine import DuckDBEngine
from generator.data_generator_advanced import generate_data
from config.db import PostgresEnv

from common.logging import get_logger
logger = get_logger(__name__)

# -------------------------------------------------
# 환경 변수
# -------------------------------------------------
STREAM_REFRESH_WEEKDAY = int(os.getenv("STREAM_REFRESH_WEEKDAY", "6"))  # Sunday = 6
RUN_INTERVAL_HOURS = int(os.getenv("RUN_INTERVAL_HOURS", "24"))


def run_daily_pipeline():
    """일일 파이프라인 실행"""
    today = date.today()
    weekday = today.weekday()

    logger.info(f"[START] Daily pipeline for {today}")

    pg = PostgresEngine(PostgresEnv().dsn())
    duck = DuckDBEngine("data/pa_lab.duckdb")

    # DuckDB 스키마 초기화
    try:
        duck.execute(open("sql/init_duckdb.sql").read())
    except FileNotFoundError:
        logger.warning("[WARN] sql/init_duckdb.sql not found, skipping")

    # ---------------------------------------------
    # 1. 전날 세션 자동 SKIPPED 처리
    # ---------------------------------------------
    duck.execute(
        """
        UPDATE daily_sessions
        SET status='SKIPPED', finished_at=now()
        WHERE session_date = ?
          AND status IN ('GENERATED','STARTED')
        """,
        [(today - timedelta(days=1)).isoformat()],
    )

    # ---------------------------------------------
    # 2. 오늘 세션 이미 있으면 종료
    # ---------------------------------------------
    if duck.exists("daily_sessions", session_date=today.isoformat()):
        logger.info("[INFO] today's session already exists")
        pg.close()
        duck.close()
        return

    # ---------------------------------------------
    # 3. PA 데이터는 매일 생성
    # ---------------------------------------------
    logger.info("[INFO] generating PA data (daily)")
    try:
        generate_data(modes=("pa",))
    except Exception as e:
        logger.error(f"[ERROR] PA data generation failed: {e}")

    # ---------------------------------------------
    # 4. Stream 데이터는 주 1회만 생성
    # ---------------------------------------------
    if weekday == STREAM_REFRESH_WEEKDAY:
        logger.info("[INFO] generating STREAM data (weekly)")
        try:
            generate_data(modes=("stream",))
        except Exception as e:
            logger.error(f"[ERROR] Stream data generation failed: {e}")
    else:
        logger.info("[INFO] skipping STREAM generation today")

    # ---------------------------------------------
    # 5. 문제 생성 (Gemini API)
    # ---------------------------------------------
    logger.info("[INFO] generating problems")
    try:
        from problems.generator import generate as gen_problems
        problem_path = gen_problems(today, pg)
        logger.info(f"[INFO] problems saved to {problem_path}")
    except Exception as e:
        logger.error(f"[ERROR] Problem generation failed: {e}")
        problem_path = None

    # ---------------------------------------------
    # 6. 세션 기록
    # ---------------------------------------------
    duck.insert("daily_sessions", {
        "session_date": today.isoformat(),
        "problem_set_path": problem_path,
        "generated_at": datetime.now(),
        "status": "GENERATED"
    })

    pg.close()
    duck.close()
    logger.info("[DONE] daily pipeline completed")


def run_scheduler():
    """스케줄러 루프 - Docker 컨테이너에서 상시 실행"""
    logger.info(f"[SCHEDULER] Starting with {RUN_INTERVAL_HOURS}h interval")
    
    # 시작 시 데이터/문제 체크 및 초기화
    check_and_init_on_startup()
    
    while True:
        try:
            run_daily_pipeline()
        except Exception as e:
            logger.error(f"[SCHEDULER] Pipeline error: {e}")
        
        # 다음 실행까지 대기
        logger.info(f"[SCHEDULER] Sleeping for {RUN_INTERVAL_HOURS} hours")
        time.sleep(RUN_INTERVAL_HOURS * 3600)


def check_and_init_on_startup():
    """시작 시 데이터/문제 체크 및 초기화"""
    today = date.today()
    logger.info(f"[STARTUP] Checking data and problems for {today}")
    
    pg = PostgresEngine(PostgresEnv().dsn())
    
    # 1. PA 데이터 체크
    try:
        df = pg.fetch_df("SELECT COUNT(*) as cnt FROM pa_users")
        pa_count = int(df.iloc[0]["cnt"])
        logger.info(f"[STARTUP] PA users count: {pa_count}")
        
        if pa_count == 0:
            logger.info("[STARTUP] PA data missing, generating...")
            generate_data(modes=("pa",))
            logger.info("[STARTUP] PA data generated")
    except Exception as e:
        logger.warning(f"[STARTUP] PA data check failed: {e}, generating...")
        try:
            generate_data(modes=("pa",))
        except Exception as e2:
            logger.error(f"[STARTUP] PA data generation failed: {e2}")
    
    # 2. 오늘 문제 체크
    problem_path = f"problems/daily/{today.isoformat()}.json"
    if not os.path.exists(problem_path):
        logger.info(f"[STARTUP] Today's problems missing, generating...")
        try:
            from problems.generator import generate as gen_problems
            gen_problems(today, pg)
            logger.info(f"[STARTUP] Problems generated: {problem_path}")
        except Exception as e:
            logger.error(f"[STARTUP] Problem generation failed: {e}")
    else:
        logger.info(f"[STARTUP] Today's problems exist: {problem_path}")
    
    pg.close()
    logger.info("[STARTUP] Initialization complete")


if __name__ == "__main__":
    run_scheduler()

