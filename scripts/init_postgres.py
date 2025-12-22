# scripts/init_postgres.py
from engine.postgres_engine import PostgresEngine
from config.settings import POSTGRES_DSN

DDL = """
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  signup_at TIMESTAMP NOT NULL,
  country TEXT NOT NULL,
  channel TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  started_at TIMESTAMP NOT NULL,
  device TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  event_time TIMESTAMP NOT NULL,
  event_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  order_time TIMESTAMP NOT NULL,
  amount INTEGER NOT NULL
);

-- 인덱스(분석 쿼리용)
CREATE INDEX IF NOT EXISTS idx_users_signup_at ON users(signup_at);
CREATE INDEX IF NOT EXISTS idx_events_user_time ON events(user_id, event_time);
CREATE INDEX IF NOT EXISTS idx_events_name_time ON events(event_name, event_time);
CREATE INDEX IF NOT EXISTS idx_orders_user_time ON orders(user_id, order_time);
"""

def main():
    pg = PostgresEngine(POSTGRES_DSN)
    pg.execute(DDL)
    print("[DONE] Postgres schema initialized.")

if __name__ == "__main__":
    main()
