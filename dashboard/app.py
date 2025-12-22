# dashboard/app.py
"""
SQL Analytics Lab - 통합 워크스페이스
- PA 연습: 매일 갱신되는 프로덕트 분석 문제
- Stream 분석: 주간 갱신되는 로그 분석 문제
- 통합 화면: 문제 + SQL 에디터 + 테이블 구조
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd

from config.db import PostgresEnv, get_duckdb_path
from engine.duckdb_engine import DuckDBEngine
from engine.postgres_engine import PostgresEngine
from common.logging import get_logger

logger = get_logger(__name__)

# ============================================================
# 헬퍼 함수
# ============================================================

def get_duck():
    return DuckDBEngine(get_duckdb_path())

def get_pg():
    return PostgresEngine(PostgresEnv().dsn())

def is_safe_sql(sql: str) -> bool:
    clean = sql.strip().upper()
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    return not any(clean.startswith(k) for k in dangerous)

def run_query(sql: str, limit: int = 100):
    """쿼리 실행 (LIMIT 자동 처리)"""
    if not sql.strip():
        return None, "SQL이 비어 있습니다."
    if not is_safe_sql(sql):
        return None, "SELECT 문만 실행 가능합니다."
    
    try:
        pg = get_pg()
        query = sql.strip().rstrip(';')
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"
        df = pg.fetch_df(query)
        pg.close()
        return df, None
    except Exception as e:
        return None, str(e)

def get_streak_info():
    duck = get_duck()
    try:
        result = duck.fetchall("""
            SELECT DISTINCT session_date 
            FROM pa_submissions 
            ORDER BY session_date DESC 
            LIMIT 30
        """)
    except:
        result = []
    finally:
        duck.close()
    
    if not result:
        return {"current": 0, "max": 0}
    
    dates = [r["session_date"] for r in result]
    streak = 0
    check_date = date.today()
    for _ in range(30):
        if check_date.isoformat() in dates:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    return {"current": streak, "max": len(dates)}

def get_level_info():
    duck = get_duck()
    try:
        result = duck.fetchone("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM pa_submissions
        """)
    except:
        result = {"total": 0, "correct": 0}
    finally:
        duck.close()
    
    correct = result.get("correct", 0) or 0
    levels = [(0, "🌱 Beginner"), (5, "🌿 Learner"), (15, "🌳 Analyst"),
              (30, "⭐ Senior"), (50, "🏆 Expert"), (100, "👑 Master")]
    
    level_name = "🌱 Beginner"
    next_threshold = 5
    for threshold, name in levels:
        if correct >= threshold:
            level_name = name
        else:
            next_threshold = threshold
            break
    
    return {"name": level_name, "correct": correct, "next": next_threshold}

def get_table_schema(prefix: str = "pa_"):
    """특정 prefix로 시작하는 테이블 스키마 조회"""
    try:
        pg = get_pg()
        tables = pg.fetch_df(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '{prefix}%'
            ORDER BY table_name
        """)
        
        schema = {}
        for _, row in tables.iterrows():
            tbl = row["table_name"]
            cols = pg.fetch_df(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{tbl}' AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            schema[tbl] = cols.to_dict('records')
        
        pg.close()
        return schema
    except:
        return {}

# ============================================================
# 통합 워크스페이스 컴포넌트
# ============================================================

def render_workspace(data_type: str, problem_path: str, table_prefix: str):
    """통합 워크스페이스 렌더링 (문제 + SQL + 테이블구조)"""
    
    # 문제 로드
    try:
        with open(problem_path, encoding="utf-8") as f:
            problems = json.load(f)
    except FileNotFoundError:
        problems = None
    
    # 레이아웃: 좌측(문제+SQL) / 우측(테이블구조)
    col_main, col_schema = st.columns([3, 1])
    
    with col_schema:
        st.markdown("### � 테이블 구조")
        schema = get_table_schema(table_prefix)
        
        if not schema:
            st.info(f"{table_prefix}* 테이블이 없습니다.")
        else:
            for tbl, cols in schema.items():
                with st.expander(f"📁 {tbl}", expanded=False):
                    for c in cols:
                        st.caption(f"`{c['column_name']}` {c['data_type']}")
    
    with col_main:
        if not problems:
            st.info(f"📌 오늘 {data_type} 문제가 없습니다.")
            st.markdown("**SQL 연습장**으로 자유롭게 연습해보세요!")
            
            # 자유 SQL 모드
            sql = st.text_area("SQL 입력", height=200, key=f"{data_type}_free_sql",
                              placeholder="SELECT * FROM pa_users LIMIT 10;")
            
            if st.button("▶️ 실행", key=f"{data_type}_run"):
                df, err = run_query(sql)
                if err:
                    st.error(err)
                elif df is not None:
                    st.success(f"✅ {len(df)} 행")
                    st.dataframe(df, use_container_width=True)
            return
        
        # 문제 선택
        problem_ids = [p["problem_id"] for p in problems]
        problem_map = {p["problem_id"]: p for p in problems}
        
        # 완료 상태
        duck = get_duck()
        try:
            completed = duck.fetchall(
                "SELECT problem_id, is_correct FROM pa_submissions WHERE session_date=?",
                [date.today().isoformat()]
            )
        except:
            completed = []
        finally:
            duck.close()
        completed_map = {c["problem_id"]: c["is_correct"] for c in completed}
        
        # 문제 카드
        st.markdown("### 📋 문제 목록")
        cols = st.columns(min(len(problems), 6))
        diff_icons = {"easy": "🟢", "medium": "🟡", "hard": "🔴",
                     "beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
        
        for i, p in enumerate(problems):
            with cols[i % len(cols)]:
                pid = p["problem_id"]
                status = "✅" if completed_map.get(pid) else ("❌" if pid in completed_map else "⬜")
                icon = diff_icons.get(p.get("difficulty", "medium"), "⚪")
                st.markdown(f"{status} {icon}")
                st.caption(pid[:15])
        
        st.divider()
        
        # 문제 선택
        selected_id = st.selectbox(
            "문제 선택", problem_ids, key=f"{data_type}_select",
            format_func=lambda x: f"{x} ({problem_map[x].get('difficulty', '')})"
        )
        p = problem_map[selected_id]
        
        # 문제 설명
        st.markdown(f"### 📌 {p.get('requester', '업무 요청')}")
        st.markdown(f"> {p['question']}")
        
        if p.get("context"):
            with st.expander("� 배경"):
                st.write(p["context"])
        
        if p.get("expected_columns"):
            st.caption(f"결과 컬럼: `{', '.join(p['expected_columns'])}`")
        
        st.divider()
        
        # SQL 에디터
        st.markdown("### 💻 SQL")
        sql = st.text_area("쿼리 작성", height=180, key=f"{data_type}_sql",
                          placeholder="SELECT ...")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            test_btn = st.button("▶️ 테스트", key=f"{data_type}_test")
        with col2:
            submit_btn = st.button("🚀 제출", type="primary", key=f"{data_type}_submit")
        
        # 테스트 실행
        if test_btn and sql.strip():
            df, err = run_query(sql, limit=20)
            if err:
                st.error(f"오류: {err}")
            elif df is not None:
                st.success(f"✅ 결과 미리보기 ({len(df)} 행)")
                st.dataframe(df, use_container_width=True)
        
        # 제출
        if submit_btn and sql.strip():
            with st.spinner("🤖 AI 채점 중..."):
                try:
                    from services.pa_submit import submit_pa
                    result = submit_pa(
                        problem_id=selected_id,
                        sql_text=sql,
                        note="",
                        session_date=date.today().isoformat()
                    )
                    
                    if result["is_correct"]:
                        st.success("✅ 정답입니다! 🎉")
                        st.balloons()
                    else:
                        st.error("❌ 오답입니다.")
                    
                    st.markdown("### 🤖 AI 피드백")
                    st.markdown(result.get("feedback", "피드백 없음"))
                except Exception as e:
                    st.error(f"제출 오류: {e}")

# ============================================================
# 메인 UI
# ============================================================

today = date.today().isoformat()
st.set_page_config(page_title="SQL Analytics Lab", page_icon="🎯", layout="wide")

# 헤더
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    st.title("🎯 SQL Analytics Lab")
with col2:
    streak = get_streak_info()
    st.metric("🔥 스트릭", f"{streak['current']}일")
with col3:
    level = get_level_info()
    st.metric("레벨", level['name'].split()[0])
with col4:
    st.metric("✅ 정답", f"{level['correct']}개")

tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 PA 연습", 
    "📊 Stream 분석",
    "📈 내 성적",
    "⚙️ 관리자"
])

# ==================================================
# 탭 1: PA 연습 (통합 워크스페이스)
# ==================================================
with tab1:
    st.header("🧠 PA 연습")
    st.caption("매일 새로운 프로덕트 분석 문제 | 리텐션, 퍼널, 코호트, 매출")
    render_workspace("pa", f"problems/daily/{today}.json", "pa_")

# ==================================================
# 탭 2: Stream 분석 (통합 워크스페이스)
# ==================================================
with tab2:
    st.header("� Stream 분석")
    st.caption("주간 로그 분석 문제 | 이벤트 패턴, 이상 탐지, 실시간 분석")
    render_workspace("stream", f"problems/stream_daily/{today}.json", "stream_")

# ==================================================
# 탭 3: 내 성적
# ==================================================
with tab3:
    st.header("📈 내 성적")
    
    streak = get_streak_info()
    level = get_level_info()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔥 연속 출석", f"{streak['current']}일")
    with col2:
        st.metric("🎯 레벨", level['name'])
    with col3:
        st.metric("다음 레벨까지", f"{level['next'] - level['correct']}문제")
    
    st.divider()
    
    duck = get_duck()
    try:
        stats = duck.fetchall("""
            SELECT session_date,
                   COUNT(*) as total,
                   SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM pa_submissions
            GROUP BY session_date
            ORDER BY session_date DESC
            LIMIT 14
        """)
    except:
        stats = []
    finally:
        duck.close()
    
    if stats:
        st.markdown("### 📊 정답률 추이")
        df = pd.DataFrame(stats)
        df["accuracy"] = (df["correct"] / df["total"] * 100).round(1)
        st.bar_chart(df.set_index("session_date")["accuracy"])

# ==================================================
# 탭 4: 관리자
# ==================================================
with tab4:
    st.header("⚙️ 관리자")
    
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["📊 상태", "🔧 작업", "📋 로그"])
    
    # 상태 탭
    with admin_tab1:
        st.markdown("### 📅 스케줄러 상태")
        
        duck = get_duck()
        try:
            today_session = duck.fetchone("""
                SELECT session_date, status, generated_at, problem_set_path
                FROM daily_sessions
                WHERE session_date = ?
            """, [today])
            
            sessions = duck.fetchall("""
                SELECT session_date, status, generated_at
                FROM daily_sessions
                ORDER BY session_date DESC
                LIMIT 7
            """)
        except:
            today_session = None
            sessions = []
        finally:
            duck.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            status = today_session.get("status", "대기") if today_session else "대기"
            st.metric("오늘 상태", status)
        with col2:
            if today_session and today_session.get("generated_at"):
                st.metric("생성 시간", str(today_session["generated_at"])[:16])
            else:
                st.metric("생성 시간", "-")
        with col3:
            st.metric("실행 주기", "24시간")
        
        st.markdown("### 🗄️ 데이터베이스")
        try:
            pg = get_pg()
            tables = pg.fetch_df("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            
            table_info = []
            for _, row in tables.iterrows():
                tbl = row["table_name"]
                try:
                    cnt = pg.fetch_df(f"SELECT COUNT(*) as cnt FROM {tbl}")
                    table_info.append({"테이블": tbl, "행 수": f"{cnt.iloc[0]['cnt']:,}"})
                except:
                    table_info.append({"테이블": tbl, "행 수": "-"})
            pg.close()
            
            st.dataframe(pd.DataFrame(table_info), use_container_width=True)
        except Exception as e:
            st.error(f"DB 연결 오류: {e}")
    
    # 작업 탭
    with admin_tab2:
        st.markdown("### � 관리 작업")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 문제 생성")
            if st.button("🤖 PA 문제 생성 (Gemini)", type="primary"):
                with st.spinner("Gemini로 문제 생성 중..."):
                    try:
                        from problems.generator import generate as gen_problems
                        pg = get_pg()
                        path = gen_problems(date.today(), pg)
                        pg.close()
                        st.success(f"✅ 문제 생성 완료: {path}")
                    except Exception as e:
                        st.error(f"오류: {e}")
            
            if st.button("📊 Stream 문제 생성"):
                st.info("Stream 문제 생성 기능 준비 중")
        
        with col2:
            st.markdown("#### 🗃️ 데이터 관리")
            if st.button("🔄 PA 데이터 갱신"):
                with st.spinner("PA 데이터 생성 중..."):
                    try:
                        from generator.data_generator_advanced import generate_data
                        generate_data(modes=("pa",))
                        st.success("✅ PA 데이터 갱신 완료")
                    except Exception as e:
                        st.error(f"오류: {e}")
            
            if st.button("🔄 Stream 데이터 갱신"):
                with st.spinner("Stream 데이터 생성 중..."):
                    try:
                        from generator.data_generator_advanced import generate_data
                        generate_data(modes=("stream",))
                        st.success("✅ Stream 데이터 갱신 완료")
                    except Exception as e:
                        st.error(f"오류: {e}")
        
        st.divider()
        
        st.markdown("#### 🧹 초기화")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 제출 기록 초기화", type="secondary"):
                try:
                    duck = get_duck()
                    duck.execute("DELETE FROM pa_submissions")
                    duck.close()
                    st.success("✅ 제출 기록 초기화 완료")
                except Exception as e:
                    st.error(f"오류: {e}")
    
    # 로그 탭
    with admin_tab3:
        st.markdown("### � 최근 세션 로그")
        
        if sessions:
            for s in sessions:
                status = s.get("status", "N/A")
                icon = {"GENERATED": "🟢", "STARTED": "🔵", "FINISHED": "✅"}.get(status, "⚪")
                st.write(f"{icon} **{s['session_date']}** - {status}")
        else:
            st.info("로그가 없습니다.")
        
        if st.button("🔄 새로고침"):
            st.rerun()
