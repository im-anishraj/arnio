// Static guard condition tests for page-transition.js
// Run in browser console or Node.js

function shouldSkipLink(href, attributes = {}) {
  if (!href || href.startsWith("#")) return true;
  if (href.startsWith("mailto:")) return true;
  if (href.startsWith("tel:")) return true;
  if (href.startsWith("javascript:")) return true;
  if (attributes.download) return true;
  try {
    const url = new URL(href, "https://example.com");
    if (url.origin !== "https://example.com") return true;
  } catch (e) {
    return true;
  }
  return false;
}

function assert(condition, message) {
  if (!condition) {
    console.error("FAIL: " + message);
  } else {
    console.log("PASS: " + message);
  }
}

assert(shouldSkipLink("mailto:test@example.com"), "skips mailto links");
assert(shouldSkipLink("tel:+911234567890"), "skips tel links");
assert(shouldSkipLink("#section"), "skips hash links");
assert(shouldSkipLink("javascript:void(0)"), "skips javascript links");
assert(shouldSkipLink("https://external.com/page"), "skips external links");
assert(shouldSkipLink("/about.html", { download: true }), "skips download links");
assert(!shouldSkipLink("/about.html"), "allows local page links");
assert(!shouldSkipLink("/contact.html"), "allows local contact page");