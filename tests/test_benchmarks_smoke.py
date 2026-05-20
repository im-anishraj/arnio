"""Integration tests to ensure all benchmark scripts execute without errors."""

import os
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

# Explicit allowlist of CI-safe benchmark scripts
CI_SAFE_BENCHMARKS = [
    "benchmark_auto_clean_memory.py",
    "benchmark_clip_numeric.py",
    "benchmark_combine_columns.py",
    "benchmark_gil_threading.py",
    "benchmark_profile_duplicate_count.py",
    "benchmark_strip_whitespace.py",
    "benchmark_to_pandas_overhead.py",
    "benchmark_vs_pandas.py",
]

# Explicit cheap arguments for specific benchmarks to ensure fast smoke runs
BENCHMARK_ARGS = {
    "benchmark_auto_clean_memory.py": ["--rows", "10", "--repeat", "1"],
    "benchmark_clip_numeric.py": ["--rows", "10", "--runs", "1"],
    "benchmark_profile_duplicate_count.py": ["--rows", "10", "--runs", "1"],
}


def get_benchmark_scripts():
    """Locate all runnable CI-safe benchmark scripts."""
    if not BENCHMARKS_DIR.exists():
        return []
    
    scripts = []
    for name in CI_SAFE_BENCHMARKS:
        script_path = BENCHMARKS_DIR / name
        if script_path.exists():
            scripts.append(script_path)
    return scripts


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
@pytest.mark.parametrize("script_path", get_benchmark_scripts(), ids=lambda p: p.name)
def test_benchmark_script_runs_successfully(script_path):
    """Run a benchmark python script in a cheap smoke-test mode and verify it exits with 0."""
    # Ensure any generated files are also run in dry run/smoke mode
    env = os.environ.copy()
    env["ARNIO_BENCHMARK_DRY_RUN"] = "1"

    # Pre-generate tiny benchmark datasets to prevent benchmark_vs_pandas from raising FileNotFoundError
    if script_path.name == "benchmark_vs_pandas.py":
        generate_path = BENCHMARKS_DIR / "generate_data.py"
        try:
            subprocess.run(
                [sys.executable, str(generate_path)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(BENCHMARKS_DIR.parent),
                timeout=10,
            )
        except subprocess.SubprocessError as e:
            pytest.fail(f"Pre-generating data for benchmark_vs_pandas failed: {e}")

    # Determine command-line arguments for cheap run
    args = BENCHMARK_ARGS.get(script_path.name, [])
    cmd = [sys.executable, str(script_path)] + args

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            cwd=str(BENCHMARKS_DIR.parent),
            timeout=15,  # Add timeout to prevent hangs in CI
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Benchmark {script_path.name} timed out after 15 seconds.\nOutput so far:\n{e.stdout}")

    assert result.returncode == 0, (
        f"Benchmark {script_path.name} failed with return code {result.returncode}.\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )

