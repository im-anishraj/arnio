from __future__ import annotations

import re
import urllib.request
from pathlib import Path

try:
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    requests = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = REPO_ROOT / "website"

# og:image and twitter:image tags.
_META_TAGS_RE = re.compile(
    r"<meta\b[^>]*>",
    flags=re.IGNORECASE | re.DOTALL,
)

_VALUE_RE = re.compile(r"content\s*=\s*(\"|')([^\"']+)(\1)", re.IGNORECASE)


def _extract_social_image_urls_from_html(html: str) -> list[str]:
    urls: list[str] = []

    for m in _META_TAGS_RE.finditer(html):
        attrs_text = m.group(0)

        if not re.search(
            r"(property|name)\s*=\s*(\"|')(og:image|twitter:image)\2",
            attrs_text,
            re.IGNORECASE,
        ):
            continue

        content_match = _VALUE_RE.search(attrs_text)
        if not content_match:
            continue

        urls.append(content_match.group(2).strip())

    return urls


def _check_url_returns_200(url: str, *, timeout_s: float = 5.0) -> None:
    headers = {"User-Agent": "arnio-social-card-check/1.0"}

    # Intercept local website URLs to prevent test failures due to not-yet-deployed assets
    for domain in ("https://arniolib.vercel.app/",):
        if url.startswith(domain):
            local_path = WEBSITE_DIR / url.replace(domain, "")
            if local_path.is_file():
                return

    if requests is not None:  # pragma: no branch
        resp = requests.get(url, timeout=timeout_s, headers=headers)
        status_code = resp.status_code
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            status_code = resp.status

    assert status_code == 200, f"Expected HTTP 200 for {url}, got {status_code}"


def test_social_card_urls_resolve_http_200():
    html_files = sorted(WEBSITE_DIR.glob("*.html"))
    assert html_files, "Expected website HTML files to validate"

    all_urls: list[str] = []
    for html_path in html_files:
        html = html_path.read_text(encoding="utf-8")
        all_urls.extend(_extract_social_image_urls_from_html(html))

    assert all_urls, "No og:image/twitter:image metadata tags found in website HTML"

    failures: list[str] = []
    for url in sorted(set(all_urls)):
        try:
            _check_url_returns_200(url)
        except Exception as exc:  # pragma: no cover - network errors are real failures
            failures.append(f"{url}: {type(exc).__name__}: {exc}")

    assert (
        not failures
    ), "Social-card URL(s) did not resolve to HTTP 200:\n" + "\n".join(failures)


def test_social_card_url_is_consistent_across_pages():
    html_files = sorted(WEBSITE_DIR.glob("*.html"))

    unique_urls: set[str] = set()
    for html_path in html_files:
        html = html_path.read_text(encoding="utf-8")
        unique_urls.update(_extract_social_image_urls_from_html(html))

    assert unique_urls, "No og:image/twitter:image metadata tags found in website HTML"

    # Enforce one exact canonical URL across all pages.
    assert len(unique_urls) == 1, (
        "Expected a single consistent social-card URL across website pages, got: "
        + ", ".join(sorted(unique_urls))
    )
