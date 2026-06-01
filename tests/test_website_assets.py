from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = REPO_ROOT / "website"

PURPOSE_BUILT_ASSETS = {
    "favicon.svg": 1_500,
    "arnio-icon.svg": 2_000,
    "arnio-logo.svg": 3_000,
    "arnio-social-card.svg": 8_000,
}

OVERSIZED_ASSETS = {
    "arnio-transparent-logo.svg",
    "updated-icon.svg",
    "transparent-icon.svg",
}

HTML_FILES = sorted(WEBSITE_DIR.glob("*.html"))


def test_website_uses_purpose_built_logo_assets():
    assert HTML_FILES, "Expected website HTML files to validate"

    for asset_name, max_size in PURPOSE_BUILT_ASSETS.items():
        asset_path = WEBSITE_DIR / asset_name
        assert asset_path.exists(), f"Missing website/{asset_name}"
        svg = asset_path.read_text(encoding="utf-8")
        assert "data:image/" not in svg
        assert len(asset_path.read_bytes()) <= max_size


def test_website_does_not_reference_oversized_logo_assets():
    haystack = "\n".join(path.read_text(encoding="utf-8") for path in HTML_FILES)

    for stale_asset in OVERSIZED_ASSETS:
        assert stale_asset not in haystack
        assert not (WEBSITE_DIR / stale_asset).exists()


def test_website_asset_references_match_display_context():
    for html_path in HTML_FILES:
        html = html_path.read_text(encoding="utf-8")
        assert 'rel="icon" type="image/svg+xml" href="favicon.svg"' in html
        assert "arnio-social-card.svg" in html
        assert "arnio-logo.svg" in html

    index_html = (WEBSITE_DIR / "index.html").read_text(encoding="utf-8")
    assert 'src="arnio-icon.svg" alt="" width="92" height="92"' in index_html
