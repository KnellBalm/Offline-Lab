// frontend/src/api/client.ts
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:15174';

export const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 문제 API
export const problemsApi = {
    list: (dataType: string, date?: string) =>
        api.get(`/problems/${dataType}`, { params: { target_date: date } }),

    detail: (dataType: string, problemId: string, date?: string) =>
        api.get(`/problems/${dataType}/${problemId}`, { params: { target_date: date } }),

    schema: (dataType: string) =>
        api.get(`/problems/schema/${dataType}`),
};

// SQL API
export const sqlApi = {
    execute: (sql: string, limit: number = 100) =>
        api.post('/sql/execute', { sql, limit }),

    submit: (problemId: string, sql: string, dataType: string = 'pa', note?: string) =>
        api.post('/sql/submit', { problem_id: problemId, sql, data_type: dataType, note }),

    hint: (problemId: string, sql: string, dataType: string = 'pa') =>
        api.post('/sql/hint', { problem_id: problemId, sql, data_type: dataType }),
};

// 통계 API
export const statsApi = {
    me: () => api.get('/stats/me'),
    history: (limit: number = 20) => api.get('/stats/history', { params: { limit } }),
};

// 관리자 API
export const adminApi = {
    status: () => api.get('/admin/status'),
    generateProblems: (dataType: string, force: boolean = false) =>
        api.post('/admin/generate-problems', { data_type: dataType, force }),
    refreshData: (dataType: string) =>
        api.post('/admin/refresh-data', { data_type: dataType }),
    resetSubmissions: () => api.post('/admin/reset-submissions'),
};
