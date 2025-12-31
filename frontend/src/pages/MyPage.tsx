// frontend/src/pages/MyPage.tsx
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { authApi } from '../api/client';
import './MyPage.css';

export function MyPage() {
    const { user, refreshUser, logout } = useAuth();
    const navigate = useNavigate();
    const [nickname, setNickname] = useState(user?.nickname || user?.name || '');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [deleting, setDeleting] = useState(false);

    if (!user) {
        return <Navigate to="/" />;
    }

    const handleSaveNickname = async () => {
        if (!nickname.trim() || nickname.trim().length < 2) {
            setMessage('닉네임은 2자 이상이어야 합니다');
            return;
        }

        setSaving(true);
        setMessage('');

        try {
            await axios.patch('/api/auth/nickname', { nickname: nickname.trim() }, { withCredentials: true });
            await refreshUser();
            setMessage('닉네임이 변경되었습니다 ✓');
        } catch (err: any) {
            setMessage(err.response?.data?.detail || '닉네임 변경에 실패했습니다');
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (!window.confirm('⚠️ 정말로 탈퇴하시겠습니까?\n\n모든 학습 기록과 데이터가 삭제되며, 복구할 수 없습니다.')) {
            return;
        }

        if (!window.confirm('⚠️ 마지막 확인입니다.\n\n탈퇴 후 동일 이메일로 다시 가입할 수 있습니다.\n정말 탈퇴하시겠습니까?')) {
            return;
        }

        setDeleting(true);
        try {
            await authApi.deleteAccount();
            alert('계정이 삭제되었습니다. 감사합니다.');
            navigate('/');
            window.location.reload();
        } catch (err: any) {
            setMessage(err.response?.data?.detail || '탈퇴 처리에 실패했습니다');
            setDeleting(false);
        }
    };

    return (
        <div className="mypage">
            <h1>👤 마이페이지</h1>

            <section className="profile-section">
                <h2>프로필 정보</h2>

                <div className="form-group">
                    <label>이메일</label>
                    <input type="text" value={user.email} disabled />
                </div>

                <div className="form-group">
                    <label>이름</label>
                    <input type="text" value={user.name} disabled />
                </div>

                <div className="form-group">
                    <label>닉네임</label>
                    <div className="nickname-input">
                        <input
                            type="text"
                            value={nickname}
                            onChange={e => setNickname(e.target.value)}
                            placeholder="닉네임을 입력하세요"
                        />
                        <button onClick={handleSaveNickname} disabled={saving}>
                            {saving ? '저장 중...' : '저장'}
                        </button>
                    </div>
                    {message && <div className={`message ${message.includes('✓') ? 'success' : 'error'}`}>{message}</div>}
                </div>
            </section>

            <section className="actions-section">
                <button onClick={logout} className="btn-logout">로그아웃</button>
            </section>

            <section className="danger-section">
                <h2>⚠️ 위험 구역</h2>
                <p className="warning-text">계정을 삭제하면 모든 학습 기록과 데이터가 영구적으로 삭제됩니다.</p>
                <button
                    onClick={handleDeleteAccount}
                    disabled={deleting}
                    className="btn-delete-account"
                >
                    {deleting ? '처리 중...' : '🗑️ 회원 탈퇴'}
                </button>
            </section>
        </div>
    );
}

