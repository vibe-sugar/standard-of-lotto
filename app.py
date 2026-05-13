"""
파일명: app.py
목적: 로또의 정석 - Flask 웹 애플리케이션 메인 진입점
      통계/최신회차 데이터는 클라이언트가 공식 API를 직접 호출
      서버는 (1) 페이지 렌더링, (2) 번호 생성, (3) 공식 API CORS 프록시 담당
작성일: 2026-05-13
버전: 2.0.0
"""

import os
import sys
import uuid
from datetime import datetime

import requests as req_lib
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS

from config.config import get_config
from utils.logger import setup_logger, app_logger
from utils.db import init_db_config, db_session
from utils.lotto_logic import (
    generate_random_numbers,
    generate_sum_range_numbers,
    generate_multiple_sets,
    get_number_color,
)

# 공식 로또 API URL
LOTTO_API_URL = (
    "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"
    "?srchStrLtEpsd=1&srchEndLtEpsd=9999"
)

# ── 앱 초기화 ─────────────────────────────────────────────────

def create_app():
    """
    Flask 애플리케이션 팩토리 함수

    Returns:
        설정이 완료된 Flask 앱 인스턴스
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg = get_config()
    app.config.from_object(cfg)

    # CORS 허용
    CORS(app)

    # DB 초기화 (선택적 — 없어도 핵심 기능 동작)
    try:
        init_db_config(
            host=cfg.DB_HOST,
            port=cfg.DB_PORT,
            user=cfg.DB_USER,
            password=cfg.DB_PASSWORD,
            db=cfg.DB_NAME,
        )
        app_logger.info("DB 연결 설정 완료")
    except Exception as e:
        app_logger.warning(f"DB 초기화 경고: {e} — DB 없이 기본 모드로 실행")

    # ── 라우트 등록 ────────────────────────────────────────────

    @app.route("/favicon.ico")
    def favicon():
        """파비콘 제공"""
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.svg",
            mimetype="image/svg+xml",
        )

    @app.route("/")
    def index():
        """메인 페이지"""
        win_stats = _get_win_stats()
        return render_template(
            "index.html",
            win_stats=win_stats,
            sum_ranges=cfg.SUM_RANGES,
        )

    @app.route("/recommend")
    def recommend():
        """번호 추천 페이지"""
        return render_template(
            "recommend.html",
            sum_ranges=cfg.SUM_RANGES,
        )

    @app.route("/statistics")
    def statistics():
        """통계 분석 페이지 — 데이터는 클라이언트가 /api/lotto/data 를 통해 직접 로드"""
        return render_template("statistics.html")

    @app.route("/history")
    def history():
        """당첨 번호 전체 조회 페이지 — 데이터는 클라이언트 로드"""
        return render_template("history.html")

    @app.route("/about")
    def about():
        """서비스 소개 페이지"""
        return render_template("about.html", sum_ranges=cfg.SUM_RANGES)

    # ── API 엔드포인트 ─────────────────────────────────────────

    @app.route("/api/lotto/data")
    def api_lotto_data():
        """
        공식 로또 API CORS 프록시
        클라이언트가 직접 dhlottery.co.kr 에 접근할 때 CORS 차단되는 경우를 방지.
        브라우저 → /api/lotto/data → dhlottery.co.kr

        Returns:
            JSON: 역대 전 회차 당첨 데이터 (list)
        """
        try:
            resp = req_lib.get(
                LOTTO_API_URL,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; LottoJeongseok/2.0)"},
            )
            resp.raise_for_status()
            payload = resp.json()
            lst = payload.get("data", {}).get("list", [])
            app_logger.info(f"[API] 공식 로또 데이터 프록시: {len(lst)}회차")
            return jsonify({"success": True, "data": lst, "total": len(lst)})
        except Exception as e:
            app_logger.error(f"[API] 공식 로또 API 호출 실패: {e}")
            return jsonify({"success": False, "message": str(e), "data": []}), 502

    @app.route("/api/recommend/random", methods=["POST"])
    def api_recommend_random():
        """
        완전 무작위 번호 추천 API

        Request JSON:
            count (int): 생성할 세트 수 (1~5, 기본값 1)

        Returns:
            JSON: 추천 번호 목록
        """
        try:
            data = request.get_json(silent=True) or {}
            count = min(max(int(data.get("count", 1)), 1), 5)
            sess_id = _get_session_id()

            sets = []
            for i in range(count):
                numbers = generate_random_numbers()
                _save_recommendation(sess_id, "random", numbers)
                sets.append({
                    "set_no": i + 1,
                    "numbers": numbers,
                    "total": sum(numbers),
                    "colors": [get_number_color(n) for n in numbers],
                })

            app_logger.info(f"[API] 랜덤 번호 {count}세트 생성 — session={sess_id[:8]}")
            return jsonify({"success": True, "sets": sets})

        except Exception as e:
            app_logger.error(f"[API] 랜덤 추천 오류: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/recommend/sum_range", methods=["POST"])
    def api_recommend_sum_range():
        """
        합산 구간 기반 번호 추천 API

        Request JSON:
            sum_min (int): 합산 최솟값
            sum_max (int): 합산 최댓값
            count   (int): 생성할 세트 수 (1~5, 기본값 1)

        Returns:
            JSON: 추천 번호 목록
        """
        try:
            data = request.get_json(silent=True) or {}
            sum_min = int(data.get("sum_min", 100))
            sum_max = int(data.get("sum_max", 170))
            count   = min(max(int(data.get("count", 1)), 1), 5)
            sess_id = _get_session_id()

            # 유효 범위 검증 (6개 최소합=21, 최대합=270)
            sum_min = max(21, min(sum_min, 270))
            sum_max = max(sum_min, min(sum_max, 270))

            sets = []
            for i in range(count):
                numbers = generate_sum_range_numbers(sum_min, sum_max)
                if numbers is None:
                    numbers = generate_random_numbers()
                _save_recommendation(sess_id, "sum_range", numbers, sum_min, sum_max)
                sets.append({
                    "set_no": i + 1,
                    "numbers": numbers,
                    "total": sum(numbers),
                    "colors": [get_number_color(n) for n in numbers],
                })

            app_logger.info(
                f"[API] 합산구간({sum_min}~{sum_max}) 번호 {count}세트 생성 — session={sess_id[:8]}"
            )
            return jsonify({"success": True, "sets": sets, "sum_min": sum_min, "sum_max": sum_max})

        except Exception as e:
            app_logger.error(f"[API] 합산구간 추천 오류: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/win_stats")
    def api_win_stats():
        """이 사이트에서 추천된 번호의 누적 당첨 통계 (DB 기반)"""
        stats = _get_win_stats()
        total = _get_total_recommendations()
        return jsonify({"success": True, "stats": stats, "total_recommendations": total})

    # ── Jinja2 필터 등록 ───────────────────────────────────────

    @app.template_filter("number_color")
    def number_color_filter(n):
        return get_number_color(n)

    @app.template_filter("format_currency")
    def format_currency_filter(value):
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)

    @app.template_filter("format_date")
    def format_date_filter(value):
        if value is None:
            return "-"
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                return value
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value)

    # ── 에러 핸들러 ────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(500)
    def internal_error(e):
        app_logger.error(f"서버 내부 오류: {e}")
        return render_template("error.html", code=500, message="서버 내부 오류가 발생했습니다."), 500

    return app


# ── DB 헬퍼 함수 ───────────────────────────────────────────────

def _get_session_id() -> str:
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def _save_recommendation(sess_id, rec_type, numbers, sum_min=None, sum_max=None):
    """추천 번호를 DB에 저장 (DB 오류 시 무시)"""
    try:
        sql = """
            INSERT INTO recommended_numbers
                (session_id, rec_type, sum_range_min, sum_range_max,
                 n1, n2, n3, n4, n5, n6, num_sum)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    sess_id, rec_type, sum_min, sum_max,
                    numbers[0], numbers[1], numbers[2],
                    numbers[3], numbers[4], numbers[5],
                    sum(numbers),
                ))
    except Exception as e:
        app_logger.debug(f"추천 번호 저장 스킵 (DB 미연결): {e}")


def _get_win_stats() -> dict:
    """사이트 누적 당첨 통계 조회"""
    default = {1: 0, 2: 0, 3: 0}
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT win_rank, COUNT(*) AS cnt
                    FROM recommended_numbers
                    WHERE win_rank IN (1, 2, 3)
                    GROUP BY win_rank
                """)
                rows = cur.fetchall()
        for r in rows:
            default[r["win_rank"]] = r["cnt"]
    except Exception:
        pass
    return default


def _get_total_recommendations() -> int:
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM recommended_numbers")
                row = cur.fetchone()
        return row["cnt"] if row else 0
    except Exception:
        return 0


# ── 서버 실행 ─────────────────────────────────────────────────

if __name__ == "__main__":
    app_logger.info("=" * 60)
    app_logger.info("로또의 정석 서버 시작")
    app_logger.info(f"포트: 15001")
    app_logger.info("=" * 60)

    app = create_app()
    try:
        app.run(host="0.0.0.0", port=15001, debug=False)
    except Exception as e:
        app_logger.error(f"서버 시작 실패: {e}")
        sys.exit(1)
