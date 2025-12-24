# 이벤트 트래킹 가이드

> 다른 프로젝트/개발자에게 전달 가능한 이벤트 트래킹 설계 및 구현 가이드

## 1. 개요

### 1.1 관련 문서
- [이벤트 설계 가이드라인 (AI 에이전트용)](./EVENT_DESIGN_GUIDELINE.md): 서비스 기획 의도 분석 및 이벤트 상세 설계 지침

### 1.2 사용 도구
| 도구 | 용도 | 무료 플랜 |
|------|------|----------|
| **Mixpanel** | 이벤트 분석, 퍼널, 리텐션 | 월 100만 이벤트 |
| **PostHog** | 이벤트 분석 + 세션 녹화 + A/B 테스트 | 월 100만 이벤트 |

### 1.3 아키텍처
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │────▶│   Mixpanel   │     │   PostHog    │
│   (React)    │────▶│     CDN      │     │     SDK      │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  analytics.ts   │
                   │  (추상화 레이어)  │
                   └─────────────────┘
```

---

## 2. 설치 및 설정

### 2.1 Mixpanel 설정 (CDN)

`index.html`의 `<head>` 태그 안에 추가:

```html
<!-- Mixpanel Tracking -->
<script type="text/javascript">
  (function(e,c){if(!c.__SV){var l,h;window.mixpanel=c;c._i=[];c.init=function(q,r,f){function t(d,a){var g=a.split(".");2==g.length&&(d=d[g[0]],a=g[1]);d[a]=function(){d.push([a].concat(Array.prototype.slice.call(arguments,0)))}}var b=c;"undefined"!==typeof f?b=c[f]=[]:f="mixpanel";b.people=b.people||[];b.toString=function(d){var a="mixpanel";"mixpanel"!==f&&(a+="."+f);d||(a+=" (stub)");return a};b.people.toString=function(){return b.toString(1)+".people (stub)"};l="disable time_event track track_pageview track_links track_forms track_with_groups add_group set_group remove_group register register_once alias unregister identify name_tag set_config reset opt_in_tracking opt_out_tracking has_opted_in_tracking has_opted_out_tracking clear_opt_in_out_tracking start_batch_senders start_session_recording stop_session_recording people.set people.set_once people.unset people.increment people.append people.union people.track_charge people.clear_charges people.delete_user people.remove".split(" ");
  for(h=0;h<l.length;h++)t(b,l[h]);var n="set set_once union unset remove delete".split(" ");b.get_group=function(){function d(p){a[p]=function(){b.push([g,[p].concat(Array.prototype.slice.call(arguments,0))])}}for(var a={},g=["get_group"].concat(Array.prototype.slice.call(arguments,0)),m=0;m<n.length;m++)d(n[m]);return a};c._i.push([q,r,f])};c.__SV=1.2;var k=e.createElement("script");k.type="text/javascript";k.async=!0;k.src="//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js";e=e.getElementsByTagName("script")[0];e.parentNode.insertBefore(k,e)}})(document,window.mixpanel||[])
  
  mixpanel.init('YOUR_MIXPANEL_TOKEN', {
    autocapture: true,
    record_sessions_percent: 100,
  });
</script>
```

### 2.2 PostHog 설정 (CDN)

`index.html`의 `<head>` 태그 안에 추가:

```html
<!-- PostHog Tracking -->
<script>
  !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
  
  posthog.init('YOUR_POSTHOG_KEY', {
    api_host: 'https://us.i.posthog.com',
    capture_pageview: true,
    capture_pageleave: true,
  });
</script>
```

### 2.3 React SDK (선택사항)

```bash
npm install posthog-js
```

`main.tsx`:
```tsx
import { PostHogProvider } from 'posthog-js/react'

const posthogKey = import.meta.env.VITE_POSTHOG_KEY || ''

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {posthogKey ? (
      <PostHogProvider apiKey={posthogKey} options={{ api_host: 'https://us.i.posthog.com' }}>
        <App />
      </PostHogProvider>
    ) : (
      <App />
    )}
  </StrictMode>
)
```

---

## 3. 이벤트 설계 방법론

### 3.1 이벤트 네이밍 규칙

```
[object]_[action]
```

**예시:**
- `page_view` (페이지를 조회함)
- `button_click` (버튼을 클릭함)
- `form_submit` (폼을 제출함)
- `problem_correct` (문제를 정답 처리함)

### 3.2 이벤트 분류 (Event Taxonomy)

| 카테고리 | 설명 | 예시 |
|---------|------|------|
| **Page Events** | 페이지 조회/이탈 | `page_view`, `page_leave` |
| **User Events** | 인증 관련 | `user_login`, `user_logout`, `user_signup` |
| **Feature Events** | 핵심 기능 사용 | `problem_submit`, `sql_execute` |
| **Engagement Events** | 참여/인터랙션 | `tab_change`, `hint_request` |
| **Error Events** | 에러 발생 | `sql_error`, `api_error` |

### 3.3 이벤트 속성 (Properties) 설계

모든 이벤트에 자동으로 포함되어야 하는 속성:

```typescript
{
  timestamp: string,      // ISO 8601 형식
  page: string,           // 현재 페이지 경로
  session_id?: string,    // 세션 ID
  user_id?: string,       // 사용자 ID (로그인 시)
}
```

기능별 추가 속성:

```typescript
// 문제 관련
{
  problem_id: string,
  problem_difficulty: 'easy' | 'medium' | 'hard',
  problem_topic: string,
  is_correct: boolean,
  attempt_number: number,
  time_spent_seconds: number,
}

// SQL 관련
{
  sql_length: number,
  has_error: boolean,
  error_message?: string,
}

// 인증 관련
{
  auth_provider: 'google' | 'kakao' | 'email',
}
```

### 3.4 이벤트 설계 체크리스트

1. **핵심 사용자 여정 정의**
   - 첫 방문 → 가입 → 첫 문제 풀이 → 정답 → 재방문

2. **각 단계별 이벤트 정의**
   - 어떤 행동을 추적할 것인가?
   - 어떤 속성이 필요한가?

3. **분석 질문 기반 설계**
   - "어떤 퍼널에서 이탈이 많은가?" → 퍼널 이벤트 필요
   - "어떤 기능을 많이 쓰는가?" → 기능 사용 이벤트 필요
   - "에러가 자주 발생하는가?" → 에러 이벤트 필요

---

## 4. 구현 코드

### 4.1 Analytics 서비스 (추상화 레이어)

`services/analytics.ts`:

```typescript
// 전역 타입 선언
declare global {
    interface Window {
        mixpanel?: {
            track: (event: string, properties?: object) => void;
            identify: (userId: string) => void;
            reset: () => void;
            people: { set: (properties: object) => void };
        };
        posthog?: {
            capture: (event: string, properties?: object) => void;
            identify: (userId: string, properties?: object) => void;
            reset: () => void;
        };
    }
}

// 이벤트 타입
export type AnalyticsEvent =
    | 'page_view'
    | 'page_leave'
    | 'problem_view'
    | 'problem_submit'
    | 'problem_correct'
    | 'problem_incorrect'
    | 'problem_hint_request'
    | 'sql_execute'
    | 'sql_error'
    | 'user_login'
    | 'user_logout'
    | 'tab_change';

class Analytics {
    private isPostHogReady(): boolean {
        return !!(window.posthog && typeof window.posthog.capture === 'function');
    }

    private isMixpanelReady(): boolean {
        return !!(window.mixpanel && typeof window.mixpanel.track === 'function');
    }

    track(event: string, properties?: object) {
        const eventData = {
            ...properties,
            timestamp: new Date().toISOString(),
            page: window.location.pathname
        };

        if (this.isMixpanelReady()) {
            window.mixpanel!.track(event, eventData);
            console.log('[Mixpanel] Track:', event, eventData);
        }

        if (this.isPostHogReady()) {
            window.posthog!.capture(event, eventData);
            console.log('[PostHog] Capture:', event, eventData);
        }
    }

    identify(userId: string, traits?: object) {
        if (this.isMixpanelReady()) {
            window.mixpanel!.identify(userId);
            if (traits) window.mixpanel!.people.set(traits);
        }
        if (this.isPostHogReady()) {
            window.posthog!.identify(userId, traits);
        }
    }

    reset() {
        if (this.isMixpanelReady()) window.mixpanel!.reset();
        if (this.isPostHogReady()) window.posthog!.reset();
    }

    // 편의 메서드
    pageView(page: string, props?: object) {
        this.track('page_view', { page, ...props });
    }

    problemSubmit(problemId: string, isCorrect: boolean, attempt: number) {
        this.track('problem_submit', { problem_id: problemId, is_correct: isCorrect, attempt_number: attempt });
        this.track(isCorrect ? 'problem_correct' : 'problem_incorrect', { problem_id: problemId });
    }

    sqlExecute(sqlLength: number, hasError: boolean, errorMsg?: string) {
        this.track('sql_execute', { sql_length: sqlLength, has_error: hasError, error_message: errorMsg });
        if (hasError) this.track('sql_error', { error_message: errorMsg });
    }
}

export const analytics = new Analytics();
```

### 4.2 컴포넌트에서 사용

```tsx
import { analytics } from '../services/analytics';

// 페이지 로드 시
useEffect(() => {
    analytics.pageView('/practice');
}, []);

// 문제 선택 시
const handleProblemSelect = (problem: Problem) => {
    analytics.track('problem_view', {
        problem_id: problem.id,
        problem_difficulty: problem.difficulty
    });
};

// SQL 실행 시
const handleExecute = async () => {
    try {
        const result = await executeSQL(sql);
        analytics.sqlExecute(sql.length, false);
    } catch (error) {
        analytics.sqlExecute(sql.length, true, error.message);
    }
};

// 문제 제출 시
const handleSubmit = async () => {
    const result = await submitAnswer(problemId, sql);
    analytics.problemSubmit(problemId, result.isCorrect, attemptNumber);
};
```

---

## 5. 이벤트 목록 (본 프로젝트)

| 이벤트 | 발생 시점 | 주요 속성 |
|--------|----------|----------|
| `page_view` | 페이지 로드/이동 | `page`, `data_type` |
| `problem_view` | 문제 선택 | `problem_id`, `difficulty`, `topic` |
| `problem_submit` | 정답 제출 | `problem_id`, `is_correct`, `attempt` |
| `problem_correct` | 정답 시 | `problem_id` |
| `problem_incorrect` | 오답 시 | `problem_id` |
| `problem_hint_request` | 힌트 요청 | `problem_id`, `difficulty` |
| `sql_execute` | SQL 실행 | `sql_length`, `has_error` |
| `sql_error` | SQL 에러 | `error_message` |
| `tab_change` | 탭 전환 | `tab`, `data_type` |
| `user_login` | 로그인 | `auth_provider` |
| `user_logout` | 로그아웃 | - |
| `schema_view` | 스키마 조회 | `data_type` |
| `contact_button_click` | 연락 버튼 클릭 | - |

---

## 6. 환경변수

`.env`:
```bash
VITE_MIXPANEL_TOKEN=your_mixpanel_token
VITE_POSTHOG_KEY=phc_your_posthog_key
VITE_POSTHOG_HOST=https://us.i.posthog.com
```

---

## 7. 확인 방법

### 7.1 개발 중 확인
1. 브라우저 DevTools (F12) → Console
2. `[Mixpanel] Track:` 또는 `[PostHog] Capture:` 로그 확인

### 7.2 대시보드 확인
- **Mixpanel**: https://mixpanel.com → Live View
- **PostHog**: https://app.posthog.com → Activity

---

## 8. 다른 프로젝트 적용 시 체크리스트

- [ ] Mixpanel/PostHog 프로젝트 생성
- [ ] `index.html`에 SDK 스니펫 추가
- [ ] `services/analytics.ts` 생성
- [ ] 핵심 사용자 여정 정의
- [ ] 이벤트 목록 작성
- [ ] 각 컴포넌트에 이벤트 호출 추가
- [ ] 콘솔에서 이벤트 전송 확인
- [ ] 대시보드에서 이벤트 수신 확인
