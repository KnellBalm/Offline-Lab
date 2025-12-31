// frontend/src/pages/Practice.tsx
/**
 * 무한 연습 모드 - Workspace와 동일한 UI, 다른 데이터 로직
 * - Gemini로 문제 생성 (파일 로드 대신)
 * - 임시 채점 (DB 저장 없음)
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { SQLEditor } from '../components/SQLEditor';
import { TableSchema } from '../components/TableSchema';
import { ResultTable } from '../components/ResultTable';
import { problemsApi, sqlApi, practiceApi } from '../api/client';
import { analytics } from '../services/analytics';
import type { TableSchema as Schema, SQLExecuteResponse, SubmitResponse } from '../types';
import './Workspace.css';

// 간단한 마크다운 변환
function renderMarkdown(text: string) {
    const html = text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br/>');
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

interface InfiniteProblem {
    id: string;
    title: string;
    description: string;
    difficulty: string;
    answer_sql: string;
}

export default function Practice() {
    const [problem, setProblem] = useState<InfiniteProblem | null>(null);
    const [tables, setTables] = useState<Schema[]>([]);
    const [sql, setSql] = useState('');
    const [result, setResult] = useState<SQLExecuteResponse | null>(null);
    const [submitResult, setSubmitResult] = useState<SubmitResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [hinting, setHinting] = useState(false);
    const [hint, setHint] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'problem' | 'schema'>('problem');
    const [leftWidth, setLeftWidth] = useState(45);
    const [editorHeight, setEditorHeight] = useState(600);
    const [totalScore, setTotalScore] = useState(0);
    const [correctCount, setCorrectCount] = useState(0);

    const resizerRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const rightPanelRef = useRef<HTMLDivElement>(null);

    // 스키마 로드
    useEffect(() => {
        analytics.pageView('/practice');
        problemsApi.schema('pa').then(res => setTables(res.data)).catch(() => { });
    }, []);

    // 문제 생성
    const generateProblem = useCallback(async () => {
        setGenerating(true);
        setProblem(null);
        setSql('');
        setResult(null);
        setSubmitResult(null);
        setHint(null);

        try {
            const res = await practiceApi.generate('pa');
            if (res.data.success && res.data.problem) {
                setProblem(res.data.problem);
                analytics.track('practice_problem_generated', {
                    difficulty: res.data.problem.difficulty
                });
            }
        } catch (e) {
            console.error('문제 생성 실패:', e);
        }
        setGenerating(false);
    }, []);

    // SQL 실행
    const handleExecute = useCallback(async () => {
        if (!sql.trim()) return;
        setLoading(true);
        setResult(null);
        try {
            const res = await sqlApi.execute(sql, 100);
            setResult(res.data);
        } catch (e: any) {
            setResult({ success: false, error: e.message });
        }
        setLoading(false);
    }, [sql]);

    // 제출 (임시 채점)
    const handleSubmit = useCallback(async () => {
        if (!sql.trim() || !problem) return;
        setSubmitting(true);
        setSubmitResult(null);

        try {
            const res = await practiceApi.submit(
                problem.id,
                sql,
                problem.answer_sql,
                problem.difficulty,
                'pa'
            );

            const isCorrect = res.data.is_correct;
            setSubmitResult({
                is_correct: isCorrect,
                feedback: res.data.message || (isCorrect ? '정답입니다!' : '오답입니다.')
            });

            if (isCorrect) {
                setTotalScore(prev => prev + (res.data.score || 0));
                setCorrectCount(prev => prev + 1);
            }
        } catch (e: any) {
            setSubmitResult({ is_correct: false, feedback: e.message });
        }
        setSubmitting(false);
    }, [sql, problem]);

    // 힌트 요청
    const handleHint = useCallback(async () => {
        if (!sql.trim() || !problem) return;
        setHinting(true);
        setHint(null);
        try {
            const res = await sqlApi.hint(problem.id, sql, 'pa');
            setHint(res.data.hint);
        } catch (e: any) {
            setHint(`힌트 요청 실패: ${e.message}`);
        }
        setHinting(false);
    }, [sql, problem]);

    // 좌우 리사이저
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        const container = containerRef.current;
        if (!container) return;

        const handleMouseMove = (e: MouseEvent) => {
            const containerRect = container.getBoundingClientRect();
            const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
            setLeftWidth(Math.min(Math.max(newWidth, 20), 80));
        };

        const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, []);

    // 상하 리사이저
    const handleMouseDownVertical = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        const rightPanel = rightPanelRef.current;
        if (!rightPanel) return;

        const handleMouseMove = (e: MouseEvent) => {
            const rightPanelRect = rightPanel.getBoundingClientRect();
            const newHeight = e.clientY - rightPanelRect.top;
            setEditorHeight(Math.min(Math.max(newHeight, 150), rightPanelRect.height - 100));
        };

        const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, []);

    const difficultyIcon: Record<string, string> = {
        easy: '🟢', medium: '🟡', hard: '🔴',
    };

    return (
        <div className="workspace" ref={containerRef}>
            {/* 좌측 패널 */}
            <div className="left-panel" style={{ width: `${leftWidth}%` }}>
                <div className="panel-tabs">
                    <button className={activeTab === 'problem' ? 'active' : ''} onClick={() => setActiveTab('problem')}>
                        🎯 무한 연습
                    </button>
                    <button className={activeTab === 'schema' ? 'active' : ''} onClick={() => setActiveTab('schema')}>
                        📋 스키마
                    </button>
                </div>

                {activeTab === 'problem' ? (
                    <div className="problem-panel">
                        {/* 점수 및 생성 버튼 */}
                        <div className="problem-list" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                <span style={{ fontWeight: 600 }}>🏆 {totalScore}점</span>
                                <span style={{ color: 'var(--success-color)' }}>✅ {correctCount}문제</span>
                            </div>
                            <button
                                onClick={generateProblem}
                                disabled={generating}
                                style={{
                                    padding: '0.5rem 1rem',
                                    background: generating ? 'var(--bg-tertiary)' : 'var(--accent-color)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: generating ? 'not-allowed' : 'pointer',
                                    fontWeight: 600
                                }}
                            >
                                {generating ? '⏳ 생성 중...' : '🎲 새 문제 생성'}
                            </button>
                        </div>

                        {/* 문제 상세 */}
                        {problem ? (
                            <div className="problem-detail">
                                <div className="problem-title">
                                    <span className="problem-number">{problem.title}</span>
                                    <span className="difficulty-badge">
                                        {difficultyIcon[problem.difficulty]} {problem.difficulty}
                                    </span>
                                </div>

                                <div className="slack-message">
                                    <div className="slack-header">
                                        <span className="slack-avatar">🤖</span>
                                        <span className="slack-sender">Gemini AI</span>
                                        <span className="slack-time">방금 생성됨</span>
                                    </div>
                                    <div className="slack-content">
                                        {renderMarkdown(problem.description)}
                                    </div>
                                </div>

                                {hint && (
                                    <div className="section">
                                        <div className="section-title">💡 힌트</div>
                                        <div className="hint-content">
                                            {renderMarkdown(hint)}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="no-problems" style={{ textAlign: 'center', padding: '3rem' }}>
                                <p style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>
                                    🎲 "새 문제 생성" 버튼을 클릭하세요!
                                </p>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                                    Gemini AI가 현재 데이터셋에 맞는 문제를 생성합니다.
                                </p>
                            </div>
                        )}
                    </div>
                ) : (
                    <TableSchema tables={tables} />
                )}
            </div>

            <div className="resizer" ref={resizerRef} onMouseDown={handleMouseDown} />

            {/* 우측 패널 */}
            <div className="right-panel" ref={rightPanelRef} style={{ width: `${100 - leftWidth}%` }}>
                <div className="editor-section" style={{ height: `${editorHeight}px` }}>
                    <div className="editor-header">
                        <span>💻 SQL</span>
                        <span className="shortcut">Ctrl+Enter로 실행</span>
                    </div>
                    <div className="editor-shell">
                        <SQLEditor
                            value={sql}
                            onChange={setSql}
                            onExecute={handleExecute}
                            height={`${editorHeight - 110}px`}
                            tables={tables}
                        />
                    </div>
                    <div className="editor-actions">
                        <button onClick={handleExecute} disabled={loading || !problem} className="btn-execute">
                            {loading ? '⏳ 실행 중...' : '▶️ 실행'}
                        </button>
                        <div className="spacer" />
                        <button onClick={handleHint} disabled={hinting || !problem} className="btn-hint">
                            {hinting ? '💭 생각 중...' : '💡 도움'}
                        </button>
                        <button onClick={handleSubmit} disabled={submitting || !problem} className="btn-submit">
                            {submitting ? '🔄 채점 중...' : '✅ 제출'}
                        </button>
                    </div>
                </div>

                <div className="v-resizer" onMouseDown={handleMouseDownVertical} />

                <div className="result-section">
                    <div className="result-header">
                        <span>📊 실행 결과</span>
                        {result?.execution_time_ms && (
                            <span className="exec-time">{result.execution_time_ms.toFixed(0)}ms</span>
                        )}
                    </div>

                    <div className="result-content">
                        {(submitting || hinting) && (
                            <div className="loading-state">
                                <div className="loading-spinner" />
                                <div className="loading-text">
                                    {submitting ? '🤔 채점 중입니다...' : '💭 AI가 힌트를 생성하고 있습니다...'}
                                </div>
                            </div>
                        )}

                        {hint && !submitting && !hinting && (
                            <div className="hint-result">
                                <div className="hint-title">💡 AI 힌트</div>
                                <div className="hint-content">{hint}</div>
                            </div>
                        )}

                        {submitResult && !submitting && (
                            <div className={`submit-result ${submitResult.is_correct ? 'correct' : 'wrong'}`}>
                                <div className="result-icon">
                                    {submitResult.is_correct ? '✅ 정답입니다!' : '❌ 틀렸습니다'}
                                </div>
                                <div className="feedback">{submitResult.feedback}</div>
                            </div>
                        )}

                        {result && result.success && result.data && !submitting && !hinting && (
                            <ResultTable columns={result.columns || []} data={result.data} />
                        )}

                        {result && !result.success && !submitting && !hinting && (
                            <div className="error-result">❌ {result.error}</div>
                        )}

                        {!result && !submitResult && !hint && !submitting && !hinting && (
                            <div className="empty-result">SQL을 작성하고 실행 버튼을 누르세요</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
