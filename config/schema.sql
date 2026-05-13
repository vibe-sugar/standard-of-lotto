-- ============================================================
-- 파일명: config/schema.sql
-- 목적: 로또의 정석 MySQL DB DDL 및 초기 데이터 설정
-- 작성일: 2026-05-13
-- 버전: 1.0.0
-- ============================================================

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS lotto_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE lotto_db;

-- ============================================================
-- 1. 로또 당첨 번호 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS lotto_results (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '내부 ID',
    lt_epsd     INT UNSIGNED NOT NULL UNIQUE      COMMENT '회차 번호',
    tm1_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '1번 번호',
    tm2_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '2번 번호',
    tm3_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '3번 번호',
    tm4_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '4번 번호',
    tm5_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '5번 번호',
    tm6_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '6번 번호',
    bns_wn_no   TINYINT UNSIGNED NOT NULL         COMMENT '보너스 번호',
    -- 합산값 (검색 최적화)
    num_sum     SMALLINT UNSIGNED NOT NULL        COMMENT '6개 번호 합산',
    -- 추첨일
    lt_rfl_ymd  DATE NOT NULL                     COMMENT '추첨일(YYYYMMDD)',
    -- 1등 정보
    rnk1_wn_nope   INT UNSIGNED DEFAULT 0         COMMENT '1등 당첨자 수',
    rnk1_wn_amt    BIGINT UNSIGNED DEFAULT 0      COMMENT '1등 1인당 당첨금',
    rnk1_sum_wn_amt BIGINT UNSIGNED DEFAULT 0     COMMENT '1등 총 당첨금',
    -- 2등 정보
    rnk2_wn_nope   INT UNSIGNED DEFAULT 0         COMMENT '2등 당첨자 수',
    rnk2_wn_amt    BIGINT UNSIGNED DEFAULT 0      COMMENT '2등 1인당 당첨금',
    rnk2_sum_wn_amt BIGINT UNSIGNED DEFAULT 0     COMMENT '2등 총 당첨금',
    -- 3등 정보
    rnk3_wn_nope   INT UNSIGNED DEFAULT 0         COMMENT '3등 당첨자 수',
    rnk3_wn_amt    BIGINT UNSIGNED DEFAULT 0      COMMENT '3등 1인당 당첨금',
    rnk3_sum_wn_amt BIGINT UNSIGNED DEFAULT 0     COMMENT '3등 총 당첨금',
    -- 4등 정보
    rnk4_wn_nope   INT UNSIGNED DEFAULT 0         COMMENT '4등 당첨자 수',
    rnk4_wn_amt    BIGINT UNSIGNED DEFAULT 0      COMMENT '4등 당첨금(고정)',
    -- 5등 정보
    rnk5_wn_nope   INT UNSIGNED DEFAULT 0         COMMENT '5등 당첨자 수',
    rnk5_wn_amt    BIGINT UNSIGNED DEFAULT 0      COMMENT '5등 당첨금(고정)',
    -- 메타
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '레코드 생성일시',
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '레코드 수정일시',

    INDEX idx_lt_epsd   (lt_epsd),
    INDEX idx_num_sum   (num_sum),
    INDEX idx_lt_rfl_ymd (lt_rfl_ymd)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='로또 6/45 역대 당첨 번호';

-- ============================================================
-- 2. 사이트 추천 번호 저장 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS recommended_numbers (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '내부 ID',
    session_id      VARCHAR(64)  NOT NULL               COMMENT '사용자 세션 ID',
    rec_type        ENUM('random','sum_range') NOT NULL COMMENT '추천 방식 (random/sum_range)',
    sum_range_min   SMALLINT UNSIGNED DEFAULT NULL      COMMENT '합산 구간 최솟값',
    sum_range_max   SMALLINT UNSIGNED DEFAULT NULL      COMMENT '합산 구간 최댓값',
    n1  TINYINT UNSIGNED NOT NULL                       COMMENT '추천 번호 1',
    n2  TINYINT UNSIGNED NOT NULL                       COMMENT '추천 번호 2',
    n3  TINYINT UNSIGNED NOT NULL                       COMMENT '추천 번호 3',
    n4  TINYINT UNSIGNED NOT NULL                       COMMENT '추천 번호 4',
    n5  TINYINT UNSIGNED NOT NULL                       COMMENT '추천 번호 5',
    n6  TINYINT UNSIGNED NOT NULL                       COMMENT '추천 번호 6',
    num_sum         SMALLINT UNSIGNED NOT NULL          COMMENT '추천 번호 합산',
    -- 당첨 결과 (배치로 업데이트)
    matched_epsd    INT UNSIGNED DEFAULT NULL           COMMENT '매칭된 회차 (당첨 시)',
    win_rank        TINYINT UNSIGNED DEFAULT NULL       COMMENT '당첨 등수 (1~5, NULL=미당첨)',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '번호 생성 일시',
    checked_at      DATETIME DEFAULT NULL               COMMENT '당첨 확인 일시',

    INDEX idx_session   (session_id),
    INDEX idx_win_rank  (win_rank),
    INDEX idx_created   (created_at),
    INDEX idx_num_combo (n1, n2, n3, n4, n5, n6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='사이트에서 추천된 번호 이력';

-- ============================================================
-- 3. 사이트 누적 당첨 통계 뷰
-- ============================================================
CREATE OR REPLACE VIEW v_win_stats AS
SELECT
    win_rank,
    COUNT(*) AS win_count
FROM recommended_numbers
WHERE win_rank IS NOT NULL
GROUP BY win_rank
ORDER BY win_rank;

-- ============================================================
-- 4. 번호별 출현 빈도 뷰
-- ============================================================
CREATE OR REPLACE VIEW v_number_frequency AS
SELECT
    num,
    SUM(cnt) AS total_count,
    ROUND(SUM(cnt) / (SELECT COUNT(*) FROM lotto_results) * 100, 2) AS frequency_pct
FROM (
    SELECT tm1_wn_no AS num, COUNT(*) AS cnt FROM lotto_results GROUP BY tm1_wn_no
    UNION ALL
    SELECT tm2_wn_no, COUNT(*) FROM lotto_results GROUP BY tm2_wn_no
    UNION ALL
    SELECT tm3_wn_no, COUNT(*) FROM lotto_results GROUP BY tm3_wn_no
    UNION ALL
    SELECT tm4_wn_no, COUNT(*) FROM lotto_results GROUP BY tm4_wn_no
    UNION ALL
    SELECT tm5_wn_no, COUNT(*) FROM lotto_results GROUP BY tm5_wn_no
    UNION ALL
    SELECT tm6_wn_no, COUNT(*) FROM lotto_results GROUP BY tm6_wn_no
) AS sub
GROUP BY num
ORDER BY num;

-- ============================================================
-- 5. 합산 구간별 당첨 빈도 뷰
-- ============================================================
CREATE OR REPLACE VIEW v_sum_range_freq AS
SELECT
    FLOOR(num_sum / 10) * 10        AS range_start,
    FLOOR(num_sum / 10) * 10 + 9    AS range_end,
    COUNT(*)                         AS draw_count,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM lotto_results) * 100, 2) AS pct
FROM lotto_results
GROUP BY range_start, range_end
ORDER BY range_start;

-- ============================================================
-- 6. 배치 실행 로그 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS batch_logs (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_name  VARCHAR(100) NOT NULL                   COMMENT '배치 이름',
    status      ENUM('success','fail','running') NOT NULL COMMENT '실행 결과',
    fetched_cnt INT UNSIGNED DEFAULT 0                  COMMENT '수집된 회차 수',
    message     TEXT DEFAULT NULL                       COMMENT '오류/결과 메시지',
    started_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at    DATETIME DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='배치 실행 로그';

-- ============================================================
-- 7. DB 사용자 생성 (최초 1회 실행)
-- ============================================================
-- root 권한으로 실행:
-- CREATE USER IF NOT EXISTS 'lotto_user'@'localhost' IDENTIFIED BY 'lotto_pass';
-- GRANT ALL PRIVILEGES ON lotto_db.* TO 'lotto_user'@'localhost';
-- FLUSH PRIVILEGES;
