from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_docs_and_api_load_search_js():
    docs_html = (REPO_ROOT / "website" / "docs.html").read_text(encoding="utf-8")
    api_html = (REPO_ROOT / "website" / "api.html").read_text(encoding="utf-8")

    assert "js/search.js" in docs_html
    assert "js/search.js" in api_html


def test_search_js_contains_keyboard_accessibility():
    search_js = (REPO_ROOT / "website" / "js" / "search.js").read_text(encoding="utf-8")

    assert "aria-controls" in search_js
    assert "aria-expanded" in search_js
    assert "aria-selected" in search_js
    assert 'e.key.toLowerCase() === "k"' in search_js
    assert "ArrowDown" in search_js
    assert "ArrowUp" in search_js
    assert "Enter" in search_js
    assert "Escape" in search_js


def test_search_index_contains_docs_and_api_targets():
    search_js = (REPO_ROOT / "website" / "js" / "search.js").read_text(encoding="utf-8")

    assert "docs.html#install" in search_js
    assert "docs.html#quickstart" in search_js
    assert "api.html#io" in search_js
    assert "api.html#frame" in search_js
