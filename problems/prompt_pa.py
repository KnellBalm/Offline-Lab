# problems/prompt_pa.py
"""
Gemini 문제 생성 프롬프트 - 실무형 프로덕트/비즈니스 분석
"""
from __future__ import annotations


def build_pa_prompt(data_summary: str, n: int = 6) -> str:
    """
    실무형 SQL 분석 문제 생성 프롬프트
    - 다른 팀/직무에서 요청하는 형태
    - 프로덕트 분석, 마케팅 분석, 비즈니스 분석 실무
    """
    return f"""
너는 스타트업의 시니어 데이터 분석가다.  
아래 데이터를 기반으로 **실무 SQL 분석 문제**를 출제하라.

[데이터 요약]
{data_summary}

[출제 요구사항]
1. 총 {n}개 문제
2. 난이도 분배: easy 2개, medium 2개, hard 2개
3. **반드시 다른 팀/직무가 요청하는 형태**로 작성
4. 정답 SQL은 작성하지 말 것

[문제 유형 (반드시 포함)]
- 리텐션 분석 (Day N Retention, Cohort Retention)
- 퍼널 분석 (전환율, 이탈 구간)
- 코호트 분석 (가입 시점별 행동 패턴)
- 매출 분석 (ARPU, LTV, 결제 전환)
- 세그먼트 분석 (사용자 그룹별 비교)
- 마케팅 분석 (채널별 성과, CAC)

[요청자 예시]
- PM팀: "이번 주 신규 기능의 전환율을 알고 싶습니다"
- 마케팅팀: "채널별 신규 가입자 리텐션을 비교해주세요"
- 경영진: "지난 달 대비 매출 트렌드를 분석해주세요"
- CX팀: "이탈 직전 사용자들의 행동 패턴이 궁금합니다"
- 그로스팀: "퍼널 병목 구간을 찾아주세요"

[JSON 스키마]
{{
  "problem_id": "unique_id_daily_001",
  "difficulty": "easy | medium | hard",
  "topic": "retention | funnel | cohort | revenue | segmentation | marketing",
  "requester": "요청팀 또는 직무 (예: PM팀, 마케팅팀)",
  "question": "실제 업무 요청처럼 작성 (예: 'OO팀입니다. XX 분석이 필요합니다...')",
  "context": "배경 설명 (왜 이 분석이 필요한지)",
  "expected_description": "기대 결과 테이블 설명",
  "expected_columns": ["col1", "col2", "..."],
  "sort_keys": ["정렬 기준 컬럼"],
  "hint": "힌트 (선택)"
}}

[중요]
- 문제는 **다른 팀에서 슬랙으로 요청하는 톤**으로 작성
- 실제 스타트업에서 발생하는 분석 요청처럼 구체적으로
- 초보자도 이해할 수 있도록 배경 설명 포함
- JSON 배열 형식으로만 출력

예시:
"PM팀입니다. 지난주 런칭한 결제 개선 기능의 성과를 파악하고 싶습니다. 
기능 적용 전후로 결제 전환율이 어떻게 변했는지 분석해주실 수 있을까요? 
가능하면 일별 추이와 전체 비교 둘 다 보고 싶습니다."
""".strip()


def build_pa_review_prompt(
    problem: dict,
    user_sql: str,
    is_correct: bool,
    error_message: str | None,
) -> str:
    """채점 피드백 프롬프트"""
    return f"""
너는 시니어 데이터 분석가다.
아래는 주니어 분석가가 제출한 SQL이다.

[문제]
{problem.get("question", "")}

[요청 배경]
{problem.get("context", "없음")}

[사용자 SQL]
{user_sql}

[정답 여부]
{"정답" if is_correct else "오답"}

[에러 메시지]
{error_message or "없음"}

[피드백 작성 기준]
1. 정답이든 오답이든 **실무 시니어처럼** 피드백
2. 오답이면 틀린 이유와 올바른 접근법 설명
3. 정답이어도 더 나은 방법이 있으면 제안
4. 쿼리 성능, 가독성, 실무 관례 관점 피드백
5. 이 분석을 실무에서 어떻게 활용할 수 있는지 팁
6. 친근하지만 전문적인 톤

[출력 형식]
마크다운, 항목별로 구분
""".strip()
