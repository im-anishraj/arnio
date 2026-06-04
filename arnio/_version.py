"""Version resolution for arnio."""

import pathlib
import re


def _resolve_version() -> str:
    """Resolve __version__ robustly for both installed and source-checkout imports.

    Strategy
    --------
    1. Try importlib.metadata first (fast path for installed distributions).
    2. If pyproject.toml exists next to the package directory, we are likely
       in a source checkout — read the version from pyproject.toml directly
       instead of trusting metadata that may belong to a different install.
    3. Fall back to importlib.metadata when no pyproject.toml is present
       (normal installed-package import).
    4. Final fallback: "unknown".
    """
    _here = pathlib.Path(__file__).resolve().parent
    _pyproject = _here.parent / "pyproject.toml"

    # If pyproject.toml exists we are in a source checkout.
    # Read the version directly so we never report a stale installed version.
    if _pyproject.exists():
        try:
            _text = _pyproject.read_text(encoding="utf-8")
            _match = re.search(r'^\s*version\s*=\s*"([^"]+)"', _text, re.MULTILINE)
            if _match:
                return _match.group(1)
        except Exception:
            pass

    # Normal installed-package import: trust importlib.metadata.
    try:
        from importlib.metadata import version

        return version("arnio")
    except Exception:
        pass

    return "unknown"


__version__ = _resolve_version()
