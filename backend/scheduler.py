# backend/scheduler.py
"""백엔드 내장 스케줄러 - APScheduler 기반 (KST 9:00 = UTC 0:00)"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
import os
import glob

from common.logging import get_logger
from backend.services.db_logger import db_log, LogCategory, LogLevel

logger = get_logger(__name__)

scheduler = BackgroundScheduler()

# 보관 일수 (이전 문제 파일 및 정답 테이블)
RETENTION_DAYS = 30


def cleanup_old_data():
    """오래된 문제 파일과 정답 테이블 정리"""
    cutoff_date = date.today() - timedelta(days=RETENTION_DAYS)
    cutoff_month = (date.today() - timedelta(days=90)).strftime("%Y-%m")  # 3개월 전
    logger.info(f"[SCHEDULER] Cleaning up data older than {cutoff_date}")
    
    deleted_files = 0
    deleted_tables = 0
    
    try:
        # 1. 오래된 daily 문제 파일 삭제
        problem_files = glob.glob("problems/daily/*.json")
        for filepath in problem_files:
            filename = os.path.basename(filepath)
            try:
                if filename.startswith("stream_"):
                    date_str = filename[7:17]
                else:
                    date_str = filename[:10]
                
                file_date = date.fromisoformat(date_str)
                if file_date < cutoff_date:
                    os.remove(filepath)
                    deleted_files += 1
                    logger.info(f"[CLEANUP] Deleted old daily file: {filepath}")
            except (ValueError, IndexError):
                continue
        
        # 2. 오래된 monthly 파일 삭제 (3개월 이전)
        monthly_files = glob.glob("problems/monthly/*.json")
        for filepath in monthly_files:
            filename = os.path.basename(filepath)
            try:
                # pa_2025-12.json 또는 stream_2025-12.json 형식
                if filename.startswith("pa_"):
                    month_str = filename[3:10]  # pa_YYYY-MM
                elif filename.startswith("stream_"):
                    month_str = filename[7:14]  # stream_YYYY-MM
                else:
                    continue
                
                if month_str < cutoff_month:
                    os.remove(filepath)
                    deleted_files += 1
                    logger.info(f"[CLEANUP] Deleted old monthly file: {filepath}")
            except (ValueError, IndexError):
                continue
        
        # 3. 오래된 grading 테이블 삭제 (날짜 prefix가 있는 테이블)
        from backend.services.database import postgres_connection
        with postgres_connection() as pg:
            tables_df = pg.fetch_df("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'grading' AND table_name LIKE 'expected_%'
            """)
            
            for _, row in tables_df.iterrows():
                table_name = row["table_name"]
                # expected_2025-12-30_xxx 형식에서 날짜 추출
                try:
                    # expected_YYYY-MM-DD_... 형식
                    if len(table_name) > 19 and table_name[9:19].count("-") == 2:
                        date_str = table_name[9:19]  # expected_YYYY-MM-DD
                        table_date = date.fromisoformat(date_str)
                        if table_date < cutoff_date:
                            pg.execute(f"DROP TABLE IF EXISTS grading.{table_name}")
                            deleted_tables += 1
                            logger.info(f"[CLEANUP] Dropped old grading table: {table_name}")
                except (ValueError, IndexError):
                    continue
        
        if deleted_files > 0 or deleted_tables > 0:
            db_log(
                category=LogCategory.SCHEDULER,
                message=f"데이터 정리: {deleted_files}개 파일, {deleted_tables}개 테이블 삭제",
                level=LogLevel.INFO,
                source="scheduler"
            )
            logger.info(f"[CLEANUP] Deleted {deleted_files} files, {deleted_tables} tables")
        
    except Exception as e:
        logger.error(f"[CLEANUP] Error: {str(e)}")


def run_daily_problem_generation():
    """매일 문제 생성 작업"""
    # 컨테이너가 UTC 기준이므로, 한국 시간 기준 오늘 날짜 계산
    # UTC 0:00 = KST 9:00이므로 date.today()는 정확히 한국 날짜
    today = date.today()
    logger.info(f"[SCHEDULER] Starting daily problem generation for {today}")
    
    db_log(
        category=LogCategory.SCHEDULER,
        message=f"일일 문제 생성 시작: {today}",
        level=LogLevel.INFO,
        source="scheduler"
    )
    
    try:
        from engine.postgres_engine import PostgresEngine
        from config.db import PostgresEnv
        
        pg = PostgresEngine(PostgresEnv().dsn())
        
        # PA 문제 생성
        pa_problem_path = f"problems/daily/{today}.json"
        if not os.path.exists(pa_problem_path):
            logger.info("[SCHEDULER] Generating PA problems...")
            from problems.generator import generate as gen_pa_problems
            gen_pa_problems(today, pg)
            
            db_log(
                category=LogCategory.PROBLEM_GENERATION,
                message=f"PA 문제 생성 완료: {today}",
                level=LogLevel.INFO,
                source="scheduler"
            )
        else:
            logger.info(f"[SCHEDULER] PA problems already exist: {pa_problem_path}")
        
        # Stream 문제 생성
        stream_problem_path = f"problems/daily/stream_{today}.json"
        if not os.path.exists(stream_problem_path):
            logger.info("[SCHEDULER] Generating Stream problems...")
            from problems.generator_stream import generate_stream_problems
            generate_stream_problems(today, pg)
            
            db_log(
                category=LogCategory.PROBLEM_GENERATION,
                message=f"Stream 문제 생성 완료: {today}",
                level=LogLevel.INFO,
                source="scheduler"
            )
        else:
            logger.info(f"[SCHEDULER] Stream problems already exist: {stream_problem_path}")
        
        pg.close()
        
        # 오래된 데이터 정리
        cleanup_old_data()
        
        db_log(
            category=LogCategory.SCHEDULER,
            message=f"일일 문제 생성 완료: {today}",
            level=LogLevel.INFO,
            source="scheduler"
        )
        logger.info(f"[SCHEDULER] Daily problem generation completed for {today}")
        
    except Exception as e:
        error_msg = f"문제 생성 실패: {str(e)}"
        logger.error(f"[SCHEDULER] {error_msg}")
        db_log(
            category=LogCategory.SCHEDULER,
            message=error_msg,
            level=LogLevel.ERROR,
            source="scheduler"
        )


def start_scheduler():
    """스케줄러 시작 - UTC 0시 (= KST 9시)"""
    # 컨테이너는 UTC 기준, KST 9:00 = UTC 0:00
    run_hour = int(os.getenv("RUN_HOUR", "0"))  # 기본값 0 (= KST 9:00)
    
    scheduler.add_job(
        run_daily_problem_generation,
        CronTrigger(hour=run_hour, minute=0),
        id="daily_problem_generation",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"[SCHEDULER] Started - daily job at UTC {run_hour}:00 (KST {run_hour+9}:00)")
    
    db_log(
        category=LogCategory.SCHEDULER,
        message=f"스케줄러 시작됨 - 매일 KST {run_hour+9}:00 실행",
        level=LogLevel.INFO,
        source="scheduler"
    )
    
    # 시작 시 오늘 문제 체크
    run_daily_problem_generation()


def stop_scheduler():
    """스케줄러 중지"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[SCHEDULER] Stopped")
