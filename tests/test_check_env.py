"""Unit tests for examples/check_env.py environment dashboard."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from examples.check_env import print_dashboard


def test_check_env_core_missing(capsys: pytest.CaptureFixture[str]) -> None:
    # Mock arnio._core is missing
    with patch.dict(sys.modules, {"arnio._core": None}):
        results = {
            "numpy": (True, "Installed"),
            "pandas": (True, "Installed"),
            "duckdb": (True, "Installed"),
            "sklearn": (True, "Installed"),
            "pytest": (True, "Installed"),
        }

        print_dashboard(results)
        captured = capsys.readouterr()
        output = captured.out

        # Verify core status reporting
        assert "Not Compiled (Pure-Python Mode)" in output
        # Verify examples report missing core
        for line in output.splitlines():
            if "arnio_with_pandas.py" in line:
                assert "[Missing arnio core]" in line
            if "arnio_with_duckdb.py" in line:
                assert "[Missing arnio core]" in line


def test_check_env_core_available_some_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Mock arnio._core is available
    mock_core = MagicMock()
    with patch.dict(sys.modules, {"arnio._core": mock_core}):
        results = {
            "numpy": (True, "Installed"),
            "pandas": (True, "Installed"),
            "duckdb": (False, "Not Installed"),
            "sklearn": (True, "Installed"),
            "pytest": (True, "Installed"),
        }

        print_dashboard(results)
        captured = capsys.readouterr()
        output = captured.out

        # Verify core status reporting
        assert "Available (C++ Accelerated)" in output

        # Verify ready / missing optional dependencies reported correctly
        for line in output.splitlines():
            if "arnio_with_numpy.py" in line:
                assert "[Ready]" in line
            if "arnio_with_duckdb.py" in line:
                assert "[Missing duckdb]" in line

        # Verify the tip lists the missing package
        assert "pip install duckdb" in output


def test_check_env_all_available(capsys: pytest.CaptureFixture[str]) -> None:
    mock_core = MagicMock()
    with patch.dict(sys.modules, {"arnio._core": mock_core}):
        results = {
            "numpy": (True, "Installed"),
            "pandas": (True, "Installed"),
            "duckdb": (True, "Installed"),
            "sklearn": (True, "Installed"),
            "pytest": (True, "Installed"),
        }

        print_dashboard(results)
        captured = capsys.readouterr()
        output = captured.out

        assert "Available (C++ Accelerated)" in output
        for line in output.splitlines():
            if "arnio_with_duckdb.py" in line:
                assert "[Ready]" in line
        assert "All optional dependencies are successfully installed!" in output
