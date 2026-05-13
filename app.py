"""
파일명: app.py
목적: 로또의 정석 - Flask 웹 애플리케이션 메인 진입점
작성일: 2026-05-13
버전: 1.0.0
"""

import os
import sys
import uuid
from datetime import datetime

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

    # DB 초기화
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
        """메인 페이지 — 누적 당첨 통계 및 최신 당첨 번호 표시"""
        win_stats = _get_win_stats()
        latest = _get_latest_rounds(5)
        total_recommendations = _get_total_recommendations()
        return render_template(
            "index.html",
            win_stats=win_stats,
            latest=latest,
            total_recommendations=total_recommendations,
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
        """통계 분석 페이지"""
        freq_data = _get_number_frequency()
        sum_dist = _get_sum_distribution()
        recent_rounds = _get_latest_rounds(20)
        total_rounds = _get_total_rounds()
        return render_template(
            "statistics.html",
            freq_data=freq_data,
            sum_dist=sum_dist,
            recent_rounds=recent_rounds,
            total_rounds=total_rounds,
        )

    @app.route("/history")
    def history():
        """당첨 번호 조회 페이지"""
        page = request.args.get("page", 1, type=int)
        per_page = cfg.ROUNDS_PER_PAGE
        rounds, total_count = _get_rounds_paginated(page, per_page)
        total_pages = (total_count + per_page - 1) // per_page
        return render_template(
            "history.html",
            rounds=rounds,
            page=page,
            total_pages=total_pages,
            total_count=total_count,
        )

    @app.route("/about")
    def about():
        """서비스 소개 페이지"""
        return render_template("about.html", sum_ranges=cfg.SUM_RANGES)

    # ── API 엔드포인트 ─────────────────────────────────────────

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

    @app.route("/api/statistics/frequency")
    def api_frequency():
        """번호별 출현 빈도 통계 API"""
        try:
            data = _get_number_frequency()
            return jsonify({"success": True, "data": data})
        except Exception as e:
            app_logger.error(f"[API] 빈도 통계 오류: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/statistics/sum_distribution")
    def api_sum_distribution():
        """합산 구간별 분포 통계 API"""
        try:
            data = _get_sum_distribution()
            return jsonify({"success": True, "data": data})
        except Exception as e:
            app_logger.error(f"[API] 합산분포 통계 오류: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/latest_round")
    def api_latest_round():
        """최신 당첨 번호 조회 API"""
        try:
            latest = _get_latest_rounds(1)
            if latest:
                return jsonify({"success": True, "data": latest[0]})
            return jsonify({"success": True, "data": None})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/batch/run", methods=["POST"])
    def api_run_batch():
        """
        수동 배치 실행 API (관리용)
        운영 환경에서는 IP 제한 또는 인증 추가 권장
        """
        try:
            import subprocess
            batch_path = os.path.join(os.path.dirname(__file__), "batch", "fetch_lotto.py")
            subprocess.Popen([sys.executable, batch_path])
            app_logger.info("[API] 배치 수동 실행 요청")
            return jsonify({"success": True, "message": "배치가 백그라운드에서 실행되었습니다."})
        except Exception as e:
            app_logger.error(f"[API] 배치 실행 오류: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    # ── Jinja2 필터 등록 ───────────────────────────────────────

    @app.template_filter("number_color")
    def number_color_filter(n):
        """템플릿에서 사용할 번호 색상 필터"""
        return get_number_color(n)

    @app.template_filter("format_currency")
    def format_currency_filter(value):
        """통화 형식 포맷 필터 (예: 1,234,567)"""
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)

    @app.template_filter("format_date")
    def format_date_filter(value):
        """날짜 형식 포맷 필터 (YYYY-MM-DD)"""
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
    """현재 세션 ID 반환 (없으면 생성)"""
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
    """전체 추천 번호 생성 건수 조회"""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM recommended_numbers")
                row = cur.fetchone()
        return row["cnt"] if row else 0
    except Exception:
        return 0


def _get_latest_rounds(limit: int = 5) -> list:
    """최신 N개 회차 당첨 번호 조회"""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT lt_epsd, tm1_wn_no, tm2_wn_no, tm3_wn_no,
                           tm4_wn_no, tm5_wn_no, tm6_wn_no, bns_wn_no,
                           num_sum, lt_rfl_ymd, rnk1_wn_nope, rnk1_wn_amt
                    FROM lotto_results
                    ORDER BY lt_epsd DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
        # 날짜 직렬화
        for r in rows:
            if r.get("lt_rfl_ymd"):
                r["lt_rfl_ymd"] = str(r["lt_rfl_ymd"])
        return rows
    except Exception as e:
        app_logger.debug(f"최신 회차 조회 스킵: {e}")
        return []


def _get_total_rounds() -> int:
    """전체 회차 수 조회"""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM lotto_results")
                row = cur.fetchone()
        return row["cnt"] if row else 0
    except Exception:
        return 0


def _get_rounds_paginated(page: int, per_page: int) -> tuple:
    """페이지네이션 처리된 회차 목록 조회"""
    try:
        offset = (page - 1) * per_page
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM lotto_results")
                total = cur.fetchone()["cnt"]
                cur.execute("""
                    SELECT lt_epsd, tm1_wn_no, tm2_wn_no, tm3_wn_no,
                           tm4_wn_no, tm5_wn_no, tm6_wn_no, bns_wn_no,
                           num_sum, lt_rfl_ymd, rnk1_wn_nope, rnk1_wn_amt,
                           rnk2_wn_nope, rnk3_wn_nope
                    FROM lotto_results
                    ORDER BY lt_epsd DESC
                    LIMIT %s OFFSET %s
                """, (per_page, offset))
                rows = cur.fetchall()
        for r in rows:
            if r.get("lt_rfl_ymd"):
                r["lt_rfl_ymd"] = str(r["lt_rfl_ymd"])
        return rows, total
    except Exception as e:
        app_logger.debug(f"회차 목록 조회 스킵: {e}")
        return [], 0


def _get_number_frequency() -> list:
    """번호별 출현 빈도 조회"""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT num AS number,
                           SUM(cnt) AS count,
                           ROUND(SUM(cnt) / (SELECT COUNT(*) FROM lotto_results) * 100, 2) AS pct
                    FROM (
                        SELECT tm1_wn_no AS num, COUNT(*) AS cnt FROM lotto_results GROUP BY tm1_wn_no
                        UNION ALL SELECT tm2_wn_no, COUNT(*) FROM lotto_results GROUP BY tm2_wn_no
                        UNION ALL SELECT tm3_wn_no, COUNT(*) FROM lotto_results GROUP BY tm3_wn_no
                        UNION ALL SELECT tm4_wn_no, COUNT(*) FROM lotto_results GROUP BY tm4_wn_no
                        UNION ALL SELECT tm5_wn_no, COUNT(*) FROM lotto_results GROUP BY tm5_wn_no
                        UNION ALL SELECT tm6_wn_no, COUNT(*) FROM lotto_results GROUP BY tm6_wn_no
                    ) AS sub
                    GROUP BY num
                    ORDER BY num
                """)
                rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        app_logger.debug(f"빈도 통계 조회 스킵: {e}")
        return []


def _get_sum_distribution() -> list:
    """합산 구간별 분포 조회"""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT FLOOR(num_sum / 10) * 10       AS range_start,
                           FLOOR(num_sum / 10) * 10 + 9  AS range_end,
                           COUNT(*)                        AS count,
                           ROUND(COUNT(*) / (SELECT COUNT(*) FROM lotto_results) * 100, 2) AS pct
                    FROM lotto_results
                    GROUP BY range_start, range_end
                    ORDER BY range_start
                """)
                rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        app_logger.debug(f"합산분포 조회 스킵: {e}")
        return []


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
