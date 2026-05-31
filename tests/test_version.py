"""Tests for _version module."""

import pytest


def test_version_is_string():
    from arnio._version import __version__

    assert isinstance(__version__, str)


def test_version_not_empty():
    from arnio._version import __version__

    assert len(__version__) > 0


def test_version_not_unknown_by_default():
    from arnio._version import __version__

    assert __version__ != "unknown"


def test_version_matches_pyproject_pattern():
    import re

    from arnio._version import __version__

    pattern = r'^\d+\.\d+\.\d+'
    assert re.match(pattern, __version__), f"Version '{__version__}' does not match expected pattern"


def test_resolve_version_returns_string():
    from arnio._version import _resolve_version

    result = _resolve_version()
    assert isinstance(result, str)


def test_resolve_version_not_empty():
    from arnio._version import _resolve_version

    result = _resolve_version()
    assert len(result) > 0
