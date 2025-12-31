# backend/services/stats_service.py
"""통계 서비스 - PostgreSQL submissions 테이블 사용"""
from datetime import date, timedelta
from typing import List

from backend.services.database import postgres_connection
from backend.schemas.submission import UserStats, SubmissionHistory


def get_user_stats() -> UserStats:
    """사용자 통계 조회"""
    streak = get_streak()
    level_info = get_level()
    
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                FROM submissions
            """)
        
        total = int(df.iloc[0]["total"]) if len(df) > 0 else 0
        correct = int(df.iloc[0]["correct"]) if len(df) > 0 and df.iloc[0]["correct"] else 0
        accuracy = (correct / total * 100) if total > 0 else 0
    except Exception:
        total, correct, accuracy = 0, 0, 0
    
    return UserStats(
        streak=streak["current"],
        max_streak=streak["max"],
        level=level_info["name"],
        total_solved=total,
        correct=level_info.get("correct", correct),
        accuracy=round(accuracy, 1),
        next_level_threshold=level_info["next"],
        score=level_info.get("score", 0),
        level_progress=level_info.get("progress", 0)
    )


def get_streak() -> dict:
    """연속 출석 스트릭 계산"""
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df("""
                SELECT DISTINCT session_date::date as session_date
                FROM submissions 
                ORDER BY session_date DESC 
                LIMIT 30
            """)
        dates = {row["session_date"].isoformat() if hasattr(row["session_date"], 'isoformat') else str(row["session_date"]) for _, row in df.iterrows()}
    except Exception:
        dates = set()
    
    if not dates:
        return {"current": 0, "max": 0}
    
    streak = 0
    check = date.today()
    for _ in range(30):
        if check.isoformat() in dates:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    
    return {"current": streak, "max": len(dates)}


def get_level() -> dict:
    """점수 기반 레벨 계산 (난이도별 차등 점수)"""
    # 난이도별 점수: easy=10, medium=25, hard=50
    DIFFICULTY_SCORES = {
        'easy': 10,
        'medium': 25,
        'hard': 50
    }
    
    try:
        with postgres_connection() as pg:
            # 정답인 제출의 점수 합계 계산
            df = pg.fetch_df("""
                SELECT 
                    COALESCE(SUM(
                        CASE difficulty
                            WHEN 'easy' THEN 10
                            WHEN 'medium' THEN 25
                            WHEN 'hard' THEN 50
                            ELSE 25
                        END
                    ), 0) as total_score,
                    COUNT(*) as correct_count
                FROM submissions
                WHERE is_correct = true
            """)
        total_score = int(df.iloc[0]["total_score"]) if len(df) > 0 else 0
        correct_count = int(df.iloc[0]["correct_count"]) if len(df) > 0 else 0
    except Exception:
        total_score = 0
        correct_count = 0
    
    # 점수 기반 레벨 체계
    levels = [
        (0, "🌱 Beginner"),
        (50, "🌿 Learner"),
        (150, "🌳 Analyst"),
        (400, "⭐ Senior"),
        (800, "🏆 Expert"),
        (1500, "👑 Master")
    ]
    
    level_name = "🌱 Beginner"
    next_threshold = 50
    current_threshold = 0
    
    for threshold, name in levels:
        if total_score >= threshold:
            level_name = name
            current_threshold = threshold
        else:
            next_threshold = threshold
            break
    else:
        # Master 레벨 달성 시
        next_threshold = total_score
    
    return {
        "name": level_name,
        "score": total_score,
        "correct": correct_count,
        "next": next_threshold,
        "current": current_threshold,
        "progress": min(100, int((total_score - current_threshold) / max(1, next_threshold - current_threshold) * 100)) if next_threshold > current_threshold else 100
    }


def get_submission_history(limit: int = 20, data_type: str = None) -> List[SubmissionHistory]:
    """제출 이력 조회 (data_type으로 필터링 가능)"""
    try:
        with postgres_connection() as pg:
            where_clause = ""
            if data_type:
                where_clause = f"WHERE data_type = '{data_type}'"
            
            df = pg.fetch_df(f"""
                SELECT problem_id, session_date::date as session_date, is_correct, 
                       submitted_at, feedback, data_type
                FROM submissions
                {where_clause}
                ORDER BY submitted_at DESC
                LIMIT {limit}
            """)
        
        return [
            SubmissionHistory(
                problem_id=row["problem_id"],
                session_date=str(row["session_date"]),
                is_correct=row["is_correct"],
                submitted_at=row["submitted_at"].isoformat() if row["submitted_at"] else None,
                feedback=row.get("feedback")
            )
            for _, row in df.iterrows()
        ]
    except Exception:
        return []


