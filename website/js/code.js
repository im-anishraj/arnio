/* ============================================================
   Arnio Code — Copy-to-clipboard for code blocks
   ============================================================ */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    // ── Add copy buttons to all code blocks ──────────────────
    document.querySelectorAll('.code-block pre, pre[data-copy]').forEach(function (pre) {
      // Skip if already has a copy button
      if (pre.querySelector('.copy-btn')) return;

      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Copy';
      btn.setAttribute('aria-label', 'Copy code to clipboard');

      btn.addEventListener('click', function () {
        const code = pre.querySelector('code') || pre;
        const text = code.textContent;

        navigator.clipboard.writeText(text).then(function () {
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(function () {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 2000);
        }).catch(function () {
          // Fallback for older browsers
          const textarea = document.createElement('textarea');
          textarea.value = text;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(function () {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 2000);
        });
      });

      pre.style.position = 'relative';
      pre.appendChild(btn);
    });

    // ── Install command click-to-copy ─────────────────────────
    // Handler function for copy action (triggered by click or keyboard)
    function handleInstallCommandCopy(el) {
      const cmd = el.getAttribute('data-cmd') || el.textContent.replace(/^\$\s*/, '').replace(/click to copy/i, '').trim();

      navigator.clipboard.writeText(cmd).then(function () {
        showCopyFeedback(el);
      }).catch(function () {
        const textarea = document.createElement('textarea');
        textarea.value = cmd;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showCopyFeedback(el);
      });
    }

    document.querySelectorAll('.install-cmd, .hero-install').forEach(function (el) {
      // Click handler
      el.addEventListener('click', function () {
        handleInstallCommandCopy(el);
      });

      // Keyboard handler for Enter and Space keys (WCAG 2.1 Level A)
      el.addEventListener('keydown', function (event) {
        // Enter (key code 13) or Space (key code 32)
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault(); // Prevent default Space scroll behavior
          handleInstallCommandCopy(el);
        }
      });
    });

    function showCopyFeedback(el) {
      const original = el.innerHTML;
      const hint = el.querySelector('.copy-hint');
      if (hint) {
        hint.textContent = 'Copied!';
        setTimeout(function () { hint.textContent = 'click to copy'; }, 2000);
      } else {
        el.style.borderColor = 'var(--color-success)';
        setTimeout(function () { el.style.borderColor = ''; }, 1500);
      }
    }

    // ── Minimal syntax highlighting ──────────────────────────
    //
    // The previous implementation read block.innerHTML and ran keyword regexes
    // over it.  Because the injected <span> tags contain attributes like
    // class="token-keyword", subsequent keyword passes (e.g. "class", "in")
    // matched inside those attribute strings, producing malformed HTML such as:
    //
    //   <span <span class="token-keyword">class</span>="token-keyword">import</span>
    //
    // The browser then exposed the broken attribute text ("class=\"token-keyword\">")
    // as DOM text nodes, so code.textContent — used by the copy button — returned
    // corrupted content instead of valid Python code.  By always starting from the original raw text, we avoid this problem.
    function escapeHTML(str) {
      return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function applyToTextOnly(html, re, replacement) {
      // Split into alternating [text, tag, text, tag, ...] segments.
      // Even indices are plain text; odd indices are tag strings like "<span ...>".
      var parts = html.split(/(<[^>]*>)/);
      for (var i = 0; i < parts.length; i += 2) {
        parts[i] = parts[i].replace(re, replacement);
      }
      return parts.join('');
    }

    document.querySelectorAll('pre code.language-python').forEach(function (block) {
      var raw = block.textContent;
      var html = escapeHTML(raw);

      // Comments — must run first so later passes don't highlight inside them.
      html = applyToTextOnly(html, /(#[^\n]*)/g, '<span class="token-comment">$1</span>');

      // Strings: after escapeHTML, double-quotes are &quot; and single-quotes are &#39;.
      html = applyToTextOnly(html, /(&quot;(?:[^&]|&(?!quot;))*&quot;)/g, '<span class="token-string">$1</span>');
      html = applyToTextOnly(html, /(&#39;(?:[^&]|&(?!#39;))*&#39;)/g, '<span class="token-string">$1</span>');

      // Keywords — \b anchors prevent partial-word matches.
      var keywords = ['import', 'from', 'as', 'def', 'return', 'if', 'else', 'elif', 'for', 'in', 'while', 'class', 'with', 'try', 'except', 'raise', 'True', 'False', 'None', 'and', 'or', 'not', 'is', 'pass', 'lambda', 'yield', 'assert'];
      keywords.forEach(function (kw) {
        var re = new RegExp('\\b(' + kw + ')\\b', 'g');
        html = applyToTextOnly(html, re, '<span class="token-keyword">$1</span>');
      });

      // Numbers.
      html = applyToTextOnly(html, /\b(\d+\.?\d*)\b/g, '<span class="token-number">$1</span>');

      block.innerHTML = html;
    });

    document.querySelectorAll('pre code.language-bash').forEach(function (block) {
      var raw = block.textContent;
      var html = escapeHTML(raw);

      // Comments.
      html = applyToTextOnly(html, /(#[^\n]*)/g, '<span class="token-comment">$1</span>');
      // Strings.
      html = applyToTextOnly(html, /(&quot;(?:[^&]|&(?!quot;))*&quot;)/g, '<span class="token-string">$1</span>');

      block.innerHTML = html;
    });
  });
})();