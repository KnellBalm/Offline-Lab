// frontend/src/pages/MainPage.tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { statsApi } from '../api/client';
import './MainPage.css';

interface LeaderboardEntry {
    rank: number;
    nickname: string;
    correct: number;
    streak: number;
    level: string;
}

export function MainPage() {
    const { user } = useAuth();
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadLeaderboard();
    }, []);

    const loadLeaderboard = async () => {
        try {
            const res = await statsApi.leaderboard();
            setLeaderboard(res.data || []);
        } catch (err) {
            console.error('Failed to load leaderboard:', err);
            setLeaderboard([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="main-page">
            {/* 히어로 섹션 */}
            <section className="hero">
                <h1>🎯 SQL Analytics Lab</h1>
                <p className="hero-subtitle">실전 SQL 문제를 풀고 데이터 분석 실력을 키워보세요</p>

                {!user && (
                    <p className="hero-cta">로그인하고 나만의 성적을 기록하세요!</p>
                )}
            </section>

            {/* 퀵 액션 카드 */}
            <section className="quick-actions-section">
                <h2>📚 연습 모드 선택</h2>
                <div className="quick-actions">
                    <Link to="/pa" className="action-card pa">
                        <span className="icon">🧠</span>
                        <h3>PA 연습</h3>
                        <p>Product Analytics 실전 문제</p>
                        <span className="badge">매일 새 문제</span>
                    </Link>
                    <Link to="/stream" className="action-card stream">
                        <span className="icon">📊</span>
                        <h3>스트림 연습</h3>
                        <p>Streaming 데이터 분석</p>
                        <span className="badge">실시간 처리</span>
                    </Link>
                    <Link to="/practice" className="action-card practice">
                        <span className="icon">🎯</span>
                        <h3>무한 연습</h3>
                        <p>AI 생성 무제한 문제</p>
                        <span className="badge">∞ 무제한</span>
                    </Link>
                </div>
            </section>

            {/* 메인 콘텐츠: 리더보드 + 팁 */}
            <div className="main-content">
                {/* 리더보드 */}
                <section className="leaderboard-section">
                    <h2>🏆 리더보드</h2>
                    {loading ? (
                        <div className="loading">불러오는 중...</div>
                    ) : leaderboard.length === 0 ? (
                        <div className="empty-state">
                            <p>아직 기록이 없습니다</p>
                            <p className="hint">문제를 풀고 첫 번째 기록을 남겨보세요!</p>
                        </div>
                    ) : (
                        <div className="leaderboard">
                            <table>
                                <thead>
                                    <tr>
                                        <th>순위</th>
                                        <th>닉네임</th>
                                        <th>정답</th>
                                        <th>연속</th>
                                        <th>레벨</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {leaderboard.map((entry, idx) => (
                                        <tr key={idx} className={entry.nickname === user?.nickname ? 'highlight' : ''}>
                                            <td className="rank">
                                                {entry.rank === 1 && '🥇'}
                                                {entry.rank === 2 && '🥈'}
                                                {entry.rank === 3 && '🥉'}
                                                {entry.rank > 3 && entry.rank}
                                            </td>
                                            <td className="nickname">{entry.nickname}</td>
                                            <td className="correct">{entry.correct}</td>
                                            <td className="streak">{entry.streak}일</td>
                                            <td className="level">{entry.level}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                {/* SQL 팁 */}
                <section className="tips-section">
                    <h2>💡 오늘의 SQL 팁</h2>
                    <div className="tip-card">
                        <h4>Window Functions 활용하기</h4>
                        <p>ROW_NUMBER(), RANK(), DENSE_RANK()를 사용하면 순위를 쉽게 계산할 수 있어요.</p>
                        <code>ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales DESC)</code>
                    </div>
                    <div className="tip-card">
                        <h4>날짜 함수 마스터하기</h4>
                        <p>DATE_TRUNC, EXTRACT를 활용하면 시계열 분석이 편리해집니다.</p>
                        <code>DATE_TRUNC('month', created_at)</code>
                    </div>
                </section>
            </div>

            {/* 하단 안내 */}
            <section className="footer-section">
                <div className="footer-content">
                    <div className="footer-item">
                        <span className="footer-icon">⏱️</span>
                        <div>
                            <h4>매일 연습</h4>
                            <p>새로운 문제가 매일 생성됩니다</p>
                        </div>
                    </div>
                    <div className="footer-item">
                        <span className="footer-icon">📈</span>
                        <div>
                            <h4>실력 추적</h4>
                            <p>정답률과 연속 일수 기록</p>
                        </div>
                    </div>
                    <div className="footer-item">
                        <span className="footer-icon">🤖</span>
                        <div>
                            <h4>AI 힌트</h4>
                            <p>막히면 AI에게 힌트를 받아보세요</p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}
