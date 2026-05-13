"""
파일명: config/config.py
목적: 애플리케이션 전역 설정 파일
작성일: 2026-05-13
버전: 1.0.0
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """기본 설정 클래스"""

    # 앱 기본 설정
    SECRET_KEY = os.environ.get("SECRET_KEY", "lotto-jeongseok-secret-key-2026")
    DEBUG = False
    TESTING = False

    # MySQL DB 설정
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "lotto_user")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "lotto_pass")
    DB_NAME = os.environ.get("DB_NAME", "lotto_db")

    # SQLAlchemy 설정
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # 로또 API 설정
    LOTTO_API_URL = (
        "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"
        "?srchStrLtEpsd=1&srchEndLtEpsd=9999"
    )

    # 로그 설정
    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log.txt")
    LOG_LEVEL = "INFO"

    # 페이지네이션
    ROUNDS_PER_PAGE = 20

    # 번호 추천 설정
    LOTTO_MIN = 1
    LOTTO_MAX = 45
    LOTTO_COUNT = 6

    # 합산 구간 버튼 정의 (구간명: [최솟값, 최댓값])
    SUM_RANGES = [
        {"label": "~100", "min": 21, "max": 100},
        {"label": "101~110", "min": 101, "max": 110},
        {"label": "111~120", "min": 111, "max": 120},
        {"label": "121~130", "min": 121, "max": 130},
        {"label": "131~140", "min": 131, "max": 140},
        {"label": "141~150", "min": 141, "max": 150},
        {"label": "151~160", "min": 151, "max": 160},
        {"label": "161~170", "min": 161, "max": 170},
        {"label": "171~180", "min": 171, "max": 180},
        {"label": "181~190", "min": 181, "max": 190},
        {"label": "191~200", "min": 191, "max": 200},
        {"label": "201~", "min": 201, "max": 270},
    ]


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """운영 환경 설정"""
    DEBUG = False
    LOG_LEVEL = "WARNING"


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True


# 환경별 설정 매핑
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """현재 환경에 맞는 설정 반환"""
    env = os.environ.get("FLASK_ENV", "default")
    return config_map.get(env, config_map["default"])
