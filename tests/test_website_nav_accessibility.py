from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = REPO_ROOT / "website" / "js" / "main.js"


def test_active_nav_links_expose_current_page_state():
    main_js = MAIN_JS.read_text(encoding="utf-8")

    assert "link.classList.add('active');" in main_js
    assert "link.setAttribute('aria-current', 'page');" in main_js
    assert "link.removeAttribute('aria-current');" in main_js
