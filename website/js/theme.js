/* ============================================================
   Arnio Theme — Dark/Light toggle with persistence
   ============================================================ */

(function () {
  'use strict';

  const STORAGE_KEY = 'arnio-theme';
  const DARK = 'dark';
  const LIGHT = 'light';

  function safeGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function safeSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) {
      // Ignore quota or access errors
    }
  }

  function getPreferred() {
    const stored = safeGet(STORAGE_KEY);
    if (stored === DARK || stored === LIGHT) return stored;
    // Fall back to system preference
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT;
  }
  function applyWithoutSaving(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    updateToggleIcon(theme);
  }

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    safeSet(STORAGE_KEY, theme);
    updateToggleIcon(theme);
  }

  function updateToggleIcon(theme) {
    const btn = document.querySelector('.theme-toggle');
    if (!btn) return;
    btn.setAttribute('aria-label', theme === DARK ? 'Switch to light mode' : 'Switch to dark mode');
    btn.innerHTML = theme === DARK ? '☀️' : '🌙';
  }

  function toggle() {
    const current = document.documentElement.getAttribute('data-theme') || getPreferred();
    apply(current === DARK ? LIGHT : DARK);
  }

  // Apply immediately to prevent flash
  applyWithoutSaving(getPreferred());

  // Listen for system preference changes
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      if (!safeGet(STORAGE_KEY)) {
        applyWithoutSaving(e.matches ? DARK : LIGHT);
      }
    });
  }

  // Bind toggle button after DOM ready
  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.querySelector('.theme-toggle');
    if (btn) {
      btn.addEventListener('click', toggle);
      updateToggleIcon(getPreferred());
    }
  });
})();
