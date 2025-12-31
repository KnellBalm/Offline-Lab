# problems/generator.py
"""PA 문제 생성기 - 월별 JSON + 정답 통합"""
import json
from pathlib import Path
from datetime import date
from problems.templates import build_expected_sql
from problems.prompt import build_prompt
from engine.postgres_engine import PostgresEngine
from common.logging import get_logger

logger = get_logger(__name__)

PROBLEM_DIR = Path("problems/monthly")
PROBLEM_DIR.mkdir(parents=True, exist_ok=True)

# 기존 daily 폴더도 유지 (호환성)
Path("problems/daily").mkdir(parents=True, exist_ok=True)

NUM_PROBLEM_SETS = 3  # 하루에 생성할 문제 세트 수

REQUIRED_FIELDS = {
    "problem_id",
    "difficulty",
    "topic",
    "question",
    "expected_columns",
    "sort_keys",
}


def load_monthly_file(month_str: str) -> dict:
    """월별 JSON 파일 로드 (없으면 빈 구조 반환)"""
    path = PROBLEM_DIR / f"pa_{month_str}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"month": month_str, "problems": []}


def save_monthly_file(month_str: str, data: dict):
    """월별 JSON 파일 저장"""
    path = PROBLEM_DIR / f"pa_{month_str}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"saved monthly file to {path}")


def get_expected_result(pg: PostgresEngine, answer_sql: str, limit: int = 1000) -> list:
    """정답 SQL 실행하여 결과 데이터 반환"""
    try:
        # 세미콜론 제거 (서브쿼리 감싸기 위해)
        clean_sql = answer_sql.strip().rstrip(";")
        # LIMIT 추가하여 너무 큰 결과 방지
        limited_sql = f"SELECT * FROM ({clean_sql}) AS _result LIMIT {limit}"
        df = pg.fetch_df(limited_sql)
        
        # DataFrame을 리스트로 변환
        result = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                # JSON 직렬화 가능하도록 변환
                if hasattr(val, 'isoformat'):  # datetime, date
                    record[col] = val.isoformat()
                elif hasattr(val, 'item'):  # numpy types
                    record[col] = val.item()
                else:
                    record[col] = val
            result.append(record)
        
        return result
    except Exception as e:
        logger.error(f"Failed to get expected result: {e}")
        return []


def generate_single_set(today: date, pg: PostgresEngine, set_index: int) -> list:
    """단일 문제 세트 생성 - 정답 데이터 포함"""
    logger.info(f"generating PA problems set {set_index} for {today}")
    problems = build_prompt()  # Gemini 호출
    logger.info(f"generated {len(problems)} problems from Gemini for set {set_index}")

    # 검증
    if len(problems) != 6:
        raise ValueError(f"문제는 반드시 6개여야 합니다. (세트 {set_index})")

    # 난이도 정규화 및 검증
    diff_cnt = {"easy": 0, "medium": 0, "hard": 0}
    for p in problems:
        if not REQUIRED_FIELDS.issubset(p.keys()):
            raise ValueError(f"문제 스키마 누락: {p}")
        # advanced -> hard 정규화
        if p["difficulty"] == "advanced":
            p["difficulty"] = "hard"
        if p["difficulty"] not in diff_cnt:
            logger.warning(f"Unknown difficulty: {p['difficulty']}, treating as medium")
            p["difficulty"] = "medium"
        diff_cnt[p["difficulty"]] += 1
        
        # 문제 ID에 날짜 + 세트 인덱스 포함
        original_id = p["problem_id"]
        p["problem_id"] = f"{today}_{original_id}_set{set_index}"
        p["date"] = today.isoformat()
        p["set_index"] = set_index
        
        # XP 값 설정
        if "xp_value" not in p:
            if p["difficulty"] == "easy":
                p["xp_value"] = 3
            elif p["difficulty"] == "medium":
                p["xp_value"] = 5
            else:  # hard
                p["xp_value"] = 8
        
        # 정답 결과 데이터 생성 (DB 테이블 대신 JSON에 저장)
        answer_sql = p.get("answer_sql")
        if answer_sql:
            expected_result = get_expected_result(pg, answer_sql)
            p["expected_result"] = expected_result
            p["expected_row_count"] = len(expected_result)
            logger.info(f"generated expected_result for {p['problem_id']} with {len(expected_result)} rows")
        else:
            logger.warning(f"answer_sql missing for {p['problem_id']}")
            p["expected_result"] = []
            p["expected_row_count"] = 0

    if any(v != 2 for v in diff_cnt.values()):
        logger.warning(f"난이도 분배가 2:2:2가 아님: {diff_cnt}")

    return problems


def generate(today: date, pg: PostgresEngine) -> str:
    """3개 문제 세트 생성 - 월별 JSON에 누적"""
    logger.info(f"start generating {NUM_PROBLEM_SETS} PA problem sets for {today}")
    
    month_str = today.strftime("%Y-%m")
    monthly_data = load_monthly_file(month_str)
    
    # 오늘 날짜 문제가 이미 있는지 확인
    existing_dates = set(p.get("date") for p in monthly_data["problems"])
    if today.isoformat() in existing_dates:
        logger.info(f"problems for {today} already exist in monthly file, skipping")
        return str(PROBLEM_DIR / f"pa_{month_str}.json")
    
    all_problems = []
    for set_idx in range(NUM_PROBLEM_SETS):
        try:
            problems = generate_single_set(today, pg, set_idx)
            all_problems.extend(problems)
        except Exception as e:
            logger.error(f"Failed to generate set {set_idx}: {e}")
    
    # 월별 파일에 추가
    monthly_data["problems"].extend(all_problems)
    save_monthly_file(month_str, monthly_data)
    
    # 기존 daily 폴더 호환을 위해 오늘 문제만 별도 저장
    daily_path = Path("problems/daily") / f"{today}.json"
    with open(daily_path, "w", encoding="utf-8") as f:
        json.dump(all_problems, f, ensure_ascii=False, indent=2)
    
    # 세트별 파일도 저장 (호환성)
    for set_idx in range(NUM_PROBLEM_SETS):
        set_problems = [p for p in all_problems if p.get("set_index") == set_idx]
        if set_problems:
            set_path = Path("problems/daily") / f"{today}_set{set_idx}.json"
            with open(set_path, "w", encoding="utf-8") as f:
                json.dump(set_problems, f, ensure_ascii=False, indent=2)
    
    logger.info(f"generated {len(all_problems)} problems for {today}")
    return str(PROBLEM_DIR / f"pa_{month_str}.json")
