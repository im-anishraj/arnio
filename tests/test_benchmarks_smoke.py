"""Integration tests to ensure all benchmark scripts execute without errors."""

import subprocess
import sys
from pathlib import Path

import pytest

# Check if the C++ extension is compiled
try:
    import arnio._core  # noqa: F401

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

BENCHMARKS_DIR = Path(__file__).parent.parent / "benchmarks"


def get_benchmark_scripts():
    """Locate all python scripts in the benchmarks directory."""
    if not BENCHMARKS_DIR.exists():
        return []
    scripts = sorted(
        [
            p
            for p in BENCHMARKS_DIR.glob("*.py")
            if p.name != "__init__.py" and p.name != "generate_data.py"
        ]
    )
    return scripts


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
@pytest.mark.parametrize("script_path", get_benchmark_scripts(), ids=lambda p: p.name)
def test_benchmark_script_runs_successfully(script_path):
    """Run a benchmark python script and verify that it exits with code 0."""
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(BENCHMARKS_DIR.parent),
    )

    assert result.returncode == 0, (
        f"Benchmark {script_path.name} failed with return code {result.returncode}.\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )
