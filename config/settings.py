# config/settings.py
"""
프로젝트 전역 설정 모듈
- 환경 변수 기반 설정
- 보안: API 키는 환경 변수로만 관리
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Database 설정
# ============================================================

# DuckDB (상태/로그/대시보드)
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", "data/pa_lab.duckdb"))

# PostgreSQL DSN (config/db.py의 PostgresEnv 클래스 사용 권장)
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "host=localhost port=5432 user=pa_lab password=pa_lab dbname=pa_lab",
)

# ============================================================
# Gemini API 설정
# ============================================================
USE_GEMINI = os.getenv("USE_GEMINI", "0") == "1"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# API 키 환경 변수 검증
if USE_GEMINI and not GEMINI_API_KEY:
    raise ValueError("USE_GEMINI=1이지만 GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

# ============================================================
# 기타 설정
# ============================================================
DEFAULT_VIEW_NAME = os.getenv("DEFAULT_VIEW_NAME", "my_answer")
PROBLEM_STORE = os.getenv("PROBLEM_STORE", "problems/pa_daily")
