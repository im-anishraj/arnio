/**
 * Regression tests for the website code highlighter (website/js/code.js).
 *
 * Verifies that highlight() produces innerHTML from which textContent
 * (what the copy button reads) exactly matches the original source —
 * no token markup fragments leaked into copied text.
 *
 * Run with: node website/js/code.test.js
 * No test framework or build step required.
 */

'use strict';

// ─── Inline the two helpers from code.js ────────────────────────────────────

function escapeHTML(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function applyToTextOnly(html, re, replacement) {
  var parts = html.split(/(<[^>]*>)/);
  for (var i = 0; i < parts.length; i += 2) {
    parts[i] = parts[i].replace(re, replacement);
  }
  return parts.join('');
}

// ─── Replicate the exact highlight pipeline from code.js ────────────────────

var KEYWORDS = [
  'import', 'from', 'as', 'def', 'return', 'if', 'else', 'elif', 'for',
  'in', 'while', 'class', 'with', 'try', 'except', 'raise', 'True',
  'False', 'None', 'and', 'or', 'not', 'is', 'pass', 'lambda', 'yield', 'assert'
];

function highlightPython(raw) {
  var html = escapeHTML(raw);
  html = applyToTextOnly(html, /(#[^\n]*)/g, '<span class="token-comment">$1</span>');
  html = applyToTextOnly(html, /(&quot;(?:[^&]|&(?!quot;))*&quot;)/g, '<span class="token-string">$1</span>');
  html = applyToTextOnly(html, /(&#39;(?:[^&]|&(?!#39;))*&#39;)/g, '<span class="token-string">$1</span>');
  KEYWORDS.forEach(function (kw) {
    var re = new RegExp('\\b(' + kw + ')\\b', 'g');
    html = applyToTextOnly(html, re, '<span class="token-keyword">$1</span>');
  });
  html = applyToTextOnly(html, /\b(\d+\.?\d*)\b/g, '<span class="token-number">$1</span>');
  return html;
}

// ─── Simulate browser textContent (strip tags → decode entities) ─────────────

function textContent(innerHTML) {
  return innerHTML
    .replace(/<[^>]*>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

// ─── Test cases ──────────────────────────────────────────────────────────────

var tests = [
  {
    label: 'import + as + class (original bug report)',
    source: 'import arnio as ar\nclass MyModel:\n    pass',
  },
  {
    label: 'from / import + comment + string',
    source: 'from arnio import ArFrame\n# Load data\ndf = ar.read_csv("data.csv")\nresult = schema.validate(df)',
  },
  {
    label: 'keyword inside an identifier should not match',
    source: 'import arnio\nclass DataClass:\n    is_valid = True\n    if is_valid:\n        return None',
  },
  {
    label: 'source containing < and > literals',
    source: '# assert x > 0 and x < 100\nassert x > 0',
  },
  {
    label: 'keyword inside a string literal',
    source: 'msg = "class is not a problem"\nprint(msg)',
  },
  {
    label: 'no broken nested spans in innerHTML',
    source: 'import arnio as ar\nclass MyModel:\n    pass',
    extraCheck: function (innerHTML) {
      if (innerHTML.includes('<span <span')) {
        return 'broken nested <span <span> detected in innerHTML';
      }
      return null;
    },
  },
];

// ─── Runner ──────────────────────────────────────────────────────────────────

var passed = 0;
var failed = 0;

tests.forEach(function (t, i) {
  var innerHTML = highlightPython(t.source);
  var copied    = textContent(innerHTML);
  var errors    = [];

  if (copied !== t.source) {
    errors.push(
      'textContent mismatch\n' +
      '  expected: ' + JSON.stringify(t.source) + '\n' +
      '  got:      ' + JSON.stringify(copied)
    );
  }

  if (t.extraCheck) {
    var extraError = t.extraCheck(innerHTML);
    if (extraError) errors.push(extraError);
  }

  if (errors.length === 0) {
    console.log('PASS [' + (i + 1) + '] ' + t.label);
    passed++;
  } else {
    console.log('FAIL [' + (i + 1) + '] ' + t.label);
    errors.forEach(function (e) { console.log('     ' + e); });
    failed++;
  }
});

console.log('\n' + passed + ' passed, ' + failed + ' failed.');
if (failed > 0) process.exit(1);