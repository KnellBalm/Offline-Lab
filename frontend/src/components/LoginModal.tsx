// frontend/src/components/LoginModal.tsx
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginModal.css';

interface LoginModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function LoginModal({ isOpen, onClose }: LoginModalProps) {
    const { login, register } = useAuth();
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        let result;
        if (mode === 'login') {
            result = await login(email, password);
        } else {
            result = await register(email, password, name);
        }

        setLoading(false);

        if (result.success) {
            onClose();
            setEmail('');
            setPassword('');
            setName('');
        } else {
            setError(result.error || '오류가 발생했습니다');
        }
    };

    const handleSocialLogin = (provider: string) => {
        alert(`${provider} 로그인은 아직 준비 중입니다.`);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <button className="modal-close" onClick={onClose}>×</button>

                <h2>{mode === 'login' ? '로그인' : '회원가입'}</h2>

                <form onSubmit={handleSubmit}>
                    {mode === 'register' && (
                        <div className="form-group">
                            <label>이름</label>
                            <input
                                type="text"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                placeholder="이름을 입력하세요"
                                required
                            />
                        </div>
                    )}

                    <div className="form-group">
                        <label>이메일</label>
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="이메일을 입력하세요"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>비밀번호</label>
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="비밀번호를 입력하세요"
                            required
                            minLength={4}
                        />
                    </div>

                    {error && <div className="error-message">{error}</div>}

                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? '처리 중...' : (mode === 'login' ? '로그인' : '회원가입')}
                    </button>
                </form>

                <div className="divider">
                    <span>또는</span>
                </div>

                <div className="social-buttons">
                    <button className="btn-google" onClick={() => handleSocialLogin('Google')}>
                        🔵 Google로 계속하기
                    </button>
                    <button className="btn-kakao" onClick={() => handleSocialLogin('Kakao')}>
                        🟡 Kakao로 계속하기
                    </button>
                </div>

                <div className="mode-switch">
                    {mode === 'login' ? (
                        <p>계정이 없으신가요? <button onClick={() => setMode('register')}>회원가입</button></p>
                    ) : (
                        <p>이미 계정이 있으신가요? <button onClick={() => setMode('login')}>로그인</button></p>
                    )}
                </div>
            </div>
        </div>
    );
}
