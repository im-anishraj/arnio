"""Unit tests for examples/check_env.py environment dashboard."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from examples.check_env import (
    EXAMPLES,
    BuildToolCheck,
    check_dependencies,
    detect_core_status,
    print_dashboard,
)
from examples.example_registry import check_env_examples

READY_BUILD_TOOLS = [
    BuildToolCheck("CMake", "cmake", True, "ok"),
    BuildToolCheck("MSVC compiler", "cl", True, "ok"),
]

MISSING_BUILD_TOOLS = [
    BuildToolCheck("CMake", "cmake", True, "ok"),
    BuildToolCheck("MSVC compiler", "cl", False, "install build tools"),
]


def test_check_env_uses_shared_example_registry() -> None:
    assert EXAMPLES == check_env_examples()
    assert "check_env.py" not in EXAMPLES
    assert EXAMPLES["basic_usage.py"] == []
    assert EXAMPLES["arnio_with_numpy.py"] == ["numpy"]


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
        }

        print_dashboard(results, build_tools=READY_BUILD_TOOLS)
        captured = capsys.readouterr()
        output = captured.out

        # Verify core status reporting
        assert "Available (C++ Accelerated)" in output
        assert "Build toolchain looks ready" in output

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
            "pyarrow": (True, "Installed"),
            "pytest": (True, "Installed"),
        }

        print_dashboard(results, build_tools=READY_BUILD_TOOLS)
        captured = capsys.readouterr()
        output = captured.out

        assert "Available (C++ Accelerated)" in output
        for line in output.splitlines():
            if "arnio_with_duckdb.py" in line:
                assert "[Ready]" in line
        assert "All optional dependencies are successfully installed!" in output
        assert "Native Arnio core is available. You are ready to go." in output


def test_main_exits_when_core_and_required_build_tools_missing() -> None:
    with (
        patch(
            "examples.check_env.check_dependencies",
            return_value={},
        ),
        patch(
            "examples.check_env.check_build_tools",
            return_value=MISSING_BUILD_TOOLS,
        ),
        patch(
            "examples.check_env.detect_core_status",
            return_value=("Not Compiled", False),
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        from examples.check_env import main

        main()

    assert exc_info.value.code == 1


def test_check_env_reports_missing_native_core_readiness(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch.dict(sys.modules, {"arnio._core": None}):
        results = {
            "numpy": (True, "Installed"),
            "pandas": (True, "Installed"),
            "duckdb": (True, "Installed"),
            "sklearn": (True, "Installed"),
            "pyarrow": (True, "Installed"),
            "pytest": (True, "Installed"),
        }

        print_dashboard(results, build_tools=MISSING_BUILD_TOOLS)

        captured = capsys.readouterr()
        output = captured.out

        assert "All optional dependencies are successfully installed!" in output
        assert "Native Arnio core is not available." in output


def test_detect_core_status_uses_importable_package_path(
    tmp_path: Path,
) -> None:
    source_package = tmp_path / "source" / "arnio"
    source_package.mkdir(parents=True)

    init_file = source_package / "__init__.py"
    init_file.write_text("# source package")

    installed_package = tmp_path / "site-packages" / "arnio"
    installed_package.mkdir(parents=True)

    (installed_package / "_arnio_cpp.pyd").write_text("compiled extension")

    with (
        patch.dict(sys.modules, {"arnio._core": None}, clear=False),
        patch(
            "importlib.util.find_spec",
            return_value=MagicMock(origin=str(init_file)),
        ),
    ):
        status, available = detect_core_status()

    assert available is False
    assert "Not Compiled" in status


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
