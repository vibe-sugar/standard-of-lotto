"""
파일명: utils/lotto_logic.py
목적: 로또 번호 추천 핵심 로직 (랜덤, 합산구간, 빈도기반)
작성일: 2026-05-13
버전: 1.0.0
"""

import random
from typing import List, Tuple, Optional
from utils.logger import app_logger


def generate_random_numbers() -> List[int]:
    """
    완전 무작위 로또 번호 6개 생성 (1~45, 중복 없음, 오름차순)

    Returns:
        정렬된 6개 번호 리스트
    """
    numbers = random.sample(range(1, 46), 6)
    numbers.sort()
    app_logger.debug(f"랜덤 번호 생성: {numbers}")
    return numbers


def generate_sum_range_numbers(sum_min: int, sum_max: int, max_attempts: int = 10000) -> Optional[List[int]]:
    """
    지정된 합산 구간에 맞는 로또 번호 6개 생성

    번호의 합이 sum_min ~ sum_max 범위에 들어오도록 랜덤 샘플링.
    최대 max_attempts 회 시도 후 실패하면 None 반환.

    Args:
        sum_min: 합산 최솟값
        sum_max: 합산 최댓값
        max_attempts: 최대 시도 횟수

    Returns:
        조건에 맞는 6개 번호 리스트, 실패 시 None
    """
    for attempt in range(max_attempts):
        numbers = random.sample(range(1, 46), 6)
        total = sum(numbers)
        if sum_min <= total <= sum_max:
            numbers.sort()
            app_logger.debug(f"합산구간({sum_min}~{sum_max}) 번호 생성 성공 (시도 {attempt+1}회): {numbers}, 합={total}")
            return numbers

    app_logger.warning(f"합산구간({sum_min}~{sum_max}) 번호 생성 실패 ({max_attempts}회 시도)")
    return None


def generate_multiple_sets(count: int = 5, rec_type: str = "random",
                           sum_min: int = None, sum_max: int = None) -> List[dict]:
    """
    여러 세트의 로또 번호를 한 번에 생성

    Args:
        count: 생성할 세트 수
        rec_type: 'random' 또는 'sum_range'
        sum_min: 합산 최솟값 (sum_range 방식 시 필요)
        sum_max: 합산 최댓값 (sum_range 방식 시 필요)

    Returns:
        번호 세트 목록 (각 딕셔너리: numbers, total, rec_type)
    """
    result = []
    for i in range(count):
        if rec_type == "sum_range" and sum_min is not None and sum_max is not None:
            numbers = generate_sum_range_numbers(sum_min, sum_max)
            if numbers is None:
                # 폴백: 순수 랜덤
                numbers = generate_random_numbers()
        else:
            numbers = generate_random_numbers()

        result.append({
            "set_no": i + 1,
            "numbers": numbers,
            "total": sum(numbers),
            "rec_type": rec_type,
        })

    return result


def analyze_sum_distribution(lotto_data: List[dict]) -> List[dict]:
    """
    역대 당첨 데이터에서 합산 구간별 분포 계산

    Args:
        lotto_data: DB에서 조회한 당첨 데이터 리스트
                    (각 딕셔너리에 num_sum 필드 필요)

    Returns:
        구간별 통계 리스트 (range_start, range_end, count, pct)
    """
    if not lotto_data:
        return []

    total = len(lotto_data)
    bucket: dict = {}

    for row in lotto_data:
        s = row.get("num_sum", 0)
        # 10 단위 버킷
        key = (s // 10) * 10
        bucket[key] = bucket.get(key, 0) + 1

    result = []
    for start in sorted(bucket.keys()):
        cnt = bucket[start]
        result.append({
            "range_start": start,
            "range_end": start + 9,
            "count": cnt,
            "pct": round(cnt / total * 100, 2),
        })

    return result


def analyze_number_frequency(lotto_data: List[dict]) -> List[dict]:
    """
    역대 당첨 데이터에서 번호별 출현 빈도 계산

    Args:
        lotto_data: DB에서 조회한 당첨 데이터 리스트
                    (tm1_wn_no ~ tm6_wn_no 필드 필요)

    Returns:
        번호별 빈도 리스트 (number, count, pct)
    """
    if not lotto_data:
        return []

    total_draws = len(lotto_data)
    freq = {i: 0 for i in range(1, 46)}

    for row in lotto_data:
        for key in ["tm1_wn_no", "tm2_wn_no", "tm3_wn_no",
                    "tm4_wn_no", "tm5_wn_no", "tm6_wn_no"]:
            num = row.get(key)
            if num and 1 <= num <= 45:
                freq[num] += 1

    result = []
    for num in range(1, 46):
        cnt = freq[num]
        result.append({
            "number": num,
            "count": cnt,
            "pct": round(cnt / total_draws * 100, 2) if total_draws > 0 else 0,
        })

    return result


def get_number_color(number: int) -> str:
    """
    로또 번호에 따른 색상 반환 (공식 로또 색상 체계)

    Args:
        number: 로또 번호 (1~45)

    Returns:
        CSS 색상 클래스명
    """
    if 1 <= number <= 10:
        return "yellow"
    elif 11 <= number <= 20:
        return "blue"
    elif 21 <= number <= 30:
        return "red"
    elif 31 <= number <= 40:
        return "gray"
    else:
        return "green"
