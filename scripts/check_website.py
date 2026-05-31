#!/usr/bin/env python3
"""
Static website smoke-checker for website/.

Checks
------
1. Every ``website/*.html`` file is parseable as UTF-8 HTML.
2. Every local ``href`` and ``src`` attribute resolves to an existing file.
3. Every fragment link (``#id``) resolves to a real ``id=`` on the target page.
4. Required shared assets (CSS, JS, SVG logo assets) are present on disk.

External links are skipped by default.  Pass ``--warn-external`` to emit
a WARNING line for each one (CI stays green; useful for local audits).

Exit codes
----------
0 – all checks passed
1 – one or more errors found
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
WEBSITE_DIR = REPO_ROOT / "website"

# These assets must exist for every page to render correctly.
REQUIRED_ASSETS: list[str] = [
    "css/base.css",
    "css/components.css",
    "css/layout.css",
    "css/pages.css",
    "css/variables.css",
    "js/main.js",
    "js/theme.js",
    "js/code.js",
    "js/github.js",
    "js/theme.js",
    "favicon.svg",
    "arnio-icon.svg",
    "arnio-logo.svg",
    "arnio-social-card.svg",
]

# URL schemes that belong to external resources — skip file-existence checks.
_EXTERNAL_SCHEMES = frozenset({"http", "https", "mailto", "tel", "ftp", "data"})

# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------


class _LinkExtractor(HTMLParser):
    """Collect (href|src) link targets and id attribute values from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        for key in ("href", "src"):
            value = attr.get(key)
            if value:
                self.links.append(value)
        id_val = attr.get("id")
        if id_val:
            self.ids.add(id_val)


def _parse_html(path: Path) -> tuple[list[str], set[str]]:
    """
    Parse *path* and return ``(links, ids)``.

    Raises ``ValueError`` on UTF-8 decode failure so callers can record it
    as an error without crashing the whole run.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"UTF-8 decode error at offset {exc.start}: {exc.reason}"
        ) from exc

    extractor = _LinkExtractor()
    extractor.feed(text)
    return extractor.links, extractor.ids


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def _is_external(url: str) -> bool:
    return urlparse(url).scheme in _EXTERNAL_SCHEMES


def _resolve(url: str, page: Path) -> tuple[Path, str | None]:
    """
    Resolve a *local* URL relative to *page* inside ``website/``.

    Returns ``(target_path, fragment)`` where *fragment* may be ``None``.
    A pure ``#id`` URL (no path component) maps to the current page.
    Query strings (cache-busters such as ``?v=20260522``) are stripped.
    """
    parsed = urlparse(url)
    fragment: str | None = parsed.fragment or None

    if not parsed.path:
        # Pure fragment: "#cleaning" → current page
        return page, fragment

    target = (page.parent / unquote(parsed.path)).resolve()
    return target, fragment


# ---------------------------------------------------------------------------
# Main checker
# ---------------------------------------------------------------------------


def check_website(
    website_dir: Path,
    *,
    warn_external: bool = False,
) -> tuple[list[str], list[str]]:
    """
    Run all smoke checks and return ``(errors, warnings)``.

    *errors* → CI fails
    *warnings* → printed but CI stays green
    """
    errors: list[str] = []
    warnings: list[str] = []

    html_files = sorted(website_dir.glob("*.html"))
    if not html_files:
        errors.append(f"No HTML files found in {website_dir}")
        return errors, warnings

    # ------------------------------------------------------------------
    # Pass 1 – parse every HTML file, collect links and id attributes.
    # Pages that fail to parse are recorded and skipped in pass 2.
    # ------------------------------------------------------------------
    page_links: dict[Path, list[str]] = {}
    page_ids: dict[Path, set[str]] = {}

    for html_file in html_files:
        try:
            links, ids = _parse_html(html_file)
        except ValueError as exc:
            errors.append(f"{html_file.relative_to(website_dir)}: parse error – {exc}")
            continue
        page_links[html_file] = links
        page_ids[html_file] = ids

    # ------------------------------------------------------------------
    # Pass 2 – required assets must exist on disk.
    # ------------------------------------------------------------------
    seen_assets: set[str] = set()
    for asset in REQUIRED_ASSETS:
        if asset in seen_assets:
            continue
        seen_assets.add(asset)
        if not (website_dir / asset).exists():
            errors.append(f"required asset missing: {asset}")

    # ------------------------------------------------------------------
    # Pass 3 – validate every link found in every page.
    # ------------------------------------------------------------------
    for page, links in page_links.items():
        rel_page = page.relative_to(website_dir)

        for url in links:
            if _is_external(url):
                if warn_external:
                    warnings.append(f"{rel_page}: external (not validated): {url}")
                continue

            target, fragment = _resolve(url, page)

            # Check the file exists.
            if not target.exists():
                try:
                    rel_target = target.relative_to(website_dir)
                except ValueError:
                    rel_target = target  # type: ignore[assignment]
                errors.append(
                    f"{rel_page}: broken link '{url}' → '{rel_target}' not found"
                )
                continue

            # Check fragment resolves to a real id= on the target page.
            if fragment and target.suffix == ".html":
                target_ids = page_ids.get(target, set())
                if fragment not in target_ids:
                    try:
                        rel_target = target.relative_to(website_dir)
                    except ValueError:
                        rel_target = target  # type: ignore[assignment]
                    errors.append(
                        f"{rel_page}: broken fragment '#{fragment}' "
                        f"not found in '{rel_target}'"
                    )

    return errors, warnings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    warn_external = "--warn-external" in argv

    if not WEBSITE_DIR.is_dir():
        print(
            f"ERROR: website directory not found: {WEBSITE_DIR}",
            file=sys.stderr,
        )
        return 1

    html_count = len(list(WEBSITE_DIR.glob("*.html")))
    print(f"Checking {html_count} HTML pages in {WEBSITE_DIR.relative_to(REPO_ROOT)} …")

    errors, warnings = check_website(WEBSITE_DIR, warn_external=warn_external)

    for w in warnings:
        print(f"WARNING: {w}")

    if errors:
        print("\nWebsite smoke check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        print(
            f"\n{len(errors)} error(s) found. " "Fix the issues above and re-run.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Website smoke check passed "
        f"({html_count} pages, all local assets present, all fragments valid)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
