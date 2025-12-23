# problems/prompt.py
"""
문제 생성 래퍼 - generator.py에서 호출
prompt_pa와 gemini 모듈을 연결
"""
from __future__ import annotations

from engine.postgres_engine import PostgresEngine
from config.db import PostgresEnv
from problems.prompt_pa import build_pa_prompt
from problems.gemini import call_gemini_json
from common.logging import get_logger

logger = get_logger(__name__)


def get_data_summary() -> str:
    """현재 PA 데이터 요약 생성"""
    pg = PostgresEngine(PostgresEnv().dsn())
    
    try:
        # 테이블별 row count
        tables = ["users", "sessions", "events", "orders"]
        summary_lines = ["## 테이블 구조"]
        
        for table in tables:
            try:
                count = pg.fetch_one(f"SELECT COUNT(*) FROM {table}")[0]
                summary_lines.append(f"- {table}: {count:,}건")
            except Exception:
                summary_lines.append(f"- {table}: 조회 불가")
        
        # 이벤트 유형
        try:
            event_types = pg.fetch_all(
                "SELECT DISTINCT event_type FROM events LIMIT 10"
            )
            summary_lines.append(f"\n## 이벤트 유형")
            summary_lines.append(", ".join([e[0] for e in event_types]))
        except Exception:
            pass
        
        return "\n".join(summary_lines)
    finally:
        pg.close()


def build_prompt() -> list[dict]:
    """
    generator.py에서 호출하는 메인 함수
    1. 데이터 요약 생성
    2. 프롬프트 빌드
    3. Gemini 호출
    4. JSON 파싱 후 반환
    """
    logger.info("building PA problems prompt")
    
    data_summary = get_data_summary()
    logger.info(f"data summary generated:\n{data_summary}")
    
    prompt = build_pa_prompt(data_summary, n=6)
    logger.info("calling Gemini for problem generation")
    
    problems = call_gemini_json(prompt)
    logger.info(f"received {len(problems)} problems from Gemini")
    
    return problems
