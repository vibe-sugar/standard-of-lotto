/**
 * 파일명: static/js/lotto-data.js
 * 목적: 로또의 정석 - 클라이언트 사이드 데이터 엔진
 *        공식 API 호출 → sessionStorage 캐싱 → 통계 계산
 * 버전: 2.0.0
 *
 * 사용법:
 *   LottoData.load().then(function(list) { ... });
 *   LottoData.calcFrequency(list)       → 번호별 출현 빈도
 *   LottoData.calcSumDist(list)         → 합산 구간 분포
 *   LottoData.getLatest(list, n)        → 최신 N회차
 *   LottoData.numberColor(n)            → 번호 색상 클래스
 *   LottoData.formatDate(yyyymmdd)      → 'YYYY-MM-DD'
 *   LottoData.formatMoney(n)            → '1,234,567'
 */

'use strict';

(function (global) {

  /* ═══════════════════════════════════════════════════
     상수
  ═══════════════════════════════════════════════════ */
  var PROXY_URL      = '/api/lotto/data';
  var CACHE_KEY      = 'lotto_data_v2';
  var CACHE_TTL_MS   = 60 * 60 * 1000; // 1시간 캐시

  /* ═══════════════════════════════════════════════════
     1. 데이터 로드 (캐시 우선, 실패 시 프록시 호출)
  ═══════════════════════════════════════════════════ */

  /**
   * 역대 전 회차 데이터 로드
   * - sessionStorage 캐시 유효하면 즉시 반환
   * - 만료/없으면 /api/lotto/data 프록시 호출
   * @returns {Promise<Array>} 회차 데이터 배열 (최신순)
   */
  function load() {
    // 캐시 확인
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (raw) {
        var cached = JSON.parse(raw);
        if (cached && cached.ts && (Date.now() - cached.ts < CACHE_TTL_MS) && Array.isArray(cached.list) && cached.list.length > 0) {
          return Promise.resolve(cached.list);
        }
      }
    } catch (e) { /* sessionStorage 비활성 환경 무시 */ }

    // 프록시를 통해 공식 API 호출
    return fetch(PROXY_URL)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (json) {
        if (!json.success || !Array.isArray(json.data)) {
          throw new Error(json.message || '데이터 형식 오류');
        }
        var list = json.data;
        // 회차 오름차순 정렬 보장 (최신이 앞에 있으므로 그대로 사용)
        // 캐시 저장
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), list: list }));
        } catch (e) { /* 저장 실패 무시 (용량 초과 등) */ }
        return list;
      });
  }

  /**
   * 캐시 강제 삭제 후 재로드
   * @returns {Promise<Array>}
   */
  function reload() {
    try { sessionStorage.removeItem(CACHE_KEY); } catch (e) {}
    return load();
  }

  /* ═══════════════════════════════════════════════════
     2. 통계 계산 함수들 (순수 함수, 부수효과 없음)
  ═══════════════════════════════════════════════════ */

  /**
   * 번호별 출현 빈도 계산
   * @param {Array} list - 회차 데이터 배열
   * @returns {Array} [{number, count, pct, color}, ...] (번호 오름차순)
   */
  function calcFrequency(list) {
    var freq = {};
    for (var n = 1; n <= 45; n++) freq[n] = 0;

    list.forEach(function (r) {
      [r.tm1WnNo, r.tm2WnNo, r.tm3WnNo, r.tm4WnNo, r.tm5WnNo, r.tm6WnNo].forEach(function (n) {
        if (n >= 1 && n <= 45) freq[n]++;
      });
    });

    var total = list.length; // 전체 회차 수
    var result = [];
    for (var i = 1; i <= 45; i++) {
      result.push({
        number : i,
        count  : freq[i],
        pct    : total > 0 ? Math.round(freq[i] / total * 1000) / 10 : 0,
        color  : numberColor(i),
      });
    }
    return result; // 1~45 오름차순
  }

  /**
   * 합산 구간 분포 계산 (10 단위 구간)
   * @param {Array} list
   * @returns {Array} [{rangeStart, rangeEnd, label, count, pct}, ...] (오름차순)
   */
  function calcSumDist(list) {
    var buckets = {};
    list.forEach(function (r) {
      var s = r.tm1WnNo + r.tm2WnNo + r.tm3WnNo + r.tm4WnNo + r.tm5WnNo + r.tm6WnNo;
      var key = Math.floor(s / 10) * 10;
      buckets[key] = (buckets[key] || 0) + 1;
    });

    var total  = list.length;
    var keys   = Object.keys(buckets).map(Number).sort(function (a, b) { return a - b; });
    return keys.map(function (k) {
      var cnt = buckets[k];
      return {
        rangeStart : k,
        rangeEnd   : k + 9,
        label      : k + '~' + (k + 9),
        count      : cnt,
        pct        : total > 0 ? Math.round(cnt / total * 1000) / 10 : 0,
      };
    });
  }

  /**
   * 보너스 번호 포함 출현 빈도 (전체 7개)
   * @param {Array} list
   * @returns {Array} [{number, mainCount, bonusCount, totalCount, pct, color}, ...]
   */
  function calcFrequencyWithBonus(list) {
    var main  = {};
    var bonus = {};
    for (var n = 1; n <= 45; n++) { main[n] = 0; bonus[n] = 0; }

    list.forEach(function (r) {
      [r.tm1WnNo, r.tm2WnNo, r.tm3WnNo, r.tm4WnNo, r.tm5WnNo, r.tm6WnNo].forEach(function (n) {
        if (n >= 1 && n <= 45) main[n]++;
      });
      if (r.bnsWnNo >= 1 && r.bnsWnNo <= 45) bonus[r.bnsWnNo]++;
    });

    var total = list.length;
    var result = [];
    for (var i = 1; i <= 45; i++) {
      var mc = main[i], bc = bonus[i];
      result.push({
        number     : i,
        mainCount  : mc,
        bonusCount : bc,
        totalCount : mc + bc,
        pct        : total > 0 ? Math.round(mc / total * 1000) / 10 : 0,
        color      : numberColor(i),
      });
    }
    return result;
  }

  /**
   * 홀짝 분포 계산
   * @param {Array} list
   * @returns {Array} [{oddCount, evenCount, label, count, pct}, ...]
   */
  function calcOddEvenDist(list) {
    var buckets = {};
    list.forEach(function (r) {
      var nums = [r.tm1WnNo, r.tm2WnNo, r.tm3WnNo, r.tm4WnNo, r.tm5WnNo, r.tm6WnNo];
      var odd  = nums.filter(function (n) { return n % 2 !== 0; }).length;
      var even = 6 - odd;
      var key  = odd + ':' + even;
      if (!buckets[key]) buckets[key] = { oddCount: odd, evenCount: even, count: 0 };
      buckets[key].count++;
    });
    var total = list.length;
    return Object.values(buckets)
      .sort(function (a, b) { return b.count - a.count; })
      .map(function (b) {
        return Object.assign({}, b, {
          label : '홀' + b.oddCount + ':짝' + b.evenCount,
          pct   : total > 0 ? Math.round(b.count / total * 1000) / 10 : 0,
        });
      });
  }

  /**
   * 연속 번호 분포 계산
   * @param {Array} list
   * @returns {Array} [{consecutive, count, pct}, ...]
   */
  function calcConsecutiveDist(list) {
    var buckets = {};
    list.forEach(function (r) {
      var nums = [r.tm1WnNo, r.tm2WnNo, r.tm3WnNo, r.tm4WnNo, r.tm5WnNo, r.tm6WnNo].sort(function (a, b) { return a - b; });
      var cnt  = 0;
      for (var i = 1; i < nums.length; i++) {
        if (nums[i] - nums[i - 1] === 1) cnt++;
      }
      buckets[cnt] = (buckets[cnt] || 0) + 1;
    });
    var total = list.length;
    return Object.keys(buckets).map(Number).sort(function (a, b) { return a - b; }).map(function (k) {
      return { consecutive: k, count: buckets[k], pct: total > 0 ? Math.round(buckets[k] / total * 1000) / 10 : 0 };
    });
  }

  /**
   * 최신 N회차 조회
   * @param {Array}  list - 최신순 정렬된 배열
   * @param {number} n
   * @returns {Array}
   */
  function getLatest(list, n) {
    return list.slice(0, n || 1);
  }

  /**
   * 특정 회차 조회
   * @param {Array}  list
   * @param {number} epsd - 회차 번호
   * @returns {Object|null}
   */
  function getRound(list, epsd) {
    return list.find(function (r) { return r.ltEpsd === epsd; }) || null;
  }

  /* ═══════════════════════════════════════════════════
     3. 유틸리티 함수
  ═══════════════════════════════════════════════════ */

  /**
   * 번호 → CSS 색상 클래스
   * 1~10: yellow, 11~20: blue, 21~30: red, 31~40: gray, 41~45: green
   * @param {number} n
   * @returns {string} CSS class name
   */
  function numberColor(n) {
    if (n <=  0 || n > 45) return 'gray';
    if (n <= 10) return 'yellow';
    if (n <= 20) return 'blue';
    if (n <= 30) return 'red';
    if (n <= 40) return 'gray';
    return 'green';
  }

  /**
   * 날짜 포맷 변환  'YYYYMMDD' → 'YYYY-MM-DD'
   * @param {string|number} d
   * @returns {string}
   */
  function formatDate(d) {
    var s = String(d);
    if (s.length === 8) return s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8);
    return s;
  }

  /**
   * 숫자 → 천 단위 콤마 문자열
   * @param {number} n
   * @returns {string}
   */
  function formatMoney(n) {
    return Number(n).toLocaleString('ko-KR');
  }

  /**
   * 원 단위를 억/만 단위로 축약
   * @param {number} n
   * @returns {string}
   */
  function formatMoneyShort(n) {
    if (n >= 1e8) return (Math.round(n / 1e8 * 10) / 10).toLocaleString('ko-KR') + '억';
    if (n >= 1e4) return Math.round(n / 1e4).toLocaleString('ko-KR') + '만';
    return formatMoney(n);
  }

  /**
   * 로또 볼 DOM 요소 생성
   * @param {number} num     - 번호
   * @param {string} sizeCls - 'ball-xs' | 'ball-sm' | 'ball-md' | 'ball-lg'
   * @param {boolean} isBonus
   * @returns {HTMLElement}
   */
  function createBallEl(num, sizeCls, isBonus) {
    var el = document.createElement('span');
    el.className = 'ball ' + (sizeCls || 'ball-sm') + ' ' + numberColor(num) + (isBonus ? ' bonus' : '');
    el.textContent = num;
    el.setAttribute('aria-hidden', 'true');
    return el;
  }

  /**
   * 회차 행 → 볼 묶음 HTML 문자열
   * @param {Object} r    - 회차 데이터
   * @param {string} size - ball size class
   * @returns {string}
   */
  function roundBallsHTML(r, size) {
    size = size || 'ball-sm';
    var nums = [r.tm1WnNo, r.tm2WnNo, r.tm3WnNo, r.tm4WnNo, r.tm5WnNo, r.tm6WnNo];
    var html = nums.map(function (n) {
      return '<span class="ball ' + size + ' ' + numberColor(n) + '" aria-hidden="true">' + n + '</span>';
    }).join('');
    html += '<span class="ball-sep" aria-hidden="true">+</span>';
    html += '<span class="ball ' + size + ' ' + numberColor(r.bnsWnNo) + ' bonus" aria-hidden="true">' + r.bnsWnNo + '</span>';
    return html;
  }

  /* ═══════════════════════════════════════════════════
     4. 로딩 상태 UI 헬퍼
  ═══════════════════════════════════════════════════ */

  /**
   * 로딩 스피너 HTML
   * @param {string} msg
   * @returns {string}
   */
  function loadingHTML(msg) {
    return '<div class="data-loading" role="status" aria-live="polite">'
         + '<div class="loading-spinner"></div>'
         + '<p class="loading-msg">' + (msg || '데이터를 불러오는 중...') + '</p>'
         + '</div>';
  }

  /**
   * 오류 HTML
   * @param {string} msg
   * @returns {string}
   */
  function errorHTML(msg) {
    return '<div class="data-error" role="alert">'
         + '<span class="error-icon" aria-hidden="true">⚠️</span>'
         + '<p>' + (msg || '데이터를 불러올 수 없습니다.') + '</p>'
         + '<button class="btn btn-sm btn-outline" onclick="location.reload()">새로고침</button>'
         + '</div>';
  }

  /* ═══════════════════════════════════════════════════
     5. 공개 API
  ═══════════════════════════════════════════════════ */

  global.LottoData = {
    load                 : load,
    reload               : reload,
    calcFrequency        : calcFrequency,
    calcFrequencyWithBonus: calcFrequencyWithBonus,
    calcSumDist          : calcSumDist,
    calcOddEvenDist      : calcOddEvenDist,
    calcConsecutiveDist  : calcConsecutiveDist,
    getLatest            : getLatest,
    getRound             : getRound,
    numberColor          : numberColor,
    formatDate           : formatDate,
    formatMoney          : formatMoney,
    formatMoneyShort     : formatMoneyShort,
    createBallEl         : createBallEl,
    roundBallsHTML       : roundBallsHTML,
    loadingHTML          : loadingHTML,
    errorHTML            : errorHTML,
  };

})(window);
