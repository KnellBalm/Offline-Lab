// frontend/src/components/Onboarding.tsx
/**
 * 전체 서비스 온보딩 플로우
 * 메인페이지 → PA 연습 → Stream 연습 → Workspace 기능
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { analytics } from '../services/analytics';
import './Onboarding.css';

interface OnboardingStep {
    id: string;
    page: string;  // 해당 단계의 페이지 경로
    target: string;
    title: string;
    content: string;
    placement: 'top' | 'bottom' | 'left' | 'right' | 'center';
    highlight?: boolean;
}

const onboardingSteps: OnboardingStep[] = [
    // 1. 메인페이지
    {
        id: 'welcome',
        page: '/',
        target: 'body',
        title: '🎉 SQL 트레이닝 센터에 오신 것을 환영합니다!',
        content: '실무 데이터 분석 문제를 풀며 SQL 실력을 키워보세요. 간단한 튜토리얼을 통해 서비스 사용법을 알려드릴게요.',
        placement: 'center',
    },
    {
        id: 'main-stats',
        page: '/',
        target: '.user-stats',
        title: '📊 내 학습 현황',
        content: '여기서 내 레벨, XP, 푼 문제 수 등 학습 현황을 확인할 수 있어요.',
        placement: 'bottom',
        highlight: true,
    },
    {
        id: 'main-nav',
        page: '/',
        target: '.nav-tabs',
        title: '🧭 메뉴 네비게이션',
        content: '상단 메뉴에서 PA 연습, Stream 연습, 마이페이지 등으로 이동할 수 있어요.',
        placement: 'bottom',
        highlight: true,
    },

    // 2. PA 연습 페이지
    {
        id: 'pa-intro',
        page: '/practice/pa',
        target: 'body',
        title: '📈 PA(프로덕트 애널리틱스) 연습',
        content: '이커머스/핀테크 등 프로덕트 데이터를 분석하는 SQL 문제를 풀어보세요. 실제 업무와 유사한 시나리오로 구성되어 있습니다.',
        placement: 'center',
    },
    {
        id: 'problem-list',
        page: '/practice/pa',
        target: '.problem-list',
        title: '📋 문제 목록',
        content: '풀고 싶은 문제를 선택하세요. 🟢 Easy, 🟡 Medium, 🔴 Hard로 난이도가 표시됩니다. ✅는 정답, ❌는 오답 문제예요.',
        placement: 'right',
        highlight: true,
    },
    {
        id: 'problem-detail',
        page: '/practice/pa',
        target: '.problem-detail',
        title: '📝 문제 상세',
        content: '선택한 문제의 상세 내용입니다. 요청사항, 컨텍스트, 힌트 등을 참고해서 SQL을 작성하세요.',
        placement: 'left',
        highlight: true,
    },
    {
        id: 'schema-tab',
        page: '/practice/pa',
        target: '.panel-tabs',
        title: '📋 스키마 확인',
        content: '"스키마" 탭을 클릭하면 사용 가능한 테이블과 컬럼 정보를 확인할 수 있어요.',
        placement: 'bottom',
        highlight: true,
    },
    {
        id: 'sql-editor',
        page: '/practice/pa',
        target: '.editor-container',
        title: '⌨️ SQL 에디터',
        content: '여기에 SQL 쿼리를 작성하세요. Ctrl+Enter로 실행! 자동완성 기능도 활용해보세요.',
        placement: 'top',
        highlight: true,
    },
    {
        id: 'submit-btn',
        page: '/practice/pa',
        target: '.btn-submit',
        title: '✅ 제출하기',
        content: '쿼리 작성 완료 후 제출 버튼을 클릭하면 정답과 비교해서 결과를 알려드려요.',
        placement: 'top',
        highlight: true,
    },

    // 3. Stream 연습 소개
    {
        id: 'stream-intro',
        page: '/practice/stream',
        target: 'body',
        title: '📡 Stream 데이터 연습',
        content: '실시간 스트리밍 데이터 분석 문제입니다. 채널별 성과, DAU/MAU 분석 등을 연습할 수 있어요.',
        placement: 'center',
    },

    // 4. 완료
    {
        id: 'complete',
        page: '/practice/pa',
        target: 'body',
        title: '🚀 준비 완료!',
        content: '이제 직접 문제를 풀어보세요! 막히면 힌트를 활용하고, 꾸준히 풀면 레벨업할 수 있어요. 화이팅! 💪',
        placement: 'center',
    },
];

export function Onboarding() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const [isActive, setIsActive] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });

    const currentStepData = onboardingSteps[currentStep];

    // 온보딩 시작 체크
    useEffect(() => {
        const hasCompletedOnboarding = localStorage.getItem('onboarding_completed');

        if (!hasCompletedOnboarding && user && location.pathname === '/') {
            const timer = setTimeout(() => {
                setIsActive(true);
                analytics.track('Onboarding Started', { user_id: user.id });
            }, 1000);

            return () => clearTimeout(timer);
        }
    }, [user, location.pathname]);

    // 페이지 이동 시 해당 스텝으로 맞추기
    useEffect(() => {
        if (isActive && currentStepData) {
            // 현재 페이지와 스텝의 페이지가 다르면 이동
            if (currentStepData.page !== location.pathname) {
                navigate(currentStepData.page);
            }
        }
    }, [isActive, currentStep, currentStepData, location.pathname, navigate]);

    // 툴팁 위치 계산
    const calculatePosition = useCallback(() => {
        if (!currentStepData) return;

        if (currentStepData.placement === 'center') {
            setTooltipPosition({
                top: window.innerHeight / 2 - 120,
                left: window.innerWidth / 2 - 220,
            });
            return;
        }

        const target = document.querySelector(currentStepData.target);
        if (!target) {
            setTooltipPosition({
                top: window.innerHeight / 2 - 120,
                left: window.innerWidth / 2 - 220,
            });
            return;
        }

        const rect = target.getBoundingClientRect();
        let top = 0, left = 0;

        switch (currentStepData.placement) {
            case 'top':
                top = rect.top - 180;
                left = rect.left + rect.width / 2 - 220;
                break;
            case 'bottom':
                top = rect.bottom + 20;
                left = rect.left + rect.width / 2 - 220;
                break;
            case 'left':
                top = rect.top + rect.height / 2 - 90;
                left = rect.left - 460;
                break;
            case 'right':
                top = rect.top + rect.height / 2 - 90;
                left = rect.right + 20;
                break;
        }

        top = Math.max(20, Math.min(top, window.innerHeight - 220));
        left = Math.max(20, Math.min(left, window.innerWidth - 460));

        setTooltipPosition({ top, left });
    }, [currentStepData]);

    useEffect(() => {
        if (isActive) {
            // 페이지 로드 후 약간의 딜레이
            const timer = setTimeout(calculatePosition, 300);
            window.addEventListener('resize', calculatePosition);
            return () => {
                clearTimeout(timer);
                window.removeEventListener('resize', calculatePosition);
            };
        }
    }, [isActive, currentStep, calculatePosition, location.pathname]);

    // 하이라이트 대상 요소에 스타일 적용
    useEffect(() => {
        if (isActive && currentStepData?.highlight) {
            const target = document.querySelector(currentStepData.target);
            if (target) {
                target.classList.add('onboarding-highlight');
                return () => target.classList.remove('onboarding-highlight');
            }
        }
    }, [isActive, currentStep, currentStepData]);

    const handleNext = () => {
        if (currentStep < onboardingSteps.length - 1) {
            setCurrentStep(currentStep + 1);
        } else {
            handleComplete();
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleSkip = () => {
        localStorage.setItem('onboarding_completed', 'true');
        analytics.track('Onboarding Skipped', {
            step_skipped_at: currentStep + 1,
            step_id: currentStepData?.id,
            user_id: user?.id,
        });
        setIsActive(false);
        navigate('/');
    };

    const handleComplete = () => {
        localStorage.setItem('onboarding_completed', 'true');
        analytics.track('Onboarding Completed', {
            total_steps: onboardingSteps.length,
            user_id: user?.id,
        });
        setIsActive(false);
    };

    if (!isActive || !currentStepData) return null;

    const isCenter = currentStepData.placement === 'center';
    const isLast = currentStep === onboardingSteps.length - 1;

    return (
        <div className="onboarding-overlay">
            <div
                className={`onboarding-tooltip ${isCenter ? 'center' : ''}`}
                style={{ top: tooltipPosition.top, left: tooltipPosition.left }}
            >
                <div className="onboarding-header">
                    <span className="step-indicator">{currentStep + 1} / {onboardingSteps.length}</span>
                </div>

                <h3 className="onboarding-title">{currentStepData.title}</h3>
                <p className="onboarding-content">{currentStepData.content}</p>

                <div className="onboarding-progress">
                    {onboardingSteps.map((_, idx) => (
                        <span
                            key={idx}
                            className={`progress-dot ${idx === currentStep ? 'active' : ''} ${idx < currentStep ? 'completed' : ''}`}
                        />
                    ))}
                </div>

                <div className="onboarding-buttons">
                    <button className="btn-skip" onClick={handleSkip}>
                        건너뛰기
                    </button>
                    <div className="btn-group">
                        {currentStep > 0 && (
                            <button className="btn-prev" onClick={handlePrev}>
                                이전
                            </button>
                        )}
                        <button className="btn-next" onClick={handleNext}>
                            {isLast ? '시작하기' : '다음'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
