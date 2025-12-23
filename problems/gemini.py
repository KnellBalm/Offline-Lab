# problems/gemini.py
from __future__ import annotations

import os
import json
import re
from dotenv import load_dotenv
from google import genai

from common.logging import get_logger

logger = get_logger(__name__)

load_dotenv()

# -------------------------------------------------
# Gemini Client
# -------------------------------------------------
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# -------------------------------------------------
# 1️⃣ 문제 출제용 (JSON 강제)
# -------------------------------------------------
def call_gemini_json(prompt: str) -> list[dict]:
    logger.info("calling gemini for json generation")

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    raw_text = response.text.strip()
    logger.debug(f"raw gemini response:\n{raw_text}")

    # ------------------------------------------------
    # 1. ```json ... ``` 코드블록 우선 추출
    # ------------------------------------------------
    code_block = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        raw_text,
        re.DOTALL | re.IGNORECASE,
    )

    if code_block:
        json_text = code_block.group(1).strip()
    else:
        # ------------------------------------------------
        # 2. 코드블록이 없으면, JSON 배열/객체 직접 추출
        # ------------------------------------------------
        json_match = re.search(
            r"(\[\s*\{.*?\}\s*\]|\{.*?\})",
            raw_text,
            re.DOTALL,
        )
        if not json_match:
            logger.error("No JSON structure found in Gemini response")
            raise RuntimeError(f"Gemini 응답에서 JSON을 찾지 못했습니다:\n{raw_text}")

        json_text = json_match.group(1).strip()

    # ------------------------------------------------
    # 3. JSON 파싱
    # ------------------------------------------------
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error("Gemini JSON parse failed")
        logger.error(f"extracted json text:\n{json_text}")
        raise RuntimeError(
            f"Gemini JSON 파싱 실패\n{json_text}"
        ) from e


# -------------------------------------------------
# 2️⃣ PA 채점용 (자연어 피드백)
# -------------------------------------------------
def grade_pa_submission(
    *,
    problem_id: str,
    sql_text: str,
    is_correct: bool,
    diff: str | None = None,
    error: str | None = None,
    note: str | None = None,
) -> str:
    """
    PA 제출 채점:
    - SQL 에러
    - 논리 오류
    - 실무 관점 피드백
    """

    logger.info(f"grading pa submission problem_id={problem_id}")

    # ---------------------------------------------
    # 프롬프트 구성
    # ---------------------------------------------
    prompt = f"""
너는 시니어 데이터 분석가다.
아래는 실무 PA(제품 분석) SQL 과제의 제출 결과다.

[문제 ID]
{problem_id}

[사용자 SQL]
{sql_text}

[사용자 메모]
{note or "없음"}

[실행 결과 요약]
- 정답 여부: {"정답" if is_correct else "오답"}
- SQL 에러: {error or "없음"}
- 결과 차이: {diff or "없음"}

[채점 기준]
1. SQL 문법 오류가 있다면 그것을 먼저 지적한다.
2. 논리적으로 왜 틀렸는지 또는 왜 맞았는지 설명한다.
3. 실무에서 더 좋은 접근이나 보완할 점을 제안한다.
4. 정답이어도 개선 포인트가 있으면 반드시 언급한다.
5. 불필요한 장황한 설명은 피하고, 실무 피드백 톤으로 작성한다.

[출력 형식]
- 자연어 텍스트
- 항목별로 명확하게 구분
"""

    # ---------------------------------------------
    # Gemini 호출
    # ---------------------------------------------
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    feedback = response.text.strip()

    logger.info("gemini grading completed")

    return feedback
