import json
from engine.postgres_engine import PostgresEngine
from engine.duckdb_engine import DuckDBEngine
from grader.grader import grade
from config.settings import PROBLEM_STORE

engine = DuckDBEngine()  # or PostgresEngine()

with open(PROBLEM_STORE) as f:
    problem = json.load(f)

print(problem["problem_markdown"])
print("\nSQL을 입력하세요:")
sql = input(">>> ")

user = engine.execute(sql)
answer = engine.execute(problem["answer_sql"])

ok, msg = grade(user, answer)
print(msg)
