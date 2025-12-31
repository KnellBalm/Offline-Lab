# backend/api/stats.py
"""통계 API"""
from typing import Optional
from fastapi import APIRouter

from backend.schemas.submission import UserStats, SubmissionHistory
from backend.services.stats_service import get_user_stats, get_submission_history
from backend.services.database import postgres_connection
from common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/me", response_model=UserStats)
async def get_my_stats():
    """내 통계 조회"""
    return get_user_stats()


@router.get("/history", response_model=list[SubmissionHistory])
async def get_history(limit: int = 20, data_type: Optional[str] = None):
    """제출 이력 조회 (data_type: 'pa' 또는 'stream' 필터링)"""
    return get_submission_history(limit, data_type)


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 20):
    """리더보드 조회 - 닉네임 기준"""
    try:
        with postgres_connection() as pg:
            # 사용자별 정답 수, 연속 일수 계산
            df = pg.fetch_df("""
                WITH user_stats AS (
                    SELECT 
                        u.id,
                        COALESCE(u.nickname, u.name, 'Anonymous') as nickname,
                        COUNT(DISTINCT CASE WHEN s.is_correct THEN s.session_date END) as correct_days,
                        COUNT(CASE WHEN s.is_correct THEN 1 END) as correct_count
                    FROM users u
                    LEFT JOIN submissions s ON s.user_id = u.id
                    GROUP BY u.id, u.nickname, u.name
                )
                SELECT 
                    nickname,
                    correct_count as correct,
                    correct_days as streak,
                    CASE 
                        WHEN correct_count >= 100 THEN '🏆 Master'
                        WHEN correct_count >= 50 THEN '💎 Diamond'
                        WHEN correct_count >= 20 THEN '🥇 Gold'
                        WHEN correct_count >= 10 THEN '🥈 Silver'
                        WHEN correct_count >= 5 THEN '🥉 Bronze'
                        ELSE '🌱 Beginner'
                    END as level
                FROM user_stats
                WHERE correct_count > 0
                ORDER BY correct_count DESC, streak DESC
                LIMIT %s
            """, [limit])
            
            result = []
            for idx, row in df.iterrows():
                result.append({
                    "rank": idx + 1,
                    "nickname": row['nickname'],
                    "correct": int(row['correct']),
                    "streak": int(row['streak']),
                    "level": row['level']
                })
            
            return result
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        return []
