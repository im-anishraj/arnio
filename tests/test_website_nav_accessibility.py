from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = REPO_ROOT / "website"
HTML_FILES = sorted(WEBSITE_DIR.glob("*.html"))


def test_mobile_menu_toggles_reference_controlled_menu():
    assert HTML_FILES, "Expected website HTML files to validate"

    for html_path in HTML_FILES:
        html = html_path.read_text(encoding="utf-8")

        hamburger_match = re.search(r'<button[^>]*class="nav-hamburger"[^>]*>', html)
        menu_match = re.search(r'<div[^>]*class="mobile-menu"[^>]*>', html)

        assert hamburger_match, f"{html_path.name}: missing mobile nav toggle"
        assert menu_match, f"{html_path.name}: missing mobile nav menu"
        assert 'aria-controls="mobile-navigation"' in hamburger_match.group(0)
        assert 'id="mobile-navigation"' in menu_match.group(0)
