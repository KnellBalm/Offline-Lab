// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom';
import { Workspace } from './pages/Workspace';
import { useEffect, useState } from 'react';
import { statsApi } from './api/client';
import type { UserStats } from './types';
import './App.css';

function App() {
  const [stats, setStats] = useState<UserStats | null>(null);

  useEffect(() => {
    statsApi.me().then(res => setStats(res.data)).catch(() => { });
  }, []);

  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <Link to="/" className="logo">🎯 SQL Analytics Lab</Link>
          <nav className="nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
              🧠 PA 연습
            </NavLink>
            <NavLink to="/stream" className={({ isActive }) => isActive ? 'active' : ''}>
              📊 Stream
            </NavLink>
            <NavLink to="/stats" className={({ isActive }) => isActive ? 'active' : ''}>
              📈 성적
            </NavLink>
            <NavLink to="/admin" className={({ isActive }) => isActive ? 'active' : ''}>
              ⚙️ 관리자
            </NavLink>
          </nav>
          <div className="user-stats">
            {stats && (
              <>
                <span className="streak">🔥 {stats.streak}일</span>
                <span className="level">{stats.level}</span>
                <span className="correct">✅ {stats.correct}</span>
              </>
            )}
          </div>
        </header>

        <main className="main">
          <Routes>
            <Route path="/" element={<Workspace dataType="pa" />} />
            <Route path="/stream" element={<Workspace dataType="stream" />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

function StatsPage() {
  return <div className="page-placeholder">📈 내 성적 (준비 중)</div>;
}

function AdminPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetch('http://localhost:15174/admin/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => { });
  }, []);

  const generateProblems = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch('http://localhost:15174/admin/generate-problems', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_type: 'pa' })
      });
      const data = await res.json();
      setMessage(data.message || '완료');
    } catch (e) {
      setMessage('오류 발생');
    }
    setLoading(false);
  };

  const refreshData = async (type: string) => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch('http://localhost:15174/admin/refresh-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_type: type })
      });
      const data = await res.json();
      setMessage(data.message || '완료');
    } catch (e) {
      setMessage('오류 발생');
    }
    setLoading(false);
  };

  return (
    <div className="admin-page">
      <h1>⚙️ 관리자</h1>

      <section className="admin-section">
        <h2>📊 시스템 상태</h2>
        {status ? (
          <div className="status-grid">
            <div className="status-item">
              <span>PostgreSQL</span>
              <span className={status.postgres_connected ? 'ok' : 'error'}>
                {status.postgres_connected ? '✅ 연결됨' : '❌ 연결 안됨'}
              </span>
            </div>
            <div className="status-item">
              <span>DuckDB</span>
              <span className={status.duckdb_connected ? 'ok' : 'error'}>
                {status.duckdb_connected ? '✅ 연결됨' : '❌ 연결 안됨'}
              </span>
            </div>
          </div>
        ) : (
          <p>로딩 중...</p>
        )}
      </section>

      <section className="admin-section">
        <h2>🔧 작업</h2>
        <div className="action-buttons">
          <button onClick={generateProblems} disabled={loading}>
            🤖 PA 문제 생성
          </button>
          <button onClick={() => refreshData('pa')} disabled={loading}>
            🔄 PA 데이터 갱신
          </button>
          <button onClick={() => refreshData('stream')} disabled={loading}>
            🔄 Stream 데이터 갱신
          </button>
        </div>
        {message && <p className="message">{message}</p>}
      </section>

      <section className="admin-section">
        <h2>🗄️ 테이블 현황</h2>
        {status?.tables && (
          <table className="admin-table">
            <thead>
              <tr><th>테이블</th><th>행 수</th></tr>
            </thead>
            <tbody>
              {status.tables.map((t: any) => (
                <tr key={t.table_name}>
                  <td>{t.table_name}</td>
                  <td>{t.row_count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default App;
