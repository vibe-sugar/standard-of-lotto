"""
파일명: utils/db.py
목적: MySQL DB 연결 및 공통 DB 유틸리티
작성일: 2026-05-13
버전: 1.0.0
"""

import pymysql
import pymysql.cursors
from contextlib import contextmanager
from utils.logger import app_logger

_db_config = {}


def init_db_config(host: str, port: int, user: str, password: str, db: str):
    """
    DB 접속 정보 초기화

    Args:
        host: DB 호스트
        port: DB 포트
        user: DB 사용자명
        password: DB 비밀번호
        db: DB 이름
    """
    global _db_config
    _db_config = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "db": db,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }
    app_logger.info(f"DB 설정 완료: {host}:{port}/{db}")


def get_connection():
    """
    새 DB 커넥션 반환

    Returns:
        pymysql.Connection 객체
    """
    if not _db_config:
        raise RuntimeError("DB 설정이 초기화되지 않았습니다. init_db_config()를 먼저 호출하세요.")
    try:
        conn = pymysql.connect(**_db_config)
        return conn
    except pymysql.Error as e:
        app_logger.error(f"DB 연결 실패: {e}")
        raise


@contextmanager
def db_session():
    """
    DB 세션 컨텍스트 매니저 (자동 커밋/롤백)

    Usage:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        app_logger.error(f"DB 세션 오류 (롤백 처리): {e}")
        raise
    finally:
        conn.close()


def execute_query(sql: str, params=None, fetchone: bool = False):
    """
    단순 SELECT 쿼리 실행 헬퍼

    Args:
        sql: 실행할 SQL
        params: 쿼리 파라미터
        fetchone: True면 단건, False면 전체 반환

    Returns:
        조회 결과 (dict 또는 list of dict)
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetchone:
                return cur.fetchone()
            return cur.fetchall()
