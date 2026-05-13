/**
 * 파일명: static/js/main.js
 * 목적: 로또의 정석 - 전역 공통 JavaScript
 * 작성일: 2026-05-13
 * 버전: 1.0.0
 */

'use strict';

/* ═══════════════════════════════════════════════════
   1. 모바일 네비게이션 토글
═══════════════════════════════════════════════════ */
(function initMobileNav() {
  const toggle = document.getElementById('navToggle');
  const nav    = document.getElementById('mainNav');
  if (!toggle || !nav) return;

  toggle.addEventListener('click', function () {
    const isOpen = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    toggle.setAttribute('aria-label', isOpen ? '메뉴 닫기' : '메뉴 열기');
  });

  // 외부 클릭 시 닫기
  document.addEventListener('click', function (e) {
    if (!toggle.contains(e.target) && !nav.contains(e.target)) {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });

  // ESC 키 닫기
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && nav.classList.contains('open')) {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
})();

/* ═══════════════════════════════════════════════════
   2. 스크롤 시 헤더 그림자 처리
═══════════════════════════════════════════════════ */
(function initHeaderScroll() {
  const header = document.querySelector('.site-header');
  if (!header) return;

  let ticking = false;
  window.addEventListener('scroll', function () {
    if (!ticking) {
      requestAnimationFrame(function () {
        header.style.boxShadow = window.scrollY > 10
          ? '0 2px 16px rgba(0,0,0,0.1)'
          : 'none';
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });
})();

/* ═══════════════════════════════════════════════════
   3. 숫자 카운트업 애니메이션 (당첨 통계)
═══════════════════════════════════════════════════ */
(function initCountUp() {
  const counters = document.querySelectorAll('.count-number');
  if (!counters.length) return;

  /**
   * 숫자를 0에서 목표값까지 애니메이션으로 표시
   * @param {HTMLElement} el - 대상 요소
   * @param {number} target  - 목표 숫자
   * @param {number} duration - 애니메이션 시간(ms)
   */
  function countUp(el, target, duration) {
    const start    = 0;
    const startTs  = performance.now();
    const isLarge  = target > 999;

    function step(ts) {
      const elapsed = ts - startTs;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(eased * (target - start) + start);
      el.textContent = isLarge ? current.toLocaleString() : current;
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = isLarge ? target.toLocaleString() : target;
    }

    requestAnimationFrame(step);
  }

  // IntersectionObserver로 뷰포트 진입 시 시작
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const el  = entry.target;
        const raw = el.textContent.replace(/,/g, '').trim();
        const val = parseInt(raw, 10);
        if (!isNaN(val) && val > 0) {
          countUp(el, val, 1200);
        }
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.3 });

  counters.forEach(function (el) { observer.observe(el); });
})();

/* ═══════════════════════════════════════════════════
   4. 접근성: 포커스 트랩 (모달용 — 재사용 유틸)
═══════════════════════════════════════════════════ */
/**
 * 포커스를 특정 컨테이너 내부로 제한
 * @param {HTMLElement} container - 포커스를 가둘 요소
 * @returns {Function} 해제 함수
 */
window.trapFocus = function (container) {
  const focusable = container.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last  = focusable[focusable.length - 1];

  function handler(e) {
    if (e.key !== 'Tab') return;
    if (e.shiftKey) {
      if (document.activeElement === first) { last.focus(); e.preventDefault(); }
    } else {
      if (document.activeElement === last) { first.focus(); e.preventDefault(); }
    }
  }

  container.addEventListener('keydown', handler);
  return function () { container.removeEventListener('keydown', handler); };
};

/* ═══════════════════════════════════════════════════
   5. 토스트 알림 유틸리티
═══════════════════════════════════════════════════ */
/**
 * 화면 하단에 토스트 메시지를 표시
 * @param {string} message - 표시할 메시지
 * @param {string} type    - 'info' | 'success' | 'error'
 * @param {number} duration - 표시 시간(ms)
 */
window.showToast = function (message, type, duration) {
  type     = type || 'info';
  duration = duration || 3000;

  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      pointerEvents: 'none',
    });
    document.body.appendChild(container);
  }

  const colorMap = {
    info:    { bg: '#1D4ED8', icon: 'ℹ️' },
    success: { bg: '#10B981', icon: '✅' },
    error:   { bg: '#EF4444', icon: '❌' },
  };
  const c = colorMap[type] || colorMap.info;

  const toast = document.createElement('div');
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  Object.assign(toast.style, {
    background: c.bg,
    color: '#fff',
    padding: '12px 20px',
    borderRadius: '12px',
    fontSize: '0.875rem',
    fontFamily: 'Pretendard, sans-serif',
    fontWeight: '600',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    pointerEvents: 'all',
    maxWidth: '320px',
    animation: 'toastIn 0.3s ease',
  });
  toast.textContent = c.icon + ' ' + message;
  container.appendChild(toast);

  setTimeout(function () {
    toast.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(function () { container.removeChild(toast); }, 280);
  }, duration);
};

// 토스트 키프레임 주입
if (!document.getElementById('toast-style')) {
  const s = document.createElement('style');
  s.id = 'toast-style';
  s.textContent = `
    @keyframes toastIn  { from { opacity:0; transform: translateX(40px); } to { opacity:1; transform: translateX(0); } }
    @keyframes toastOut { from { opacity:1; } to { opacity:0; transform: translateX(40px); } }
  `;
  document.head.appendChild(s);
}
