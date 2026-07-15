"""Version resolution for arnio."""

from __future__ import annotations

import pathlib
import re


def _resolve_version() -> str:
    """Resolve ``__version__`` for both installed and source-checkout imports.

    Strategy:
        1. Source checkout: read from ``pyproject.toml`` next to the package.
        2. Installed package: use ``importlib.metadata``.
        3. Fallback: ``"unknown"``.
    """
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"

    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8")
            match = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception:
            pass

    try:
        from importlib.metadata import version

        return version("arnio")
    except Exception:
        pass

    return "unknown"


__version__: str = _resolve_version()
