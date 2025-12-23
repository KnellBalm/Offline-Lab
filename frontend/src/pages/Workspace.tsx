// frontend/src/pages/Workspace.tsx
import { useEffect, useState, useCallback, useRef } from 'react';
import { SQLEditor } from '../components/SQLEditor';
import { TableSchema } from '../components/TableSchema';
import { ResultTable } from '../components/ResultTable';
import { problemsApi, sqlApi } from '../api/client';
import type { Problem, TableSchema as Schema, SQLExecuteResponse, SubmitResponse } from '../types';
import './Workspace.css';

interface WorkspaceProps {
    dataType: 'pa' | 'stream';
}

interface CompletedStatus {
    [problemId: string]: { is_correct: boolean; submitted_at: string };
}

export function Workspace({ dataType }: WorkspaceProps) {
    const [problems, setProblems] = useState<Problem[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [tables, setTables] = useState<Schema[]>([]);
    const [sql, setSql] = useState('');
    const [result, setResult] = useState<SQLExecuteResponse | null>(null);
    const [submitResult, setSubmitResult] = useState<SubmitResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [hinting, setHinting] = useState(false);
    const [hint, setHint] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'problem' | 'schema' | 'history'>('problem');
    const [leftWidth, setLeftWidth] = useState(45);
    const [editorHeight, setEditorHeight] = useState(250); // 기본 높이 px
    const [completedStatus, setCompletedStatus] = useState<CompletedStatus>({});
    const [history, setHistory] = useState<any[]>([]);
    const resizerRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const rightPanelRef = useRef<HTMLDivElement>(null);

    const selectedProblem = problems[selectedIndex] || null;

    // 데이터 로드
    useEffect(() => {
        async function load() {
            try {
                const [problemsRes, schemaRes] = await Promise.all([
                    problemsApi.list(dataType),
                    problemsApi.schema(dataType),
                ]);
                setProblems(problemsRes.data.problems);
                setTables(schemaRes.data);
                setSelectedIndex(0);
                setSubmitResult(null);
                setResult(null);
                setHint(null);
                setSql('');
            } catch (error) {
                console.error('Failed to load data:', error);
            }
        }
        load();
        const saved = localStorage.getItem(`completed_${dataType}`);
        if (saved) {
            try { setCompletedStatus(JSON.parse(saved)); } catch { }
        }
    }, [dataType]);

    // SQL 실행
    const handleExecute = useCallback(async () => {
        if (!sql.trim()) return;
        setLoading(true);
        setSubmitResult(null);
        setHint(null);
        try {
            const res = await sqlApi.execute(sql);
            setResult(res.data);
        } catch (error: any) {
            setResult({ success: false, error: error.message });
        }
        setLoading(false);
    }, [sql]);

    // 제출
    const handleSubmit = useCallback(async () => {
        if (!sql.trim() || !selectedProblem) return;
        setSubmitting(true);
        setSubmitResult(null);
        setHint(null);
        try {
            const res = await sqlApi.submit(selectedProblem.problem_id, sql, dataType);
            setSubmitResult(res.data);

            const newStatus = {
                ...completedStatus,
                [selectedProblem.problem_id]: {
                    is_correct: res.data.is_correct,
                    submitted_at: new Date().toISOString()
                }
            };
            setCompletedStatus(newStatus);
            localStorage.setItem(`completed_${dataType}`, JSON.stringify(newStatus));

            setHistory(prev => [{
                problem_id: selectedProblem.problem_id,
                problem_num: selectedIndex + 1,
                sql: sql,
                is_correct: res.data.is_correct,
                feedback: res.data.feedback,
                submitted_at: new Date().toLocaleTimeString()
            }, ...prev].slice(0, 20));
        } catch (error: any) {
            setSubmitResult({ is_correct: false, feedback: error.message });
        }
        setSubmitting(false);
    }, [sql, selectedProblem, completedStatus, dataType, selectedIndex]);

    // 힌트 요청
    const handleHint = useCallback(async () => {
        if (!sql.trim() || !selectedProblem) return;
        setHinting(true);
        setHint(null);
        try {
            const res = await sqlApi.hint(selectedProblem.problem_id, sql, dataType);
            setHint(res.data.hint);
        } catch (error: any) {
            setHint(`힌트 요청 실패: ${error.message}`);
        }
        setHinting(false);
    }, [sql, selectedProblem, dataType]);

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
            setEditorHeight(Math.min(Math.max(newHeight, 150), 600));
        };

        const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, []);

    const getStatusIcon = (problemId: string) => {
        const status = completedStatus[problemId];
        if (!status) return '⬜';
        return status.is_correct ? '✅' : '❌';
    };

    const difficultyIcon: Record<string, string> = {
        easy: '🟢', medium: '🟡', hard: '🔴',
    };

    return (
        <div className="workspace" ref={containerRef}>
            {/* 좌측 패널 */}
            <div className="left-panel" style={{ width: `${leftWidth}%` }}>
                <div className="panel-tabs">
                    <button className={activeTab === 'problem' ? 'active' : ''} onClick={() => setActiveTab('problem')}>
                        📌 문제
                    </button>
                    <button className={activeTab === 'schema' ? 'active' : ''} onClick={() => setActiveTab('schema')}>
                        📋 스키마
                    </button>
                    <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}>
                        📜 기록
                    </button>
                </div>

                {activeTab === 'problem' ? (
                    <div className="problem-panel">
                        <div className="problem-list">
                            {problems.map((p, idx) => (
                                <button
                                    key={p.problem_id}
                                    className={`problem-item ${selectedIndex === idx ? 'active' : ''}`}
                                    onClick={() => { setSelectedIndex(idx); setSubmitResult(null); setHint(null); }}
                                >
                                    <span className="status">{getStatusIcon(p.problem_id)}</span>
                                    <span className="num">{idx + 1}번</span>
                                    <span className="difficulty">{difficultyIcon[p.difficulty]}</span>
                                </button>
                            ))}
                        </div>

                        {selectedProblem && (
                            <div className="problem-detail">
                                <div className="problem-title">
                                    <span className="problem-number">문제 {selectedIndex + 1}</span>
                                    <span className="difficulty-badge">
                                        {difficultyIcon[selectedProblem.difficulty]} {selectedProblem.difficulty}
                                    </span>
                                </div>

                                {selectedProblem.requester && (
                                    <div className="slack-message">
                                        <div className="slack-header">
                                            <span className="slack-avatar">👤</span>
                                            <span className="slack-sender">{selectedProblem.requester}</span>
                                            <span className="slack-time">오늘 오전 10:30</span>
                                        </div>
                                        <div className="slack-content">
                                            {selectedProblem.question}
                                        </div>
                                        {selectedProblem.context && (
                                            <div className="slack-context">
                                                💡 {selectedProblem.context}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {selectedProblem.expected_columns && (
                                    <div className="section">
                                        <div className="section-title">📊 결과 컬럼</div>
                                        <div className="columns-box">
                                            {selectedProblem.expected_columns.map((col, i) => (
                                                <code key={i}>{col}</code>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {selectedProblem.hint && (
                                    <details className="hint-section">
                                        <summary>💬 힌트 보기</summary>
                                        <p>{selectedProblem.hint}</p>
                                    </details>
                                )}
                            </div>
                        )}

                        {problems.length === 0 && (
                            <div className="no-problems">
                                오늘 {dataType.toUpperCase()} 문제가 없습니다.
                            </div>
                        )}
                    </div>
                ) : activeTab === 'schema' ? (
                    <TableSchema tables={tables} />
                ) : (
                    <div className="history-panel">
                        <div className="history-header">
                            <h3>📜 제출 기록</h3>
                            <span className="data-info">{dataType.toUpperCase()} 데이터셋</span>
                        </div>
                        {history.length === 0 ? (
                            <div className="no-history">아직 제출 기록이 없습니다.</div>
                        ) : (
                            <div className="history-list">
                                {history.map((h, i) => (
                                    <div key={i} className={`history-item ${h.is_correct ? 'correct' : 'wrong'}`}>
                                        <div className="history-meta">
                                            <span className="history-status">{h.is_correct ? '✅' : '❌'}</span>
                                            <span className="history-problem">문제 {h.problem_num}</span>
                                            <span className="history-time">{h.submitted_at}</span>
                                        </div>
                                        <pre className="history-sql">{h.sql.slice(0, 100)}{h.sql.length > 100 ? '...' : ''}</pre>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
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
                            height={`${editorHeight - 110}px`} // header(35) + actions(45) + border/padding
                            tables={tables}
                        />
                    </div>
                    <div className="editor-actions">
                        <button onClick={handleExecute} disabled={loading} className="btn-execute">
                            {loading ? '⏳ 실행 중...' : '▶️ 실행'}
                        </button>
                        <div className="spacer" />
                        <button onClick={handleHint} disabled={hinting || !selectedProblem} className="btn-hint">
                            {hinting ? '💭 생각 중...' : '💡 도움'}
                        </button>
                        <button onClick={handleSubmit} disabled={submitting || !selectedProblem} className="btn-submit">
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
                        {/* 로딩 상태 */}
                        {(submitting || hinting) && (
                            <div className="loading-state">
                                <div className="loading-spinner" />
                                <div className="loading-text">
                                    {submitting ? '🤔 채점 중입니다...' : '💭 AI가 힌트를 생성하고 있습니다...'}
                                </div>
                            </div>
                        )}

                        {/* 힌트 */}
                        {hint && !submitting && !hinting && (
                            <div className="hint-result">
                                <div className="hint-title">💡 AI 힌트</div>
                                <div className="hint-content">{hint}</div>
                            </div>
                        )}

                        {/* 제출 결과 */}
                        {submitResult && !submitting && (
                            <div className={`submit-result ${submitResult.is_correct ? 'correct' : 'wrong'}`}>
                                <div className="result-icon">
                                    {submitResult.is_correct ? '✅ 정답입니다!' : '❌ 틀렸습니다'}
                                </div>
                                <div className="feedback">{submitResult.feedback}</div>
                            </div>
                        )}

                        {/* 쿼리 결과 */}
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
