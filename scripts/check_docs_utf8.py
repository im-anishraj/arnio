#!/usr/bin/env python3
"""Fail if tracked documentation files are not valid UTF-8."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

DOC_SUFFIXES = {".md", ".rst"}
DOC_TEXT_SUFFIXES = {".txt"}
DOC_DIRECTORIES = {"docs"}
WEBSITE_TEXT_SUFFIXES = {".html", ".css", ".js"}
WEBSITE_DIRECTORY = "website"
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "site",
}


def _tracked_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return [
            path
            for path in Path(".").rglob("*")
            if path.is_file() and ".git" not in path.parts
        ]

    return [Path(line) for line in result.stdout.splitlines() if line]


def _is_doc_file(path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    if path.suffix.lower() in DOC_SUFFIXES:
        return True
    if path.suffix.lower() in DOC_TEXT_SUFFIXES and path.parts[0] in DOC_DIRECTORIES:
        return True
    return (
        path.suffix.lower() in WEBSITE_TEXT_SUFFIXES and WEBSITE_DIRECTORY in path.parts
    )


def _candidate_files(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if _is_doc_file(path) and path.exists()]


def check_utf8(paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []

    for path in _candidate_files(paths):
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(
                f"{path}: invalid UTF-8 byte at offset {exc.start}: {exc.reason}"
            )

    return errors


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv] if argv else _tracked_files()
    errors = check_utf8(paths)

    if errors:
        print("Documentation files must be valid UTF-8:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Documentation UTF-8 check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
