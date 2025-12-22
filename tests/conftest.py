# tests/conftest.py
"""
pytest 공통 fixture 및 설정
"""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_duckdb_path():
    """임시 DuckDB 파일 경로 생성"""
    import uuid
    path = f"/tmp/test_duckdb_{uuid.uuid4().hex}.duckdb"
    yield path
    # 테스트 후 정리
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_problem():
    """테스트용 샘플 문제"""
    return {
        "problem_id": "test_001",
        "difficulty": "easy",
        "question": "사용자 수를 조회하세요",
        "sort_keys": ["user_id"]
    }
