CREATE TABLE IF NOT EXISTS stream_submissions (
    session_date DATE,
    problem_id TEXT,
    submitted_at TIMESTAMP,
    PRIMARY KEY (session_date, problem_id)
);

CREATE TABLE IF NOT EXISTS daily_sessions (
    session_date DATE PRIMARY KEY,
    problem_set_path TEXT,
    generated_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT DEFAULT 'GENERATED'
);
