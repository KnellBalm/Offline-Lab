// frontend/src/services/analytics.ts
/**
 * 이벤트 트래킹 서비스 - Mixpanel 가이드 준수
 * - 이벤트 네이밍: Title Case (동사 + 대상)
 * - Core Action: Problem Solved
 * - 환경 구분: env property
 */

// Mixpanel 전역 타입 선언
declare global {
    interface Window {
        mixpanel?: {
            init: (token: string, config?: object) => void;
            track: (event: string, properties?: object) => void;
            identify: (userId: string) => void;
            reset: () => void;
            people: {
                set: (properties: object) => void;
                increment: (property: string, value?: number) => void;
            };
        };
        posthog?: {
            init: (key: string, config?: object) => void;
            capture: (event: string, properties?: object) => void;
            identify: (userId: string, properties?: object) => void;
            reset: () => void;
        };
    }
}

// MVP 기준 필수 이벤트 (가이드 준수)
export type AnalyticsEvent =
    // 유입
    | 'Page Viewed'
    // 회원
    | 'Sign Up Completed'
    // 인증
    | 'Login Success'
    | 'Logout Completed'
    // 핵심 가치 (Core Action)
    | 'Problem Solved'  // ⭐ Core Action
    // 문제 풀이 관련
    | 'Problem Viewed'
    | 'Problem Attempted'
    | 'Problem Submitted'
    | 'Problem Failed'
    | 'Hint Requested'
    // SQL 관련
    | 'SQL Executed'
    | 'SQL Error Occurred'
    // 온보딩
    | 'Onboarding Started'
    | 'Onboarding Completed'
    | 'Onboarding Skipped'
    // 기타
    | 'Tab Changed'
    | 'Schema Viewed'
    | 'Contact Clicked';

// 환경 구분
const getEnvironment = (): 'local' | 'staging' | 'prod' => {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') return 'local';
    if (hostname.includes('staging') || hostname.includes('test')) return 'staging';
    return 'prod';
};

// 이벤트 속성 타입
export interface EventProperties {
    // 공통
    timestamp?: string;
    page?: string;
    env?: 'local' | 'staging' | 'prod';

    // 문제 관련
    problem_id?: string;
    problem_difficulty?: 'easy' | 'medium' | 'hard';
    problem_topic?: string;
    data_type?: 'pa' | 'stream';

    // 결과 관련
    is_correct?: boolean;
    attempt_number?: number;
    time_spent_seconds?: number;
    execution_time_ms?: number;

    // SQL 관련
    sql_length?: number;
    error_message?: string;
    has_error?: boolean;

    // 인증 관련
    auth_provider?: 'google' | 'kakao' | 'email';

    // 온보딩 관련
    step_skipped_at?: number;
    total_steps?: number;

    // 기타
    user_id?: string;
    [key: string]: unknown;
}

// User Properties 타입
export interface UserProperties {
    user_id: string;
    email?: string;
    user_type: 'free' | 'admin';
    signup_date?: string;
    total_problems_solved?: number;
    current_level?: number;
    current_xp?: number;
}


class Analytics {
    private env: 'local' | 'staging' | 'prod';

    constructor() {
        this.env = getEnvironment();
    }

    private isPostHogReady(): boolean {
        return !!(window.posthog && typeof window.posthog.capture === 'function');
    }

    private isMixpanelReady(): boolean {
        return !!(window.mixpanel && typeof window.mixpanel.track === 'function');
    }

    /**
     * 사용자 식별 + User Properties 설정
     */
    identify(userId: string, properties?: Partial<UserProperties>) {
        const userProps: Partial<UserProperties> = {
            user_id: userId,
            user_type: properties?.user_type || 'free',
            ...properties
        };

        if (this.isMixpanelReady()) {
            window.mixpanel!.identify(userId);
            window.mixpanel!.people.set(userProps);
            console.log('[Mixpanel] Identified:', userId, userProps);
        }

        if (this.isPostHogReady()) {
            window.posthog!.identify(userId, userProps);
            console.log('[PostHog] Identified:', userId);
        }
    }

    /**
     * 사용자 식별 해제 (로그아웃)
     */
    reset() {
        if (this.isMixpanelReady()) {
            window.mixpanel!.reset();
            console.log('[Mixpanel] Reset');
        }

        if (this.isPostHogReady()) {
            window.posthog!.reset();
            console.log('[PostHog] Reset');
        }
    }

    /**
     * 이벤트 추적 - 핵심 메서드
     */
    track(event: AnalyticsEvent | string, properties?: EventProperties) {
        const eventData: EventProperties = {
            ...properties,
            timestamp: new Date().toISOString(),
            page: window.location.pathname,
            env: this.env  // 환경 구분 자동 추가
        };

        // Mixpanel
        if (this.isMixpanelReady()) {
            try {
                window.mixpanel!.track(event, eventData);
                console.log('[Mixpanel] Track:', event, eventData);
            } catch (e) {
                console.warn('[Mixpanel] Track failed:', e);
            }
        }

        // PostHog
        if (this.isPostHogReady()) {
            try {
                window.posthog!.capture(event, eventData);
                console.log('[PostHog] Capture:', event, eventData);
            } catch (e) {
                console.warn('[PostHog] Capture failed:', e);
            }
        }
    }

    /**
     * 문제 정답 시 solved 카운트 증가
     */
    private incrementSolved() {
        if (this.isMixpanelReady() && typeof window.mixpanel!.people.increment === 'function') {
            window.mixpanel!.people.increment('total_problems_solved', 1);
        }
    }

    // ============ 편의 메서드 ============

    /**
     * 페이지뷰
     */
    pageView(pageName: string, properties?: EventProperties) {
        this.track('Page Viewed', { ...properties, page: pageName });
    }

    /**
     * 회원가입 완료
     */
    signUpCompleted(userId: string, provider: 'google' | 'kakao' | 'email') {
        this.track('Sign Up Completed', {
            user_id: userId,
            auth_provider: provider
        });
    }

    /**
     * 로그인 성공
     */
    loginSuccess(userId: string, provider: 'google' | 'kakao' | 'email') {
        this.track('Login Success', {
            user_id: userId,
            auth_provider: provider
        });
    }

    /**
     * 로그아웃 완료
     */
    logoutCompleted() {
        this.track('Logout Completed', {});
        this.reset();
    }

    /**
     * 문제 조회
     */
    problemViewed(problemId: string, difficulty: string, topic: string, dataType: 'pa' | 'stream') {
        this.track('Problem Viewed', {
            problem_id: problemId,
            problem_difficulty: difficulty as 'easy' | 'medium' | 'hard',
            problem_topic: topic,
            data_type: dataType
        });
    }

    /**
     * 문제 제출
     */
    problemSubmitted(problemId: string, isCorrect: boolean, attemptNumber: number, timeSpent: number) {
        this.track('Problem Submitted', {
            problem_id: problemId,
            is_correct: isCorrect,
            attempt_number: attemptNumber,
            time_spent_seconds: timeSpent
        });

        // ⭐ Core Action: 정답인 경우
        if (isCorrect) {
            this.track('Problem Solved', {
                problem_id: problemId,
                attempt_number: attemptNumber,
                time_spent_seconds: timeSpent
            });
            this.incrementSolved();
        } else {
            this.track('Problem Failed', {
                problem_id: problemId,
                attempt_number: attemptNumber
            });
        }
    }

    /**
     * SQL 실행
     */
    sqlExecuted(sqlLength: number, executionTimeMs: number, hasError: boolean, errorMessage?: string) {
        this.track('SQL Executed', {
            sql_length: sqlLength,
            execution_time_ms: executionTimeMs,
            has_error: hasError
        });

        if (hasError && errorMessage) {
            this.track('SQL Error Occurred', { error_message: errorMessage });
        }
    }

    /**
     * 힌트 요청
     */
    hintRequested(problemId: string, difficulty: string, dataType: 'pa' | 'stream') {
        this.track('Hint Requested', {
            problem_id: problemId,
            problem_difficulty: difficulty as 'easy' | 'medium' | 'hard',
            data_type: dataType
        });
    }

    /**
     * 탭 변경
     */
    tabChanged(tab: string, dataType: 'pa' | 'stream') {
        this.track('Tab Changed', { tab, data_type: dataType });
    }

    /**
     * 스키마 조회
     */
    schemaViewed(dataType: 'pa' | 'stream') {
        this.track('Schema Viewed', { data_type: dataType });
    }

    /**
     * 연락 버튼 클릭
     */
    contactClicked() {
        this.track('Contact Clicked', {});
    }
}

// 싱글톤 인스턴스
export const analytics = new Analytics();

// SDK 초기화 함수
export function initAnalytics() {
    console.log('[Analytics] Init check - Mixpanel:', !!window.mixpanel, 'PostHog:', !!window.posthog);
    console.log('[Analytics] Environment:', getEnvironment());
}
