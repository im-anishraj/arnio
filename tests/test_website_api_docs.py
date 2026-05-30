"""Website API reference drift checks."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _public_exports() -> list[str]:
    tree = ast.parse((REPO_ROOT / "arnio" / "__init__.py").read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                return [
                    item.value
                    for item in node.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                ]
    raise AssertionError("arnio.__all__ not found")


def test_website_api_reference_mentions_public_exports():
    api_html = (REPO_ROOT / "website" / "api.html").read_text()

    missing = [name for name in _public_exports() if name not in api_html]

    assert missing == []


def test_website_profile_signature_matches_current_options():
    api_html = (REPO_ROOT / "website" / "api.html").read_text()

    assert "top_n=5" not in api_html
    assert "approx_top_values_min_unique=1000" in api_html
    assert "approx_top_values_min_ratio=0.2" in api_html
    assert "approx_top_values_sample_size=2000" in api_html
