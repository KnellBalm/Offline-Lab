# Offline Analytics Lab

SQL 분석 연습 및 자동 채점 플랫폼입니다.

## 🎯 주요 기능

- **PA(Product Analytics) 쿼리 연습**: SQL 문제 풀이 및 자동 채점
- **Stream 로그 분석 업무**: 실무형 데이터 분석 과제
- **Gemini AI 피드백**: Google Gemini를 활용한 자동 피드백 생성
- **Streamlit 대시보드**: 웹 기반 사용자 인터페이스

## 📁 프로젝트 구조

```
offline_lab/
├── common/          # 공통 유틸리티 (로깅)
├── config/          # 설정 모듈
├── dashboard/       # Streamlit 웹 앱
├── data/            # DuckDB 데이터 저장소
├── engine/          # DB 엔진 (DuckDB, PostgreSQL)
├── generator/       # 데이터 및 문제 생성기
├── grader/          # 채점 로직
├── problems/        # 문제 정의 및 Gemini 통합
├── scripts/         # 실행 스크립트
├── services/        # 서비스 레이어
├── sql/             # SQL 초기화 스크립트
└── tests/           # 테스트
```

## 🚀 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_USER=pa_lab
PG_PASSWORD=your_password
PG_DB=pa_lab

# DuckDB
DUCKDB_PATH=data/pa_lab.duckdb

# Gemini (선택)
USE_GEMINI=0
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-1.5-pro
```

### 3. 데이터베이스 초기화

```bash
python scripts/init_postgres.py
```

### 4. 대시보드 실행

```bash
streamlit run dashboard/app.py
```

또는 Docker 사용:

```bash
docker-compose up -d
```

## 🧪 테스트

```bash
pytest tests/ -v
```

## 📊 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python 3.12+ |
| Database | PostgreSQL, DuckDB |
| Web UI | Streamlit |
| AI | Google Gemini |
| Testing | pytest |

## ⚠️ 보안 참고사항

- API 키는 반드시 환경 변수로 관리하세요
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- SQL Injection 방어가 적용되어 있습니다

## 📝 라이선스

Internal Use Only
