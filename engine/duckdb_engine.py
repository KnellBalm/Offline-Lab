# engine/duckdb_engine.py
from __future__ import annotations
import duckdb
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Iterable

# SQL Injection 방어: 허용된 테이블/컬럼명 정규식
_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# 허용된 테이블 목록 (화이트리스트)
ALLOWED_TABLES = {
    "daily_sessions", "submissions", "pa_submissions",
    "stream_submissions", "pa_answers"
}

def _validate_identifier(name: str, identifier_type: str = "identifier") -> None:
    """SQL 식별자(테이블명, 컬럼명) 유효성 검증"""
    if not _IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"유효하지 않은 {identifier_type}: {name}")

def _validate_table(table: str) -> None:
    """테이블명 화이트리스트 검증"""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"허용되지 않은 테이블: {table}. 허용 목록: {ALLOWED_TABLES}")

INIT_SQL = """
CREATE TABLE IF NOT EXISTS daily_sessions (
    session_date DATE PRIMARY KEY,
    data_version TEXT,
    problem_set_id TEXT,
    problem_set_path TEXT,
    generated_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT
);

CREATE TABLE IF NOT EXISTS submissions (
    session_date DATE,
    problem_id TEXT,
    difficulty TEXT,
    submitted_at TIMESTAMP,

    is_correct BOOLEAN,

    error_category TEXT,  -- ENGINE_ERROR | LOGIC_ERROR
    error_type TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS pa_submissions (
    session_date TEXT,
    problem_id TEXT,
    sql_text TEXT,
    is_correct BOOLEAN,
    feedback TEXT,
    submitted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stream_submissions (
    session_date TEXT,
    problem_id TEXT,
    submitted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pa_answers (
    problem_id TEXT PRIMARY KEY,
    answer_sql TEXT
);
"""

class DuckDBEngine:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        self.conn.execute(INIT_SQL)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        if params is None:
            self.conn.execute(sql)
        else:
            self.conn.execute(sql, params)

    def fetchone(self, sql: str, params: Iterable[Any] | None = None) -> dict | None:
        cur = self.conn.execute(sql, params) if params is not None else self.conn.execute(sql)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def fetchall(self, sql: str, params: Iterable[Any] | None = None) -> list[dict]:
        cur = self.conn.execute(sql, params) if params is not None else self.conn.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]

    def exists(self, table: str, **where) -> bool:
        _validate_table(table)
        for col in where.keys():
            _validate_identifier(col, "컬럼명")
        
        if not where:
            r = self.fetchone(f"SELECT 1 FROM {table} LIMIT 1")
            return r is not None
        cond = " AND ".join([f"{k} = ?" for k in where.keys()])
        params = list(where.values())
        r = self.fetchone(f"SELECT 1 FROM {table} WHERE {cond} LIMIT 1", params)
        return r is not None

    def insert(self, table: str, row: dict) -> None:
        _validate_table(table)
        cols = list(row.keys())
        for col in cols:
            _validate_identifier(col, "컬럼명")
        
        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        self.execute(sql, [row[c] for c in cols])

    def close(self):
        self.conn.close()
