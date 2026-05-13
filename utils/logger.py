"""
파일명: utils/logger.py
목적: 애플리케이션 공통 로깅 유틸리티
작성일: 2026-05-13
버전: 1.0.0
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(name: str = "lotto", log_file: str = None, level: str = "INFO") -> logging.Logger:
    """
    로거 설정 및 반환

    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (None이면 프로젝트 루트 log.txt 사용)
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        설정된 Logger 인스턴스
    """
    if log_file is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(base_dir, "log.txt")

    logger = logging.getLogger(name)

    # 이미 핸들러가 설정된 경우 중복 방지
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 포맷 설정 (타임스탬프 포함)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.addHandler(console_handler)

    # 파일 핸들러 (최대 10MB, 최대 5개 백업)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"로그 파일 핸들러 설정 실패: {e}")

    return logger


# 전역 기본 로거
app_logger = setup_logger("lotto_app")
batch_logger = setup_logger("lotto_batch")
