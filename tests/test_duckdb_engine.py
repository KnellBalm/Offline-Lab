# tests/test_duckdb_engine.py
"""
DuckDBEngine 단위 테스트
"""
import pytest
from engine.duckdb_engine import (
    DuckDBEngine, 
    ALLOWED_TABLES, 
    _validate_identifier, 
    _validate_table
)


class TestValidation:
    """SQL Injection 방어 검증 테스트"""
    
    def test_validate_identifier_valid(self):
        """유효한 식별자는 통과해야 함"""
        _validate_identifier("user_id")
        _validate_identifier("session_date")
        _validate_identifier("_private")
        _validate_identifier("Column123")
    
    def test_validate_identifier_invalid(self):
        """유효하지 않은 식별자는 ValueError 발생"""
        with pytest.raises(ValueError):
            _validate_identifier("DROP TABLE users; --")
        with pytest.raises(ValueError):
            _validate_identifier("column name")  # 공백 포함
        with pytest.raises(ValueError):
            _validate_identifier("123column")  # 숫자로 시작
        with pytest.raises(ValueError):
            _validate_identifier("col;umn")  # 특수문자 포함
    
    def test_validate_table_allowed(self):
        """허용된 테이블은 통과해야 함"""
        for table in ALLOWED_TABLES:
            _validate_table(table)
    
    def test_validate_table_not_allowed(self):
        """허용되지 않은 테이블은 ValueError 발생"""
        with pytest.raises(ValueError):
            _validate_table("users")
        with pytest.raises(ValueError):
            _validate_table("malicious_table")


class TestDuckDBEngine:
    """DuckDBEngine 기본 기능 테스트"""
    
    def test_init_creates_schema(self, temp_duckdb_path):
        """초기화 시 스키마가 생성되어야 함"""
        engine = DuckDBEngine(temp_duckdb_path)
        
        # daily_sessions 테이블 존재 확인
        result = engine.fetchone("SELECT 1 FROM daily_sessions LIMIT 1")
        # 빈 테이블이므로 None 반환
        assert result is None
        
        engine.close()
    
    def test_insert_and_exists(self, temp_duckdb_path):
        """insert 및 exists 메서드 테스트"""
        engine = DuckDBEngine(temp_duckdb_path)
        
        # 데이터 삽입
        engine.insert("daily_sessions", {
            "session_date": "2024-01-01",
            "status": "PENDING"
        })
        
        # exists 확인
        assert engine.exists("daily_sessions") is True
        assert engine.exists("daily_sessions", session_date="2024-01-01") is True
        assert engine.exists("daily_sessions", session_date="2024-01-02") is False
        
        engine.close()
    
    def test_fetchall(self, temp_duckdb_path):
        """fetchall 메서드 테스트"""
        engine = DuckDBEngine(temp_duckdb_path)
        
        engine.insert("daily_sessions", {"session_date": "2024-01-01", "status": "A"})
        engine.insert("daily_sessions", {"session_date": "2024-01-02", "status": "B"})
        
        rows = engine.fetchall("SELECT * FROM daily_sessions ORDER BY session_date")
        assert len(rows) == 2
        assert rows[0]["session_date"].isoformat() == "2024-01-01"
        assert rows[1]["session_date"].isoformat() == "2024-01-02"
        
        engine.close()
    
    def test_insert_blocked_table(self, temp_duckdb_path):
        """허용되지 않은 테이블 insert 시 오류 발생"""
        engine = DuckDBEngine(temp_duckdb_path)
        
        with pytest.raises(ValueError, match="허용되지 않은 테이블"):
            engine.insert("users", {"id": 1})
        
        engine.close()
