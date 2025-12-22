# dashboard/app.py
import json
from datetime import date
import streamlit as st

from config.db import get_duckdb_path
from engine.duckdb_engine import DuckDBEngine
from services.pa_submit import submit_pa
from common.logging import get_logger

logger = get_logger(__name__)


def get_duck():
    """DuckDB 연결 생성 (동시 접근 문제 방지)"""
    return DuckDBEngine(get_duckdb_path())


today = date.today().isoformat()

st.title("📊 Offline Analytics Lab")

tab1, tab2 = st.tabs(["🧠 PA 연습", "📊 Stream 로그 분석"])

# ==================================================
# PA 연습 탭
# ==================================================
with tab1:
    st.header("🧠 PA 쿼리 연습")

    problem_path = f"problems/pa_daily/{today}.json"

    try:
        with open(problem_path, encoding="utf-8") as f:
            problems = json.load(f)
        logger.info(f"loaded {len(problems)} pa problems from {problem_path}")
    except FileNotFoundError:
        st.info("오늘 생성된 PA 문제가 없습니다.")
        st.stop()

    problem_ids = [p["problem_id"] for p in problems]
    problem_map = {p["problem_id"]: p for p in problems}

    selected_problem_id = st.selectbox(
        "문제 선택",
        problem_ids,
        format_func=lambda x: f"{x} ({problem_map[x]['difficulty']})"
    )

    p = problem_map[selected_problem_id]

    st.markdown(f"### 📌 문제 설명 ({p['difficulty']})")
    st.write(p["question"])

    st.markdown("### ✍️ SQL 제출")
    sql_text = st.text_area(
        "DBeaver에서 작성한 SQL을 그대로 붙여넣으세요",
        height=300,
        placeholder="SELECT ..."
    )

    note = st.text_area(
        "해석 / 접근 방법 (선택)",
        height=120,
        placeholder="어떤 기준으로 풀었는지 간단히 정리"
    )

    if st.button("🚀 제출"):
        if not sql_text.strip():
            st.warning("SQL이 비어 있습니다.")
        else:
            with st.spinner("채점 중입니다..."):
                try:
                    result = submit_pa(
                        problem_id=selected_problem_id,
                        sql_text=sql_text,
                        note=note,
                        session_date=today
                    )
                except Exception as e:
                    logger.exception("PA submission failed")
                    st.error(f"제출 처리 중 오류 발생: {e}")
                else:
                    if result["is_correct"]:
                        st.success("✅ 정답입니다!")
                    else:
                        st.error("❌ 오답입니다.")

                    st.markdown("### 🤖 Gemini 피드백")
                    st.write(result["feedback"])

# ==================================================
# Stream 로그 분석 탭
# ==================================================
with tab2:
    st.header("📊 Stream 로그 분석 업무 요청")

    path = f"problems/stream_daily/{today}.json"

    try:
        with open(path, encoding="utf-8") as f:
            tasks = json.load(f)
        logger.info(f"loaded {len(tasks)} stream tasks from {path}")
    except FileNotFoundError:
        st.info("오늘 생성된 로그 분석 업무 요청이 없습니다.")
        st.stop()

    # 제출 상태 조회
    duck = get_duck()
    try:
        submitted = duck.fetchall(
            "SELECT problem_id FROM stream_submissions WHERE session_date=?",
            [today]
        )
    finally:
        duck.close()
    submitted_ids = {r["problem_id"] for r in submitted}

    for t in tasks:
        st.markdown(f"## 🧾 업무 요청: {t['task_id']}")
        st.caption(f"{t['domain']} · {t['difficulty']}")

        st.markdown("### 📌 배경")
        st.write(t["context"])

        st.markdown("### 📌 요청 사항")
        for r in t["request"]:
            st.write(f"- {r}")

        st.markdown("### 📌 제약 조건")
        for c in t["constraints"]:
            st.write(f"- {c}")

        st.markdown("### 📌 기대 산출물")
        for d in t["deliverables"]:
            st.write(f"- {d}")

        if t["task_id"] in submitted_ids:
            st.success("업무 완료 처리됨")
        else:
            if st.button(f"업무 완료 처리: {t['task_id']}"):
                duck = get_duck()
                try:
                    duck.execute(
                        """
                        INSERT INTO stream_submissions (session_date, problem_id, submitted_at)
                        VALUES (?, ?, now())
                        """,
                        [today, t["task_id"]]
                    )
                finally:
                    duck.close()
                st.success("업무 완료로 기록되었습니다")
                st.rerun()

