# 로또의 정석 (Lotto Jeongseok)

## 📌 프로그램 개요

**로또의 정석**은 역대 로또 6/45 당첨 데이터를 기반으로 통계적으로 분석하여 스마트한 번호를 추천하는 웹 서비스입니다.

- 동행복권 공식 API를 통해 전 회차 데이터를 수집하고 MySQL DB에 저장합니다.
- 완전 무작위 추천과 합산 구간 기반 추천 두 가지 방식을 제공합니다.
- 추천된 모든 번호를 DB에 저장하여 실제 당첨 결과를 투명하게 공개합니다.
- Python Flask 기반의 반응형 웹앱으로 구현되었습니다.

---

## 🗂️ 프로젝트 구조

```
webapp/
├── app.py                  # Flask 메인 진입점 (포트 15001)
├── requirements.txt        # Python 의존성 패키지
├── .env                    # 환경변수 (DB 접속 정보 등)
├── log.txt                 # 실행 로그
│
├── config/
│   ├── __init__.py
│   ├── config.py           # 환경별 설정 (개발/운영/테스트)
│   └── schema.sql          # MySQL DDL (테이블 생성 스크립트)
│
├── utils/
│   ├── __init__.py
│   ├── logger.py           # 공통 로깅 유틸리티
│   ├── db.py               # DB 연결 및 헬퍼
│   └── lotto_logic.py      # 번호 추천 핵심 로직
│
├── batch/
│   ├── __init__.py
│   └── fetch_lotto.py      # 데이터 수집 배치 프로그램
│
├── templates/
│   ├── base.html           # 공통 레이아웃 (헤더/푸터)
│   ├── index.html          # 메인 페이지
│   ├── recommend.html      # 번호 추천 페이지
│   ├── statistics.html     # 통계 분석 페이지
│   ├── history.html        # 역대 당첨 번호 페이지
│   ├── about.html          # 서비스 소개 페이지
│   └── error.html          # 오류 페이지
│
└── static/
    ├── css/
    │   └── style.css       # 전역 스타일시트 (Pretendard 폰트)
    └── js/
        ├── main.js         # 공통 JavaScript
        └── recommend.js    # 번호 추천 페이지 JS (룰렛 애니메이션)
```

---

## 🚀 설치 방법

### 1. 사전 요구 사항

- Python 3.12 이상
- MySQL 8.0 이상 (로컬 설치: `127.0.0.1`)
- pip (Python 패키지 관리자)

### 2. 가상환경 생성 및 활성화

**Linux / macOS**
```bash
cd /path/to/webapp
python3 -m venv venv
source venv/bin/activate
```

**Windows**
```cmd
cd C:\path\to\webapp
python -m venv venv
venv\Scripts\activate
```

### 3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. MySQL 데이터베이스 설정

MySQL에 root로 접속하여 다음을 실행합니다.

```sql
-- DB 생성
CREATE DATABASE lotto_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 생성 및 권한 부여
CREATE USER 'lotto_user'@'localhost' IDENTIFIED BY 'lotto_pass';
GRANT ALL PRIVILEGES ON lotto_db.* TO 'lotto_user'@'localhost';
FLUSH PRIVILEGES;
```

그 다음 DDL 스크립트를 실행합니다.

```bash
mysql -u root -p lotto_db < config/schema.sql
```

### 5. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=lotto_user
DB_PASSWORD=lotto_pass
DB_NAME=lotto_db
```

---

## ▶️ 실행 방법

### 웹 서버 실행

```bash
# 가상환경 활성화 상태에서
python app.py
```

브라우저에서 [http://localhost:15001](http://localhost:15001) 접속

### 데이터 수집 배치 실행 (최초 1회 및 매주 실행)

```bash
python batch/fetch_lotto.py
```

**Linux cron 등록 (매주 일요일 오전 9시)**
```bash
crontab -e
# 다음 줄 추가:
0 9 * * 0 cd /path/to/webapp && /path/to/venv/bin/python batch/fetch_lotto.py
```

**Windows 작업 스케줄러**
- 작업 스케줄러 → 기본 작업 만들기 → 주간 → `python batch\fetch_lotto.py`

---

## 🌟 주요 기능

| 기능 | 설명 |
|------|------|
| **완전 무작위 추천** | 1~45 중 무작위 6개 번호 추천 (1~5세트) |
| **합산 구간 추천** | 번호 합산 범위를 지정하여 해당 구간의 번호 추천 |
| **번호 통계** | 번호별 출현 빈도 차트 및 히트맵 |
| **합산 분포** | 역대 당첨 번호의 합산 구간별 분포 차트 |
| **역대 당첨 번호** | 전 회차 당첨 번호 조회 및 검색 |
| **투명성 공개** | 사이트 추천 번호 당첨 이력 메인 화면 공개 |
| **룰렛 애니메이션** | 번호 생성 시 볼이 하나씩 등장하는 애니메이션 효과 |

---

## 📊 API 엔드포인트

| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/recommend/random` | 무작위 번호 추천 |
| POST | `/api/recommend/sum_range` | 합산 구간 번호 추천 |
| GET  | `/api/statistics/frequency` | 번호별 출현 빈도 |
| GET  | `/api/statistics/sum_distribution` | 합산 구간 분포 |
| GET  | `/api/latest_round` | 최신 당첨 번호 |
| POST | `/api/batch/run` | 배치 수동 실행 (관리용) |

### 요청/응답 예시

**POST /api/recommend/random**
```json
// 요청
{ "count": 2 }

// 응답
{
  "success": true,
  "sets": [
    { "set_no": 1, "numbers": [3, 11, 22, 33, 41, 45], "total": 155, "colors": ["yellow","blue","red","gray","green","green"] },
    { "set_no": 2, "numbers": [7, 14, 25, 30, 38, 42], "total": 156, "colors": [...] }
  ]
}
```

**POST /api/recommend/sum_range**
```json
// 요청
{ "sum_min": 121, "sum_max": 130, "count": 1 }

// 응답
{ "success": true, "sets": [...], "sum_min": 121, "sum_max": 130 }
```

---

## 🗄️ DB 구조

| 테이블 | 설명 |
|--------|------|
| `lotto_results` | 역대 당첨 번호 저장 |
| `recommended_numbers` | 사이트에서 추천된 번호 이력 |
| `batch_logs` | 배치 실행 로그 |
| `v_win_stats` | 누적 당첨 통계 뷰 |
| `v_number_frequency` | 번호별 출현 빈도 뷰 |
| `v_sum_range_freq` | 합산 구간별 당첨 빈도 뷰 |

---

## ⚠️ 주의사항 및 FAQ

### Q. DB 연결 없이도 실행되나요?
A. 네. DB가 없어도 서버는 실행되며, DB 연동 기능(통계, 당첨 번호 조회 등)은 비활성화됩니다. 번호 추천(랜덤 로직)은 정상 작동합니다.

### Q. 배치는 얼마나 자주 실행해야 하나요?
A. 로또는 매주 토요일에 추첨되므로 주 1회(일요일 이후)에 실행하면 충분합니다.

### Q. 포트를 변경하고 싶어요.
A. `app.py` 하단의 `port=15001`을 원하는 포트로 변경하세요.

### Q. 번호 추천이 당첨을 보장하나요?
A. **절대 아닙니다.** 본 서비스는 통계 기반의 엔터테인먼트 서비스이며, 당첨을 보장하지 않습니다. 로또는 사행행위입니다.

### Q. 합산 구간이란 무엇인가요?
A. 6개 당첨 번호를 모두 더한 값의 범위입니다. 이론적으로 최소 21(1+2+3+4+5+6), 최대 270(40+41+42+43+44+45)입니다. 역대 데이터 분석 결과 100~200 구간에서 당첨이 집중되는 경향이 있습니다.

---

## 📝 로그

모든 실행 내역은 프로젝트 루트의 `log.txt`에 저장됩니다.

```
[2026-05-13 09:00:00] INFO     | lotto_batch | 로또 데이터 수집 배치 시작
[2026-05-13 09:00:02] INFO     | lotto_batch | API 수집 완료: 1223개 회차
[2026-05-13 09:00:05] INFO     | lotto_batch | DB UPSERT 완료: 1223건
```
