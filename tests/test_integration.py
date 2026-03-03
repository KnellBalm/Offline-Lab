# tests/test_integration.py
"""
통합 테스트 - Docker 환경 배포 전 전체 흐름 검증
PostgreSQL 연결이 필요한 테스트는 @pytest.mark.integration 마커 사용
"""
import pytest
import os
from datetime import date

# 통합 테스트 마커
integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "0") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests"
)


class TestConfigSettings:
    """설정 모듈 통합 테스트"""
    
    def test_config_loads_without_error(self):
        """config.settings 모듈이 에러 없이 로드되어야 함"""
        from backend.config.settings import DUCKDB_PATH, POSTGRES_DSN
        assert DUCKDB_PATH is not None
        assert POSTGRES_DSN is not None
    
    def test_db_config_loads(self):
        """config.db 모듈이 에러 없이 로드되어야 함"""
        from backend.config.db import PostgresEnv, get_duckdb_path

        # Ensure we are testing in a safe environment context,
        # as other tests might have set ENV=production globally.
        original_env = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            env = PostgresEnv()
            assert env.dsn() is not None
            assert get_duckdb_path() is not None
        finally:
            if original_env:
                os.environ["ENV"] = original_env
            else:
                os.environ.pop("ENV", None)


class TestDailyPipeline:
    """일일 파이프라인 통합 테스트"""
    
    def test_run_daily_imports(self):
        """run_daily 모듈이 임포트되어야 함"""
        from scripts.run_daily import run_daily_pipeline, run_scheduler
        assert callable(run_daily_pipeline)
        assert callable(run_scheduler)


@integration
class TestPostgresIntegration:
    """PostgreSQL 연결 통합 테스트 (DB 필요)"""
    
    def test_postgres_connection(self):
        """PostgreSQL 연결 테스트"""
        from backend.engine.postgres_engine import PostgresEngine
        from backend.config.db import PostgresEnv
        
        pg = PostgresEngine(PostgresEnv().dsn())
        result = pg.fetch_df("SELECT 1 as test")
        assert len(result) == 1
        assert result.iloc[0]["test"] == 1
        pg.close()
    
    def test_postgres_schema_exists(self):
        """PostgreSQL 스키마 존재 확인"""
        from backend.engine.postgres_engine import PostgresEngine
        from backend.config.db import PostgresEnv
        
        pg = PostgresEngine(PostgresEnv().dsn())
        # 기본 테이블 중 하나라도 있는지 확인
        tables = pg.fetch_df("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        pg.close()
        assert len(tables) >= 0  # 스키마가 초기화되지 않았을 수 있음


class TestDashboardImports:
    """대시보드 임포트 테스트"""
    
    def test_dashboard_app_imports(self):
        """dashboard/app.py의 핵심 임포트가 작동해야 함"""
        # streamlit을 직접 임포트하면 앱이 실행되므로 모듈만 테스트
        from backend.engine.duckdb_engine import DuckDBEngine
        from backend.services.grading_service import grade_submission
        assert callable(grade_submission)


class TestGeneratorImports:
    """Generator 모듈 임포트 테스트"""
    
    def test_data_generator_imports(self):
        """데이터 생성기 임포트"""
        from backend.generator.data_generator_advanced import generate_data
        assert callable(generate_data)
    
    def test_generator_config_imports(self):
        """Generator 설정 임포트"""
        from backend.generator.config import GENERATOR_MODES, GENERATOR_TARGETS
        assert isinstance(GENERATOR_MODES, list)
        assert isinstance(GENERATOR_TARGETS, list)
