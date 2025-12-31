// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import axios from 'axios';

interface User {
    id: string;
    email: string;
    name: string;
    nickname?: string;
    is_admin?: boolean;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
    register: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const refreshUser = async () => {
        try {
            const res = await axios.get('/api/auth/me', { withCredentials: true });
            if (res.data.logged_in) {
                setUser(res.data.user);
            } else {
                setUser(null);
            }
        } catch {
            setUser(null);
        }
    };

    useEffect(() => {
        refreshUser().finally(() => setIsLoading(false));
    }, []);

    const login = async (email: string, password: string) => {
        try {
            const res = await axios.post('/api/auth/login', { email, password }, { withCredentials: true });
            if (res.data.success) {
                // 로그인 성공 후 /auth/me에서 is_admin 포함 전체 정보 조회
                await refreshUser();
                return { success: true };
            }
            return { success: false, error: '로그인에 실패했습니다' };
        } catch (err: any) {
            return { success: false, error: err.response?.data?.detail || '로그인에 실패했습니다' };
        }
    };

    const register = async (email: string, password: string, name: string) => {
        try {
            const res = await axios.post('/api/auth/register', { email, password, name }, { withCredentials: true });
            if (res.data.success) {
                setUser(res.data.user);
                return { success: true };
            }
            return { success: false, error: '회원가입에 실패했습니다' };
        } catch (err: any) {
            return { success: false, error: err.response?.data?.detail || '회원가입에 실패했습니다' };
        }
    };

    const logout = async () => {
        try {
            await axios.post('/api/auth/logout', {}, { withCredentials: true });
        } catch {
            // ignore
        }
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
}
