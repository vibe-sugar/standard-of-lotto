"""
파일명: batch/fetch_lotto.py
목적: 로또 역대 당첨 번호 수집 배치 프로그램
      - 공식 API 호출 후 MySQL DB에 저장/업데이트
      - 주 1회 cron 또는 수동 실행
작성일: 2026-05-13
버전: 1.0.0
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import get_config
from utils.logger import batch_logger
from utils.db import init_db_config, db_session

# ── 상수 ──────────────────────────────────────────────────────
LOTTO_API_URL = (
    "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"
    "?srchStrLtEpsd=1&srchEndLtEpsd=9999"
)
REQUEST_TIMEOUT = 30   # 초
RETRY_COUNT = 3        # API 재시도 횟수
RETRY_DELAY = 5        # 재시도 대기 시간(초)


# ── 데이터 수집 ───────────────────────────────────────────────

def fetch_lotto_data() -> list:
    """
    공식 로또 API 호출 후 전체 회차 데이터 반환

    Returns:
        회차별 당첨 데이터 리스트 (dict)
    Raises:
        Exception: API 호출 실패 시
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        ),
        "Referer": "https://www.dhlottery.co.kr/",
        "Accept": "application/json, text/plain, */*",
    }

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            batch_logger.info(f"API 호출 시도 {attempt}/{RETRY_COUNT}: {LOTTO_API_URL}")
            response = requests.get(
                LOTTO_API_URL,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # 응답 구조 검증
            raw_list = data.get("data", {}).get("list", [])
            if not raw_list:
                raise ValueError("API 응답에 데이터가 없습니다.")

            batch_logger.info(f"API 수집 완료: {len(raw_list)}개 회차")
            return raw_list

        except requests.RequestException as e:
            batch_logger.warning(f"API 호출 오류 (시도 {attempt}): {e}")
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
            else:
                raise
        except (json.JSONDecodeError, ValueError) as e:
            batch_logger.error(f"API 응답 파싱 오류: {e}")
            raise


# ── DB 저장 ───────────────────────────────────────────────────

def _parse_date(ymd_str: str):
    """
    'YYYYMMDD' 형식 문자열을 datetime.date로 변환

    Args:
        ymd_str: 예) '20260509'
    Returns:
        datetime.date 또는 None
    """
    try:
        return datetime.strptime(str(ymd_str), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


def upsert_lotto_results(raw_list: list) -> int:
    """
    API 데이터를 DB에 UPSERT (신규 삽입 + 기존 업데이트)

    Args:
        raw_list: API 응답 리스트

    Returns:
        처리된 레코드 수
    """
    sql = """
        INSERT INTO lotto_results (
            lt_epsd, tm1_wn_no, tm2_wn_no, tm3_wn_no,
            tm4_wn_no, tm5_wn_no, tm6_wn_no, bns_wn_no,
            num_sum, lt_rfl_ymd,
            rnk1_wn_nope, rnk1_wn_amt, rnk1_sum_wn_amt,
            rnk2_wn_nope, rnk2_wn_amt, rnk2_sum_wn_amt,
            rnk3_wn_nope, rnk3_wn_amt, rnk3_sum_wn_amt,
            rnk4_wn_nope, rnk4_wn_amt,
            rnk5_wn_nope, rnk5_wn_amt
        ) VALUES (
            %(lt_epsd)s, %(tm1)s, %(tm2)s, %(tm3)s,
            %(tm4)s, %(tm5)s, %(tm6)s, %(bns)s,
            %(num_sum)s, %(lt_rfl_ymd)s,
            %(rnk1_nope)s, %(rnk1_amt)s, %(rnk1_sum)s,
            %(rnk2_nope)s, %(rnk2_amt)s, %(rnk2_sum)s,
            %(rnk3_nope)s, %(rnk3_amt)s, %(rnk3_sum)s,
            %(rnk4_nope)s, %(rnk4_amt)s,
            %(rnk5_nope)s, %(rnk5_amt)s
        )
        ON DUPLICATE KEY UPDATE
            tm1_wn_no       = VALUES(tm1_wn_no),
            tm2_wn_no       = VALUES(tm2_wn_no),
            tm3_wn_no       = VALUES(tm3_wn_no),
            tm4_wn_no       = VALUES(tm4_wn_no),
            tm5_wn_no       = VALUES(tm5_wn_no),
            tm6_wn_no       = VALUES(tm6_wn_no),
            bns_wn_no       = VALUES(bns_wn_no),
            num_sum         = VALUES(num_sum),
            lt_rfl_ymd      = VALUES(lt_rfl_ymd),
            rnk1_wn_nope    = VALUES(rnk1_wn_nope),
            rnk1_wn_amt     = VALUES(rnk1_wn_amt),
            rnk1_sum_wn_amt = VALUES(rnk1_sum_wn_amt),
            rnk2_wn_nope    = VALUES(rnk2_wn_nope),
            rnk2_wn_amt     = VALUES(rnk2_wn_amt),
            rnk2_sum_wn_amt = VALUES(rnk2_sum_wn_amt),
            rnk3_wn_nope    = VALUES(rnk3_wn_nope),
            rnk3_wn_amt     = VALUES(rnk3_wn_amt),
            rnk3_sum_wn_amt = VALUES(rnk3_sum_wn_amt),
            rnk4_wn_nope    = VALUES(rnk4_wn_nope),
            rnk4_wn_amt     = VALUES(rnk4_wn_amt),
            rnk5_wn_nope    = VALUES(rnk5_wn_nope),
            rnk5_wn_amt     = VALUES(rnk5_wn_amt),
            updated_at      = CURRENT_TIMESTAMP
    """

    processed = 0
    with db_session() as conn:
        with conn.cursor() as cur:
            for row in raw_list:
                try:
                    n1 = int(row["tm1WnNo"])
                    n2 = int(row["tm2WnNo"])
                    n3 = int(row["tm3WnNo"])
                    n4 = int(row["tm4WnNo"])
                    n5 = int(row["tm5WnNo"])
                    n6 = int(row["tm6WnNo"])

                    params = {
                        "lt_epsd":   int(row["ltEpsd"]),
                        "tm1": n1, "tm2": n2, "tm3": n3,
                        "tm4": n4, "tm5": n5, "tm6": n6,
                        "bns":       int(row["bnsWnNo"]),
                        "num_sum":   n1 + n2 + n3 + n4 + n5 + n6,
                        "lt_rfl_ymd": _parse_date(row.get("ltRflYmd")),
                        "rnk1_nope": int(row.get("rnk1WnNope", 0)),
                        "rnk1_amt":  int(row.get("rnk1WnAmt", 0)),
                        "rnk1_sum":  int(row.get("rnk1SumWnAmt", 0)),
                        "rnk2_nope": int(row.get("rnk2WnNope", 0)),
                        "rnk2_amt":  int(row.get("rnk2WnAmt", 0)),
                        "rnk2_sum":  int(row.get("rnk2SumWnAmt", 0)),
                        "rnk3_nope": int(row.get("rnk3WnNope", 0)),
                        "rnk3_amt":  int(row.get("rnk3WnAmt", 0)),
                        "rnk3_sum":  int(row.get("rnk3SumWnAmt", 0)),
                        "rnk4_nope": int(row.get("rnk4WnNope", 0)),
                        "rnk4_amt":  int(row.get("rnk4WnAmt", 0)),
                        "rnk5_nope": int(row.get("rnk5WnNope", 0)),
                        "rnk5_amt":  int(row.get("rnk5WnAmt", 0)),
                    }
                    cur.execute(sql, params)
                    processed += 1

                except (KeyError, TypeError, ValueError) as e:
                    batch_logger.warning(f"회차 {row.get('ltEpsd', '?')} 파싱 오류: {e}")

    batch_logger.info(f"DB UPSERT 완료: {processed}건")
    return processed


# ── 당첨 확인 배치 ─────────────────────────────────────────────

def check_winning_numbers():
    """
    recommended_numbers 테이블에서 미확인 번호를 조회하여
    실제 당첨 여부(1~5등)를 확인하고 win_rank를 업데이트
    """
    select_sql = """
        SELECT r.id, r.n1, r.n2, r.n3, r.n4, r.n5, r.n6,
               r.matched_epsd
        FROM recommended_numbers r
        WHERE r.win_rank IS NULL
          AND r.created_at < NOW() - INTERVAL 7 DAY
        LIMIT 500
    """

    update_sql = """
        UPDATE recommended_numbers
        SET win_rank = %(rank)s,
            matched_epsd = %(epsd)s,
            checked_at = NOW()
        WHERE id = %(id)s
    """

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            pending = cur.fetchall()

            if not pending:
                batch_logger.info("당첨 확인 대상 없음")
                return

            # 모든 당첨 번호 로드
            cur.execute("""
                SELECT lt_epsd, tm1_wn_no, tm2_wn_no, tm3_wn_no,
                       tm4_wn_no, tm5_wn_no, tm6_wn_no, bns_wn_no
                FROM lotto_results
                ORDER BY lt_epsd DESC
            """)
            all_results = cur.fetchall()

            checked = 0
            for rec in pending:
                rec_nums = {rec["n1"], rec["n2"], rec["n3"],
                            rec["n4"], rec["n5"], rec["n6"]}

                for draw in all_results:
                    draw_nums = {
                        draw["tm1_wn_no"], draw["tm2_wn_no"],
                        draw["tm3_wn_no"], draw["tm4_wn_no"],
                        draw["tm5_wn_no"], draw["tm6_wn_no"],
                    }
                    bonus = draw["bns_wn_no"]
                    match_cnt = len(rec_nums & draw_nums)

                    rank = None
                    if match_cnt == 6:
                        rank = 1
                    elif match_cnt == 5 and bonus in rec_nums:
                        rank = 2
                    elif match_cnt == 5:
                        rank = 3
                    elif match_cnt == 4:
                        rank = 4
                    elif match_cnt == 3:
                        rank = 5

                    if rank is not None:
                        cur.execute(update_sql, {
                            "rank": rank,
                            "epsd": draw["lt_epsd"],
                            "id":   rec["id"],
                        })
                        checked += 1
                        break  # 가장 높은 등수만 기록

            batch_logger.info(f"당첨 확인 완료: {checked}건 업데이트")


# ── 배치 실행 기록 ─────────────────────────────────────────────

def log_batch_result(conn, batch_name: str, status: str, fetched: int, message: str = ""):
    """배치 실행 결과를 batch_logs 테이블에 기록"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO batch_logs (batch_name, status, fetched_cnt, message, ended_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (batch_name, status, fetched, message)
            )
        conn.commit()
    except Exception as e:
        batch_logger.warning(f"배치 로그 저장 실패: {e}")


# ── 메인 진입점 ───────────────────────────────────────────────

def run_batch():
    """
    전체 배치 실행 진입점
    1. API에서 데이터 수집
    2. DB UPSERT
    3. 추천 번호 당첨 확인
    """
    cfg = get_config()
    init_db_config(
        host=cfg.DB_HOST,
        port=cfg.DB_PORT,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
        db=cfg.DB_NAME,
    )

    batch_logger.info("=" * 60)
    batch_logger.info("로또 데이터 수집 배치 시작")
    batch_logger.info("=" * 60)

    status = "success"
    fetched = 0
    message = ""

    try:
        # 1) API 호출
        raw_list = fetch_lotto_data()

        # 2) DB UPSERT
        fetched = upsert_lotto_results(raw_list)

        # 3) 당첨 확인
        check_winning_numbers()

        batch_logger.info(f"배치 완료 — 처리 건수: {fetched}")

    except Exception as e:
        status = "fail"
        message = str(e)
        batch_logger.error(f"배치 실패: {e}")
        sys.exit(1)

    finally:
        # 배치 로그 저장
        try:
            from utils.db import get_connection
            conn = get_connection()
            log_batch_result(conn, "fetch_lotto", status, fetched, message)
            conn.close()
        except Exception:
            pass

    batch_logger.info("배치 정상 종료")


if __name__ == "__main__":
    run_batch()
