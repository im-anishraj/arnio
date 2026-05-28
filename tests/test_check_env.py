"""Unit tests for examples/check_env.py environment dashboard."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from examples.check_env import EXAMPLES, print_dashboard
from examples.check_env import BuildToolCheck, check_dependencies, print_dashboard

READY_BUILD_TOOLS = [
    BuildToolCheck("CMake", "cmake", True, "ok"),
    BuildToolCheck("MSVC compiler", "cl", True, "ok"),
]

MISSING_BUILD_TOOLS = [
    BuildToolCheck("CMake", "cmake", True, "ok"),
    BuildToolCheck("MSVC compiler", "cl", False, "install build tools"),
]


def test_check_env_core_missing(capsys: pytest.CaptureFixture[str]) -> None:
    # Mock arnio._core is missing
    with patch.dict(sys.modules, {"arnio._core": None}):
        results = {
            "numpy": (True, "Installed"),
            "pandas": (True, "Installed"),
            "duckdb": (True, "Installed"),
            "sklearn": (True, "Installed"),
            "pyarrow": (True, "Installed"),
            "pytest": (True, "Installed"),
            "pyarrow": (True, "Installed"),
        }

        print_dashboard(results, build_tools=MISSING_BUILD_TOOLS)
        captured = capsys.readouterr()
        output = captured.out

        # Verify core status reporting
        assert "Not Compiled" in output
        assert "Build Toolchain Status" in output
        assert "[BUILD BLOCKED]" in output
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
            "pyarrow": (True, "Installed"),
            "pytest": (True, "Installed"),
            "pyarrow": (True, "Installed"),
        }

        print_dashboard(results, build_tools=READY_BUILD_TOOLS)
        captured = capsys.readouterr()
        output = captured.out

        # Verify core status reporting
        assert (
            "Available (C++ Accelerated)" in output
            or "Not Compiled (Pure-Python Mode)" in output
        )
        assert "Available (C++ Accelerated)" in output
        assert "Build toolchain looks ready" in output

        # Verify ready / missing optional dependencies reported correctly
        for line in output.splitlines():
            if "arnio_with_numpy.py" in line:
                assert (
                    "[Ready]" in line
                    or "[Missing arnio core]" in line
                )
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
            "pyarrow": (True, "Installed"),
            "pytest": (True, "Installed"),
            "pyarrow": (True, "Installed"),
        }

        print_dashboard(results, build_tools=READY_BUILD_TOOLS)
        captured = capsys.readouterr()
        output = captured.out

        assert (
            "Available (C++ Accelerated)" in output
            or "Not Compiled (Pure-Python Mode)" in output
        )
        for line in output.splitlines():
            if "arnio_with_duckdb.py" in line:
                assert (
                    "[Ready]" in line
                    or "[Missing arnio core]" in line
                )
        assert "All optional dependencies are successfully installed!" in output


IGNORED = {"check_env.py"}


def test_all_examples_listed() -> None:
    example_files = {p.name for p in Path("examples").glob("*.py")}

    listed = set(EXAMPLES.keys()) | IGNORED

    missing = example_files - listed

    assert not missing, f"Missing examples in EXAMPLES mapping: {missing}"
def test_check_dependencies_reports_broken_import() -> None:
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise RuntimeError("broken binary dependency")
        return real_import(name, *args, **kwargs)

    with (
        patch("examples.check_env.DEPENDENCIES", {"pandas": ("pandas", "desc")}),
        patch("builtins.__import__", side_effect=fake_import),
    ):
        results = check_dependencies()

    assert results["pandas"][0] is False
    assert "Import failed: RuntimeError" in results["pandas"][1]


def test_check_dependencies_reports_transitive_import_error() -> None:
    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("DLL load failed", name="_ctypes")
        raise AssertionError(f"unexpected import: {name}")

    with (
        patch("examples.check_env.DEPENDENCIES", {"pandas": ("pandas", "desc")}),
        patch("builtins.__import__", side_effect=fake_import),
    ):
        results = check_dependencies()

    assert results["pandas"][0] is False
    assert results["pandas"][1] == "Import failed: missing _ctypes"
