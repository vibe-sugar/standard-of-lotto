/**
 * 파일명: static/js/recommend.js
 * 목적: 로또의 정석 - 번호 추천 페이지 JavaScript
 *        룰렛 애니메이션, 탭 전환, 번호 생성 API 연동
 * 작성일: 2026-05-13
 * 버전: 1.0.0
 */

'use strict';

/* ═══════════════════════════════════════════════════
   1. 핵심 번호 생성 함수 (API 호출 + 애니메이션)
═══════════════════════════════════════════════════ */

/**
 * 번호 추천 API 호출 및 결과 렌더링
 *
 * @param {string} type          - 'random' | 'sum_range'
 * @param {Object} params        - 요청 파라미터 { count, sum_min, sum_max }
 * @param {string} resultAreaId  - 결과를 표시할 래퍼 element ID
 * @param {string} resultBodyId  - 결과 콘텐츠 element ID
 */
window.generateNumbers = function (type, params, resultAreaId, resultBodyId) {
  const resultArea = document.getElementById(resultAreaId);
  const resultBody = document.getElementById(resultBodyId);
  if (!resultArea || !resultBody) return;

  const endpoint = type === 'sum_range'
    ? '/api/recommend/sum_range'
    : '/api/recommend/random';

  // 로딩 상태 표시
  resultArea.removeAttribute('hidden');
  resultBody.removeAttribute('hidden');
  resultBody.innerHTML = '<div class="spinner" aria-label="번호 생성 중..."></div>';

  // 이전에 보이던 placeholder 숨기기
  const placeholder = document.getElementById('resultPlaceholder');
  if (placeholder) placeholder.style.display = 'none';

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (!data.success) {
        showError(resultBody, data.message || '번호 생성에 실패했습니다.');
        return;
      }
      renderResultSets(resultBody, data.sets);

      // 저장 목록에 추가 (추천 페이지 전용)
      if (window._savedNumbers !== undefined) {
        data.sets.forEach(function (s) { addToSaved(s, type, params); });
      }
    })
    .catch(function (err) {
      showError(resultBody, '서버와의 통신에 실패했습니다. 잠시 후 다시 시도해 주세요.');
      console.error('[recommend.js] API 오류:', err);
    });
};

/* ═══════════════════════════════════════════════════
   2. 결과 렌더링 (룰렛 애니메이션 포함)
═══════════════════════════════════════════════════ */

/**
 * 번호 세트 목록을 HTML로 렌더링
 * @param {HTMLElement} container - 렌더링 대상
 * @param {Array}       sets      - API 응답 sets 배열
 */
function renderResultSets(container, sets) {
  container.innerHTML = '';

  sets.forEach(function (set, idx) {
    const div = document.createElement('div');
    div.className = 'result-set';
    div.setAttribute('aria-label',
      set.set_no + '번 추천: ' + set.numbers.join(', ') + ', 합계 ' + set.total);

    const label = document.createElement('span');
    label.className = 'set-label';
    label.textContent = set.set_no + '번';

    const ballsWrap = document.createElement('div');
    ballsWrap.className = 'set-balls';

    // 볼 하나씩 룰렛처럼 등장
    set.numbers.forEach(function (num, ballIdx) {
      const ball = createBallElement(num, set.colors[ballIdx], 'ball-lg');
      // 딜레이 계산: 세트 간 간격 + 볼 간 간격
      const delay = idx * 300 + ballIdx * 120 + 100;
      ball.style.animationDelay = delay + 'ms';
      ballsWrap.appendChild(ball);
    });

    const total = document.createElement('span');
    total.className = 'set-total';
    total.textContent = '합계 ' + set.total;

    div.appendChild(label);
    div.appendChild(ballsWrap);
    div.appendChild(total);
    container.appendChild(div);
  });

  // 스크린 리더 알림
  if (window.showToast) {
    const msg = sets.length === 1
      ? '번호 추천 완료: ' + sets[0].numbers.join(', ')
      : sets.length + '세트 번호 추천 완료';
    window.showToast(msg, 'success', 2500);
  }
}

/**
 * 로또 볼 DOM 요소 생성
 * @param {number} num      - 번호
 * @param {string} colorCls - 색상 클래스 (yellow, blue, red, gray, green)
 * @param {string} sizeCls  - 크기 클래스 (ball-sm, ball-md, ball-lg)
 * @returns {HTMLElement}
 */
function createBallElement(num, colorCls, sizeCls) {
  const span = document.createElement('span');
  span.className = 'ball ' + (sizeCls || 'ball-md') + ' ' + (colorCls || 'blue');
  span.textContent = num;
  span.setAttribute('aria-hidden', 'true');
  return span;
}

/**
 * 오류 메시지 렌더링
 * @param {HTMLElement} container
 * @param {string}      message
 */
function showError(container, message) {
  container.innerHTML =
    '<div class="result-error" role="alert" style="color:#EF4444;padding:16px;text-align:center;">' +
    '⚠️ ' + message + '</div>';
}

/* ═══════════════════════════════════════════════════
   3. 추천 페이지 전용 로직
═══════════════════════════════════════════════════ */

// 세션 내 저장된 번호 (최대 20개)
window._savedNumbers = [];
const SAVED_MAX = 20;

/**
 * 추천 페이지 초기화
 * (recommend.html 에서 initRecommendPage() 호출)
 */
window.initRecommendPage = function () {
  initTabs();
  initCountButtons('.count-btn',    'randomCount');
  initCountButtons('.count-btn-sr', 'sumCount');
  initSumRangeButtons();
  initRandomButton();
  initSumRangeButton();
  initSavedSection();
};

/* ── 탭 전환 ──────────────────────────────────── */
function initTabs() {
  const tabs   = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      panels.forEach(function (p) { p.classList.add('hidden'); });

      this.classList.add('active');
      this.setAttribute('aria-selected', 'true');
      const panel = document.getElementById(this.getAttribute('aria-controls'));
      if (panel) panel.classList.remove('hidden');
    });
  });
}

/* ── 세트 수 선택 버튼 ──────────────────────── */
function initCountButtons(selector, hiddenId) {
  const btns   = document.querySelectorAll(selector);
  const hidden = document.getElementById(hiddenId);
  if (!btns.length || !hidden) return;

  btns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      btns.forEach(function (b) {
        b.classList.remove('active');
        b.setAttribute('aria-pressed', 'false');
      });
      this.classList.add('active');
      this.setAttribute('aria-pressed', 'true');
      if (hidden) hidden.value = this.dataset.count;
    });
  });
}

/* ── 합산 구간 버튼 ─────────────────────────── */
function initSumRangeButtons() {
  const btns       = document.querySelectorAll('.btn-range-lg');
  const minInput   = document.getElementById('selectedMin');
  const maxInput   = document.getElementById('selectedMax');
  const rangeText  = document.getElementById('selectedRangeText');

  btns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      btns.forEach(function (b) {
        b.classList.remove('selected');
        b.setAttribute('aria-pressed', 'false');
      });
      this.classList.add('selected');
      this.setAttribute('aria-pressed', 'true');

      const min = this.dataset.min;
      const max = this.dataset.max;
      if (minInput) minInput.value = min;
      if (maxInput) maxInput.value = max;
      if (rangeText) rangeText.textContent = min + ' ~ ' + max;
    });
  });
}

/* ── 무작위 추천 버튼 ───────────────────────── */
function initRandomButton() {
  const btn = document.getElementById('randomBtn');
  if (!btn) return;

  btn.addEventListener('click', function () {
    const count = parseInt(document.getElementById('randomCount').value, 10) || 1;
    btn.disabled = true;
    btn.textContent = '생성 중...';

    generateNumbers('random', { count: count }, 'resultArea', 'resultContent');

    // 버튼 복구
    setTimeout(function () {
      btn.disabled = false;
      btn.innerHTML = '<span aria-hidden="true">✨</span> 번호 추천받기';
    }, count * 300 + 800);
  });
}

/* ── 합산 구간 추천 버튼 ─────────────────────── */
function initSumRangeButton() {
  const btn = document.getElementById('sumRangeBtn');
  if (!btn) return;

  btn.addEventListener('click', function () {
    const sumMin = parseInt(document.getElementById('selectedMin').value, 10);
    const sumMax = parseInt(document.getElementById('selectedMax').value, 10);
    const count  = parseInt(document.getElementById('sumCount').value, 10) || 1;

    if (isNaN(sumMin) || isNaN(sumMax)) {
      window.showToast && window.showToast('합산 구간을 먼저 선택해 주세요.', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = '생성 중...';

    generateNumbers('sum_range',
      { sum_min: sumMin, sum_max: sumMax, count: count },
      'resultArea', 'resultContent'
    );

    setTimeout(function () {
      btn.disabled = false;
      btn.innerHTML = '<span aria-hidden="true">✨</span> 번호 추천받기';
    }, count * 300 + 800);
  });
}

/* ── 저장 목록 섹션 ─────────────────────────── */
function initSavedSection() {
  const clearBtn = document.getElementById('clearSavedBtn');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      window._savedNumbers = [];
      renderSaved();
    });
  }
}

/**
 * 생성된 번호를 저장 목록에 추가
 * @param {Object} set     - 번호 세트
 * @param {string} type    - 추천 방식
 * @param {Object} params  - 요청 파라미터
 */
function addToSaved(set, type, params) {
  if (window._savedNumbers.length >= SAVED_MAX) {
    window._savedNumbers.shift(); // 오래된 항목 제거
  }
  window._savedNumbers.push({
    numbers: set.numbers,
    colors: set.colors,
    total: set.total,
    type: type,
    params: params,
    ts: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
  });
  renderSaved();
}

/**
 * 저장 목록 UI 업데이트
 */
function renderSaved() {
  const section = document.getElementById('savedSection');
  const list    = document.getElementById('savedList');
  if (!section || !list) return;

  if (window._savedNumbers.length === 0) {
    section.setAttribute('hidden', '');
    list.innerHTML = '';
    return;
  }

  section.removeAttribute('hidden');
  list.innerHTML = '';

  // 최신 순으로 표시
  const reversed = window._savedNumbers.slice().reverse();
  reversed.forEach(function (item) {
    const el = document.createElement('div');
    el.className = 'saved-item';
    el.setAttribute('role', 'listitem');
    el.setAttribute('aria-label',
      (item.type === 'random' ? '무작위' : '합산구간') +
      ' | ' + item.numbers.join(', ') + ' (합계 ' + item.total + ')');

    const typeTag = document.createElement('span');
    typeTag.className = 'saved-type';
    typeTag.textContent = item.type === 'random' ? '🎲' : '🎯';

    const ballsWrap = document.createElement('div');
    ballsWrap.style.display = 'flex';
    ballsWrap.style.gap = '4px';
    ballsWrap.style.alignItems = 'center';

    item.numbers.forEach(function (num, i) {
      const ball = createBallElement(num, item.colors[i], 'ball-xs');
      ballsWrap.appendChild(ball);
    });

    const totalSpan = document.createElement('span');
    totalSpan.className = 'set-total';
    totalSpan.textContent = '합 ' + item.total;

    const tsSpan = document.createElement('span');
    tsSpan.style.marginLeft = 'auto';
    tsSpan.style.fontSize = '0.7rem';
    tsSpan.style.color = '#9CA3AF';
    tsSpan.textContent = item.ts;

    el.appendChild(typeTag);
    el.appendChild(ballsWrap);
    el.appendChild(totalSpan);
    el.appendChild(tsSpan);
    list.appendChild(el);
  });
}
