import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_benchmark_dry_run(tmp_path):
    benchmark_script = (
        Path(__file__).resolve().parents[1]
        / "benchmarks"
        / "benchmark_from_pandas_memory.py"
    )
    if not benchmark_script.exists():
        pytest.skip("benchmark script is only available in a source checkout")

    env = os.environ.copy()
    env["ARNIO_BENCHMARK_DRY_RUN"] = "1"
    result = subprocess.run(
        [sys.executable, str(benchmark_script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "BENCHMARK: from_pandas() peak memory" in result.stdout
    assert "HOTSPOT: per-column peak memory" in result.stdout
