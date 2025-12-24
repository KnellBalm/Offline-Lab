# SQL Analytics Lab

> 프로덕트 분석가 양성을 위한 AI 기반 SQL 실습 플랫폼

[↑ 목차로](#목차)

---

## 목차

### 바로가기

| 개요 | 기획 | 개발 | 분석 |
|:----:|:----:|:----:|:----:|
| [서비스 소개](#1-서비스-소개) | [제품 명세](#6-제품-명세) | [개발 가이드](#7-개발-가이드) | [분석 가이드](#8-분석-가이드) |
| [주요 기능](#2-주요-기능) | [사용자 여정](#65-사용자-여정) | [로컬 개발](#73-로컬-개발) | [데이터 스키마](#84-데이터-스키마) |
| [빠른 시작](#5-빠른-시작) | [핵심 지표](#66-핵심-지표) | [시스템 구조](#74-시스템-상세-구조) | [문제 유형](#83-문제-유형) |

### 전체 목차

1. [서비스 소개](#1-서비스-소개)
2. [주요 기능](#2-주요-기능)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [기술 스택](#4-기술-스택)
5. [빠른 시작](#5-빠른-시작)
6. [제품 명세](#6-제품-명세)
7. [개발 가이드](#7-개발-가이드)
8. [분석 가이드](#8-분석-가이드)
9. [관련 문서](#9-관련-문서)
10. [로드맵](#10-로드맵)

[↑ 목차로](#목차)

---

## 1. 서비스 소개

### 1.1 문제 정의

| 기존 방식의 한계 | 본 서비스의 해결책 |
|-----------------|------------------|
| 교과서적 SQL 문법 학습만 가능 | 실무 비즈니스 질문 기반 문제 |
| 단순 SELECT 쿼리 연습 | 퍼널/코호트/리텐션 분석 |
| 정답 확인만 가능 | AI 기반 피드백 및 개선 제안 |
| 단일 도메인 데이터셋 | 5가지 프로덕트 타입 지원 |

### 1.2 타겟 사용자

| 세그먼트 | 니즈 | 기대 효과 |
|---------|------|----------|
| 취업 준비생 | 실무 경험 대체, 포트폴리오 | 면접 준비, 과제 수행 역량 |
| 주니어 분석가 | 분석 프레임워크 학습 | 시니어 레벨 역량 획득 |
| PM/기획자 | 데이터 기반 의사결정 | 직접 쿼리 작성 능력 |

### 1.3 핵심 가치

- **6가지 분석 유형** 마스터 → 어떤 도메인에서든 분석 업무 수행
- **AI 피드백** 활용 → 시니어 분석가 코드리뷰 효과
- **실제 데이터 패턴** 경험 → 면접/과제에 즉시 적용 가능

[↑ 목차로](#목차)

---

## 2. 주요 기능

### 2.1 핵심 기능

| 기능 | 설명 | 우선순위 |
|------|------|---------|
| PA 문제 풀이 | 정적 분석 문제 6개/일 | P0 |
| 스트림 문제 풀이 | 동적 로그 분석 문제 | P0 |
| SQL 에디터 | Monaco 기반 인터랙티브 에디터 | P0 |
| 자동 채점 | 결과 테이블 비교 기반 채점 | P0 |
| AI 피드백 | Gemini 기반 코드 리뷰 | P1 |
| 스키마 탐색기 | 테이블/컬럼 정보 조회 | P1 |

### 2.2 지원 프로덕트 타입

| 타입 | 도메인 | 이벤트 수 | 분석 초점 |
|------|--------|----------|----------|
| 커머스 | 이커머스 | 15개 | 퍼널, 장바구니 이탈 |
| 콘텐츠 | 미디어 플랫폼 | 12개 | 완독률, 구독 전환 |
| SaaS | B2B 소프트웨어 | 13개 | 활성화, 기능 사용률 |
| 커뮤니티 | 소셜 네트워크 | 11개 | 창작자/소비자 비율 |
| 핀테크 | 금융 서비스 | 12개 | 거래 성공률, KYC |

[↑ 목차로](#목차)

---

## 3. 시스템 아키텍처

### 3.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                           클라이언트 레이어                             ||
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    React SPA (Vite)                           │  │
│  │                       :5173                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ REST API
┌─────────────────────────────────▼───────────────────────────────────┐
│                           서비스 레이어                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI 백엔드                               │  │
│  │                       :8000                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└───────────┬─────────────────────┬─────────────────────┬─────────────┘
            │                     │                     │
┌───────────▼───────────┐ ┌───────▼───────┐ ┌───────────▼───────────┐
│     PostgreSQL        │ │    DuckDB     │ │     Gemini API        │
│      (메인 DB)         │ │   (분석용)      │ │    (AI 피드백)          │
└───────────────────────┘ └───────────────┘ └───────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────────────┐
│                          스케줄러                                   │
│                 (데이터 및 문제 자동 생성)                              │
└───────────────────────────────────────────────────────────────────┘
```

### 3.2 데이터 생성 파이프라인

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1단계: 프로덕트 타입 선택                                                 │
├─────────────────────────────────────────────────────────────────────┤
│   커머스     콘텐츠      SaaS     커뮤니티     핀테크                      │
│    20%       20%        20%        20%        20%                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2단계: 이벤트 생성 (전략 패턴)                                            │
├─────────────────────────────────────────────────────────────────────┤
│   BaseProductProfile                                                │
│         │                                                           │
│         ├── CommerceProfile.generate_session_events()               │
│         ├── ContentProfile.generate_session_events()                │
│         ├── SaaSProfile.generate_session_events()                   │
│         ├── CommunityProfile.generate_session_events()              │
│         └── FintechProfile.generate_session_events()                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3단계: 데이터 저장                                                      │
├─────────────────────────────────────────────────────────────────────┤
│   PostgreSQL: pa_users, pa_sessions, pa_events, pa_orders           │
│   DuckDB: stream_events, stream_daily_metrics                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4단계: 문제 생성 (Gemini AI)                                           │
├─────────────────────────────────────────────────────────────────────┤
│   프로덕트 타입 → 맞춤형 프롬프트 → 일 6개 문제 생성                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 설계 패턴

| 패턴 | 적용 위치 | 효과 |
|------|----------|------|
| 전략 패턴 | ProductProfile | 타입별 이벤트 생성 로직 분리 |
| 팩토리 패턴 | get_profile() | 문자열 기반 인스턴스 생성 |
| 저장소 패턴 | Engine 클래스 | DB 접근 추상화 |
| 서비스 레이어 | Generator, Grader | 비즈니스 로직 캡슐화 |

[↑ 목차로](#목차)

---

## 4. 기술 스택

### 4.1 프론트엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 18.x | UI 프레임워크 |
| Vite | 5.x | 빌드 도구 |
| TypeScript | 5.x | 타입 안전성 |
| Monaco Editor | - | SQL 코드 에디터 |
| Mixpanel | - | 이벤트 트래킹 |
| PostHog | - | 분석 및 세션 녹화 |

### 4.2 백엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.12+ | 런타임 |
| FastAPI | 0.115+ | API 서버 |
| Pydantic | 2.x | 데이터 검증 |
| Pandas | - | 데이터 처리 |
| psycopg2 | - | PostgreSQL 드라이버 |
| DuckDB | - | 분석용 데이터베이스 |

### 4.3 AI 및 분석

| 기술 | 용도 |
|------|------|
| Google Gemini Pro | 문제 생성, AI 피드백 |
| Mixpanel | 사용자 행동 분석 |
| PostHog | 이벤트 트래킹, 세션 녹화 |

### 4.4 인프라

| 기술 | 용도 |
|------|------|
| Docker Compose | 컨테이너 오케스트레이션 |
| PostgreSQL | 메인 데이터베이스 |
| DuckDB | 분석용 데이터베이스 |

[↑ 목차로](#목차)

---

## 5. 빠른 시작

### 5.1 사전 요구사항

```bash
# 필수
- Docker & Docker Compose
- Git

# 선택 (로컬 개발 시)
- Node.js 18+
- Python 3.12+
```

### 5.2 설치 및 실행

```bash
# 저장소 클론
git clone https://github.com/your-org/offline_lab.git
cd offline_lab

# 환경변수 설정
cp .env.example .env
# .env 파일 수정 (Gemini API 키 등)

# 서비스 시작
docker compose up -d

# 접속
# 프론트엔드: http://localhost:5173
# API 문서: http://localhost:8000/docs
# 관리자: http://localhost:5173/admin
```

### 5.3 초기 데이터 생성

```bash
docker compose exec backend python -c "
from generator.data_generator_advanced import run_pa
from problems.generator import generate as gen_pa
from engine.postgres_engine import PostgresEngine
from config.db import PostgresEnv
from datetime import date

run_pa()
pg = PostgresEngine(PostgresEnv().dsn())
gen_pa(date.today(), pg)
pg.close()
"
```

[↑ 목차로](#목차)

---

## 6. 제품 명세

### 6.1 서비스 컨셉

> PM/마케팅팀에서 슬랙으로 데이터 분석을 요청하는 실무 상황 시뮬레이션

**UX 원칙:**
1. 실무 톤앤매너: "PM팀입니다. ~분석 부탁드려요" 형식
2. 명확한 요구사항: 필요 컬럼, 정렬 기준, 기간 명시
3. 즉각적 피드백: 실행 결과 즉시 확인
4. AI 리뷰: 시니어 분석가 관점 개선점 제안

### 6.2 기능 목록

#### 사용자 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| PA 문제 풀이 | 정적 분석 문제 6개/일 | ✅ |
| 스트림 문제 풀이 | 동적 로그 분석 문제 | ✅ |
| SQL 에디터 | Monaco 기반 코드 작성 | ✅ |
| 자동 채점 | 결과 테이블 비교 채점 | ✅ |
| AI 피드백 | Gemini 기반 코드 리뷰 | ✅ |
| 스키마 탐색기 | 테이블/컬럼 정보 조회 | ✅ |
| 풀이 기록 | 제출 이력 관리 | ✅ |

#### 관리자 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| 문제 생성 | PA/스트림 문제 수동 생성 | ✅ |
| 데이터 갱신 | 사용자/이벤트 데이터 재생성 | ✅ |
| 스케줄러 모니터링 | 자동 생성 로그 확인 | ✅ |
| 데이터셋 버전 관리 | 생성 이력 조회 | ✅ |

### 6.3 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-001 | 사용자는 6개의 PA 문제를 조회할 수 있다 | P0 |
| FR-002 | 사용자는 SQL을 작성하고 실행할 수 있다 | P0 |
| FR-003 | 사용자는 정답을 제출하고 채점 결과를 확인할 수 있다 | P0 |
| FR-004 | 사용자는 AI 피드백을 요청할 수 있다 | P1 |
| FR-005 | 관리자는 문제를 수동으로 생성할 수 있다 | P1 |
| FR-006 | 시스템은 매일 자동으로 새 문제를 생성한다 | P1 |

### 6.4 비기능 요구사항

| ID | 요구사항 | 기준 |
|----|---------|------|
| NFR-001 | API 응답 시간 | < 500ms (p95) |
| NFR-002 | SQL 실행 시간 | < 5s (타임아웃) |
| NFR-003 | AI 피드백 응답 시간 | < 30s |
| NFR-004 | 동시 사용자 지원 | 100명 |

### 6.5 사용자 여정

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│   방문    │──▶│ 문제선택    │──▶│ SQL작성   │──▶│   제출    │──▶│  피드백   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
                    │              │              │              │
                    ▼              ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
              │  스키마   │   │ 실행결과   │  │  자동채점  │  │ AI리뷰    │
              │  조회     │  │ 미리보기   │  │          │  │          │
              └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 6.6 핵심 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| DAU | 일간 활성 사용자 | - |
| 문제 완료율 | 제출 수 / 조회 수 | > 40% |
| 정답률 | 정답 수 / 총 제출 수 | > 60% |
| 세션당 문제 수 | 평균 시도 문제 | > 2 |
| D1 리텐션 | 다음날 재방문율 | > 30% |

[↑ 목차로](#목차)

---

## 7. 개발 가이드

### 7.1 프로젝트 구조

```
offline_lab/
├── backend/                    # FastAPI 백엔드
│   ├── api/                    # API 라우터
│   │   ├── admin.py            # 관리자 API
│   │   ├── problems.py         # 문제 API
│   │   └── stats.py            # 통계 API
│   ├── schemas/                # Pydantic 스키마
│   └── main.py                 # FastAPI 앱
│
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── pages/              # 페이지 컴포넌트
│   │   ├── components/         # 공통 컴포넌트
│   │   ├── services/           # API 클라이언트, 분석
│   │   └── App.tsx             # 라우팅
│   └── index.html              # 진입점
│
├── generator/                  # 데이터 생성기
│   ├── product_config.py       # 프로덕트 타입 설정
│   ├── product_profiles/       # 전략 프로필
│   │   ├── base.py             # 베이스 클래스
│   │   ├── commerce.py         # 이커머스 프로필
│   │   ├── content.py          # 콘텐츠 프로필
│   │   ├── saas.py             # SaaS 프로필
│   │   ├── community.py        # 커뮤니티 프로필
│   │   └── fintech.py          # 핀테크 프로필
│   └── data_generator_advanced.py
│
├── problems/                   # 문제 관리
│   ├── generator.py            # PA 문제 생성
│   ├── generator_stream.py     # 스트림 문제 생성
│   ├── prompt_pa.py            # PA 프롬프트 (타입별)
│   └── gemini.py               # Gemini API 클라이언트
│
├── grader/                     # 채점 로직
│   └── sql_grader.py           # SQL 결과 비교
│
├── engine/                     # 데이터베이스 엔진
│   ├── postgres_engine.py      # PostgreSQL 래퍼
│   └── duckdb_engine.py        # DuckDB 래퍼
│
├── scheduler/                  # 스케줄러
│   └── main.py                 # 자동 실행
│
├── docs/                       # 문서
│   ├── EVENT_TRACKING_GUIDE.md
│   └── EVENT_DESIGN_GUIDELINE.md
│
├── docker-compose.yml          # 컨테이너 구성
├── .env                        # 환경변수
└── README.md                   # 이 문서
```

### 7.2 환경변수

```bash
# PostgreSQL
PG_HOST=db
PG_PORT=5432
PG_USER=palab
PG_PASSWORD=your_password
PG_DB=palab

# DuckDB
DUCKDB_PATH=data/pa_lab.duckdb

# Gemini AI
USE_GEMINI=1
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-pro

# 분석 도구 (프론트엔드)
VITE_MIXPANEL_TOKEN=your_mixpanel_token
VITE_POSTHOG_KEY=your_posthog_key
VITE_POSTHOG_HOST=https://us.i.posthog.com

# 생성기
PRODUCT_TYPES=commerce,content,saas,community,fintech
PA_NUM_USERS=50000
```

### 7.3 로컬 개발

```bash
# 전체 스택 (Docker)
docker compose up -d

# 프론트엔드만 (개발 모드)
cd frontend && npm install && npm run dev

# 백엔드만 (개발 모드)
cd backend && uvicorn main:app --reload --port 8000

# 스케줄러만
python scheduler/main.py
```

### 7.4 시스템 상세 구조

#### API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/problems/pa` | GET | PA 문제 목록 |
| `/problems/stream` | GET | 스트림 문제 목록 |
| `/problems/schema/{type}` | GET | 스키마 정보 |
| `/execute` | POST | SQL 실행 |
| `/submit` | POST | 정답 제출 |
| `/feedback` | POST | AI 피드백 요청 |
| `/admin/status` | GET | 시스템 상태 |
| `/admin/generate-problems` | POST | 문제 생성 |
| `/admin/refresh-data` | POST | 데이터 갱신 |

#### 요청 흐름

```
[사용자 SQL 입력]
        │
        ▼
[/execute API]
        │
        ▼
[PostgresEngine | DuckDBEngine]
        │
        ▼
[결과 반환]
        │
        ├──────────────────────▶ [/submit API]
        │                              │
        │                              ▼
        │                        [SQLGrader]
        │                              │
        │                              ▼
        │                      [정답 테이블 비교]
        │                              │
        │                              ▼
        │                       [정답 / 오답]
        │
        └──────────────────────▶ [/feedback API]
                                       │
                                       ▼
                               [Gemini API 호출]
                                       │
                                       ▼
                               [AI 피드백 반환]
```

### 7.5 확장 가이드

#### 새 프로덕트 타입 추가

```python
# 1. 프로필 생성 (generator/product_profiles/gaming.py)
from .base import BaseProductProfile, Event

class GamingProfile(BaseProductProfile):
    product_type = "gaming"
    
    def generate_session_events(self, user_id, session_id, base_time):
        events = []
        # 이벤트 생성 로직
        return events

# 2. 등록 (generator/product_profiles/__init__.py)
from .gaming import GamingProfile
PROFILE_MAP["gaming"] = GamingProfile

# 3. 설정 (generator/product_config.py)
PRODUCT_EVENTS["gaming"] = ["login", "play_start", "level_up", ...]
PRODUCT_PROBABILITIES["gaming"] = {"level_up": 0.3, ...}

# 4. 프롬프트 추가 (problems/prompt_pa.py)
PRODUCT_TYPE_CONTEXTS["gaming"] = {
    "name": "게임 플랫폼",
    "requesters": [...],
    "topics": [...]
}
```

[↑ 목차로](#목차)

---

## 8. 분석 가이드

### 8.1 시작하기

1. **PA 또는 스트림 탭 선택**
2. **문제 선택** (난이도별 정렬)
3. **스키마 확인** (테이블/컬럼 정보)
4. **SQL 작성** (Monaco 에디터)
5. **실행** (결과 미리보기)
6. **제출** (채점)
7. **피드백 요청** (AI 리뷰)

### 8.2 문제 예시

```
[PM팀 요청]
이번 주 신규 가입자의 Day 1 Retention을 알고 싶습니다.
결과에는 가입일(signup_date), 가입자 수(signups), 
D1 재방문자 수(d1_retained), D1 리텐션율(d1_retention) 컬럼이 필요합니다.
가입일 기준 내림차순 정렬해주세요.
```

### 8.3 문제 유형

| 유형 | 난이도 | 설명 | SQL 기법 |
|------|--------|------|----------|
| 퍼널 분석 | 쉬움~보통 | 전환율, 이탈 구간 | COUNT, GROUP BY |
| 리텐션 분석 | 보통 | Day N 리텐션 | DATE_TRUNC, LAG |
| 코호트 분석 | 보통~어려움 | 가입 시점별 패턴 | 윈도우 함수 |
| 세그먼트 분석 | 보통 | 그룹별 비교 | CASE WHEN, JOIN |
| 매출 분석 | 쉬움~어려움 | ARPU, LTV | SUM, AVG |
| 마케팅 분석 | 보통 | 채널별 성과 | UNION, CTE |

### 8.4 데이터 스키마

#### PA 테이블

```sql
pa_users (
    user_id TEXT PRIMARY KEY,
    signup_at TIMESTAMP,
    country TEXT,
    channel TEXT
)

pa_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES pa_users,
    started_at TIMESTAMP,
    device TEXT
)

pa_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES pa_users,
    session_id TEXT REFERENCES pa_sessions,
    event_time TIMESTAMP,
    event_name TEXT
)

pa_orders (
    order_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES pa_users,
    order_time TIMESTAMP,
    amount INT
)
```

#### 스트림 테이블

```sql
stream_events (
    user_id INT,
    session_id TEXT,
    event_name TEXT,
    event_time TIMESTAMP,
    device TEXT,
    channel TEXT
)

stream_daily_metrics (
    date DATE,
    revenue FLOAT,
    purchases INT
)
```

### 8.5 이벤트 목록 (커머스 예시)

| 이벤트 | 설명 |
|--------|------|
| `page_view` | 페이지 조회 |
| `view_product` | 상품 조회 |
| `view_review` | 리뷰 조회 |
| `add_to_cart` | 장바구니 추가 |
| `remove_from_cart` | 장바구니 제거 |
| `begin_checkout` | 결제 시작 |
| `apply_coupon` | 쿠폰 적용 |
| `purchase` | 구매 완료 |
| `reorder` | 재구매 |
| `refund_request` | 환불 요청 |
| `search` | 검색 |
| `wishlist_add` | 위시리스트 추가 |
| `compare_product` | 상품 비교 |
| `bundle_view` | 번들 상품 조회 |
| `notification_open` | 알림 열기 |

[↑ 목차로](#목차)

---

## 9. 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| 이벤트 트래킹 가이드 | [docs/EVENT_TRACKING_GUIDE.md](./docs/EVENT_TRACKING_GUIDE.md) | 구현 가이드 |
| 이벤트 설계 가이드라인 | [docs/EVENT_DESIGN_GUIDELINE.md](./docs/EVENT_DESIGN_GUIDELINE.md) | 설계 명세 |
| API 문서 | http://localhost:8000/docs | Swagger UI |

[↑ 목차로](#목차)

---

## 10. 로드맵

### v1.0 (현재)
- [x] PA/스트림 문제 풀이
- [x] 자동 채점
- [x] AI 피드백 (Gemini)
- [x] 5가지 프로덕트 타입
- [x] 이벤트 트래킹

### v1.1 (예정)
- [ ] 사용자 인증 (Google/Kakao)
- [ ] 문제 북마크
- [ ] 풀이 기록 저장
- [ ] 리더보드

### v2.0 (계획)
- [ ] 커스텀 문제 생성
- [ ] 팀/그룹 기능
- [ ] 학습 커리큘럼
- [ ] 수료증 발급

[↑ 목차로](#목차)

---

## 라이선스

Internal Use Only

[↑ 목차로](#목차)

---

## 기여 방법

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add some amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

[↑ 목차로](#목차)

---

**프로덕트 분석가를 꿈꾸는 모든 분들을 위해 ❤️**
